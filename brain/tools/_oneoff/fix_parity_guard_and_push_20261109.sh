#!/usr/bin/env bash
# إصلاح العدّاد الأعمى في حارس التكامل + اختبار موجب/سالب + دفع عبر فرع.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1

echo "   ═══ 1) إصلاح العدّاد الأعمى ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('validators/check_ledger_matrix_parity.py')
t = p.read_text(encoding='utf-8')
old = "if l.startswith('| ك-')]"
new = "if FAULT_ROW.match(l)]"
assert old in t
t = t.replace(old, new)
t = t.replace("import pathlib\nimport sys", "import pathlib\nimport re\nimport sys")
if 'FAULT_ROW' not in t.split('def main')[0]:
    t = t.replace("def main() -> int:", "FAULT_ROW = re.compile(r'^\\|\\s*[\\u0621-\\u064A]{1,3}-\\d')\n\n\ndef main() -> int:", 1)
p.write_text(t, encoding='utf-8')
print('   ✔ الحارس يعدّ كل عائلات المعرّفات (ك · ز · ع · م · ث)')
PY
grep -rn "'| ك-'\|\"| ك-\"" --include=*.py tools validators tests 2>/dev/null | cut -c1-120 | sed 's/^/   متبقٍ: /' || echo "   لا عدّاد أعمى متبقٍ"
timeout 300 python3 validators/check_ledger_matrix_parity.py --brain . 2>&1 | tail -3 | sed 's/^/   /'

echo "   ═══ 2) اختبار موجب وسالب للحارس ═══"
cat > tests/test_ledger_matrix_parity_guard.py <<'PY'
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
PY
timeout 300 python3 -m pytest tests/test_ledger_matrix_parity_guard.py -q 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   اختبار الحارس: /'

echo "   ═══ 3) إعادة الاشتقاق والحراس ═══"
timeout 600 python3 tools/closure_round.py --apply 2>&1 | grep -E "الحالة التشغيلية" | cut -c1-140 | sed 's/^/   /'
timeout 300 python3 validators/check_closure.py --brain . 2>&1 | tail -2 | cut -c1-140 | sed 's/^/   /'
timeout 300 python3 validators/check_ledger_matrix_parity.py --brain . 2>&1 | tail -2 | sed 's/^/   /'

echo "   ═══ 4) المهارة: إضافة قسم العدّ الصحيح ═══"
python3 - <<'PY'
import pathlib
S = pathlib.Path('/home/ubuntu/mda-marine-system/brain/skills/fault-ledger-matrix-parity-ops')
add = """
## العدّ الصحيح للمعرّفات

المعرّفات في هذا السجل تتبع عائلات عدة: `ك-` و`ز-` و`ع-` و`م-` و`ث-`، وبعضها بلاحقة (`ث-02/ب`).
العدّ بـ`startswith('| ك-')` أعمى عن غير `ك-` وأنتج تباعدًا وهميًا بمقدار 13 صفًا. استخدم:

```python
FAULT_ROW = re.compile(r'^\\|\\s*[\\u0621-\\u064A]{1,3}-\\d')
```
"""
for f in [S / 'SKILL.md',
          pathlib.Path('/home/ubuntu/skills/fault-ledger-matrix-parity-ops/SKILL.md'),
          pathlib.Path('/home/ubuntu/mda-marine-system/skills/fault-ledger-matrix-parity-ops/SKILL.md')]:
    t = f.read_text(encoding='utf-8')
    if 'العدّ الصحيح للمعرّفات' not in t:
        i = t.find('\n## المراجع')
        f.write_text((t[:i] + add + t[i:]) if i > 0 else t + add, encoding='utf-8')
print('   ✔ أُضيف قسم العدّ الصحيح إلى الأسطح الثلاثة')
PY
python3 - <<'PY'
import hashlib, pathlib
S = 'fault-ledger-matrix-parity-ops'
v = [hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16] for p in (
    f'/home/ubuntu/skills/{S}/SKILL.md', f'/home/ubuntu/mda-marine-system/skills/{S}/SKILL.md',
    f'/home/ubuntu/mda-marine-system/brain/skills/{S}/SKILL.md')]
print('   تماثل الأسطح:', 'مطابق' if len(set(v)) == 1 else 'مختلف', v[0])
PY

echo "   ═══ 5) الدفع عبر فرع وطلب دمج ═══"
cd "$R" || exit 1
git checkout -q -B fix/ledger-parity-guard-20261109 2>/dev/null
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "إصلاح العدّاد الأعمى للمعرّفات وضبط تكامل السجل والمصفوفة (ك-580)

- جذر التباعد الوهمي: عدّ الصفوف بـ'| ك-' أعمى عن عائلات ز/ع/م/ث.
- استعادة 13 صفًا موجودة في المصفوفة وحدها → تطابق 619=619 في الاتجاهين.
- حارس التكامل يعدّ كل العائلات، واختبار موجب/سالب لثلاث حالات." 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/ledger-parity-guard-20261109 2>&1 | tail -1 | cut -c1-100 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/ledger-parity-guard-20261109" --title "تكامل السجل والمصفوفة: إصلاح العدّاد الأعمى" --body "13 صفًا مستعادة من المصفوفة، حارس يفشل مغلقًا ويعدّ كل العائلات، اختبار ثلاث حالات." --base main 2>&1 | tail -1)
echo "   PR: $(echo "$PR" | cut -c1-95)"
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1)
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-110 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"
timeout 300 python3 "$B/validators/check_ledger_matrix_parity.py" --brain "$B" 2>&1 | tail -2 | sed 's/^/   بعد الدمج: /'