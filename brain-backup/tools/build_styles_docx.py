#!/usr/bin/env python3
"""مولّد ملف Word/PDF لتقرير الأساليب التحريرية، باتجاه RTL إلزامي.

يعيد استخدام أدوات مولّد MACR المعتمد (الخط Sakkal Majalla · RTL · جداول RTL).
الاستخدام: python3 tools/build_styles_docx.py <input.md> <output.docx>
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.shared import Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import build_macr_docx as B  # أدوات RTL والخطوط والجداول

BLUE = B.BLUE


def parse(md_path):
    """يفصل ترويسة البيانات (المفتاح: القيمة) عن المتن، ويقرأ العنوان."""
    lines = Path(md_path).read_text(encoding='utf-8').split('\n')
    meta, body, in_head, title = {}, [], True, ''
    for ln in lines:
        s = ln.strip()
        if s.startswith('#'):
            in_head = False
            if not title and s.startswith('# '):
                title = s[2:].strip()
                if ' — ' in title and title.split(' — ')[0].strip().isdigit():
                    title = title.split(' — ', 1)[1].strip()
        m = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', s) if in_head else None
        if m:
            meta[m.group(1).strip()] = m.group(2).strip()
            continue
        body.append(ln)
    return meta, body, title


def build(md_path, out_path):
    meta, lines, title = parse(md_path)
    doc = Document()
    B.doc_defaults(doc)

    # ===== الغلاف =====
    s1 = doc.sections[0]
    s1.page_width, s1.page_height = Cm(21), Cm(29.7)
    for m in ('top_margin', 'bottom_margin', 'left_margin', 'right_margin'):
        setattr(s1, m, Cm(2.54))
    B.page_border(s1)
    B.para(doc, 'بسم الله الرحمن الرحيم', size=18, align='center', space_after=30)
    B.para(doc, 'مركز الوعي بالمجال البحري', size=20, align='center', space_after=6)
    B.para(doc, 'دولة مملكة البحرين', size=16, align='center', space_after=60)
    B.para(doc, meta.get('نوع المستند', 'تقرير مرجعي'), size=18, align='center', space_after=6)
    B.para(doc, title, size=24, align='center', space_after=20)
    B.para(doc, meta.get('التصنيف', ''), size=14, align='center', space_after=6)
    B.para(doc, meta.get('النطاق', ''), size=14, align='center', space_after=40)
    B.para(doc, meta.get('التاريخ', '').replace('/', ' / '), size=18, align='center', space_after=6)
    B.para(doc, 'إعداد: مركز الوعي بالمجال البحري', size=14, align='center', space_after=0)

    # ===== المتن =====
    s2 = doc.add_section(WD_SECTION.NEW_PAGE)
    s2.page_width, s2.page_height = Cm(21), Cm(29.7)
    s2.top_margin, s2.bottom_margin = Cm(1.5), Cm(1.0)
    s2.left_margin, s2.right_margin = Cm(1.5), Cm(1.5)
    B.page_border(s2)
    B.page_num_start(s2, 2)
    s2.header.is_linked_to_previous = False
    s2.footer.is_linked_to_previous = False
    hp = s2.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hp.add_run(title + ' — مرجع داخلي ملزم')
    B.fmt_runs(hp, size=12)
    f1 = s2.footer.paragraphs[0]
    f1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    B.field_page(f1, size=14)

    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s or s == '---':
            i += 1
            continue
        if s.startswith('### '):
            B.para(doc, s[4:], size=16, bold=True, space_after=8, color=BLUE)
        elif s.startswith('## '):
            B.para(doc, s[3:], size=18, space_after=10, color=BLUE)
        elif s.startswith('# '):
            B.para(doc, s[2:], size=20, align='center', space_after=12)
        elif s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(set(c) <= set('-: ') for c in cells):
                    rows.append(cells)
                i += 1
            ncols = max(len(r) for r in rows)
            tbl = doc.add_table(rows=len(rows), cols=ncols)
            tbl.style = 'Table Grid'
            for r, cells in enumerate(rows):
                for c in range(ncols):
                    tbl.cell(r, c).text = cells[c] if c < len(cells) else ''
            B.table_rtl(tbl)
            B.para(doc, '', size=12, space_after=4)
            continue
        elif s.startswith('> '):
            B.para(doc, s[2:], size=14, space_after=6)
        elif s.startswith('- '):
            B.para(doc, '• ' + s[2:], size=14, space_after=6)
        elif re.match(r'^\d+\.\s', s):
            B.para(doc, s, size=14, space_after=6)
        else:
            B.para(doc, s, size=14, space_after=8)
        i += 1

    doc.save(out_path)
    print(f'  ✔ أُنشئ ملف Word: {out_path}')
    return out_path


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])