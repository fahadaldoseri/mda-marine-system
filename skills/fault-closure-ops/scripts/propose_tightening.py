#!/usr/bin/env python3
"""اقتراح تشديد ذاتي للحارس — يقرأ السجل ويستخرج أصناف الثغرات التي يجب أن يُضاف لها اختبار سلبي.

الاستعمال:
  python3 propose_tightening.py --brain <BRAIN> [--json]

المخرَج: قائمة تشديدات مرتّبة بالأولوية، كل بند مع اختبار سلبي مقترح جاهز للإدراج في test_closure_gate.py.
المنطق: كل صنف عطل ظهر مرة يمكن أن يعود؛ الحارس يجب أن يمنعه قبل أن يعود.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

REG = 'audit/سجل-الأعطال-والثغرات.md'
LOG = 'memory/learning-log.jsonl'
OUTCOME = re.compile(r'خرج\s*\d+|exit\s*\d+|رمز\s*\d+|نجح\s*\d+|فاشل\s*\d+|\d+\s*/\s*\d+|مطابق|بصمة\s*[0-9a-f]{6,}')
STATES = {'مغلق', 'مفتوح', 'بانتظار التحقق', 'موروث غير مثبت'}
ABSPATH = re.compile(r'(?<![\w/])/(?:home|Users|opt|var|srv)/')


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
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    brain = _root(a.brain)
    reg = brain / REG
    if not reg.exists():
        print(f'✘ مفقود: {reg}')
        return 2

    rows, ids, states = [], [], Counter()
    for l in reg.read_text(encoding='utf-8').splitlines():
        if not l.startswith('|'):
            continue
        c = [x.strip() for x in l.strip('|').split('|')]
        if len(c) < 8 or not re.match(r'^[كزعثم]-\d+', c[0]):
            continue
        rows.append(c)
        ids.append(c[0])
        states[c[-1]] += 1

    lessons = set()
    log = brain / LOG
    if log.exists():
        for l in log.read_text(encoding='utf-8').splitlines():
            try:
                lessons.add(str(json.loads(l).get('fault_id', '')).split('/')[0])
            except Exception:
                pass

    proposals = []
    closed_no_evidence = [c[0] for c in rows if c[-1] == 'مغلق' and not OUTCOME.search(f'{c[5]} {c[6]}')]
    if closed_no_evidence:
        proposals.append({
            'priority': 1, 'class': 'إغلاق بلا دليل نتيجة',
            'count': len(closed_no_evidence), 'sample': closed_no_evidence[:5],
            'test': "assert gate({'state': 'مغلق', 'fix': 'منفَّذ: إصلاح', 'barrier': 'مطبَّق: قاعدة'}) == 2",
        })
    unknown = {s: n for s, n in states.items() if s not in STATES and s not in ('—', '')}
    if unknown:
        proposals.append({
            'priority': 1, 'class': 'حالة خارج المفردات المعتمدة',
            'count': sum(unknown.values()), 'sample': list(unknown)[:5],
            'test': "assert gate({'state': 'فعّال'}) == 2   # رمز حاجز في خانة الحالة",
        })
    dup = [i for i, n in Counter(ids).items() if n > 1]
    if dup:
        proposals.append({
            'priority': 2, 'class': 'معرّفات مكرّرة',
            'count': len(dup), 'sample': dup[:5],
            'test': "assert duplicate_ids(register) == []",
        })
    no_lesson = [c[0] for c in rows if c[0] not in lessons and c[-1] == 'مغلق']
    if no_lesson:
        proposals.append({
            'priority': 2, 'class': 'صفّ مغلق بلا درس مطابق',
            'count': len(no_lesson), 'sample': no_lesson[:5],
            'test': "assert gate({'state': 'مغلق', 'lesson_id': 'ك-999'}) == 2",
        })
    abspath_rows = [c[0] for c in rows if ABSPATH.search(f'{c[5]} {c[6]}')]
    if abspath_rows:
        proposals.append({
            'priority': 2, 'class': 'مسار مطلق في نصّ الإصلاح أو الحاجز',
            'count': len(abspath_rows), 'sample': abspath_rows[:5],
            'test': "run('check_portable_paths.py') == 0",
        })
    dash_fix = [c[0] for c in rows if 'منفَّذ' not in c[5] and c[-1] == 'مغلق']
    if dash_fix:
        proposals.append({
            'priority': 3, 'class': 'إصلاح بلا كلمة «منفَّذ» في صفّ مغلق',
            'count': len(dash_fix), 'sample': dash_fix[:5],
            'test': "assert pick('منفَّذ — كذا', POLICY['قاعدة_الإصلاح']) == 'منفَّذ'",
        })

    if a.json:
        print(json.dumps({'rows': len(rows), 'states': dict(states), 'proposals': proposals}, ensure_ascii=False, indent=2))
        return 0
    print(f'  الصفوف: {len(rows)} · الحالات: {dict(states)} · الدروس: {len(lessons)}')
    if not proposals:
        print('  ✔ لا تشديدات مقترحة — الحارس يغطي كل الأصناف المرصودة.')
        return 0
    for p in sorted(proposals, key=lambda x: x['priority']):
        print(f"  [{p['priority']}] {p['class']} — {p['count']} حالة · مثال: {', '.join(p['sample'])}")
        print(f"       اختبار سلبي مقترح: {p['test']}")
    print('  الخطوة: أضف كل اختبار إلى test_closure_gate.py ثم شغّله — التشديد لا التخفيف.')
    return 0


if __name__ == '__main__':
    sys.exit(main())