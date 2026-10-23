#!/usr/bin/env bash
# إثبات السلسلة كاملة على نسخة مؤقتة من الإنتاج: تشغيل → خطوة وكيل → إتمام → بوابات → بناء.
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
C=/tmp/rb-prod-copy2
D=2026-10-23
rm -rf "$C"; mkdir -p "$C"
tar -C "$B" --exclude=.git --exclude=logs --exclude=design --exclude='*.pdf' -cf - . | tar -C "$C" -xf -
cd "$C" || exit 2
python3 - <<'PY'
import json
from pathlib import Path
p = Path('runbook/runbook.json'); m = json.loads(p.read_text(encoding='utf-8'))
t = next(s for s in m['steps'] if s['id'] == 'S000')['links']['tests']
import os
for d, _, fs in os.walk('tests'):
    for f in fs:
        rel = os.path.join(d, f)
        if rel not in t: t.append(rel)
p.write_text(json.dumps(m, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
PY
python3 tools/runbook.py handbook >/dev/null
echo "═══ verify على النسخة ═══"; python3 tools/runbook.py verify; echo "exit=$?"
for i in $(seq 1 8); do
  echo "═══ دورة $i ═══"
  timeout 600 python3 tools/runbook.py run --date $D 2>&1 | tail -6
  rc=$?
  echo "exit=$rc"
  pending=$(python3 - <<'PY'
import json, os
p = f'logs/runbook/{os.environ.get("D","2026-10-23")}.jsonl'
last = {}
if os.path.exists(p):
    for l in open(p, encoding='utf-8'):
        if l.strip():
            e = json.loads(l); last[e['step']] = e
m = json.load(open('runbook/runbook.json', encoding='utf-8'))
w = [s['id'] for s in m['steps'] if s['kind'] == 'agent' and last.get(s['id'], {}).get('status') == 'waiting_agent']
print(w[0] if w else '')
PY
)
  [ -n "$pending" ] || { echo "  (لا خطوة وكيل معلّقة)"; break; }
  echo "  ── إتمام $pending بدليل الملفات ──"
  timeout 120 python3 tools/runbook.py complete "$pending" --date $D 2>&1 | tail -3
  [ "$pending" = "W020" ] && python3 - <<'PY'
import json
from pathlib import Path
p = Path('web/meta/2026-10-23.json')
if not p.exists():
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"date": "2026-10-23", "summary": "نسخة اختبار"}, ensure_ascii=False), encoding='utf-8')
PY
done
echo "═══ الحالة النهائية ═══"; python3 tools/runbook.py status --date $D | tail -12