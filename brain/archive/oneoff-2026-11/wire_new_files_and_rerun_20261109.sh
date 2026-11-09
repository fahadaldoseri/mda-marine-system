#!/usr/bin/env bash
# ربط الملفات الأربعة غير المتصلة بخطواتها في المانيفست ثم استئناف جولة 2026-11-09.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1

echo "   ═══ 1) ربط الملفات بمصادرها الحاكمة ═══"
python3 - <<'PY'
import json, pathlib
m = json.loads(pathlib.Path('runbook/runbook.json').read_text(encoding='utf-8'))
steps = m.get('steps', m if isinstance(m, list) else [])
NEW = {
    'validators/check_ledger_matrix_parity.py': 'validators/check_closure.py',
    'validators/check_enforcer_coverage.py': 'tools/self_improve.py',
    'tests/test_ledger_matrix_parity_guard.py': 'validators/check_closure.py',
    'tests/test_batch_runner_safe_id.py': 'tools/measurement_batch_runner.py',
}
# فهرسة كل قوائم الملفات في المانيفست بمواضعها
found = {}
for si, s in enumerate(steps):
    for key in ('files', 'inputs', 'outputs', 'artifacts'):
        if isinstance(s.get(key), list):
            for fi, f in enumerate(s[key]):
                if isinstance(f, str):
                    found.setdefault(f, (si, key, fi))
added = []
for new, ref in NEW.items():
    if new in found:
        print(f'   • {new}: مربوط مسبقًا')
        continue
    if ref not in found:
        print(f'   ⚠ مرجع {ref} غير معلن — {new} يحتاج ربطًا يدويًا')
        continue
    si, key, fi = found[ref]
    steps[si][key].insert(fi + 1, new)
    added.append((new, steps[si].get('id') or steps[si].get('step') or si, key))
pathlib.Path('runbook/runbook.json').write_text(
    json.dumps(m, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for n, s, k in added:
    print(f'   ✔ {n} → الخطوة {s} ({k})')
print(f'   أُضيف: {len(added)}')
PY

echo "   ═══ 2) توليد الكتيب والتحقق ═══"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"
timeout 400 python3 tools/runbook.py verify --root . 2>&1 | tail -3 | cut -c1-170 | sed 's/^/   /'

echo "   ═══ 3) تثبيت الربط عبر فرع وطلب دمج ═══"
cd "$R" || exit 1
git checkout -q -B fix/wire-new-files-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "ربط الملفات الأربعة الجديدة بخطواتها في المانيفست (ك-582)

حارس تكامل السجل والمصفوفة وحارس تغطية المُفعِّلات واختباراهما كانا غير متصلين
بأي خطوة، فرفض فحص المانيفست S000 الجولة برمز 2." 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/wire-new-files-20261109 2>&1 | tail -1 | cut -c1-60 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/wire-new-files-20261109" --title "ربط الملفات الجديدة بخطوات المانيفست" --body "إصلاح سبب توقف S000: أربعة ملفات غير متصلة." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 4) استئناف جولة 2026-11-09 ═══"
cd "$B" || exit 1
D=$(date -u +%F)
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909.log 2>&1
RC=$?
echo "   rc=$RC"
tail -18 /tmp/run0909.log | cut -c1-175 | sed 's/^/   /'
echo "   ── الحالة ──"
timeout 300 python3 tools/runbook.py status --date "$D" 2>&1 | tail -6 | cut -c1-150 | sed 's/^/   /'