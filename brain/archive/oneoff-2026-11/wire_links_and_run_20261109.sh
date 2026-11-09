#!/usr/bin/env bash
# ربط الملفات الأربعة عبر بنية links الفعلية ثم استئناف الجولة.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1

echo "   ═══ 1) الربط عبر links.files و links.tests ═══"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('runbook/runbook.json')
m = json.loads(p.read_text(encoding='utf-8'))
steps = m['steps']

def locate(name):
    """يعيد (الفهرس, المفتاح) للخطوة التي تعلن اسمًا في links أو في أمرها."""
    for i, s in enumerate(steps):
        links = s.get('links') or {}
        for key in ('files', 'tests', 'gates'):
            if any(name == str(x) for x in links.get(key, [])):
                return i, f'links.{key}'
        blob = ' '.join(s.get('command') or []) + ' ' + json.dumps(s.get('assert', []), ensure_ascii=False)
        if name in blob:
            return i, 'command'
    return None, None

PLAN = [
    ('validators/check_ledger_matrix_parity.py', 'validators/check_closure.py', 'files'),
    ('tests/test_ledger_matrix_parity_guard.py', 'validators/check_closure.py', 'tests'),
    ('validators/check_enforcer_coverage.py', 'tools/self_improve.py', 'files'),
    ('tests/test_batch_runner_safe_id.py', 'tools/apply_batch_results.py', 'tests'),
]
done = 0
for new, ref, slot in PLAN:
    if locate(new)[0] is not None:
        print(f'   • {new}: مربوط مسبقًا'); continue
    i, where = locate(ref)
    if i is None:
        print(f'   ⚠ {new}: مرجع {ref} غير معلن في أي خطوة'); continue
    links = steps[i].setdefault('links', {})
    links.setdefault(slot, [])
    if new not in links[slot]:
        links[slot].append(new)
    done += 1
    print(f'   ✔ {new} → الخطوة {steps[i].get("id")} في links.{slot} (المرجع عبر {where})')
p.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'   أُضيف: {done}')
PY

echo "   ═══ 2) توليد الكتيب والتحقق ═══"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"
timeout 400 python3 tools/runbook.py verify --root . 2>&1 | tail -3 | cut -c1-170 | sed 's/^/   /'

echo "   ═══ 3) تثبيت عبر فرع وطلب دمج ═══"
cd "$R" || exit 1
git checkout -q -B fix/wire-links-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "ربط الملفات الجديدة عبر links الفعلية في المانيفست (ك-582)" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/wire-links-20261109 2>&1 | tail -1 | cut -c1-60 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/wire-links-20261109" --title "ربط الملفات الجديدة عبر links" --body "إصلاح بنية الربط الصحيحة بعد فشل S000." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 4) استئناف جولة 2026-11-09 ═══"
cd "$B" || exit 1
D=$(date -u +%F)
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909b.log 2>&1
echo "   rc=$?"
tail -20 /tmp/run0909b.log | cut -c1-175 | sed 's/^/   /'
echo "   ── الحالة ──"
timeout 300 python3 tools/runbook.py status --date "$D" 2>&1 | tail -5 | cut -c1-150 | sed 's/^/   /'