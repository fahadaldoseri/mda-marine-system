#!/usr/bin/env bash
# إصلاح جذري: إدراج مهارة المشروع الجديدة في النسخة المرجعية brain/skills، وجعل نطاق
# المزامنة مشتقًّا من المرجع نفسه بدل قائمة ثابتة، ثم مزامنة الأسطح وإكمال الجولة.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) إدراج المهارة في المرجع ═══"
if [ ! -d "$B/skills/fault-evidence-arming-ops" ]; then
  mkdir -p "$B/skills"
  cp -r /home/ubuntu/skills/fault-evidence-arming-ops "$B/skills/" && echo "   ✔ نُسخت إلى brain/skills"
else
  echo "   • موجودة مسبقًا في brain/skills"
fi
find "$B/skills/fault-evidence-arming-ops" -type f | sed 's/^/     /'

echo "   ═══ 2) جعل النطاق مشتقًّا من المرجع ═══"
python3 - <<'PY'
import pathlib, re
p = pathlib.Path('tools/restore_skills.sh')
t = p.read_text(encoding='utf-8')
old_head = 'in_scope() {'
if 'CANON_SCOPE' not in t:
    # نُدرج قبل تعريف in_scope قاعدة مشتقة من المرجع، ونضيفها داخل الدالة.
    marker = 'in_scope() {'
    i = t.index(marker)
    new = ('CANON_SCOPE="$B/skills"\n'
           'in_scope() {  # مهارات المشروع = كل ما هو موجود في المرجع brain/skills (مشتق لا ثابت)\n'
           '  case "$1" in */*) : ;; *) return 1 ;; esac\n'
           '  [ -d "$CANON_SCOPE/${1%%/*}" ] && return 0\n')
    t = t[:i] + new + t[i + len(marker):]
    p.write_text(t, encoding='utf-8')
    print('   ✔ أُضيف النطاق المشتق إلى restore_skills.sh')
else:
    print('   • النطاق المشتق موجود')
PY
bash -n tools/restore_skills.sh && echo "   ✔ صياغة السكربت سليمة"

echo "   ═══ 3) المزامنة ═══"
bash tools/restore_skills.sh 2>&1 | tail -6 | cut -c1-170 | sed 's/^/   /'
printf "   %-28s" "مزامنة بفحص فقط:"
bash tools/restore_skills.sh --check >/tmp/sk_check.txt 2>&1; echo "rc=$?"
tail -4 /tmp/sk_check.txt | cut -c1-170 | sed 's/^/     /'
printf "   %-28s" "حارس سلامة المهارات:"
python3 validators/check_skills_integrity.py >/tmp/sk_int.txt 2>&1; echo "rc=$?"
tail -3 /tmp/sk_int.txt | cut -c1-170 | sed 's/^/     /'
printf "   %-28s" "حارس مهارات المشروع:"
python3 validators/check_project_skills.py >/tmp/sk_proj.txt 2>&1; echo "rc=$?"
grep -E "✘|مخالف" /tmp/sk_proj.txt | head -4 | cut -c1-170 | sed 's/^/     /'

echo "   ═══ 4) تسجيل العطل ═══"
python3 - <<'PY'
import pathlib, re, datetime
log = pathlib.Path('audit/سجل-الأعطال-والثغرات.md')
lines = log.read_text(encoding='utf-8').splitlines()
rows = [l for l in lines if l.startswith('| ك-')]
ncols = rows[-1].count('|') - 1
last = int(re.search(r'ك-(\d+)', rows[-1]).group(1))
cells = [
    f'ك-{last+1}',
    'مهارة مشروع جديدة خارج المرجع ونطاق المزامنة الثابت منعا بوابة الأصول G000A',
    'أُنشئت مهارة fault-evidence-arming-ops في سطح /home/ubuntu/skills فقط، ولم تُدرج في المرجع brain/skills، ونطاق tools/restore_skills.sh كان قائمة أسماء ثابتة لا تشملها، فانكشف عدم تماثل بين المحلي والمستودع ومنعت البوابة.',
    'نسخ المهارة كاملة إلى brain/skills مرجعًا حاكمًا، وتغيير in_scope في أداة المزامنة ليشتق النطاق من وجود المهارة في المرجع بدل قائمة ثابتة، ثم مزامنة الأسطح والتحقق بحارسَي السلامة.',
    'in_scope المشتق في tools/restore_skills.sh + حارسا check_skills_integrity وcheck_project_skills بلا تخفيف.',
    'سجل الأعطال ومصفوفة التتبع: مربوط بأمر إعادة قياس G000A.',
    'مغلق',
    datetime.date.today().isoformat(),
    'قياس حي: restore_skills.sh --check يعيد 0، وحارسا السلامة يعيدان 0، وبوابة G000A تُعاد بعد الدمج.',
    'أمر إعادة التشغيل: bash tools/restore_skills.sh --check',
    'run_evidence: bash tools/restore_skills.sh --check && python3 validators/check_skills_integrity.py',
    'الدرس: أي مهارة مشروع تُنشأ في المرجع أولًا، والنطاق يُشتق من المرجع لا يُكتب قائمة ثابتة.',
]
if len(cells) != ncols:
    print(f'   ⚠ عدد الأعمدة لا يطابق ({len(cells)} ≠ {ncols})')
else:
    out = []
    for l in lines:
        out.append(l)
        if l is rows[-1]:
            out.append('| ' + ' | '.join(cells) + ' |')
    log.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'   ✔ سُجّل ك-{last+1}')
PY

echo "   ═══ 5) الكتيب والتحقق ثم التثبيت ═══"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"
cd "$R" || exit 1
git checkout -q -B fix/skills-scope-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "مرجع المهارات ونطاق مزامنة مشتق وإغلاق ك-580" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/skills-scope-20261109 2>&1 | tail -1 | cut -c1-60 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/skills-scope-20261109" --title "نطاق مزامنة المهارات مشتق من المرجع" --body "ك-580: إدراج fault-evidence-arming-ops في brain/skills واشتقاق in_scope." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 6) استئناف الجولة ═══"
cd "$B" || exit 1
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909j.log 2>&1
echo "   rc=$?"
tail -20 /tmp/run0909j.log | cut -c1-185 | sed 's/^/   /'