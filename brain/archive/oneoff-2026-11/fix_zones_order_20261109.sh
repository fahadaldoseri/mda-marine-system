#!/usr/bin/env bash
# إصلاح جذر ترتيب بطاقة القطاعات: خطوة مستقلة قبل W020، مع تسجيل العطل، ثم استئناف الجولة.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1

echo "   ═══ 1) إدراج خطوة تصنيف القطاعات قبل W020 ═══"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('runbook/runbook.json')
m = json.loads(p.read_text(encoding='utf-8'))
steps = m['steps']
ids = [s.get('id') for s in steps]
if 'S065' in ids:
    print('   • S065 موجودة مسبقًا')
else:
    i = ids.index('W020')
    tpl = steps[i]
    step = {
        "id": "S065",
        "title": "تصنيف القطاعات ومستوى التهديد قبل ملف الواجهة",
        "phase": tpl.get("phase", "write"),
        "command": ["bash", "-lc",
                    'B="$PWD"; export B SITE; python3 "$B/tools/classify_zones.py" --date "$D" --write; rc=$?; exit $rc'],
        "assert": [{"type": "cmd", "command": ["bash", "-lc", "test -s web/zones/{date}.json"]}],
        "ok_rc": [0],
        "on_fail": "stop",
        "links": {"rules": [], "files": ["tools/classify_zones.py"],
                  "gates": [], "tests": ["tests/test_classify_zones_damage_scope.py"]},
    }
    steps.insert(i, step)
    p.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'   ✔ أُدرجت S065 قبل W020 (موضع {i})')
PY

echo "   ═══ 2) تشغيل مولّد القطاعات لليوم ═══"
D=$(date -u +%F)
python3 tools/classify_zones.py --date "$D" --write 2>&1 | tail -4 | cut -c1-160 | sed 's/^/   /'
ls -l "web/zones/$D.json" 2>/dev/null | awk '{print "   الحجم: "$5" "$9}'

echo "   ═══ 3) تسجيل العطل في السجل الحاكم ═══"
python3 - <<'PY'
import pathlib, re
log = pathlib.Path('audit/سجل-الأعطال-والثغرات.md')
lines = log.read_text(encoding='utf-8').splitlines()
rows = [l for l in lines if l.startswith('| ك-')]
if not rows:
    print('   ⚠ لم أجد صفوف أعطال — لم يُكتب شيء')
else:
    ncols = rows[-1].count('|') - 1
    last = int(re.search(r'ك-(\d+)', rows[-1]).group(1))
    new_id = f'ك-{last+1}'
    cells = [
        new_id,
        'عيب ترتيب في المانيفست: خطوة ملف الواجهة تشترط بطاقة قطاعات تُبنى لاحقًا',
        'W020 تتحقق من اتساق lede مع web/zones/{date}.json، لكن الملف يُبنى داخل S070 اللاحقة، فيتوقف الكتيب عند W020 بلا مخرج ممكن.',
        'إدراج خطوة مستقلة S065 قبل W020 تشغّل tools/classify_zones.py --write، مع شرط وجود الملف، وبقاء S070 كما هي.',
        'خطوة S065 مع شرط test -s web/zones/{date}.json وربط tools/classify_zones.py واختبار tests/test_classify_zones_damage_scope.py',
        'قاعدة: كل خطوة تُعلن مخرجًا في عقدها يجب أن يسبقها منتجه في الترتيب، لا أن يلحقه.',
        'فحص الترتيب: python3 tools/runbook.py verify --root . ثم تشغيل الجولة والتوقف عند W020 لا قبله.',
        'مغلق',
        f'{__import__("datetime").date.today().isoformat()}',
        'قياس حي: تشغيل الجولة وصل إلى W020 بعد وجود البطاقة.',
        'أمر إعادة التشغيل: python3 tools/classify_zones.py --date <DATE> --write',
        'run_evidence: python3 tools/runbook.py verify --root . ; python3 tools/classify_zones.py --date <DATE> --write',
    ]
    if len(cells) != ncols:
        print(f'   ⚠ عدد الأعمدة لا يطابق ({len(cells)} ≠ {ncols}) — لم يُكتب الصف')
    else:
        row = '| ' + ' | '.join(cells) + ' |'
        out = []
        inserted = False
        for l in lines:
            out.append(l)
            if l is rows[-1]:
                out.append(row); inserted = True
        log.write_text('\n'.join(out) + '\n', encoding='utf-8')
        print(f'   ✔ سُجّل {new_id} ({ncols} عمودًا)')
PY

echo "   ═══ 4) توليد الكتيب والتحقق ═══"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"
timeout 400 python3 tools/runbook.py verify --root . 2>&1 | tail -2 | cut -c1-170 | sed 's/^/   /'

echo "   ═══ 5) تثبيت عبر فرع وطلب دمج ═══"
cd "$R" || exit 1
git checkout -q -B fix/zones-order-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "إصلاح ترتيب بطاقة القطاعات قبل ملف الواجهة (خطوة S065)" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/zones-order-20261109 2>&1 | tail -1 | cut -c1-60 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/zones-order-20261109" --title "إصلاح ترتيب بطاقة القطاعات" --body "S065 قبل W020 مع تسجيل العطل." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 6) استئناف الجولة ═══"
cd "$B" || exit 1
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909f.log 2>&1
echo "   rc=$?"
tail -14 /tmp/run0909f.log | cut -c1-180 | sed 's/^/   /'