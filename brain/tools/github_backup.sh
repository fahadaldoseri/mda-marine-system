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
LOG="$B/logs/github-backup-$(date -u +%F).log"
mkdir -p "$B/logs"
exec 3>&2

print_backup_log_on_exit() {
  rc=$?
  trap - EXIT
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

  # يلزم خط أساس حديث ونظيف من main قبل بناء أي التزام احتياطي.
  git fetch -q origin main || abort "تعذر جلب origin/main؛ لم يُنشأ التزام أو دفع"
  [ -z "$(git status --porcelain)" ] || abort "شجرة المستودع غير نظيفة؛ لم يُنشأ فرع أو دفع"
  git checkout -q main || abort "تعذر الانتقال إلى main؛ لم يُنشأ فرع أو دفع"
  git merge -q --ff-only origin/main || abort "main المحلي تباعد عن origin/main؛ أوقف النسخ"
  python3 "$B/tools/apply_from_github.py" --repo "$REPO" --brain "$B" \
    || echo "⚠ تعذّر/تعارض في تطبيق الشيفرة (تستمر نسخة البيانات بعد تسجيل التحذير)"

  # بناء الشجرة: بيانات فقط؛ الشيفرة تبقى كما في GitHub.
  python3 "$B/tools/github_backup.py" || abort "فشل بناء الشجرة"
  python3 "$B/validators/check_secrets.py" --root "$REPO" \
    || { echo "✘ بوابة الأسرار: مُنع النسخ الاحتياطي والدفع"; exit 70; }
  python3 "$B/validators/check_server_code_tracking.py" --root "$B" --repo "$REPO" \
    || { echo "✘ ملفات شيفرة غير متتبَّعة على الخادم: مُنع النسخ الاحتياطي والدفع"; exit 70; }

  # حماية ملف الأسرار المعتمد من الحذف أو التفريغ.
  PROT="$REPO/brain/secrets/secrets.env"
  if [ ! -s "$PROT" ]; then
    if git -C "$REPO" show HEAD:brain/secrets/secrets.env > "$PROT" 2>/dev/null; then
      echo "  ↺ أُعيد ملف الأسرار المعتمد من المستودع (لا يُحذف بالنسخ)"
    fi
  fi

  git add -A
  if git diff --cached --quiet; then
    echo "لا تغيير منذ آخر نسخة"
  else
    # أنشئ فرعًا فريدًا قبل الالتزام؛ لا يُسمح بتغيير main مباشرة.
    BACKUP_BRANCH="backup/$(date -u +%F-%H%M%S)-$$"
    case "$BACKUP_BRANCH" in
      main|refs/heads/main|*/main) abort "اسم الفرع المحسوب محظور: $BACKUP_BRANCH" ;;
    esac
    git show-ref --verify --quiet "refs/heads/$BACKUP_BRANCH" \
      && abort "فرع النسخ موجود محليًا: $BACKUP_BRANCH"
    git switch -q -c "$BACKUP_BRANCH" || abort "تعذر إنشاء فرع النسخ: $BACKUP_BRANCH"
    git -c user.name="MDA Backup" -c user.email="mda-backup@localhost" commit -q \
      -m "نسخة احتياطية $(date -u +%F) — تحديث البيانات" \
      -m "هوية الخادم: MDA Backup · يُدمج عبر طلب دمج لا عبر دفع مباشر."

    # الحاجز الساكن يوقف أي صيغة دفع تستهدف main قبل لمس الشبكة.
    python3 "$B/validators/check_backup_push_safety.py" \
      --script "$B/tools/github_backup.sh" \
      || abort "حاجز الدفع المباشر منع العملية"
    command -v gh >/dev/null 2>&1 \
      || abort "gh غير متاح؛ لا يمكن إنشاء طلب دمج تلقائيًا"

    git push -q -u origin "$BACKUP_BRANCH" \
      || abort "تعذر دفع فرع النسخ؛ لم يُدفع main"
    git ls-remote --exit-code --heads origin "$BACKUP_BRANCH" >/dev/null 2>&1 \
      || abort "لم تثبت مرجعية فرع النسخ على origin"

    PR_URL=""
    if ! PR_URL="$(gh pr create --base main --head "$BACKUP_BRANCH" \
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
