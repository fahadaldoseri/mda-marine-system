#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار البوابة: المصدر الساقط يجب أن يمنع، والحالة الكاملة تمر."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "validators"))
from check_source_daily_coverage import validate  # noqa: E402


def valid_result() -> dict:
    return {
        "approved_source_count": 62,
        "checked_union_manual_count": 62,
        "checked_missing_sources": [],
        "checked_unknown_sources": [],
        "manual_reference": [39, 52],
        "status_manual_reference": [39, 52],
        "manual_reference_reasons": {"39": "سبب مقيس", "52": "سبب مقيس"},
        "checked_declared": 60,
        "checked_unique_count": 60,
        "sources": [
            {"num": number, "route_state": "مرجعية يدوية" if number in (39, 52) else "مسار آلي",
             "manual": number in (39, 52)}
            for number in range(1, 63)
        ],
    }


def main() -> int:
    good = valid_result()
    assert validate(good) == [], validate(good)
    bad = copy.deepcopy(good)
    bad["checked_union_manual_count"] = 61
    bad["checked_missing_sources"] = [52]
    bad["status_manual_reference"] = []
    problems = validate(bad)
    assert problems, "البوابة لم تمنع مصدرًا ساقطًا مصطنعًا"
    print("موجب: 0 مشكلة")
    print("سالب: منع 2 منطقيًا؛ " + " · ".join(problems))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
