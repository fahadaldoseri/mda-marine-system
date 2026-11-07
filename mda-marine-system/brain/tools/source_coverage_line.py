#!/usr/bin/env python3
"""احسب سطر تغطية محاولات التغذية من ملفات المصدر الفعلية.

العد الظاهر هو عدّ صفوف المحاولات في feeds JSON (78/81 في الجولة الحالية)،
بينما يتحقق السكربت أيضًا من عدّ المصدر الفريد في status JSON. لا يكتب الواجهة
إذا وُجد رقم في الحالة بلا صف مطابق في ملف التغذية.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class CoverageError(ValueError):
    """مانع فشل مغلق عند غياب سند أو عدم اتساق عدادات المصدر."""


def _num(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CoverageError(f"{label} ليس رقمًا صحيحًا: {value!r}")
    return value


def _reason(row: dict[str, Any], status_failed: dict[int, dict[str, Any]]) -> str:
    reason = row.get("block_reason") or row.get("error")
    if reason:
        return str(reason)
    item = status_failed.get(_num(row.get("num"), "num"), {})
    return str(item.get("block_reason") or item.get("error") or "سبب الحجب غير مسجل")


def build_coverage(root: Path, date: str) -> dict[str, Any]:
    feeds_path = root / "feeds" / f"feeds-{date}.json"
    status_path = root / "feeds" / f"feeds-{date}.status.json"
    try:
        feed_rows = json.loads(feeds_path.read_text(encoding="utf-8"))
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageError(f"تعذّرت قراءة ملفات التغطية: {exc}") from exc
    if not isinstance(feed_rows, list) or not feed_rows:
        raise CoverageError("ملف التغذية يجب أن يكون قائمة غير فارغة")
    if not isinstance(status, dict):
        raise CoverageError("ملف حالة التغذية يجب أن يكون كائنًا")

    feed_nums: list[int] = []
    false_rows: list[dict[str, Any]] = []
    successful_rows = 0
    for row in feed_rows:
        if not isinstance(row, dict) or "num" not in row or "name" not in row or not isinstance(row.get("ok"), bool):
            raise CoverageError("كل صف في feeds يحتاج num وname وok منطقيًا")
        num = _num(row["num"], "feeds.num")
        feed_nums.append(num)
        if row["ok"]:
            successful_rows += 1
        else:
            false_rows.append(row)
    feed_num_set = set(feed_nums)

    checked_rows = status.get("checked_feeds", [])
    if not isinstance(checked_rows, list):
        raise CoverageError("checked_feeds ليس قائمة")
    checked_nums = set()
    for row in checked_rows:
        if not isinstance(row, dict) or "num" not in row:
            raise CoverageError("صف checked_feeds بلا رقم")
        num = _num(row["num"], "checked_feeds.num")
        checked_nums.add(num)
        if num not in feed_num_set:
            raise CoverageError(f"رقم الحالة بلا سند في ملف التغذية: {num}")

    by_num_success: dict[int, bool] = {}
    for row in checked_rows:
        num = _num(row["num"], "checked_feeds.num")
        by_num_success[num] = by_num_success.get(num, False) or bool(row.get("ok"))
    unique_ok = {num for num, ok in by_num_success.items() if ok}
    unique_failed = set(by_num_success) - unique_ok
    for field, expected in (("checked", len(checked_nums)), ("ok", len(unique_ok)), ("failed", len(unique_failed))):
        actual = _num(status.get(field), f"status.{field}")
        if actual != expected:
            raise CoverageError(f"status.{field}={actual} لا يساوي الدليل المحسوب {expected}")

    failed_attempts = status.get("failed_attempts", [])
    if not isinstance(failed_attempts, list):
        raise CoverageError("failed_attempts ليس قائمة")
    failed_by_num: dict[int, dict[str, Any]] = {}
    for item in failed_attempts:
        if not isinstance(item, dict) or "num" not in item:
            raise CoverageError("محاولة فاشلة بلا رقم")
        num = _num(item["num"], "failed_attempts.num")
        if num not in feed_num_set:
            raise CoverageError(f"رقم المحاولة الفاشلة بلا سند في ملف التغذية: {num}")
        failed_by_num[num] = item
    false_nums = {_num(row["num"], "feeds.num") for row in false_rows}
    if not set(failed_by_num).issubset(false_nums):
        missing = sorted(set(failed_by_num) - false_nums)
        raise CoverageError(f"failed_attempts بلا صف فاشل مطابق في feeds: {missing}")

    blocked = [
        {
            "num": _num(row["num"], "feeds.num"),
            "name": str(row["name"]),
            "reason": _reason(row, failed_by_num),
        }
        for row in false_rows
    ]
    base_line = f"فحص المصادر: {successful_rows} ناجحًا من {len(feed_rows)} · {len(false_rows)} محجوبة"
    detail = "؛ ".join(f"{item['name']} — {item['reason']}" for item in blocked)
    display_line = f"{base_line} · المحجوبة: {detail}" if detail else base_line
    return {
        "line": base_line,
        "display_line": display_line,
        "attempted": len(feed_rows),
        "successful": successful_rows,
        "blocked_count": len(false_rows),
        "blocked": blocked,
        "basis": {
            "feeds": str(feeds_path.relative_to(root)),
            "status": str(status_path.relative_to(root)),
            "unique_checked": len(checked_nums),
            "unique_successful": len(unique_ok),
            "unique_failed": len(unique_failed),
        },
    }


def write_meta(root: Path, date: str, coverage: dict[str, Any]) -> None:
    path = root / "web" / "meta" / f"{date}.json"
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageError(f"تعذّرت قراءة واجهة اليوم: {exc}") from exc
    if not isinstance(meta, dict):
        raise CoverageError("واجهة اليوم ليست كائن JSON")
    meta["source_coverage"] = coverage
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    parser.add_argument("--brain", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true", help="اكتب source_coverage في web/meta")
    args = parser.parse_args(argv)
    try:
        coverage = build_coverage(args.brain.resolve(), args.date)
        if args.write:
            write_meta(args.brain.resolve(), args.date, coverage)
        print(coverage["display_line"])
        return 0
    except (CoverageError, OSError) as exc:
        print(f"فشل سطر تغطية المصادر: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
