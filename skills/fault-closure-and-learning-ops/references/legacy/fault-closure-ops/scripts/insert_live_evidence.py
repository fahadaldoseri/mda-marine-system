#!/usr/bin/env python3
"""إدراج أدلة تشغيل حيّة في خانة «الإصلاح» أو «الحاجز» لصفوف محدّدة — بلا قصّ وبأمان تكرار.

الاستعمال:
  python3 insert_live_evidence.py --brain <BRAIN> --map evidence.json [--cell barrier|fix]

ملف الأدلة: {"ك-04": "تحقق حي 2026-10-28: python3 validators/check_portable_paths.py → خرج 0", ...}

المبادئ:
  · الدليل يُوضع أول الخانة كي لا يقطعه أي عرض محدود.
  · لا قصّ للخانة — القصّ يفصل الدليل عن نتيجته فيمنع الصف كذبًا.
  · أي إدراج سابق بتاريخ يُزال قبل الإدراج الجديد (العملية مُكرَّرة بأمان).
  · أي معرّف غير موجود = فشل (رمز 2) ولا يُكتم.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REG = 'audit/سجل-الأعطال-والثغرات.md'
PRIOR = re.compile(r'تحقق حي\s*\d{4}-\d{2}-\d{2}[^|]*')
ID_RE = re.compile(r'^\|\s*([^|]+?)\s*\|')


def _root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get('BRAIN_DIR')
    if env and Path(env).is_dir():
        return Path(env)
    p = Path(__file__).resolve()
    for i in range(1, min(6, len(p.parents))):
        c = p.parents[i] / 'brain-marine-news'
        if (c / 'audit').is_dir():
            return c
        if (p.parents[i] / 'audit').is_dir():
            return p.parents[i]
    return p.parents[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--brain')
    ap.add_argument('--map', required=True, help='ملف JSON: معرّف العطل → نصّ الدليل')
    ap.add_argument('--cell', choices=['barrier', 'fix'], default='barrier')
    a = ap.parse_args()

    brain = _root(a.brain)
    register = brain / REG
    if not register.exists():
        print(f'✘ مفقود: {register}')
        return 2
    mapping = json.loads(Path(a.map).read_text(encoding='utf-8'))
    idx = 6 if a.cell == 'barrier' else 5

    lines = register.read_text(encoding='utf-8').splitlines()
    done, missing = [], []
    for ident, evidence in mapping.items():
        hit = False
        for i, l in enumerate(lines):
            m = ID_RE.match(l)
            if not m or m.group(1).strip().split('/')[0] != ident:
                continue
            cells = [c.strip() for c in l.strip('|').split('|')]
            if len(cells) < 8:
                continue
            cells[idx] = (evidence.strip() + ' · ' + PRIOR.sub('', cells[idx]).strip(' ·')).strip(' ·')
            lines[i] = '| ' + ' | '.join(cells) + ' |'
            hit = True
            break
        (done if hit else missing).append(ident)

    register.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'✔ أُدرج دليل حيّ في {len(done)} صفًا: {", ".join(done) if done else "—"}')
    if missing:
        print(f'✘ معرّفات غير موجودة: {", ".join(missing)}')
        return 2
    print('  الخطوة التالية: closure_round.py --apply ثم check_closure.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())