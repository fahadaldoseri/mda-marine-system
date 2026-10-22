#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فاحص الانحراف عن خط الأساس الرسمي (virgin).

يقارن بصمات ملفات التصميم والبوابات المعتمدة في بيان خط الأساس بالواقع الحالي،
ويُنبّه عند أي تغيير. تنبيهي بطبيعته: لا يوقف التسليم، بل يمنع أن يتغيّر شكل
التقرير الرسمي دون قرار موثَّق.

الاستخدام:
  python3 tools/check_baseline.py                 # تقرير فقط (رمز 0 دائمًا)
  python3 tools/check_baseline.py --strict        # رمز 2 عند أي انحراف
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
BRAIN = Path(os.environ.get("BRAIN_DIR") or _ROOT)


def _tree(env, base, *names):
    v = os.environ.get(env)
    if v:
        return Path(v)
    for n in names:
        c = base.parent / n
        if c.is_dir():
            return c
    return base.parent / names[0]


SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")
MANIFEST = BRAIN / "templates" / "approved-pdf" / "BASELINE-virgin-2026-10-23.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="رمز 2 عند أي انحراف")
    args = ap.parse_args()
    if not MANIFEST.is_file():
        print(f"  ✘ بيان خط الأساس غير موجود: {MANIFEST}")
        return 2 if args.strict else 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    same, changed, missing = [], [], []
    for rel, meta in (man.get("files") or {}).items():
        f = (BRAIN / rel) if rel.startswith(("tools/", "validators/", "sections/", "templates/", "appendices/", "docs/")) else (SITE / rel)
        if not f.is_file():
            missing.append(rel)
        elif sha256(f) == meta.get("sha256"):
            same.append(rel)
        else:
            changed.append(rel)
    print(f"خط الأساس: {man.get('baseline')} · {man.get('on')} · {man.get('status','')}")
    print(f"  مطابق: {len(same)} ملفًا · متغيّر: {len(changed)} · مفقود: {len(missing)}")
    for r in changed:
        print(f"    • متغيّر: {r}")
    for r in missing:
        print(f"    • مفقود: {r}")
    if changed or missing:
        print("  ⚠ انحراف عن النسخة الرسمية — إن كان التغيير مقصودًا فحدِّث بيان خط الأساس بقرار موثَّق.")
        return 2 if args.strict else 1
    print("  ✔ لا انحراف عن خط الأساس الرسمي")
    return 0


if __name__ == "__main__":
    sys.exit(main())