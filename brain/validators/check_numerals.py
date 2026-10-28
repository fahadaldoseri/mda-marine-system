#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة الأرقام: تمنع الأرقام العربية الهندية (U+0660..U+0669) والفواصل العربية (\\u066B \\u066C \\u066A).
قرار صاحب القرار — 20 أكتوبر 2026: اعتماد الأرقام الإنجليزية (0-9) في المشروع بشكل كامل.
رموز الخروج: 0 = مطابق · 1 = مواضع في ملفات سجلّية (تنبيه) · 2 = مخالفة مانعة توقف التسليم.
الاستخدام: python3 validators/check_numerals.py [--roots ..] [--advisory ..]
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAIN = Path(os.environ.get("BRAIN_DIR") or ROOT)
SITE = Path(os.environ.get("SITE_DIR") or (ROOT.parent / "seawatch"))
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".pytest_cache", "shots"}
BINARY = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".zip", ".gz", ".tgz", ".woff", ".woff2",
          ".ttf", ".mp4", ".ico", ".xlsx", ".db", ".pyc"}
ARABIC_ANY = [chr(0x0660 + i) for i in range(10)] + [chr(0x066B), chr(0x066C), chr(0x066A)]
# نطاقات ملزمة: مصدر النظام ومخرجاته ومولّد الموقع ومصادره
MANDATORY = ["sections", "appendices", "validators", "tools", "reports", "web", "memory", "cumulative-2026",
             "templates", "feeds", "watchlist", "state"]
MANDATORY_SITE = ["generator", "sources", "dist", "server"]
# سجلّات وتواريخ وأصول حرفية: تنبيه لا منع
ADVISORY = ["docs", "notes", "audit", "research", "archive", "logs"]


def nums(p: Path) -> int:
    try:
        t = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return 0
    return sum(t.count(c) for c in ARABIC_ANY)


def walk(root: Path, subs):
    out = []
    for s in subs:
        base = root / s
        if not base.exists():
            continue
        if base.is_file():
            out.append(base); continue
        for d, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                p = Path(d, f)
                if p.suffix.lower() not in BINARY:
                    out.append(p)
    return out


def main() -> int:
    print("=== بوابة الأرقام — المعتمد: 0-9 لاتينية (وقرار 20 أكتوبر 2026) ===")
    blockers, warnings = [], []
    for p in walk(BRAIN, MANDATORY):
        n = nums(p)
        if n:
            blockers.append(f"{p.relative_to(BRAIN.parent)} ← {n} محرفًا عربيًا")
    for p in walk(SITE, MANDATORY_SITE):
        n = nums(p)
        if n:
            blockers.append(f"{p.relative_to(SITE.parent)} ← {n} محرفًا عربيًا")
    for p in walk(BRAIN, ADVISORY):
        n = nums(p)
        if n:
            warnings.append(f"{p.relative_to(BRAIN.parent)} ← {n} محرفًا عربيًا")
    for w in warnings[:10]:
        print(f"   ◐ تنبيه (سجلّي/أرشيفي): {w}")
    for b in blockers[:20]:
        print(f"   ✘ مخالفة مانعة: {b}")
    if blockers:
        print(f"  النتيجة: مانع — {len(blockers)} ملفًا فيه أرقام عربية. الإصلاح: python3 tools/normalize_digits.py")
        return 2
    if warnings:
        print(f"  النتيجة: مطابق في الملفات الملزمة · {len(warnings)} ملفًا سجلّيًا فيه أرقام عربية (تنبيه)")
        return 1
    print("  النتيجة: مطابق — لا أرقام عربية في الملفات الملزمة")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
