#!/usr/bin/env bash
# نسخة احتياطية للبيانات على GitHub — مركز الوعي بالمجال البحري.
# المصدر: GitHub/main للشيفرة؛ التغيير الناتج يمر دائمًا عبر فرع وطلب دمج.
set -u

# حاجز واجهة مبكر: لا معاملات حتى لا تُشغَّل النسخة عرضًا.
if [ "$#" -ne 0 ]; then
  echo "✘ معامل غير معروف: $1 — لا يدعم github_backup.sh معاملات (بما فيها --help)" >&2
  echo "الاستخدام: bash tools/github_backup.sh" >&2
  exit 2
fi

B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REPO="${BACKUP_REPO_DIR:-$(dirname "$B")/mda-marine-system}"
case "$REPO" in
  */mda-marine-system/mda-marine-system) REPO="${REPO%/mda-marine-system}" ;;
esac
SITE_ROOT="${SITE_DIR:-${SITE:-$B/../seawatch}}"
LOG="$B/logs/github-backup-$(date -u +%F).log"
WORKTREE=""
mkdir -p "$B/logs"
exec 3>&2

cleanup_worktree() {
  if [ -n "${WORKTREE:-}" ] && [ -d "$WORKTREE" ]; then
    git -C "$REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
}

print_backup_log_on_exit() {
  rc=$?
  trap - EXIT
  cleanup_worktree
  if [ -f "$LOG" ]; then
    tail -3 "$LOG" >&3 || true
  else
    echo "✘ فشل مغلق: لم يُنشأ سجل النسخة الاحتياطية: $LOG" >&3
  fi
  exec 3>&-
  exit "$rc"
}
trap print_backup_log_on_exit EXIT

{
  abort() {
    echo "✘ فشل مغلق: $*"
    exit 2
  }

  echo "=== بدء النسخ الاحتياطي: $(date -u +%FT%TZ) ==="
  cd "$REPO" || abort "تعذر دخول مستودع النسخة: $REPO"

  # سجلات التشغيل المعلنة محلية ولا تمنع النسخ؛ الشيفرة/البيانات الحقيقية تمنع مغلقًا.
  python3 "$B/validators/check_backup_tree_clean.py" --repo "$REPO" --brain "$B" \
    || abort "حارس شجرة النسخ منع العملية؛ راجع تصنيف المسارات وبصمات SHA-256"

  # اعزل النسخة عن شجرة التشغيل: لا تبديل فرع ولا إسقاط لسجلات الجولة المحلية.
  git fetch -q origin main || abort "تعذر جلب origin/main؛ لم يُنشأ التزام أو دفع"
  WORKTREE="$(mktemp -d "${TMPDIR:-/tmp}/mda-backup-worktree.XXXXXX")" \
    || abort "تعذر إنشاء مجلد worktree مؤقت"
  rmdir "$WORKTREE" || abort "تعذر تجهيز مسار worktree المؤقت"
  git worktree add -q --detach "$WORKTREE" origin/main \
    || abort "تعذر إنشاء worktree من origin/main؛ لم يُنشأ فرع أو دفع"

  # طبّق المصدر الملتزم على الخادم ثم ابنِ البيانات داخل worktree، لا داخل شجرة التشغيل.
  python3 "$B/tools/apply_from_github.py" --repo "$WORKTREE" --brain "$B" \
    || echo "⚠ تعذّر/تعارض في تطبيق الشيفرة (تستمر نسخة البيانات بعد تسجيل التحذير)"
  BRAIN_DIR="$B" SITE_DIR="$SITE_ROOT" BACKUP_REPO_DIR="$WORKTREE" \
    python3 "$B/tools/github_backup.py" \
    || abort "فشل بناء الشجرة"
  python3 "$B/validators/check_secrets.py" --root "$WORKTREE" \
    || { echo "✘ بوابة الأسرار: مُنع النسخ الاحتياطي والدفع"; exit 70; }
  python3 "$B/validators/check_server_code_tracking.py" --root "$B" --repo "$WORKTREE" \
    || { echo "✘ ملفات شيفرة غير متتبَّعة على الخادم: مُنع النسخ الاحتياطي والدفع"; exit 70; }

  # حماية ملف الأسرار المعتمد من الحذف أو التفريغ.
  PROT="$WORKTREE/brain/secrets/secrets.env"
  if [ ! -s "$PROT" ]; then
    if git -C "$WORKTREE" show HEAD:brain/secrets/secrets.env > "$PROT" 2>/dev/null; then
      echo "  ↺ أُعيد ملف الأسرار المعتمد من المستودع (لا يُحذف بالنسخ)"
    fi
  fi

  git -C "$WORKTREE" add -A
  if git -C "$WORKTREE" diff --cached --quiet; then
    echo "لا تغيير منذ آخر نسخة"
  else
    # أنشئ فرعًا فريدًا قبل الالتزام؛ لا يُسمح بتغيير main مباشرة.
    BACKUP_BRANCH="backup/$(date -u +%F-%H%M%S)-$$"
    case "$BACKUP_BRANCH" in
      main|refs/heads/main|*/main) abort "اسم الفرع المحسوب محظور: $BACKUP_BRANCH" ;;
    esac
    git -C "$WORKTREE" show-ref --verify --quiet "refs/heads/$BACKUP_BRANCH" \
      && abort "فرع النسخ موجود محليًا: $BACKUP_BRANCH"
    git -C "$WORKTREE" switch -q -c "$BACKUP_BRANCH" \
      || abort "تعذر إنشاء فرع النسخ: $BACKUP_BRANCH"
    git -C "$WORKTREE" -c user.name="MDA Backup" -c user.email="mda-backup@localhost" commit -q \
      -m "نسخة احتياطية $(date -u +%F) — تحديث البيانات" \
      -m "هوية الخادم: MDA Backup · يُدمج عبر طلب دمج لا عبر دفع مباشر."

    # الحاجز الساكن يوقف أي صيغة دفع تستهدف main قبل لمس الشبكة.
    python3 "$B/validators/check_backup_push_safety.py" \
      --script "$B/tools/github_backup.sh" \
      || abort "حاجز الدفع المباشر منع العملية"
    command -v gh >/dev/null 2>&1 \
      || abort "gh غير متاح؛ لا يمكن إنشاء طلب دمج تلقائيًا"

    git -C "$WORKTREE" push -q -u origin "$BACKUP_BRANCH" \
      || abort "تعذر دفع فرع النسخ؛ لم يُدفع main"
    git -C "$WORKTREE" ls-remote --exit-code --heads origin "$BACKUP_BRANCH" >/dev/null 2>&1 \
      || abort "لم تثبت مرجعية فرع النسخ على origin"

    PR_URL=""
    if ! PR_URL="$(cd "$WORKTREE" && gh pr create --base main --head "$BACKUP_BRANCH" \
      --title "نسخة احتياطية $(date -u +%F)" \
      --body "نسخة بيانات آلية من github_backup.sh. تُراجع وتُدمج عبر طلب دمج؛ لا دفع مباشر إلى main." 2>&1)"; then
      echo "$PR_URL"
      abort "تعذر إنشاء طلب الدمج للفرع $BACKUP_BRANCH"
    fi
    echo "تم دفع الفرع فقط: $BACKUP_BRANCH"
    echo "تم إنشاء طلب الدمج: $PR_URL"
  fi
  echo "=== انتهى: $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
