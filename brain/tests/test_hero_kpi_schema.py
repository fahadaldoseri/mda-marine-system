#!/usr/bin/env python3
"""اختبار عقد بناء hero_kpis: مخطط قديم تاريخي ومخطط صفين حديث."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path("/home/ubuntu/seawatch")
sys.path.insert(0, str(SITE / "generator"))
import build_report  # noqa: E402


OLD = {
    "title": "تقرير قديم",
    "date_label": "30 أكتوبر 2026",
    "threat_level": "مرتفع",
    "hero_kpis": [
        {"label": "قديم 1", "value": "1", "note": "ملاحظة"},
        {"label": "قديم 2", "value": "2", "note": "ملاحظة"},
        {"label": "قديم 3", "value": "3", "note": "ملاحظة"},
        {"label": "قديم 4", "value": "4", "note": "ملاحظة"},
    ],
}

NEW = {
    "title": "تقرير حديث",
    "date_label": "31 أكتوبر 2026",
    "threat_level": "مرتفع",
    "hero_kpis": [
        {"id": f"k{i}", "row": 1 if i < 4 else 2, "title": f"بطاقة {i}", "value": str(i)}
        for i in range(7)
    ],
}


class HeroKpiSchemaTests(unittest.TestCase):
    def _build(self, date: str, meta: dict) -> str:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            md = root / f"{date}-sectioned.md"
            out = root / "out.html"
            md.write_text("# تقرير\n\n## الخلاصة\nنص مختصر.\n", encoding="utf-8")
            build_report.build(md, out, meta)
            return out.read_text(encoding="utf-8")

    def test_historical_schema_is_strict_and_keeps_flat_cards(self):
        self.assertIs(build_report.validate_meta(OLD, report_date="2026-10-30"), OLD)
        html = self._build("2026-10-30", OLD)
        self.assertNotIn('<div class="kpi-row', html)
        self.assertNotIn('<div class="sc-kpi-row', html)
        self.assertEqual(html.count('class="kpi acc-'), 4)
        self.assertEqual(html.count('data-kpi-id='), 0)

    def test_historical_missing_label_fails_closed(self):
        bad = {**OLD, "hero_kpis": [{"value": "1"}]}
        with self.assertRaises(build_report.BuildError):
            build_report.validate_meta(bad, report_date="2026-10-30")

    def test_current_schema_requires_title_and_builds_4_then_3(self):
        self.assertIs(build_report.validate_meta(NEW, report_date="2026-10-31"), NEW)
        html = self._build("2026-10-31", NEW)
        self.assertIn('class="kpi-row kpi-row-1"', html)
        self.assertIn('class="kpi-row kpi-row-2"', html)
        self.assertEqual(html.count('data-kpi-id='), 14)

    def test_current_missing_title_fails_closed(self):
        bad = {**NEW, "hero_kpis": [{"value": "1", "row": 1}]}
        with self.assertRaises(build_report.BuildError):
            build_report.validate_meta(bad, report_date="2026-10-31")


if __name__ == "__main__":
    unittest.main()
