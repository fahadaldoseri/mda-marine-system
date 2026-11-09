#!/usr/bin/env python3
"""حارس تغطية المُفعِّلات: يمنع انحدار نسبة الأعطال ذات المُفعِّل، ويحفظ خط الأساس."""
from __future__ import annotations

import json
import pathlib
import re
import sys

FAULT = re.compile(r'^\|\s*[\u0621-\u064A]{1,3}-\d')
KEYS = ('مطبَّق', 'فعّال', 'حارس', 'بوابة', 'اختبار')


def main() -> int:
    root = pathlib.Path(sys.argv[sys.argv.index('--brain') + 1] if '--brain' in sys.argv else '.')
    rows = []
    for line in (root / 'audit/سجل-الأعطال-والثغرات.md').read_text(encoding='utf-8').splitlines():
        if FAULT.match(line):
            c = [x.strip() for x in line.strip().strip('|').split('|')]
            if len(c) >= 12:
                rows.append(c)
    with_env = [c for c in rows if any(k in c[10] for k in KEYS)]
    pct = round(len(with_env) / max(1, len(rows)) * 100, 1)
    base_p = root / 'audit/measurements/enforcer-baseline.json'
    prev = json.loads(base_p.read_text(encoding='utf-8'))['percent'] if base_p.exists() else 0.0
    print(f'   التغطية: {len(with_env)}/{len(rows)} = {pct}% · خط الأساس: {prev}%')
    if pct < prev:
        print('   ✘ انحدار في تغطية المُفعِّلات')
        return 2
    base_p.parent.mkdir(parents=True, exist_ok=True)
    base_p.write_text(json.dumps({'percent': pct, 'rows': len(rows), 'updated': '2026-11-09'},
                                 ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('   ✔ لا انحدار')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
