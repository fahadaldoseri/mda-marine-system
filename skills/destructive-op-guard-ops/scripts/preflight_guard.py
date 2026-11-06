#!/usr/bin/env python3
"""Fail-closed preflight checks for destructive synchronization or replacement."""
from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDES = [".git", "secrets", "state", ".env", ".env.*", "*.pem", "*.key"]
SENSITIVE_DIRS = {".git", "secrets", "secret", "state", ".secrets"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def _resolve(value: str | Path) -> Path:
    return Path(value).expanduser().resolve(strict=False)


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _git(cwd: Path, *arguments: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _find_git_root(path: Path) -> Path | None:
    code, output, _ = _git(path, "rev-parse", "--show-toplevel")
    return _resolve(output) if code == 0 and output else None


def _is_sensitive_name(name: str) -> bool:
    return (
        name in SENSITIVE_DIRS
        or name == ".env"
        or name.startswith(".env.")
        or any(name.endswith(suffix) for suffix in SENSITIVE_SUFFIXES)
    )


def _is_excluded(relative: str, excludes: Iterable[str]) -> bool:
    """Return whether a relative path is outside the destructive operation."""
    name = Path(relative).name
    return any(
        fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(name, pattern)
        for pattern in excludes
    )


def _sensitive_paths(scope: Path, excludes: Iterable[str]) -> list[str]:
    found: list[str] = []
    if _is_sensitive_name(scope.name):
        found.append(scope.name)
    if not scope.is_dir():
        return found
    for directory, dirnames, filenames in os.walk(scope, topdown=True, followlinks=False):
        base = Path(directory)
        for name in list(dirnames):
            relative = (base / name).relative_to(scope).as_posix()
            if _is_excluded(relative, excludes):
                # The operation does not enter an explicitly excluded subtree.
                dirnames.remove(name)
                continue
            if _is_sensitive_name(name):
                found.append(relative)
                # Do not inspect the sensitive subtree or print its contents.
                dirnames.remove(name)
        for name in filenames:
            relative = (base / name).relative_to(scope).as_posix()
            if not _is_excluded(relative, excludes) and _is_sensitive_name(name):
                found.append(relative)
    return sorted(set(found))


def _exclude_inside_scope(target: Path, scope: Path, excludes: Iterable[str]) -> list[str]:
    inside: list[str] = []
    for value in excludes:
        candidate = _resolve(value) if os.path.isabs(value) else _resolve(target / value)
        if _within(candidate, scope):
            inside.append(candidate.relative_to(scope).as_posix() or ".")
    return sorted(set(inside))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="افحص جذر الهدف، نطاق الأسرار، وتتبع الفرع قبل عملية قد تحذف أو تستبدل ملفات."
    )
    parser.add_argument("--target", required=True, type=Path, help="الهدف الذي ستعمل عليه الأداة")
    parser.add_argument("--source", type=Path, help="مصدر العملية؛ يُستخدم لتحديد نطاقها")
    parser.add_argument("--repo", type=Path, help="جذر المستودع المتوقع؛ يُستنتج إن غاب")
    parser.add_argument("--expected-branch", default="main", help="الفرع المتوقع (الافتراضي main)")
    parser.add_argument("--expected-upstream", default="origin/main", help="التتبع المتوقع (الافتراضي origin/main)")
    parser.add_argument(
        "--exclude",
        action="append",
        dest="excludes",
        help="مسار مستثنى إضافي؛ كرر الخيار عند الحاجة",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = _resolve(args.target)
    issues: list[str] = []
    # Explicit exclusions add to the safe baseline; they must not silently
    # remove protections such as .git, secrets, state, or key files.
    excludes = [*DEFAULT_EXCLUDES, *(args.excludes or [])]

    if not target.is_dir():
        print("النتيجة: غير آمن (خرج 2)")
        print("السبب: الهدف ليس مجلدًا موجودًا.")
        print("اقتراح الحاجز: أوقف العملية وحدد هدفًا موجودًا وقابلًا للقراءة.")
        return 2

    git_root = _find_git_root(target)
    requested_repo = _resolve(args.repo) if args.repo else None
    if git_root is None:
        issues.append("لم يُعثر على جذر مستودع Git للهدف.")
        repo = requested_repo or target
    else:
        repo = git_root
        if requested_repo is not None and requested_repo != git_root:
            issues.append("--repo لا يطابق جذر Git المكتشف للهدف.")

    if git_root is not None and not _within(target, git_root):
        issues.append("الهدف خارج جذر المستودع.")

    if git_root is not None and target == git_root:
        target_kind = "جذر مستودع"
        issues.append("الهدف هو جذر المستودع؛ الحارس يرفض النطاق الواسع افتراضيًا.")
    else:
        target_kind = "مجلد فرعي"

    source = _resolve(args.source) if args.source else target
    if not source.is_dir():
        issues.append("المصدر ليس مجلدًا موجودًا.")
    if source == target:
        issues.append("المصدر والهدف متطابقان؛ لا تسمح بعملية استبدال ذاتية النطاق.")

    source_sensitive = _sensitive_paths(source, excludes)
    target_sensitive = _sensitive_paths(target, excludes)
    sensitive = sorted(set(source_sensitive + target_sensitive))
    excludes_inside = _exclude_inside_scope(target, source, excludes)
    if source_sensitive:
        issues.append("توجد مسارات حساسة/مستثناة داخل نطاق المصدر: " + ", ".join(source_sensitive))
    if target_sensitive:
        issues.append("توجد مسارات حساسة/مستثناة داخل نطاق الهدف: " + ", ".join(target_sensitive))
    if excludes_inside:
        issues.append("مسارات مستثناة معلنة داخل نطاق العملية: " + ", ".join(excludes_inside))

    branch = "غير معروف"
    upstream = "غير مضبوط"
    dirty = False
    if git_root is not None:
        code, branch_output, _ = _git(git_root, "symbolic-ref", "--short", "HEAD")
        if code == 0 and branch_output:
            branch = branch_output
        else:
            issues.append("المستودع في حالة detached HEAD أو تعذر قراءة الفرع الحالي.")
        code, upstream_output, _ = _git(git_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if code == 0 and upstream_output:
            upstream = upstream_output
        else:
            issues.append("لا يوجد تتبع upstream مضبوط للفرع الحالي.")
        if branch != args.expected_branch:
            issues.append(f"الفرع الحالي {branch!r} لا يطابق المتوقع {args.expected_branch!r}.")
        if upstream != args.expected_upstream:
            issues.append(f"تتبع الفرع {upstream!r} لا يطابق المتوقع {args.expected_upstream!r}.")
        status_code, status_output, _ = _git(git_root, "status", "--porcelain", "--untracked-files=normal")
        if status_code != 0:
            issues.append("تعذر قراءة حالة العمل.")
        elif status_output:
            dirty = True
            issues.append("شجرة العمل غير نظيفة؛ احفظ أو راجع التغييرات قبل العملية المدمرة.")

    print("فحص ما قبل العملية المدمرة (فشل مغلق)")
    print(f"الهدف: {target}")
    print(f"تصنيف الهدف: {target_kind}")
    print(f"جذر Git: {repo}")
    print(f"المصدر: {source}")
    print(f"المسارات الحساسة/المستثناة داخل النطاق: {', '.join(sensitive) if sensitive else 'لا توجد'}")
    print(f"التتبع: الفرع={branch} · upstream={upstream} · المتوقع={args.expected_branch}/{args.expected_upstream}")
    worktree_state = "غير نظيفة" if dirty else ("نظيفة" if git_root is not None else "غير قابلة للتحقق")
    print(f"شجرة العمل: {worktree_state}")

    if issues:
        print("النتيجة: غير آمن (خرج 2)")
        print("الأسباب:")
        for issue in issues:
            print(f"  - {issue}")
        print("اقتراح الحاجز: استخدم مجلدًا فرعيًا محددًا، افصل الأسرار و.git/state، صحّح upstream، ثم أعد الفحص قبل التنفيذ.")
        return 2

    print("النتيجة: آمن مبدئيًا (خرج 0؛ لا يغني عن خطة جافة ومراجعة بشرية).")
    print("اقتراح الحاجز: شغّل plan_diff.py مع سقف حذف وتجربة جافة، وسجّل قياس قبل/بعد.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
