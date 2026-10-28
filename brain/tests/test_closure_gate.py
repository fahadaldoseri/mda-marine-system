#!/usr/bin/env python3
"""اختبار سلبي/إيجابي لبوابة الإغلاق: يثبت أنها تمنع فعلًا ولا تمرّ بلا فحص.

الحالات:
1) عطل بلا درس وبلا استثناء ⇒ منع (2)
2) استثناء منتهي الصلاحية ⇒ منع (2)
3) سجل ناقص الحقول ⇒ منع (2)
4) سجل مطابق كامل ⇒ مجتاز (0)
5) انهيار داخلي (سجل غير موجود) ⇒ 70
"""
import json, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

GATE = '/home/ubuntu/brain-marine-news/validators/check_closure.py'
CANON = ['الرقم', 'التاريخ', 'المحور', 'العَرَض', 'السبب الجذري', 'الإصلاح', 'التشديد والحالة',
         'الحالة الأصلية', 'حالة الإصلاح', 'حالة التحقق', 'حالة الحاجز', 'الحالة التشغيلية']


def fixture(tmp: Path, rows, exc_entries, trace_rows):
    (tmp / 'audit').mkdir(parents=True, exist_ok=True)
    (tmp / 'audit' / 'سجل-الأعطال-والثغرات.md').write_text(
        '# سجل\n\n| ' + ' | '.join(CANON) + ' |\n|' + '---|' * 12 + '\n' +
        '\n'.join('| ' + ' | '.join(r) + ' |' for r in rows) + '\n', encoding='utf-8')
    now = datetime.now(timezone.utc)
    (tmp / 'audit' / 'closure-exceptions.json').write_text(json.dumps(
        {'version': 1, 'created_at': now.isoformat(), 'approved_by': 't', 'entries': exc_entries},
        ensure_ascii=False), encoding='utf-8')
    (tmp / 'audit' / 'traceability.json').write_text(json.dumps(
        {'version': 1, 'chain': 'x', 'rows': trace_rows}, ensure_ascii=False), encoding='utf-8')


def row(ident, state, verify='غير متحقق', barrier='غير موثَّق'):
    return [ident, '2026-10-28', 'gate', 'عَرَض', 'سبب', 'إصلاح', 'حاجز', 'قديم',
            'منفَّذ', verify, barrier, state]


def run(tmp: Path) -> int:
    p = subprocess.run([sys.executable, GATE, '--brain', str(tmp)], capture_output=True, text=True)
    return p.returncode


def main():
    now = datetime.now(timezone.utc)
    ok = True

    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / 'a'
        fixture(t, [row('ك-1', 'مفتوح')], [], [{'fault_id': 'ك-1', 'lesson_id': None, 'barrier_id': 'B-1', 'run_evidence': None}])
        rc = run(t); print(f'  1) عطل بلا درس وبلا استثناء → {rc} {"✔" if rc == 2 else "✘"}'); ok &= rc == 2

    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / 'b'
        e = {'fault_id': 'ك-1', 'state': 'مفتوح', 'reason': 'x', 'owner': 't', 'approved_by': 't',
             'created_at': now.isoformat(), 'expires_at': (now - timedelta(days=1)).isoformat(),
             'compensating_control': 'c', 'replacement_plan': 'p', 'evidence': 'e'}
        fixture(t, [row('ك-1', 'مفتوح')], [e], [{'fault_id': 'ك-1', 'lesson_id': 'ك-1', 'barrier_id': 'B-1', 'run_evidence': 'r'}])
        rc = run(t); print(f'  2) استثناء منتهي الصلاحية → {rc} {"✔" if rc == 2 else "✘"}'); ok &= rc == 2

    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / 'c'
        fixture(t, [['ك-1', 'سطر', 'ناقص']], [], [])
        rc = run(t); print(f'  3) مخطط غير قانوني → {rc} {"✔" if rc == 2 else "✘"}'); ok &= rc == 2

    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / 'e'
        e = {'fault_id': 'ك-1', 'state': 'مفتوح', 'reason': 'x', 'owner': 't', 'approved_by': 't',
             'created_at': now.isoformat(), 'expires_at': (now + timedelta(days=30)).isoformat(),
             'compensating_control': 'c', 'replacement_plan': 'p', 'evidence': 'e'}
        fixture(t, [row('ك-1', 'مفتوح'), row('ك-2', 'مغلق', 'تحقق تشغيلي ناجح', 'فعّال')], [e],
                [{'fault_id': 'ك-1', 'lesson_id': 'ك-1', 'barrier_id': 'B-1', 'run_evidence': 'r'},
                 {'fault_id': 'ك-2', 'lesson_id': 'ك-2', 'barrier_id': 'B-2', 'run_evidence': 'r'}])
        rc = run(t); print(f'  4) سجل مطابق كامل → {rc} {"✔" if rc == 0 else "✘"}'); ok &= rc == 0

    with tempfile.TemporaryDirectory() as d:
        rc = run(Path(d) / 'missing')
        print(f'  5) سجل غير موجود (انهيار) → {rc} {"✔" if rc == 70 else "✘"}'); ok &= rc == 70

    print('  الحصيلة: كل الاختبارات نجحت ✔' if ok else '  الحصيلة: فشل ✘')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())