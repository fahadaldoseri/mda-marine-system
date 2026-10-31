#!/usr/bin/env python3
"""حارس عقد المانيفست↔الأداة: كل سطر نجاح يطلبه B010 يجب أن يصدره منتجه الفعلي."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "runbook" / "runbook.json"
PRODUCER = ROOT / "validators" / "check_card_counters.py"
DETAIL_LINE = "✔ حراسة البطاقات التصريحية:"


class ManifestOutputContractTests(unittest.TestCase):
    def test_b010_contract_lines_are_emitted_by_card_counter_tool(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        step = next(step for step in manifest["steps"] if step["id"] == "B010")
        assertions = "\n".join(" ".join(a.get("command", [])) for a in step.get("assert", []))
        contracts = re.findall(r"grep\s+-q\s+'([^']+)'", assertions)
        self.assertTrue(contracts, "B010 يجب أن يحوي سطر عقد grep صريحًا")
        source = PRODUCER.read_text(encoding="utf-8")
        for line in contracts:
            self.assertIn(line, source, f"سطر عقد B010 غير مُصدر من {PRODUCER}: {line}")
        self.assertIn(DETAIL_LINE, source, "يجب ألا يُحذف السطر التفصيلي الجديد من مخرج الحارس")


if __name__ == "__main__":
    unittest.main()
