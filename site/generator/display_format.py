#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تنسيق حقول البيانات الخام إلى نصوص عرض مفهومة دون تغيير المصدر."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

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
    # توقيت البحرين (UTC+3 ثابت، بلا توقيت صيفي) بجانب العالمي: القارئ في البحرين لا يحسب الفرق بنفسه
    bh = (dt + timedelta(hours=3)).strftime("%H:%M")
    if language == "en":
        return f"{dt.day} {EN_MONTHS[dt.month]} {dt.year} · {dt:%H:%M} UTC ({bh} Bahrain time)"
    return f"{dt.day} {AR_MONTHS[dt.month]} {dt.year} · {dt:%H:%M} حسب التوقيت العالمي ({bh} بتوقيت البحرين)"


_YY = {"25", "26", "27"}


def format_release_version(value: str) -> str:
    """يُسقط بادئة «و ب» من رقم الإصدار المعروض، ويوحّد ترتيبه يوم/شهر/سنة.

    إصدارات أكتوبر الأولى كُتبت سنة/شهر/يوم («26/10/17») وما بعدها يوم/شهر/سنة
    («20/11/26»)، فيلتبس الترتيب على القارئ. التوحيد للعرض فقط؛ القيمة الخام لا تتغير.
    """
    text = re.sub(r"^\s*و\s*ب\s*", "", str(value or "")).strip()
    m = re.match(r"^(\d{2})/(\d{1,2})/(\d{1,2})(.*)$", text)
    if m and m.group(3) not in _YY and m.group(1) in _YY:
        text = f"{int(m.group(3)):02d}/{int(m.group(2)):02d}/{m.group(1)}{m.group(4)}"
    return text
