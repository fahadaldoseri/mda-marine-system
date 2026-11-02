#!/usr/bin/env python3
"""حارس جودة مرجع المصائد: لا وصفة بلا أمر إثبات قابل للتشغيل.

السبب (جولة 2026-11-02): مرجع المصائد ينمو مع كل عطل مُغلق، فإذا دخلته وصفة
بخلايا ناقصة أو بلا أمر إثبات صار «الإغلاق وثيقة بلا دليل» — وهو ما يمنعه
حارس الإغلاق في المشروع. هذه الأداة تجعل القاعدة قابلة للقياس قبل النشر.

يفشل مغلقًا (رمز 2) عند: صف بجدول المصائد بخلايا ناقصة · وجود `TODO` ·
صف بلا أمر إثبات (python3/bash/gh/sh) في خانة «أمر الإثبات».
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

DEFAULT = pathlib.Path(__file__).resolve().parents[1] / "references" / "playbook.md"
CMD = re.compile(r"\b(python3|bash|gh|sh|curl)\b")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--playbook", default=str(DEFAULT))
    a = ap.parse_args()

    path = pathlib.Path(a.playbook)
    if not path.is_file():
        print(f"   ✘ منع: مرجع المصائد غير موجود: {path}")
        return 2

    text = path.read_text(encoding="utf-8")
    bad, rows = [], 0
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s.startswith("|") or set(s) <= set("|-: "):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and cells[0] in ("الخطوة", "المصيدة", "الرقم"):
            continue
        if len(cells) != 5:
            bad.append(f"سطر {i}: عدد الخلايا {len(cells)} بدل 5")
            continue
        rows += 1
        empty = [j + 1 for j, c in enumerate(cells) if not c]
        if empty:
            bad.append(f"سطر {i}: خلايا فارغة ({', '.join(map(str, empty))})")
        if "TODO" in s:
            bad.append(f"سطر {i}: يحتوي TODO")
        if not CMD.search(cells[4]):
            bad.append(f"سطر {i}: «أمر الإثبات» بلا أمر قابل للتشغيل: {cells[4][:60]}")

    for b in bad:
        print(f"   ✘ {b}")
    if bad:
        print(f"   ✘ منع: {len(bad)} خللًا في {rows} وصفة")
        return 2
    if not rows:
        print("   ✘ منع: لا وصفات في المرجع")
        return 2
    print(f"   ✔ {rows} وصفة مكتملة، وكلها تحمل أمر إثبات قابلًا للتشغيل")
    return 0


if __name__ == "__main__":
    sys.exit(main())