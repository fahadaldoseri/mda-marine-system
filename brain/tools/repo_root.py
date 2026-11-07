#!/usr/bin/env python3
"""اشتقاق جذر Git من القياس الفعلي، لا من اسم المجلد."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


class RepoRootError(RuntimeError):
    """فشل مغلق عند غياب جذر Git أو اكتشاف شجرة مضاعفة."""


def duplicate_tree(repo: Path) -> Path | None:
    """يعثر على نسخة repo/repo.name التي تحمل شجرة brain مضاعفة."""
    candidate = repo / repo.name
    if candidate.is_dir() and (candidate / "brain").is_dir():
        return candidate.resolve()
    return None


def find_git_root(start: Path, *, reject_duplicate: bool = False) -> Path:
    """يصعد من start ويعيد الجذر الذي يثبته git rev-parse.

    لا يوجد fallback بالاسم. قائمة المسارات المفحوصة تدخل رسالة الفشل
    حتى لا يتحول خطأ المسار إلى تخمين صامت.
    """
    start = start.expanduser().resolve()
    candidates = [start, *start.parents]
    checked: list[str] = []
    for candidate in candidates:
        checked.append(str(candidate))
        try:
            result = subprocess.run(
                ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            result = None
        if result is None or result.returncode != 0:
            continue
        raw = (result.stdout or "").strip()
        if not raw:
            continue
        repo = Path(raw).resolve()
        if reject_duplicate:
            duplicate = duplicate_tree(repo)
            if duplicate:
                raise RepoRootError(
                    f"شجرة مضاعفة تحت الجذر المقيس {repo}: {duplicate}"
                )
        return repo
    raise RepoRootError(
        "لا جذر Git في المسارات المفحوصة: " + " · ".join(checked)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=".")
    parser.add_argument("--reject-duplicate", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(find_git_root(Path(args.start), reject_duplicate=args.reject_duplicate))
    except RepoRootError as exc:
        print(f"✘ فشل مغلق: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
