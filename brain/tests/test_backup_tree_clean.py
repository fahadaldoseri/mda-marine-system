#!/usr/bin/env python3
"""اختبار حارس D040: سجلات التشغيل المحلية لا توقف النسخ، والشيفرة تبقى مانعة."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "github_backup.sh"
GUARD = ROOT / "validators" / "check_backup_tree_clean.py"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, text=True,
                   capture_output=True)


class BackupTreeCleanContractTests(unittest.TestCase):
    def test_backup_script_uses_runtime_tree_clean_guard(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(
            "check_backup_tree_clean.py",
            source,
            "D040 يجب أن يستخدم حارسًا يميّز السجلات المحلية عن الشيفرة",
        )

    def _repo(self, tmp: Path) -> Path:
        repo = tmp / "mda-marine-system"
        (repo / "brain" / "logs").mkdir(parents=True)
        (repo / "brain" / "tools").mkdir(parents=True)
        (repo / "brain" / "reports").mkdir(parents=True)
        (repo / "brain" / "tools" / "real.py").write_text("print('baseline')\n", encoding="utf-8")
        (repo / "brain" / "reports" / "data.json").write_text("{}\n", encoding="utf-8")
        subprocess.run(["git", "init", "-b", "main", str(repo)], check=True,
                       text=True, capture_output=True)
        git(repo, "config", "user.name", "test")
        git(repo, "config", "user.email", "test@example.invalid")
        git(repo, "add", ".")
        git(repo, "commit", "-m", "baseline")
        return repo

    def _run_guard(self, repo: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update({"BRAIN_DIR": str(ROOT), "BACKUP_REPO_DIR": str(repo)})
        return subprocess.run(
            ["python3", str(GUARD), "--repo", str(repo), "--brain", str(ROOT)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )

    def test_runtime_logs_only_pass_with_sha256_evidence(self):
        with tempfile.TemporaryDirectory(prefix="backup-tree-clean-") as raw:
            repo = self._repo(Path(raw))
            runtime = repo / "brain" / "logs" / "runbook-2026-11-07.log"
            runtime.write_text("runtime output\n", encoding="utf-8")
            proc = self._run_guard(repo)
            digest = hashlib.sha256(runtime.read_bytes()).hexdigest()
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("سجلات تشغيل معلنة", proc.stdout)
            self.assertIn(f"sha256={digest}", proc.stdout)

    def test_real_code_change_fails_closed_with_sha256_evidence(self):
        with tempfile.TemporaryDirectory(prefix="backup-tree-clean-") as raw:
            repo = self._repo(Path(raw))
            changed = repo / "brain" / "tools" / "real.py"
            changed.write_text("print('real change')\n", encoding="utf-8")
            proc = self._run_guard(repo)
            digest = hashlib.sha256(changed.read_bytes()).hexdigest()
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("تعديلات حاكمة", proc.stdout)
            self.assertIn("brain/tools/real.py", proc.stdout)
            self.assertIn(f"sha256={digest}", proc.stdout)


if __name__ == "__main__":
    unittest.main()
