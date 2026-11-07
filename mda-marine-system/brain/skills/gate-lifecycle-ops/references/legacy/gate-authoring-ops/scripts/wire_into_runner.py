#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""أدرج أمر بوابة واحدًا في مشغّل run_checks مع عدّاده الحالي."""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

MARK_PREFIX = "# gate-authoring-ops:"


def build_line(runner: Path, gate: Path, label: str) -> str:
    root = runner.parent.parent
    try:
        relative_gate = gate.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("يجب أن تكون البوابة داخل جذر المشغّل ليبقى الربط محمولًا") from exc
    command = (
        f't "{label}" python3 "$B/{relative_gate}" '
        '--date "$(date -u +%F)" --brain "$B" '
        '--site "${SITE_DIR:-$B/../seawatch}" '
        '--pdf "${PDF_PATH:-$B/../seawatch/dist/reports/pdf/$(date -u +%F).pdf}"'
    )
    return f"{MARK_PREFIX} {gate.name} — {label}\n{command}\n"


def validate_runner(text: str) -> str | None:
    required = (
        (r"\bPASS\s*=\s*0\b", "عداد PASS/FAIL غير موجود"),
        (r"\bFAIL\s*=\s*0\b", "عداد FAIL غير موجود"),
        (r"(?m)^t\(\)", "دالة t غير موجودة؛ لا يمكن استخدام عداد المشغّل نفسه"),
        (r"----- الحصيلة -----", "موضع حصيلة المشغّل غير موجود"),
    )
    for pattern, message in required:
        if not re.search(pattern, text):
            return message
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="ربط بوابة في tests/run_checks.sh")
    parser.add_argument("--runner", required=True, help="مسار مشغّل الفحوص")
    parser.add_argument("--gate", required=True, help="مسار ملف البوابة")
    parser.add_argument("--label", default="بوابة جديدة", help="وصف يظهر في عداد المشغّل")
    parser.add_argument("--apply", action="store_true", help="طبّق الفرق؛ الافتراضي dry-run")
    args = parser.parse_args()

    runner = Path(args.runner).expanduser().resolve()
    gate = Path(args.gate).expanduser().resolve()
    if not runner.is_file():
        print(f"منع: مشغّل الفحوص غير موجود: {runner}")
        return 2
    if not gate.is_file():
        print(f"منع: ملف البوابة غير موجود: {gate}")
        return 2
    try:
        original = runner.read_text(encoding="utf-8")
        error = validate_runner(original)
        if error:
            print(f"منع: لا يمكن الربط بأمان: {error}")
            return 2
        marker = f"{MARK_PREFIX} {gate.name}"
        if marker in original or f'"$B/{gate.relative_to(runner.parent.parent).as_posix()}"' in original:
            print(f"لا تغيير: البوابة موجودة مسبقًا بلا تكرار: {gate.name}")
            return 0
        insertion = build_line(runner, gate, args.label)
        anchor = 'echo "----- الحصيلة -----"'
        index = original.find(anchor)
        if index < 0:
            print("منع: موضع إدراج الحصيلة غير قابل للتحديد")
            return 2
        updated = original[:index] + insertion + "\n" + original[index:]
    except (OSError, ValueError) as exc:
        print(f"منع: تعذّرت قراءة أو بناء الفرق: {exc}")
        return 2

    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(runner),
            tofile=str(runner) + " (مقترح)",
        )
    )
    print(diff if diff else "لا تغيير")
    if args.apply:
        try:
            runner.write_text(updated, encoding="utf-8")
        except OSError as exc:
            print(f"منع: تعذّر تطبيق الفرق: {exc}")
            return 2
        print(f"طُبّق الربط بلا تكرار: {runner}")
    else:
        print("وضع dry-run: لم يُعدّل الملف؛ أعد الأمر مع --apply للتطبيق")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
