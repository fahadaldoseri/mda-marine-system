#!/usr/bin/env python3
"""استخراج بنود المنع حرفيًا من سجل خطوة بناء فاشلة مغلقًا.

الاستخدام:
    python3 extract_closed_fail_items.py --log logs/runbook/2026-11-11/B010.log
    python3 extract_closed_fail_items.py --log <سجل> --json /tmp/items.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

# رسائل المنع الشائعة في خطوط البناء المغلقة
BLOCK_MARKERS = (
    "فشل مغلق",
    "بلا ترجمة",
    "تسرّب رمز قالب",
    "تعديل حاكم",
    "غير متتبَّع",
    "مفقود",
)
ITEM_RE = re.compile(r"^\s*(?:[-•·✘✔→]|\d+\))\s*(.+?)\s*$")
SKIP_RE = re.compile(r"^\s*(?:[-•·✘✔]|\d+\))?\s*(?:أقسام مُخفاة|المسارات|الملفات|elapsed)")


def extract(text: str) -> list[str]:
    """أعد البنود المطبوعة بعد أول رسالة منع، بلا تكرار وبالترتيب."""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if any(m in ln for m in BLOCK_MARKERS):
            start = i
            break
    if start is None:
        return []
    items: list[str] = []
    for ln in lines[start:]:
        m = ITEM_RE.match(ln)
        if not m:
            continue
        val = m.group(1).strip()
        if not val or SKIP_RE.match(ln) or val in items:
            continue
        items.append(val)
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="مسار سجل الخطوة")
    ap.add_argument("--json", help="مسار ملف JSON للخرج")
    a = ap.parse_args()

    p = pathlib.Path(a.log)
    if not p.exists():
        print(f"مفقود: {p}", file=sys.stderr)
        return 2
    items = extract(p.read_text(encoding="utf-8", errors="ignore"))
    if not items:
        print("لم تُعثر بنود منع في السجل — تحقّق من الخطوة أو اقرأ السجل كاملًا.")
        return 0
    print(f"عدد بنود المنع: {len(items)}")
    for i, it in enumerate(items, 1):
        print(f"{i:>3}| {it}")
    if a.json:
        out = pathlib.Path(a.json)
        out.write_text(json.dumps({"log": str(p), "count": len(items), "items": items},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"حُفظ: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
