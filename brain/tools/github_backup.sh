#!/usr/bin/env bash
# نسخة احتياطية للبيانات على GitHub — مركز الوعي بالمجال البحري.
# الشيفرة والقواعد مصدرها GitHub (قرار المالك 2026-10-24): قبل النسخ تُجلب أحدث main وتُطبَّق على الخادم (apply_from_github)،
# ثم تُبنى الشجرة فتُنسخ البيانات فقط ولا تُكتب الشيفرة فوق المستودع. غير مُعطِّل للخط اليومي: فشله يُسجَّل ولا يوقف التسليم.
set -u
# حاجز واجهة مُبكر: هذا السكربت لا يقبل معاملات؛ رفض --help وأي معامل مجهول
# يسبق تهيئة المسارات وفتح السجل حتى لا يشغّل النسخة الاحتياطية عرضًا.
if [ "$#" -ne 0 ]; then
  echo "✘ معامل غير معروف: $1 — لا يدعم github_backup.sh معاملات (بما فيها --help)" >&2
  echo "الاستخدام: bash tools/github_backup.sh" >&2
  exit 2
fi
B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REPO="${BACKUP_REPO_DIR:-$(dirname "$B")/mda-marine-system}"
# حماية: لو تسرّب جذر المرآة في BRAIN_DIR لظهر جذر مكرر مثل .../mda-marine-system/mda-marine-system
case "$REPO" in
  */mda-marine-system/mda-marine-system) REPO="${REPO%/mda-marine-system}" ;;
esac
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
  # 2.5) بوابة الأسرار (ك-162 — طلب فهد 2026-10-24): لا سرّ في الشجرة ولا في الالتزام القادم.
  # سببها: رمز بوت تلغرام دخل brain/secrets/secrets.env في تاريخ المستودع. لا يتكرر.
  python3 "$B/validators/check_secrets.py" --root "$REPO" || { echo "✘ بوابة الأسرار: مُنع النسخ الاحتياطي والدفع"; exit 70; }
  # 2.6) فحص مكمّل (البند 6): لا ملف شيفرة على الخادم خارج المستودع — منع.
  python3 "$B/validators/check_server_code_tracking.py" --root "$B" --repo "$REPO" || { echo "✘ ملفات شيفرة غير متتبَّعة على الخادم: مُنع النسخ الاحتياطي والدفع"; exit 70; }
  # 2.7) حماية ملف الأسرار المعتمد: لا يُحذف ولا يُفرَّغ بالنسخ الاحتياطي (ك-168 — حذفه الالتزام eac53cd).
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
    # هوية خادم منفصلة + سطر تفويض صريح (طلب فهد 2026-10-24، البند 19).
    git -c user.name="MDA Backup" -c user.email="mda-backup@localhost" commit -q \
      -m "نسخة احتياطية $(date -u +%F) — تحديث البيانات" \
      -m "هوية الخادم: MDA Backup · دُمج بتفويض فهد الدوسري (تفويض 2026-10-24)."
    # الدفع المباشر إلى main مقصود ومعتمد في المانيفست بقرار المالك: أداة
    # التماثل تقارن بفرع main، لذلك تغييره يتطلب تغيير الأداة لا تجاوز العقد.
    if ! git push -q origin main 2>/dev/null; then   # تقدّم origin بين الجلب والدفع (دمج PR مثلًا): إعادة تأسيس ثم دفع
      git pull -q --rebase origin main && git push -q origin main
    fi && echo "تم الدفع: $(git rev-parse --short HEAD)" || echo "✘ فشل الدفع"
  fi
  echo "=== انتهى: $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
tail -3 "$LOG"
