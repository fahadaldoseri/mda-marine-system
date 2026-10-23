#!/usr/bin/env bash
# نسخة احتياطية للبيانات على GitHub — مركز الوعي بالمجال البحري.
# الشيفرة والقواعد مصدرها GitHub (قرار المالك 2026-10-24): قبل النسخ تُجلب أحدث main وتُطبَّق على الخادم (apply_from_github)،
# ثم تُبنى الشجرة فتُنسخ البيانات فقط ولا تُكتب الشيفرة فوق المستودع. غير مُعطِّل للخط اليومي: فشله يُسجَّل ولا يوقف التسليم.
set -u
B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REPO="${BACKUP_REPO_DIR:-$(dirname "$B")/mda-marine-system}"
LOG="$B/logs/github-backup-$(date -u +%F).log"
mkdir -p "$B/logs"
{
  echo "=== بدء النسخ الاحتياطي: $(date -u +%FT%TZ) ==="
  cd "$REPO" || exit 1
  # 1) أحدث main من GitHub (تقدّم سريع فقط) ثم تطبيق الشيفرة على الخادم
  if git fetch -q origin main 2>/dev/null; then
    git checkout -q main 2>/dev/null
    if [ -z "$(git status --porcelain | head -1)" ]; then
      git merge -q --ff-only origin/main || { echo "✘ main المحلي تباعد عن origin/main — أوقف النسخ"; exit 1; }
      python3 "$B/tools/apply_from_github.py" --repo "$REPO" --brain "$B" || echo "⚠ تعذّر/تعارض في تطبيق الشيفرة (رمز $?) — انظر أعلاه؛ تستمر النسخة للبيانات"
    else
      echo "⚠ شجرة المستودع فيها تعديل غير مدفوع — لا جلب ولا تطبيق في هذه الجولة"
    fi
  else
    echo "⚠ تعذّر الجلب من origin — تُنسخ البيانات فقط"
  fi
  # 2) بناء الشجرة: بيانات فقط (الشيفرة تبقى كما في GitHub)
  python3 "$B/tools/github_backup.py" || { echo "فشل بناء الشجرة"; exit 1; }
  git add -A
  if git diff --cached --quiet; then
    echo "لا تغيير منذ آخر نسخة"
  else
    git commit -q -m "نسخة احتياطية $(date -u +%F) — تحديث البيانات"
    if ! git push -q origin main 2>/dev/null; then   # تقدّم origin بين الجلب والدفع (دمج PR مثلًا): إعادة تأسيس ثم دفع
      git pull -q --rebase origin main && git push -q origin main
    fi && echo "تم الدفع: $(git rev-parse --short HEAD)" || echo "✘ فشل الدفع"
  fi
  echo "=== انتهى: $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
tail -3 "$LOG"
