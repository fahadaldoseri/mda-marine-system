# -*- coding: utf-8 -*-
"""تطبيق مادة UKMTO VRA No.11 وJMIC 105 على تقرير سفينتي الحاويات (ملف المستخدم).
يبدأ من نسخة المستخدم كما هي، ويحافظ على القالب والمسافات والترقيم.
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table

SRC = "/home/ubuntu/upload/pasted_file_FxdqHX_تقرير-GFS-PRIDE-GFS-GISELLE-نهائي-2026-10-17.docx"
DST = f"{BRAIN}/reports/docx/تقرير-GFS-PRIDE-GFS-GISELLE-مدقق-2026-10-17.docx"

doc = Document(SRC)
log = []


def plain(el):
    return "".join(n.text or "" for n in el.iter() if n.tag.endswith('}t')).strip()


def paras():
    out = []
    for el in doc.element.body.iterchildren():
        if el.tag.split('}')[1] == 'p' and plain(el):
            out.append(el)
    return out


def tables():
    return doc.tables


def set_par_text(p_el, text):
    runs = p_el.findall(qn('w:r'))
    for r in runs[1:]:
        p_el.remove(r)
    if runs:
        r = runs[0]
        for t in r.findall(qn('w:t')):
            r.remove(t)
        t = OxmlElement('w:t')
        t.set(qn('xml:space'), 'preserve')
        t.text = text
        r.append(t)
    else:
        r = OxmlElement('w:r')
        t = OxmlElement('w:t')
        t.set(qn('xml:space'), 'preserve')
        t.text = text
        r.append(t)
        p_el.append(r)


def find_par(prefix):
    for p in paras():
        if plain(p).startswith(prefix):
            return p
    raise SystemExit(f"لم يُعثر على فقرة تبدأ بـ: {prefix}")


def find_par_after(start_prefix, contains):
    """أول فقرة بعد فقرة معيّنة تحتوي نصًّا معيّنًا."""
    hit = False
    for p in paras():
        t = plain(p)
        if not hit and t.startswith(start_prefix):
            hit = True
            continue
        if hit and contains in t:
            return p
    raise SystemExit(f"لم يُعثر على فقرة تحتوي: {contains}")


def insert_after(el, text, template=None):
    new = deepcopy(template if template is not None else el)
    set_par_text(new, text)
    el.addnext(new)
    return new


def insert_before(el, text, template=None):
    new = deepcopy(template if template is not None else el)
    set_par_text(new, text)
    el.addprevious(new)
    return new


def cell_set(cell, text):
    ps = cell.paragraphs
    for p in ps[1:]:
        p._p.getparent().remove(p._p)
    set_par_text(ps[0]._p, text)


def row_insert(table, after_idx, values, template_idx=1):
    tr = deepcopy(table.rows[template_idx]._tr)
    table.rows[after_idx]._tr.addnext(tr)
    row = table.rows[after_idx + 1]
    for i, v in enumerate(values):
        if i < len(row.cells):
            cell_set(row.cells[i], v)
    return row


def row_index(table, first_cell_prefix):
    for i, row in enumerate(table.rows):
        txt = " ".join(c.text for c in row.cells).strip()
        if txt.startswith(first_cell_prefix):
            return i
    raise SystemExit(f"لم يُعثر على صف يبدأ بـ: {first_cell_prefix}")


T1, T2, T3 = tables()[0], tables()[1], tables()[2]

# ============ 1) جدول 1: صفوف جديدة وتصحيح خلل ============
i_alam = row_index(T1, "العلم")
row_insert(T1, i_alam, [
    "الحمولة الكلية (وفق UKMTO)",
    "غير معلنة رسميًا — محجوبة في سجل UKMTO",
    "50,000 طن",
])
log.append("جدول 1: صف الحمولة الكلية وفق UKMTO")

i_last = row_index(T1, "آخر موضع AIS")
row_insert(T1, i_last, [
    "موضع الإصابة الرسمي (UKMTO)",
    "خط عرض 26°16′ شمالًا وخط طول 056°09′ شرقًا — أثناء الخروج",
    "خط عرض 26°15′ شمالًا وخط طول 056°36′ شرقًا — أثناء الدخول",
])
log.append("جدول 1: صف موضع الإصابة الرسمي بالإحداثيات")

# إصلاح القوس المفتوح في صف آخر موضع AIS
i_last = row_index(T1, "آخر موضع AIS")
c = T1.rows[i_last].cells[2]
txt = c.text
if txt.rstrip().endswith("("):
    cell_set(c, txt.rstrip().rstrip("(").rstrip())
    log.append("جدول 1: إزالة قوس ناقص في صف آخر موضع AIS")

# إضافة حالة الحطام الرسمية إلى خلية الحمولة
i_cargo = row_index(T1, "الحمولة في موقع الغرق")
c = T1.rows[i_cargo].cells[1]
cell_set(c, c.text.rstrip() + " وتصف UKMTO حالة الحطام والحمولة والتلوث بأنها غير مؤكدة.")
log.append("جدول 1: إضافة وصف UKMTO لحالة الحطام")

# ============ 2) جدول 2: صفوف جديدة ============
i_pride = row_index(T2, "13 أكتوبر 2026 الساعة غير محسومة")
c = T2.rows[i_pride].cells[3]
cell_set(c, c.text.rstrip() + " وموضعها الرسمي خط عرض 26°16′ شمالًا وخط طول 056°09′ شرقًا، وهي خارجة من المضيق.")
log.append("جدول 2: موضع GFS PRIDE الرسمي واتجاه العبور")

i_gis = row_index(T2, "13 أكتوبر 2026 (UTC)")
c = T2.rows[i_gis].cells[3]
cell_set(c, c.text.rstrip() + " وموضعها الرسمي خط عرض 26°15′ شمالًا وخط طول 056°36′ شرقًا، وبلاغ UKMTO لها متأخر (time-late).")
log.append("جدول 2: موضع GFS GISELLE الرسمي ووسم البلاغ المتأخر")

row_insert(T2, i_gis, [
    "11 أكتوبر 2026",
    "أوقات غير منشورة",
    "—",
    "موجة إصابات في نطاق هرمز: ست سفن بمقذوفات غير محددة وطائرة مسيّرة، وفق البلاغات 164-26 إلى 169-26. منها ناقلة خام أعلنت عدم قدرتها على المناورة. وسفينة حاويات داخلة بإصابة طفيفة واحدة في طاقمها.",
    "بلاغات رسمية من UKMTO",
])
row_insert(T2, i_gis + 1, [
    "11 أكتوبر 2026",
    "165-26",
    "—",
    "أُصيبت ناقلة منتجات بطائرة مسيّرة قبالة صحار (خط عرض 24°33′ شمالًا وخط طول 056°42′ شرقًا)؛ أُخلي طاقمها وفُقد اثنان وفق وزارة الخارجية الهندية؛ وظلت على مقربة من ميناء صحار حتى 14 أكتوبر.",
    "بلاغ رسمي من UKMTO",
])
log.append("جدول 2: صفا موجة 11 أكتوبر وإصابة المسيّرة قرب صحار")

i_nav = row_index(T2, "17 أكتوبر 2026")
row_insert(T2, i_nav, [
    "16 أكتوبر 2026",
    "161100Z OCT 26 (وقت إصدار الملف)",
    "14:00",
    "UKMTO: التقرير الأسبوعي لمنطقة الإبلاغ الطوعي رقم 11 — يضم المواضع الرسمية للبلاغات، وعدّادات الأضرار والنتائج، وإحصاءات العبور والتشويش.",
    "منتج رسمي من UKMTO",
])
log.append("جدول 2: صف إصدار تقرير UKMTO الأسبوعي رقم 11")

# ============ 3) المثبت رسميًا ============
p = find_par("المثبت رسميًا")
insert_after(p, "ويضيف UKMTO أن أغلب السفن المُستهدَفة تمتنع عن الإبلاغ، وأنه يعلم بحوادث من مصادر أخرى لكنه مقيّد بغياب التحقق. ولذلك يكون الرقم المُعلن حدًّا أدنى لا حصرًا. وأُبلغ عن 12 هجومًا في أسبوع واحد: 10 في مضيق هرمز، وواحد في الخليج العربي، وواحد في خليج عُمان.")
log.append("المثبت رسميًا: امتناع السفن عن الإبلاغ + 12 هجومًا في أسبوع")

# ============ 4) المجهولات ============
p = find_par("مجهولات مؤثرة في التقدير")
cell_extra = " ولم تُعلن المصادر الرسمية اسم المرسى الآمن الذي وصلته «GFS GISELLE»، ولا عدد الحاويات المفقودة من «GFS PRIDE»."
insert_after(p, plain(p) + cell_extra)
p.getparent().remove(p)
log.append("المجهولات: إضافة المرسى الآمن غير المعلن وعدد الحاويات المفقودة")

# ============ 5) قسم جديد: المؤشرات الإقليمية المرجعية ============
anchor = find_par("سُجلت أربع وقائع على سفن تديرها GFS")
heading = insert_after(anchor, "المؤشرات الإقليمية المرجعية (UKMTO وJMIC).", template=find_par("بيانات السفينتين"))
lead = insert_after(heading, "أرقام رسمية حتى 14–16 أكتوبر 2026 تُقرأ كحدّ أدنى لا حصرًا، وتضع الواقعتين في نطاقهما الإقليمي.", template=anchor)
log.append("قسم جديد: المؤشرات الإقليمية المرجعية")

# جدول المؤشرات: يُبنى من قالب جدول 3
src_tbl = T3._tbl
new_tbl_el = deepcopy(src_tbl)
lead.getparent()  # noop
lead.addnext(new_tbl_el)
# تنظيف الجدول الجديد إلى الصفوف المطلوبة
new_tbl = Table(new_tbl_el, doc)
while len(new_tbl.rows) > 1:
    new_tbl._tbl.remove(new_tbl.rows[-1]._tr)
cell_set(new_tbl.rows[0].cells[0], "المؤشر")
cell_set(new_tbl.rows[0].cells[1], "الرقم")
cell_set(new_tbl.rows[0].cells[2], "السند")

ROWS = [
    ("تحذيرات UKMTO منذ بداية العام", "145", "التقرير الأسبوعي رقم 11"),
    ("نشرات استشارية", "20", "التقرير الأسبوعي رقم 11"),
    ("حوادث مرتبطة بنزاع إيران–أمريكا", "135", "التقرير الأسبوعي رقم 11"),
    ("بلاغات مضيق هرمز منذ 28 فبراير", "84", "التقرير الأسبوعي رقم 11"),
    ("تقارير أضرار بسفن (سنوي)", "114", "التقرير الأسبوعي رقم 11"),
    ("حالات اقتراب كاد", "13", "التقرير الأسبوعي رقم 11"),
    ("وفيات وإصابات", "76", "التقرير الأسبوعي رقم 11"),
    ("خسارة كلية / احتاجت مساعدة / واصلت الرحلة", "6 / 24 / 105", "التقرير الأسبوعي رقم 11"),
    ("هجمات هذا الأسبوع", "12 (10 هرمز · 1 خليج عربي · 1 خليج عُمان)", "UKMTO"),
    ("إصابات بمقذوف على المسار الجنوبي منذ 6 يوليو", "55 من 74", "UKMTO"),
    ("عبور هرمز في سبعة أيام", "125 خارجة · 129 داخلة — أقل نحو 70% من ما قبل النزاع", "UKMTO / NCAGS"),
    ("العبور المرصود بـAIS", "42 (كان 60)، والميسّر أمريكيًا بنسبة 5:1", "UKMTO"),
    ("نسبة ناقلات الطاقة من العبور", "80%", "UKMTO"),
    ("مواضع AIS شاذة في سبعة أيام", "23,166 (كان 18,881)", "UKMTO"),
    ("بلاغات تداخل GNSS منذ بداية العام", "675", "UKMTO"),
    ("مستويات التهديد", "هرمز شديد · الخليج العربي وخليج عُمان متوسط · خليج عدن وباب المندب جسيم", "JMIC"),
]
for k, v, s in ROWS:
    tpl = 1 if len(new_tbl.rows) > 1 else 0
    row_insert(new_tbl, len(new_tbl.rows) - 1, [k, v, s], template_idx=tpl)
log.append(f"جدول المؤشرات الإقليمية: {len(ROWS)} صفًّا")

note = insert_after(new_tbl_el, "وأثر التشويش على التوثيق مباشر: مواضع AIS الشاذة بلغت 23,166 في سبعة أيام، وبلاغات التداخل 675 منذ بداية العام. ولذلك لا تُستخدم بيانات التتبع للحسم.", template=anchor)
log.append("ملاحظة أثر التشويش على التوثيق")

# ============ 6) تصحيح CAPE DAO ============
i_cape = row_index(T3, "«CAPE DAO»")
cell_set(T3.rows[i_cape].cells[2],
         "توفي بحّار هندي واحد؛ وتديرها Peonies Shipmanagement. وأفاد تحذير NAVAREA IX 370/26 وHYDROPAC 2970/26 بغرقها في 13 أكتوبر، "
         "وتقييم JMIC أن الحالة متنازع عليها وأنها لم تغرق. والمعتمد عندنا: بقيت طافية وأبحرت إلى مرسى آمن (لم يُسمَّ رسميًا).")
log.append("تصحيح CAPE DAO: فصل البلاغ عن التقييم")

# ============ 7) ملحق (ج) سند الأرقام ============
anchor_b = find_par("ملحق (ب): خطوط الخدمة والحركة السابقة.")
insert_after(anchor_b, "ملحق (ج): سند الأرقام الرسمية.", template=anchor_b)
log.append("سطر ملحق (ج) في قائمة الملاحق")

p = find_par("نسخة إلى:")
annex_head = insert_before(p, "ملحق (ج): سند الأرقام الرسمية.", template=find_par("الملاحق:"))
src_tbl = T3._tbl
new_tbl_el2 = deepcopy(src_tbl)
annex_head.addnext(new_tbl_el2)
new_tbl = Table(new_tbl_el2, doc)
while len(new_tbl.rows) > 1:
    new_tbl._tbl.remove(new_tbl.rows[-1]._tr)
cell_set(new_tbl.rows[0].cells[0], "المصدر الرسمي")
cell_set(new_tbl.rows[0].cells[1], "الرقم أو الوصف")
cell_set(new_tbl.rows[0].cells[2], "ما استُخدم منه")
SRC_ROWS = [
    ("UKMTO — بلاغات 164-26 إلى 173-26", "بلاغات رسمية", "المواضع بالإحداثيات، واتجاه العبور، والأوزان، وجملة الأضرار والنتائج"),
    ("UKMTO — التقرير الأسبوعي رقم 11", "16 أكتوبر 2026", "العدّادات، والعبور، والتشويش، ونسب المسار الجنوبي"),
    ("JMIC — تحديث 105", "مسودة · 15 أكتوبر 2026", "الحطام والمواضع، ومستويات التهديد، وتقييم حالة CAPE DAO"),
    ("NAVAREA IX", "373/26 و381/26 (ما زال ساريًا)", "موضع الحطام ووصف سبب التحذير الملاحي"),
    ("HYDROPAC", "2978/26 و2970/26", "موضع حطام «GFS PRIDE»، وبلاغ غرق «CAPE DAO»"),
    ("هيئة الموانئ والملاحة السنغافورية", "بيان 14 أكتوبر 2026", "تأكيد الغرق وسلامة الطواقم، ووصف المرسى الآمن"),
    ("وزارة النقل العُمانية", "تحذير 15–16 أكتوبر 2026", "الحاويات الطافية والمواد الخطرة ورقم الإبلاغ"),
    ("القيادة المركزية الأمريكية", "بيان 15 أكتوبر 2026", "إسناد إصابة «GFS PRIDE» إلى مقذوف للحرس الثوري، ونفي رواية اللغم"),
]
for a, b, c_ in SRC_ROWS:
    tpl = 1 if len(new_tbl.rows) > 1 else 0
    row_insert(new_tbl, len(new_tbl.rows) - 1, [a, b, c_], template_idx=tpl)
log.append(f"ملحق (ج): {len(SRC_ROWS)} صفًّا")


# ============ 8) ضبط تخطيط الصفحات: لا عنوان يتيم قبل جدول ============
from docx.text.paragraph import Paragraph as _Par
_children = list(doc.element.body.iterchildren())
_fixed = 0
for _i, _el in enumerate(_children[:-1]):
    if _el.tag.endswith('}p') and _children[_i + 1].tag.endswith('}tbl'):
        _par = _Par(_el, doc)
        if not _par.paragraph_format.keep_with_next:
            _par.paragraph_format.keep_with_next = True
            _fixed += 1
log.append(f"ضبط بقاء العنوان مع الجدول: {_fixed} فقرة")

doc.save(DST)
print("  ✔ حُفظ:", DST)
print("  عدد التعديلات:", len(log))
for i, l in enumerate(log, 1):
    print(f"   {i:2d}. {l}")
print("  حجم الملف:", Path(DST).stat().st_size, "بايت")
