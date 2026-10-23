#!/usr/bin/env python3
"""تجميع «الأوامر والتعليمات» الكاملة لنظام Brain في وثيقة واحدة (Markdown + DOCX + PDF).

الاستخدام:
  python3 tools/build_instructions_doc.py

المخرجات:
  docs/الأوامر-والتعليمات-الكاملة.md
  reports/docx/الأوامر-والتعليمات-الكاملة.docx
  reports/docx/الأوامر-والتعليمات-الكاملة.pdf
"""
from __future__ import annotations
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(f"{BRAIN}")
DOCS = ROOT / "docs"
DOCX_DIR = ROOT / "reports" / "docx"
TITLE = "الأوامر والتعليمات — نظام مركز الوعي بالمجال البحري (Brain)"

# (المصدر, عنوان القسم في الوثيقة المجمّعة)
PARTS = [
    ("INDEX.md", "الفهرس الملزم — قواعد القراءة والتنفيذ"),
    ("sections/00-identity.md", "أولًا: الهوية والنطاق والمسؤولية"),
    ("sections/10-sources.md", "ثانيًا: المصادر الأربعون وأصولها"),
    ("sections/20-language.md", "ثالثًا: اللغة والمصطلحات المعتمدة"),
    ("sections/30-structure.md", "رابعًا: بنية التقرير وترتيب أقسامه"),
    ("sections/40-blocks.md", "خامسًا: كتل التقرير وصيغها"),
    ("sections/50-analysis.md", "سادسًا: التحليل والاحتمالات ونسبة الحوادث إلى جهات"),
    ("sections/55-intelligence.md", "سابعًا: التحليل الاستخباري (ح1–ح12)"),
    ("sections/60-validation.md", "ثامنًا: بوابات التحقق (ف1–ف5)"),
    ("sections/70-delivery.md", "تاسعًا: بوابة التسليم والقنوات (س1–س2)"),
    ("sections/75-style.md", "عاشرًا: الأسلوب الكتابي للتقارير العملياتية"),
    ("sections/80-learning.md", "حادي عشر: التعلّم وتسجيل الدروس"),
    ("sections/90-automation.md", "ثاني عشر: خط التشغيل اليومي (أ1–أ14)"),
    ("appendices/version-numbering.md", "ملحق أ: ترقيم الإصدارات"),
    ("appendices/report-blocks.md", "ملحق ب: مرجع الكتل"),
    ("appendices/terminology.md", "ملحق ج: المعجم والمصطلحات"),
    ("appendices/telegram-delivery.md", "ملحق د: قناة تسليم تلغرام"),
    ("appendices/web-delivery.md", "ملحق هـ: التسليم على الموقع الدائم"),
    ("appendices/navarea-373-381-coordinates.md", "ملحق و: صيغة الإحداثيات وقاعدة NAVAREA"),
    ("docs/دليل-الأساليب-التحريرية-العسكرية-2026-10-17.md", "ملحق ز: دليل الأساليب التحريرية العسكرية"),
]


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return text


def demote(text: str, levels: int = 1) -> str:
    """يُخفض عناوين المصدر درجة أو درجتين حتى لا تتزاحم مع عناوين الوثيقة المجمّعة."""
    out = []
    for line in text.split("\n"):
        m = re.match(r"^(#{1,5})\s+(.*)$", line)
        if m:
            hashes = "#" * min(6, len(m.group(1)) + levels)
            out.append(f"{hashes} {m.group(2)}")
        else:
            out.append(line)
    return "\n".join(out)


