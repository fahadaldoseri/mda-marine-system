#!/usr/bin/env python3
"""بوابة قاعدة النقاط في المصدر — 19 أكتوبر 2026.

تمنع عودة التعداد المكتوب فقرة متصلة (فتظهر النقاط مطموسة في الصفحة والورق):
  1) حقول أهم الأخبار المتعلقة بالأمن البحري في ملف الواجهة يجب أن تكون قائمة نصية لا نصًّا بفواصل.
  2) «ما يُراقب خلال 24 ساعة» بين 3 و4 نقاط.
  3) فقرات المصدر التي تحمل تعدادًا (3 فواصل أو أكثر) تُرصد كتحذير لتُحوَّل إلى نقاط.

رموز الخروج: 0 سليم · 1 تحذير · 2 مانع.
الاستخدام: python3 validators/check_points_rule.py --md reports/<date>-sectioned.md --meta web/meta/<date>.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ("changed", "action", "watch")
SEPS = ("،", "؛", ";")
WATCH_MIN, WATCH_MAX = 3, 4


def items_of(value) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [str(value).strip()] if value else []


def check_meta(meta_path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    if not meta_path.exists():
        errors.append(f"ملف الواجهة غير موجود: {meta_path}")
        return errors, warns
    d = json.loads(meta_path.read_text(encoding="utf-8"))
    dc = d.get("decision_card") or {}
    for f in FIELDS:
        v = dc.get(f)
        if v is None:
            continue
        if isinstance(v, str):
            seps = sum(v.count(s) for s in SEPS)
            if seps >= 1 and len(re.split(r"[،؛;]", v)) >= 2:
                errors.append(
                    f"حقل البطاقة «{f}» نصٌّ بفواصل لا قائمة — اكتبه قائمة نصية في المصدر.")
            continue
        if isinstance(v, list) and len(v) == 0:
            warns.append(f"حقل البطاقة «{f}» قائمة فارغة.")
    w = dc.get("watch")
    n = len(items_of(w))
    if n and not (WATCH_MIN <= n <= WATCH_MAX):
        errors.append(
            f"«ما يُراقب خلال 24 ساعة» فيه {n} نقاط — الملزم {WATCH_MIN}–{WATCH_MAX} نقاط.")
    for f in FIELDS:
        for i, it in enumerate(items_of(dc.get(f)), 1):
            if len(it.split()) > 20:
                warns.append(f"النقطة {i} في «{f}» تجاوزت 20 كلمة ({len(it.split())}).")
    return errors, warns


def check_md(md_path: Path) -> list[str]:
    warns: list[str] = []
    if not md_path.exists():
        return [f"ملف المصدر غير موجود: {md_path}"]
    text = md_path.read_text(encoding="utf-8")
    for i, raw in enumerate(text.split("\n"), 1):
        line = raw.strip()
        if not line or line.startswith(("-", "#", "|", ">", "*", "**", "<!--")):
            continue
        if len(line) < 180:
            continue
        seps = sum(line.count(s) for s in ("،", "؛"))
        if seps >= 3:
            warns.append(
                f"سطر {i}: فقرة تحمل تعدادًا ({seps} فاصلًا) — حوّلها نقاطًا (`- ` لكل بند).")
    return warns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--meta", required=True)
    a = ap.parse_args()

    errors, warns = check_meta(Path(a.meta) if Path(a.meta).is_absolute() else ROOT / a.meta)
    warns += check_md(Path(a.md) if Path(a.md).is_absolute() else ROOT / a.md)

    print("=== بوابة قاعدة النقاط في المصدر ===")
    for w in warns:
        print(f"  ! {w}")
    for e in errors:
        print(f"  ✘ {e}")
    if errors:
        print(f"النتيجة: مانع — {len(errors)} مخالفة · {len(warns)} تحذير")
        return 2
    if warns:
        print(f"النتيجة: مقبول مع تحذير — {len(warns)} تحذير")
        return 1
    print("النتيجة: مجتاز — النقاط مكتوبة في المصدر كما تلزم القاعدة")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
