#!/usr/bin/env python3
"""حارس تكامل المزامنة: لا صفّ في المصفوفة خارج السجل، ولا تكرار، ولا انحدار في العدّ.

يفشل مغلقًا (rc=2) عند أي تباعد، ويحفظ خط الأساس في audit/measurements/ledger-baseline.json.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys


FAULT_ROW = re.compile(r'^\|\s*[\u0621-\u064A]{1,3}-\d')


def main() -> int:
    root = pathlib.Path(sys.argv[sys.argv.index('--brain') + 1] if '--brain' in sys.argv else '.')
    log = root / 'audit/سجل-الأعطال-والثغرات.md'
    mat = root / 'audit/traceability.json'
    base_p = root / 'audit/measurements/ledger-baseline.json'
    ids = [l.strip().strip('|').split('|')[0].strip()
           for l in log.read_text(encoding='utf-8').splitlines() if FAULT_ROW.match(l)]
    rows = json.loads(mat.read_text(encoding='utf-8'))
    mids = [r['fault_id'] for r in (rows['rows'] if isinstance(rows, dict) else rows)]
    problems = []
    outside = sorted({m for m in mids if m not in set(ids)})
    if outside:
        problems.append(f'صفوف في المصفوفة خارج السجل: {len(outside)} → {", ".join(outside[:6])}')
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        problems.append(f'معرّفات مكررة في السجل: {len(dups)} → {", ".join(dups[:6])}')
    base = json.loads(base_p.read_text(encoding='utf-8')) if base_p.exists() else {}
    prev = int(base.get('log_rows', 0))
    if len(ids) < prev:
        problems.append(f'انحدار في عدّ الصفوف: {prev} ← {len(ids)}')
    if not problems and len(ids) >= prev:
        base_p.parent.mkdir(parents=True, exist_ok=True)
        base_p.write_text(json.dumps({'log_rows': len(ids), 'matrix_rows': len(mids),
                                      'updated': '2026-11-09'}, ensure_ascii=False, indent=1) + '\n',
                          encoding='utf-8')
    print(f'   السجل: {len(ids)} · المصفوفة: {len(mids)} · خط الأساس السابق: {prev}')
    if problems:
        for x in problems:
            print(f'   ✘ {x}')
        return 2
    print('   ✔ تكامل المزامنة سليم: لا صفّ خارج السجل · لا تكرار · لا انحدار')
    return 0


if __name__ == '__main__':
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
