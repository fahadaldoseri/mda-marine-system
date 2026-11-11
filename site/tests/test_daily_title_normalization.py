"""اختبار انحدار: تطبيع عنوان الإصدار اليومي (ك-595).

الحالة الموجبة: عنوان يومي بتاريخ عربي ملحق يُطبَّع إلى الاسم المعتمد.
الحالة السالبة: عنوان مخصّص حقيقي لا يُطبَّع.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "generator"))

from daily_title import DAILY_TITLE, is_daily_placeholder, normalize_daily_title  # noqa: E402

DATED = "التقرير اليومي لأمن الملاحة والأوضاع الراهنة في المنطقة — 29 أكتوبر 2026"
PLAIN = "التقرير اليومي لأمن الملاحة والأوضاع الراهنة في المنطقة"
CUSTOM = "تقرير خاص بسلامة الملاحة في خليج عدن"


def test_dated_daily_title_is_normalized() -> None:
    assert is_daily_placeholder(DATED) is True
    assert normalize_daily_title(DATED) == DAILY_TITLE


def test_plain_daily_title_is_normalized() -> None:
    assert normalize_daily_title(PLAIN) == DAILY_TITLE
    assert normalize_daily_title("التقرير الصباحي اليومي") == DAILY_TITLE


def test_custom_title_is_preserved() -> None:
    assert is_daily_placeholder(CUSTOM) is False
    assert normalize_daily_title(CUSTOM) == CUSTOM


def test_empty_falls_back_to_daily_title() -> None:
    assert normalize_daily_title("") == DAILY_TITLE
    assert normalize_daily_title(None) == DAILY_TITLE


if __name__ == "__main__":
    test_dated_daily_title_is_normalized()
    test_plain_daily_title_is_normalized()
    test_custom_title_is_preserved()
    test_empty_falls_back_to_daily_title()
    print("   ✔ اختبار تطبيع عنوان الإصدار: 4 حالات ناجحة")