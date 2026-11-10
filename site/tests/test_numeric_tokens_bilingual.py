#!/usr/bin/env python3
"""اختبار انحدار لعطل ك-601 — مطابقة الأعداد بقيمتها لا بشكلها.

الخلفية: بناء النسخة الإنجليزية كان يفشل مغلقًا على نص مترجم سليم لأن
`_numeric_tokens()` لم تكن تقرأ كلمات الأعداد الإنجليزية، فتُعدّ «ثلاثة تحذيرات»
⇒ "Three warnings" فقدًا للرقم 3.

القاعدة المُثبَّتة هنا: عدد الأصل يُطابَق بقيمته في المخرج، سواء كُتب رقمًا أو كلمةً
بالعربية أو بالإنجليزية، وأي عدد مفقود فعليًا يبقى مرفوضًا (فشل مغلق).

رمز الخروج: 0 نجاح · 1 فشل.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
import i18n_en as I  # noqa: E402


def preserves(source: str, target: str) -> bool:
    od = I._numeric_tokens(source)
    td = I._numeric_tokens(target)
    # نفس شرط `_unit_ok`: لا يُشترط وجود عدد، ويُشترط عدم فقدان أي عدد موجود.
    return all(t in td for t in od)


# (الوحدة العربية · المخرج الإنجليزي · هل يجب أن يُقبل)
CASES: list[tuple[str, str, bool]] = [
    ("ثلاثة تحذيرات", "Three warnings", True),
    ("تحذيران جديدان", "Two new warnings", True),
    ("ثلاثون سفينة", "Thirty vessels", True),
    ("إحدى وعشرون واقعة", "Twenty-one incidents", True),
    ("سبع وأربعون رحلة", "Forty-seven voyages", True),
    ("مئة مصدر", "One hundred sources", True),
    ("اثنتي عشرة ساعة", "Twelve hours", True),
    ("واقعة مؤهّلة واحدة", "One qualifying incident", True),
    ("خمسة بنود", "Five items", True),
    ("المجموع 125 حادثة و24 وفاة", "The total is 125 incidents and 24 fatalities", True),
    ("تحديث للتحذير 190-26", "An update to warning 190-26", True),
    ("مرتفع جدًا (02-01 إلى 02-05)", "Very high (02-01 to 02-05)", True),
    # سلبي: عدد مفقود فعليًا ⇒ يجب أن يبقى مرفوضًا
    ("ثلاثة تحذيرات", "Warnings were issued", False),
    ("ثلاثون سفينة", "Vessels were listed", False),
    ("إحدى وعشرون واقعة", "Incidents were listed", False),
    ("تحديث للتحذير 190-26", "An update to a warning", False),
    ("المجموع 125 حادثة و24 وفاة", "The total is 125 incidents", False),
]


def main() -> int:
    failed = 0
    for source, target, expected in CASES:
        got = preserves(source, target)
        if got != expected:
            failed += 1
            print(f"✘ متوقع={expected} مقيس={got} · «{source}» ⇒ «{target}»")
    total = len(CASES)
    if failed:
        print(f"✘ فشل {failed} من {total} حالة")
        return 1
    print(f"✔ مطابقة الأعداد بين اللغتين سليمة · {total} حالة (موجب وسالب)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
