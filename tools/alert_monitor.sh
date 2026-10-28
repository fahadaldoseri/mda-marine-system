#!/usr/bin/env bash
# مراقب مستقل: يفحص سجل المحرّك لليوم، وإن لم تكتمل الخطوات كتب تنبيهًا في logs/alerts/ باسم الخطوة العالقة.
# يُشغَّل بمهمة مجدولة ثانية بعد وقت التسليم المتوقع بساعة. لا يرسل شيئًا إلى تلغرام.
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
D="${1:-$(date -u +%F)}"
L="$B/logs/runbook/$D.jsonl"
A="$B/logs/alerts"
mkdir -p "$A"
if [ ! -s "$L" ]; then
  echo "$(date -u +%FT%TZ) · لا سجل تشغيل لليوم $D — المحرّك لم يبدأ" > "$A/$D-no-run.txt"
  echo "✘ لا سجل تشغيل لليوم $D"; exit 2
fi
python3 - "$L" "$D" "$A" <<'PY'
import json, sys, time, os
ledger, date, adir = sys.argv[1], sys.argv[2], sys.argv[3]
last = {}
for line in open(ledger, encoding='utf-8'):
    if line.strip():
        e = json.loads(line); last[e['step']] = e
m = json.load(open('runbook/runbook.json', encoding='utf-8'))
pending = [s['id'] for s in m['steps']
           if not s.get('optional') and (s['id'] not in last or last[s['id']]['status'] not in ('done', 'done_warn'))]
out = os.path.join(adir, f'{date}-incomplete.txt')
if pending:
    waiting = [i for i in pending if last.get(i, {}).get('status') == 'waiting_agent']
    body = (f'{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}\n'
            f'تشغيل {date} لم يكتمل. الخطوة العالقة: {pending[0]}\n'
            f'بانتظار الوكيل: {waiting or "لا"}\n'
            f'كل غير المكتمل: {"، ".join(pending)}\n')
    open(out, 'w', encoding='utf-8').write(body)
    print(f'✘ تشغيل ناقص — الخطوة العالقة {pending[0]} (تنبيه: {out})')
    sys.exit(2)
print('✔ تشغيل اليوم مكتمل')
PY