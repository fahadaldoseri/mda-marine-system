#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يبني/يحدّث قائمة فحص OFAC من السفن المذكورة في إصدار اليوم.

الغرض: تنفيذ قاعدة «لا سفينة بلا فحص» — القائمة لا تبقى ثابتة يدويًا.
المخرج: watchlist/ofac-targets.txt (يُدمج الجديد مع القديم بلا حذف)
الاستخدام: python3 tools/ofac_targets_from_report.py --date 2026-10-19
"""
from __future__ import annotations
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vessel_names import from_report  # noqa: E402

B = Path(f'{BRAIN}')
TARGETS = B / 'watchlist' / 'ofac-targets.txt'


def load_existing() -> list[str]:
    if not TARGETS.exists():
        return []
    return [l.strip() for l in TARGETS.read_text(encoding='utf-8').splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    a = ap.parse_args()

    report_md = B / 'reports' / f'{a.date}-sectioned.md'
    report_meta = B / 'web' / 'meta' / f'{a.date}.json'
    if not report_md.exists() and not report_meta.exists():
        print(f"  ✘ تعذر استخراج أهداف OFAC: لا يوجد تقرير أو واجهة للإصدار {a.date}")
        return 2
    if report_meta.exists():
        try:
            json.loads(report_meta.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            print(f"  ✘ تعذر استخراج أهداف OFAC: واجهة الإصدار غير صالحة ({exc})")
            return 2
    existing = load_existing()
    try:
        vessels = from_report(a.date)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"  ✘ تعذر استخراج أهداف OFAC من الإصدار {a.date} ({exc})")
        return 2
    if not vessels:
        print(f"  · لا سفن مُعرَّفة في إصدار {a.date} — لا إضافة")
    added = [v for v in vessels if v not in existing]
    merged = existing + added
    TARGETS.parent.mkdir(parents=True, exist_ok=True)
    TARGETS.write_text("\n".join(merged) + ("\n" if merged else ""), encoding='utf-8')
    print(f"  سفن الإصدار: {len(vessels)} · مضاف جديد: {len(added)} · إجمالي القائمة: {len(merged)}")
    for v in added:
        print(f"   ＋ {v}")
    if vessels:
        print("  القائمة: " + " · ".join(vessels))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
