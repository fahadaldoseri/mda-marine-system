#!/usr/bin/env python3
"""جرد أسطح إعادة التسمية: أين يعيش الاسم القديم؟ وهل وصل الجديد إلى كل سطح؟

الاستعمال:
  python3 scan_name_surfaces.py --old "الوقائع الجديدة" --new "سجل الأحداث" \
      --root "المتن=/path/reports" --root "السجل=/path/runbook" \
      --root "المولّد=/path/generator" --governed "المتن" "السجل" "المولّد"

الخروج: 0 لا بقايا في الأسطح الحاكمة · 1 بقايا موجودة · 2 خطأ استعمال.
"""
import argparse, os, sys
from pathlib import Path

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.history'}
SKIP_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.zip', '.woff', '.woff2', '.ttf', '.ico', '.mp4'}
MAX_BYTES = 2_000_000

def scan(root: Path, old: str, new: str):
    hits_old, hits_new, examples = 0, 0, []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in SKIP_EXT: continue
            try:
                if p.stat().st_size > MAX_BYTES: continue
                t = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            a, b = t.count(old), t.count(new)
            hits_old += a; hits_new += b
            if a and len(examples) < 3:
                examples.append(f"{p.relative_to(root)} ({a})")
    return hits_old, hits_new, examples

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--old', required=True)
    ap.add_argument('--new', required=True)
    ap.add_argument('--root', action='append', default=[], help='label=path')
    ap.add_argument('--governed', nargs='*', default=[], help='تسميات الأسطح الحاكمة')
    a = ap.parse_args()
    if not a.root:
        print('  لا جذور — مرّر --root "label=path"'); return 2
    fails = []
    print(f"  الاسم القديم: «{a.old}» · الجديد: «{a.new}»")
    for spec in a.root:
        if '=' not in spec:
            print(f'  صيغة جذر غير صحيحة: {spec}'); return 2
        label, path = spec.split('=', 1)
        root = Path(path)
        if not root.exists():
            print(f"  ⚠ «{label}»: المسار غير موجود {path}"); continue
        old, new, ex = scan(root, a.old, a.new)
        gov = label in a.governed
        mark = '✗' if (gov and old) else '✓'
        print(f"  {mark} «{label}»{' (حاكم)' if gov else ''}: قديم={old} · جديد={new}"
              + (f" · أمثلة: {', '.join(ex)}" if ex else ''))
        if gov and old:
            fails.append(label)
    if fails:
        print("  النتيجة: بقايا في أسطح حاكمة —", ' · '.join(fails)); return 1
    print("  النتيجة: لا بقايا في الأسطح الحاكمة ✓"); return 0

if __name__ == '__main__':
    sys.exit(main())
