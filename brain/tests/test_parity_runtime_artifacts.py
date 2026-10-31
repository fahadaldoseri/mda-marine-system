#!/usr/bin/env python3
"""حارس مخرجات التشغيل: يستثني نسخة restore_skills المؤقتة فقط، لا السجلات العامة."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VALIDATOR = Path(__file__).resolve().parents[1] / "validators" / "check_backup_parity.py"


def run_case(rel: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="parity-runtime-") as td:
        root = Path(td)
        brain = root / "brain"
        site = root / "seawatch"
        repo = root / "mda-marine-system"
        skills = root / "skills"
        generated = brain / "logs" / rel
        generated.parent.mkdir(parents=True)
        generated.write_text("generated\n", encoding="utf-8")
        site.mkdir()
        skills.mkdir()
        repo.mkdir()
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
        validator = root / "check_backup_parity.py"
        shutil.copy2(VALIDATOR, validator)
        shutil.copy2(VALIDATOR.with_name("_guard.py"), root / "_guard.py")
        env = dict(os.environ, BRAIN_DIR=str(brain), SITE_DIR=str(site),
                   BACKUP_REPO_DIR=str(repo), SKILLS_DIR=str(skills))
        return subprocess.run([sys.executable, str(validator), "--mode", "strict"],
                              env=env, text=True, capture_output=True)


def test_restore_backup_is_local_only() -> None:
    result = run_case("skills-sync-20261031/foo/SKILL.md.local.bak")
    assert result.returncode == 0, result.stdout + result.stderr


def test_general_run_log_is_not_allowlisted() -> None:
    result = run_case("runbook/2026-10-31/other.log")
    assert result.returncode == 2, result.stdout + result.stderr


if __name__ == "__main__":
    test_restore_backup_is_local_only()
    test_general_run_log_is_not_allowlisted()
    print("runtime-artifact guard: 2/2")
