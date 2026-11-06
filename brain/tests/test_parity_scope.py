#!/usr/bin/env python3
"""اختبار نطاق فاحص التماثل وأسبابه — أمر فهد 2026-10-24 (البنود 5 و8).

يمنع ثلاثة أشياء:
  1) مجموعة استثناء في الفاحص بلا سبب مكتوب في GROUP_REASONS.
  2) خروج أي ملف من النطاق بصمت: عدد الملفات المقارَنة لا يقلّ عن الأرضية 1682.
  3) حذف ملف الأسرار المعتمد من قائمة الحماية.
  4) المهارة المعتمدة المتطابقة تمر ولو وُجدت مهارة غير معتمدة في المصدر.
  5) اختلاف/فقد ملف داخل مهارة معتمدة يفشل مغلقًا ويسمّي الملف.
رمز الخروج: 0 سليم · 1 مخالفة.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
V = B / "validators" / "check_backup_parity.py"
FLOOR = 1682


def _fixture(
    repo_skill_text: str | None = "approved\n",
    *,
    include_source_unapproved: bool = True,
    include_repo_unapproved: bool = False,
) -> tuple[tempfile.TemporaryDirectory[str], dict[str, Path]]:
    """أنشئ شجرة دنيا ومستودع Git متتبّعًا لاختبار عقد المدقق الحقيقي."""
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


def test_approved_skill_match_passes_and_unapproved_skill_is_ignored() -> None:
    td, paths = _fixture()
    try:
        result = _run_fixture(paths)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "unapproved-skill" not in result.stdout
    finally:
        td.cleanup()


def test_approved_skill_difference_fails_and_names_file() -> None:
    td, paths = _fixture(repo_skill_text="tampered\n")
    try:
        result = _run_fixture(paths)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "skills/approved-skill/SKILL.md" in result.stdout
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


def test_missing_approved_skill_fails_closed() -> None:
    td, paths = _fixture(repo_skill_text=None)
    try:
        result = _run_fixture(paths)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "skills/approved-skill/SKILL.md" in result.stdout
    finally:
        td.cleanup()


def groups(src: str) -> set[str]:
    found = set()
    for name in ("BSKIP_DIRS", "SSKIP_DIRS", "BSKIP_FILES", "SSKIP_FILES", "SKIP_GLOBS", "ALLOW_REPO_ONLY", "LOCAL_ONLY_PATTERNS"):
        if re.search(rf"^{name}\s*=", src, re.M):
            found.add(name)
    return found


def run_skill_scope_contracts() -> int:
    for test in (
        test_approved_skill_match_passes_and_unapproved_skill_is_ignored,
        test_approved_skill_difference_fails_and_names_file,
        test_unapproved_repo_skill_is_ignored,
        test_missing_approved_skill_fails_closed,
    ):
        try:
            test()
        except AssertionError as exc:
            print(f"  ✘ عقد نطاق المهارات فشل: {exc}")
            return 1
    print("  ✔ عقد نطاق المهارات المعتمدة: موجب 2/2 · سالب 2/2")
    return 0


def main() -> int:
    src = V.read_text(encoding="utf-8")
    reasons = re.search(r"GROUP_REASONS\s*=\s*\{(.*?)\n\}", src, re.S)
    if not reasons:
        print("  ✘ لا يوجد GROUP_REASONS في فاحص التماثل")
        return 1
    declared = set(re.findall(r'"([A-Z_]+)":', reasons.group(1)))
    missing = sorted(groups(src) - declared)
    if missing:
        print("  ✘ مجموعات استثناء بلا سبب مكتوب: " + " · ".join(missing))
        return 1
    print(f"  ✔ كل مجموعات الاستثناء لها سبب مكتوب: {len(declared)}")
    if run_skill_scope_contracts():
        return 1

    repo = Path(__import__("os").environ.get("BACKUP_REPO_DIR") or V.resolve().parents[1].parent / "mda-marine-system")
    if not (repo / "brain" / "validators").is_dir():
        # مستودع وهمي أو غائب (بيئة معزولة/اختبار): لا نطاق حقيقي للمقارنة
        print("  · لا مستودع مرآة صالح في هذه البيئة — يُتخطّى فحص النطاق")
        return 0
    r = subprocess.run([sys.executable, str(V), "--mode", "strict"],
                       capture_output=True, text=True, timeout=600)
    out = r.stdout
    if r.returncode == 3:
        # بيئة بلا مستودع نسخ (مثل النسخة المعزولة): لا نطاق للمقارنة — ليس تضييقًا
        print("  · لا مستودع نسخ احتياطي في هذه البيئة — يُتخطّى فحص النطاق")
        return 0
    if "لا مقارنة" in out:
        # تشغيل من داخل نسخة من المستودع (استنساخ/Codespaces/نسخة معزولة)
        print("  · تشغيل من داخل نسخة من المستودع — يُتخطّى فحص النطاق")
        return 0
    m = re.search(r"الشجرة المحلية:\s*(\d+)", out)
    if not m:
        print("  ✘ لم يطبع الفاحص عدد ملفات النطاق")
        return 1
    count = int(m.group(1))
    if count < FLOOR:
        print(f"  ✘ تضييق صامت للنطاق: {count} ملفًا مقابل الأرضية {FLOOR}")
        return 1
    print(f"  ✔ نطاق التماثل {count} ملفًا ≥ الأرضية {FLOOR}")

    if "secrets/secrets.env" not in src:
        print("  ✘ ملف الأسرار المعتمد ليس في قائمة الحماية")
        return 1
    print("  ✔ ملف الأسرار المعتمد محمي من الحذف في النسخ الاحتياطي")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
