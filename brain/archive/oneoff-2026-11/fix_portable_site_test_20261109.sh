#!/usr/bin/env bash
# إغلاق ك-587: مسار مطلق في اختبار الموقع أسقط بوابة قابلية النقل G026، وتثبيت الإصلاح
# في شجرة الموقع ومرآتها، ثم استئناف الجولة.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
S=/home/ubuntu/seawatch
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) تسجيل ك-587 ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('audit/سجل-الأعطال-والثغرات.md')
lines = p.read_text(encoding='utf-8').splitlines()
cells = ['ك-587',
 'مسار مطلق مكتوب في شيفرة اختبار الموقع أوقف بوابة قابلية النقل',
 'seawatch/tests/test_i18n_alignment.py كتب جذر brain مطلقًا في وسيط احتياطي، فرفضته بوابة G026 عند فحص شجرة الموقع.',
 'اشتقاق الجذر من وحدة الجذر القانوني في المولّد (generator/brain_root.py) بدل كتابة المسار في الشيفرة.',
 'وحدة brain_root() قابلة للاستيراد + بوابة check_portable_paths تفشل مغلقًا على أي مسار مطلق.',
 'قياس حي: بوابة قابلية النقل rc=0 واختبار المواءمة نفسه rc=0 بعد الإصلاح (ولم يكن يعمل قبل الوحدة).',
 'أمر إعادة التشغيل: python3 validators/check_portable_paths.py && python3 tests/test_i18n_alignment.py',
 'مغلقة', 'منفَّذ', 'تحقق تشغيلي ناجح', 'مطبَّق', 'مغلقة نهائيًا']
row = '| ' + ' | '.join(cells) + ' |'
idx = max(i for i, l in enumerate(lines) if l.startswith('| ك-'))
lines[idx + 1:idx + 1] = [row]
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('   ✔ أُضيف ك-587')
PY

echo "   ═══ 2) مزامنة المرآة وتوليد الحلقة ═══"
cp "$S/tests/test_i18n_alignment.py" "$R/site/tests/test_i18n_alignment.py" && echo "   ✔ زُوّمت نسخة الاختبار في مرآة المستودع"
timeout 900 python3 tools/closure_round.py --apply 2>&1 | tail -2 | cut -c1-170 | sed 's/^/   /'
printf "   %-30s" "حارس الإغلاق:"; timeout 600 python3 validators/check_closure.py --brain . >/tmp/cc3.txt 2>&1; echo "rc=$?"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"

echo "   ═══ 3) تثبيت شجرة الموقع عبر فرع وطلب دمج ═══"
cd "$S" || exit 1
echo "   ملفات متغيرة: $(git status --porcelain | wc -l)"
git checkout -q -B fix/portable-site-test-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "اختبار المواءمة: اشتقاق جذر brain من الوحدة القانونية بدل مسار مطلق" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/portable-site-test-20261109 2>&1 | tail -1 | cut -c1-70 | sed 's/^/   /'
PRS=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/portable-site-test-20261109" --title "قابلية نقل اختبار المواءمة" --body "إزالة مسار مطلق من اختبار المواءمة واشتقاق الجذر من brain_root()." --base main 2>&1 | tail -1)
NS=$(echo "$PRS" | grep -oE '[0-9]+$' | tail -1); echo "   PR الموقع: $NS"
[ -n "${NS:-}" ] && env -u GH_TOKEN gh pr merge "$NS" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   الموقع main: $(git rev-parse --short HEAD) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 4) تثبيت الحزمة في مستودع الدماغ ═══"
cd "$R" || exit 1
git checkout -q -B fix/portable-gate-20261109 main
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "إغلاق ك-587: قابلية نقل اختبار الموقع وملاءمة المرآة وحلقة الإغلاق" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/portable-gate-20261109 2>&1 | tail -1 | cut -c1-70 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/portable-gate-20261109" --title "إغلاق ك-587 وقابلية النقل" --body "سجل العطل + ملاءمة مرآة الموقع + حلقة الإغلاق." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR الدماغ: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 5) استئناف الجولة ═══"
cd "$B" || exit 1
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909n.log 2>&1
echo "   rc=$?"
tail -20 /tmp/run0909n.log | cut -c1-185 | sed 's/^/   /'