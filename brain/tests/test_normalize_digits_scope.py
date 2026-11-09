#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار نطاق تطبيع الأرقام (ك-562).

العطل المقيس: `tools/normalize_digits.py` كان يزحف على مصادر المهارات، فحوّل
أرقامًا عربية-هندية داخل جدول تحويل مقصود في
`skills/report-surface-and-print-ops/references/legacy/.../verify_range_bidi.py`،
فصار ملف المهارة مختلفًا بين سطح الجذر القانوني وسطح الخادم (انحراف بايت واحد
عبر ثلاثة أسطر) وأوقف بوابة سلامة المهارات G018A.

القاعدة: نطاق التطبيع نصوص القارئ فقط؛ مجلدات `skills/` و`references/` خارج النطاق.

الخروج: 0 سليم · 1 فشل.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

BRAIN = pathlib.Path(__file__).resolve().parent.parent
SKILLS = BRAIN / "skills"
sys.path.insert(0, str(BRAIN / "tools"))

spec = importlib.util.spec_from_file_location("normalize_digits", BRAIN / "tools" / "normalize_digits.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)  # type: ignore[union-attr]


def main() -> int:
    fails: list[str] = []
    scanned = [p.as_posix() for p in mod.targets([str(BRAIN)])]
    leaked = [p for p in scanned if "/skills/" in p]
    if leaked:
        fails.append(f"نطاق التطبيع يزحف على مصادر المهارات: {leaked[:3]}")

    # موجب: سطح نص القارئ داخل النطاق (تقرير اليوم)
    report = BRAIN / "reports" / "2026-11-08-sectioned.md"
    if report.exists() and report.as_posix() not in scanned:
        fails.append("نطاق التطبيع لا يشمل متن التقرير")

    # سالب مباشر: جدول التحويل المقصود في مصدر المهارة يبقى كما هو
    mapping = (SKILLS / "report-surface-and-print-ops" / "references" / "legacy" /
               "live-visual-audit-ops" / "scripts" / "verify_range_bidi.py")
    if mapping.exists():
        text = mapping.read_text(encoding="utf-8", errors="replace")
        if "0123456789" not in text:
            fails.append("جدول الأرقام العربية-الهندية مفقود من مصدر المهارة")

    if fails:
        for item in fails:
            print("   ✘ " + item)
        print("   النتيجة: فشل")
        return 1
    print("   ✔ نطاق التطبيع محصور في نصوص القارئ، وجداول المهارات سليمة")
    print("   النتيجة: سليم")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())