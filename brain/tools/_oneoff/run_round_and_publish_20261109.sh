#!/usr/bin/env bash
# تثبيت إصلاح محاذاة الإنجليزية + تشغيل الكتيب حتى النشر + التحقق الحي
set -uo pipefail
D="${1:-2026-11-08}"
R="/home/ubuntu/seawatch"
B="/home/ubuntu/mda-marine-system/brain"
M="/home/ubuntu/mda-marine-system"

echo "   ═══ 1) تثبيت إصلاح الموقع ═══"
cd "$R" || exit 1
echo "   الفرع: $(git branch --show-current)"
echo "   التغييرات: $(git status --porcelain | wc -l)"
git status --porcelain | head -6 | sed 's/^/      /'
git add -A sources tests generator 2>/dev/null
if ! git diff --cached --quiet; then
  git -c user.name="Manus" -c user.email="manus@local" commit -q -m "إصلاح جذري لمحاذاة الماستر الإنجليزي لجولة 2026-11-08

- إزالة سطر إنجليزي لا يقابله نص عربي، وإعادة القيمة 1982 إلى 1935.
- اختبار انحدار: test_2026_11_08_rebuild_preserves_arabic_page_structure
  (عدد tz-zones وli يساوي المصدر العربي، وبلا نصوص عربية في الإنجليزي).
- السبب المقيس: تحقق build_tm كان يفشل مغلقًا (عربي=140 · إنجليزي=141)."
  echo "   الالتزام: $(git log --oneline -1)"
else
  echo "   لا تغييرات قابلة للالتزام"
fi
env -u GH_TOKEN git push -q origin HEAD 2>&1 | tail -1
PR=$(env -u GH_TOKEN gh pr create --title "إصلاح جذري لمحاذاة الماستر الإنجليزي 2026-11-08" --body "إزالة سطر إنجليزي غير مقابل + إعادة 1935 + اختبار انحدار." 2>&1 | tail -1)
echo "   PR الموقع: $PR"
N=$(echo "$PR" | grep -oE '[0-9]+$' || true)
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1

echo "   ═══ 2) الكتيب: $D ═══"
cd "$B" || exit 1
pgrep -af 'runbook.py run' | cut -c1-80 | sed 's/^/   جارية: /'
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/rb.log 2>&1
RC=$?
echo "   الكتيب rc=$RC"
tail -12 /tmp/rb.log | cut -c1-170 | sed 's/^/   /'
if [ "$RC" = "10" ]; then
  echo "   → توقف يطلب تنفيذ خطوة: اقرأ /tmp/rb.log أعلاه"
elif [ "$RC" = "2" ]; then
  S=$(grep -oE '^[A-Z0-9]+' /tmp/rb.log | tail -1)
  echo "   → منع في $S · آخر سجل:"
  tail -8 "logs/runbook/$D/$S.log" 2>/dev/null | cut -c1-170 | sed 's/^/      /'
fi

echo "   ═══ 3) الحالة والتحقق الحي ═══"
python3 tools/runbook.py status --date "$D" 2>&1 | tail -4 | cut -c1-150 | sed 's/^/   /'
P="$R/dist/reports/$D.html"
if [ -f "$P" ]; then
  SHA=$(sha256sum "$P" | cut -c1-16)
  echo "   بناء محلي: $(stat -c%s "$P") بايت · $SHA"
fi
for U in "https://seawatch-live.pages.dev/reports/$D" "https://seawatch-xp4qirmr.manus.space/reports/$D.html"; do
  R2=$(curl -sSL --max-time 40 -o /tmp/out.html -w '%{http_code}|%{size_download}|%{content_type}' "$U" 2>/dev/null)
  echo "   $U → $R2"
done
echo "   ═══ 4) حلقة الإغلاق ═══"
timeout 600 python3 validators/check_closure.py --brain . 2>&1 | tail -3 | cut -c1-120 | sed 's/^/   /'
cd "$M" || exit 1
echo "   ملفات غير ملتزمة: $(git status --porcelain | wc -l)"
git log --oneline -1 | sed 's/^/   main: /'
