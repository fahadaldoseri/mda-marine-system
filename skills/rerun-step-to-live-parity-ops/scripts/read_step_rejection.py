#!/usr/bin/env python3
"""Extract the first explicit blocking/rejection line from a runbook step log."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATTERNS = (
    re.compile(r"(?:فشل مغلق|رفض|مانع|✘|✖|ERROR|error|rc\s*=\s*[1-9]|خروج\s+[1-9])"),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="يقرأ سجل خطوة كاملًا ويعرض أسطر الرفض الفعلية لا عنوان الخطوة."
    )
    parser.add_argument("--log", required=True, help="مسار سجل الخطوة")
    parser.add_argument("--all", action="store_true", help="عرض كل أسطر الرفض بدل أول سطر")
    args = parser.parse_args()

    path = Path(args.log)
    if not path.is_file():
        print(f"رفض: سجل غير موجود: {path}", file=sys.stderr)
        return 2

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        print(f"رفض: تعذر قراءة السجل: {exc}", file=sys.stderr)
        return 2

    matches = [
        (number, line)
        for number, line in enumerate(lines, start=1)
        if any(pattern.search(line) for pattern in PATTERNS)
    ]
    if not matches:
        print("لم يُعثر على سطر رفض صريح", file=sys.stderr)
        return 2

    selected = matches if args.all else matches[:1]
    for number, line in selected:
        print(f"line={number}: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
