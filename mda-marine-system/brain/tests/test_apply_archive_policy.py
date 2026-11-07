#!/usr/bin/env python3
"""حارس أرشيفات apply: لا تُتبع في المرآة ولا تُعاد مزامنتها، ولا تُؤرشف skills."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT.parent), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [p.decode("utf-8") for p in result.stdout.split(b"\0") if p]


def test_no_apply_archive_path_is_tracked() -> None:
    offenders = [
        p for p in tracked_paths()
        if any(part.startswith("apply-") for part in Path(p).parts)
    ]
    assert not offenders, "أرشيفات apply متتبعة في المرآة:\n" + "\n".join(offenders)


def test_archive_and_sync_guards_are_explicit() -> None:
    backup = (ROOT / "tools" / "github_backup.py").read_text(encoding="utf-8")
    sync = (ROOT / "tools" / "sync_to_repo.py").read_text(encoding="utf-8")
    apply = (ROOT / "tools" / "apply_from_github.py").read_text(encoding="utf-8")
    assert '"logs/apply-*"' in backup
    assert "logs/apply-*" in sync
    assert "ARCHIVE_EXCLUDE_TOPS = {\"skills\"}" in apply
    assert "archiveable" in apply


if __name__ == "__main__":
    test_no_apply_archive_path_is_tracked()
    test_archive_and_sync_guards_are_explicit()
    print("apply-archive policy: 2/2")
