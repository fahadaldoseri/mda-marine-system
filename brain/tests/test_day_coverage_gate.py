#!/usr/bin/env python3
"""اختبار موجبة/سالبة لحارس تغطية الأيام، باستخدام ملفات مؤقتة فقط."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_gate():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "check_day_coverage", root / "validators" / "check_day_coverage.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_day(root: Path, date: str, rows: list[dict]) -> None:
    daily = root / "cumulative-2026" / "daily"
    daily.mkdir(parents=True, exist_ok=True)
    appendices = root / "appendices"
    appendices.mkdir(parents=True, exist_ok=True)
    (appendices / "source-label-blacklist.json").write_text(
        json.dumps({"labels": ["وصف عام ممنوع"]}, ensure_ascii=False), encoding="utf-8"
    )
    (daily / f"{date}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


def material() -> dict:
    return {
        "code": "MN-2026-02-28-01",
        "source": "UKMTO",
        "evidence_ref": "feeds/2026-02-28#1",
        "retrieved_at": "2026-02-28T12:00:00Z",
    }


def no_incident() -> dict:
    return {
        "no_incident": True,
        "retrieved_at": "2026-02-28T12:00:00Z",
        "sources_checked": [{
            "source": "UKMTO",
            "url": "https://example.test/ukmto",
            "http_status": 200,
            "retrieved_at": "2026-02-28T12:00:00Z",
        }],
    }


def test_complete_material_or_no_incident_pass(tmp_path: Path) -> None:
    gate = load_gate()
    write_day(tmp_path, "2026-02-28", [material()])
    assert gate.check_coverage(tmp_path, start_date="2026-02-28") == []
    write_day(tmp_path, "2026-03-01", [no_incident()])
    assert gate.check_coverage(tmp_path, start_date="2026-02-28") == []


def test_missing_evidence_and_blocked_only_source_fail(tmp_path: Path) -> None:
    gate = load_gate()
    bad_material = material()
    bad_material.pop("evidence_ref")
    write_day(tmp_path, "2026-02-28", [bad_material])
    write_day(tmp_path, "2026-03-01", [{
        "no_incident": True,
        "retrieved_at": "2026-02-29T12:00:00Z",
        "sources_checked": [{
            "source": "UKMTO",
            "url": "https://example.test/ukmto",
            "http_status": 403,
            "retrieved_at": "2026-02-29T12:00:00Z",
            "status": "المصدر محجوب",
        }],
    }])
    errors = gate.check_coverage(tmp_path, start_date="2026-02-28")
    assert len(errors) >= 2
    assert any("evidence_ref" in error for error in errors)
    assert any("محجوب" in error for error in errors)


if __name__ == "__main__":
    raise SystemExit(0)


def write_gaps(root: Path, gaps: list[dict]) -> None:
    (root / "cumulative-2026").mkdir(parents=True, exist_ok=True)
    (root / "cumulative-2026" / "migration-gaps.json").write_text(
        json.dumps({"migration_gaps": gaps}, ensure_ascii=False), encoding="utf-8"
    )


def test_migration_gap_covers_missing_day(tmp_path: Path) -> None:
    gate = load_gate()
    write_day(tmp_path, "2026-02-28", [material()])
    write_day(tmp_path, "2026-03-02", [material()])
    assert any("2026-03-01" in e for e in gate.check_coverage(tmp_path, start_date="2026-02-28"))
    write_gaps(tmp_path, [{"from": "2026-03-01", "to": "2026-03-01",
                           "reason": "بيانات اليوم بقيت على الخادم القديم",
                           "decided_by": "owner", "decision_date": "2026-11-17"}])
    assert gate.check_coverage(tmp_path, start_date="2026-02-28") == []


def test_migration_gap_overlapping_file_fails(tmp_path: Path) -> None:
    gate = load_gate()
    write_day(tmp_path, "2026-02-28", [material()])
    write_gaps(tmp_path, [{"from": "2026-02-28", "to": "2026-02-28",
                           "reason": "سبب", "decided_by": "owner", "decision_date": "2026-11-17"}])
    assert any("فجوة نقل" in e for e in gate.check_coverage(tmp_path, start_date="2026-02-28"))
