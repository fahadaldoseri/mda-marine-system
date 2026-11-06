#!/usr/bin/env python3
"""يتحقق أن كل لفظ ممنوع يراه الكاتب في ملفات القواعد المضمَّنة في برومت الكتابة.

الاستعمال:
  python3 check_writer_visibility.py --blacklist <style-blacklist.json> --includes <dir> [--key blocking]

الخروج: 0 كل لفظ ممنوع مرئي · 1 ألفاظ غير مرئية · 2 خطأ.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blacklist", required=True)
    ap.add_argument("--includes", required=True, help="مجلد ملفات القواعد المضمَّنة (sections/)")
    ap.add_argument("--key", default="blocking")
    a = ap.parse_args()
    bl, inc = Path(a.blacklist), Path(a.includes)
    if not bl.exists() or not inc.is_dir():
        print("  ✘ مسار القائمة أو مجلد القواعد غير موجود")
        return 2
    d = json.loads(bl.read_text(encoding="utf-8"))
    terms = [str(e.get("term", "")).strip() for e in d.get(a.key, []) if str(e.get("term", "")).strip()]
    blob = "\n".join(f.read_text(encoding="utf-8") for f in inc.glob("*.md"))
    missing = [t for t in terms if t not in blob]
    if missing:
        print(f"  ✘ ألفاظ ممنوعة لا يراها الكاتب ({len(missing)} من {len(terms)}): " + " · ".join(missing[:10]))
        return 1
    print(f"  ✔ كل لفظ ممنوع مرئي للكاتب ({len(terms)} لفظًا · {len(list(inc.glob('*.md')))} ملف قواعد)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
