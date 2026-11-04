#!/usr/bin/env python3
"""حارس مفردات حقل «الموقع» — يفشل مغلقًا على أي قيمة خارج السجل.

المصدر الحاكم: appendices/zone-registry.json (areas · area_value_format · area_rules).
لا تُعد «غير مكاني/غير مكانية» قيمة موقع؛ غياب ``area`` لا يُقبل إلا مع
``area_basis`` غير فارغ. وتُفحص المصطلحات المحظورة على صفوف الدفتر وملفات
الواجهة ومتـون التقارير المقروءة.

الخروج: 0 مطابق · 2 مخالف · 70 انهيار مدقق.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = pathlib.Path("appendices/zone-registry.json")
LEDGER = pathlib.Path("cumulative-2026") / "daily"
META = pathlib.Path("web") / "meta"
REPORTS = pathlib.Path("reports")

SCOPE = ("المنطقة كاملة", "سياق إقليمي")
NON_SPATIAL_TERMS = ("غير مكاني", "غير مكانية")


def load_allowed(root: pathlib.Path = ROOT) -> tuple[set[str], str]:
    reg = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    names = {a["ar"] for a in reg.get("areas", [])}
    return names, reg.get("non_spatial_value", "غير مكانية")


def parts_ok(raw: str, names: set[str], non_spatial: str) -> tuple[bool, str]:
    raw = raw.strip()
    if not raw:
        return False, "قيمة فارغة"
    for term in NON_SPATIAL_TERMS:
        if term in raw:
            return False, f"لفظ موقع غير مسموح: «{term}»"
    for part in [p.strip() for p in raw.split("·") if p.strip()]:
        if part in names or part in SCOPE:
            continue
        if " - " in part:
            left, _, right = part.rpartition(" - ")
            if left.strip() and right.strip() in names:
                continue
            return False, f"صيغة غير مطابقة: «{part}»"
        return False, f"قيمة خارج السجل: «{part}»"
    return True, ""


def is_no_incident(row: dict) -> bool:
    code = str(row.get("code") or "")
    title = str(row.get("title") or "")
    desc = str(row.get("source_description") or "")
    if code.startswith("NI-") or "لا واقعة" in title or "لا واقعة" in desc:
        return True
    if code.startswith("COVER-") and not str(row.get("area") or "").strip():
        return True
    return False


def walk_rows(obj: Any, out: list[dict]) -> None:
    if isinstance(obj, dict):
        if "area" in obj or "code" in obj:
            out.append(obj)
        for value in obj.values():
            walk_rows(value, out)
    elif isinstance(obj, list):
        for value in obj:
            walk_rows(value, out)


def _text_values(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _text_values(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _text_values(child, f"{path}[{index}]")


def _term_errors(text: str, where: str) -> list[str]:
    hits: list[str] = []
    for term in sorted(NON_SPATIAL_TERMS, key=len, reverse=True):
        if term in text:
            hits.append(term)
    if "غير مكانية" in hits and "غير مكاني" in hits:
        hits.remove("غير مكاني")
    return [f"{where}: لفظ موقع محظور «{term}»" for term in hits]


def _row_errors(row: dict, where: str, names: set[str], non_spatial: str) -> list[str]:
    errors: list[str] = []
    for path, text in _text_values(row):
        errors.extend(_term_errors(text, f"{where}.{path}"))
    if not str(row.get("code") or ""):
        return errors
    if is_no_incident(row):
        if str(row.get("area") or "").strip():
            errors.append(f"{where} · صف «لا واقعة» يحمل قيمة موقع «{row['area']}»")
        return errors
    area = str(row.get("area") or "").strip()
    if not area:
        basis = str(row.get("area_basis") or "").strip()
        if not basis:
            errors.append(f"{where} · area فارغة بلا area_basis يوضح غياب الموقع")
        return errors
    if any(term in area for term in NON_SPATIAL_TERMS):
        return errors
    ok, why = parts_ok(area, names, non_spatial)
    if not ok:
        errors.append(f"{where} · {why}")
    return errors


def _load_json(path: pathlib.Path, relative: str) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [f"{relative}: تعذر قراءة JSON: {exc}"]


def scan_root(root: pathlib.Path | str = ROOT) -> list[str]:
    """يمسح الصفوف والأسطح المطلوبة ويعيد المخالفات دون تعديل أي ملف."""
    root = pathlib.Path(root).resolve()
    try:
        names, non_spatial = load_allowed(root)
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return [f"سجل المناطق الحاكم غير قابل للقراءة: {exc}"]
    errors: list[str] = []

    for path in sorted((root / LEDGER).glob("*.json")):
        data, load_errors = _load_json(path, str(path.relative_to(root)))
        errors.extend(load_errors)
        if data is None:
            continue
        rows: list[dict] = []
        walk_rows(data, rows)
        for index, row in enumerate(rows, 1):
            errors.extend(_row_errors(row, f"{path.relative_to(root)}#{index}", names, non_spatial))

    for path in sorted((root / META).glob("*.json")):
        data, load_errors = _load_json(path, str(path.relative_to(root)))
        errors.extend(load_errors)
        if data is None:
            continue
        for field_path, text in _text_values(data):
            errors.extend(_term_errors(text, f"{path.relative_to(root)}.{field_path}"))
        for index, event in enumerate(data.get("event_keys") or [], 1) if isinstance(data, dict) else []:
            if not isinstance(event, dict):
                continue
            errors.extend(_row_errors(event, f"{path.relative_to(root)}.event_keys[{index}]", names, non_spatial))

    for path in sorted((root / REPORTS).glob("*-sectioned.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{path.relative_to(root)}: تعذر قراءة المتن: {exc}")
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            errors.extend(_term_errors(line, f"{path.relative_to(root)}:{line_no}"))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", default=str(ROOT), help="جذر B")
    args = parser.parse_args(argv)
    errors = scan_root(args.root)
    print("حارس مفردات الموقع — أسماء المناطق الحاكمة وقاعدة غياب الموقع")
    if errors:
        print(f"✘ مخالفات: {len(errors)}")
        for error in errors[:80]:
            print(f"  {error}")
        if len(errors) > 80:
            print(f"  … و{len(errors) - 80} مخالفة أخرى")
        return 2
    print("✔ قيم الموقع سليمة، واللفظان غير مكاني/غير مكانية غير موجودين على الأسطح")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
