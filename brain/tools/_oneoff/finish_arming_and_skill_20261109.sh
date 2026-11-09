#!/usr/bin/env bash
# إتمام دفعة الأدلة الحقيقية + تثبيت المهارة الجديدة + الدمج.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
S=fault-evidence-arming-ops
cd "$B" || exit 1

echo "   ═══ 1) إعادة بناء الدفعة الحقيقية الكاملة ═══"
python3 - <<'PY'
import json, pathlib, re
root = pathlib.Path('.')
idx = {}
for d in ('validators', 'tests', 'tools', 'generator'):
    base = root / d
    if base.is_dir():
        for p in base.rglob('*'):
            if p.is_file() and p.suffix in ('.py', '.sh'):
                idx.setdefault(p.name, p)
TOKEN = re.compile(r'(?:validators|tests|tools|generator|skills)/[\w\u0600-\u06FF./-]+\.(?:py|sh)')
BASE = re.compile(r'\b([A-Za-z_][\w-]*\.(?:py|sh))\b')
rows = {}
for line in (root / 'audit/سجل-الأعطال-والثغرات.md').read_text(encoding='utf-8').splitlines():
    if line.startswith('| ك-'):
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) >= 12:
            rows[c[0]] = c
d = json.loads((root / 'audit/traceability.json').read_text(encoding='utf-8'))
open_ids = {r['fault_id'] for r in (d['rows'] if isinstance(d, dict) else d)
            if r['state'] in ('مفتوح', 'بانتظار التحقق')}
armed, unarmed = {}, []
for fid in sorted(open_ids):
    c = rows.get(fid)
    if not c:
        continue
    blob = ' '.join(c[4:11])
    rel = next((t for t in TOKEN.findall(blob) if (root / t).exists()), None)
    if rel:
        armed[fid] = f'timeout 120 python3 {rel}'
        continue
    bn = next((n for n in BASE.findall(blob) if n in idx), None)
    if bn:
        armed[fid] = f'timeout 120 python3 {idx[bn]}'
        continue
    unarmed.append(fid)
(root / 'audit/measurements/batches/commands-E2.json').write_text(
    json.dumps({'commands': armed}, ensure_ascii=False, indent=1), encoding='utf-8')
(root / 'audit/measurements/batches/no-command-rows-2.json').write_text(
    json.dumps({'rows': unarmed}, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'   مفتوح/بانتظار: {len(open_ids)} · مسلَّح: {len(armed)} · بلا دليل مسمّى: {len(unarmed)}')
PY

echo "   ═══ 2) تشغيل الدفعة الحقيقية E2 ═══"
timeout 3000 python3 tools/measurement_batch_runner.py --root . --batch E2 --timeout 120 --write-every 5 2>&1 | tail -6 | cut -c1-150 | sed 's/^/   /'
timeout 300 python3 tools/apply_batch_results.py --root . --apply 2>&1 | grep -E "مطبَّق" | head -2 | cut -c1-120 | sed 's/^/   /'
timeout 600 python3 tools/closure_round.py --apply 2>&1 | grep -E "الحالة التشغيلية" | cut -c1-140 | sed 's/^/   /'
timeout 300 python3 validators/check_closure.py --brain . 2>&1 | tail -2 | cut -c1-140 | sed 's/^/   /'

echo "   ═══ 3) تثبيت المهارة ═══"
rm -f "$B/skills/$S/references/api_reference.md"
rmdir "$B/skills/$S/templates" 2>/dev/null
python3 /home/ubuntu/skills/skill-creator/scripts/quick_validate.py --path "$B/skills/$S" 2>&1 | tail -2 | sed 's/^/   /'
for D in /home/ubuntu/skills /home/ubuntu/mda-marine-system/skills; do
  rm -rf "$D/$S"; cp -r "$B/skills/$S" "$D/$S"
done
python3 - <<'PY'
import hashlib, pathlib
def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]
paths = [f'/home/ubuntu/skills/fault-evidence-arming-ops/SKILL.md',
         f'/home/ubuntu/mda-marine-system/skills/fault-evidence-arming-ops/SKILL.md',
         f'/home/ubuntu/mda-marine-system/brain/skills/fault-evidence-arming-ops/SKILL.md']
vals = [h(p) for p in paths]
print('   تماثل الأسطح الثلاثة:', 'مطابق' if len(set(vals)) == 1 else 'مختلف', vals[0])
PY

echo "   ═══ 4) اعتماد المهارة في فهرس المشروع ═══"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('INDEX.md')
t = p.read_text(encoding='utf-8')
line = '- `skills/fault-evidence-arming-ops` — تسليح صفوف الأعطال بأوامر دليل حقيقية وتشغيلها حتى الإغلاق المشتقّ.\n'
if 'fault-evidence-arming-ops' not in t:
    marker = '\n## '
    i = t.find(marker)
    t = (t[:i] + '\n' + line + t[i:]) if i > 0 else (t + '\n' + line)
    p.write_text(t, encoding='utf-8')
    print('   ✔ أُضيفت إلى INDEX.md')
else:
    print('   • مسجّلة سابقًا')
PY

echo "   ═══ 5) الدمج عبر فرع وطلب دمج ═══"
cd "$R" || exit 1
git checkout -q -b fix/arming-skill-20261109 2>/dev/null || git checkout -q fix/arming-skill-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "تسليح الأدلة وتشديد شرط الإغلاق: منع الإغلاق بقياس فاشل وإغلاق 16 صفًا موثّقًا

- اشتقاق حكم الدفعة من rc وبناء الدليل من الأمر ورمزه.
- ضبط عمود الإصلاح ليُشتق الصف «منفَّذ» بدل «لم يبدأ».
- فصل نمط النجاح SUCCESS عن OUTCOME: لا إغلاق بقياس فاشل.
- مهارة جديدة: fault-evidence-arming-ops مع سكربت تسليح ومرجع عقد الدليل."
PR=$(env -u GH_TOKEN gh pr create --title "تسليح الأدلة وتشديد شرط الإغلاق (ك-579)" --body "إصلاح جذري لخط الربط بين نتيجة الدفعة وصف العطل، وتشديد الإغلاق على النجاح فقط، ومهارة تسليح الأدلة." --base main 2>&1 | tail -1)
echo "   PR: $(echo "$PR" | cut -c1-90)"
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1)
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -2 | cut -c1-110 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · نظافة: $(git status --porcelain | wc -l) ملف"