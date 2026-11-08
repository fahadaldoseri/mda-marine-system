#!/usr/bin/env python3
"""مشغّل دفعات القياس: يُنفّذ أوامر معلنة لكل صف عطل ويُثبّت الدليل تدريجيًا.

الجذر السببي الذي أُنشئت لأجله: كانت المشغّلات المؤقتة تُكتب في /tmp بأوامر داخل
نصوص بايثون، فتنكسر بسبب الاقتباس العربي/المتداخل وتُفقد الجولة. هنا الأوامر
**بيانات JSON** لا نصوص شيفرة، فتنكسر فئة الخطأ كلها.

المدخل:  audit/measurements/batches/commands-<batch>.json
  {"commands": {"<fault_id>": "<shell command>"}}
المخرجات:
  audit/measurements/batches/logs/<batch2>/<fault_id>.log   (المخرَج الحرفي الكامل)
  audit/measurements/batches/state-<batch>.json             (تقدّم بعد كل صف)
  audit/measurements/batches/result-<batch>.json            (نتيجة بعد كل N صفوف)

الاستخدام:
  python3 tools/measurement_batch_runner.py --batch B --total 115 --timeout 120 [--write-every 5]
رموز الخروج: 0 اكتمل العدد · 2 نقص أوامر · 3 خطأ إعداد.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

BASE = 'audit/measurements/batches'


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _text(x) -> str:
    """مخرَج المهلة قد يصل bytes في بعض الحالات؛ نحوّله دائمًا إلى نصّ بلا انهيار."""
    if x is None:
        return ''
    if isinstance(x, (bytes, bytearray)):
        return x.decode('utf-8', 'replace')
    return x


def main() -> int:
    ap = argparse.ArgumentParser(description='مشغّل دفعات القياس')
    ap.add_argument('--root', default='.')
    ap.add_argument('--batch', required=True)
    ap.add_argument('--total', type=int, default=0)
    ap.add_argument('--timeout', type=int, default=120)
    ap.add_argument('--write-every', type=int, default=5)
    ap.add_argument('--logs-dir', default='')
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    base = root / BASE
    cmd_p = base / f'commands-{a.batch}.json'
    if not cmd_p.is_file():
        print(f'✘ ملف الأوامر مفقود: {cmd_p}')
        return 3
    commands = json.loads(cmd_p.read_text(encoding='utf-8')).get('commands', {})
    scope_p = base / f'scope-{a.batch}-measurable.json'
    ids = list(commands)
    if scope_p.is_file():
        ids = [r['fault_id'] for r in json.loads(scope_p.read_text(encoding='utf-8'))['rows']]
    missing_cmds = [i for i in ids if not (commands.get(i) or '').strip()]
    logs_dir = base / (a.logs_dir or f'logs/{a.batch}')
    logs_dir.mkdir(parents=True, exist_ok=True)
    res_p = base / f'result-{a.batch}.json'
    state_p = base / f'state-{a.batch}.json'
    state = json.loads(state_p.read_text(encoding='utf-8')) if state_p.is_file() else {}
    existing = {}
    if res_p.is_file():
        for r in json.loads(res_p.read_text(encoding='utf-8')).get('results', []):
            existing[r['fault_id']] = r

    total = a.total or len(ids)
    print(f'   الصفوف: {len(ids)} · بأوامر: {len(ids) - len(missing_cmds)} · بلا أمر: {len(missing_cmds)} · سابق: {len(existing)}')
    if missing_cmds:
        print(f'   ✘ أوامر ناقصة ({len(missing_cmds)}): {missing_cmds[:10]}')
    done = 0
    for fid in ids:
        cmd = (commands.get(fid) or '').strip()
        if not cmd or fid in existing:
            continue
        started = now()
        try:
            p = subprocess.run(['bash', '-lc', cmd], cwd=str(root), capture_output=True,
                               text=True, timeout=a.timeout)
            rc, out = p.returncode, (p.stdout or '') + (p.stderr or '')
        except subprocess.TimeoutExpired as e:
            rc, out = 124, f'تجاوز المهلة {a.timeout}s\n' + _text(e.stdout) + _text(e.stderr)
        except Exception as e:  # خطأ تشغيل = دليل لا انهيار
            rc, out = 125, f'خطأ تنفيذ: {e}'
        log_p = logs_dir / f'{fid}.log'
        log_p.write_text(f'COMMAND: {cmd}\nSTARTED_AT: {started}\nRC: {rc}\nOUTPUT_BEGIN\n{out}\nOUTPUT_END\n',
                         encoding='utf-8')
        digest = hashlib.sha256(log_p.read_bytes()).hexdigest()
        tail = '\n'.join([l for l in out.strip().splitlines() if l.strip()][-3:])[:400]
        if rc == 0:
            barrier = f'قياس مباشر: {cmd} → rc=0 · بصمة {digest[:12]}'
            verdict, reason = 'مغلق', ''
        else:
            barrier = f'قياس مباشر: {cmd} → rc={rc} (لم يُغلق؛ السبب في السجل)'
            verdict, reason = 'لم يُغلق', f'rc={rc}: {tail[-160:]}'
        existing[fid] = {'fault_id': fid, 'command': cmd, 'rc': rc, 'output_tail': tail,
                         'log_file': str(log_p.relative_to(root)), 'sha256': digest,
                         'verdict': verdict, 'barrier_text': barrier,
                         'fix_applied': '', 'reason_if_not_closed': reason}
        done += 1
        state = {'batch': a.batch, 'run': 'runner', 'updated_at': now(), 'processed': len(existing),
                 'total': total, 'last_fault_id': fid}
        state_p.write_text(json.dumps(state, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        if done % a.write_every == 0 or len(existing) == total:
            rs = list(existing.values())
            res_p.write_text(json.dumps({
                'batch': a.batch, 'measured_at': now(), 'results': rs,
                'summary': {'closed': sum(1 for r in rs if r['verdict'] == 'مغلق'),
                            'not_closed': sum(1 for r in rs if r['verdict'] != 'مغلق'),
                            'total': len(rs)},
            }, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            print(f'   [{len(existing)}/{total}] آخر صف {fid} rc={rc} · مغلق {sum(1 for r in rs if r["verdict"]=="مغلق")}')

    rs = list(existing.values())
    res_p.write_text(json.dumps({
        'batch': a.batch, 'measured_at': now(), 'results': rs,
        'summary': {'closed': sum(1 for r in rs if r['verdict'] == 'مغلق'),
                    'not_closed': sum(1 for r in rs if r['verdict'] != 'مغلق'), 'total': len(rs)},
    }, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    closed = sum(1 for r in rs if r['verdict'] == 'مغلق')
    print(f'   النتيجة: {len(rs)}/{total} · مغلق {closed} · غير مغلق {len(rs)-closed}')
    if len(rs) < total:
        print(f'   ⚠ ناقص {total - len(rs)} صفًا — أضف أوامرها إلى {cmd_p.name} وأعد التشغيل (يستأنف تلقائيًا)')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
