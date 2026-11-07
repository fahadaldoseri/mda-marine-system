#!/usr/bin/env python3
"""عقد سجل نطاق التماثل: سبب مكتوب، تصنيف شامل، وفشل مغلق."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
V = B / "validators" / "check_backup_parity.py"
SCOPE = B / "runbook" / "parity-scope.json"
FLOOR = 1682


def _fixture(
    repo_skill_text: str | None = "approved\n",
    *,
    include_source_unapproved: bool = True,
    include_repo_unapproved: bool = False,
) -> tuple[tempfile.TemporaryDirectory[str], dict[str, Path]]:
    td = tempfile.TemporaryDirectory(prefix="parity-approved-scope-")
    root = Path(td.name)
    brain = root / "brain"
    site = root / "site"
    repo = root / "mda-marine-system"
    source = root / "skills"
    for path in (brain / "validators", brain / "runbook", site,
                 repo / "brain" / "validators", repo / "brain" / "runbook", source):
        path.mkdir(parents=True, exist_ok=True)

    (brain / "runbook" / "approved-skills.json").write_text(
        json.dumps({"skills": ["approved-skill"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(SCOPE, brain / "runbook" / "parity-scope.json")
    for name in ("check_backup_parity.py", "_guard.py"):
        shutil.copy2(V.parent / name, brain / "validators" / name)
    approved = source / "approved-skill"
    approved.mkdir()
    (approved / "SKILL.md").write_text("approved\n", encoding="utf-8")
    if include_source_unapproved:
        unapproved = source / "unapproved-skill"
        unapproved.mkdir()
        (unapproved / "SKILL.md").write_text("unapproved\n", encoding="utf-8")

    shutil.copy2(brain / "runbook" / "approved-skills.json", repo / "brain" / "runbook" / "approved-skills.json")
    shutil.copy2(brain / "runbook" / "parity-scope.json", repo / "brain" / "runbook" / "parity-scope.json")
    for name in ("check_backup_parity.py", "_guard.py"):
        shutil.copy2(brain / "validators" / name, repo / "brain" / "validators" / name)
    if repo_skill_text is not None:
        mirror_skill = repo / "skills" / "approved-skill"
        mirror_skill.mkdir(parents=True)
        (mirror_skill / "SKILL.md").write_text(repo_skill_text, encoding="utf-8")
    if include_repo_unapproved:
        mirror_unapproved = repo / "skills" / "unapproved-skill"
        mirror_unapproved.mkdir(parents=True)
        (mirror_unapproved / "SKILL.md").write_text("unapproved\n", encoding="utf-8")

    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "parity-test"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)
    return td, {"brain": brain, "site": site, "repo": repo, "source": source}


def _run_fixture(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    env = dict(
        os.environ,
        BRAIN_DIR=str(paths["brain"]),
        SITE_DIR=str(paths["site"]),
        BACKUP_REPO_DIR=str(paths["repo"]),
        SKILLS_DIR=str(paths["source"]),
    )
    return subprocess.run(
        [sys.executable, str(paths["brain"] / "validators" / "check_backup_parity.py"), "--mode", "strict"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_scope_registry_has_reasons_and_four_policies() -> None:
    data = json.loads(SCOPE.read_text(encoding="utf-8"))
    categories = data["categories"]
    assert {item["id"] for item in categories} == {
        "governing", "evidence_measurements", "operational_logs", "generated"
    }
    assert all(item["reason"].strip() for item in categories)
    assert all(item["policy"] in {"strict", "informational"} for item in categories)


def test_approved_skill_match_passes_and_unapproved_skill_is_ignored() -> None:
    td, paths = _fixture()
    try:
        result = _run_fixture(paths)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "unapproved-skill" not in result.stdout
    finally:
        td.cleanup()


def test_unapproved_repo_skill_is_ignored() -> None:
    td, paths = _fixture(include_source_unapproved=False, include_repo_unapproved=True)
    try:
        result = _run_fixture(paths)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "unapproved-skill" not in result.stdout
    finally:
        td.cleanup()


def test_missing_scope_registry_fails_closed() -> None:
    td, paths = _fixture()
    try:
        (paths["brain"] / "runbook" / "parity-scope.json").unlink()
        result = _run_fixture(paths)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "parity-scope.json" in result.stdout
    finally:
        td.cleanup()


def test_in_repo_mode_emits_explicit_matching_result(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    brain = repo / "brain"
    site = repo / "site"
    skills = tmp_path / "skills"
    (brain / "validators").mkdir(parents=True)
    (brain / "runbook").mkdir()
    (site / "generator").mkdir(parents=True)
    (skills / "approved-skill").mkdir(parents=True)
    shutil.copy2(V, brain / "validators" / V.name)
    shutil.copy2(V.parent / "_guard.py", brain / "validators" / "_guard.py")
    shutil.copy2(SCOPE, brain / "runbook" / "parity-scope.json")
    (brain / "runbook" / "approved-skills.json").write_text(
        json.dumps({"skills": ["approved-skill"]}) + "\n", encoding="utf-8"
    )
    (skills / "approved-skill" / "SKILL.md").write_text("approved\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "parity-test"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)

    result = subprocess.run(
        [sys.executable, str(brain / "validators" / V.name), "--mode", "strict"],
        env=dict(
            os.environ,
            BRAIN_DIR=str(brain),
            SITE_DIR=str(site),
            BACKUP_REPO_DIR=str(repo),
            SKILLS_DIR=str(skills),
        ),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "لا مقارنة" not in result.stdout
    assert "الشجرة المحلية:" in result.stdout
    assert "المستودع:" in result.stdout
    assert "النتيجة: مطابق" in result.stdout


def test_live_scope_not_narrowed() -> None:
    repo = Path(os.environ.get("BACKUP_REPO_DIR") or V.resolve().parents[1].parent / "mda-marine-system")
    if not (repo / "brain" / "validators").is_dir():
        return
    result = subprocess.run([sys.executable, str(V), "--mode", "strict"], text=True, capture_output=True, check=False)
    if result.returncode == 3 or "لا مقارنة" in result.stdout:
        return
    marker = "الشجرة المحلية:"
    assert marker in result.stdout, result.stdout + result.stderr
    count = int(result.stdout.split(marker, 1)[1].split("·", 1)[0].strip())
    assert count >= FLOOR, result.stdout


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
