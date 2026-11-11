#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار لإصلاحات ك-597 في مترجم النسخة الإنجليزية.

الحالات السالبة (كانت تُنتج نصًا عربيًا داخل الصفحة الإنجليزية):
  1. مفتاح معجم قصير («ع» = «AR») اختطف كل وحدة تبدأ بحرف العين.
  2. معجم الواجهة الحاكم لم يُقرأ أصلًا (المحلّل يبحث عن "en" بينما الملف يكتب en:{).
  3. معجم الواجهة كان يُبنى بالاتجاه المعاكس (معرّف الوسم ← العربية) بدل عربي ← إنجليزي.
  4. مقدمة الخريطة أسقطت الرقم الثاني فمنعها حارس حفظ الأرقام.
  5. ترويسة الإصدار بصيغة يوم/شهر/سنة لم يكن لها نمط.

الحالات الموجبة: الوحدات الخمس تُترجم والإنجليزية خالية من أي حرف عربي، وكل الأرقام
محفوظة، وترويسة الإصدار تُبنى بالتاريخ الصحيح.
"""
from __future__ import annotations

import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'generator'))
import i18n_en as I  # noqa: E402

ARABIC = re.compile(r"[\u0600-\u06FF]")


def _out(unit: str) -> str:
    value = I.localize_patterns(I.norm(unit))
    assert value, f"الوحدة بلا ترجمة: {unit[:60]}"
    assert not ARABIC.search(value), f"نص عربي متبقٍّ في الترجمة: {value}"
    return value


def test_short_glossary_key_never_matches_partially():
    # «ع» = «AR» موجود للمطابقة التامة (زر اللغة) ولا يجوز أن يطابق جزئيًا
    assert I._partial_key_safe("عناوين مهربية", "ع") is False
    assert I._partial_key_safe("عدد البنود: 4 · وتفصيلها", "ع") is False
    assert I._partial_key_safe("التقرير اليومي للأمن البحري", "التقرير اليومي") is True


def test_chrome_glossary_is_parsed_and_directed_arabic_to_english():
    chrome = I.chrome_glossary()
    assert len(chrome) >= 10, "معجم الواجهة لم يُقرأ"
    assert chrome.get("علامات الإنذار المبكر") == "Early warning signs"
    assert not any(ARABIC.search(v) for v in chrome.values()), "قيمة عربية داخل معجم الواجهة"


def test_generated_phrases_are_governed_pairs():
    gl = I.load_glossary()
    for ar in ("أدرجت",
               "أهم الأخبار — في صفحة",
               "عنوانان: نشاط مشبوه وهجوم",
               "عن واقعة تشمل سفينة بضائع سائبة وقوات عسكرية",
               "عن واقعة متأخرة الإبلاغ مصنفة هجومًا في مضيق هرمز",
               "عناوين إعلامية عن ناقلة أو ناقلات احترقت أو أصيبت بألغام في مضيق هرمز",
               "عنوانًا عن واقعة مصنفة هجومًا في مضيق هرمز؛ لا اسم سفينة أو نتيجة."):
        value = gl.get(I.norm(ar))
        assert value and not ARABIC.search(value), f"عبارة مولَّدة بلا زوج حاكم: {ar[:40]}"


def test_report_title_with_day_month_year():
    out = _out("التقرير اليومي للأمن البحري والأوضاع الراهنة في المنطقة — 09/11/2026")
    assert out == "Daily Maritime Security Report — 2026-11-09 (English edition)"


def test_incident_row_uses_governed_vocabulary():
    out = _out("الواقعة 09-06 — المنطقة خليج عُمان، الصفة نقل مهني، الإثبات مرجّح، الموقع تقريبي.")
    assert out.startswith("Incident 09-06 — area Gulf of Oman")
    assert "trade report" in out and "probable" in out and "approximate" in out
    # المنطقة المركّبة: تُترجم أجزاؤها ولا يبقى حرف عربي
    comp = _out("الواقعة 07-02 — المنطقة مضيق هرمز · خليج عُمان، الصفة بلاغ غير مؤكد، "
                "الإثبات غير مؤكد، الموقع تقريبي.")
    assert "Strait of Hormuz · Gulf of Oman" in comp and "unconfirmed report" in comp


def test_map_lede_keeps_both_numbers():
    unit = ("مواقع 6 واقعة داخل نطاق التقرير؛ منها 6 بموقع تقريبي داخل المنطقة نفسها لأن المصدر "
            "لم يذكر إحداثيات.")
    out = _out(unit)
    assert "Positions of 6 incidents" in out and "6 of them" in out


def test_ukmto_fragments_keep_distance_and_bearing():
    a = _out("عن نشاط مشبوه على بعد 8 أميال بحرية شمال غرب خصب")
    assert a == "about suspicious activity 8 nautical miles northwest of Khasab"
    b = _out("عن واقعة هجوم متأخرة الإبلاغ على بعد 16 ميلًا بحريًا شرق خصب")
    assert b == "about a late-reported attack incident 16 nautical miles east of Khasab"
    c = _out("عنوانًا عن نشاط مشبوه على بعد 8 أميال بحرية شمال غرب خصب؛ التفاصيل التشغيلية غير ظاهرة.")
    assert c.endswith("; operational details are not visible.")


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"   ✔ {name}")
            except AssertionError as exc:
                fails += 1
                print(f"   ✘ {name}: {exc}")
    print(f"   النتيجة: {'كل الحالات ناجحة' if fails == 0 else f'فشل {fails}'}")
    sys.exit(1 if fails else 0)
