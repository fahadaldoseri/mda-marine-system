#!/usr/bin/env python3
"""Restore commit-deleted paths one at a time, never rewriting branch history."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath


class GitError(RuntimeError):
    pass


def _git(repo: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        message = completed.stderr.decode("utf-8", "replace").strip()
        raise GitError(message or f"git exited {completed.returncode}")
    return completed


def _deleted_paths(repo: Path, revision: str) -> list[str]:
    completed = _git(
        repo,
        "diff",
        "--diff-filter=D",
        "--name-only",
        "-z",
        "--no-renames",
        revision,
        "HEAD",
        "--",
    )
    raw_paths = completed.stdout.split(b"\0")
    paths: list[str] = []
    for raw in raw_paths:
        if not raw:
            continue
        path = os.fsdecode(raw)
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts:
            raise GitError(f"git returned an unsafe path: {path!r}")
        paths.append(path)
    return paths


def _is_present(repo: Path, relative: str) -> bool:
    # lexists also protects a broken symlink from being mistaken for a missing file.
    return os.path.lexists(repo / Path(relative))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="استعد الملفات التي حذفها HEAD مقارنةً بالتزام سابق، ملفًا ملفًا وبلا إعادة كتابة تاريخ."
    )
    parser.add_argument("--repo", required=True, type=Path, help="مسار مستودع Git")
    parser.add_argument("--sha", default="HEAD~1", help="الالتزام السابق (الافتراضي HEAD~1)")
    parser.add_argument("--apply", action="store_true", help="نفّذ الاستعادة؛ بدونه تبقى العملية تجربة جافة")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        print("خطأ: --repo ليس مجلدًا موجودًا.", file=sys.stderr)
        return 2
    try:
        top_level = Path(_git(repo, "rev-parse", "--show-toplevel").stdout.decode().strip()).resolve()
        resolved_sha = _git(repo, "rev-parse", "--verify", f"{args.sha}^{{commit}}").stdout.decode().strip()
        deleted = _deleted_paths(repo, resolved_sha)
    except GitError as exc:
        print(f"خطأ Git: {exc}", file=sys.stderr)
        return 2

    if top_level != repo:
        # Keep paths and command scope unambiguous: --repo must be the worktree root.
        print("خطأ: يجب تمرير جذر مستودع Git إلى --repo، لا مجلدًا فرعيًا.", file=sys.stderr)
        return 2

    to_restore = [path for path in deleted if not _is_present(repo, path)]
    before_missing = len(to_restore)
    print(f"المستودع: {repo}")
    print(f"المصدر: {resolved_sha}")
    print(f"عدد الملفات المحذوفة المرشحة للاستعادة: {len(deleted)}")
    print(f"عدد الملفات الغائبة الآن التي ستُستعاد: {before_missing}")
    if to_restore:
        print("المسارات المرشحة:")
        for path in to_restore:
            print(f"  - {path}")

    if not args.apply:
        print("الوضع: تجربة جافة؛ لم تُنفذ الاستعادة.")
        print(f"التحقق قبل/بعد (لم يُنفذ): {before_missing}/{before_missing} ملفًا غائبًا.")
        print("اقتراح الحاجز: راجع القائمة ثم استخدم --apply فقط بعد التأكد من SHA والمسارات.")
        return 0

    failures: list[str] = []
    restored = 0
    for path in to_restore:
        completed = _git(repo, "checkout", resolved_sha, "--", path, check=False)
        if completed.returncode != 0:
            failures.append(path)
            detail = completed.stderr.decode("utf-8", "replace").strip()
            print(f"فشل استعادة مسار واحد: {path} ({detail})", file=sys.stderr)
            continue
        restored += 1

    after_missing = sum(1 for path in to_restore if not _is_present(repo, path))
    print(f"الوضع: طُبّقت الاستعادة الآمنة على {restored} ملفًا.")
    print(f"التحقق بعد/قبل: قبل={before_missing} · بعد={after_missing} ملفًا غائبًا.")
    print("ملاحظة: لم يُنفذ reset أو force-push أو commit تلقائي.")
    print("اقتراح الحاجز: راجع git diff وgit status، ثم سجّل الدرس والحاجز قبل أي commit لاحق.")

    if failures or after_missing:
        print(f"القرار: غير مكتمل (خرج 2؛ فشل {len(failures)}، وبقي غائبًا {after_missing}).")
        return 2
    print("القرار: تمت الاستعادة والتحقق (خرج 0).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
