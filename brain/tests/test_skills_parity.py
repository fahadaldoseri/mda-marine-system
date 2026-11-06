#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""عقد تماثل ملفات المهارات: نسخ متطابقة تمر، والاختلاف أو الفقد يمنع."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "validators" / "check_skills_parity.py"


class SkillsParityTests(unittest.TestCase):
    def _run(self, source: Path, mirror: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CHECKER),
                "--source-root",
                str(source),
                "--mirror-root",
                str(mirror),
                "--skills",
                "demo",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def _seed(self, source: Path, mirror: Path) -> None:
        for base in (source, mirror):
            (base / "demo" / "references").mkdir(parents=True)
            (base / "demo" / "SKILL.md").write_text("---\nname: demo\n---\nقاعدة\n", encoding="utf-8")
            (base / "demo" / "references" / "rules.md").write_text("# قواعد\n", encoding="utf-8")

    def test_identical_approved_skill_passes_with_counts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skills-parity-") as td:
            root = Path(td)
            source, mirror = root / "source", root / "mirror"
            self._seed(source, mirror)
            result = self._run(source, mirror)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("المهارات: 1", result.stdout)
            self.assertIn("الملفات: 2", result.stdout)
            self.assertIn("المختلف: 0", result.stdout)

    def test_changed_skill_fails_closed_and_names_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skills-parity-") as td:
            root = Path(td)
            source, mirror = root / "source", root / "mirror"
            self._seed(source, mirror)
            changed = mirror / "demo" / "references" / "rules.md"
            changed.write_text("# قواعد معدلة\n", encoding="utf-8")
            result = self._run(source, mirror)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("references/rules.md", result.stdout)
            self.assertIn("المختلف: 1", result.stdout)


if __name__ == "__main__":
    unittest.main()
