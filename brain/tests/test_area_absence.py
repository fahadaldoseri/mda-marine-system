#!/usr/bin/env python3
"""اختبار موجبة/سالبة لغياب area مع area_basis، باستخدام شجرة مؤقتة."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_gate():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "check_area_vocabulary", root / "validators" / "check_area_vocabulary.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_schema_gate():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "check_daily_events_schema", root / "validators" / "check_daily_events_schema.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_day(root: Path, row: dict) -> None:
    daily = root / "cumulative-2026" / "daily"
    daily.mkdir(parents=True, exist_ok=True)
    appendices = root / "appendices"
    appendices.mkdir(parents=True, exist_ok=True)
    (appendices / "zone-registry.json").write_text(
        json.dumps({"areas": [{"ar": "مضيق هرمز"}], "non_spatial_value": "غير مكانية"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (daily / "2026-11-04.json").write_text(json.dumps([row], ensure_ascii=False), encoding="utf-8")


def row(**changes) -> dict:
    value = {"code": "MN-2026-11-04-01", "area": "مضيق هرمز"}
    value.update(changes)
    return value


def test_area_can_be_absent_with_nonempty_basis(tmp_path: Path) -> None:
    gate = load_gate()
    write_day(tmp_path, row(area="", area_basis="المصدر لا يحدد موقع الواقعة"))
    assert gate.scan_root(tmp_path) == []


def test_area_absence_without_basis_fails_closed(tmp_path: Path) -> None:
    gate = load_gate()
    write_day(tmp_path, row(area="", area_basis=""))
    errors = gate.scan_root(tmp_path)
    assert errors and any("area_basis" in error for error in errors)


def schema_row(**changes) -> dict:
    value = {
        "code": "MN-2026-11-04-01",
        "date": "2026-11-04",
        "title": "تحذير بحري",
        "source": "UKMTO",
        "class": "بلاغ رسمي",
        "confidence": "متوسطة",
        "evidence_ref": "feeds/2026-11-04#1",
        "retrieved_at": "2026-11-04T12:00:00Z",
        "source_excerpt": "نص أصلي",
        "source_excerpt_from": "feeds/2026-11-04.json#1",
        "area": "مضيق هرمز",
    }
    value.update(changes)
    return value


def test_schema_accepts_missing_area_with_basis(tmp_path: Path) -> None:
    schema_gate = load_schema_gate()
    row_value = schema_row(area="", area_basis="المصدر لا يحدد موقع الواقعة")
    write_day(tmp_path, row_value)
    loaded = json.loads((tmp_path / "cumulative-2026" / "daily" / "2026-11-04.json").read_text(encoding="utf-8"))
    assert schema_gate.violations(loaded, date_label="2026-11-04") == []


def test_schema_rejects_missing_area_basis(tmp_path: Path) -> None:
    schema_gate = load_schema_gate()
    row_value = schema_row(area="", area_basis="")
    write_day(tmp_path, row_value)
    loaded = json.loads((tmp_path / "cumulative-2026" / "daily" / "2026-11-04.json").read_text(encoding="utf-8"))
    errors = schema_gate.violations(loaded, date_label="2026-11-04")
    assert errors and any("area" in error for error in errors)


if __name__ == "__main__":
    raise SystemExit(0)
