#!/usr/bin/env bash
# نسخة احتياطية كاملة على GitHub — مركز الوعي بالمجال البحري
# يبني الشجرة النظيفة (brain + site) ثم يدفعها إلى المستودع الخاص.
# غير مُعطِّل للخط اليومي: فشله يُسجَّل ولا يوقف التسليم.
set -u
B="/home/ubuntu/brain-marine-news"
REPO="/home/ubuntu/mda-marine-system"
LOG="$B/logs/github-backup-$(date -u +%F).log"
mkdir -p "$B/logs"
{
  echo "=== بدء النسخ الاحتياطي: $(date -u +%FT%TZ) ==="
  python3 "$B/tools/github_backup.py" || { echo "فشل بناء الشجرة"; exit 1; }
  cd "$REPO" || exit 1
  git add -A
  if git diff --cached --quiet; then
    echo "لا تغيير منذ آخر نسخة"
  else
    git commit -q -m "نسخة احتياطية $(date -u +%F) — تحديث النظام والبيانات"
    git push -q origin main && echo "تم الدفع: $(git rev-parse --short HEAD)"
  fi
  echo "=== انتهى: $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
tail -3 "$LOG"
