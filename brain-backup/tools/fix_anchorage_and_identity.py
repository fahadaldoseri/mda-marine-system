#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""إصلاح ثلاث نقاط في تقرير السفينتين:
1) لغة «بقدرتها الذاتية» → «بمحركاتها» + تعيين حالة المرسى الآمن (غير معلن رسميًا).
2) تصحيح هوية AL SAADIYAT وبيانات ALFONSO.
3) توضيح أول وآخر محطة في خط الخدمة + إضافة بيان ثغرة معلومات.
يطبَّق على: مصدر Brain، ونص الموقع، وملف Word.
"""
import sys
from pathlib import Path

NOTE = ("ثغرة معلومات: بيان سنغافورة الرسمي يقول إن «GFS GISELLE» وصلت مرسى آمنًا ولم تسمِّه. "
        "ولم تثبت المصادر الرسمية وصولها الفعلي إلى الفجيرة، ولا محطة خورفكان في رحلتها محل الواقعة. "
        "وآخر موضع تسجيل لها كان في مرسى الفجيرة (الإمارات) قبل الواقعة بأسبوعين تقريبًا. "
        "تُعد هذه الثغرة مفتوحة وتُفصح صراحةً، وتُفحص في كل تحديث.")

REPL = [
    # 1) لغة المرسى
    ("ووصلت بقدرتها الذاتية إلى مرسى آمن",
     "وواصلت إبحارها بمحركاتها إلى مرسى آمن"),
    ("ثم وصلت بقدرتها الذاتية إلى مرسى آمن.",
     "ثم واصلت إبحارها بمحركاتها إلى مرسى آمن؛ ولم تسمِّ المصادر الرسمية هذا المرسى."),
    ("بقدرتها الذاتية", "بمحركاتها"),
    # 2) خطوط الخدمة — أول وآخر محطة
    ("| خط الخدمة المنشور | خورفكان – الفجيرة – كراتشي | نافا شيفا – الفجيرة (وسجل الرحلة المفتوح لا يثبت محطة خورفكان في الرحلة محل الواقعة) |",
     "| خط الخدمة المنشور | خورفكان – الفجيرة – كراتشي. وفي الرحلة محل الواقعة: أبحرت من كراتشي (باكستان) في ١ أكتوبر ٢٠٢٦، ووصلت مرسى الفجيرة (الإمارات) في ٣ أكتوبر ٢٠٢٦. وسجل الرحلة المفتوح لا يثبت محطة خورفكان في هذه الرحلة | نافا شيفا (الهند) – الفجيرة (الإمارات). أبحرت من نافا شيفا في ٥ أكتوبر ٢٠٢٦، والوصول المتوقّع إلى الفجيرة ٨ أكتوبر ٢٠٢٦ (غير مثبت) |"),
    # 3) السعة الاسمية لـGFS GISELLE
    ("٤٬٣٥٠ وحدة مكافئة (TEU) — سعة اسمية، ولا تعني عدد الحاويات المحمَّلة فعلًا",
     "٤٬٣٧٠ وحدة مكافئة (TEU) بحسب مصدر مهني؛ وسجل التسجيل يذكر ٤٬٣٥٠. والسعة اسمية ولا تعني عدد الحاويات المحمَّلة فعلًا"),
    # 4) هوية AL SAADIYAT
    ("سفينة حاويات تديرها GFS، أُصيبت أثناء خروجها من المضيق",
     "سفينة حاويات (١٬٧٣٠ وحدة مكافئة، IMO 9760598) ترفع علم جزر مارشال وتشغّلها Safeen Feeders التابعة لمجموعة موانئ أبوظبي؛ أُصيبت أثناء خروجها من المضيق"),
    ("أضرار طفيفة، بلا إصابات، وواصلت الرحلة.",
     "أضرار طفيفة، بلا إصابات، وواصلت الرحلة. وخطها المنشور بين الإمارات وجيبوتي."),
    # 5) هوية ALFONSO
    ("| «ALFONSO» | ناقلة يُرجح مهنيًا أنها «ALFONSO»؛",
     "| «ALFONSO» | ناقلة منتجات نفطية وكيميائية (IMO 9256298، ٣٨٬٨٧٧ طنًا ساكنًا، علم بربادوس، وتديرها شركة من دبي)؛ ويُرجح مهنيًا أنها «ALFONSO»؛"),
]

def fix_text(t):
    n = 0
    for a, b in REPL:
        if a in t:
            n += t.count(a)
            t = t.replace(a, b)
    return t, n

def fix_md(path):
    p = Path(path)
    if not p.exists():
        return 0
    t = p.read_text(encoding="utf-8")
    t2, n = fix_text(t)
    if "ثغرة معلومات: بيان سنغافورة" not in t2 and "خطوط الخدمة والحركة السابقة" in t2:
        lines = t2.split("\n")
        idx = [i for i, l in enumerate(lines) if l.startswith("## ") and "خطوط الخدمة" in l]
        if idx:
            i = idx[0] + 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            lines.insert(i, "### ثغرة معلومات معلنة\n" + NOTE + "\n")
            t2 = "\n".join(lines)
            n += 1
    if n:
        p.write_text(t2, encoding="utf-8")
    return n

def fix_docx(path):
    from docx import Document
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    from docx.table import Table
    from docx.oxml import OxmlElement
    d = Document(path)
    total = 0

    def fix_par(par):
        nonlocal total
        t = par.text
        t2, n = fix_text(t)
        if n and par.runs:
            par.runs[0].text = t2
            for r in par.runs[1:]:
                r.text = ""
            total += n

    for par in d.paragraphs:
        fix_par(par)
    for tb in d.tables:
        for row in tb.rows:
            for c in row.cells:
                for par in c.paragraphs:
                    fix_par(par)

    # إدراج بيان الثغرة بعد جدول البيانات الفنية (الذي يحوي «خط الخدمة المنشور»)
    if "ثغرة معلومات" not in "\n".join(p.text for p in d.paragraphs):
        for ch in list(d.element.body.iterchildren()):
            if ch.tag != qn("w:tbl"):
                continue
            txt = " ".join(c.text for r in Table(ch, d).rows for c in r.cells)
            if "خط الخدمة المنشور" in txt:
                new_p = OxmlElement("w:p")
                ch.addnext(new_p)
                par = Paragraph(new_p, d)
                par.add_run("ثغرة معلومات معلنة")
                par2 = OxmlElement("w:p")
                new_p.addnext(par2)
                Paragraph(par2, d).add_run(NOTE)
                total += 1
                break
    d.save(path)
    return total

if __name__ == "__main__":
    srcs = [
        "/home/ubuntu/brain-marine-news/reports/GFS-MACR-المعتمد-2026-10-17.md",
        "/home/ubuntu/brain-marine-news/reports/special-2026-10-15-GFS-MACR.md",
        "/home/ubuntu/seawatch/sources/special/gfs-pride-giselle-2026-10-15.md",
    ]
    for s in srcs:
        print(f"  {Path(s).name}: {fix_md(s)} استبدال")
    docx = "/home/ubuntu/brain-marine-news/reports/docx/تقرير-GFS-PRIDE-GFS-GISELLE-مصحح-2026-10-17.docx"
    print(f"  DOCX: {fix_docx(docx)} استبدال")