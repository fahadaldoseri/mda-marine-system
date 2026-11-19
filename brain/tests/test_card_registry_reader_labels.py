#!/usr/bin/env python3
"""حارس تسميات مصدر البطاقات (2026-11-19).

العطل المقيس: نقل بطاقتي UKMTO والروايات إلى العدّاد الحاكم جعل `source_label`
مسار ملف «web/kpis-totals/...»، فرفض `validate_report.py` (ف4.8) واجهتي 12 و18
بعبارة داخلية «kpis»، ولم يلتقطه run_checks ولا CI لأن المدقق لا يُشغَّل على العقد نفسه.
الحالة الموجبة: كل تسمية مصدر في العقدين خالية من العبارات الداخلية لقائمة المدقق نفسها.
الحالة السالبة: تسمية فيها «kpis» تُكشف.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "validators"))
import validate_report as V  # noqa: E402

REGISTRIES = [ROOT / "appendices" / "card_registry.json"]
_site = ROOT.parent / "site" / "sources" / "card_registry.json"
if _site.is_file():
    REGISTRIES.append(_site)


def _labels(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("source_label") and isinstance(v, str):
                yield f"{path}/{k}", v
            else:
                yield from _labels(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _labels(v, f"{path}[{i}]")


def _offenders(registry: dict) -> list[str]:
    return [f"{p}: «{t}»" for p, s in _labels(registry) for t in V.INTERNAL if t in s]


def test_registry_labels_are_reader_clean() -> None:
    for reg in REGISTRIES:
        bad = _offenders(json.loads(reg.read_text(encoding="utf-8")))
        assert not bad, f"{reg}: {bad}"


def test_internal_label_is_caught() -> None:
    reg = {"hero_kpis": {"cards": [{"source_label": "web/kpis-totals/{date}.json · x"}]}}
    assert _offenders(reg)


if __name__ == "__main__":
    test_registry_labels_are_reader_clean()
    test_internal_label_is_caught()
    print("✔ تسميات مصدر البطاقات خالية من العبارات الداخلية")
