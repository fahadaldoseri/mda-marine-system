#!/usr/bin/env python3
"""اختبارات فرز gate_audit: الحالة الحقيقية تُكتشف، والبنية السليمة لا تُرفع كمرشح."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_AUDIT = Path("/home/ubuntu/skills/gate-strictness-hardening-ops/scripts/gate_audit.py")
if not SKILL_AUDIT.exists():
    SKILL_AUDIT = ROOT / "skills" / "gate-strictness-hardening-ops" / "scripts" / "gate_audit.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"تعذر تحميل {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_module(SKILL_AUDIT, "gate_audit_under_test")
CROSSING = load_module(ROOT / "tools" / "crossing_gate.py", "crossing_gate_under_test")
ESTIMATE = load_module(ROOT / "tools" / "estimate_accuracy.py", "estimate_accuracy_under_test")


class GateAuditTriageTests(unittest.TestCase):
    def write(self, root: Path, rel: str, text: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_real_cases_still_detected_while_fixtures_and_bounded_code_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "runbook/runbook.json", "{}")
            self.write(root, "INDEX.md", "")
            self.write(root, "validators/check_unlinked.py", "def main():\n    return 2\n")
            self.write(root, "tests/test_unlinked.py", "raise SystemExit(1)\n")
            self.write(root, "tools/real_secret.py", "API_KEY = 'real-secret-value'\n")
            self.write(root, "tests/test_secret_fixture.py", "TELEGRAM_BOT_TOKEN='tok-123'\n")
            self.write(root, "tools/bounded.py", """
items = [1, 2]
i = 0
while i < len(items):
    i += 1
""")
            self.write(root, "tools/unbounded.py", """
while pending:
    pass
""")
            self.write(root, "tools/http_probe.py", "curl -s https://example.test\n")
            self.write(root, "tools/http_probe_ok.py", "curl -A 'MDA-Live-Gate/1.0' --max-time 10 https://example.test\n")
            self.write(root, "tools/api_client.py", "import urllib.request\n")
            self.write(root, "tools/report.py", "LOG = 'logs/report.jsonl'\nLOG.write_text(json.dumps({'outcome': 'x'}))\n")
            self.write(root, "tools/report_dated.py", "LOG = 'logs/report.jsonl'\nLOG.write_text(json.dumps({'date': args.date, 'outcome': 'x'}))\n")

            self.assertEqual(AUDIT.check_unlinked(root, "{}", ""), ["validators/check_unlinked.py"])
            self.assertEqual(AUDIT.check_secret_false_positives(root), ["tools/real_secret.py"])
            self.assertEqual(AUDIT.check_unbounded_loops(root), ["tools/unbounded.py:2"])
            self.assertEqual(AUDIT.check_static_verification(root), ["tools/http_probe.py"])
            self.assertEqual(AUDIT.check_verdict_freshness(root), ["tools/report.py"])

    def test_estimate_report_gets_one_replaceable_generation_stamp(self):
        table = (
            "| عدد التقديرات | 1 |\n"
            "| ما تحقق | 1 |\n"
            "| ما لم يتحقق | 0 |\n"
            "| ما بقي لم يتم التأكيد بعد | 0 |\n"
            "| أكثر سبب للخطأ | غير مسجل بعد |\n"
        )
        stamped = ESTIMATE.stamp_report(table, "2026-11-06T19:20:00+00:00")
        self.assertIn("**آخر توليد (UTC):** 2026-11-06T19:20:00+00:00", stamped)
        replaced = ESTIMATE.stamp_report(stamped, "2026-11-06T19:21:00+00:00")
        self.assertEqual(replaced.count("آخر توليد (UTC)"), 1)
        self.assertIn("19:21:00", replaced)

    def test_related_guard_contract_accepts_assert_equal_zero_and_two(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "validators/check_reference_generated.py", "def main():\n    return 0\n")
            self.write(root, "tests/test_reference_generator.py", """
def test_contract():
    self.assertEqual(cmd_check("valid"), 0)
    self.assertEqual(cmd_check("invalid"), 2)
""")

            self.assertEqual(AUDIT.check_negative_tests(root), [])

    def test_live_probe_is_bounded_and_attributable(self):
        script = CROSSING.live_probe_script("https://example.test", ("index",))
        self.assertIn("-A 'MDA-Live-Gate/1.0'", script)
        self.assertIn("--connect-timeout 10", script)
        self.assertIn("--max-time 25", script)
        self.assertNotIn("curl -s -o", script)


if __name__ == "__main__":
    unittest.main()
