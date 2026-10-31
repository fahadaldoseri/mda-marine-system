#!/usr/bin/env python3
"""حارس استمرارية الدفتر، يفشل مغلقًا عند غياب أي سجل يومي.

كل يوم تقويمي مطلوب له ملف في cumulative-2026/daily/*.json. الملف إما
سجل مادة، أو صف واحد/أكثر من نوع ``no_incident`` يحمل قائمة مصادر رسمية
مفحوصة ووقت استرجاع. لا تُستخدم no-material كبديل عن السجل اليومي.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

DEFAULT_START = dt.date(2026, 2, 28)
NO_INCIDENT_TEXT = "لا واقعة مسجّلة في المصادر الرسمية المفحوصة"


def parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"تاريخ غير صالح: {value}") from exc


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"تعذر قراءة {path}: {exc}") from exc


def rows_from_daily(path: Path, value: object) -> list[dict]:
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict):
        rows = next((value.get(k) for k in ("events", "items", "rows")
                     if isinstance(value.get(k), list)), None)
        if rows is None:
            raise RuntimeError(f"بنية دفتر غير معروفة: {path}")
    else:
        raise RuntimeError(f"بنية دفتر غير معروفة: {path}")
    if not all(isinstance(row, dict) for row in rows):
        raise RuntimeError(f"صف غير صالح في {path}")
    return rows


def _is_no_incident(row: dict) -> bool:
    return bool(row.get("no_incident")) or row.get("event_kind") == "no_incident" \
        or row.get("class") == "no_incident"


def validate_no_incident(path: Path, row: dict) -> None:
    if row.get("title") != NO_INCIDENT_TEXT and row.get("description") != NO_INCIDENT_TEXT:
        raise RuntimeError(f"سجل no_incident بلا العبارة المعتمدة: {path}")
    checked = row.get("sources_checked")
    if not isinstance(checked, list) or not checked:
        raise RuntimeError(f"سجل no_incident بلا قائمة مصادر مفحوصة: {path}")
    for index, source in enumerate(checked, 1):
        if not isinstance(source, dict):
            raise RuntimeError(f"مصدر مفحوص غير صالح في {path} (#{index})")
        required = ("source_id", "url", "invoked", "result", "retrieved_at")
        missing = [key for key in required if not source.get(key)]
        if missing:
            raise RuntimeError(f"مصدر no_incident ناقص {missing} في {path} (#{index})")
    if not row.get("retrieved_at"):
        raise RuntimeError(f"سجل no_incident بلا retrieved_at: {path}")


def daily_coverage(root: Path) -> tuple[set[str], set[str]]:
    daily = root / "cumulative-2026" / "daily"
    material: set[str] = set()
    no_incident: set[str] = set()
    if not daily.exists():
        return material, no_incident
    for path in sorted(daily.glob("*.json")):
        if path.name.startswith("_") or path.stem == "no-material":
            continue
        value = load_json(path)
        if value is None:
            raise RuntimeError(f"ملف يومي مفقود أو غير مقروء: {path}")
        rows = rows_from_daily(path, value)
        if not rows:
            continue
        negative = [_is_no_incident(row) for row in rows]
        if any(negative):
            if not all(negative):
                raise RuntimeError(f"خلط مادة وno_incident في الملف نفسه: {path}")
            for row in rows:
                validate_no_incident(path, row)
            no_incident.add(path.stem)
        else:
            material.add(path.stem)
    return material, no_incident


def no_material_dates(root: Path) -> set[str]:
    path = root / "cumulative-2026" / "no-material.json"
    value = load_json(path)
    if value is None:
        return set()
    if not isinstance(value, dict) or not isinstance(value.get("no_material"), list):
        raise RuntimeError(f"وسم no_material غير صالح: {path}")
    result = set()
    for item in value["no_material"]:
        if not isinstance(item, str):
            raise RuntimeError(f"تاريخ no_material غير نصي: {item!r}")
        parse_date(item)
        result.add(item)
    return result


def expected_dates(start: dt.date, end: dt.date):
    day = start
    while day <= end:
        if day.isoformat() != "2026-02-29":
            yield day
        day += dt.timedelta(days=1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--start", type=parse_date, default=DEFAULT_START)
    parser.add_argument("--date", type=parse_date, default=dt.datetime.now(dt.timezone.utc).date())
    args = parser.parse_args(argv)
    if args.start > args.date:
        print(f"✘ مدى غير صالح: {args.start} بعد {args.date}")
        return 2
    try:
        material, no_incident = daily_coverage(args.root)
        exempt = no_material_dates(args.root)
    except (RuntimeError, ValueError) as exc:
        print(f"✘ فشل مغلق: {exc}")
        return 2
    covered_by_daily = material | no_incident
    conflicts = sorted(material & exempt)
    expected = {day.isoformat() for day in expected_dates(args.start, args.date)}
    missing = sorted(expected - covered_by_daily)
    out_of_range = sorted((covered_by_daily | exempt) - expected)
    if conflicts:
        print("✘ فشل مغلق: يوم موسوم no_material وله مادة أيضًا: " + ", ".join(conflicts))
    if missing:
        print("✘ فشل مغلق: أيام بلا سجل يومي موثق:")
        print("  " + ", ".join(missing))
    if out_of_range:
        print("✘ فشل مغلق: تواريخ خارج المدى المعلن: " + ", ".join(out_of_range))
    if conflicts or missing or out_of_range:
        return 2
    print(
        f"✔ استمرارية الدفتر مكتملة: {len(expected)} يومًا · "
        f"مادة {len(material & expected)} · no_incident موثق {len(no_incident & expected)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
