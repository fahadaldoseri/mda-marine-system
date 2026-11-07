#!/usr/bin/env python3
"""تصريف العدادات العربية من مواصفة واحدة في سجل البطاقة."""
from __future__ import annotations

from collections.abc import Mapping


def _bucket(value: int) -> str:
    """Return the Arabic cardinal bucket for a non-negative integer."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"قيمة عداد عربية غير صالحة: {value!r}")
    if value == 0:
        return "zero"
    remainder = value % 100
    if remainder == 1:
        return "one"
    if remainder == 2:
        return "two"
    if 3 <= remainder <= 10:
        return "few"
    return "many"


def format_arabic_count(value: int, number_format: Mapping[str, str]) -> str:
    """Format ``value`` with the noun form declared by the card contract."""
    if not isinstance(number_format, Mapping):
        raise ValueError("مواصفة تصريف العدد العربية مفقودة أو غير صالحة")
    bucket = _bucket(value)
    form_key = str(number_format.get(bucket) or "")
    noun = str(number_format.get(form_key) or "").strip()
    if not noun:
        raise ValueError(f"مواصفة تصريف العدد العربية ناقصة للمجموعة: {bucket}")
    return f"{value} {noun}"
