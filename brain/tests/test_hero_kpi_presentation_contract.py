#!/usr/bin/env python3
"""حاجز عرض بطاقات hero_kpis: الكامل يُقبل والناقص/المخالف يُرفض."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from tools import build_hero_kpis
from validators.validate_report import check_schema

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-11-07"


def _load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _built_meta() -> dict:
    meta = _load(f"web/meta/{DATE}.json")
    zones = _load(f"web/zones/{DATE}.json")
    registry = _load("appendices/card_registry.json")
    kpis = _load(f"web/kpis-totals/{DATE}.json")
    result = copy.deepcopy(meta)
    result["hero_kpis"] = build_hero_kpis.build(meta, zones, registry, kpis)
    return result


def _hero_errors(meta: dict) -> list[str]:
    return [error for error in check_schema(meta) if "hero_kpis" in error]


def test_complete_hero_kpi_presentation_is_accepted():
    errors = _hero_errors(_built_meta())
    assert errors == [], errors


def test_missing_presentation_field_is_rejected():
    broken = _built_meta()
    broken["hero_kpis"][1].pop("label", None)
    broken["hero_kpis"][1].pop("note", None)
    broken["hero_kpis"][1].pop("accent", None)
    errors = _hero_errors(broken)
    assert any("hero_kpis[1] ينقصه label" in error for error in errors), errors
    assert any("hero_kpis[1] ينقصه note" in error for error in errors), errors
    assert any("hero_kpis[1] ينقصه accent" in error for error in errors), errors


def test_disallowed_accent_is_rejected():
    broken = _built_meta()
    broken["hero_kpis"][2]["accent"] = "neutral"
    errors = _hero_errors(broken)
    assert any("accent" in error and "neutral" in error for error in errors), errors


if __name__ == "__main__":
    test_complete_hero_kpi_presentation_is_accepted()
    test_missing_presentation_field_is_rejected()
    test_disallowed_accent_is_rejected()
    print("G012 presentation contract: GREEN")
