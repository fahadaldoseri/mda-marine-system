#!/usr/bin/env python3
"""اختبارات موجب وسالب للحارس المغلق لاستمرارية السجلات اليومية."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
VALIDATOR = B / "validators" / "check_ledger_continuity.py"


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(root), *args],
        text=True, capture_output=True, check=False,
    )


def source_row():
    return {
        "source_id": "imo_confirmed",
        "url": "file:///tmp/imo.md",
        "invoked": "قراءة ملف رسمي محفوظ",
        "result": "بلا مادة لهذا التاريخ",
        "retrieved_at": "2026-10-31T16:48:00Z",
    }


def make_root(tmp_path: Path, *, missing_day: bool = False, missing_sources: bool = False) -> Path:
    root = tmp_path / "brain"
    daily = root / "cumulative-2026" / "daily"
    daily.mkdir(parents=True)
    material = [{"date": "2026-02-28", "code": "TEST-2026-02-28", "title": "مادة"}]
    (daily / "2026-02-28.json").write_text(json.dumps(material, ensure_ascii=False), encoding="utf-8")
    if not missing_day:
        (daily / "2026-03-01.json").write_text(json.dumps([{
            "date": "2026-03-01", "code": "NI-2026-03-01", "class": "no_incident",
            "event_kind": "no_incident", "no_incident": True,
            "title": "لا واقعة مسجّلة في المصادر الرسمية المفحوصة",
            "description": "لا واقعة مسجّلة في المصادر الرسمية المفحوصة",
            "sources_checked": [] if missing_sources else [source_row()],
            "retrieved_at": "2026-10-31T16:48:00Z",
        }], ensure_ascii=False), encoding="utf-8")
    (daily / "2026-03-02.json").write_text(json.dumps([{
        "date": "2026-03-02", "code": "TEST-2026-03-02", "title": "مادة"
    }], ensure_ascii=False), encoding="utf-8")
    (root / "cumulative-2026" / "no-material.json").write_text(
        json.dumps({"no_material": []}, ensure_ascii=False), encoding="utf-8"
    )
    return root


def test_continuity_positive(tmp_path: Path) -> None:
    result = run(make_root(tmp_path), "--date", "2026-03-02")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "مكتملة" in result.stdout
    assert "no_incident موثق 1" in result.stdout


def test_continuity_negative_missing_day(tmp_path: Path) -> None:
    result = run(make_root(tmp_path, missing_day=True), "--date", "2026-03-02")
    assert result.returncode != 0
    assert "2026-03-01" in result.stdout


def test_continuity_negative_no_incident_without_sources(tmp_path: Path) -> None:
    result = run(make_root(tmp_path, missing_sources=True), "--date", "2026-03-02")
    assert result.returncode != 0
    assert "بلا قائمة مصادر مفحوصة" in result.stdout


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
