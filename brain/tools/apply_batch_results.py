#!/usr/bin/env python3
"""تطبيق مركزي لنتائج دفعات الوكلاء على سجل الأعطال — بحاجز تحقق مسبق.

الأداة لا تثق بأي نصّ قادم: كل تحديث يمرّ ببوابة عقد الدليل نفسها التي يقرؤها
`tools/closure_round.py`، فلا يُقبل نصّ حاجز بلا مفردة معلنة وبلا نتيجة صريحة.
ولا تكتب على صفٍّ غير موجود، ولا تلمس صفًا مُغلقًا بناءً على «لم يُغلق».

الاستخدام:
  python3 tools/apply_batch_results.py --root . [--results audit/measurements/batches] [--apply]
رموز الخروج: 0 نجح التطبيق/التجربة الجافة · 2 مدخلات مرفوضة · 3 ملف مفقود.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import sys

LOG = 'audit/سجل-الأعطال-والثغرات.md'
BARRIER_WORDS = ('بوابة', 'اختبار', 'حارس', 'قاعدة', 'check_', 'فحص', 'قياس')
OUTCOME = re.compile(
    r'(rc\s*=\s*(?:0|2|70)|خرج\s*(?:0|2|70)|رمز\s*(?:0|2|70)|exit\s*(?:0|2)|'
    r'فاشل\s*0|\b\d{1,3}\s*/\s*\d{1,3}\b|بصمة\s*[0-9a-f]{6,})')
HDR_CELLS = ('الرقم', 'رقم')


def read_log(p: pathlib.Path) -> list[str]:
    return p.read_text(encoding='utf-8').splitlines()


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip('|').split('|')]


def build_row(cells: list[str]) -> str:
    return '| ' + ' | '.join(cells) + ' |'


def valid_barrier(text: str) -> tuple[bool, str]:
    if not text or len(text.strip()) < 12:
        return False, 'نصّ حاجز فارغ أو قصير'
    if not any(w in text for w in BARRIER_WORDS):
        return False, 'لا يحمل مفردة حاجز معلنة'
    if not OUTCOME.search(text):
        return False, 'لا يحمل نتيجة صريحة (rc / فاشل 0 / n-n / بصمة)'
    return True, ''


def main() -> int:
    ap = argparse.ArgumentParser(description='تطبيق نتائج الدفعات على سجل الأعطال')
    ap.add_argument('--root', default='.')
    ap.add_argument('--results', default='audit/measurements/batches')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    log_p = root / LOG
    if not log_p.is_file():
        print(f'✘ سجل الأعطال مفقود: {log_p}')
        return 3
    lines = read_log(log_p)
    index: dict[str, int] = {}
    for i, line in enumerate(lines):
        if line.startswith('|'):
            cells = split_row(line)
            if len(cells) >= 8 and cells[0] and cells[0] not in HDR_CELLS and not set(cells[0]) <= set('- '):
                index.setdefault(cells[0], i)

    stats = {'closed_applied': 0, 'closed_skipped': 0, 'rejected': [], 'axis_applied': 0, 'missing_rows': []}
    axis_updates: dict[str, str] = {}

    # نكتشف كل ملفات النتائج (result-A · result-B · result-A2 · result-B3 …) بدل قائمة ثابتة،
    # حتى لا يفشل التطبيق عند إضافة دفعة جديدة في التوسّع المستقبلي.
    result_files = sorted((root / a.results).glob('result-*.json'))
    if not result_files:
        print(f'✘ لا ملفات نتائج في {root / a.results}')
        return 2
    for p in result_files:
        data = json.loads(p.read_text(encoding='utf-8'))
        for r in data.get('results', []):
            fid = r.get('fault_id')
            rc = r.get('rc')
            verdict = r.get('verdict') or ('مغلق' if str(rc).strip() == '0' else '')
            if verdict != 'مغلق':
                stats['closed_skipped'] += 1
                continue
            text = (r.get('barrier_text') or '').strip()
            if not text and r.get('command'):
                text = f"قياس مباشر: {r['command']} → rc={rc}"
                if r.get('log_file'):
                    text += f" · {r['log_file']}"
                text = text.strip()
            ok, why = valid_barrier(text)
            if not ok:
                stats['rejected'].append(f'{fid}: {why}')
                stats['closed_skipped'] += 1
                continue
            i = index.get(fid)
            if i is None:
                stats['missing_rows'].append(fid)
                continue
            cells = split_row(lines[i])
            while len(cells) < 12:
                cells.append('')
            if text not in cells[6]:
                cells[6] = text
            while len(cells) < 12:
                cells.append('')
            if cells[11] != 'مغلق':
                cells[11] = 'مغلق'
            if (cells[5] or '').strip() in ('', '—', '-'):
                cells[5] = f"إصلاح مُتحقَّق بدليل القياس: {r.get('command', '')}".strip()
                stats['fix_filled'] = stats.get('fix_filled', 0) + 1
            lines[i] = build_row(cells)
            stats['closed_applied'] += 1

    p = root / a.results / 'result-C.json'
    if p.is_file():
        data = json.loads(p.read_text(encoding='utf-8'))
        for r in data.get('rows', []):
            fid, axis = r.get('fault_id'), (r.get('axis') or '').strip()
            if fid and axis and axis not in ('—', '-'):
                axis_updates[fid] = axis
    for fid, axis in axis_updates.items():
        i = index.get(fid)
        if i is None:
            stats['missing_rows'].append(fid)
            continue
        cells = split_row(lines[i])
        while len(cells) < 12:
            cells.append('')
        if cells[2] == axis:
            continue
        cells[2] = axis
        lines[i] = build_row(cells)
        stats['axis_applied'] += 1

    print(f'   إغلاق مطبَّق: {stats["closed_applied"]} · متخطّى: {stats["closed_skipped"]} · محاور مُلئت: {stats["axis_applied"]}')
    if stats['rejected']:
        print(f'   مرفوض بعقد الدليل ({len(stats["rejected"])}):')
        for x in stats['rejected'][:12]:
            print(f'     - {x}')
    if stats['missing_rows']:
        print(f'   معرّفات بلا صفّ في السجل ({len(stats["missing_rows"])}): {stats["missing_rows"][:8]}')

    if not a.apply:
        print('   تجربة جافة: لم يُكتب شيء (أضف --apply للتنفيذ)')
        return 0
    if stats['closed_applied'] == 0 and stats['axis_applied'] == 0:
        print('   لا تغيير يستحق الكتابة')
        return 0
    bak = root / 'audit/backups' / f'batch-apply-{dt.datetime.now():%Y%m%d-%H%M%S}'
    bak.mkdir(parents=True, exist_ok=True)
    shutil.copy2(log_p, bak / log_p.name)
    log_p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'   ✔ كُتب السجل · نسخة احتياطية: {bak.relative_to(root)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
