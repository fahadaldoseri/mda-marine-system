#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إعادة إصدار «تقرير استهداف السفينتين GFS PRIDE وGFS GISELLE» بالتصحيحات المعتمدة،
مع الحفاظ التام على قالب المستخدم: الأنماط، الترقيم، التباعد، الترويسة، الاتجاه RTL.
المصدر: ملف المستخدم المعدّل يدويًا. المخرج: نسخة مصححة جديدة (لا يُمسّ الأصل).
"""
import shutil
import sys
from copy import deepcopy
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

SRC = "/home/ubuntu/upload/pasted_file_7Dghr6_GFSPRIDE&CAPEDAO.docx"
OUT = "/home/ubuntu/brain-marine-news/reports/docx/تقرير-GFS-PRIDE-GFS-GISELLE-المصحح-2026-10-16.docx"


# ---------- أدوات ----------
def set_text(par, text):
    """يضع النص في أول مقطع ويحذف الباقي — يحفظ تنسيق المقطع الأول."""
    runs = par.runs
    if not runs:
        par.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r._element.getparent().remove(r._element)


def is_head_run(r):
    return bool(r.bold or r.underline)


def rewrite(par, new_text):
    """يحافظ على تنسيق العنوان الافتتاحي (عريض/تحته خط) ويستبدل بقية النص."""
    runs = par.runs
    if not runs:
        par.add_run(new_text)
        return
    i = 0
    while i < len(runs) - 1 and is_head_run(runs[i]):
        i += 1
    head = "".join(r.text for r in runs[:i])
    if head and new_text.startswith(head):
        runs[i].text = new_text[len(head):]
        for r in runs[i + 1:]:
            r._element.getparent().remove(r._element)
    else:
        set_text(par, new_text)


def rewrite_all(doc, mapping):
    """mapping: [(كلمة مفتاحية, نص جديد)] — يطابق على نص الفقرة الحالي."""
    done = set()
    for par in doc.paragraphs:
        t = par.text
        for key, new in mapping:
            if key in t and key not in done:
                rewrite(par, new)
                done.add(key)
                break
    return done


def set_cell(cell, text):
    ps = cell.paragraphs
    if not ps:
        return
    rewrite(ps[0], text)
    for extra in ps[1:]:
        extra._p.getparent().remove(extra._p)


def find_row(tbl, needle):
    for r in tbl.rows:
        if any(needle in c.text for c in r.cells):
            return r
    return None


def cell_by(tbl, needle, col):
    r = find_row(tbl, needle)
    return r.cells[col] if r else None


def main():
    shutil.copy(SRC, OUT)
    d = Document(OUT)

    # ===== 1) فقرات المتن =====
    body = [
        ("عام. إصابة سفينتين",
         "عام. إصابة سفينتي حاويات تحملان علم سنغافورة بمقذوفين غير محددي المصدر في مضيق هرمز ومياه مسندم.\n"
         "«GFS PRIDE» غرقت بعد حريق ونجا طاقمها وعددهم ٢١ بحّارًا، و«GFS GISELLE» بقيت طافية وأبحرت إلى مرسى مسندم "
         "ونجا طاقمها وعددهم ٢٢ بحّارًا، وكلتاهما لمشغّل واحد هو Global Feeder Shipping الإماراتية على خطوط التغذية الخليجية."),
        ("القصد. عرض",
         "القصد. عرض وتوضيح ما جرى للسفينتين بالتاريخ والوقت والمكان، وفصل المؤكد عن غير المؤكد، "
         "وتحديد هوية السفينتين وحركتهما وشحنتهما."),
        ("بيانات الناقلة", "بيانات السفينتين."),
        ("تملك مجموعة AD Ports",
         "تملك مجموعة AD Ports نسبة واحد وثمانين في المئة من الشركة المشغّلة Global Feeder Shipping، والتشغيل إماراتي. "
         "ولذلك تصنّف المصادر المهنية الحادثين ضمن استهداف السفن المرتبطة بالإمارات."),
        ("إصابة السفينتين بمقذوف",
         "المؤكد: إصابة السفينتين بمقذوف غير محدد المصدر، وحريق «GFS PRIDE» ثم غرقها، وتضرر بدن «GFS GISELLE» "
         "واستمرار إبحارها. وسلامة الطواقم كاملة وعددها ثلاثة وأربعون بحّارًا."),
        ("السفن المتصلة بالحادث", "السفن في سياق الحادث"),
        ("جدول 3: السفن المتصلة مباشرة", "جدول 3: السفن في سياق الحادث"),
        ("تكرار استهداف الأسطول نفسه في يوليو",
         "تكرار استهداف سفن المشغّل نفسه مؤشر استخباري: «GFS GALAXY» في 11 يوليو، ثم «GFS PRIDE» و«GFS GISELLE» "
         "و«AL SAADIYAT» في أكتوبر. ويستوجب ذلك رفع درجة المتابعة لهذا المشغّل ولسفنه كلها، لا الاكتفاء بتقييم السفينة الواحدة."),
        ("السفينتان من أسطول واحد",
         "السفينتان من أسطول واحد ومشغّل واحد وخطّين متقاربين. وهذا يرفع احتمال أن الاستهداف موجّه إلى نوع المشغّل، "
         "لا إلى سفينة بعينها."),
        ("نمط الإصابة متكرر",
         "نمط الإصابة متكرر: إصابة البدن، ثم الحريق، ثم إعاقة الدفع. والنمط نفسه ظهر في «CAPE DAO» و«GFS GALAXY»."),
        ("الحطام خطر مستمر",
         "الحطام خطر مستمر بعد الغرق. الحاويات الطافية تفرض تحذيرًا ملاحيًا وتعقيدًا بيئيًا وتأمينيًا ممتدًا."),
        ("الرسو قرب المضيق",
         "الرسو قرب المضيق أو قرب الساحل العُماني لا يوفّر حماية مؤكدة؛ فقد وقعت إصابات في 11 و13 أكتوبر على مقربة "
         "من الساحل وفي مرسى صحار."),
        ("التهديد خارج نطاق الناقلات",
         "التهديد خارج نطاق الناقلات. إصابة سفينتي حاويات في يوم واحد تعني أن حماية الناقلات وحدها لا تكفي، "
         "وأن سفن التغذية تحمل إمداد الخليج وهي مكشوفة."),
        ("انقطاع بث AIS",
         "انقطاع بث AIS يقلّل فرص الكشف المسبق، ويُلغي وجود موضع حيّ لحظة الإصابة، فيُبطئ الإنقاذ ويُضعف التوثيق."),
        ("تكرار استهداف الأسطول نفسه إشارة",
         "تكرار استهداف سفن المشغّل نفسه إشارة استخبارية: أربع حوادث على سفن المشغّل نفسه خلال نحو ثلاثة أشهر "
         "تستوجب تصنيفًا خاصًا لهذا النوع من المشغّلين."),
        ("نسخه الى", "نسخة إلى:"),
        ("ملحق (أ) صور السفن", "ملحق (أ): صور السفن."),
        ("ملحق (ب) خط السير", "ملحق (ب): خط السير."),
        ("صور لسفينة GFS Giselle", "صور السفينة «GFS GISELLE»"),
    ]
    done = rewrite_all(d, body)

    # سطر «ما لم يثبت» بعد آخر بند في الخلاصة
    anchor = None
    for par in d.paragraphs:
        if "تكرار استهداف سفن المشغّل نفسه إشارة" in par.text:
            anchor = par
    if anchor is not None:
        new_el = deepcopy(anchor._p)
        anchor._p.addnext(new_el)
        np = Paragraph(new_el, anchor._parent)
        rewrite(np, "ما لم يثبت: الجهة المنفذة، ونوع المقذوف، وبيان الحمولة الرسمي. ولا يُبنى على أي منها حكم.")

    # ===== 2) الجداول =====
    t1, t2, t3 = d.tables[0], d.tables[1], d.tables[2]

    # جدول 1 — البيانات الفنية
    for row in t1.rows:
        label = row.cells[0].text.strip()
        if label == "الراية":
            set_cell(row.cells[0], "العلم")
        if label == "آخر إشارة قبل الإصابة":
            set_cell(row.cells[0], "آخر إشارة بث (AIS) قبل الإصابة")
    for row in t1.rows:
        for i in (1, 2):
            tx = row.cells[i].text
            if " - " in tx:
                set_cell(row.cells[i], tx.replace(" - ", " — "))
            if "حاويات طافية -" in row.cells[i].text:
                set_cell(row.cells[i], row.cells[i].text.replace("حاويات طافية -", "حاويات طافية —"))

    # جدول 2 — التسلسل الزمني: الترتيب الزمني
    r_dep_pride = find_row(t2, "تُبحر من كراتشي")
    r_dep_giselle = find_row(t2, "تُبحر من نافا شيفا")
    if r_dep_pride is not None and r_dep_giselle is not None:
        r_dep_pride._tr.addnext(r_dep_giselle._tr)

    # جدول 2 — نصوص الخلايا
    t2_fixes = [
        ("تُبحر من كراتشي", 4, "مؤكد — بيانات التتبع"),
        ("تصل مرسى الفجيرة", 4, "مؤكد — بيانات التتبع"),
        ("تُبحر من نافا شيفا", 4, "مؤكد — بيانات التتبع"),
        ("الوصول المتوقع", 3, "الوصول المتوقّع لـ«GFS GISELLE» إلى الفجيرة"),
        ("الوصول المتوقع", 4, "مؤكد — بيانات التتبع"),
        ("على مسافة ميل بحري واحد", 4, "مؤكد — بلاغ رسمي وتحليل مهني"),
        ("أثناء عبور قادم", 3, "إصابة «GFS GISELLE» أثناء عبور داخل (قادم)"),
        ("أثناء عبور قادم", 4, "مؤكد — بلاغ رسمي مباشر"),
        ("AL SAADIYAT", 4, "مؤكد — تحليل مهني"),
        ("اعتراض الحرس الثوري", 3,
         "اعتراض الحرس الثوري ناقلة النفط «GOL» عند المدخل وأمرها بالعودة، فغيّرت مسارها وألغت العبور ولم تُصب"),
        ("اعتراض الحرس الثوري", 4, "بلاغ رسمي مباشر (UKMTO) — تعيين الاسم من مصدر مهني"),
        ("NAVAREA IX", 3,
         "تحذير ملاحي رسمي (الهيدروغرافي الباكستاني — NAVAREA IX): «GFS PRIDE» مشتعلة وتائهة، "
         "وموضع الغرق أربعة أميال بحرية شمال غرب رأس الشيخ مسعود"),
        ("NAVAREA IX", 4, "مؤكد — تحذير ملاحي رسمي"),
        ("الجهة الرسمية السنغافورية", 3, "هيئة الموانئ والملاحة بسنغافورة: تأكيد الغرق وسلامة الطواقم"),
    ]
    for needle, col, val in t2_fixes:
        c = cell_by(t2, needle, col)
        if c is not None:
            set_cell(c, val)

    # حذف صف التكرار (تحذير الملّاحين الباكستاني) بعد دمجه
    dup = find_row(t2, "تحذير الملّاحين الباكستاني")
    if dup is not None:
        dup._tr.getparent().remove(dup._tr)

    # جدول 3 — السفن في سياق الحادث
    t3_fixes = [
        ("«GFS GISELLE»", 2, "تضرر البدن، ثم أبحرت إلى مرسى آمن."),
        ("«ALFONSO»", 2, "الحالة غير واضحة، وهي مُدرجة في القائمة الإيرانية."),
        ("«GOL»", 1, "ناقلة نفط اعترضها الحرس الثوري عند المدخل وأمرها بالعودة"),
        ("«GOL»", 2, "غيّرت مسارها وألغت العبور ولم تُصب."),
        ("«CAPE DAO»", 0, "«CAPE DAO» (IMO 9219020)"),
        ("«CAPE DAO»", 1,
         "سفينة بضائع جافة (Bulk carrier)، علم أنتيغوا وبربودا. أُصيبت في 23 سبتمبر على 15 ميلًا بحريًا "
         "شمال شرق خصب، ثم غرقت في 13 أكتوبر بعد فشل الإنقاذ"),
        ("«CAPE DAO»", 2, "غرقت، ومقتل بحّار هندي واحد. إدارة إماراتية."),
        ("«GFS GALAXY»", 1, "سفينة حاويات في الأسطول نفسه، أُصيبت في 11 يوليو"),
        ("«GFS GALAXY»", 2, "أضرار في غرفة المحركات وحريق، وفقدان بحّار واحد."),
        ("«AL SAADIYAT»", 1, "سفينة حاويات في الأسطول نفسه، أُصيبت أثناء عبور مغادر"),
        ("«AL SAADIYAT»", 2, "لا خسائر ولا أضرار جسيمة."),
    ]
    for needle, col, val in t3_fixes:
        c = cell_by(t3, needle, col)
        if c is not None:
            set_cell(c, val)

    # ===== 3) إزالة التظليل الأصفر وعلامات المراجعة =====
    parts = [d]
    for s in d.sections:
        parts += [s.header, s.footer]
    for part in parts:
        for par in part.paragraphs:
            for r in par.runs:
                if r.font.highlight_color is not None:
                    r.font.highlight_color = None
        for t in part.tables:
            for row in t.rows:
                for c in row.cells:
                    for par in c.paragraphs:
                        for r in par.runs:
                            if r.font.highlight_color is not None:
                                r.font.highlight_color = None

    # ===== 4) حذف الفقرة الفارغة المنسّقة بالأحمر =====
    for par in list(d.paragraphs):
        if par.text.strip():
            continue
        bad = False
        for r in par.runs:
            col = r.font.color
            if r.font.underline or (col is not None and col.rgb is not None and str(col.rgb) == "EE0000"):
                bad = True
        if bad:
            par._p.getparent().remove(par._p)

    d.save(OUT)

    print("✔ حُفظت النسخة المصححة:", OUT)
    print("  فقرات معدّلة بالبحث المفتاحي:", len(done), "من", len(body))
    missing = [k for k, _ in body if k not in done]
    if missing:
        print("  ⚠ لم يُطابق:", missing)
    print("  صفوف الجداول:", [len(t.rows) for t in d.tables])
    return 0


if __name__ == "__main__":
    sys.exit(main())