#!/usr/bin/env python3
"""مصفوفة حالات لأي مدقق: يتحقق أن الإصلاح أزال المنع ولم يُضعف الكاشف.

تقرأ ملف JSON بالشكل:
{
  "cmd": "python3 validators/check_prose_defects.py --md {file}",
  "cases": [
    {"name": "نظيف", "file": "reports/x.md", "expect_rc": 0},
    {"name": "مخالف حقيقي", "file": "/tmp/x.md", "expect_rc": 2}
  ]
}

رموز الخروج: 0 كل الحالات مطابقة · 2 حالة واحدة على الأقل خالفت المتوقع.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shlex
import subprocess
import sys


def run_case(cmd: str, path: str, cwd: str, timeout: int) -> tuple[int, str]:
    argv = [a.replace("{file}", path) for a in shlex.split(cmd)]
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        return 127, f"الأمر غير موجود: {exc}"
    except subprocess.TimeoutExpired:
        return 124, f"تجاوز المهلة ({timeout} ثانية)"
    tail = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, tail.strip().splitlines()[-1] if tail.strip() else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="مصفوفة حالات مدقق واحد")
    ap.add_argument("--matrix", required=True, help="ملف JSON للمصفوفة")
    ap.add_argument("--cwd", default=".", help="مجلد تشغيل الأوامر")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.matrix).read_text(encoding="utf-8"))
    cmd = data.get("cmd") or ""
    cases = data.get("cases") or []
    if not cmd or not cases:
        print("✘ المصفوفة تحتاج cmd و cases")
        return 2

    failures = 0
    for case in cases:
        name = case.get("name", "بلا اسم")
        path = case.get("file", "")
        expect = int(case.get("expect_rc", 0))
        if not path or not pathlib.Path(path).exists():
            print(f"✘ {name}: الملف غير موجود → {path}")
            failures += 1
            continue
        rc, last = run_case(cmd, path, args.cwd, args.timeout)
        mark = "✔" if rc == expect else "✘"
        print(f"{mark} {name}: رمز {rc} (المتوقع {expect})" + (f" · {last[:90]}" if last else ""))
        if rc != expect:
            failures += 1

    print(f"— الحصيلة: حالات {len(cases)} · ناجحة {len(cases) - failures} · مخالفة {failures}")
    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
