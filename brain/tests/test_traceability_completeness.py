#!/usr/bin/env python3
"""حاجز G048: لا يجوز أن تتأخر مصفوفة التتبع عن سجل الأعطال."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAULT_ID = re.compile(r"^\|\s*([كزعثم]-\d+(?:/[بجدهوزحطيكلمنصعقفرستثخ]+)?)\s*\|")
LEGAL_STATES = {"مغلق", "مفتوح", "بانتظار التحقق", "موروث غير مثبت", "أعيد فتحه"}


def audit_fault_ids() -> list[str]:
    audit = ROOT / "audit" / "سجل-الأعطال-والثغرات.md"
    return [m.group(1) for line in audit.read_text(encoding="utf-8").splitlines() if (m := FAULT_ID.match(line))]


def traceability_rows() -> list[dict]:
    trace = ROOT / "audit" / "traceability.json"
    return json.loads(trace.read_text(encoding="utf-8")).get("rows", [])


def test_traceability_covers_every_fault_once() -> None:
    faults = audit_fault_ids()
    rows = traceability_rows()
    trace_ids = [row.get("fault_id") for row in rows]
    assert faults, "سجل الأعطال فارغ"
    assert len(faults) == len(set(faults)), "معرّف عطل مكرر في سجل الأعطال"
    assert len(trace_ids) == len(set(trace_ids)), "معرّف عطل مكرر في مصفوفة التتبع"
    assert set(trace_ids) == set(faults), (
        "مصفوفة التتبع لا تطابق سجل الأعطال: "
        f"مفقود={sorted(set(faults) - set(trace_ids))} "
        f"زائد={sorted(set(trace_ids) - set(faults))}"
    )


def test_traceability_states_are_legal() -> None:
    rows = traceability_rows()
    bad = [(row.get("fault_id"), row.get("state")) for row in rows if row.get("state") not in LEGAL_STATES]
    assert not bad, f"حالات تشغيلية غير قانونية في المصفوفة: {bad}"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
