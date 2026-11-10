#!/usr/bin/env python3
"""بوابة حداثة مسارات المصادر.

الرموز: 0 كل المسارات مقيسة وحديثة، 2 مانع، 64 خطأ استعمال.
لا يكفي عدد العناصر؛ يجب وجود أحدث مادة وحقول القياس الأربعة.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

REQUIRED = ("route", "items", "chars", "elapsed_seconds", "measured_at", "newest_published")


def date_value(value: object) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def records(doc: object) -> list[dict]:
    if isinstance(doc, list):
        return [x for x in doc if isinstance(x, dict)]
    if isinstance(doc, dict):
        for key in ("routes", "measurements", "records"):
            if isinstance(doc.get(key), list):
                return [x for x in doc[key] if isinstance(x, dict)]
        return [doc]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="فحص حداثة قياسات مسارات المصادر")
    parser.add_argument("--measurement", required=True, help="ملف JSON يحوي قياسات المسارات")
    parser.add_argument("--as-of", required=True, help="تاريخ القياس المرجعي بصيغة YYYY-MM-DD")
    parser.add_argument("--max-age-days", type=int, default=3)
    parser.add_argument("--min-items", type=int, default=1)
    parser.add_argument("--min-chars", type=int, default=1)
    args = parser.parse_args()
    as_of = date_value(args.as_of)
    if as_of is None or args.max_age_days < 0 or args.min_items < 0 or args.min_chars < 0:
        parser.error("التاريخ والحدود يجب أن تكون صالحة")
    try:
        doc = json.loads(Path(args.measurement).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"gate": "مانع", "error": type(exc).__name__}, ensure_ascii=False))
        return 2
    rows = records(doc)
    problems: list[str] = []
    checked: list[dict] = []
    if not rows:
        problems.append("لا توجد قياسات")
    for index, row in enumerate(rows, 1):
        label = str(row.get("route") or f"مسار-{index}")
        missing = [key for key in REQUIRED if key not in row or row[key] in (None, "")]
        if missing:
            problems.append(f"{label}: حقول ناقصة {','.join(missing)}")
            continue
        newest = date_value(row["newest_published"])
        measured = date_value(row["measured_at"])
        if newest is None or measured is None:
            problems.append(f"{label}: تاريخ القياس أو أحدث مادة غير صالح")
            continue
        try:
            items = int(row["items"])
            chars = int(row["chars"])
            elapsed = float(row["elapsed_seconds"])
        except (TypeError, ValueError):
            problems.append(f"{label}: حقول العدد أو الزمن غير رقمية")
            continue
        age = (as_of - newest).days
        row_result = {"route": label, "items": items, "chars": chars,
                      "elapsed_seconds": elapsed, "age_days": age,
                      "newest_published": newest.isoformat(),
                      "measured_at": measured.isoformat()}
        checked.append(row_result)
        if items < args.min_items:
            problems.append(f"{label}: العناصر {items} أقل من {args.min_items}")
        if chars < args.min_chars:
            problems.append(f"{label}: الحروف {chars} أقل من {args.min_chars}")
        if elapsed < 0:
            problems.append(f"{label}: الزمن سالب")
        if age < 0 or age > args.max_age_days:
            problems.append(f"{label}: عمر أحدث مادة {age} يومًا، والحد {args.max_age_days}")
    result = {
        "gate": "ناجح" if not problems else "مانع",
        "as_of": as_of.isoformat() if as_of else args.as_of,
        "max_age_days": args.max_age_days,
        "checked": checked,
        "problems": problems,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
