#!/usr/bin/env python3
"""Regression test for github_backup.sh's fail-closed caller-visible output."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "github_backup.sh"


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, text=True)


class GithubBackupFailureOutputTest(unittest.TestCase):
    def test_backup_uses_isolated_worktree_for_runtime_logs(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("git worktree add", source)
        self.assertNotIn("git checkout -q main", source)

    def test_dirty_repo_reason_reaches_caller_and_log(self) -> None:
        with tempfile.TemporaryDirectory(prefix="github-backup-output-") as raw:
            tmp = Path(raw)
            brain = tmp / "brain"
            tools = brain / "tools"
            tools.mkdir(parents=True)
            script = tools / "github_backup.sh"
            shutil.copy2(SCRIPT, script)
            script.chmod(0o755)
            validators = brain / "validators"
            validators.mkdir(parents=True)
            shutil.copy2(ROOT / "validators" / "check_backup_tree_clean.py", validators)
            runbook = brain / "runbook"
            runbook.mkdir(parents=True)
            shutil.copy2(ROOT / "runbook" / "parity-scope.json", runbook)

            bare = tmp / "origin.git"
            repo = tmp / "mda-marine-system"
            subprocess.run(["git", "init", "--bare", str(bare)], check=True, text=True)
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, text=True)
            run_git(repo, "config", "user.name", "test")
            run_git(repo, "config", "user.email", "test@example.invalid")
            (repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
            run_git(repo, "add", "tracked.txt")
            run_git(repo, "commit", "-m", "baseline")
            run_git(repo, "remote", "add", "origin", str(bare))
            run_git(repo, "push", "-u", "origin", "main")
            (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")

            env = os.environ.copy()
            env.update(
                {
                    "BRAIN_DIR": str(brain),
                    "BACKUP_REPO_DIR": str(repo),
                }
            )
            proc = subprocess.run(
                ["bash", str(script)],
                cwd=brain,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            combined = proc.stdout + proc.stderr
            self.assertIn("حارس شجرة النسخ منع العملية", combined)
            utc_date = datetime.now(timezone.utc).date().isoformat()
            log = brain / "logs" / f"github-backup-{utc_date}.log"
            self.assertIn("تعديل حاكم", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
