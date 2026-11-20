#!/usr/bin/env python3
"""الفجوات الثلاث المنقولة من الطلبات القديمة (فرز 20 نوفمبر 2026، اعتماد فهد).

1. seawatch-web #9: أقواس MOBILE_NAV_CSS متوازنة ولا يُغلق الاستعلام قبل آخر قواعده.
2. seawatch-web #10 (ك-إ1، ك-إ2): المعجم يرفض المفتاح المكرر والقيمة غير النصية أو الفارغة.
   (ك-إ4): لا سمة مقروءة عربية في الصفحة الإنجليزية، ووسوم المشاركة تُشتق من رأسها الإنجليزي.
   (ك-إ3): لا مطابقة جزئية — لا تُكمَّل وحدة قصيرة بمقابل مفتاح أطول، ولا تُقتطع جملة إلى مقابل أولها.
3. seawatch-brain #6: اسم سفينة ذو مقطع واحد في دفتر اليوم («ST3») يدخل قائمة فحص العقوبات.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
SITE = Path(os.environ.get("SITE_DIR") or B.parent / "site")
sys.path.insert(0, str(SITE / "generator"))
sys.path.append(str(B / "tools"))
FAILS = []


def expect(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAILS.append(msg)


def css_ok(css: str) -> bool:
    depth = 0
    for ch in re.sub(r"/\*.*?\*/", "", css, flags=re.S):
        depth += (ch == "{") - (ch == "}")
        if depth < 0:
            return False
    return depth == 0


def main() -> int:
    import site_chrome
    expect(css_ok(site_chrome.MOBILE_NAV_CSS), "أقواس MOBILE_NAV_CSS متوازنة بلا إغلاق مبكر")
    expect(not css_ok(".a{x:1}\n}\n.b{y:2}\n}"), "سالب: القوس الزائد يُكشف")

    import i18n_en
    old = i18n_en.I18N
    try:
        with tempfile.TemporaryDirectory() as d:
            i18n_en.I18N = Path(d)
            g = Path(d) / "glossary.json"
            g.write_text('{"entries": {"أ": "A", "ب": "B"}}', encoding="utf-8")
            expect(i18n_en.load_glossary() is not None, "موجب: معجم سليم يُحمَّل")
            for bad, why in (('{"entries": {"أ": "A", "أ": "B"}}', "مفتاح مكرر"),
                             ('{"entries": {"أ": {"en": "A"}}}', "قيمة كائنية"),
                             ('{"entries": {"أ": "  "}}', "قيمة فارغة")):
                g.write_text(bad, encoding="utf-8")
                try:
                    i18n_en.load_glossary()
                    expect(False, f"سالب: {why} يُرفض")
                except ValueError:
                    expect(True, f"سالب: {why} يُرفض")
    finally:
        i18n_en.I18N = old
    i18n_en.load_glossary()
    expect(True, "المعجم الحقيقي يجتاز الحاجزين")

    page = ('<html><head><title>Daily Report — 2030-01-01</title>'
            '<meta name="description" content="English description">'
            '<meta property="og:site_name" content="مركز الوعي بالمجال البحري">'
            '<meta property="og:locale" content="ar_BH">'
            '<meta property="og:title" content="التقرير اليومي">'
            '<meta name="twitter:description" content="وصف عربي"></head>'
            '<body><span data-classification="بلاغ رسمي">Official report</span></body></html>')
    expect(len(i18n_en.arabic_reader_attributes(page)) == 3, "سالب ك-إ4: وسوم المشاركة العربية تُكشف")
    fixed = i18n_en.localize_social_meta(page)
    expect(i18n_en.arabic_reader_attributes(fixed) == [], "وسوم المشاركة تُشتق من الرأس الإنجليزي")
    expect('content="Daily Report — 2030-01-01"' in fixed and 'content="en_US"' in fixed,
           "العنوان من <title> واللغة en_US")
    expect('data-classification="بلاغ رسمي"' in fixed, "مفتاح data-* التعاقدي يبقى كما هو")
    expect(i18n_en.arabic_reader_attributes('<b aria-label="زر">x</b>') == ["زر"], "سالب: aria-label عربية تُكشف")
    built = sorted((SITE / "dist" / "reports" / "en").glob("*.html"))
    if built:
        bad = [p.name for p in built if i18n_en.arabic_reader_attributes(p.read_text(encoding="utf-8"))]
        expect(not bad, f"الصفحات الإنجليزية المبنية بلا سمة مقروءة عربية ({len(built)} صفحة)")
    else:
        print("  • تخطٍّ معلن: لا صفحات إنجليزية مبنية")

    gl_small = {"أساس التقدير:": "Basis of assessment:", "مضيق هرمز": "the Strait of Hormuz"}
    tr = i18n_en.make_translator({}, gl_small)
    arabic = lambda v: bool(re.search(r"[\u0600-\u06FF]", v or ""))
    expect(tr("مضيق هرمز") == "the Strait of Hormuz", "موجب ك-إ3: المفتاح التام يُترجم")
    expect(arabic(tr("أساس التقدير: أثبتت الجهة نشاطًا مشبوهًا فقط.")),
           "سالب ك-إ3: جملة تبدأ بمفتاح لا تُقتطع إلى «Basis of assessment:» فتبقى ناقصة معلنة")
    expect(arabic(tr("مضيق")), "سالب ك-إ3: وحدة قصيرة لا تُكمَّل بمقابل مفتاح أطول")
    expect(i18n_en.localize_patterns("بحر العرب — مستواه منخفض.") == "Arabian Sea — level: Low.",
           "نمط سطر القطاع يحفظ المستوى (كان يُقتطع إلى اسم القطاع)")
    expect(i18n_en.localize_patterns("بحر العرب: منخفض — ذيل حر غير معروف.") is None,
           "سالب: ذيل غير معروف لا يُترجم بالتخمين")
    latest = sorted((SITE / "dist" / "reports" / "en").glob("2026-11-2*.html"))
    card = SITE / "dist" / "reports" / "en" / "2026-11-20.html"
    if card.is_file():
        text = card.read_text(encoding="utf-8")
        expect("Basis of assessment: the overall level is Moderate" in text,
               "جملة «أساس التقدير» في بطاقة الحكم 20 نوفمبر كاملة لا «Basis of assessment:» وحدها")
    else:
        print(f"  • تخطٍّ معلن: صفحة 20 نوفمبر الإنجليزية غير مبنية ({len(latest)} صفحة)")

    import vessel_names
    old_b = vessel_names.B
    try:
        with tempfile.TemporaryDirectory() as d:
            vessel_names.B = Path(d)
            (Path(d) / "cumulative-2026" / "daily").mkdir(parents=True)
            (Path(d) / "cumulative-2026" / "daily" / "2030-01-01.json").write_text(json.dumps(
                [{"code": "MN-2030-01-01-01", "vessel_name": "ST3"}, {"vessel_name": "—"}, {"vessel_name": None}]),
                encoding="utf-8")
            got = vessel_names.from_report("2030-01-01")
            expect("ST3" in got, "اسم ذو مقطع واحد في الدفتر يدخل قائمة الفحص")
            expect("—" not in got and "None" not in got, "الفارغ و«—» لا يدخلان")
            expect(vessel_names.extract("السفينة ST3 تعرضت") == [], "الاستخراج النصي وحده يسقطه (سبب الحاجة)")
    finally:
        vessel_names.B = old_b
    print(f"الحصيلة: فشل {len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
