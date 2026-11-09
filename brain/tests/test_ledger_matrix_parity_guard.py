"""انحدار: الحارس يعدّ كل عائلات المعرّفات ويفشل مغلقًا على التباعد."""
import json
import pathlib
import subprocess
import sys

BRAIN = pathlib.Path(__file__).resolve().parents[1]
GUARD = BRAIN / 'validators/check_ledger_matrix_parity.py'
ROW = ('| {fid} | 2026-11-09 | محور | عَرَض | سبب | إصلاح | حاجز | مفتوح | '
       'منفَّذ | تحقق | مطبَّق | مغلق |')


def build(tmp: pathlib.Path, log_ids, matrix_ids):
    (tmp / 'audit').mkdir(parents=True, exist_ok=True)
    head = '| الرقم | التاريخ | المحور |\n|---|---|---|\n'
    body = '\n'.join(ROW.format(fid=i) for i in log_ids)
    (tmp / 'audit/سجل-الأعطال-والثغرات.md').write_text(head + body + '\n', encoding='utf-8')
    rows = [{'fault_id': i} for i in matrix_ids]
    (tmp / 'audit/traceability.json').write_text(
        json.dumps({'rows': rows}, ensure_ascii=False), encoding='utf-8')


def run(tmp: pathlib.Path) -> int:
    return subprocess.run([sys.executable, str(GUARD), '--brain', str(tmp)],
                          capture_output=True, text=True).returncode


def test_non_k_family_rows_are_counted(tmp_path):
    build(tmp_path, ['ك-1', 'ز-01', 'ث-02/ب'], ['ك-1', 'ز-01', 'ث-02/ب'])
    assert run(tmp_path) == 0


def test_matrix_row_outside_log_fails_closed(tmp_path):
    build(tmp_path, ['ك-1'], ['ك-1', 'ز-01'])
    assert run(tmp_path) == 2


def test_regression_below_baseline_fails_closed(tmp_path):
    build(tmp_path, ['ك-1', 'ك-2'], ['ك-1', 'ك-2'])
    assert run(tmp_path) == 0
    build(tmp_path, ['ك-1'], ['ك-1'])
    assert run(tmp_path) == 2
