#!/usr/bin/env python3
"""عقد التماثل: اللقطة الملتزمة مانعة، والعمل غير الملتزم معلوماتي."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validators" / "check_backup_parity.py"
GUARD = ROOT / "validators" / "_guard.py"
SCOPE = {
    "version": 1,
    "categories": [
        {
            "id": "governing",
            "reason": "محتوى حاكم يجب أن يطابق المرآة بعد الالتزام.",
            "policy": "strict",
            "prefixes": [
                "brain/validators/",
                "brain/runbook/",
                "brain/governing/",
                "skills/",
            ],
        },
        {
            "id": "evidence_measurements",
            "reason": "أدلة وقياسات تشغيلية تُذكر ولا تمنع اللقطة الملتزمة.",
            "policy": "informational",
            "prefixes": ["brain/evidence/", "brain/audit/measurements/"],
        },
        {
            "id": "operational_logs",
            "reason": "سجلات التشغيل يعاد توليدها وتعرض معلوماتيًا.",
            "policy": "informational",
            "prefixes": ["brain/logs/"],
        },
        {
            "id": "generated",
            "reason": "مخرجات مولدة لا تدخل حكم محتوى المصدر الملتزم.",
            "policy": "informational",
            "prefixes": ["brain/generated/"],
        },
    ],
    "roots": {
        "brain": {"skip_dirs": ["__pycache__", ".git"], "skip_files": []},
        "site": {"skip_dirs": ["__pycache__", ".git"], "skip_files": []},
    },
    "repo": {
        "only_prefixes": [],
        "extra_allow": [],
        "sanitized": [],
        "protected": [],
        "symlink_views": [],
    },
    "junk_files": [".DS_Store", ".skill_versions.json"],
}


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(cwd), *args], text=True, capture_output=True, check=check)


def _fixture(tmp_path: Path, *, mirror_governing: bool = True) -> tuple[Path, Path]:
    source = tmp_path / "source"
    repo = tmp_path / "repo"
    for path in (
        source / "validators",
        source / "runbook",
        source / "governing",
        repo / "brain" / "validators",
        repo / "brain" / "runbook",
        repo / "brain" / "governing",
    ):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VALIDATOR, source / "validators" / VALIDATOR.name)
    shutil.copy2(GUARD, source / "validators" / GUARD.name)
    shutil.copy2(VALIDATOR, repo / "brain" / "validators" / VALIDATOR.name)
    shutil.copy2(GUARD, repo / "brain" / "validators" / GUARD.name)
    approved = {"skills": ["approved-skill"]}
    (source / "runbook" / "approved-skills.json").write_text(
        json.dumps(approved) + "\n", encoding="utf-8"
    )
    (repo / "brain" / "runbook" / "approved-skills.json").write_text(
        json.dumps(approved) + "\n", encoding="utf-8"
    )
    (source / "runbook" / "parity-scope.json").write_text(
        json.dumps(SCOPE, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (repo / "brain" / "runbook" / "parity-scope.json").write_text(
        json.dumps(SCOPE, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (source / "governing" / "committed.txt").write_text("committed\n", encoding="utf-8")
    if mirror_governing:
        (repo / "brain" / "governing" / "committed.txt").write_text("committed\n", encoding="utf-8")
    _git(source, "init", "-q")
    _git(source, "config", "user.email", "test@example.invalid")
    _git(source, "config", "user.name", "parity-test")
    _git(source, "add", "validators", "runbook", "governing")
    _git(source, "commit", "-qm", "source committed snapshot")

    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "parity-test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "mirror snapshot")
    return source, repo


def _run(source: Path, repo: Path, *, skills: Path, scope_override: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(
        os.environ,
        BRAIN_DIR=str(source),
        SITE_DIR=str(source / "site"),
        BACKUP_REPO_DIR=str(repo),
        SKILLS_DIR=str(skills),
        SOURCE_GIT_DIR=str(source),
        SOURCE_GIT_PREFIX="",
    )
    if scope_override is not None:
        env["PARITY_SCOPE_FILE"] = scope_override
    return subprocess.run(
        [sys.executable, str(source / "validators" / VALIDATOR.name), "--mode", "strict"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _skills(tmp_path: Path) -> Path:
    skills = tmp_path / "skills"
    (skills / "approved-skill").mkdir(parents=True, exist_ok=True)
    (skills / "approved-skill" / "SKILL.md").write_text("approved\n", encoding="utf-8")
    return skills


def test_committed_governing_file_missing_from_mirror_fails_closed(tmp_path: Path) -> None:
    source, repo = _fixture(tmp_path, mirror_governing=False)
    result = _run(source, repo, skills=_skills(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr
    assert "مفقود من المستودع: brain/governing/committed.txt" in result.stdout


def test_new_uncommitted_source_file_is_informational(tmp_path: Path) -> None:
    source, repo = _fixture(tmp_path)
    (source / "governing" / "new-uncommitted.txt").write_text("work in progress\n", encoding="utf-8")
    result = _run(source, repo, skills=_skills(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "غير ملتزم" in result.stdout
    assert "new-uncommitted.txt" in result.stdout


def test_missing_or_corrupt_scope_registry_fails_closed(tmp_path: Path) -> None:
    source, repo = _fixture(tmp_path)
    scope = source / "runbook" / "parity-scope.json"
    scope.unlink()
    result = _run(source, repo, skills=_skills(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr
    assert "parity-scope.json" in result.stdout

    scope.write_text("{broken\n", encoding="utf-8")
    result = _run(source, repo, skills=_skills(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr
    assert "parity-scope.json" in result.stdout


def test_unclassified_file_fails_closed(tmp_path: Path) -> None:
    source, repo = _fixture(tmp_path)
    rogue = source / "rogue" / "not-classified.txt"
    rogue.parent.mkdir()
    rogue.write_text("rogue\n", encoding="utf-8")
    _git(source, "add", "rogue/not-classified.txt")
    _git(source, "commit", "-qm", "add unclassified source file")
    result = _run(source, repo, skills=_skills(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr
    assert "غير مصن" in result.stdout
    assert "brain/rogue/not-classified.txt" in result.stdout


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
