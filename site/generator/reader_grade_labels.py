#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""وسم رموز درجات الإسناد في سطح القارئ — مصدر واحد للعربية والإنجليزية.

العلّة الجذرية (ك-599): خريطة الدرجات الحاكمة تحمل وسمًا عربيًا ووسمًا إنجليزيًا،
لكن الحجب كان مطبَّقًا في المسار العربي وحده، فتسرّب رمز داخلي (مثل «C/3») إلى
الصفحة الإنجليزية. القاعدة الآن: كل سطح قارئ يمرّ على هذه الوحدة، والوسم يُختار
باللغة، فلا يُحقن نص عربي في سطح إنجليزي ولا يظهر رمز داخلي في أي سطح.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from brain_root import under_brain

MAP_RELATIVE = ("appendices", "confidence-grade-map.json")
LANGS = ("ar", "en")
_FIELD = {"ar": "arabic", "en": "english"}


@lru_cache(maxsize=1)
def _labels() -> dict[str, dict[str, str]]:
    """يقرأ الخريطة الحاكمة مرة واحدة، ويفشل مغلقًا إذا غاب حقل لغة."""
    raw = json.loads(under_brain(*MAP_RELATIVE).read_text(encoding="utf-8"))
    grades = raw.get("grades") or {}
    if not grades:
        raise RuntimeError("خريطة درجات الإسناد الحاكمة فارغة")
    out: dict[str, dict[str, str]] = {}
    for code, entry in grades.items():
        missing = [f for f in _FIELD.values() if not entry.get(f)]
        if missing:
            raise RuntimeError(f"رمز {code} بلا وسم لغة: {missing}")
        out[code] = {lang: entry[_FIELD[lang]] for lang in LANGS}
    return out


@lru_cache(maxsize=1)
def _pattern() -> re.Pattern[str]:
    codes = sorted(_labels(), key=len, reverse=True)
    return re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(re.escape(c) for c in codes) + r")(?![A-Za-z0-9_])")


def redact(text: str, lang: str = "ar") -> str:
    """يحوّل رموز الدرجات الداخلية إلى وسم القارئ بلغة السطح المعطاة."""
    if lang not in _FIELD:
        raise ValueError(f"لغة غير مدعومة: {lang}")
    labels = _labels()
    return _pattern().sub(lambda m: labels[m.group(0)][lang], text)


def exposed_codes(text: str) -> list[str]:
    """يرجع الرموز الداخلية الظاهرة في نص — يستخدمه الفحص والاختبارات."""
    return sorted(set(_pattern().findall(text)))
