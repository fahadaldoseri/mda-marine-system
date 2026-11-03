#!/usr/bin/env python3
"""حارس شكل لأي ملف JSON مشتق: يمنع الكتابة في عقدة غير التي يقرأها المستهلك.

مثال الاستخدام:
python3 check_object_shape.py --file sources/i18n/en/glossary.json \
  --require entries --allow _note,_derived,updated,date_updated,date_created

رموز الخروج: 0 سليم · 2 مخالف (مفتاح غير مسموح · عقدة مطلوبة مفقودة أو ليست كائنًا · JSON غير صالح).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def split_list(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()}


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس شكل ملف JSON مشتق")
    ap.add_argument("--file", required=True)
    ap.add_argument("--require", default="", help="عقدة (أو عقد) يجب وجودها ككائن، مفصولة بفواصل")
    ap.add_argument("--allow", default="", help="المفاتيح الجذرية المسموحة، مفصولة بفواصل")
    ap.add_argument("--allow-lists", action="store_true",
                    help="اسمح بأن تكون العقدة المطلوبة قائمة بدل كائن")
    args = ap.parse_args()

    path = pathlib.Path(args.file)
    if not path.exists():
        print(f"✘ الملف غير موجود: {path}")
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"✘ الملف ليس JSON صالحًا: {exc}")
        return 2
    if not isinstance(data, dict):
        print("✘ الجذر ليس كائنًا (object)")
        return 2

    required = split_list(args.require)
    allowed = split_list(args.allow)
    problems: list[str] = []

    if not required and not allowed:
        print("✘ لا شرط فحص: مرِّر --require و/أو --allow · لا يُقبل «سليم» بلا فحص")
        return 2

    for node in required:
        if node not in data:
            problems.append(f"العقدة المطلوبة مفقودة: {node}")
        else:
            ok = isinstance(data[node], dict) or (args.allow_lists and isinstance(data[node], list))
            if not ok:
                problems.append(f"العقدة {node} موجودة لكن نوعها غير متوقع")

    if allowed:
        stray = sorted(k for k in data if k not in allowed)
        if stray:
            problems.append(f"مفاتيح جذرية غير مسموحة: {len(stray)}")
            for k in stray[:5]:
                problems.append(f"   · {k[:70]}")

    if problems:
        print(f"✘ شكل الملف مخالف ({len(problems)})")
        for p in problems[:12]:
            print(f"   {p}")
        print("  الإصلاح: انقل المدخل إلى العقدة التي يقرأها المستهلك، لا إلى الجذر.")
        return 2

    summary = " · ".join(f"{n}={len(data[n])}" for n in required if isinstance(data[n], (dict, list)))
    print(f"✔ الشكل سليم · {summary or 'لا عقد مطلوبة'} · مفاتيح الجذر={len(data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
