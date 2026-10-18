#!/usr/bin/env python3
"""توليد نسخة Word (RTL) من مصدر التقرير اليومي.

الاستخدام:
  python3 tools/build_report_docx.py --date 2026-10-18 [--no-hidden]

المخرجات:
  reports/docx/التقرير-اليومي-<التاريخ>.docx
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/ubuntu/brain-marine-news")
MAP_PNG = Path("/home/ubuntu/seawatch/dist/reports/img")
HIDDEN_SECTIONS = ("المصادر والمراجع", "موثوقية المصادر")


def set_rtl(par, align_right: bool = True):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    ppr = par._p.get_or_add_pPr()
    if ppr.find(qn("w:bidi")) is None:
        ppr.append(ppr.makeelement(qn("w:bidi"), {}))
    if align_right:
        par.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def add_run(par, text: str, bold: bool = False, size=None, mono: bool = False):
    from docx.oxml.ns import qn
    from docx.shared import Pt
    run = par.add_run(text)
    run.bold = bold
    if size:
        run.font.size = Pt(size)
    run.font.name = "Arial"
    rpr = run._element.get_or_add_rPr()
    if rpr.find(qn("w:rtl")) is None:
        rpr.append(rpr.makeelement(qn("w:rtl"), {}))
    return run


def rich(par, text: str, base_bold: bool = False, size=None):
    """يكتب نصًا مع دعم **عريض** والروابط والرموز الحرفية."""
    text = re.sub(r"<[^>]+>", "", text)                      # وسوم HTML
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)  # روابط
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            add_run(par, part[2:-2], bold=True, size=size)
        else:
            add_run(par, part, bold=base_bold, size=size)


def add_table(doc, rows: list[list[str]]):
    from docx.oxml.ns import qn
    from docx.shared import Pt
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    tblpr = t._tbl.tblPr
    if tblpr.find(qn("w:bidiVisual")) is None:
        tblpr.append(tblpr.makeelement(qn("w:bidiVisual"), {}))
    for ri, r in enumerate(rows):
        cells = t.add_row().cells
        for c, val in zip(cells, r):
            c.text = ""
            p = c.paragraphs[0]
            set_rtl(p)
            rich(p, val.strip(), base_bold=(ri == 0), size=9)
            p.paragraph_format.space_after = Pt(0)
    return t


def footer_page_numbers(section):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_rtl(p)
    add_run(p, "صفحة ", size=8)
    for instr in ("PAGE", "NUMPAGES"):
        fld = p._p.makeelement(qn("w:fldSimple"), {qn("w:instr"): f" {instr} "})
        p._p.append(fld)
        add_run(p, " من " if instr == "PAGE" else "", size=8)


def build(date: str, include_hidden: bool) -> Path:
    from docx import Document
    from docx.shared import Cm, Pt

    src = ROOT / "reports" / f"{date}-sectioned.md"
    lines = src.read_text(encoding="utf-8").split("\n")

    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Arial"
    st.font.size = Pt(10.5)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin, sec.bottom_margin = Cm(1.6), Cm(1.8)
    sec.left_margin, sec.right_margin = Cm(1.8), Cm(1.8)
    footer_page_numbers(sec)

    i = 0
    inserted_map = False
    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()
        if not s:
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl, title = len(m.group(1)), m.group(2).strip()
            if lvl == 2 and any(h in title for h in HIDDEN_SECTIONS) and not include_hidden:
                # تُستبعد من النسخة المطبوعة، وتُدرج بعنوان واضح إن طُلبت
                p = doc.add_paragraph()
                set_rtl(p)
                add_run(p, f"— قسم «{title}» محجوب من نسخة الطباعة بحسب قرار صاحب القرار —",
                        bold=True, size=9)
                i += 1
                continue
            p = doc.add_paragraph()
            set_rtl(p)
            add_run(p, title, bold=True, size=17 if lvl == 1 else (13 if lvl == 2 else 11.5))
            p.paragraph_format.space_before = Pt(10 if lvl <= 2 else 6)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            i += 1
            # إدراج الخريطة في قسم التوزيع الجغرافي
            if lvl == 2 and "التوزيع الجغرافي" in title and not inserted_map:
                png = MAP_PNG / f"map-{date}.png"
                if png.exists():
                    pic = doc.add_paragraph()
                    set_rtl(pic)
                    pic.add_run().add_picture(str(png), width=Cm(17.0))
                    cap = doc.add_paragraph()
                    set_rtl(cap)
                    add_run(cap, "خريطة الوقائع — مواقع الوقائع داخل نطاق التقرير.", size=8.5)
                    inserted_map = True
            continue

        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i].strip()):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            if rows:
                add_table(doc, rows)
                doc.add_paragraph()
            continue

        if s.startswith(">"):
            p = doc.add_paragraph()
            set_rtl(p)
            rich(p, s.lstrip("> ").strip(), size=9)
            i += 1
            continue

        m = re.match(r"^\s*[-*]\s+(.*)$", s)
        if m:
            p = doc.add_paragraph(style="List Bullet")
            set_rtl(p)
            rich(p, m.group(1))
            i += 1
            continue

        m = re.match(r"^\s*(\d+)[.)]\s+(.*)$", s)
        if m:
            p = doc.add_paragraph(style="List Number")
            set_rtl(p)
            rich(p, m.group(2))
            i += 1
            continue

        p = doc.add_paragraph()
        set_rtl(p)
        p.paragraph_format.space_after = Pt(4)
        rich(p, s)
        i += 1

    out = ROOT / "reports" / "docx" / f"التقرير-اليومي-{date}.docx"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--no-hidden", action="store_true",
                    help="استبعاد قسمي المصادر والموثوقية كليًا")
    a = ap.parse_args()
    out = build(a.date, include_hidden=not a.no_hidden)
    print(f"[docx] {out} ({out.stat().st_size/1024:.0f} ك.ب)")
    # تحقق الاكتمال: تحويل إلى PDF وعدّ الأقسام
    r = subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf",
                        "--outdir", str(out.parent), str(out)],
                       capture_output=True, text=True, timeout=300)
    pdf = out.with_suffix(".pdf")
    if pdf.exists():
        txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        src = (ROOT / "reports" / f"{a.date}-sectioned.md").read_text(encoding="utf-8")
        heads = re.findall(r"^##\s+(.+)$", src, re.M)
        nrm = lambda t: re.sub(r"[^\u0621-\u064A]", "", t)
        missing = [h for h in heads if nrm(h)[:14] not in nrm(txt)]
        pages = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        pages = re.search(r"Pages:\s+(\d+)", pages)
        print(f"[pdf]  {pdf} · صفحات: {pages.group(1) if pages else '؟'}")
        print(f"[تحقق] أقسام المصدر: {len(heads)} · غير موجودة في Word: {len(missing)}"
              + (f" → {missing}" if missing else " ✓"))
    else:
        print("تعذّر التحقق عبر PDF:", r.stdout[-150:], r.stderr[-150:])
    return 0


if __name__ == "__main__":
    sys.exit(main())