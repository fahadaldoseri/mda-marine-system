#!/usr/bin/env python3
"""اختبار حاجز النسخ الاحتياطي: الدفع إلى فرع مسموح، وإلى main ممنوع."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "github_backup.sh"
GUARD = ROOT / "validators" / "check_backup_push_safety.py"


class BackupPushSafetyTests(unittest.TestCase):
    def run_guard(self, body: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "github_backup.sh"
            script.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(GUARD), "--script", str(script)],
                capture_output=True,
                text=True,
            )

    def test_guard_accepts_branch_push_and_rejects_main_push(self):
        safe = self.run_guard(
            'BACKUP_BRANCH="backup/2026-10-31-210000"\n'
            'git push -q -u origin "$BACKUP_BRANCH"\n'
            'gh pr create --base main --head "$BACKUP_BRANCH"\n'
        )
        self.assertEqual(safe.returncode, 0, safe.stdout + safe.stderr)
        self.assertIn("آمن", safe.stdout)

        direct = self.run_guard('git push -q origin main\n')
        self.assertEqual(direct.returncode, 2, direct.stdout + direct.stderr)
        self.assertIn("main", direct.stdout + direct.stderr)

    def test_backup_script_uses_pr_flow_and_guard(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"git\s+push\b[^\n#]*\bmain\b")
        self.assertIn("check_backup_push_safety.py", text)
        self.assertIn('git push -q -u origin "$BACKUP_BRANCH"', text)
        self.assertIn('gh pr create --base main --head "$BACKUP_BRANCH"', text)
        self.assertIn("فشل مغلق", text)

    def test_unknown_arguments_fail_before_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            isolated = Path(tmp)
            script = isolated / "github_backup.sh"
            script.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            env = {"BRAIN_DIR": str(isolated / "brain"), "BACKUP_REPO_DIR": str(isolated / "repo")}
            for argument in ("--help", "--unknown"):
                result = subprocess.run(
                    ["bash", str(script), argument],
                    cwd=isolated,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("معامل غير معروف", result.stderr)
                self.assertFalse((isolated / "brain").exists())
                self.assertFalse((isolated / "repo").exists())


if __name__ == "__main__":
    unittest.main()
