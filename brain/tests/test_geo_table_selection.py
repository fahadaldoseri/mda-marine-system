#!/usr/bin/env python3
"""اختبار B010: لا يُعامل جدول مستوى التهديد كجدول توزيع جغرافي.

الحالة الموجبة: جدول «القطاع + عدد الوقائع + النسبة» ينتج خمس صفوف رقمية.
الحالة السالبة: جدول «القطاع + المستوى» يمر كجدول محتوى عادي بلا خطأ الخريطة.
"""
from __future__ import annotations

import sys
from pathlib import Path

SITE = Path(__import__("os").environ.get("SITE_DIR", "/home/ubuntu/seawatch")).resolve()
sys.path.insert(0, str(SITE / "generator"))

from build_report import render_section_body  # noqa: E402


GEO_LINES = [
    "| القطاع | عدد الوقائع | النسبة | المصدر/الأساس |",
    "|---|---:|---:|---|",
    "| Z1 | 12 | 75% | أساس |",
    "| Z2 | 1 | 6.25% | أساس |",
    "| Z3 | 1 | 6.25% | أساس |",
    "| Z4 | 1 | 6.25% | أساس |",
    "| غير مكانية | 1 | 6.25% | أساس |",
    "| المجموع | 16 | 100% | أساس |",
]

THREAT_LINES = [
    "| القطاع | المستوى | بطاقة القرار | أساس الحكم |",
    "|---|---|---|---|",
    "| Z1 | مرتفع | مرتفع | أساس |",
    "| Z2 | مرتفع استمراري | مرتفع | أساس |",
    "| Z3 | متوسط | متوسط | أساس |",
    "| Z4 | متوسط | متوسط | أساس |",
]


def main() -> int:
    geo = render_section_body("التوزيع الجغرافي للوقائع", GEO_LINES, {})
    bars = geo.count('class="bar-row"')
    assert bars == 5, f"المتوقع numeric_rows=5، الواقع bar_rows={bars}"
    assert 'class="viz reveal"' in geo
    print("POSITIVE: geo_selected=True numeric_rows=5")

    threat = render_section_body("مستوى التهديد", THREAT_LINES, {})
    assert 'class="viz reveal"' not in threat
    assert 'class="dg-grid"' in threat
    print("NEGATIVE: threat_selected=False geo_error=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
