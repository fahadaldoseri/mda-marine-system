#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""عقد تأجيل أسطح التقرير: إعلان حاكم + إنفاذ لاحق حقيقي.

الحالات الإلزامية:
  1) موجب: صفحة مؤجلة بإعلان صحيح وG045 إنفاذ لاحق تمر كمؤجل معلن.
  2) سالب: سطح غائب بلا إعلان يبقى غير مغطى ومانعًا.
  3) سالب: إعلان بلا خطوة إنفاذ لاحقة يبقى غير مغطى ومانعًا.
  4) سالب: سطح موجود لكن فحصه غير مغطى يبقى مانعًا.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "audit_style_coverage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_style_coverage", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"تعذّر تحميل بوابة التغطية: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SurfaceDeferralContractTests(unittest.TestCase):
    def manifest(self, declaration=None, enforcer_command=None):
        g001 = {"id": "G001", "phase": "gates"}
        if declaration is not None:
            g001["deferred_surfaces"] = [declaration]
        g045 = {
            "id": "G045",
            "phase": "build",
            "command": enforcer_command or ["python3 tools/audit_style_coverage.py"],
        }
        return {"steps": [g001, {"id": "B010", "phase": "build"}, g045]}

    def valid_page_declaration(self):
        return {
            "label": "صفحة التقرير",
            "producer": "B010",
            "enforced_by": "G045",
            "enforcement_contract": "surface-coverage",
            "reason": "B010 يبني الصفحة بعد G001، وG045 يعيد فحص تغطية الأسطح بعد البناء.",
            "effective_from": "2026-11-07",
        }

    def test_positive_deferred_surface_with_real_later_enforcement_is_not_blocking(self):
        module = load_module()
        deferred = module.deferred_producer_ids(
            self.manifest(self.valid_page_declaration()), "G001"
        )
        self.assertIn("B010", deferred)
        result = module.classify_missing_surface(
            {"label": "صفحة التقرير", "producer": "B010"},
            deferred,
            {},
            "المصدر غير موجود",
        )
        self.assertEqual(result["status"], "مؤجل معلن")
        self.assertFalse(result["blocked"])

    def test_negative_missing_surface_without_declaration_blocks(self):
        module = load_module()
        deferred = module.deferred_producer_ids(self.manifest(), "G001")
        result = module.classify_missing_surface(
            {"label": "صفحة التقرير", "producer": "B010"},
            deferred,
            {},
            "المصدر غير موجود",
        )
        self.assertEqual(result["status"], "غير مغطى")
        self.assertTrue(result["blocked"])

    def test_negative_declaration_without_later_enforcement_blocks(self):
        module = load_module()
        declaration = self.valid_page_declaration()
        declaration.pop("enforced_by")
        deferred = module.deferred_producer_ids(self.manifest(declaration), "G001")
        result = module.classify_missing_surface(
            {"label": "صفحة التقرير", "producer": "B010"},
            deferred,
            {},
            "المصدر غير موجود",
        )
        self.assertNotIn("B010", deferred)
        self.assertEqual(result["status"], "غير مغطى")
        self.assertTrue(result["blocked"])

    def test_negative_existing_surface_with_failed_check_blocks(self):
        module = load_module()
        result = module.classify_evaluated_surface(style_rc=2, prose_rc=0)
        self.assertEqual(result["status"], "مانع")
        self.assertTrue(result["blocked"])


if __name__ == "__main__":
    unittest.main()
