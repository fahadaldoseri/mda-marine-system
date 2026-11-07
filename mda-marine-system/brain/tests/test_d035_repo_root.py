#!/usr/bin/env python3
"""حارس عقد D035: لا يُضاعف جذر المرآة عند تمرير --repo."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "runbook" / "runbook.json"


class D035RepoRootContractTests(unittest.TestCase):
    def test_d035_resolves_repo_from_brain_git_root_without_duplication(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        step = next(item for item in manifest["steps"] if item["id"] == "D035")
        command = " ".join(step["command"])

        self.assertNotIn(
            '$(dirname "$B")/mda-marine-system',
            command,
            "D035 يجب ألا يضاعف اسم المرآة عندما يكون B داخلها",
        )
        self.assertIn(
            'git -C "$B" rev-parse --show-toplevel',
            command,
            "D035 يجب أن يشتق جذر المرآة من Git بدل مسار ثابت",
        )
        self.assertIn(
            'check_repo_secrets.py --repo "$REPO"',
            command,
            "فاحص أسرار المرآة يجب أن يستخدم الجذر المشتق",
        )


if __name__ == "__main__":
    unittest.main()