def build_md() -> Path:
    parts_md = []
    toc = []
    for i, (rel, heading) in enumerate(PARTS, 1):
        p = ROOT / rel
        if not p.exists():
            print(f"  تحذير: المصدر غير موجود — {rel}")
            continue
        body = demote(strip_frontmatter(p.read_text(encoding="utf-8")).strip(), 1)
        anchor = f"ق{i}"
        toc.append(f"{i}. {heading}  \n   `{rel}`")
        parts_md.append(f"\n---\n\n## {anchor}. {heading}\n\n{body}\n")
    head = (
        f"# {TITLE}\n\n"
        f"**تاريخ التجميع:** {datetime.now().strftime('%Y-%m-%d')} · "
        f"**الحالة:** ساري · **الجهة:** مركز الوعي بالمجال البحري MDA.BH\n\n"
        "هذه وثيقة مرجعية واحدة تجمع الأوامر والتعليمات الملزمة لتشغيل التقرير اليومي "
        "والتقارير الخاصة ونسخ التسليم. المصدر الملزم يبقى ملفات `sections/` و`appendices/` "
        "داخل مجلد النظام؛ وهذه الوثيقة تجميع للقراءة والمراجعة، وأي تعديل يُعتمد يجب أن يُطبَّق "
        "على ملف المصدر أولًا ثم يُعاد تجميع هذه الوثيقة.\n\n"
        "## المحتويات\n\n" + "\n".join(toc) + "\n"
    )
    out = DOCS / "الأوامر-والتعليمات-الكاملة.md"
    out.write_text(head + "".join(parts_md), encoding="utf-8")
    return out


def md_to_docx(md: Path) -> Path:
    """تحويل مبسّط إلى Word عربي RTL (عناوين · نقاط · جداول · فقرات)."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)
    rpr = style.element.get_or_add_rPr()
    rtl = rpr.makeelement(qn("w:rtl"), {})
    rpr.append(rtl)

    def para(text: str, size: int = 11, bold: bool = False, style_name: str | None = None):
        p = doc.add_paragraph(style=style_name) if style_name else doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        ppr = p._p.get_or_add_pPr()
        bidi = ppr.makeelement(qn("w:bidi"), {})
        ppr.append(bidi)
        run = p.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)
        run.font.name = "Arial"
        rpr2 = run._element.get_or_add_rPr()
        rtl2 = rpr2.makeelement(qn("w:rtl"), {})
        rpr2.append(rtl2)
        return p

    lines = md.read_text(encoding="utf-8").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.strip() == "---":
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            para(m.group(2).strip(), size={1: 18, 2: 15, 3: 13}.get(lvl, 12), bold=True)
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                if not re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            if rows:
                t = doc.add_table(rows=0, cols=len(rows[0]))
                t.style = "Table Grid"
                for r in rows:
                    cells = t.add_row().cells
                    for c, val in zip(cells, r):
                        c.text = ""
                        p = c.paragraphs[0]
                        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        run = p.add_run(val)
                        run.font.size = Pt(9.5)
                        run.font.name = "Arial"
            continue
        m = re.match(r"^\s*[-*+]\s+(.*)$", line)
        if m:
            para("• " + m.group(1).strip(), size=11)
            i += 1
            continue
        m = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)
        if m:
            para(f"{m.group(1)}. {m.group(2).strip()}", size=11)
            i += 1
            continue
        if line.lstrip().startswith(">"):
            para(line.lstrip().lstrip(">").strip(), size=11)
            i += 1
            continue
        para(re.sub(r"[*_`]", "", line).strip(), size=11)
        i += 1

    out = DOCX_DIR / "الأوامر-والتعليمات-الكاملة.docx"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out


def main() -> int:
    md = build_md()
    print(f"[md] {md} ({md.stat().st_size/1024:.0f} ك.ب)")
    docx = md_to_docx(md)
    print(f"[docx] {docx} ({docx.stat().st_size/1024:.0f} ك.ب)")
    pdf = docx.with_suffix(".pdf")
    r = subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf",
                        "--outdir", str(docx.parent), str(docx)],
                       capture_output=True, text=True, timeout=300)
    if pdf.exists():
        print(f"[pdf] {pdf} ({pdf.stat().st_size/1024:.0f} ك.ب)")
    else:
        print("فشل تحويل PDF:", r.stdout[-200:], r.stderr[-200:])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())