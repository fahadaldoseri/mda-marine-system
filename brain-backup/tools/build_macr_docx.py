#!/usr/bin/env python3
"""مولّد ملفات MACR (Word/PDF) من تقرير Markdown.

يطبّق مواصفات المهارة (البند 5.1):
- A4 · خط Sakkal Majalla · أحجام 24/18/16/14 · تباعد متعدد 0.8 · مسافة بعد 10pt
- اتجاه RTL ومحاذاة يمين لكل فقرة (مع w:rtl/w:bidi في docDefaults)
- ثلاثة أقسام: غلاف (بلا ترويسة) · متن (طرة «محظور» + ترقيم من 2) · ملاحق (ترويسة فارغة)
- إطار صفحة أزرق #215E99 · جداول RTL بمحاذاة وسط
"""
import re
import sys
import copy
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT = 'Sakkal Majalla'
BLUE = '215E99'


# ---------- أدوات XML ----------
def _set(el, tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), v)
    el.append(e)
    return e


def rtl_para(p, align_right=True):
    """يمين (RTL) = <w:bidi/> بلا jc لأن الافتراضي في الفقرة العربية هو يمين (مؤكد باختبار فعلي).
    يسار = بلا bidi مع jc=left، لتجاوز تفسير LibreOffice لـ«right» بوصفه نهاية السطر في RTL."""
    pPr = p._p.get_or_add_pPr()
    for tag in ('w:bidi', 'w:jc', 'w:spacing'):
        el = pPr.find(qn(tag))
        if el is not None:
            pPr.remove(el)
    pPr.append(OxmlElement('w:bidi'))
    pm = OxmlElement('w:rPr'); pm.append(OxmlElement('w:rtl')); pPr.append(pm)
    sp = OxmlElement('w:spacing')
    sp.set(qn('w:before'), '0')
    sp.set(qn('w:after'), '200')
    sp.set(qn('w:line'), '192')
    sp.set(qn('w:lineRule'), 'auto')
    pPr.append(sp)
    if align_right is not True:
        jc = OxmlElement('w:jc')
        jc.set(qn('w:val'), 'left')
        pPr.append(jc)
    return p


def fmt_runs(p, size=16, bold=False, color=None, align=None):
    """يطبّق الخط والحجم والاتجاه على كل حرف بترتيب صحيح: rFonts · b · color · sz · szCs · rtl."""
    for r in p.runs:
        rPr = r._element.get_or_add_rPr()
        for tag in ('w:rFonts', 'w:b', 'w:color', 'w:sz', 'w:szCs', 'w:rtl'):
            el = rPr.find(qn(tag))
            if el is not None:
                rPr.remove(el)
        rf = OxmlElement('w:rFonts')
        for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
            rf.set(qn(a), FONT)
        rPr.append(rf)
        if bold or r.bold:
            rPr.append(OxmlElement('w:b'))
        if color:
            c = OxmlElement('w:color'); c.set(qn('w:val'), color); rPr.append(c)
        sz = OxmlElement('w:sz'); sz.set(qn('w:val'), str(int(size * 2))); rPr.append(sz)
        szc = OxmlElement('w:szCs'); szc.set(qn('w:val'), str(int(size * 2))); rPr.append(szc)
        rPr.append(OxmlElement('w:rtl'))
    return p


def para(doc, text, size=16, bold=False, align='right', space_after=10, color=None):
    """فقرة جديدة بكل المواصفات، مع دعم **عريض** داخل النص."""
    p = doc.add_paragraph()
    for i, part in enumerate(re.split(r'\*\*(.+?)\*\*', text)):
        if part == '':
            continue
        r = p.add_run(part)
        r.bold = bold or (i % 2 == 1)
    if align == 'center':
        pPr = p._p.get_or_add_pPr()
        pPr.append(OxmlElement('w:bidi'))
        jc = OxmlElement('w:jc'); jc.set(qn('w:val'), 'center'); pPr.append(jc)
    elif align == 'left':
        pPr = p._p.get_or_add_pPr()
        off = OxmlElement('w:bidi'); off.set(qn('w:val'), '0'); pPr.append(off)
        jc = OxmlElement('w:jc'); jc.set(qn('w:val'), 'left'); pPr.append(jc)
    else:
        rtl_para(p, align_right=True)
    fmt_runs(p, size=size, color=color)
    return p


