#!/usr/bin/env bash
# ربط اختبار المشغّل الدائم بمالكه الحقيقي ثم استئناف الجولة.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1

echo "   ═══ 1) أين تُعلن أدوات الدفعات في المانيفست ═══"
python3 - <<'PY'
import json, pathlib
m = json.loads(pathlib.Path('runbook/runbook.json').read_text(encoding='utf-8'))
hits = []
for i, s in enumerate(m.get('steps', [])):
    blob = json.dumps(s, ensure_ascii=False)
    for tok in ('measurement_batch_runner', 'apply_batch_results', 'commands-E', 'batches'):
        if tok in blob:
            hits.append((s.get('id') or i, tok, i))
for sec in m.get('sections', []) or []:
    if 'batch' in json.dumps(sec, ensure_ascii=False).lower():
        print(f'   قسم يذكر الدفعات: {sec.get("id")}')
for sid, tok, i in hits[:8]:
    print(f'   الخطوة {sid} تذكر: {tok}')
print(f'   عدد المواضع: {len(hits)}')
PY

echo "   ═══ 2) الربط ═══"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('runbook/runbook.json')
m = json.loads(p.read_text(encoding='utf-8'))
steps = m['steps']
NEW = 'tests/test_batch_runner_safe_id.py'

def has(name):
    for s in steps:
        links = s.get('links') or {}
        if any(name in [str(x) for x in links.get(k, [])] for k in ('files', 'tests', 'gates')):
            return True
    return False

if has(NEW):
    print('   • مربوط مسبقًا')
else:
    owner = None
    for i, s in enumerate(steps):
        blob = json.dumps(s, ensure_ascii=False)
        if 'measurement_batch_runner' in blob or 'apply_batch_results' in blob:
            owner = i; break
    if owner is None:
        # أسرع مالك حقيقي: خطوة إغلاق الأعطال
        for i, s in enumerate(steps):
            if any('closure_round.py' in str(x) for x in (s.get('links') or {}).get('files', [])):
                owner = i; break
    if owner is None:
        for i, s in enumerate(steps):
            if s.get('id') == 'D050':
                owner = i; break
    links = steps[owner].setdefault('links', {})
    links.setdefault('tests', [])
    links['tests'].append(NEW)
    print(f'   ✔ {NEW} → الخطوة {steps[owner].get("id")} في links.tests')
p.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY

echo "   ═══ 3) توليد الكتيب والتحقق ═══"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"
timeout 400 python3 tools/runbook.py verify --root . 2>&1 | tail -3 | cut -c1-170 | sed 's/^/   /'

echo "   ═══ 4) تثبيت عبر فرع وطلب دمج ═══"
cd "$R" || exit 1
git checkout -q -B fix/wire-batch-test-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "ربط اختبار المشغّل الدائم بمالكه في المانيفست (ك-582)" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/wire-batch-test-20261109 2>&1 | tail -1 | cut -c1-60 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/wire-batch-test-20261109" --title "ربط اختبار المشغّل الدائم" --body "آخر ملف غير متصل من أربعة." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 5) استئناف جولة 2026-11-09 ═══"
cd "$B" || exit 1
D=$(date -u +%F)
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909c.log 2>&1
echo "   rc=$?"
tail -22 /tmp/run0909c.log | cut -c1-175 | sed 's/^/   /'
echo "   ── الحالة ──"
timeout 300 python3 tools/runbook.py status --date "$D" 2>&1 | tail -5 | cut -c1-150 | sed 's/^/   /'