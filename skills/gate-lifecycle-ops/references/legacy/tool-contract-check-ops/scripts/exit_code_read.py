#!/usr/bin/env python3
"""شغّل أمرًا، واقرأ رمز خروجه ومخرجه الحرفي مع تحقق العقد."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from cli_contract import inspect_command, unknown_arguments  # noqa: E402


def _split(argv: Sequence[str]) -> tuple[list[str], list[str]]:
    values = list(argv)
    if "--" not in values:
        return values, []
    idx = values.index("--")
    return values[:idx], values[idx + 1 :]


def _classification(code: int) -> str:
    if code == 0:
        return "0 نجاح"
    if code == 2:
        return "2 منع/استخدام خاطئ"
    if code == 10:
        return "10 يحتاج تدخلًا"
    return f"{code} عطل"


def main(argv: Sequence[str] | None = None) -> int:
    own, command = _split(list(argv if argv is not None else sys.argv[1:]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract-tool", default=None, help="مسار العقد إن تعذر استنتاجه من الأمر")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args(own)
    if not command:
        parser.error("أعطِ الأمر بعد الفاصل --")
    contract, passed = inspect_command(command, timeout=min(args.timeout, 2.0), tool_override=args.contract_tool)
    print("العقد قبل التشغيل:")
    print(f"  المصدر: {contract.source_method} · الأداة: {contract.tool}")
    print("  الخيارات المقبولة: " + (", ".join(contract.accepted_options) if contract.accepted_options else "(لم تُستخرج)"))
    unknown = unknown_arguments(contract, passed)
    if unknown:
        print("  تنبيه العقد: الاستخدام يتضمن وسائط لا يعرفها العقد: " + ", ".join(unknown))
    elif contract.source is None and not contract.accepted_options:
        print("  تنبيه العقد: لم يُستخرج عقد قابل للمقارنة؛ لا يُفترض أن الاستدعاء صحيح")
    for warning in contract.warnings:
        print("  تحذير استخراج: " + warning)
    try:
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=args.timeout, check=False)
        code = completed.returncode
        output = completed.stdout or ""
    except subprocess.TimeoutExpired as exc:
        code = 124
        output = ((exc.stdout or "") if isinstance(exc.stdout, str) else "")
        output += "\n[انتهت مهلة التشغيل]"
    except OSError as exc:
        code = 127
        output = f"[تعذر تشغيل الأمر: {type(exc).__name__}: {exc}]"
    lines = output.splitlines()
    print(f"كود الخروج: {code}")
    print("آخر 30 سطرًا من المخرج الحرفي:")
    if lines:
        for line in lines[-30:]:
            print(line)
    else:
        print("(لا مخرج)")
    print("التصنيف المقترح: " + _classification(code))
    if code != 0:
        print("قاعدة الفشل المغلق: توقّف واقرأ المخرج والعقد قبل أي متابعة")
    return code if 0 <= code <= 125 else 1


if __name__ == "__main__":
    raise SystemExit(main())