def page_border(section):
    sectPr = section._sectPr
    pgb = OxmlElement('w:pgBorders')
    pgb.set(qn('w:offsetFrom'), 'page')
    for side in ('w:top', 'w:left', 'w:bottom', 'w:right'):
        e = OxmlElement(side)
        e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '12')
        e.set(qn('w:space'), '24'); e.set(qn('w:color'), BLUE)
        pgb.append(e)
    sectPr.append(pgb)


def page_num_start(section, start):
    sectPr = section._sectPr
    e = OxmlElement('w:pgNumType')
    e.set(qn('w:start'), str(start))
    sectPr.append(e)


def field_page(paragraph, size=14):
    for instr, kind in (('begin', None), ('PAGE', 'instr'), ('end', None)):
        if kind == 'instr':
            r = paragraph.add_run()
            f = OxmlElement('w:instrText'); f.set(qn('xml:space'), 'preserve'); f.text = ' PAGE '
            r._element.append(f)
        else:
            r = paragraph.add_run()
            fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'), instr)
            r._element.append(fc)
        rPr = r._element.get_or_add_rPr()
        rf = OxmlElement('w:rFonts')
        for a in ('w:ascii', 'w:hAnsi', 'w:cs'):
            rf.set(qn(a), FONT)
        rPr.insert(0, rf)
        _set(rPr, 'w:sz', **{'w:val': str(size * 2)})
        _set(rPr, 'w:szCs', **{'w:val': str(size * 2)})


def doc_defaults(doc):
    """إلزامي: <w:rtl/> و<w:bidi/> في docDefaults لضمان المحاذاة في Word."""
    styles = doc.styles.element
    dd = styles.find(qn('w:docDefaults'))
    if dd is None:
        dd = OxmlElement('w:docDefaults'); styles.insert(0, dd)
    rPrD = dd.find(qn('w:rPrDefault'))
    if rPrD is None:
        rPrD = OxmlElement('w:rPrDefault'); dd.append(rPrD)
    rPr = rPrD.find(qn('w:rPr'))
    if rPr is None:
        rPr = OxmlElement('w:rPr'); rPrD.append(rPr)
    rf = OxmlElement('w:rFonts')
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), FONT)
    rPr.insert(0, rf)
    _set(rPr, 'w:rtl')
    _set(rPr, 'w:sz', **{'w:val': '32'})
    pPrD = dd.find(qn('w:pPrDefault'))
    if pPrD is None:
        pPrD = OxmlElement('w:pPrDefault'); dd.append(pPrD)
    pPr = pPrD.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr'); pPrD.append(pPr)
    _set(pPr, 'w:bidi')


def table_rtl(tbl):
    tblPr = tbl._tbl.tblPr
    _set(tblPr, 'w:bidiVisual')
    for row in tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                rtl_para(p, align_right=False)
                pPr = p._p.get_or_add_pPr()
                pPr.find(qn('w:jc')).set(qn('w:val'), 'center')
                fmt_runs(p, size=14)


# ---------- قراءة التقرير ----------
def read_report(path):
    lines = Path(path).read_text(encoding='utf-8').split('\n')
    meta, body, in_head = {}, [], True
    for ln in lines:
        if ln.startswith('#'):
            in_head = False
        m = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', ln.strip()) if in_head else None
        if m and not m.group(1).startswith('جدول'):
            meta[m.group(1)] = m.group(2)
            continue
        body.append(ln)
    return meta, body


