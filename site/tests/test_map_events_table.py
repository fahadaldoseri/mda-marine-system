#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار لك-227 و ك-228 (2026-11-11).

ك-227: جدول «تفاصيل الوقائع» كان يُبنى من نقاط الخريطة وحدها، فتُسقط واقعة مؤهلة
بلا إحداثيات. الاختبار يثبت أن الواقعة غير المكانية تُضاف صفًا كاملًا برمزها الكامل،
ويثبت سلبيًا أن الجدول لا يتضخم ولا يكرّر الصف عند غياب وقائع إضافية.

ك-228: زر «EN» يحمل data-go، فيلزم وجود مستمع نقر له في سكربت الشريط المشترك.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import map_gulf  # noqa: E402
import site_chrome  # noqa: E402

POINT = {"code": "MN-2026-11-11-02", "label": "مضيق هرمز", "area": "مضيق هرمز",
         "lat": 26.5, "lon": 56.5, "kind": "unconfirm", "ref": "UKMTO 202-26",
         "source": "UKMTO", "precision": "approximate"}
NONSPATIAL = {"code": "MN-2026-11-11-01", "date": "2026-11-11", "class": "بلاغ رسمي",
              "title": "هجوم — بلاغ UKMTO 201-26", "confidence": "منخفضة"}


def _rows(html: str) -> int:
    return html.count("<tr>")


def test_nonspatial_event_row_added():
    html = map_gulf.build_map([POINT], "المصدر: جدول التوزيع الجغرافي للوقائع.",
                              None, extra_events=[NONSPATIAL])
    assert "MN-2026-11-11-01" in html, "الواقعة غير المكانية لم تُضف إلى جدول التفاصيل"
    assert "غير محددة في المواد الحالية" in html, "لا وسم لغياب الموقع"
    assert html.count("MN-2026-11-11-01") == 1, "الصف مضاف أكثر من مرة"


def test_negative_no_extra_events():
    with_extra = _rows(map_gulf.build_map([POINT], "المصدر: جدول التوزيع الجغرافي للوقائع.",
                                          None, extra_events=[NONSPATIAL]))
    without = _rows(map_gulf.build_map([POINT], "المصدر: جدول التوزيع الجغرافي للوقائع."))
    assert with_extra == without + 1, f"عدد الصفوف غير متوقع: {with_extra} مقابل {without}"


def test_negative_duplicate_code_not_repeated():
    """واقعة لها نقطة على الخريطة لا تُكرّر صفًا في الجدول."""
    base = _rows(map_gulf.build_map([POINT], "المصدر: جدول التوزيع الجغرافي للوقائع."))
    dup = _rows(map_gulf.build_map([POINT], "المصدر: جدول التوزيع الجغرافي للوقائع.", None,
                                   extra_events=[dict(NONSPATIAL, code="MN-2026-11-11-02")]))
    assert dup == base, f"تكرار الصف: {dup} مقابل {base}"


def test_lang_button_has_click_handler():
    js = site_chrome.PREFS_LATE
    assert "[data-go]" in js, "لا مستمع نقر لزر اللغة"
    assert "location.href" in js, "المستمع لا ينقل إلى النسخة الإنجليزية"


if __name__ == "__main__":
    for fn in (test_nonspatial_event_row_added, test_negative_no_extra_events,
               test_negative_duplicate_code_not_repeated, test_lang_button_has_click_handler):
        fn()
        print(f"   ✔ {fn.__name__}")
    print("   النتيجة: نجحت كل الحالات")
