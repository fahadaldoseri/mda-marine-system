#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة تغطية فحص العقوبات: كل سفينة مذكورة في الإصدار لها نتيجة فحص OFAC.

رموز الخروج: 0 = مكتمل · 1 = تحذير (تغطية جزئية) · 2 = مانع (سفينة بلا فحص)
الاستخدام: python3 validators/check_ofac_coverage.py --date 2026-10-19
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from vessel_names import from_report  # noqa: E402

B = Path('/home/ubuntu/brain-marine-news')
SCREEN = B / 'archive' / 'ofac-screen-latest.json'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--report', default='')
    a = ap.parse_args()

    vessels = from_report(a.date)
    print(f"=== بوابة تغطية فحص العقوبات — {a.date} ===")
    if not vessels:
        print("  ✔ لا سفن مُعرَّفة في الإصدار — لا فحص مطلوب")
        return 0

    if not SCREEN.exists():
        print("  ✘ لا يوجد ملف نتيجة فحص OFAC: archive/ofac-screen-latest.json")
        return 2
    try:
        data = json.loads(SCREEN.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f"  ✘ ملف نتيجة الفحص ليس JSON صالحًا ({e})")
        return 2
    results = {str(r.get('target', '')).upper(): r.get('result') for r in data.get('results', [])}

    missing, matches, reviews = [], [], []
    for v in vessels:
        res = results.get(v.upper())
        if res is None:
            missing.append(v)
            print(f"   ✘ بلا نتيجة: {v}")
        elif res == 'match':
            matches.append(v)
            print(f"   ✘ تطابق إدراج: {v} — يحتاج قرارًا قبل النشر")
        elif res == 'review':
            reviews.append(v)
            print(f"   ◐ تطابق جزئي يحتاج تحققًا يدويًا: {v}")
        else:
            print(f"   ✔ لا تطابق: {v}")

    if matches:
        print(f"  النتيجة: مانع — تطابق إدراج صريح: {', '.join(matches)}")
        return 2
    if missing:
        print(f"  النتيجة: مانع — {len(missing)} سفينة بلا نتيجة فحص")
        return 2
    if reviews:
        print(f"  النتيجة: تحذير — {len(reviews)} سفينة بتطابق جزئي يحتاج تحققًا")
        return 1
    print("  النتيجة: مكتمل — كل سفن الإصدار لها نتيجة فحص")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())