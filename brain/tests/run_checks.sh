#!/usr/bin/env bash
# اختبارات البوابات — تُشغَّل بعد كل إصلاح: bash tests/run_checks.sh
# الغرض: إثبات أن سلوك البوابة في الحالات الحرجة صحيح، لا مجرد قراءة الشيفرة.
set -uo pipefail
B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); printf '  ✔ %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  ✘ %s\n' "$1"; }
check(){ [ "$1" = "$2" ] && ok "$3 (=$1)" || bad "$3 — المتوقع $2 والواقع $1"; }

echo "===== اختبارات بوابات النظام — $(date -u +%FT%TZ) ====="

# ── 1) سلوك دالة step في بوابة التسليم: انهيار ≠ تحذير (ك-131) ──────────────
echo "1) دالة step: تصنيف رموز الخروج"
# نستخرج دالة step الحقيقية من البوابة لنختبر الشيفرة الفعلية لا نسخة منها.
awk '/^step\(\) \{/,/^\}/' "$B/tools/final_gate.sh" > "$TMP/step.sh"
if [ ! -s "$TMP/step.sh" ]; then
  bad "تعذّر استخراج دالة step من tools/final_gate.sh"
else
  run_case() {  # run_case <اسم> <أمر الاختبار>
    local name="$1"; shift
    LOGDIR="$TMP/log-$name"; mkdir -p "$LOGDIR"; REP="$LOGDIR/report.txt"; : > "$REP"; N=0; WORST=0
    ( set -uo pipefail; source "$TMP/step.sh"; step "فحص تجريبي" 2 "$@" ) >/dev/null 2>&1
    local st
    # اسم الفحص قد يحوي مسافات، فتُقرأ الحالة من مجموعة الحالات المعروفة (كما يفعل البوابة)
    st=$(awk '{for(i=1;i<=NF;i++) if($i=="ok"||$i=="warn"||$i=="block"||$i=="crash"){print $i; exit}}' "$REP" | head -1)
    printf '%s' "$st"
  }
  s=$(run_case crash python3 -c "1/0")
  check "$s" "crash" "انهيار بايثون (ZeroDivisionError) يُصنّف انهيارًا لا تحذيرًا"
  s=$(run_case warn python3 -c "import sys; print('تحذير مقصود'); sys.exit(1)")
  check "$s" "warn" "رمز 1 بلا أثر انهيار يبقى تحذيرًا"
  s=$(run_case block python3 -c "import sys; print('مخالفة'); sys.exit(2)")
  check "$s" "block" "رمز المانع 2 يُصنّف منعًا"
  s=$(run_case clean python3 -c "print('مطابق')")
  check "$s" "ok" "رمز 0 يُصنّف نجاحًا"
fi

# ── 2) فحص العنوان اليتيم في فاحص شكل PDF يعمل فعلًا (ك-130 · البند ح-2) ────
echo "2) فاحص شكل PDF: فحص العنوان اليتيم"
if grep -qE "^\s*problems\.append" "$B/validators/check_pdf_format.py"; then
  bad "ما زال يستدعي problems غير المعرّف (NameError مُبتلع)"
else
  ok "لا استدعاء لمتغير غير معرّف في فحص العنوان اليتيم"
fi
PDF="$B/../seawatch/dist/reports/pdf/$(date -u +%F).pdf"
if [ -f "$PDF" ]; then
  OUT=$(python3 "$B/validators/check_pdf_format.py" --pdf "$PDF" 2>&1)
  if printf '%s' "$OUT" | grep -qE "(لا عنوان قسم أو بطاقة يتيم|عنوان يتيم آخر ورقة)"; then
    ok "الفحص نفّذ حكمًا فعليًا على ملف حقيقي (لا ابتلاع استثناء)"
  else
    bad "الفحص لم يُصدر حكمًا على العنوان اليتيم: $(printf '%s' "$OUT" | grep -E 'تعذّر|Error' | head -1)"
  fi
else
  printf '  • تخطٍّ: لا ملف PDF لليوم (%s) — يُختبر عند أول إصدار\n' "$(date -u +%F)"
fi

# ── 3) عقد رموز الخروج موثَّق في البوابة ─────────────────────────────────────
echo "3) عقد رموز الخروج"
if grep -q "انهيار المدقق ليس تحذيرًا" "$B/tools/final_gate.sh"; then
  ok "قاعدة الانهيار مكتوبة في البوابة (قابلة للتتبع)"
else
  bad "قاعدة الانهيار غير موجودة في البوابة"
fi

echo "4) صياغة سكربتات الشل وكتلها المضمّنة (ك-132: خلاصة البوابة انهارت بإزاحة خطأ)"
sh_bad=0; py_bad=0
for f in "$B"/tools/*.sh; do
  [ -f "$f" ] || continue
  # لا يُفحص هذا الملف نفسه: يحتوي نمط الاستخراج حرفيًا فيتطابق مع نفسه.
  [ "$(basename "$f")" = "run_checks.sh" ] && continue
  bash -n "$f" 2>/dev/null || { sh_bad=$((sh_bad+1)); printf '  ✘ صياغة شل: %s\n' "$(basename "$f")"; }
  awk "/<<'PY'/{f=1;next} /^PY\$/{f=0} f" "$f" > "$TMP/inline.py" 2>/dev/null
  if [ -s "$TMP/inline.py" ]; then
    python3 -c "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$TMP/inline.py" 2>/dev/null \
      || { py_bad=$((py_bad+1)); printf '  ✘ كتلة بايثون مضمّنة: %s\n' "$(basename "$f")"; }
  fi
done
check "$sh_bad" "0" "صياغة كل سكربتات الشل سليمة"
check "$py_bad" "0" "كل كتل بايثون المضمّنة في السكربتات سليمة الصياغة"

echo "----- الحصيلة -----"
printf '  نجح: %s · فشل: %s\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
