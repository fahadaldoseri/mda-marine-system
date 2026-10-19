#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يبني خريطة حرفية لتغييرات المصطلحات في تقرير GFS: القسم ← الفقرة/الصف ← النص الحالي ← النص الجديد."""
import json, re, sys
from pathlib import Path
from docx import Document

DOC = Path('/home/ubuntu/brain-marine-news/reports/docx/تقرير-GFS-PRIDE-GFS-GISELLE-المصحح-2026-10-16.docx')

# (القديم، الجديد، الوسم)
RULES = [
    ("بقيت طافية وأبحرت إلى مرسى", "لم تغرق، وواصلت إبحارها إلى مرسى آمن", "صياغة مباشرة"),
    ("خط العمل (الخدمة)", "خط السير الملاحي", "مصطلح"),
    ("مؤكد — بيانات التتبع", "بيانات تتبّع السفن (AIS)", "حالة التحقق"),
    ("مؤكد — بلاغ رسمي وتحليل مهني", "مؤكد رسميًّا من UKMTO — اسم السفينة من مصدر مهني", "حالة التحقق"),
    ("مؤكد — الجهة الرسمية", "مؤكد رسميًّا من هيئة الموانئ والملاحة بسنغافورة (MPA)", "حالة التحقق"),
    ("مؤكد — تحليل مهني", "مؤكد رسميًّا من UKMTO — اسم السفينة من مصدر مهني", "حالة التحقق"),
    ("بلاغ رسمي مباشر (UKMTO) — تعيين الاسم من مصدر مهني", "مؤكد رسميًّا من UKMTO — اسم السفينة من مصدر مهني", "حالة التحقق"),
    ("مؤكد — تحذير ملاحي رسمي", "تحذير ملاحي رسمي من الهيدروغرافي الباكستاني (NAVAREA IX)", "حالة التحقق"),
    ("رسمي مباشر", "رسمي مباشر من <اسم الجهة>", "حالة التحقق"),
    ("سفينة شقيقة", "سفينة في الأسطول نفسه", "مصطلح"),
    ("النافذة نفسها", "في المدة نفسها", "مصطلح"),
    ("عبور مغادر", "أثناء خروجها من المضيق", "مصطلح"),
    ("عبور داخل (قادم)", "أثناء دخولها للمضيق", "مصطلح"),
    ("وألغت العبور", "ولم تُكمل عبور المضيق", "مصطلح"),
    ("راية", "علم", "مصطلح"),
    ("السائبة", "سفينة البضائع الجافة", "مصطلح"),
    ("ناقلة السوائب", "سفينة البضائع الجافة", "مصطلح"),
    ("ناقلة سوائب", "سفينة بضائع جافة", "مصطلح"),
]


def units(doc):
    """يُرجع الوحدات بترتيب المستند: (النوع، المرجع، القسم، النص)."""
    out, heading = [], ""
    body = doc.element.body
    ti = pi = 0
    for child in body.iterchildren():
        tag = child.tag.split('}')[-1]
        if tag == 'p':
            pi += 1
            p = doc.paragraphs[pi - 1] if pi - 1 < len(doc.paragraphs) else None
            if p is None:
                continue
            txt = p.text.strip()
            st = (p.style.name or '')
            if txt and ('Heading' in st or 'عنوان' in st):
                heading = txt
                out.append(('عنوان', f'فقرة {pi}', heading, txt))
            elif txt:
                out.append(('فقرة', f'فقرة {pi}', heading, txt))
        elif tag == 'tbl':
            t = doc.tables[ti]
            ti += 1
            for ri, row in enumerate(t.rows, 1):
                for ci, cell in enumerate(row.cells, 1):
                    txt = cell.text.strip()
                    if txt:
                        out.append(('جدول', f'جدول {ti} · صف {ri} · عمود {ci}', heading, txt))
    return out


def main():
    doc = Document(DOC)
    us = units(doc)
    hits = []
    for kind, ref, sec, txt in us:
        for old, new, tag in RULES:
            if old in txt:
                # سياق مختصر حول الموضع
                i = txt.find(old)
                ctx = txt[max(0, i - 45): i + len(old) + 45].replace('\n', ' ')
                hits.append({'kind': kind, 'ref': ref, 'section': sec, 'old': old,
                             'new': new, 'tag': tag, 'context': ctx, 'cell': txt[:120]})
    out = Path('/home/ubuntu/brain-marine-news/audit/خريطة-تطبيق-المصطلحات-GFS.json')
    out.write_text(json.dumps(hits, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'الوحدات: {len(us)} · مواضع مطابقة: {len(hits)}')
    print(f'حُفظت في: {out}')
    # طباعة مضغوطة
    for h in hits:
        print(f"[{h['tag']}] {h['ref']} | {h['section'][:38]} | {h['old']} ← {h['new'][:38]}")
        print(f"      سياق: …{h['context']}…")


if __name__ == '__main__':
    main()