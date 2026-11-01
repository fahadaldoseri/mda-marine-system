#!/usr/bin/env python3
"""تعريف واحد لعبارات وحدات إسناد المصدر.

القائمة هنا هي العقد الحرفي بين مولّد سطر الوقائع وحاجز أمانة المحتوى.
أي إضافة أو تغيير يجب أن يمر عبر اختبار وحدات الإسناد قبل استعماله.
"""

from __future__ import annotations

import re

SINGLE_UNITS = ("واقعة واحدة", "بلاغ واحد", "حادثة واحدة", "واقعة منفردة")
DOUBLE_UNITS = ("واقعتان", "بلاغان", "حادثتان")
MANY_UNITS = ("{n} وقائع", "{n} بلاغات", "{n} حوادث")


def count_phrase(count: int, index: int) -> str:
    """أعد العبارة الحرفية التي يستخدمها المولّد للعدد والفهرس."""
    if count == 1:
        return SINGLE_UNITS[index % len(SINGLE_UNITS)]
    if count == 2:
        return DOUBLE_UNITS[index % len(DOUBLE_UNITS)]
    return MANY_UNITS[index % len(MANY_UNITS)].format(n=count)


def _whole_phrase(pattern: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){pattern}(?!\w)")


def count_written_attributions(text: str) -> int:
    """احسب الإسنادات المكتوبة باستخدام وحدات المولّد فقط."""
    total = 0
    for phrase in SINGLE_UNITS:
        total += len(_whole_phrase(re.escape(phrase)).findall(text))
    for phrase in DOUBLE_UNITS:
        total += 2 * len(_whole_phrase(re.escape(phrase)).findall(text))
    for template in MANY_UNITS:
        suffix = template.split(" ", 1)[1]
        for match in _whole_phrase(rf"(\d+)\s+{re.escape(suffix)}").finditer(text):
            total += int(match.group(1))
    return total
