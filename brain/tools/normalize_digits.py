#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""توحيد الأرقام: تحويل الأرقام العربية الهندية (U+0660..U+0669) والفواصل العربية إلى إنجليزية.
قرار صاحب القرار — 20 أكتوبر 2026: اعتماد الأرقام الإنجليزية (0-9) في المشروع بشكل كامل.
المحارف مكتوبة بأكواد \\u كي لا تتأثر بترميز التحرير أو النسخ.
الاستخدام: python3 tools/normalize_digits.py [--check] [جذور...]
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # مجلد brain
BASE = HERE.parent                                      # جذر مساحة العمل
ROOTS = [str(BASE / "brain-marine-news"), str(BASE / "seawatch")]
if not Path(ROOTS[0]).exists():                          # عند التشغيل داخل نسخة مستنسخة
    ROOTS = [str(HERE)] + ([str(HERE.parent / "site")] if (HERE.parent / "site").exists() else [])
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".pytest_cache", "shots", "logs",
             "archive", "originals", "templates", ".history", ".manus-jobs",
             "terminal_full_output", "backup-repo", "web"}
SKIP_FILES = {"tools/normalize_digits.py", "validators/check_numerals.py"}
BINARY = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".zip", ".gz", ".tgz", ".woff", ".woff2",
          ".ttf", ".mp4", ".ico", ".xlsx", ".db", ".pyc"}
TABLE = {0x0660 + i: str(i) for i in range(10)}          # \\u0660..\\u0669 → 0-9
TABLE.update({0x066B: ".", 0x066C: ",", 0x066A: "%"})     # \\u066B  \\u066C  \\u066A
ARABIC_ANY = [chr(0x0660 + i) for i in range(10)] + [chr(0x066B), chr(0x066C), chr(0x066A)]


def to_latin(text: str) -> str:
    """يحوّل الأرقام العربية الهندية والفواصل العربية إلى نظيرها اللاتيني (قرار 20 أكتوبر 2026)."""
    return text.translate(TABLE)


def targets(roots):
    for root in roots:
        rp = Path(root)
        if not rp.exists():
            continue
        for d, dirs, files in os.walk(rp):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                p = Path(d, f)
                if p.suffix.lower() in BINARY:
                    continue
                if any(str(p).endswith(x) for x in SKIP_FILES):
                    continue
                if "/archive/" in p.as_posix() or "/originals/" in p.as_posix():
                    continue
                yield p


def scan(p: Path) -> int:
    try:
        t = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return 0
    return sum(t.count(c) for c in ARABIC_ANY)


def main() -> int:
    args = sys.argv[1:]
    check = "--check" in args
    roots = [a for a in args if not a.startswith("--")] or ROOTS
    files = occ = 0
    details = []
    for p in targets(roots):
        n = scan(p)
        if not n:
            continue
        occ += n; files += 1
        details.append((str(p), n))
        if not check:
            p.write_text(p.read_text(encoding="utf-8").translate(TABLE), encoding="utf-8")
    for f, n in sorted(details, key=lambda x: -x[1])[:12]:
        print(f"   {n:6d}  {f}")
    if check:
        print(f"  النتيجة: {occ} رقمًا عربيًا في {files} ملفًا")
        return 1 if occ else 0
    print(f"  ✔ حُوِّل {occ} رقمًا في {files} ملفًا إلى الأرقام الإنجليزية")
    return 0


if __name__ == "__main__":
    sys.exit(main())
