#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قياس تغطية المصادر: المعتمدة · ما له مسار معلن · ما هو «يدوي» · الفجوة.

الاستخدام:
    python3 measure_coverage.py --brain /path/to/brain [--date YYYY-MM-DD]

يقرأ من المشروع:
  • السجل الحاكم: appendices/source-reliability-40.json   (المعتمدة)
  • جدول المسارات: tools/check_feeds.feeds()               (مسار آلي)
  • tools/source_channels.MANUAL_REFERENCE                 (يدوي)
  • حالة الفحص: feeds/feeds-<date>.status.json             (ناجح/متعذّر)
المخرج: خرج 0 إن كانت التغطية كاملة، وخرج 1 إن وُجدت فجوة (فشل مغلق).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def load(brain: Path, date: str) -> dict:
    sys.path.insert(0, str(brain / 'tools'))
    import check_feeds  # noqa: WPS433
    import source_channels  # noqa: WPS433

    approved = sorted(int(r[0]) for r in json.loads(
        (brain / 'appendices' / 'source-reliability-40.json').read_text(encoding='utf-8')))
    routed = sorted({int(f['num']) for f in check_feeds.feeds()})
    manual = sorted(int(x) for x in source_channels.MANUAL_REFERENCE)

    ok, failed = set(), set()
    status = brain / 'feeds' / f'feeds-{date}.status.json'
    if status.exists():
        live = json.loads(status.read_text(encoding='utf-8'))
        by_num: dict[int, bool] = {}
        for f in live.get('checked_feeds', []):
            n = int(f['num'])
            by_num[n] = by_num.get(n, False) or bool(f['ok'])
        ok = {n for n, good in by_num.items() if good}
        failed = {n for n, good in by_num.items() if not good}

    return {'approved': approved, 'routed': routed, 'manual': manual,
            'ok': sorted(ok), 'failed': sorted(failed), 'status': status.exists()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--brain', required=True)
    ap.add_argument('--date', default=datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    a = ap.parse_args()

    d = load(Path(a.brain), a.date)
    covered = set(d['routed']) | set(d['manual'])
    gap = sorted(set(d['approved']) - covered)
    both = sorted(set(d['routed']) & set(d['manual']))

    print(f'   المعتمدة: {len(d["approved"])} · مسار آلي: {len(d["routed"])} · '
          f'يدوي: {len(d["manual"])} {d["manual"]}')
    if d['status']:
        print(f'   حالة الفحص ({a.date}): ناجح {len(d["ok"])} · متعذّر {len(d["failed"])} {d["failed"]}')
    else:
        print(f'   حالة الفحص ({a.date}): لا ملف — شغّل فحص التغذيات أولًا')
    problems = []
    if gap:
        problems.append(f'فجوة: مصادر معتمدة بلا مسار معلن: {gap}')
    if both:
        problems.append(f'مصادر آليّة ويدوية معًا: {both}')
    if d['status'] and len(d['ok']) + len(d['failed']) + len(d['manual']) != len(d['approved']):
        problems.append('العدّاد لا يغطي كل المصادر المعتمدة')
    for p in problems:
        print(f'   ✘ {p}')
    print(f'   الخلاصة: تغطية كاملة' if not problems else f'   الخلاصة: فجوة ({len(problems)})')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())