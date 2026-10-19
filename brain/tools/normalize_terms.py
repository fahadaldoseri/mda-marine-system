#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
توحيد المصطلحين المعتمدين في 16 أكتوبر 2026 على كل المخرجات:
  «راية» → «علم» (Flag)
  «سائبة/سائب/ناقلة سوائب/السوائب» → «سفينة بضائع جافة (Bulk carrier)» ثم «سفينة البضائع الجافة»
يستثني ملفات القاعدة نفسها (المعجم ومدقّق اللغة) حتى لا تُمحى القاعدة.
الاستخدام: python3 tools/normalize_terms.py [--apply]
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")
import re
import sys
from pathlib import Path

ROOTS = [
    Path(f"{BRAIN}/reports"),
    Path(f"{BRAIN}/web"),
    Path(f"{BRAIN}/cumulative-2026"),
    Path(f"{BRAIN}/historical"),
    Path(f"{BRAIN}/docs"),
    Path(f"{BRAIN}/feeds"),
    Path(f"{BRAIN}/sources"),
    Path(f"{SITE}/sources"),
    Path(f"{SITE}/generator"),
]
SKIP_PARTS = ("/backups/", "/brain-backup/", "/audit/", "/docx/", "/__pycache__/",
              "/reports/latest/", "/validators/")
SKIP_FILES = {"terminology.md", "normalize_terms.py", "check_language.py",
              "fix_gfs_docx.py", "terminology-map.md"}
EXTS = {".md", ".json", ".py", ".txt", ".html", ".jsonl"}

RULES = [
    (r"ناقلة سوائب \(سفينة شحن سائب\)", "سفينة بضائع جافة (Bulk carrier)"),
    (r"ناقلة سوائب \(Bulk carrier\)", "سفينة بضائع جافة (Bulk carrier)"),
    (r'"ناقلة سوائب": "سفينة شحن سائب \(Bulk carrier\)"', '"سائبة": "سفينة بضائع جافة (Bulk carrier)"'),
    (r"ناقلة السوائب", "سفينة البضائع الجافة"),
    (r"ناقلة سوائب", "سفينة بضائع جافة"),
    (r"ناقلة سائبة", "سفينة بضائع جافة"),
    (r"سفينة بضائع سائبة", "سفينة بضائع جافة"),
    (r"سفينة الشحن السائبة", "سفينة البضائع الجافة"),
    (r"سفينة سائبة", "سفينة بضائع جافة"),
    (r"غرق السائبة «", "غرق سفينة البضائع الجافة «"),
    (r"والسوائب", "والبضائع الجافة"),
    (r"و«السائبة»", "و«البضائع الجافة»"),
    (r"راية أنتيغوا", "علم أنتيغوا"),
    (r"راية سنغافورة", "علم سنغافورة"),
    (r"راية غير معلنة", "علم غير معلنة"),
    (r"الراية", "العلم"),
    (r"الراية", "العلم"),
    # دفعة مكمّلة — أنماط متفرقة ظهرت في السجلات
    (r"سفينة شحن سائب \(Bulk carrier\) تنقل", "سفينة تنقل"),
    (r"ناقلة سائب \(bulk carrier\)", "سفينة بضائع جافة (Bulk carrier)"),
    (r"ناقلة بضائع سائبة", "سفينة بضائع جافة"),
    (r"سفينة شحن سائبة", "سفينة بضائع جافة"),
    (r"والسائبات", "والبضائع الجافة"),
    (r"راية", "علم"),
]


def sweep(apply=False):
    total = {}
    for root in ROOTS:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.suffix not in EXTS:
                continue
            sp = str(p)
            if any(x in sp for x in SKIP_PARTS) or p.name in SKIP_FILES:
                continue
            try:
                s = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            o = s
            n = 0
            for pat, rep in RULES:
                s, k = re.subn(pat, rep, s)
                n += k
            if n and s != o:
                total[sp] = n
                if apply:
                    p.write_text(s, encoding="utf-8")
    return total


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    t = sweep(apply)
    print(("طُبِّق على " if apply else "سيُطبَّق على ") + f"{len(t)} ملفًا · {sum(t.values())} استبدالًا")
    for k, v in list(t.items())[:25]:
        print(f"   {v:>3}  {k}")
    if not apply:
        print("\n(تجربة بلا كتابة — أضف --apply للتنفيذ)")
