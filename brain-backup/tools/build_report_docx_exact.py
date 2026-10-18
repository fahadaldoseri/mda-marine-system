#!/usr/bin/env python3
"""توليد نسخة Word «طبق الأصل» من نسخة PDF المعتمدة (v3).

المسار: صفحة الطباعة (HTML) ← إزالة عناصر الشاشة وما يُحجب في الطباعة ←
تحويل LibreOffice إلى DOCX ← معالجة نهائية (RTL · الخط · الهوامش · التذييل · الخريطة).

الاستخدام:
  python3 tools/build_report_docx_exact.py --date 2026-10-18
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
DIST = Path("/home/ubuntu/seawatch/dist/reports")
MAP_PNG = DIST / "img"

# عناصر تظهر على الشاشة فقط، أو تُحجب في نسخة الطباعة
STRIP_SELECTORS = ["#topbar", ".topbar", ".no-print", ".notice", ".map-keys",
                   ".dc-foot", ".cls-banner", "nav", "script", "style",
                   ".theme-toggle", ".pg-nav"]
HIDDEN_HEADINGS = ("المصادر والمراجع", "موثوقية المصادر")


def preprocess(date: str, workdir: Path) -> Path:
    from bs4 import BeautifulSoup
    src = DIST / f"{date}.html"
    soup = BeautifulSoup(src.read_text(encoding="utf-8"), "html.parser")

    for sel in STRIP_SELECTORS:
        for el in soup.select(sel):
            el.decompose()

    # حجب أقسام المصادر والموثوقية كما في الطباعة
    for h in soup.find_all(["h2", "h3"]):
        title = h.get_text(" ", strip=True)
        if any(k in title for k in HIDDEN_HEADINGS):
            sec = h.find_parent("section") or h.parent
            (sec or h).decompose()

    # استبدال رسم الخريطة (SVG) بصورة الخريطة المعتمدة
    png = MAP_PNG / f"map-{date}.png"
    if png.exists():
        shutil.copy(png, workdir / png.name)
        target = None
        for svg in soup.find_all("svg"):
            if svg.find(class_=re.compile("mp-")) or "mp-events" in str(svg)[:4000]:
                target = svg
                break
        if target is None:
            panel = soup.select_one(".map-viz") or soup.select_one(".map-wrap")
            target = panel.find("svg") if panel else None
        if target is not None:
            img = soup.new_tag("img", src=png.name)
            img["style"] = "width:100%"
            target.replace_with(img)

    out = workdir / f"{date}-print.html"
    out.write_text(str(soup), encoding="utf-8")
    return out


def to_docx(html: Path, workdir: Path) -> Path:
    # HTML يُفتح كـ Writer/Web، فيلزم تحديد مرشّح التصدير صراحةً
    r = subprocess.run(["soffice", "-env:UserInstallation=file:///tmp/lo-exact-profile",
                        "--headless", "--convert-to", "docx:MS Word 2007 XML",
                        "--outdir", str(workdir), str(html)],
                       capture_output=True, text=True, timeout=420)
    out = workdir / (html.stem + ".docx")
    if not out.exists():
        raise SystemExit("فشل تحويل LibreOffice إلى DOCX: " + (r.stdout + r.stderr)[-300:])
    return out


def polish(docx_path: Path, date: str, out_path: Path) -> dict:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    d = Document(str(docx_path))
    stats = {"paras": 0, "tables": len(d.tables), "images": 0}

    def rtl(p):
        ppr = p._p.get_or_add_pPr()
        if ppr.find(qn("w:bidi")) is None:
            ppr.append(ppr.makeelement(qn("w:bidi"), {}))
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for r in p.runs:
            rpr = r._element.get_or_add_rPr()
            if rpr.find(qn("w:rtl")) is None:
                rpr.append(rpr.makeelement(qn("w:rtl"), {}))
            r.font.name = "Arial"

    for p in d.paragraphs:
        rtl(p)
        stats["paras"] += 1
    for t in d.tables:
        tblpr = t._tbl.tblPr
        if tblpr.find(qn("w:bidiVisual")) is None:
            tblpr.append(tblpr.makeelement(qn("w:bidiVisual"), {}))
        for row_i, row in enumerate(t.rows):
            for c in row.cells:
                for p in c.paragraphs:
                    rtl(p)
                    if row_i == 0:
                        for r in p.runs:
                            r.bold = True

    # مقاس الورقة والهوامش مطابقة للطباعة المعتمدة
    for sec in d.sections:
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.top_margin, sec.bottom_margin = Cm(1.6), Cm(1.8)
        sec.left_margin, sec.right_margin = Cm(1.8), Cm(1.8)

    # تذييل بترقيم الصفحات، وترويسة باسم التقرير
    for sec in d.sections:
        f = sec.footer.paragraphs[0]
        f.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rtl(f)
        run = f.add_run("صفحة ")
        run.font.size = Pt(8)
        fld = f._p.makeelement(qn("w:fldSimple"), {qn("w:instr"): " PAGE "})
        f._p.append(fld)
        run2 = f.add_run(" من ")
        run2.font.size = Pt(8)
        fld2 = f._p.makeelement(qn("w:fldSimple"), {qn("w:instr"): " NUMPAGES "})
        f._p.append(fld2)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(out_path))
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    date = a.date

    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        html = preprocess(date, wd)
        docx_raw = to_docx(html, wd)
        out = B / "reports" / "docx" / f"التقرير-اليومي-{date}-طبق-الأصل.docx"
        stats = polish(docx_raw, date, out)
        print(f"[docx] {out} ({out.stat().st_size/1024:.0f} ك.ب)")
        print(f"[بنية] فقرات {stats['paras']} · جداول {stats['tables']}")

    # تحقق: تحويل إلى PDF وقياس المطابقة
    r = subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf",
                        "--outdir", str(out.parent), str(out)],
                       capture_output=True, text=True, timeout=420)
    pdf = out.with_suffix(".pdf")
    if pdf.exists():
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
        txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        nrm = lambda t: re.sub(r"[^\u0621-\u064A0-9]", "", t)
        flat = nrm(txt)
        heads = [h.strip() for h in re.findall(r"^##\s+(.+)$",
                 (B / "reports" / f"{date}-sectioned.md").read_text(encoding="utf-8"), re.M)]
        miss = [h for h in heads if not any(x in h for x in HIDDEN_HEADINGS)
                and nrm(h)[:12] not in flat]
        hidden_shown = any(nrm(x) in flat for x in HIDDEN_HEADINGS)
        print(f"[pdf]  صفحات: {pages} | أقسام ناقصة: {len(miss)}"
              + (f" → {miss}" if miss else " ✓")
              + f" | المصادر ظاهرة: {'نعم' if hidden_shown else 'لا ✓'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
