#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس أسماء المصادر — يمنع أوصاف المصدر العامة على الأسطح المقروءة.

يفحص الحارس:
- الحقول ``source`` في صفوف ``cumulative-2026/daily/*.json``، بما فيها
  عناصر ``sources_checked`` في صفوف «لا واقعة».
- كل النصوص في ملفات ``web/meta/*.json``، لأن الواجهة قد تنقل الاسم عبر
  ``ref`` أو ``source`` أو ``source_label``.
- متن ``reports/*-sectioned.md``.

قائمة الأوصاف الممنوعة مصدر بيانات وحيد في
``appendices/source-label-blacklist.json``. الخروج: 0 مطابق، 2 منع، 70 انهيار.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
BLACKLIST = Path("appendices/source-label-blacklist.json")


def load_blacklist(root: Path) -> list[str]:
    """اقرأ الأوصاف الممنوعة من ملف البيانات، وارفض البنية الفاسدة."""
    path = root / BLACKLIST
    raw = json.loads(path.read_text(encoding="utf-8"))
    labels = raw.get("labels") if isinstance(raw, dict) else raw
    if not isinstance(labels, list) or not labels or not all(isinstance(x, str) and x.strip() for x in labels):
        raise ValueError(f"قائمة الأوصاف الممنوعة غير صالحة: {path}")
    return [x.strip() for x in labels]


def _text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _text_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _text_values(child)


def _source_values(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    """يعيد كل قيمة تحت مفتاح source، بما فيها القوائم المتداخلة."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key == "source":
                for text in _text_values(child):
                    yield child_path, text
            else:
                yield from _source_values(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _source_values(child, f"{path}[{index}]")


def _label_hits(text: str, labels: list[str]) -> list[str]:
    return [label for label in labels if label in text]


def _scan_json_source_fields(path: Path, labels: list[str], *, relative: str) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"{relative}: تعذر قراءة JSON: {exc}"]
    errors: list[str] = []
    for field_path, text in _source_values(data):
        for label in _label_hits(text, labels):
            errors.append(f"{relative} · {field_path}: وصف مصدر عام ممنوع «{label}»")
    return errors


def _scan_meta(path: Path, labels: list[str], *, relative: str) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"{relative}: تعذر قراءة JSON: {exc}"]
    errors: list[str] = []
    for value in _text_values(data):
        for label in _label_hits(value, labels):
            errors.append(f"{relative}: وصف مصدر عام ممنوع «{label}»")
    return errors


def _scan_report(path: Path, labels: list[str], *, relative: str) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"{relative}: تعذر قراءة المتن: {exc}"]
    errors: list[str] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for label in _label_hits(line, labels):
            errors.append(f"{relative}:{line_no}: وصف مصدر عام ممنوع «{label}»")
    return errors


def scan_root(root: Path | str = ROOT) -> list[str]:
    """يمسح الأسطح المطلوبة ويعيد المخالفات دون تعديل أي ملف."""
    root = Path(root).resolve()
    try:
        labels = load_blacklist(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"قائمة أسماء المصادر: {exc}"]

    errors: list[str] = []
    daily = root / "cumulative-2026" / "daily"
    meta = root / "web" / "meta"
    reports = root / "reports"
    for path in sorted(daily.glob("*.json")):
        errors.extend(_scan_json_source_fields(path, labels, relative=str(path.relative_to(root))))
    for path in sorted(meta.glob("*.json")):
        errors.extend(_scan_meta(path, labels, relative=str(path.relative_to(root))))
    for path in sorted(reports.glob("*-sectioned.md")):
        errors.extend(_scan_report(path, labels, relative=str(path.relative_to(root))))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", default=str(ROOT), help="جذر B")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    errors = scan_root(root)
    print(f"حارس اسم المصدر الحقيقي — الجذر: {root}")
    if errors:
        print(f"✘ مخالفات: {len(errors)}")
        for error in errors[:80]:
            print(f"  {error}")
        if len(errors) > 80:
            print(f"  … و{len(errors) - 80} مخالفة أخرى")
        return 2
    print("✔ لا يوجد وصف مصدر عام ممنوع على الأسطح المفحوصة")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
