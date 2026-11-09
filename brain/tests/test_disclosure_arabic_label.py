#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""عقد الإفصاح: متن عربي يُقبل بتسميته العربية للمكوّن، والرموز اللاتينية ليست شرطًا."""
from __future__ import annotations

import pathlib
import sys
import unittest

BRAIN = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN / "validators"))


class DisclosureLabelTests(unittest.TestCase):
    def test_arabic_label_table_covers_mark_components(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "crc", BRAIN / "validators" / "check_run_completeness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for comp in ("feeds", "ofac", "originals", "ledger_merge"):
            self.assertIn(comp, module.COMPONENT_LABELS_AR, f"لا تسمية عربية للمكوّن {comp}")
            self.assertTrue(all(lbl.strip() for lbl in module.COMPONENT_LABELS_AR[comp]))

    def test_arabic_disclosure_text_would_match(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "crc", BRAIN / "validators" / "check_run_completeness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        body = "سُجِّل تعذّر مسارات المصدرين، والتغذية ناقصة بإفصاح مكتوب."
        labels = module.COMPONENT_LABELS_AR.get("feeds", ())
        self.assertTrue(any(lbl in body for lbl in labels))


if __name__ == "__main__":
    unittest.main()
