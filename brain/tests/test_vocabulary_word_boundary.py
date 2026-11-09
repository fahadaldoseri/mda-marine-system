#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ك-591: حدود الكلمة العربية — «سند» لا تُطابق داخل «تُسند»، والبديل يُقرأ من plain."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

BRAIN = pathlib.Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "cv", BRAIN / "validators" / "check_vocabulary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WordBoundaryTests(unittest.TestCase):
    def test_verb_containing_term_is_not_a_hit(self):
        self.assertFalse(_module()._word_hit("سند", "لا تُسند المصادر الإعلامية واقعةً وحدها."))

    def test_standalone_term_is_a_hit(self):
        self.assertTrue(_module()._word_hit("سند", "هذا سند قوي للواقعة."))

    def test_plain_field_supplies_alternative(self):
        self.assertEqual(
            _module()._alternative({"term": "سند", "plain": ["مصدر التقدير", "الأساس"]}),
            "مصدر التقدير؛ الأساس")


if __name__ == "__main__":
    unittest.main()
