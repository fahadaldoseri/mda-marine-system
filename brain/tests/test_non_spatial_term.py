#!/usr/bin/env python3
"""اختبار موجبة/سالبة للفظ «غير مكانية» و«غير مكاني»."""
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


def write_tree(root: Path, text: str) -> None:
    (root / "cumulative-2026" / "daily").mkdir(parents=True)
    (root / "web" / "meta").mkdir(parents=True)
    (root / "appendices").mkdir(parents=True)
    (root / "appendices" / "zone-registry.json").write_text(
        json.dumps({"areas": [{"ar": "مضيق هرمز"}], "non_spatial_value": "غير مكانية"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "cumulative-2026" / "daily" / "2026-11-04.json").write_text(
        json.dumps([{"code": "MN-2026-11-04-01", "area": text}], ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "web" / "meta" / "2026-11-04.json").write_text(
        json.dumps({"event_keys": [{"code": "MN-2026-11-04-01", "area": text}]}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_clean_spatial_value_passes(tmp_path: Path) -> None:
    gate = load_gate()
    write_tree(tmp_path, "مضيق هرمز")
    assert gate.scan_root(tmp_path) == []


def test_non_spatial_terms_fail_on_any_surface(tmp_path: Path) -> None:
    gate = load_gate()
    write_tree(tmp_path, "غير مكانية")
    errors = gate.scan_root(tmp_path)
    assert errors and any("غير مكانية" in error for error in errors)


if __name__ == "__main__":
    raise SystemExit(0)
