#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار عقد السطوح المؤجلة في G045."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "audit_style_coverage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_style_coverage", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"تعذّر تحميل بوابة التغطية: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_telegram_is_deferred_only_when_manifest_places_producer_after_gate():
    module = load_module()
    manifest = {
        "steps": [
            {"id": "G045", "deferred_surfaces": [{
                "label": "رسالة تلغرام", "producer": "D030",
                "reason": "اختياري ولاحق", "effective_from": "2026-11-06",
            }]},
            {"id": "D030", "title": "إرسال الملخص وPDF على تلغرام"},
        ]
    }
    deferred = module.deferred_producer_ids(manifest, "G045")
    assert deferred["D030"]["producer_index"] > deferred["D030"]["gate_index"]

    reordered = {"steps": [manifest["steps"][1], manifest["steps"][0]]}
    assert module.deferred_producer_ids(reordered, "G045") == {}


if __name__ == "__main__":
    test_telegram_is_deferred_only_when_manifest_places_producer_after_gate()
    print("اختبار ترتيب سطح Telegram: نجاح")
