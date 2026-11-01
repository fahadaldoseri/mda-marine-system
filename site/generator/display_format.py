#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تنسيق حقول البيانات الخام إلى نصوص عرض مفهومة دون تغيير المصدر."""
from __future__ import annotations

import re
from datetime import datetime, timezone

AR_MONTHS = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}
EN_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}


def _parse_utc(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_update_label(value: str, *, language: str = "ar") -> str:
    """يُبقي القيمة الخام كما هي عند تعذّر تحليلها، وإلا يعرضها بتوقيت UTC."""
    dt = _parse_utc(value)
    if dt is None:
        return str(value or "")
    if language == "en":
        return f"{dt.day} {EN_MONTHS[dt.month]} {dt.year} · {dt:%H:%M} UTC"
    return f"{dt.day} {AR_MONTHS[dt.month]} {dt.year} · {dt:%H:%M} حسب التوقيت العالمي"


def format_release_version(value: str) -> str:
    """يُسقط بادئة يوم الأسبوع القديمة من رقم الإصدار المعروض فقط."""
    return re.sub(r"^\s*و\s*ب\s*", "", str(value or "")).strip()
