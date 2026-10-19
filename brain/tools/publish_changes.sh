#!/usr/bin/env bash
# إغلاق أي جلسة تطوير: يدفع كل تغييرات النظام إلى المستودع الخاص، ثم يحفظ تغييرات الموقع.
# الاستخدام:  bash tools/publish_changes.sh ["رسالة الالتزام"]
# السبب: قاعدة «مصدر واحد للحقيقة» — لا يبقى تعديل محليًا بلا نسخة على GitHub.
set -u
_B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
_S="${SITE_DIR:-$(dirname "$_B")/seawatch}"
MSG="${1:-تحديث النظام $(date -u +%F)}"
FAIL=0

echo "١) النسخة الاحتياطية للنظام → المستودع الخاص"
bash "$_B/tools/github_backup.sh" || FAIL=1

echo
echo "٢) تغييرات الموقع → مستودع الموقع"
if [ -d "$_S/.git" ]; then
  cd "$_S"
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -q -m "$MSG" || true
    git pull --rebase -q origin main 2>/dev/null || true
    git push -q origin main && echo "  ✔ الموقع مدفوع: $(git log --oneline -1)" || { echo "  ✘ دفع الموقع فشل"; FAIL=1; }
  else
    echo "  لا تغييرات في الموقع — $(git log --oneline -1)"
  fi
else
  echo "  ! مجلد الموقع ليس مستودع git: $_S"
fi

echo
echo "٣) الحصيلة"
echo "  النظام:  $(git -C "$_B" rev-parse --short HEAD 2>/dev/null || echo '-')  (المستودع الخاص)"
echo "  الموقع:  $(git -C "$_S" rev-parse --short HEAD 2>/dev/null || echo '-')"
exit $FAIL