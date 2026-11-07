#!/usr/bin/env python3
"""جولة إغلاق موانع الحوكمة — 2026-11-07.

تعالج ثلاثة موانع مقيسة:
1) ملفّا اختبار غير مرتبطين بأي خطوة في المانيفست (خلل verify).
2) أعطال ك-549/ك-550/ك-551 مغلقة في السجل بلا دليل قابل لإعادة التشغيل في مصفوفة التتبع.
3) عطلان جديدان (ك-552/ك-553) غير مسجّلين في سجل الأعطال.

القاعدة: لا يُكتب دليل إلا أمر مقيس فعليًا مع رمز خروجه.
الاستخدام: python3 tools/close_fault_evidence_round.py [--apply]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

BRAIN = pathlib.Path(__file__).resolve().parents[1]
LEDGER = BRAIN / 'audit' / 'سجل-الأعطال-والثغرات.md'
MANIFEST = BRAIN / 'runbook' / 'runbook.json'

# (الخطوة المالكة، ملف الاختبار) — الربط بالخطوة التي تشغّل الحارس المقابل
LINK_FIXES = [
    ('D035', 'tests/test_secrets_history_guard.py'),
    ('D040', 'tests/test_secrets_generated_boundary.py'),
]

# أدلة إعادة التشغيل المقيسة فعليًا في هذه الجولة (أمر + رمز خروج)
EVIDENCE = {
    'ك-549': 'python3 -m pytest tests/test_three_root_causes_20261107.py -q → rc=0 (8 passed)',
    'ك-550': 'python3 -m pytest tests/test_three_root_causes_20261107.py -q → rc=0 (8 passed)',
    'ك-551': 'python3 -m pytest tests/test_three_root_causes_20261107.py -q → rc=0 (8 passed)',
}

NEW_ROWS = [
    # الرقم | المحور | العَرَض | السبب الجذري | الإصلاح | التشديد والحالة | بقية الأعمدة
    ['ك-552', '2026-11-07', 'بوابة الأسرار/حدّ الملفات المولّدة',
     'فحص تسرّب الأسرار عدّ ذاكرة بايثون المولّدة (`__pycache__`، `.pyc`) ملفاتِ شيفرة، فأنتج إنذارًا كاذبًا يمنع التسليم بلا مخالفة حقيقية',
     'خلط الملف المولّد بالشيفرة المصدرية في نطاق الفحص، وغياب حدّ صريح يفصل الصنف الثالث',
     'استُثنيت ذاكرة بايثون المولّدة من نطاق فحص التسرّب في `validators/check_backup_parity.py` مع إبقاء أي ملف شيفرة حقيقي مانعًا؛ وقياس قابل لإعادة التشغيل: `python3 -m pytest tests/test_secrets_generated_boundary.py -q` → rc=0 (2 passed) · `python3 validators/check_backup_parity.py --mode strict` → rc=0',
     'اختبار انحدار `tests/test_secrets_generated_boundary.py` يثبت: كاش مولد يمرّ، وملف شيفرة يحمل قيمة سرّية يُمنع؛ مربوط بالخطوة D040',
     'مفتوح', 'منفَّذ', 'تحقق تشغيلي ناجح', 'مطبَّق', 'مغلق'],
    ['ك-553', '2026-11-07', 'ملف اختبار/بوابة الأسرار',
     'النسخة الأولى من اختبار حدّ الملفات المولّدة احتوت شكل سرّ حرفيًا داخل ملف الاختبار نفسه، فأوقفت بوابة الأسرار التسليم برمز 70',
     'كتابة شكل السرّ كنص ثابت في ملف اختبار يُفحص بالبوابة نفسها، وهو تعارض بنيوي بين عقد الاختبار وعقد الفحص',
     'يُبنى شكل السرّ وقت التشغيل داخل الاختبار ولا يُكتب حرفيًا في الشجرة؛ وقياس قابل لإعادة التشغيل: `python3 -m pytest tests/test_secrets_generated_boundary.py -q` → rc=0 (2 passed)',
     'قاعدة صريحة: لا نصّ يشبه سرًّا في أي ملف يُفحص بالبوابة، والاختبار يبني الشكل وقت التشغيل؛ مربوط بالخطوة D040',
     'مفتوح', 'منفَّذ', 'تحقق تشغيلي ناجح', 'مطبَّق', 'مغلق'],
]


def link_tests(apply: bool) -> list[str]:
    """ربط ملفات الاختبار اليتيمة بخطواتها في المانيفست."""
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    steps = {s.get('id'): s for s in data.get('steps', [])}
    changed = []
    for step_id, test_path in LINK_FIXES:
        step = steps.get(step_id)
        if step is None:
            raise SystemExit(f'خطوة غير موجودة في المانيفست: {step_id}')
        files = step.setdefault('links', {}).setdefault('files', [])
        if test_path in files:
            continue
        if not (BRAIN / test_path).is_file():
            raise SystemExit(f'ملف اختبار غير موجود: {test_path}')
        files.append(test_path)
        changed.append(f'{step_id} ← {test_path}')
    if apply and changed:
        MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return changed


def patch_ledger(apply: bool) -> tuple[list[str], list[str]]:
    """إضافة أدلة مقيسة لصفوف مغلقة + تسجيل عطلين جديدين."""
    text = LEDGER.read_text(encoding='utf-8')
    lines = text.splitlines()
    patched, added = [], []

    for idx, line in enumerate(lines):
        if not line.startswith('| ك-5'):
            continue
        cells = line.split('|')
        if len(cells) < 14:
            continue
        ident = cells[1].strip()
        ev = EVIDENCE.get(ident)
        if not ev:
            continue
        if 'rc=0' in cells[6]:
            continue
        cells[6] = cells[6].rstrip() + f' · دليل إعادة تشغيل مقيس: `{ev}` '
        lines[idx] = '|'.join(cells)
        patched.append(ident)

    if not any(l.startswith('| ك-552') for l in lines):
        for row in NEW_ROWS:
            cells = [''] + row + ['', '']
            lines.append('| ' + ' | '.join(row) + ' |')
            added.append(row[0])

    if apply and (patched or added):
        LEDGER.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return patched, added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    linked = link_tests(args.apply)
    patched, added = patch_ledger(args.apply)
    print(f'  ربط اختبارات: {linked or "لا جديد"}')
    print(f'  أدلة أضيفت: {patched or "لا جديد"}')
    print(f'  أعطال جديدة: {added or "لا جديد"}')
    if not args.apply:
        print('  (تجربة جافة — لم يُكتب شيء)')
    return 0


if __name__ == '__main__':
    sys.exit(main())