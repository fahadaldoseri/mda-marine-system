from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "partition_audit_files.py"
REAL_ROUND_FILES = [
    "brain/notes/defects-2026-11-11-measured.md",
    "brain/web/meta/2026-11-11.json",
    "brain/cumulative-2026/daily/2026-11-11.json",
    "brain/reports/2026-11-11-sectioned.md",
    "site/sources/i18n/en/2026-11-11-sectioned.en.md",
    "site/generator/build_report.py",
    "site/generator/build_site.py",
    "site/generator/map_gulf.py",
]


class PartitionAuditFilesTests(unittest.TestCase):
    def run_manifest(self, text: str, agents: str = "raw,site,governance") -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "files.txt"
            manifest.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--files", str(manifest), "--agents", agents],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

    def test_measured_round_files_are_assigned_once(self) -> None:
        result = self.run_manifest("\n".join(REAL_ROUND_FILES) + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        assignments = output["assignments"]
        flattened = [path for owned in assignments.values() for path in owned]
        self.assertEqual(output["file_count"], len(REAL_ROUND_FILES))
        self.assertEqual(output["unique_assignments"], len(REAL_ROUND_FILES))
        self.assertCountEqual(flattened, REAL_ROUND_FILES)
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_duplicate_file_fails_closed(self) -> None:
        duplicate = REAL_ROUND_FILES[0]
        result = self.run_manifest(f"{duplicate}\n{duplicate}\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("مسار مكرر", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_duplicate_agent_fails_closed(self) -> None:
        result = self.run_manifest("\n".join(REAL_ROUND_FILES[:2]) + "\n", "raw,raw")
        self.assertEqual(result.returncode, 2)
        self.assertIn("اسم وكيل مكرر", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
