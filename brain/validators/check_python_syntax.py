#!/usr/bin/env python3
"""حارس ترجمة الشيفرة: يمنع أي ملف Python معطوب صياغيًا من دخول المشروع.

السبب: ملفات سبق أن دخلت المشروع وفيها `from __future__ import annotations`
بعد عبارات أخرى، فتوقّف الكتيب عند بوابة لاحقة بخطأ ترجمة لا علاقة له بالبيانات.
يفشل مغلقًا (rc=2) عند أي خطأ، ويعرض الملف والسطر والرسالة.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {"node_modules", ".git", "logs", "dist", "archive", "audit"}
ROOTS = [ROOT, pathlib.Path("/home/ubuntu/seawatch")]


SHADOW_PAT = re.compile(r"from _guard import run\b(?! as)")


def shadowed_guard_run(path: pathlib.Path, text: str) -> list[str]:
    """يكشف تعارض اسم: تثبيت run من حارس الانهيار مع تعريف run محلي في الملف نفسه."""
    if path.name == "_guard.py" or not SHADOW_PAT.search(text):
        return []
    if re.search(r"^(async )?def run\(", text, re.M):
        return [f"{path}: «run» مُثبَّت من _guard ومُعرَّف محليًا في الملف نفسه"]
    return []

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    bad, scanned = [], 0
    for base in ROOTS:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if any(x in path.parts for x in SKIP):
                continue
            scanned += 1
            try:
                compile(path.read_text(encoding="utf-8", errors="ignore"), str(path), "exec")
            except SyntaxError as exc:
                bad.append({"file": str(path), "line": exc.lineno, "message": exc.msg})
                continue
            for msg in shadowed_guard_run(path, path.read_text(encoding="utf-8", errors="ignore")):
                bad.append({"file": str(path), "line": 0, "message": "تعارض اسم: run"})
                print(f"   ⚠ {msg}")
    for row in bad:
        print(f"   ✘ {row['file']}:{row['line']} — {row['message']}")
    if args.json:
        import json
        pathlib.Path(args.json).write_text(
            json.dumps({"scanned": scanned, "bad": bad}, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
    if bad:
        print(f"   ✘ منع: {len(bad)} ملف Python معطوب من {scanned} ملفًا مفحوصًا")
        return 2
    print(f"   ✔ ترجمة سليمة: {scanned} ملف Python مفحوصًا")
    return 0


if __name__ == "__main__":
    sys.exit(main())
