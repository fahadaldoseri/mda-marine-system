#!/usr/bin/env python3
"""اختبار انحدار: مخلفات بايثون المولَّدة ليست شيفرة ولا بيانات (ك-516).

السبب: `brain/tools/**` و`brain/tests/**` مصنَّفة شيفرة، فصار ملف `.pyc` مولَّد
يُقارَن بين الخادم والمستودع ويُعلَن «تعارضًا» يمنع تطبيق الشيفرة والنسخ الاحتياطي.
القاعدة الجديدة: قائمة `ignore` في `appendices/code-paths.json` تُصنّف المولَّد
«generated» فلا يُقارَن ولا يُنسخ ولا يُلزم تعقّبه.

اختبار موجب: مسار مولَّد → generated.
اختبار سالب: شيفرة حقيقية → code، وبيانات → data (لا يتسرّب التجاهل).
"""
import json
import sys
import unittest
from pathlib import Path

BRAIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRAIN / "tools"))
import code_paths  # noqa: E402


def spec():
    return json.loads((BRAIN / "appendices" / "code-paths.json").read_text(encoding="utf-8"))


class CodePathsIgnoreTests(unittest.TestCase):
    def test_ignore_list_declared(self):
        self.assertTrue(spec().get("ignore"), "قائمة التجاهل غائبة عن المواصفة")

    def test_generated_pyc_is_not_code(self):
        for rel in (
            "brain/tools/__pycache__/ledger_totals.cpython-312.pyc",
            "brain/tests/__pycache__/test_card_counters.cpython-312.pyc",
            "site/generator/__pycache__/build_report.cpython-312.pyc",
        ):
            self.assertEqual("generated", code_paths.classify(rel, spec()), rel)

    def test_generated_is_ignored(self):
        self.assertTrue(code_paths.is_ignored("brain/tools/__pycache__/x.pyc", spec()))
        self.assertFalse(code_paths.is_ignored("brain/tools/ledger_totals.py", spec()))

    def test_real_code_still_code(self):
        for rel in (
            "brain/tools/ledger_totals.py",
            "brain/validators/check_number_bindings.py",
            "site/generator/build_report.py",
            "skills/.skill_versions.json",
        ):
            self.assertEqual("code", code_paths.classify(rel, spec()), rel)

    def test_data_still_data(self):
        for rel in (
            "brain/web/meta/2026-11-04.json",
            "brain/cumulative-2026/daily/2026-11-04.json",
        ):
            self.assertEqual("data", code_paths.classify(rel, spec()), rel)


if __name__ == "__main__":
    unittest.main(verbosity=2)