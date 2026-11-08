#!/usr/bin/env python3
"""اختبار انحدار: مشغّل الدفعات لا ينهار عند تجاوز المهلة ويسجّل rc=124.

الجذر السببي: كان مسار subprocess.TimeoutExpired يجمع bytes مع نص فينهار المشغّل
ويُفقد الصف بدل تسجيله. الاختبار يمنع رجوع ذلك الصنف.

حالة موجبة: أمر يتجاوز المهلة ⇒ rc=124 مسجَّل + النتيجة مكتوبة + لا Traceback.
حالة سالبة: أمر سريع ناجح ⇒ rc=0 و«مغلق».
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

BRAIN = pathlib.Path(__file__).resolve().parent.parent
RUNNER = BRAIN / 'tools/measurement_batch_runner.py'


def run_case(tmp: pathlib.Path, commands: dict, timeout: int) -> tuple[int, dict]:
    base = tmp / 'audit/measurements/batches'
    base.mkdir(parents=True, exist_ok=True)
    (base / 'commands-T.json').write_text(json.dumps({'commands': commands}, ensure_ascii=False), encoding='utf-8')
    p = subprocess.run([sys.executable, str(RUNNER), '--root', str(tmp), '--batch', 'T',
                        '--timeout', str(timeout), '--write-every', '1'],
                       capture_output=True, text=True, timeout=300)
    res = json.loads((base / 'result-T.json').read_text(encoding='utf-8'))
    return p.returncode, {'rc': p.returncode, 'out': p.stdout + p.stderr, 'res': res}


def main() -> int:
    fails = []
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        code, r = run_case(tmp, {'T-TIMEOUT': 'sleep 6; echo انتهى'}, timeout=1)
        entry = {x['fault_id']: x for x in r['res']['results']}.get('T-TIMEOUT')
        if entry is None:
            fails.append('حالة موجبة: الصف المتجاوز لم يُسجَّل أصلًا')
        else:
            if entry['rc'] != 124:
                fails.append(f"حالة موجبة: rc={entry['rc']} بدل 124")
            if entry['verdict'] != 'لم يُغلق':
                fails.append('حالة موجبة: صف متجاوز المهلة أُعلن مغلقًا')
            if 'Traceback' in r['out']:
                fails.append('حالة موجبة: المشغّل انهار بـTraceback')
        code, r = run_case(tmp, {'T-OK': 'exit 0'}, timeout=30)
        ok = {x['fault_id']: x for x in r['res']['results']}.get('T-OK')
        if not ok or ok['rc'] != 0 or ok['verdict'] != 'مغلق':
            fails.append('حالة سالبة: الصف الناجح لم يُغلق برمز 0')

    if fails:
        print('✘ اختبار مشغّل الدفعات:')
        for f in fails:
            print(f'   - {f}')
        return 1
    print('✔ مشغّل الدفعات: مسار المهلة يسجّل rc=124 بلا انهيار · والمسار الناجح يُغلق')
    return 0


if __name__ == '__main__':
    sys.exit(main())
