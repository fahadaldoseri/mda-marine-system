#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس تغطية الأيام — فشل مغلق عند غياب ملف أو دليل قابل للتدقيق.

لكل يوم من 2026-02-28 حتى آخر ملف يومي يجب أن توجد مادة مكتملة الدليل أو
سجل ``no_incident`` مكتمل بفحوص مصادر مسماة. لا تُعدّ قائمة مصدر محجوب
وحدها فحصًا ناجحًا.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
START_DATE = dt.date(2026, 2, 28)
BLACKLIST_REL = Path("appendices/source-label-blacklist.json")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _is_no_incident(row: dict[str, Any]) -> bool:
    return bool(row.get("no_incident")) or row.get("event_kind") == "no_incident" \
        or row.get("class") == "no_incident"


def _load_labels(root: Path) -> list[str]:
    raw = json.loads((root / BLACKLIST_REL).read_text(encoding="utf-8"))
    labels = raw.get("labels") if isinstance(raw, dict) else raw
    if not isinstance(labels, list) or not labels or not all(isinstance(x, str) and x.strip() for x in labels):
        raise ValueError("قائمة أسماء المصادر فارغة أو غير صالحة")
    return [x.strip() for x in labels]


def _source_named(value: Any, labels: list[str]) -> bool:
    if isinstance(value, list):
        values = [str(x).strip() for x in value if str(x).strip()]
        return bool(values) and all(_source_named(x, labels) for x in values)
    text = _text(value)
    return bool(text) and not any(label in text for label in labels)


def _blocked(item: dict[str, Any]) -> bool:
    status = " ".join(_text(item.get(key)) for key in ("status", "result", "error", "block_reason")).lower()
    if any(token in status for token in ("محجوب", "حجب", "blocked", "forbidden", "timeout", "تعذر")):
        return True
    raw_status = item.get("http_status")
    try:
        return not (200 <= int(raw_status) < 300)
    except (TypeError, ValueError):
        return True


def _rows(data: Any, label: str) -> list[dict[str, Any]]:
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = next((data.get(key) for key in ("events", "items", "rows") if isinstance(data.get(key), list)), None)
        if rows is None:
            raise ValueError(f"{label}: لا توجد قائمة سجلات")
    else:
        raise ValueError(f"{label}: جذر JSON ليس قائمة أو كائنًا")
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{label}: قائمة السجلات فارغة أو تحتوي عنصرًا غير صالح")
    return rows


def _check_material(row: dict[str, Any], label: str, labels: list[str], index: int) -> list[str]:
    where = f"{label}#{index}"
    errors: list[str] = []
    for key in ("source", "evidence_ref", "retrieved_at"):
        if not _text(row.get(key)):
            errors.append(f"{where}: صف مادة بلا {key}")
    if _text(row.get("source")) and not _source_named(row.get("source"), labels):
        errors.append(f"{where}: source ليس اسم مصدر حقيقي")
    return errors


def _check_no_incident(row: dict[str, Any], label: str, labels: list[str], index: int) -> list[str]:
    where = f"{label}#{index}"
    errors: list[str] = []
    if not _text(row.get("retrieved_at")):
        errors.append(f"{where}: سجل لا واقعة بلا retrieved_at")
    sources = row.get("sources_checked")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{where}: سجل لا واقعة بلا sources_checked غير فارغة")
        return errors
    for source_index, item in enumerate(sources, 1):
        source_where = f"{where}.sources_checked[{source_index}]"
        if not isinstance(item, dict):
            errors.append(f"{source_where}: عنصر المصدر ليس كائنًا")
            continue
        if not _source_named(item.get("source", item.get("source_id")), labels):
            errors.append(f"{source_where}: source ليس اسم مصدر حقيقي")
        for key in ("url", "http_status", "retrieved_at"):
            value = item.get(key)
            if key == "http_status":
                if value is None or (isinstance(value, bool)):
                    errors.append(f"{source_where}: http_status غائب أو غير صالح")
            elif not _text(value):
                errors.append(f"{source_where}: {key} غائب أو فارغ")
        if _text(item.get("url")) and not _text(item.get("url")).startswith(("http://", "https://")):
            errors.append(f"{source_where}: url ليس رابطًا")
    if all(isinstance(item, dict) and _blocked(item) for item in sources):
        errors.append(f"{where}: كل المصادر محجوبة/فاشلة؛ لا يعدّ الفحص نجاحًا")
    return errors


def check_coverage(root: Path | str = ROOT, *, start_date: str = "2026-02-28") -> list[str]:
    """يعيد مخالفات تغطية الفترة، بلا كتابة بيانات الإنتاج."""
    root = Path(root).resolve()
    errors: list[str] = []
    daily = root / "cumulative-2026" / "daily"
    try:
        start = dt.date.fromisoformat(start_date)
    except ValueError:
        return [f"تاريخ البداية غير صالح: {start_date}"]
    files = {}
    for path in daily.glob("*.json"):
        try:
            files[dt.date.fromisoformat(path.stem)] = path
        except ValueError:
            errors.append(f"اسم ملف يومي غير صالح: {path.name}")
    if not files:
        return errors + [f"لا ملفات يومية في {daily}"]
    end = max(files)
    try:
        labels = _load_labels(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return errors + [f"تعذر قراءة قائمة أسماء المصادر: {exc}"]
    day = start
    while day <= end:
        path = files.get(day)
        label = day.isoformat()
        if path is None:
            errors.append(f"{label}: ملف يومي مفقود")
            day += dt.timedelta(days=1)
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows = _rows(data, label)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{label}: {exc}")
            day += dt.timedelta(days=1)
            continue
        kinds = {_is_no_incident(row) for row in rows}
        if len(kinds) > 1:
            errors.append(f"{label}: لا يجوز خلط صف مادة مع صف لا واقعة")
        for index, row in enumerate(rows, 1):
            if _is_no_incident(row):
                errors.extend(_check_no_incident(row, label, labels, index))
            else:
                errors.extend(_check_material(row, label, labels, index))
        day += dt.timedelta(days=1)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", default=str(ROOT), help="جذر B")
    parser.add_argument("--start-date", default="2026-02-28")
    args = parser.parse_args(argv)
    errors = check_coverage(args.root, start_date=args.start_date)
    print(f"حارس تغطية الأيام — من {args.start_date} إلى آخر ملف يومي")
    if errors:
        print(f"✘ مخالفات: {len(errors)}")
        for error in errors[:100]:
            print(f"  {error}")
        if len(errors) > 100:
            print(f"  … و{len(errors) - 100} مخالفة أخرى")
        return 2
    print("✔ كل يوم مغطّى بمادة ذات دليل أو بسجل لا واقعة موثّق")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
