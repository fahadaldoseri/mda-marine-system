#!/usr/bin/env python3
"""اختبار انحدار: نتيجة الدفعة يجب أن تُحرّك حالة الصف في سجل الأعطال.

الموجب: نتيجة rc=0 تُغلق الصف (العمود 12 يصير «مغلق») ويُكتب دليل قابل لإعادة التشغيل.
السالب: نتيجة rc=2 لا تُغلق الصف ولا تُغيّر حالته.

يمكن توجيه الاختبار إلى نسخة أخرى من الأداة عبر المتغيّر APPLY_TOOL لإثبات RED.
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

BRAIN = pathlib.Path(__file__).resolve().parents[1]
TOOL = pathlib.Path(os.environ.get('APPLY_TOOL') or (BRAIN / 'tools/apply_batch_results.py'))
HDR = ('| الرقم | التاريخ | المحور | العَرَض | السبب الجذري | الإصلاح | التشديد والحالة | '
       'الحالة الأصلية | حالة الإصلاح | حالة التحقق | حالة الحاجز | الحالة التشغيلية |')
SEP = '|' + '---|' * 12


def build_tree(tmp: pathlib.Path, fault: str, state: str = 'مفتوح') -> pathlib.Path:
    (tmp / 'audit/measurements/batches').mkdir(parents=True, exist_ok=True)
    row = (f'| {fault} | 2026-11-09 | محور الاختبار | عَرَض تجريبي | سبب تجريبي | إصلاح تجريبي | '
           f'قياس أولي: rc=2 | مفتوح | إصلاح تجريبي | تحقق أولي | مطبَّق | {state} |')
    (tmp / 'audit/سجل-الأعطال-والثغرات.md').write_text(
        '\n'.join(['# سجل الأعطال والثغرات', HDR, SEP, row, '']) + '\n', encoding='utf-8')
    return tmp


def write_result(tmp: pathlib.Path, fault: str, rc: int, name: str = 'result-T.json') -> None:
    payload = {'batch': 'T', 'measured_at': '2026-11-09T00:00:00Z',
               'results': [{'fault_id': fault, 'command': 'timeout 120 python3 tests/test_demo.py',
                            'rc': rc, 'output_tail': 'demo', 'log_file': 'audit/measurements/batches/logs/T/x.log'}]}
    (tmp / 'audit/measurements/batches' / name).write_text(
        json.dumps(payload, ensure_ascii=False), encoding='utf-8')


def derive_state(cells: list[str]) -> str:
    spec = importlib.util.spec_from_file_location('cr', BRAIN / 'tools/closure_round.py')
    cr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cr)
    out = cr.derive(cells[1], cells[5], cells[6], cells[7])
    return out[3] if isinstance(out, list) else out


def read_row(tmp: pathlib.Path, fault: str) -> list[str]:
    for line in (tmp / 'audit/سجل-الأعطال-والثغرات.md').read_text(encoding='utf-8').splitlines():
        if line.startswith(f'| {fault} '):
            return [c.strip() for c in line.strip().strip('|').split('|')]
    raise AssertionError('الصف غير موجود')


def run_tool(tmp: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), '--root', str(tmp), '--apply'],
                          capture_output=True, text=True, timeout=300)


def test_rc0_closes_row(tmp_path):
    build_tree(tmp_path, 'ك-901')
    write_result(tmp_path, 'ك-901', 0)
    r = run_tool(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    cells = read_row(tmp_path, 'ك-901')
    assert cells[11] == 'مغلق', f'الحالة لم تُغلق: {cells[11]}'
    assert 'rc=0' in cells[6], f'الدليل لا يحمل نتيجة صريحة: {cells[6]}'
    assert (cells[5] or '').strip() not in ('', '—'), f'عمود الإصلاح فارغ: {cells[5]}'
    assert derive_state(cells) == 'مغلق', f'الاشتقاق لا يغلق الصف: {derive_state(cells)}'


def test_rc2_keeps_row_open(tmp_path):
    build_tree(tmp_path, 'ك-902')
    write_result(tmp_path, 'ك-902', 2)
    r = run_tool(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    cells = read_row(tmp_path, 'ك-902')
    assert cells[11] == 'مفتوح', f'الصف أُغلق بنتيجة فاشلة: {cells[11]}'
    assert derive_state(cells) != 'مغلق', 'الاشتقاق أغلق صفًا بقياس فاشل (rc=2)'
    assert 'rc=2' not in cells[6] or 'قياس مباشر' not in cells[6]