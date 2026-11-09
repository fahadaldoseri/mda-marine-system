#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار لحارس أزواج سجل البطاقات (ك-596) — يعمل بـunittest.

الحالات:
  1. سالبة 1: قائمة عربية أقصر من نظيرتها الإنجليزية → مخالفة (وهي العطل المقيس:
     badges عربي بند واحد مقابل إنجليزي بندين، فقُرئ البند العربي بترجمة عبارة
     أخرى ودخل المعجم مدخلًا خاطئًا).
  2. سالبة 2: تاريخ عربي غائب عن نظيره الإنجليزي → مخالفة.
  3. سالبة 3: سنة في العربي غائبة عن الإنجليزي → مخالفة.
  4. موجبة: أزواج متطابقة الطول ومحافظة على الأرقام → لا مخالفة.
  5. موجبة حيّة: السجل الحاكم الفعلي خالٍ من المخالفات.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

B = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "check_card_registry_pairs", B / "validators" / "check_card_registry_pairs.py")
V = importlib.util.module_from_spec(spec)
sys.modules["check_card_registry_pairs"] = V
spec.loader.exec_module(V)


def _write(payload: dict) -> pathlib.Path:
    target = pathlib.Path(tempfile.mkdtemp()) / "card_registry.json"
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return target


class CardRegistryPairs(unittest.TestCase):
    def test_negative_list_length_mismatch(self):
        p = _write({"official_cards": {"cards": [
            {"id": "x", "badges": ["آخر تحديث سبتمبر 2026"],
             "badges_en": ["For public information", "Last updated September 2026"]}]}})
        bad = V.check(p)
        self.assertEqual(len(bad), 1)
        self.assertIn("طول القائمة مختلف", bad[0])

    def test_negative_missing_date_in_english(self):
        p = _write({"official_cards": {"cards": [
            {"id": "y", "layer": {"value": "03/11/2026", "value_en": "02/11/2026"}}]}})
        bad = V.check(p)
        self.assertEqual(len(bad), 1)
        self.assertIn("أرقام في العربي غائبة", bad[0])

    def test_negative_missing_year_in_english(self):
        p = _write({"official_cards": {"cards": [
            {"id": "w", "badges": ["آخر تحديث سبتمبر 2026"],
             "badges_en": ["For public information"]}]}})
        bad = V.check(p)
        self.assertEqual(len(bad), 1)
        self.assertIn("أرقام في العربي غائبة", bad[0])

    def test_positive_matching_pairs(self):
        p = _write({"official_cards": {"cards": [
            {"id": "z", "badges": ["آخر تحديث سبتمبر 2026"],
             "badges_en": ["Last updated September 2026"],
             "layer": {"value": "03/11/2026", "value_en": "03/11/2026"}}]}})
        self.assertEqual(V.check(p), [])

    def test_live_registry_is_clean(self):
        self.assertEqual(V.check(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
