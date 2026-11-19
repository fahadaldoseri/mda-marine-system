#!/usr/bin/env bash
# تجهيز بيئة التشغيل السحابية قبل الخط اليومي — متساوي القوى (يُعاد بلا ضرر).
#
# العلّة المقيسة (تشغيل 2026-11-19): ضاعت قرابة ساعة قبل أول خطوة مفيدة في تجهيز الحاوية
# يدويًا من نص الأمر: مفاتيح أرضية الأصول (audit/asset-floor.json) مسارات مطلقة تحت
# /home/ubuntu، والمهارات تُقرأ من /home/ubuntu/skills، وG000C يحتاج bubblewrap وصلاحية
# قراءة /home/ubuntu، وG001 يحتاج site/dist قبل البناء اليومي (نحو 8 دقائق).
# هذه الأداة تنفّذ ذلك كله بأمر واحد مقيس، ولا تمسّ أي بوابة ولا أي ملف حاكم.
#
# الاستعمال (من أي دليل):  bash brain/tools/cloud_env_prep.sh [--no-site-check]
# المخرج: سطر لكل بند بحالته، ورمز 0 عند اكتمال التجهيز، و2 عند تعذّر بند لازم.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CANON=/home/ubuntu/mda-marine-system
SITE_CHECK=1
[ "${1:-}" = "--no-site-check" ] && SITE_CHECK=0
fail() { echo "✘ $*"; exit 2; }
T0=$(date +%s)

# 1) المسار القانوني: المستودع في /home/ubuntu/mda-marine-system ورابط رمزي من مكان الاستنساخ.
if [ "$HERE" != "$CANON" ]; then
  if [ -e "$CANON" ]; then
    fail "المسار القانوني مشغول بغير هذا المستودع: $CANON (لا يُكتب فوقه)"
  fi
  mkdir -p /home/ubuntu || fail "تعذّر إنشاء /home/ubuntu"
  ORIG="$HERE"
  mv "$ORIG" "$CANON" || fail "تعذّر نقل المستودع إلى $CANON"
  ln -s "$CANON" "$ORIG" || fail "تعذّر إنشاء الرابط $ORIG"
  echo "✔ نُقل المستودع إلى $CANON وبقي الرابط $ORIG"
else
  echo "✔ المستودع في المسار القانوني $CANON"
fi

# 2) المهارات في /home/ubuntu/skills من نسخة المستودع (مصدرها الوحيد في السحابة).
if [ -d "$CANON/skills" ]; then
  rm -rf /home/ubuntu/skills && cp -a "$CANON/skills" /home/ubuntu/skills \
    || fail "تعذّر نسخ المهارات إلى /home/ubuntu/skills"
  echo "✔ المهارات: $(find /home/ubuntu/skills -maxdepth 1 -mindepth 1 -type d | wc -l) مجلدًا"
else
  fail "لا مجلد مهارات في المستودع: $CANON/skills"
fi

# 3) شروط G000C: bubblewrap وصلاحية قراءة /home/ubuntu للمستخدم المعزول.
chmod o+rx /home/ubuntu || fail "تعذّر ضبط صلاحية /home/ubuntu"
if ! command -v bwrap >/dev/null 2>&1; then
  { apt-get install -y -q bubblewrap >/dev/null 2>&1 \
    || { apt-get update -q >/dev/null 2>&1 && apt-get install -y -q bubblewrap >/dev/null 2>&1; }; } \
    || fail "تعذّر تثبيت bubblewrap"
fi
echo "✔ bubblewrap: $(command -v bwrap)"

# 3ب) G011 يفحص خادم المعاينة على 3000 بـ`ss`، وحاوية السحابة بلا iproute2؛ فيُكتب «ممنوع التسليم»
# في سجله فيمنع gate_verdict إرسال تلغرام (D030) يوميًا. قيس في 19 نوفمبر 2026 على نسخة 19 نوفمبر.
if ! command -v ss >/dev/null 2>&1; then
  { apt-get install -y -q iproute2 >/dev/null 2>&1 \
    || { apt-get update -q >/dev/null 2>&1 && apt-get install -y -q iproute2 >/dev/null 2>&1; }; } \
    || fail "تعذّر تثبيت iproute2 (ss)"
fi
echo "✔ ss: $(command -v ss)"

# 4) حزم Python المثبّتة الإصدار في المستودع (لا تُعاد إن كانت مثبّتة).
if ! python3 - "$CANON/brain/requirements.txt" <<'PY' >/dev/null 2>&1
import sys, re
from importlib.metadata import version, PackageNotFoundError
for line in open(sys.argv[1], encoding="utf-8"):
    m = re.match(r"\s*([A-Za-z0-9_.-]+)==([^\s#]+)", line)
    if not m:
        continue
    try:
        if version(m.group(1)) != m.group(2):
            raise SystemExit(1)
    except PackageNotFoundError:
        raise SystemExit(1)
PY
then
  pip install -q -r "$CANON/brain/requirements.txt" >/dev/null 2>&1 || fail "تعذّر تثبيت requirements.txt"
fi
echo "✔ حزم Python مطابقة لـ requirements.txt"

# 5) site/dist لـ G001 في الخلفية فورًا، فيجري بالتوازي مع خطوات الجلب والكتابة.
if [ "$SITE_CHECK" = "1" ]; then
  LOG="$CANON/brain/logs/env-prep-site-check.log"
  mkdir -p "$(dirname "$LOG")"
  ( cd "$CANON/site" && BRAIN_DIR="$CANON/brain" SITE_DIR="$CANON/site" \
      nohup python3 generator/build_site.py --check >"$LOG" 2>&1; echo "rc=$?" >>"$LOG" ) >/dev/null 2>&1 &
  echo "✔ بناء site/dist لـ G001 بدأ في الخلفية (pid $!) · السجل: $LOG"
  echo "  انتظر سطر rc=0 في آخر السجل قبل G001."
fi
echo "✔ اكتمل التجهيز في $(( $(date +%s) - T0 )) ثانية"
