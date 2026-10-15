#!/usr/bin/env bash
# خط التشغيل الصباحي الموحّد — الإصدار 3 (13 أكتوبر 2026)
# v1: أمره كان يُستدعى بـpython3 (SyntaxError) + مدخلات /tmp + فشل صامت.
# v2: سجل + رمز خروج + علامة نجاح + قوائم دائمة في watchlist/.
# v3: أُضيفت خطوة دمج الذاكرة التراكمية (ملف اليوم → الدفتر الجامع + خريطة الرموز)،
#     لأن ملف اليوم كان يُكتب ولا يُدمج أبدًا فتنقطع الذاكرة التراكمية.
# الاستخدام: bash tools/daily_pipeline.sh [UTC_DATE] [OFAC_TARGETS_FILE] [ORIGINALS_URLS_FILE]
set -uo pipefail
B=/home/ubuntu/brain-marine-news
SITE=/home/ubuntu/seawatch
cd "$B" || exit 2
D="${1:-$(date -u +%F)}"
TARGETS="${2:-$B/watchlist/ofac-targets.txt}"
URLS="${3:-$B/watchlist/original-sources.txt}"
LOGDIR="$B/logs"; mkdir -p "$LOGDIR"
LOG="$LOGDIR/pipeline-$D.log"
MARK="$LOGDIR/pipeline-$D.json"

echo "===== خط التشغيل الموحّد v3 — $D — $(date -u +%FT%TZ) =====" | tee -a "$LOG"

S_FEEDS="failed"; S_OFAC="failed"; S_ARCH="failed"; S_LEDGER="failed"
NOTE_OFAC=""; NOTE_ARCH=""; NOTE_LEDGER=""

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

# 4) دمج الذاكرة التراكمية: ملف اليوم → الدفتر الجامع + خريطة الرموز
echo "-- 4) دمج الذاكرة التراكمية --" | tee -a "$LOG"
if python3 tools/merge_ledger_daily.py >>"$LOG" 2>&1; then
  cp -f cumulative-2026/event-ledger-master.json "$SITE/sources/ledger.json" 2>>"$LOG"
  S_LEDGER="ok"; NOTE_LEDGER="دُمج ملف اليوم في الدفتر الجامع وبُنيت خريطة الرموز ونُسخ الدفتر إلى الموقع"
  echo "   ✔ $NOTE_LEDGER" | tee -a "$LOG"
else
  echo "   ✘ فشل دمج الدفتر التراكمي" | tee -a "$LOG"
fi

# 5) خطوات النموذج المدمج (اختيارية — تُتخطى بصمت إن غاب المشغّل، بلا مفاتيح خارجية)
echo "-- 5) النموذج المدمج: ترشيح التغذيات + مراجعة لغوية --" | tee -a "$LOG"
S_LLM="skip"; NOTE_LLM="لم تُشغَّل (لا مشغّل متاح)"
FEEDS_MD="feeds/feeds-$D.md"; REPORT_MD="reports/$D-sectioned.md"
if command -v manus-node >/dev/null 2>&1; then
  S_LLM="ok"; NOTE_LLM=""
  if [ -f "$FEEDS_MD" ]; then
    if ! python3 tools/llm_triage.py --input "$FEEDS_MD" >>"$LOG" 2>&1; then
      S_LLM="failed"; NOTE_LLM="فشل ترشيح التغذيات"
    fi
  fi
  if [ -f "$REPORT_MD" ]; then
    if ! python3 tools/llm_review.py --report "$REPORT_MD" --limit 25 >>"$LOG" 2>&1; then
      S_LLM="failed"; NOTE_LLM="${NOTE_LLM:+$NOTE_LLM · }فشل المراجعة اللغوية"
    fi
  fi
  [ "$S_LLM" = "ok" ] && NOTE_LLM="رُشّحت التغذيات ورُوجعت اللغة آلياً بالنموذج المدمج"
  echo "   ✔ $NOTE_LLM" | tee -a "$LOG"
else
  echo "   · تخطٍّ: manus-node غير متاح في هذه البيئة" | tee -a "$LOG"
fi

if [ -f "archive/originals/$D/manifest.json" ]; then MANIFEST="archive/originals/$D/manifest.json"; else MANIFEST=""; fi
python3 - "$MARK" "$D" "$S_FEEDS" "$S_OFAC" "$S_ARCH" "$S_LEDGER" "$NOTE_OFAC" "$NOTE_ARCH" "$NOTE_LEDGER" "$MANIFEST" "$S_LLM" "$NOTE_LLM" <<'PY'
import json, sys, datetime
mark, d, f, o, a, l, no, na, nl, man, sl, nlm = sys.argv[1:12]
ok = all(s == "ok" for s in (f, o, a, l)) and sl != "failed"
json.dump({
    "date": d, "pipeline_version": 3,
    "finished_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "overall": "ok" if ok else "failed",
    "feeds": {"status": f}, "ofac": {"status": o, "note": no},
    "originals": {"status": a, "note": na, "manifest": man},
    "ledger_merge": {"status": l, "note": nl},
    "builtin_llm": {"status": sl, "note": nlm},
}, open(mark, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"-- الخلاصة: تغذيات={f} · OFAC={o} · أصول={a} · دمج الذاكرة={l} · النموذج المدمج={sl} · العلامة: {mark}")
sys.exit(0 if ok else 1)
PY
RC=$?
echo "===== نهاية الخط (رمز الخروج: $RC) =====" | tee -a "$LOG"
exit $RC