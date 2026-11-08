#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات القرار 9: بطاقات IMO الدائمة وفصل تحديثات الدفتر عن سجل الأحداث."""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# build_report.py جزء من نسخة الموقع المعلنة داخل المستودع، لا من اسم مجلد
# بديل قد يوجد في بيئة نشر أخرى.
SITE_ROOT = ROOT.parent / "site"
# حارس البطاقات يقرأ هذا المتغير عند الاستيراد؛ اربطه بالشجرة نفسها التي يختبرها
# الملف بدل الاعتماد على اسم النشر التاريخي «seawatch».
os.environ["SITE_DIR"] = str(SITE_ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SITE_ROOT / "generator"))

import build_report  # noqa: E402
import validators.check_card_counters as card_checks  # noqa: E402
from tools.ledger_totals import make_imo_attacks  # noqa: E402
from validators.check_daily_event_surface import validate_documents  # noqa: E402


class Owner9ImoCardsTests(unittest.TestCase):
    def test_imo_metric_uses_single_incidents_identifier(self):
        metric = make_imo_attacks(dt.date(2026, 11, 3))
        self.assertEqual(metric["id"], "imo-confirmed-incidents")
        self.assertEqual(metric["today"], 6)
        self.assertEqual(metric["cumulative"], 128)

    def test_imo_permanent_card_guard_exists_and_accepts_current_contract(self):
        guard = getattr(card_checks, "validate_imo_permanent_cards", None)
        self.assertIsNotNone(guard, "حارس البطاقتين الدائمتين غير موجود")
        if guard is None:
            return
        meta = json.loads((ROOT / "web/meta/2026-11-03.json").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "appendices/card_registry.json").read_text(encoding="utf-8"))
        totals = json.loads((ROOT / "web/kpis-totals/2026-11-03.json").read_text(encoding="utf-8"))
        self.assertEqual(guard(meta, registry, totals), [])

    def test_imo_permanent_card_guard_rejects_duplicate_source(self):
        guard = getattr(card_checks, "validate_imo_permanent_cards", None)
        self.assertIsNotNone(guard, "حارس مصدر IMO المكرر غير موجود")
        if guard is None:
            return
        meta = json.loads((ROOT / "web/meta/2026-11-03.json").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "appendices/card_registry.json").read_text(encoding="utf-8"))
        totals = json.loads((ROOT / "web/kpis-totals/2026-11-03.json").read_text(encoding="utf-8"))
        changed = copy.deepcopy(meta)
        changed.setdefault("official_cards", []).append(copy.deepcopy(changed["official_cards"][-1]))
        errors = guard(changed, registry, totals)
        self.assertTrue(any("تكرار" in error and "IMO" in error for error in errors), errors)

    def test_imo_permanent_guard_rejects_duplicate_within_same_surface(self):
        """التكرار داخل سطح التقرير ممنوع، بينما نسخة الشاشة سطح مستقل مسموحة."""
        guard = getattr(card_checks, "validate_imo_permanent_cards", None)
        self.assertIsNotNone(guard, "حارس بطاقات IMO الدائمة غير موجود")
        if guard is None:
            return
        meta = json.loads((ROOT / "web/meta/2026-11-03.json").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "appendices/card_registry.json").read_text(encoding="utf-8"))
        totals = json.loads((ROOT / "web/kpis-totals/2026-11-03.json").read_text(encoding="utf-8"))
        rendered = """<html><body>
          <div class="kpis hero-kpis">
            <div data-kpi-id="imo-confirmed-incidents"></div>
            <div data-kpi-id="imo-confirmed-incidents"></div>
            <div data-kpi-id="imo-seafarer-deaths"></div>
          </div>
          <div class="sc-hero"><div class="sc-kpis hero-kpis">
            <div data-kpi-id="imo-confirmed-incidents"></div>
            <div data-kpi-id="imo-seafarer-deaths"></div>
          </div></div>
        </body></html>"""
        errors = guard(meta, registry, totals, rendered_html=rendered)
        self.assertTrue(
            any("imo-confirmed-incidents" in error and "سطح التقرير/الطباعة" in error and "2" in error
                for error in errors),
            errors,
        )

    def test_event_generator_excludes_cumulative_update_records(self):
        update = {
            "code": "MN-2026-11-03-04",
            "date": "2026-11-03",
            "title": "تحديث IMO التراكمي",
            "source": "IMO",
            "confidence": "عالية",
            "event_kind": "تحديث بيانات",
            "counts_as_new": False,
        }
        incident = {
            "code": "MN-2026-11-03-01",
            "date": "2026-11-03",
            "title": "واقعة بحرية",
            "source": "UKMTO",
            "confidence": "عالية",
            "event_kind": "جديد",
            "counts_as_new": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            rendered = build_report.render_ledger_events([update, incident], {}, Path(tmp) / "2026-11-03-sectioned.md")
        self.assertNotIn("MN-2026-11-03-04", rendered)
        self.assertIn("MN-2026-11-03-01", rendered)
        self.assertRegex(rendered, r'data-count="1"')

    def test_event_surface_guard_counts_only_renderable_records(self):
        update = {
            "code": "MN-2026-11-03-04",
            "date": "2026-11-03",
            "title": "تحديث IMO التراكمي",
            "event_kind": "تحديث بيانات",
            "counts_as_new": False,
        }
        incident = {
            "code": "MN-2026-11-03-01",
            "date": "2026-11-03",
            "title": "واقعة بحرية",
            "event_kind": "جديد",
            "counts_as_new": True,
        }
        report = (
            '<html><body><section><h2>سجل الأحداث</h2>'
            '<div class="ev-grid" data-count="1" data-source-count="1" '
            'data-relation-count="0" data-branch-count="0" data-unresolved-branch-count="0">'
            '<article data-event-code="MN-2026-11-03-01">واقعة</article>'
            '</div></section></body></html>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            errors = validate_documents(
                daily=[update, incident], report=report,
                additions="<html><body></body></html>", site=Path(tmp),
                policy={"required_in_additions": [], "required_in_report": []}
            )
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
