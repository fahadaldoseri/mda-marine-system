#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات عقد شريط نسب القطاعات: موجب وفشل مكوّن وفشل مغلق."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validators.check_zone_strip import validate_zone_strip  # noqa: E402


SOURCE = {
    "date": "2026-10-31",
    "zones": [
        {
            "id": "Z1",
            "confirmed": 1,
            "probable": 1,
            "qualifying_codes": ["a", "b", "c", "d"],
            "excluded": 8,
            "events": 12,
        },
        {
            "id": "Z2",
            "confirmed": 0,
            "probable": 0,
            "qualifying_codes": [],
            "excluded": 1,
            "events": 1,
        },
    ],
}


def strip_html(source: dict = SOURCE) -> str:
    rows = []
    for zone in source["zones"]:
        unconfirmed = len(zone.get("qualifying_codes") or []) - zone["confirmed"] - zone["probable"]
        rows.append(
            "<li>"
            f"<span class=\"zs-id\">{zone['id']}</span>"
            "<span class=\"zs-c\">"
            f"<span class=\"zs-p\"><span class=\"zs-lab\">مؤكدة</span> <bdi>{zone['confirmed']}</bdi></span> · "
            f"<span class=\"zs-p\"><span class=\"zs-lab\">مرجّحة</span> <bdi>{zone['probable']}</bdi></span> · "
            f"<span class=\"zs-p\"><span class=\"zs-lab\">مؤهلة غير مؤكدة</span> <bdi>{unconfirmed}</bdi></span> · "
            f"<span class=\"zs-p\"><span class=\"zs-lab\">مستثناة</span> <bdi>{zone['excluded']}</bdi></span> · "
            f"<span class=\"zs-p\"><span class=\"zs-lab\">إجمالي</span> <bdi>{zone['events']}</bdi></span>"
            "</span></li>"
        )
    return f'<div class="hmap-zstrip"><h4>نسب التهديد</h4><ul>{"".join(rows)}</ul></div>'


class ZoneStripGateTests(unittest.TestCase):
    def test_positive_strip_matches_source(self):
        self.assertEqual(validate_zone_strip(strip_html(), SOURCE), [])

    def test_negative_metric_drift_fails_closed(self):
        bad = strip_html().replace("إجمالي</span> <bdi>12", "إجمالي</span> <bdi>11", 1)
        errors = validate_zone_strip(bad, SOURCE)
        self.assertTrue(any("Z1" in error and "إجمالي" in error for error in errors), errors)

    def test_negative_source_sum_drift_fails_closed(self):
        source = copy.deepcopy(SOURCE)
        source["zones"][0]["events"] = 13
        errors = validate_zone_strip(strip_html(), source)
        self.assertTrue(any("مجموع" in error and "Z1" in error for error in errors), errors)

    def test_missing_strip_fails_closed(self):
        errors = validate_zone_strip("<html><body></body></html>", SOURCE)
        self.assertTrue(any("الشريط" in error or "غير قابل" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
