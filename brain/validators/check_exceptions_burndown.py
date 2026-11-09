#!/usr/bin/env python3
"""حارس ميزانية الاستثناءات: يمنع الزيادة ويُنبّه قبل انتهاء المهلة.

الاستثناء قبول مخاطر مؤقت بمهلة ومالك (لا إغلاقًا). لذلك يجب أن:
1) لا يزيد عدد الاستثناءات عن خط الأساس المسجَّل (زيادة = صف جديد بلا إصلاح).
2) لا يبقى استثناء واحد تنتهي مهلته خلال 30 يومًا بلا إغلاق.

الاستخدام: python3 validators/check_exceptions_burndown.py --root . [--baseline-write]
رموز الخروج: 0 سليم · 2 مانع · 3 خطأ إعداد.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

SOON_DAYS = 30
EXC = 'audit/closure-exceptions.json'
BASE = 'audit/measurements/exceptions-baseline.json'


def main() -> int:
    ap = argparse.ArgumentParser(description='حارس ميزانية الاستثناءات')
    ap.add_argument('--root', default='.')
    ap.add_argument('--baseline-write', action='store_true', help='تثبيت خط الأساس من القياس الحالي')
    ap.add_argument('--json', action='store_true', help='إخراج ملخص JSON بدل السطور البشرية')
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    exc_p = root / EXC
    if not exc_p.is_file():
        print(f'✘ ملف الاستثناءات مفقود: {exc_p}')
        return 3
    entries = json.loads(exc_p.read_text(encoding='utf-8'))['entries']
    count = len(entries)
    today = dt.date.today()
    soon = []
    for e in entries:
        exp = (e.get('expires_at') or '')[:10]
        if not exp:
            continue
        try:
            d = dt.date.fromisoformat(exp)
        except ValueError:
            continue
        if (d - today).days <= SOON_DAYS:
            soon.append(f"{e.get('fault_id')} تنتهي {exp}")

    base_p = root / BASE
    baseline = None
    if base_p.is_file():
        baseline = json.loads(base_p.read_text(encoding='utf-8'))
    if a.baseline_write or baseline is None:
        base_p.parent.mkdir(parents=True, exist_ok=True)
        base_p.write_text(json.dumps({'date': today.isoformat(), 'count': count,
                                      'note_ar': 'خط أساس عدد الاستثناءات؛ الزيادة عليه مانع.'},
                                     ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if baseline is None and not a.baseline_write:
            print(f'   ثُبّت خط الأساس: {count} استثناء بتاريخ {today.isoformat()} (قياس أول)')

    fails = []
    if baseline and count > baseline.get('count', count):
        fails.append(f'زيادة الاستثناءات: {count} مقابل خط الأساس {baseline["count"]}')
    if soon:
        fails.append(f'استثناءات تنتهي خلال {SOON_DAYS} يومًا بلا إغلاق: {len(soon)}')

    summary = {'count': count, 'baseline': baseline.get('count') if baseline else None,
               'expiring_soon': len(soon), 'failures': fails}
    if a.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f'   الاستثناءات: {count} · خط الأساس: {baseline.get("count") if baseline else "جديد"} · تنتهي قريبًا: {len(soon)}')
    if fails:
        for f in fails:
            print(f'   ✘ {f}')
        for s in soon[:10]:
            print(f'     - {s}')
        return 2
    print('   ✔ ميزانية الاستثناءات سليمة: لا زيادة ولا مهلة على وشك الانتهاء')
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:
        def run(fn):
            raise SystemExit(fn())
    run(main)
