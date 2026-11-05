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


def _status_reasons(brain: Path, date: str, numbers: list[int]) -> dict[int, str]:
    """أسباب فشل المصادر المعطّلة كما سُجّلت في ملف حالة الفحص (دليل القياس)."""
    path = brain / "feeds" / f"feeds-{date}.status.json"
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    wanted = {int(n) for n in numbers}
    out: dict[int, str] = {}
    for row in status.get("checked_feeds", []):
        try:
            num = int(row.get("num"))
        except (TypeError, ValueError):
            continue
        if num not in wanted or row.get("ok"):
            continue
        reason = str(row.get("block_reason") or row.get("error") or "")
        out[num] = (out.get(num, "") + " " + reason).strip()
    return out


def _declared_transient(brain: Path, date: str, disabled: list[dict[str, Any]]) -> tuple[bool, str, str]:
    """هل يغطّي إعلان عطل عابر مُهَل في known-faults المصادرَ المعطّلة اليوم؟

    الشرط مغلق: يلزم إعلان سارٍ غير منتهٍ، وعدده الأقصى لا يقلّ عن عدد المعطّل،
    وأن يطابق سبب كل مصدر معطّل أحد أنماط الإعلان. أي نقص في ذلك يُبقي المنع.
    """
    if not disabled:
        return True, "", ""
    path = brain / "appendices" / "known-faults.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, "", f"تعذّر قراءة إعلانات الأعطال المعروفة: {type(exc).__name__}"
    allowed = data.get("allowed") or []
    numbers = [int(row.get("num")) for row in disabled if str(row.get("num", "")).isdigit()]
    reasons_by_num = _status_reasons(brain, date, numbers)
    if any(num not in reasons_by_num for num in numbers):
        # بلا سبب مقيس في ملف الحالة لا يوجد دليل عطل عابر ⇒ يبقى المنع.
        return False, "", ""
    reasons = [reasons_by_num[num].lower() for num in numbers]
    for entry in allowed:
        if "feeds" not in (entry.get("applies_to") or []):
            continue
        if str(entry.get("expires") or "") < date:
            continue
        if int(entry.get("max_items") or 0) < len(disabled):
            continue
        patterns = [str(p).lower() for p in (entry.get("reason_patterns") or [])]
        if not patterns or not all(any(p in r for p in patterns) for r in reasons):
            continue
        return True, str(entry.get("reason_ar_full") or entry.get("reason_ar") or ""), ""
    return False, "", ""


def validate(result: dict[str, Any], brain: Path | None = None, date: str = "") -> list[str]:
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
    disabled = [
        row for row in sources
        if isinstance(row, dict) and row.get("route_state") == "معطّل" and not row.get("manual")
    ]
    bad_rows = [row for row in sources if not isinstance(row, dict)]
    if bad_rows:
        problems.append("سجل مصدر غير كائن")
    if disabled:
        if brain is None or not date:
            problems.append(
                "مصدر آلي معطّل أو بلا مسار معلن: " + ", ".join(str(r.get("num")) for r in disabled)
            )
        else:
            covered, reason, error = _declared_transient(brain, date, disabled)
            if error:
                problems.append(error)
            elif not covered:
                problems.append(
                    "مصدر آلي معطّل أو بلا مسار معلن بلا إعلان عطل سارٍ: "
                    + ", ".join(str(r.get("num")) for r in disabled)
                )
            else:
                result["disclosed_transient"] = {
                    "count": len(disabled),
                    "numbers": [r.get("num") for r in disabled],
                    "reason": reason,
                }
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
        problems = validate(result, brain, args.date)
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
            disclosed = result.get("disclosed_transient") or {}
            if disclosed:
                print(
                    "  ◻ تشغيل منقوص مُفصح: "
                    f"{disclosed.get('count')} مصدرًا ({', '.join(str(n) for n in disclosed.get('numbers', []))}) — "
                    f"{disclosed.get('reason')}"
                )
            print("  ✔ فُحص كل مصدر مسجّل أو أُعلن صراحةً مرجعية يدوية؛ لا توجد فجوة صامتة")
    return 2 if problems else 0


if __name__ == "__main__":
    import sys as _sys, pathlib as _pl
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
