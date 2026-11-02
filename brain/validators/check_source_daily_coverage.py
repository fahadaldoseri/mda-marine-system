#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة فحص اتحاد المصادر في التشغيل اليومي.

تمنع البوابة الإغلاق الكاذب عندما يُحذف مصدر من التشغيل: يجب أن يساوي اتحاد
المصادر الظاهرة في checked_feeds والمرجعية اليدوية سجل المصادر الحاكم كاملًا.
لا تشترط البوابة أن ينتج كل مصدر واقعة؛ «لا مستجد» حالة مقيسة وليست إسقاطًا.

الاستخدام:
  python3 validators/check_source_daily_coverage.py --brain /path/to/brain \
      --date 2026-11-01 --days 30 --json-out logs/...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any



def _load_measure_module(brain: Path):
    tools = str(brain / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import measure_source_ledger_coverage as measure  # type: ignore
    return measure


def validate(result: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    approved = int(result.get("approved_source_count", -1))
    checked = int(result.get("checked_union_manual_count", -1))
    missing = list(result.get("checked_missing_sources", []))
    unknown = list(result.get("checked_unknown_sources", []))
    manual = {int(x) for x in result.get("manual_reference", [])}
    status_manual = {int(x) for x in result.get("status_manual_reference", [])}
    manual_reasons = {int(x) for x in result.get("manual_reference_reasons", {})}
    sources = result.get("sources", [])
    source_numbers = {int(x.get("num")) for x in sources if isinstance(x, dict) and "num" in x}
    if approved != 62:
        problems.append(f"السجل الحاكم لا يساوي 62: {approved}")
    if source_numbers != set(range(1, approved + 1)):
        problems.append(f"أرقام السجل الحاكم ليست 1..{approved}: {sorted(source_numbers)}")
    if checked != approved:
        problems.append(f"اتحاد checked_feeds واليدوي لا يغطي السجل: {checked}/{approved}")
    if missing:
        problems.append(f"مصادر مسجّلة لم تُفحص ولم تُعلن يدويًا: {sorted(missing)}")
    if unknown:
        problems.append(f"أرقام في ملف الحالة وليست في السجل الحاكم: {sorted(unknown)}")
    if status_manual != manual:
        problems.append(f"manual_reference في الحالة لا يطابق القنوات: {sorted(status_manual)} != {sorted(manual)}")
    if manual_reasons != manual:
        problems.append(f"سبب المرجعية اليدوية ناقص/زائد: {sorted(manual_reasons)} != {sorted(manual)}")
    if int(result.get("checked_declared", result.get("status_declared_checked", -1))) != int(result.get("checked_unique_count", -2)):
        problems.append(
            "عداد checked في ملف الحالة لا يساوي عدد المصادر الفريد المفحوص: "
            f"{result.get('status_declared_checked')} != {result.get('checked_unique_count')}"
        )
    for row in sources:
        if not isinstance(row, dict):
            problems.append("سجل مصدر غير كائن")
            continue
        if row.get("route_state") == "معطّل" and not row.get("manual"):
            problems.append(f"مصدر آلي معطّل أو بلا مسار معلن: {row.get('num')}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--json-out")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    brain = Path(args.brain).resolve()
    try:
        measure = _load_measure_module(brain)
        result = measure.measure(brain, args.date, args.days)
        # The measurement result uses this explicit name in its public JSON.
        result["checked_declared"] = result.get("status_declared_checked")
        problems = validate(result)
    except (OSError, ValueError, KeyError, ImportError, json.JSONDecodeError) as exc:
        result = {"date": args.date, "error": f"{type(exc).__name__}: {exc}"}
        problems = [result["error"]]
    result["gate"] = "check_source_daily_coverage"
    result["problems"] = problems
    result["exit_code"] = 2 if problems else 0
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.quiet:
        print(f"بوابة تغطية فحص المصادر — {args.date} — الفترة {result.get('period_start', '?')} إلى {result.get('period_end', '?')}")
        print(
            f"  السجل الحاكم: {result.get('approved_source_count', '?')} · "
            f"checked_feeds الفريد: {result.get('checked_unique_count', '?')} · "
            f"يدوي: {result.get('manual_reference_count', '?')} · "
            f"الاتحاد: {result.get('checked_union_manual_count', '?')}"
        )
        print(
            f"  وصول إلى الدفتر: {result.get('sources_reaching_ledger_count', '?')} مصدرًا · "
            f"بلا واقعة: {result.get('sources_without_ledger_events_count', '?')} مصدرًا"
        )
        if problems:
            for problem in problems:
                print(f"  ✘ {problem}")
        else:
            print("  ✔ فُحص كل مصدر مسجّل أو أُعلن صراحةً مرجعية يدوية؛ لا توجد فجوة صامتة")
    return 2 if problems else 0


if __name__ == "__main__":
    import sys as _sys, pathlib as _pl
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
