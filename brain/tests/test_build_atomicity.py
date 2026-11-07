#!/usr/bin/env python3
"""اختبارات منع عيب البناء: بصمة ذرية وقفل single-flight."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_lock import BuildLock, BuildLockBusy  # noqa: E402
from build_transaction import run_atomic  # noqa: E402


def _fixture(tmp_path: Path):
    brain = tmp_path / "brain"
    site = tmp_path / "site"
    (brain / "reports").mkdir(parents=True)
    (brain / "logs").mkdir()
    (site / "dist" / "reports").mkdir(parents=True)
    date = "2026-11-07"
    report = brain / "reports" / f"{date}-sectioned.md"
    report.write_text("النص النهائي\n", encoding="utf-8")
    return brain, site, date, report


def test_atomic_build_rejects_text_changed_after_hash_record(tmp_path: Path):
    brain, site, date, report = _fixture(tmp_path)

    def build_from_stale_input():
        (site / "dist" / "reports" / f"{date}.html").write_text(
            "<html>built</html>", encoding="utf-8"
        )
        report.write_text("النص تغيّر بعد تسجيل البصمة\n", encoding="utf-8")
        return 0

    result = run_atomic(brain, site, date, build_fn=build_from_stale_input)

    assert result.returncode != 0
    assert "نص التقرير تغيّر بعد تسجيل البصمة" in result.output


def test_second_build_is_rejected_while_first_holds_lock(tmp_path: Path):
    lock_path = tmp_path / "build.lock"
    first = BuildLock(lock_path, stale_after=60)
    first.acquire()
    try:
        second = BuildLock(lock_path, stale_after=60)
        with pytest.raises(BuildLockBusy, match="بناء جارٍ"):
            second.acquire(timeout=0)
    finally:
        first.release()


def test_lock_reclaims_dead_owner_after_timeout(tmp_path: Path):
    lock_path = tmp_path / "build.lock"
    lock_path.mkdir()
    (lock_path / "owner.json").write_text(
        '{"pid": 99999999, "started_utc": "2000-01-01T00:00:00Z"}',
        encoding="utf-8",
    )
    lock = BuildLock(lock_path, stale_after=0)
    lock.acquire(timeout=0)
    lock.release()
