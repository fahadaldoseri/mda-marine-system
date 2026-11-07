#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# تمنع هذه البوابة اعتماد مخرج بلا مدخلات قابلة للقياس أو بلا أثر يثبت نطاقها؛
# عدّل قاعدة النطاق داخل violations() بعد تحديد قاعدة المجال، ولا تفتح الفشل المغلق.
"""قالب بوابة فحص — الخروج 0 للمطابقة و2 للمنع."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date as date_type
from pathlib import Path

GATE_NAME = __GATE_NAME_LITERAL__
GATE_DESCRIPTION = __GATE_DESCRIPTION_LITERAL__
GATE_SCOPE = __GATE_SCOPE_LITERAL__
SCOPE_MARKER = "gate-scope:" + GATE_SCOPE


class GateInputError(ValueError):
    """خطأ قابل للحكم: تعذّر قياس مدخل، ولذلك يجب المنع."""


def read_text_file(path: str | Path, label: str) -> str:
    """اقرأ ملفًا نصيًا غير فارغ، وحوّل كل تعذّر إلى سبب حرفي قابل للحكم."""
    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise GateInputError(f"{label}: الملف غير موجود: {candidate}")
    if not candidate.is_file():
        raise GateInputError(f"{label}: المسار ليس ملفًا قابلًا للقياس: {candidate}")
    try:
        text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GateInputError(f"{label}: تعذّرت قراءة الملف: {candidate} ({exc})") from exc
    if not text.strip():
        raise GateInputError(f"{label}: الملف فارغ؛ تعذّر القياس: {candidate}")
    return text


def _measurement_file(root: str | Path, label: str) -> Path:
    """حلّ مجلد القياس إلى gate-measurement.txt، أو اقبل ملفًا مباشرًا للاختبار."""
    candidate = Path(root).expanduser()
    if candidate.is_file():
        return candidate
    if candidate.is_dir():
        measurement = candidate / "gate-measurement.txt"
        if not measurement.is_file():
            raise GateInputError(
                f"{label}: لا يوجد ملف القياس gate-measurement.txt داخل {candidate}"
            )
        return measurement
    raise GateInputError(f"{label}: المدخل مفقود أو غير قابل للقياس: {candidate}")


def _valid_date(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) and _date_ok(value))


def _date_ok(value: str) -> bool:
    try:
        date_type.fromisoformat(value)
    except ValueError:
        return False
    return True


def violations(
    *, date_value: str | None, brain: str | Path | None,
    site: str | Path | None, pdf: str | Path | None,
) -> list[str]:
    """أعد أسباب المنع فقط؛ الدالة لا تطبع ولا تغيّر ملفات، فتصلح للاختبار."""
    failures: list[str] = []
    if not date_value:
        failures.append("--date: المدخل مفقود")
    elif not _valid_date(date_value):
        failures.append(f"--date: تاريخ غير صالح للقياس: {date_value}")

    inputs = (("--brain", brain, True), ("--site", site, True), ("--pdf", pdf, False))
    measured: list[tuple[str, str]] = []
    for label, value, is_root in inputs:
        if value is None or str(value).strip() == "":
            failures.append(f"{label}: المدخل مفقود؛ تعذّر القياس")
            continue
        try:
            path = _measurement_file(value, label) if is_root else Path(value).expanduser()
            measured.append((label, read_text_file(path, label)))
        except (GateInputError, OSError, UnicodeError) as exc:
            failures.append(str(exc))

    if failures:
        return failures

    for label, text in measured:
        if SCOPE_MARKER not in text:
            failures.append(
                f"{label}: تعذّر القياس — وسم النطاق «{SCOPE_MARKER}» غير موجود"
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=GATE_DESCRIPTION)
    parser.add_argument("--date", default="", help="تاريخ المخرج بصيغة YYYY-MM-DD")
    parser.add_argument("--brain", default="", help="جذر Brain أو ملف قياس مباشر")
    parser.add_argument("--site", default="", help="جذر الموقع أو ملف قياس مباشر")
    parser.add_argument("--pdf", default="", help="ملف PDF/إثبات القياس")
    parser.add_argument("--json", action="store_true", help="أخرج الحكم بصيغة JSON")
    args = parser.parse_args()

    try:
        failures = violations(
            date_value=args.date, brain=args.brain, site=args.site, pdf=args.pdf
        )
    except Exception as exc:  # الفشل المغلق: لا نجاح عند تعذر القياس الداخلي.
        failures = [f"تعذّر القياس الداخلي: {type(exc).__name__}: {exc}"]

    status = "مطابق" if not failures else "منع"
    if args.json:
        print(json.dumps({"gate": GATE_NAME, "status": status, "violations": failures}, ensure_ascii=False))
    elif failures:
        print(f"منع: {GATE_NAME}")
        for failure in failures:
            print(f"  ✗ {failure}")
    else:
        print(f"مطابق: {GATE_NAME} — {GATE_DESCRIPTION}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
