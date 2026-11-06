#!/usr/bin/env python3
"""تسجيل عطل في سجل الأعطال + درس في سجل التعلم — بمعرّف تلقائي وصفّ قياسي 12 عمودًا.

الاستعمال:
  python3 record_fault.py --brain <BRAIN> --axis system \
      --symptom "..." --cause "..." --fix "..." --barrier "تحقق حي: <أمر> → خرج 0"
اختياري: --date (افتراضي اليوم) · --cls · --owner · --prefix (افتراضي ك) · --id صريح

المبدأ: لا يُسجَّل عطل بلا سبب جذري ودليل نتيجة في الحاجز، والعملية مُكرَّرة بأمان.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REG = 'audit/سجل-الأعطال-والثغرات.md'
LOG = 'memory/learning-log.jsonl'
OUTCOME = re.compile(r'(خرج\s*\d+|exit\s*\d+|رمز\s*\d+|نجح\s*\d+\s*·?\s*فشل\s*\d+|\d+\s*/\s*\d+|مطابق|بصمة\s*[0-9a-f]{6,})')


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


def next_id(register: Path, prefix: str) -> str:
    txt = register.read_text(encoding='utf-8')
    nums = [int(m.group(1)) for m in re.finditer(rf'^\|\s*{re.escape(prefix)}-(\d+)\s*\|', txt, re.M)]
    return f'{prefix}-{max(nums) + 1 if nums else 1}'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--brain')
    ap.add_argument('--axis', default='system')
    ap.add_argument('--cls', default='')
    ap.add_argument('--symptom', required=True)
    ap.add_argument('--cause', required=True)
    ap.add_argument('--fix', required=True)
    ap.add_argument('--barrier', required=True)
    ap.add_argument('--owner', default='—')
    ap.add_argument('--prefix', default='ك')
    ap.add_argument('--id', dest='ident')
    ap.add_argument('--date', default=datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    a = ap.parse_args()

    brain = _root(a.brain)
    register, log = brain / REG, brain / LOG
    for p in (register, log):
        if not p.exists():
            print(f'✘ مفقود: {p}')
            return 2
    if not OUTCOME.search(a.barrier):
        print('✘ الحاجز بلا دليل نتيجة قابل لإعادة التشغيل — أضف «خرج 0» أو «نجح N · فشل 0» أو «مطابق».')
        return 2

    txt = register.read_text(encoding='utf-8')
    ident = a.ident or next_id(register, a.prefix)
    key = a.symptom.strip()[:60]
    if any(key and key in l and l.startswith(f'| {ident}') for l in txt.splitlines()):
        print(f'· الصف {ident} مسجَّل بالعَرَض نفسه — لا تكرار.')
        return 0

    fix_txt = a.fix if re.search(r'منفَّذ|جزئي|لم يبدأ', a.fix) else f'منفَّذ: {a.fix}'
    bar_txt = a.barrier if re.search(r'مطبَّق|فعّال|معلّق|مؤجَّل', a.barrier) else f'مطبَّق: {a.barrier}'
    symptom = f'{a.cls}: {a.symptom}' if a.cls else a.symptom
    row = [ident, a.date, a.axis, symptom, a.cause, fix_txt, bar_txt, '—',
           'منفَّذ', 'تحقق تشغيلي ناجح', 'مطبَّق', 'مغلق']
    register.write_text(txt.rstrip() + '\n| ' + ' | '.join(row) + ' |\n', encoding='utf-8')

    entry = {
        'ts': datetime.now(timezone.utc).isoformat(), 'entry_kind': 'fault', 'cls': a.cls,
        'status': 'مغلق', 'status_norm': 'مغلق', 'fault_id': ident, 'symptom': a.symptom,
        'root_cause': a.cause, 'lesson': f'القاعدة التي تغيّرت: {bar_txt}', 'action': a.fix,
        'barrier': bar_txt, 'evidence': bar_txt, 'owner': a.owner,
    }
    with log.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f'✔ سُجّل {ident} في السجل وسجل التعلم · الدليل: {OUTCOME.search(a.barrier).group(0)}')
    print('  الخطوة التالية: closure_round.py --apply ثم check_closure.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())