#!/usr/bin/env python3
"""اختبار موجب وسالب لأدوات بوابة العبور.

موجب: الأدوات الست تستجيب لـ --help · حارس الجاهزية يمرّ · مصفوفة الأثر تعمل.
سالب: أداة تغيب · ملف بصمة غير موجود · مصفوفة أثر غير صالحة · تغيير غير معلن ·
       سجل انحدار غائب ⇒ يفشل الأمر، فلا تُعلن جاهزية بلا دليل.

الاستعمال: python3 tests/test_gate_tools.py    رمز 0 سليم · 2 خلل
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parent / "seawatch"
TOOLS = ["crossing_gate.py", "surface_fingerprint.py", "number_fingerprint.py",
         "impact_matrix.py", "regression_gate.py", "gate_coverage.py"]


def run(argv: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], cwd=ROOT, capture_output=True, text=True, timeout=timeout)


class Positive(unittest.TestCase):
    def test_all_tools_respond_to_help(self):
        for name in TOOLS:
            with self.subTest(tool=name):
                self.assertEqual(run(["python3", f"tools/{name}", "--help"]).returncode, 0)

    def test_readiness_guard_passes(self):
        self.assertEqual(run(["python3", "validators/check_gate_readiness.py", "--root", ".", "--summary"]).returncode, 0)

    def test_impact_matrix_resolves_known_file(self):
        r = run(["python3", "tools/impact_matrix.py", "--root", ".", "--changed", "site/generator/build_report.py"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("الأسطح المتأثرة", r.stdout)


class Negative(unittest.TestCase):
    def test_undeclared_change_is_blocked(self):
        r = run(["python3", "tools/impact_matrix.py", "--root", ".", "--require-declared",
                 "--changed", "مجهول/ملف-غريب.py"])
        self.assertEqual(r.returncode, 2)

    def test_missing_baseline_file_fails(self):
        r = run(["python3", "tools/surface_fingerprint.py", "--root", ".", "--compare",
                 "/tmp/لا-يوجد-بصمة.json"])
        self.assertNotEqual(r.returncode, 0)

    def test_invalid_impact_map_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "runbook").mkdir()
            (Path(t) / "runbook" / "impact-map.json").write_text('{"rules":[{"match":"ليس-قائمة"}]}', encoding="utf-8")
            r = run(["python3", "tools/impact_matrix.py", "--root", t, "--changed", "x/y.py"])
            self.assertNotEqual(r.returncode, 0)

    def test_missing_regression_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            r = run(["python3", "tools/regression_gate.py", "--root", t, "--until", "الكل"])
            self.assertNotEqual(r.returncode, 0)

    def test_readiness_guard_detects_missing_tool(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "tools").mkdir()
            (root / "runbook").mkdir()
            (root / "runbook" / "runbook.json").write_text('{"steps":[]}', encoding="utf-8")
            (root / "runbook" / "regression-items.json").write_text(json.dumps({"items": [], "phase_order": []}), encoding="utf-8")
            (root / "runbook" / "impact-map.json").write_text(json.dumps({"rules": []}), encoding="utf-8")
            r = run(["python3", "validators/check_gate_readiness.py", "--root", t])
            self.assertEqual(r.returncode, 2)
            self.assertIn("أداة غائبة", r.stdout)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 2)
