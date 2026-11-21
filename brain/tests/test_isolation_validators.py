#!/usr/bin/env python3
"""مدققات B010 تحترم عزل النسخة الإنجليزية (اختبار العطل المصطنع، 21 نوفمبر 2026).

القياس: بعد AH-C1 فشلت إعادة B010 بـ«ملف مطلوب مفقود: dist/reports/en/D.html» لأن
check_card_counters وcheck_kpi_layers وcheck_map_note_counts تطلب الصفحة الإنجليزية التي
لا تُبنى عمدًا. الحارس: العزل يُقرأ من حالة الإصلاح الذاتي، والحالة التالفة = لا عزل.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from auto_heal import en_isolated_safe  # noqa: E402

DATE = "2099-01-01"
STATE = ROOT / "logs" / "auto-heal" / f"{DATE}.json"
FAIL = []


def check(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAIL.append(msg)


def mod(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


made_dir = not STATE.parent.exists()
try:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    check(en_isolated_safe(ROOT, DATE) is False, "بلا حالة: لا عزل")
    STATE.write_text(json.dumps({"date": DATE, "isolated": {"en": {"rule": "AH-C1"}}, "holds": []}),
                     encoding="utf-8")
    check(en_isolated_safe(ROOT, DATE) is True, "حالة عزل صالحة: معزول")
    for rel in ("validators/check_card_counters.py", "validators/check_kpi_layers.py",
                "validators/check_map_note_counts.py"):
        check(mod(rel)._en_isolated(DATE) is True, f"{Path(rel).stem} يقرأ العزل")
    STATE.write_text("{تالف", encoding="utf-8")
    check(en_isolated_safe(ROOT, DATE) is False, "حالة تالفة: لا عزل (فشل مغلق)")
finally:
    STATE.unlink(missing_ok=True)
    if made_dir:
        shutil.rmtree(STATE.parent, ignore_errors=True)
if FAIL:
    raise SystemExit(1)
print("  ✔ المدققات تحترم العزل")
