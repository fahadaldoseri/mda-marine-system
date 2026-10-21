#!/usr/bin/env bash
# ═══ أمر الإغلاق الدائم — كل جلسة تطوير أو إصدار ينتهي بهذا الأمر ═══
# القاعدة (قرار صاحب القرار — 20 أكتوبر 2026):
#   لا يُعدّ أي عمل منتهيًا قبل أن تُحدَّث المكتبات وتُتحقَّق المهارات ويُدفع GitHub.
#
# المراحل:
#   1) تحديث المكتبات اللغوية من كل الإصدارات
#   2) التحقق من سلامة المهارتين الحاكمتين
#   3) فحص الأسرار قبل الدفع (فشل مغلق)
#   4) دفع النسخة الاحتياطية + الموقع إلى GitHub
#   5) تحقق نهائي من الحصيلة
#
# الاستخدام: bash tools/publish_changes.sh ["رسالة الالتزام"] [--no-libs]
set -u

_B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
_S="${SITE_DIR:-$(dirname "$_B")/seawatch}"
_OUT="${BACKUP_REPO_DIR:-$(dirname "$_B")/mda-marine-system}"
_SK="${SKILLS_DIR:-/home/ubuntu/skills}"
MSG="${1:-تحديث النظام $(date -u +%F)}"
SKIP_LIBS=0
for a in "$@"; do [ "$a" = "--no-libs" ] && SKIP_LIBS=1; done
FAIL=0
say() { printf '\n───── %s ─────\n' "$1"; }

D=$(ls "$_B/reports" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-sectioned\.md$' \
    | sed 's/-sectioned\.md//' | sort | tail -1)

# 1) المكتبات اللغوية
if [ "$SKIP_LIBS" = "0" ] && [ -n "$D" ]; then
  say "1) تحديث المكتبات اللغوية — حتى $D"
  python3 "$_B/tools/audit_corpus.py" --date "$D" 2>&1 | tail -3 || FAIL=1
  python3 "$_B/tools/build_audit_report.py" "$D" 2>&1 | tail -3 || FAIL=1
  echo "  مكتبات: $(ls "$_B/appendices/libraries" 2>/dev/null | wc -l) ملفًا"
else
  say "1) المكتبات — تخطٍّ"
fi

# 2) المهارات
say "2) التحقق من المهارتين الحاكمتين"
for sk in marine-news-brain military-arabic-editing; do
  if python3 "$_SK/skill-creator/scripts/quick_validate.py" "$sk" 2>&1 | grep -q "valid"; then
    echo "  ✔ $sk"
  else
    echo "  ✘ $sk — مهارة غير صالحة، أوقف الدفع"; FAIL=1
  fi
done
for sk in marine-news-brain military-arabic-editing; do
  [ -f "$_SK/$sk/SKILL.md" ] || { echo "  ✘ مهارة مفقودة: $sk"; FAIL=1; }
done
# شواهد القواعد المعتمدة — عطل ك-48: فُقدت قواعد معتمدة ثم نُسخ النقص فوق المستودع.
# القاعدة: ما نقص يُستعاد من المستودع، ولا يُدفع نقص فوقه.
SK_OUT=$(python3 "$_B/validators/check_skills_integrity.py" 2>&1); SK_RC=$?
python3 "$_B/validators/check_libraries_skills.py" || echo "  • تدقيق المكتبات والمهارات: تحذير"
echo "$SK_OUT" | tail -4
if [ "$SK_RC" = "2" ]; then
  echo "  ↩ استعادة المهارات من المستودع قبل الدفع"
  bash "$_B/tools/restore_skills.sh" 2>&1 | tail -3
  SK_OUT=$(python3 "$_B/validators/check_skills_integrity.py" 2>&1); SK_RC=$?
  echo "$SK_OUT" | tail -3
  [ "$SK_RC" = "2" ] && { echo "  ✘ نقص قواعد لم يُستعد — أوقف الدفع"; FAIL=1; }
fi

# 3) فحص الأسرار — فشل مغلق
say "3) فحص الأسرار"
SECRETS=$(grep -rlE '8949347226:[A-Za-z0-9_-]{30,}|sk-[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY' \
  "$_B" "$_S" 2>/dev/null | grep -v '/\.git/' | grep -vE '\.example$|telegram-policy|appendices/telegram-chat' | head -10)
if [ -n "$SECRETS" ]; then
  echo "  ✘ أسرار محتملة — أوقف الدفع:"; echo "$SECRETS" | sed 's/^/     /'; FAIL=1
else
  echo "  ✔ لا أسرار في الشجرة"
fi
[ "$FAIL" = "1" ] && { say "أوقف: أصلح ما سبق قبل الدفع"; exit 2; }

# 4) الدفع
say "4) الدفع إلى GitHub"
bash "$_B/tools/github_backup.sh" 2>&1 | tail -3 || FAIL=1

echo "── تماثل المهارات بعد الدفع ──"
bash "$_B/tools/restore_skills.sh" --check 2>&1 | tail -2 || \
  echo "  • تماثل المهارات: يحتاج مراجعة (المحلي أحدث — ادفعه)"
if [ -d "$_S/.git" ]; then
  cd "$_S"
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -q -m "$MSG" || true
    git pull --rebase -q origin main 2>/dev/null || true
    git push -q origin main && echo "  ✔ الموقع مدفوع: $(git log --oneline -1)" \
      || { echo "  ✘ دفع الموقع فشل"; FAIL=1; }
  else
    echo "  لا تغييرات في الموقع — $(git log --oneline -1)"
  fi
else
  echo "  ! مجلد الموقع ليس مستودع git: $_S"
fi

# 4ب) ميزانية الصفحات — تُعلن في كل إغلاق حتى يُعرف الحد قبل أي تعديل نصي
if [ -n "$D" ] && [ -f "$_S/dist/reports/pdf/$D.pdf" ]; then
  say "4ب) ميزانية الصفحات — $D"
  python3 "$_B/tools/page_budget.py" --date "$D" 2>&1 | tail -4
fi

# 5) تحقق نهائي
say "5) الحصيلة"
echo "  النظام:  $(git -C "$_OUT" rev-parse --short HEAD 2>/dev/null || echo '-')"
echo "  الموقع:  $(git -C "$_S" rev-parse --short HEAD 2>/dev/null || echo '-')"
echo "  المكتبات في المستودع: $(git -C "$_OUT" ls-files brain/appendices/libraries 2>/dev/null | wc -l) ملفًا"
echo "  المهارات في المستودع: $(git -C "$_OUT" ls-files skills 2>/dev/null | wc -l) ملفًا"
UNPUSHED=$(git -C "$_OUT" log --oneline origin/main..HEAD 2>/dev/null | wc -l)
[ "$UNPUSHED" = "0" ] && echo "  ✔ لا التزامات محلية معلّقة" \
  || { echo "  ✘ $UNPUSHED التزامًا غير مدفوع"; FAIL=1; }
[ "$FAIL" = "0" ] && echo "  ✔ الإغلاق مكتمل" || echo "  ✘ الإغلاق ناقص"
exit "$FAIL"
