#!/usr/bin/env bash
# خط التشغيل الصباحي الموحّد — الإصدار 2 (اعتُمد 13 أكتوبر 2026 بعد حادثة توقف التقرير)
# السبب: الإصدار 1 كان يُستدعى بـpython3 (SyntaxError)، ويقرأ مدخلات من /tmp غير دائمة،
# ويُخفي كل الأخطاء بـ2>/dev/null بلا رمز خروج ولا سجل — أي فشل صامت لا يُكتشف.
# الاستخدام: bash tools/daily_pipeline.sh [UTC_DATE] [OFAC_TARGETS_FILE] [ORIGINALS_URLS_FILE]
set -uo pipefail
B=/home/ubuntu/brain-marine-news
cd "$B" || exit 2
D="${1:-$(date -u +%F)}"
TARGETS="${2:-$B/watchlist/ofac-targets.txt}"
URLS="${3:-$B/watchlist/original-sources.txt}"
LOGDIR="$B/logs"; mkdir -p "$LOGDIR"
LOG="$LOGDIR/pipeline-$D.log"
MARK="$LOGDIR/pipeline-$D.json"

echo "===== خط التشغيل الموحّد v2 — $D — $(date -u +%FT%TZ) =====" | tee -a "$LOG"

S_FEEDS="failed"; S_OFAC="failed"; S_ARCH="failed"; NOTE_OFAC=""; NOTE_ARCH=""

# 1) التغذيات — إنذار مبكر من 38 تغذية
echo "-- 1) التغذيات (38 تغذية) --" | tee -a "$LOG"
if python3 tools/check_feeds.py >>"$LOG" 2>&1; then
  if [ -f "feeds/feeds-$D.md" ]; then
    S_FEEDS="ok"; echo "   ✔ مستجدات التغذيات: feeds/feeds-$D.md" | tee -a "$LOG"
  else
    echo "   ✘ لم يُنتج ملف التغذيات" | tee -a "$LOG"
  fi
else
  echo "   ✘ فشل فاحص التغذيات" | tee -a "$LOG"
fi

# 2) فحص OFAC — لكل سفينة أو وسيط مرشح للذكر
echo "-- 2) فحص OFAC --" | tee -a "$LOG"
if [ ! -f "$TARGETS" ]; then
  echo "   ✘ قائمة المستهدفات مفقودة: $TARGETS (خطأ إعداد — لا يُعتبر نجاحًا)" | tee -a "$LOG"
  NOTE_OFAC="قائمة المستهدفات مفقودة"
elif [ ! -s "$TARGETS" ]; then
  S_OFAC="ok"; NOTE_OFAC="لا مستهدف في نافذة اليوم — لا فحص مطلوب"
  echo "   ○ $NOTE_OFAC" | tee -a "$LOG"
else
  if python3 tools/ofac_screen.py "$TARGETS" >>"$LOG" 2>&1; then
    S_OFAC="ok"; NOTE_OFAC="فُحص $(grep -cve '^[[:space:]]*$' "$TARGETS") مستهدفًا"
    echo "   ✔ $NOTE_OFAC" | tee -a "$LOG"
  else
    echo "   ✘ فشل فحص OFAC" | tee -a "$LOG"
  fi
fi

# 3) حفظ الأصول الرسمية — HTML/PDF + وقت UTC + بصمة sha256
echo "-- 3) حفظ الأصول الرسمية --" | tee -a "$LOG"
if [ ! -f "$URLS" ]; then
  echo "   ✘ قائمة روابط الأصول مفقودة: $URLS (خطأ إعداد — لا يُعتبر نجاحًا)" | tee -a "$LOG"
  NOTE_ARCH="قائمة الأصول مفقودة"
elif [ ! -s "$URLS" ]; then
  S_ARCH="ok"; NOTE_ARCH="لا بلاغ رسمي في نافذة اليوم — لا أصل مطلوب"
  echo "   ○ $NOTE_ARCH" | tee -a "$LOG"
else
  if python3 tools/archive_originals.py "$D" "$URLS" >>"$LOG" 2>&1; then
    S_ARCH="ok"; NOTE_ARCH="حُفظت الأصول في archive/originals/$D/"
    echo "   ✔ $NOTE_ARCH" | tee -a "$LOG"
  else
    echo "   ✘ فشل حفظ الأصول الرسمية" | tee -a "$LOG"
  fi
fi

# علامة نجاح قابلة للفحص آليًا (بوابة التسليم تقرأها)
if [ -f "archive/originals/$D/manifest.json" ]; then MANIFEST="archive/originals/$D/manifest.json"; else MANIFEST=""; fi
python3 - "$MARK" "$D" "$S_FEEDS" "$S_OFAC" "$S_ARCH" "$NOTE_OFAC" "$NOTE_ARCH" "$MANIFEST" <<'PY'
import json, sys, datetime
mark, d, f, o, a, no, na, man = sys.argv[1:9]
ok = all(s == "ok" for s in (f, o, a))
json.dump({
    "date": d, "pipeline_version": 2,
    "finished_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "overall": "ok" if ok else "failed",
    "feeds": {"status": f}, "ofac": {"status": o, "note": no},
    "originals": {"status": a, "note": na, "manifest": man},
}, open(mark, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"-- الخلاصة: تغذيات={f} · OFAC={o} · أصول={a} · العلامة: {mark}")
sys.exit(0 if ok else 1)
PY
RC=$?
echo "===== نهاية الخط (رمز الخروج: $RC) =====" | tee -a "$LOG"
exit $RC
