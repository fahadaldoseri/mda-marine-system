#!/usr/bin/env python3
"""حراسة اعتماد مهارة النقل: ملفات، مستهلك G026، قرار بدليل وحالة سالبة."""
from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "portable-paths-repair-ops"
REF = f"skills/{NAME}/SKILL.md"


def wiring_errors(root: Path, manifest: dict, registry: dict) -> list[str]:
    errors = []
    for path in (root / REF, root.parent / REF):
        if not path.is_file():
            errors.append(f"ملف المهارة مفقود: {path}")
    index = (root / "INDEX.md").read_text(encoding="utf-8")
    if f"| `{NAME}` |" not in index:
        errors.append("المهارة غير مدرجة في جدول الفهرس")
    steps = manifest.get("steps", [])
    gate = next((s for s in steps if s.get("id") == "G026"), {})
    if REF not in gate.get("links", {}).get("files", []):
        errors.append("G026 لا يستهلك مرجع المهارة")
    restore = (root / "tools/restore_skills.sh").read_text(encoding="utf-8")
    match = re.search(r'OUR_SKILLS="([^"]+)"', restore)
    if not match or NAME not in match.group(1).split():
        errors.append("المهارة غير مسجلة في قائمة الاستعادة")
    runner = (root / "tests/run_checks.sh").read_text(encoding="utf-8")
    active = runner.split("\nexit 0", 1)[0]
    if not re.search(r'^t\s+"[^"]+"\s+python3\s+tests/test_portable_paths_skill_adoption\.py\s*$',
                     active, re.MULTILINE):
        errors.append("G001 لا يشغل حارس الاعتماد")
    decisions = [d for d in registry.get("decisions", [])
                 if NAME in d.get("title_ar", "")]
    if len(decisions) != 1:
        errors.append("لا قرار اعتماد وحيد للمهارة")
    else:
        decision = decisions[0]
        evidence = {e.get("ref") for e in decision.get("evidence", [])
                    if isinstance(e, dict) and e.get("kind") == "file"}
        if not {REF, "INDEX.md", "runbook/runbook.json"}.issubset(evidence):
            errors.append("قرار الاعتماد بلا أدلة الملف والفهرس والمستهلك")
        if decision.get("governing_file") != "INDEX.md":
            errors.append("ملف حاكم غير مطابق لاعتماد المهارة")
    return errors


class SkillAdoptionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "runbook/runbook.json").read_text())
        cls.registry = json.loads((ROOT / "decisions/registry.json").read_text())

    def test_project_wiring_passes(self):
        self.assertEqual([], wiring_errors(ROOT, self.manifest, self.registry))

    def test_missing_gate_reference_is_rejected(self):
        bad = copy.deepcopy(self.manifest)
        gate = next(s for s in bad["steps"] if s["id"] == "G026")
        gate["links"]["files"] = [p for p in gate["links"]["files"] if p != REF]
        self.assertIn("G026 لا يستهلك مرجع المهارة", wiring_errors(ROOT, bad, self.registry))

    def test_unsubstantiated_adoption_is_rejected(self):
        bad = copy.deepcopy(self.registry)
        for decision in bad["decisions"]:
            if NAME in decision.get("title_ar", ""):
                decision["evidence"] = []
        self.assertIn("قرار الاعتماد بلا أدلة الملف والفهرس والمستهلك",
                      wiring_errors(ROOT, self.manifest, bad))


if __name__ == "__main__":
    unittest.main(verbosity=2)
