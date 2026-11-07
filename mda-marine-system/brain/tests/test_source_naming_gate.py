#!/usr/bin/env python3
"""اختبار موجبة/سالبة لحارس أسماء المصادر، باستخدام شجرة مؤقتة فقط."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_gate():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "check_source_naming", root / "validators" / "check_source_naming.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_tree(root: Path, *, source: str, meta_source: str, report_source: str) -> None:
    (root / "cumulative-2026" / "daily").mkdir(parents=True)
    (root / "web" / "meta").mkdir(parents=True)
    (root / "reports").mkdir(parents=True)
    (root / "appendices").mkdir(parents=True)
    (root / "appendices" / "source-label-blacklist.json").write_text(
        json.dumps({"labels": ["وصف عام ممنوع"]}, ensure_ascii=False), encoding="utf-8"
    )
    (root / "cumulative-2026" / "daily" / "2026-02-28.json").write_text(
        json.dumps([{"code": "MN-2026-02-28-01", "source": source}], ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "web" / "meta" / "2026-02-28.json").write_text(
        json.dumps({"event_keys": [{"code": "MN-2026-02-28-01", "source": meta_source}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "reports" / "2026-02-28-sectioned.md").write_text(
        f"**المصدر:** {report_source}\n", encoding="utf-8"
    )


def test_clean_source_names_pass(tmp_path: Path) -> None:
    gate = load_gate()
    write_tree(tmp_path, source="UKMTO", meta_source="IMO", report_source="UKMTO — التحذير 1")
    assert gate.scan_root(tmp_path) == []


def test_blacklisted_source_label_fails_closed(tmp_path: Path) -> None:
    gate = load_gate()
    write_tree(tmp_path, source="وصف عام ممنوع", meta_source="IMO", report_source="UKMTO")
    errors = gate.scan_root(tmp_path)
    assert errors and any("وصف عام ممنوع" in error for error in errors)


def test_daily_narrative_surfaces_use_registered_source_names() -> None:
    root = Path(__file__).resolve().parents[1]
    daily = json.loads(
        (root / "cumulative-2026" / "daily" / "2026-11-07.json").read_text(encoding="utf-8")
    )
    event = next(row for row in daily if row.get("code") == "MN-2026-11-07-02")
    names = [item["name"] for item in event["sources"]]
    report = (root / "reports" / "2026-11-07-sectioned.md").read_text(encoding="utf-8")
    meta = json.loads((root / "web" / "meta" / "2026-11-07.json").read_text(encoding="utf-8"))
    report_line = next(line for line in report.splitlines() if line.startswith("- روايات الناقلات؛"))
    meta_line = meta["intel_analysis"]["indicators"][1]
    labels = json.loads(
        (root / "appendices" / "source-label-blacklist.json").read_text(encoding="utf-8")
    )["labels"]
    for name in names:
        assert name in report_line
        assert name in meta_line
    for label in labels:
        assert label not in report_line
        assert label not in meta_line


if __name__ == "__main__":
    raise SystemExit(0)