def build(md_path, out_path):
    meta, lines = read_report(md_path)
    doc = Document()
    doc_defaults(doc)

    # ===== قسم ١: الغلاف =====
    s1 = doc.sections[0]
    s1.page_width, s1.page_height = Cm(21), Cm(29.7)
    for m in ('top_margin', 'bottom_margin', 'left_margin', 'right_margin'):
        setattr(s1, m, Cm(2.54))
    page_border(s1)
    for _ in range(6):
        para(doc, '', size=16, space_after=0)
    para(doc, meta.get('نوع المستند', 'تقرير'), size=18, align='center', space_after=6)
    title = Path(md_path).read_text(encoding='utf-8').split('\n')[0].lstrip('# ').strip()
    para(doc, title, size=24, align='center', space_after=10)
    para(doc, meta.get('الجهة المُصدِرة', 'مركز الوعي بالمجال البحري'), size=18, align='center', space_after=6)
    para(doc, f"{meta.get('التصنيف','')} · {meta.get('النطاق','')}", size=14, align='center', space_after=6)
    para(doc, f"مملكة البحرين — {meta.get('التاريخ','').replace('/', ' / ')}", size=18, align='center', space_after=0)

    # ===== قسم ٢: المتن =====
    s2 = doc.add_section(WD_SECTION.NEW_PAGE)
    s2.page_width, s2.page_height = Cm(21), Cm(29.7)
    s2.top_margin, s2.bottom_margin = Cm(1.25), Cm(0.75)
    s2.left_margin, s2.right_margin = Cm(1.27), Cm(1.27)
    page_border(s2)
    page_num_start(s2, 2)
    s2.header.is_linked_to_previous = False
    s2.footer.is_linked_to_previous = False
    for hp in list(s2.header.paragraphs):
        hp.text = ''
    h = s2.header.paragraphs[0]
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.add_run('محظور'); fmt_runs(h, size=16)
    f0 = s2.footer.paragraphs[0]
    f0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f0.add_run('محظور'); fmt_runs(f0, size=16)
    f1 = s2.footer.add_paragraph()
    f1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field_page(f1, size=16)

    # ===== محتوى المتن =====
    i, in_body, n_tbl = 0, True, 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith('## ملحق'):
            break
        if ln.startswith('## '):
            para(doc, ln[3:], size=18, space_after=10, color=BLUE)
        elif ln.startswith('**جدول') and ln.endswith('**') and '—' in ln:
            para(doc, ln.strip('*'), size=14, space_after=4)
        elif ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(set(c) <= set('-: ') for c in cells):
                    rows.append(cells)
                i += 1
            n_tbl += 1
            tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
            tbl.style = 'Table Grid'
            for r, cells in enumerate(rows):
                for c, v in enumerate(cells):
                    tbl.cell(r, c).text = v
            table_rtl(tbl)
            para(doc, '', size=14, space_after=4)
            continue
        elif re.match(r'^\d+\. ', ln):
            para(doc, re.sub(r'^\d+\. ', '', ln), size=16)
        elif ln.startswith('**الرتبة'):
            para(doc, ln.replace('**', ''), size=18, space_after=10, align='left')
        elif ln.startswith('**') and ln.endswith('**'):
            para(doc, ln, size=16, space_after=4)
        elif ln.strip() and not ln.startswith('#'):
            para(doc, ln.strip(), size=14, space_after=6)
        i += 1

    # ===== قسم ٣: الملاحق =====
    s3 = doc.add_section(WD_SECTION.NEW_PAGE)
    s3.page_width, s3.page_height = Cm(21), Cm(29.7)
    s3.top_margin, s3.bottom_margin = Cm(1.25), Cm(0.75)
    s3.left_margin, s3.right_margin = Cm(1.27), Cm(1.27)
    page_border(s3)
    s3.header.is_linked_to_previous = False
    s3.footer.is_linked_to_previous = False
    for hp in list(s3.header.paragraphs):
        hp.text = ''
    for fp in list(s3.footer.paragraphs):
        fp.text = ''

    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith('## '):
            para(doc, ln[3:], size=14, space_after=10, color=BLUE)
        elif ln.startswith('**جدول') and ln.endswith('**') and '—' in ln:
            para(doc, ln.strip('*'), size=14, space_after=4)
        elif ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(set(c) <= set('-: ') for c in cells):
                    rows.append(cells)
                i += 1
            tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
            tbl.style = 'Table Grid'
            for r, cells in enumerate(rows):
                for c, v in enumerate(cells):
                    tbl.cell(r, c).text = v
            table_rtl(tbl)
            para(doc, '', size=14, space_after=4)
            continue
        elif re.match(r'^\d+\. ', ln):
            para(doc, re.sub(r'^\d+\. ', '', ln), size=14, space_after=6)
        i += 1

    doc.save(out_path)
    print(f'  ✔ أُنشئ: {out_path}')
    return out_path


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])