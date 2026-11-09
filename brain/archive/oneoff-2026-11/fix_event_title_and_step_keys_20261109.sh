#!/usr/bin/env bash
# إصلاح جذري: إعادة نوع الواقعة إلى عنوانها كما في المصدر، وإكمال مفاتيح الخطوة S065، وتسجيل العطل.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1
D=$(date -u +%F)

echo "   ═══ 1) إصلاح العنوان في الدفتر والمتنين ═══"
python3 - <<'PY'
import json, pathlib
OLD_AR = "تحديث عنوان UKMTO عن واقعة متأخرة الإبلاغ على بعد 16 ميلًا بحريًا شرق خصب"
NEW_AR = "تحديث عنوان UKMTO عن واقعة هجوم متأخرة الإبلاغ على بعد 16 ميلًا بحريًا شرق خصب"
# الدفتر
p = pathlib.Path('cumulative-2026/daily/2026-11-09.json')
d = json.loads(p.read_text(encoding='utf-8'))
hit = 0
for e in d:
    if e.get('code') == 'MN-2026-11-09-03' and OLD_AR in str(e.get('title', '')):
        e['title'] = NEW_AR
        e['title_basis'] = "نوع الواقعة «هجوم» من نص المصدر نفسه: «06/11/2026 Attack:UKMTO has received a time-late report…»"
        hit += 1
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'   الدفتر: عُدّل {hit} عنوانًا')
# المتن العربي
ar = pathlib.Path('reports/2026-11-09-sectioned.md')
t = ar.read_text(encoding='utf-8')
n = t.count(OLD_AR)
if n:
    ar.write_text(t.replace(OLD_AR, NEW_AR), encoding='utf-8')
print(f'   المتن العربي: {n} موضعًا')
# الماستر الإنجليزي: إظهار نوع الواقعة على السطر نفسه
en = pathlib.Path('/home/ubuntu/seawatch/sources/i18n/en/2026-11-09-sectioned.en.md')
if en.exists():
    lines = en.read_text(encoding='utf-8').splitlines()
    c = 0
    for i, l in enumerate(lines):
        if 'MN-2026-11-09-03' in l and 'an incident' in l:
            lines[i] = l.replace('an incident', 'an attack'); c += 1
    en.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'   الماستر الإنجليزي: {c} سطرًا')
PY

echo "   ═══ 2) إكمال مفاتيح الخطوة S065 ═══"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('runbook/runbook.json')
m = json.loads(p.read_text(encoding='utf-8'))
by = {s.get('id'): s for s in m['steps']}
s65, s70 = by.get('S065'), by.get('S070')
if not s65:
    print('   ⚠ S065 غير موجودة')
else:
    s65.setdefault('kind', 'script')
    s65.setdefault('reads', ['cumulative-2026/daily/{date}.json', 'appendices/zone-registry.json',
                             'appendices/zone-overrides.json', 'appendices/threat-scale.json'])
    s65.setdefault('writes', ['web/zones/{date}.json'])
    s65.setdefault('declares', {'reads': ['cumulative-2026/daily/*.json'], 'writes': ['web/zones/{date}.json']})
    p.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('   ✔ مفاتيح S065:', sorted(s65))
PY

echo "   ═══ 3) تسجيل العطل في السجل الحاكم ═══"
python3 - <<'PY'
import pathlib, re, datetime
log = pathlib.Path('audit/سجل-الأعطال-والثغرات.md')
lines = log.read_text(encoding='utf-8').splitlines()
rows = [l for l in lines if l.startswith('| ك-')]
ncols = rows[-1].count('|') - 1
last = int(re.search(r'ك-(\d+)', rows[-1]).group(1))
cells = [
    f'ك-{last+1}',
    'عنوان واقعة رسمية أسقط نوعها المذكور في المصدر فأوقفت بوابة الاستبعاد الصامت بطاقة القطاعات',
    'مولّد القطاعات يشترط أن يحمل عنوان الواقعة الرسمية المستهدفة للسفن كلمة نوع مؤهّل من السجل، وعنوان MN-2026-11-09-03 كتب «واقعة» بلا نوع، فنُعتت الواقعة استبعادًا صامتًا وأُوقفت الخطوة.',
    'إعادة نوع الواقعة إلى العنوان كما في نص المصدر نفسه («Attack» ⇒ هجوم) في الدفتر والمتنين، مع حقل أساس للعنوان؛ وبقيت البوابة كما هي بلا تخفيف.',
    'قاعدة: عنوان الواقعة يحمل نوعها الوارد في المصدر حرفيًا، وبوابة الاستبعاد الصامت تفشل مغلقًا عند غيابه.',
    'سجل الأعطال ومصفوفة التتبع: الصف مربوط بأمر إعادة قياس بوابة القطاعات.',
    'مغلق',
    datetime.date.today().isoformat(),
    'قياس حي: تشغيل مولّد القطاعات بعد التعديل يعيد رمزًا 0 ويكتب بطاقة اليوم.',
    'أمر إعادة التشغيل: python3 tools/classify_zones.py --date <DATE> --write',
    'run_evidence: python3 tools/classify_zones.py --date <DATE> --write && test -s web/zones/<DATE>.json',
    'الدرس: نوع الواقعة جزء من عنوانها لا زينة؛ إسقاطه يوقف العدّ.',
]
if len(cells) != ncols:
    print(f'   ⚠ عدد الأعمدة لا يطابق ({len(cells)} ≠ {ncols}) — لم يُكتب الصف')
else:
    out, done = [], False
    for l in lines:
        out.append(l)
        if l is rows[-1]:
            out.append('| ' + ' | '.join(cells) + ' |'); done = True
    log.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'   ✔ سُجّل ك-{last+1}' if done else '   ⚠ لم يُدرج')
PY

echo "   ═══ 4) إعادة قياس القطاعات والتحقق ═══"
timeout 300 python3 tools/classify_zones.py --date "$D" --write 2>&1 | tail -3 | cut -c1-175 | sed 's/^/   /'
ls -l "web/zones/$D.json" 2>/dev/null | awk '{print "   بطاقة اليوم: "$5" بايت"}'
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"
timeout 400 python3 tools/runbook.py verify --root . 2>&1 | tail -2 | cut -c1-170 | sed 's/^/   /'

echo "   ═══ 5) تثبيت عبر فرع وطلب دمج ═══"
cd "$R" || exit 1
git checkout -q -B fix/event-title-type-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "إعادة نوع الواقعة إلى عنوانها وإكمال مفاتيح خطوة القطاعات (ك-578)" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/event-title-type-20261109 2>&1 | tail -1 | cut -c1-60 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/event-title-type-20261109" --title "إصلاح نوع الواقعة ومفاتيح S065" --body "بوابة القطاعات كانت محقة؛ الإصلاح في العنوان." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 6) استئناف الجولة ═══"
cd "$B" || exit 1
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909g.log 2>&1
echo "   rc=$?"
tail -16 /tmp/run0909g.log | cut -c1-180 | sed 's/^/   /'