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

# ك-247: فحوص الأسطح تحتاج صفحة مبنية. قبل البناء تُقاس على أحدث إصدار مبني،
# ويبقى إنفاذ اليوم فشلًا مغلقًا في بوابات ما بعد البناء (G045 · G046 · G047).
# ك-598 · خ-09: اشتقاق جذر الموقع مصدره واحد: tools/site_root.sh — بشرط وجود dist،
# وإلا فشل مغلق برسالة صريحة (لا مسار مُخمَّن بلا dist يخفي عيبًا).
. "$B/tools/site_root.sh"
if ! site_root_resolve "$B"; then
  site_root_message
  exit 2
fi
export SITE_DIR="$SITE"
BUILT_HTML="$(ls -1 "$SITE"/dist/reports/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].html 2>/dev/null | sort | tail -1)"
if [ -n "$BUILT_HTML" ]; then
  SURFACE_DATE="$(basename "$BUILT_HTML" .html)"
  [ "$SURFACE_DATE" = "$(date -u +%F)" ] || echo "  ملاحظة: لم تُبنَ صفحة اليوم بعد — فحوص الأسطح تُقاس على $SURFACE_DATE، وإنفاذ اليوم في بوابات ما بعد البناء"
else
  SURFACE_DATE="$(date -u +%F)"
fi

# ك-315: بوابتا اللغة الحيّة وتماثل النسخة الإنجليزية تُشغَّلان بعد تهيئة B وSITE وSURFACE_DATE
# (كانتا قبل التهيئة فتُتخطّيان بصمت).
# بوابة زرّي اللغة على الموقع المنشور (تُشغَّل عند تمرير LIVE_URL)
if [ -n "${LIVE_URL:-}" ]; then
  if timeout 700 python3 "$B/tools/check_lang_switch_live.py" --url "$LIVE_URL" --date "${SURFACE_DATE:-$(date -u +%F)}" >/dev/null 2>&1; then
    ok "lang-switch-live"
  else
    bad "lang-switch-live — زرّا اللغة لا يعملان على الموقع المنشور"
  fi
fi

# بوابة تماثل النسخة الإنجليزية مع المتن (تفشل مغلقًا إن أُسقط رقم أو كود)
ENMD="$SITE/sources/i18n/en/${SURFACE_DATE}-sectioned.en.md"
# الإصلاح الذاتي (21 نوفمبر): نسخة إنجليزية معزولة لا تُبنى ولا تُنشر، فلا يُقاس تماثلها.
if python3 "$B/tools/auto_heal.py" isolated --date "$SURFACE_DATE" --surface en >/dev/null 2>&1; then
  ok "EN-parity-${SURFACE_DATE} — النسخة الإنجليزية معزولة لهذا اليوم (logs/auto-heal)"
elif [ -f "$ENMD" ]; then
  if python3 "$B/validators/check_en_parity.py" --date "$SURFACE_DATE" >/dev/null 2>&1; then
    ok "EN-parity-${SURFACE_DATE}"
  else
    bad "EN-parity-${SURFACE_DATE} — الترجمة تفقد بنية أو رقمًا"
  fi
fi

echo "===== اختبارات بوابات النظام — $(date -u +%FT%TZ) ====="

echo "0) حاجز الألفاظ المانعة على الأسطح (المتن · الواجهة · الصفحة)"
python3 "$B/tests/test_forbidden_surface_terms.py" >"$TMP/forbidden-surface.txt" 2>&1
check "$?" "0" "الحاجز يمنع نافذة في الاختبار السالب ويمرر السطح النظيف"
cat "$TMP/forbidden-surface.txt"

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
# ك-486: الطباعة معطَّلة بأمر المالك، فيبقى ملف PDF صفر بايت؛ ويُعلن التخطّي بدل إسقاط الاختبار كذبًا.
if [ -f "$PDF" ] && [ ! -s "$PDF" ]; then
  printf '  • تخطٍّ معلن: ملف PDF لليوم صفر بايت (الطباعة معطَّلة بأمر المالك) — يُختبر عند أول إصدار مطبوع\n'
elif [ -f "$PDF" ]; then
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

echo "5) رمز الانهيار 70 (حارس موحّد) يمنع التسليم"
cd "$B" || exit 1
R=$(ls reports/*-sectioned.md 2>/dev/null | tail -1)
crash_rc=$(REPORT="$R" python3 - <<'PY2' 2>/dev/null
import importlib.util, os, pathlib, sys
spec = importlib.util.spec_from_file_location("cs", "validators/check_style.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
_o = pathlib.Path.read_text
pathlib.Path.read_text = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("انهيار مصطنع"))
sys.path.insert(0, "validators")
from _guard import guard
sys.argv = ["check_style.py", os.environ["REPORT"]]
try:
    rc = guard(m.main)
finally:
    pathlib.Path.read_text = _o
print(rc)
PY2
)
check "$crash_rc" "70" "انهيار مصطنع داخل check_style يُخرج رمز 70"
if [ -s "$TMP/step.sh" ]; then
  LOGDIR="$TMP/log-c70"; mkdir -p "$LOGDIR"; REP="$LOGDIR/report.txt"; : > "$REP"; N=0; WORST=0
  ( set -uo pipefail; source "$TMP/step.sh"; step "فحص تجريبي" 2 python3 -c "import sys; sys.exit(70)" ) >/dev/null 2>&1
  s70=$(awk '{for(i=1;i<=NF;i++) if($i=="ok"||$i=="warn"||$i=="block"||$i=="crash"){print $i; exit}}' "$REP" | head -1)
  check "$s70" "crash" "خطوة برمز 70 بلا أي نص مخرج تُصنّف انهيارًا (منع)"
fi

echo "6) أرقام المصادر الثلاثة (معتمدة · مفحوصة · ناجحة)"
D=$(basename "$R" | sed 's/-sectioned.md//')
if [ -n "$D" ] && [ -f "feeds/feeds-$D.status.json" ]; then
  python3 -m pytest -q tests/test_source_totals_governed.py >"$TMP/source-totals.txt" 2>&1
  check "$?" "0" "إجماليات المصدر تُشتق وتُحدّث في المتنين العربي والإنجليزي"
  cat "$TMP/source-totals.txt"
  python3 tools/source_counts.py --date "$D" --write >"$TMP/sc.txt" 2>&1
  check "$?" "0" "كتابة سطر الأرقام في متن التقرير وملف الواجهة"
  python3 tools/source_counts.py --date "$D" --check >"$TMP/scc.txt" 2>&1
  check "$?" "0" "تطابق الأرقام في كل المواضع (متن · واجهة)"
  printf '     %s\n' "$(tail -1 "$TMP/sc.txt")"
else
  printf '  • تخطٍّ: لا ملف تغذيات لتاريخ %s\n' "$D"
fi

echo "7) قاعدة الأعطال المعروفة (التشغيل المنقوص قاعدة آلية)"
FD=1999-01-01
printf '{"date":"%s","overall":"failed","weird_component":{"status":"failed","note":"عطل غريب"}}\n' "$FD" > "logs/pipeline-$FD.json"
printf '## ما لم يُحسم\n- اختبار\n' > "reports/$FD-sectioned.md"
python3 validators/check_run_completeness.py --date "$FD" >/dev/null 2>&1
check "$?" "2" "عطل غير معروف في القائمة يمنع التسليم"
printf '{"date":"%s","overall":"degraded","feeds":{"status":"degraded","failed_feeds":[{"name":"وام","block_reason":"403 حجب"}]}}\n' "$FD" > "logs/pipeline-$FD.json"
printf '{"date":"%s","status":"degraded","checked":35,"ok":34,"failed":1,"failed_feeds":[{"num":37,"name":"وام","error":"حجب مصدر — رفض الخادم الطلب (HTTP 403)","block_reason":"all routes failed: primary: حجب مصدر (HTTP 403)"}]}\n' "$FD" > "feeds/feeds-$FD.status.json"
printf '## ما لم يُحسم\n- المصادر: 62 معتمدة · 35 مفحوصة في هذا التشغيل · 33 ناجحة · تعذّر 1: وام — حجب المصدر · مرجع العطل ك-63.\n- تشغيل منقوص مُفصح: التغذيات: حجب مصدر رسمي يمنع الجلب الآلي.\n' > "reports/$FD-sectioned.md"
python3 validators/check_run_completeness.py --date "$FD" >/dev/null 2>&1
check "$?" "1" "عطل معروف مُفصح عنه يمرّ بتحذير لا بمنع"
rm -f "feeds/feeds-$FD.status.json"
rm -f "logs/pipeline-$FD.json" "reports/$FD-sectioned.md"

echo "8) مخطط العلامة الثابت وكاتب العلامة"
if [ -f "logs/pipeline-${D}.json" ]; then
  if [ -f "logs/gate-${D}/gate.json" ]; then
    python3 tools/write_mark.py --date "$D" --stage final >"$TMP/wm.txt" 2>&1
    check "$?" "0" "كتابة العلامة بعد البوابة"
  else
    python3 tools/write_mark.py --date "$D" --stage final >"$TMP/wm.txt" 2>&1
    check "$?" "70" "رفض كتابة علامة نهائية قبل تشغيل بوابة التسليم"
    python3 tools/write_mark.py --date "$D" --stage pipeline >"$TMP/wmp.txt" 2>&1
    check "$?" "0" "اشتقاق علامة مرحلة pipeline من حالة المصادر الحالية قبل البوابة"
  fi
  python3 validators/check_mark_schema.py --date "$D" >"$TMP/cms.txt" 2>&1
  check "$?" "0" "مخطط العلامة مطابق (حقول وأنواع وأرقام)"
  python3 tests/test_mark_components_bootstrap.py >"$TMP/mcb.txt" 2>&1
  check "$?" "0" "mark_components يحدّث مصادر علامة قديمة من الحالة الحاكمة"
  cat "$TMP/mcb.txt"
  python3 -c "
import json;d=json.load(open('logs/pipeline-${D}.json'))
print('     الحقول:', len(d), '· نص التقرير موجود:', d.get('report_present_at_pipeline_end'), '· المصادر:', d.get('sources',{}).get('approved'),'/',d.get('sources',{}).get('checked'),'/',d.get('sources',{}).get('ok'))"
fi

echo "9) عدّادات التغذيات (ك-146): تُحسب بعدد المصادر ولا تفقد مصدرًا"
python3 tests/test_feed_counters.py && ok "عدّادات التغذيات متسقة" || bad "عدّادات التغذيات غير متسقة"

echo "10) قاعدة العنوان اليتيم (ك-148): تكتشف عنوان ذيل الصفحة وتتجاهل التذييل"
python3 tests/test_orphan_rule.py && ok "قاعدة العنوان اليتيم صحيحة" || bad "قاعدة العنوان اليتيم لا تعمل"

echo "11) حلقة التعلم الذاتي (ك-149): لا تكرار لدرس اليوم · والدليل في الكتلة"
python3 tests/test_skill_lessons.py && ok "حلقة التعلم صحيحة" || bad "حلقة التعلم لا تعمل"
python3 tests/test_known_faults_report_date.py && ok "الاستثناء يُختار بتاريخ التقرير لا بتاريخ التشغيل" || bad "الاستثناء يُختار بتاريخ التشغيل فيتغير إفصاح التقارير القديمة"
python3 tests/test_tg_digest_style.py && ok "رسالة تلغرام: جمل مكتملة بلا «…» وتجتاز مدقق الأسلوب" || bad "رسالة تلغرام تُقص أو تُدمج بنودها في جملة طويلة"
python3 tests/test_tg_digest_masdar.py && ok "رسالة تلغرام: الإجراء بصيغة المصدر لا الأمر" || bad "رسالة تلغرام: سطر الإجراء بصيغة الأمر"
python3 tests/test_tg_digest_layout.py && ok "رسالة تلغرام: الرمز والتاريخ والمؤشرات والإجراءات بالشكل المعتمد" || bad "رسالة تلغرام: شكل الرسالة مخالف لملاحظات المالك"
python3 tests/test_tg_after_publish.py && ok "تلغرام: لا إرسال قبل أن يعيد رابط التقرير 200، وD030 وحدها مفعّلة" || bad "تلغرام قد يسبق النشر أو فُعّلت خطوة بلا أمر"

echo "12) قائمة المهارات موحّدة (ك-150): النسخ الاحتياطي يقرأها من المزامنة"
python3 tests/test_backup_skills.py && ok "قائمة المهارات موحّدة" || bad "قائمتا المهارات مختلفتان"
python3 tests/test_pre_execution_plan_audit_skill_contract.py && ok "عقد مهارة تدقيق الخطة والادعاءات" || bad "عقد مهارة تدقيق الخطة والادعاءات فاشل"
python3 tests/test_gate_root_fail_closed.py && ok "الفشل المغلق في اشتقاق جذر الموقع" || bad "الفشل المغلق في اشتقاق جذر الموقع لا يعمل"
python3 tests/test_en_master_build_site_root.py && ok "مسار بناء الإنجليزية موجب وسالب" || bad "مسار بناء الإنجليزية لا يشتق جذر الموقع أو لا يفشل مغلقًا"
python3 tests/test_en_source_assets.py && ok "عقد الأصل الإنجليزي والمعجم وتسلسل B004/B004A/B005/B009" || bad "عقد الأصل الإنجليزي أو مزامنة الأصول أو ترتيب المنتج/المستهلك فاشل"

# ── مرحلة 24 أكتوبر 2026: أدوات اللغة · المحرّك · التسليم · PDF · البنية على GitHub ─────────
# المقترح ١ (اعتماد فهد 20 نوفمبر 2026): عند إعادة G001 لا يُعاد إلا الفحص الذي تغيّرت مدخلاته.
# الذاكرة تعمل فقط حين يمرّر المستدعي RUN_CHECKS_CACHE (أمر G001 وحده)، وحكمها في tools/run_checks_cache.py:
# نجاح سابق في اليوم نفسه + بصمة كل ما قرأه الفحص لم تتغير + تتبع كامل؛ وإلا يُعاد الفحص.
CACHED=0
[ -z "${RUN_CHECKS_CACHE:-}" ] || mkdir -p "$(dirname "$RUN_CHECKS_CACHE")" || RUN_CHECKS_CACHE=""
t() {  # t "الوصف" أمر...  — يمرّ إن كان رمز الخروج 0
  local name="$1"; shift
  if [ -z "${RUN_CHECKS_CACHE:-}" ]; then
    if "$@" >"$TMP/t.out" 2>&1; then ok "$name"; else bad "$name"; sed 's/^/      /' "$TMP/t.out" | tail -6; fi
    return
  fi
  { printf '%s\0' "$name" "$PWD" "$(date -u +%F)" "${B:-}" "${SITE:-}" "${SURFACE_DATE:-}" "${D:-}" "${LIVE_URL:-}" "${BRAIN_DIR:-}"
    printf '%s\0' "$@"; } > "$TMP/t.key"
  if python3 "$B/tools/run_checks_cache.py" lookup "$RUN_CHECKS_CACHE" "$TMP/t.key" 2>/dev/null; then
    CACHED=$((CACHED+1)); ok "$name · نتيجة مخزّنة (لم تتغير مدخلاته منذ آخر نجاح)"; return
  fi
  : > "$TMP/t.trace"
  local rc=0
  CHECKS_TRACE="$TMP/t.trace" PYTHONPATH="$B/tools/checks_trace${PYTHONPATH:+:$PYTHONPATH}" "$@" >"$TMP/t.out" 2>&1 || rc=$?
  { printf "%s\t" "$name"; python3 "$B/tools/run_checks_cache.py" record "$RUN_CHECKS_CACHE" "$TMP/t.key" "$TMP/t.trace" "$rc" 2>&1 || true; echo; } >>"$RUN_CHECKS_CACHE.log"
  if [ "$rc" -eq 0 ]; then ok "$name"; else bad "$name"; sed 's/^/      /' "$TMP/t.out" | tail -6; fi
}
cd "$B" || exit 1
echo "13) أدوات اللغة: حارس الحفظ · الإملاء · التحرير الآلي"
t "أدوات اللغة (اختبار قديم)" python3 tests/test_language_tools.py
t "وحدات إسناد المصدر مشتركة بين المولّد والحاجز" python3 tests/test_content_fidelity_units.py
t "حارس الحفظ: ترقيم ملاصق · عناوين · مسموح الحذف" python3 tests/test_preserve_check.py
t "فاحص الإملاء بلا إنذار كاذب" python3 tests/test_orthography.py
t "التحرير الآلي يحفظ التمهيد ويرفض تغيّر الأرقام" python3 tests/test_edit_pass.py
t "استخراج نص الأسطح بمحرك العرض بلا عيوب وهمية" python3 tests/test_audit_extract_no_phantom.py
t "قرار 9: بطاقات IMO الدائمة وسجل التحديثات" python3 tests/test_owner9_imo_cards.py
t "تسميات مصدر البطاقات خالية من العبارات الداخلية (ف4.8)" python3 tests/test_card_registry_reader_labels.py
t "البوابة الواحدة من سجل المحرّك والتسليم السحابي بلا حذف" python3 tests/test_single_gate_verdict.py

echo "14) محرّك الكتيب والمانيفست"
t "عقد الجذر الصريح: موجب من /tmp وسالب للمفقود/المخالف" python3 tests/test_root_contract_phase1.py
t "تقوية المحرّك (مسارات · ترتيب · gate-json · إتمام بالدليل)" python3 tests/test_runbook_hardening.py
t "اعتماد مهارة النقل: ربط فعلي وحالتا منع" python3 tests/test_portable_paths_skill_adoption.py
t "اختبارات المحرّك الأصلية" bash tests/test_runbook_engine.sh
t "إضافة قسم ثم حذفه على نسخة مؤقتة" bash tests/test_section_registry.sh
t "سجل الأقسام متسق مع التقرير والسياسة" python3 tests/test_sections_registry_vs_report.py --selftest
t "السجل مقابل أحدث تقرير" python3 tests/test_sections_registry_vs_report.py
t "برومت الكتابة يحمل المعجم والأمثلة والأقسام" python3 tests/test_write_prompt.py
t "نطاق فحص الحجب (المتن مقابل الملحق والفهرس)" python3 tests/test_hidden_scope.py
t "final_gate.sh متسق مع المانيفست" python3 tests/test_final_gate_vs_manifest.py
t "أوامر المانيفست: سكربتات وخيارات موجودة" python3 tests/test_manifest_commands.py
t "verify على المانيفست الحقيقي" python3 tools/runbook.py verify
t "ذاكرة فحوص G001: لا نتيجة مخزّنة إلا بلا تغيّر أي مدخل (موجب + سوالب)" python3 tests/test_run_checks_cache.py
t "الفحص المسبق المبكر S015: موجب وسالبا G000 وG049" python3 tests/test_early_preflight.py
t "جدول أزمنة المراحل: elapsed_s لكل سطر وجدول تلقائي بعد كل run" python3 tests/test_runbook_timings.py
t "قاعدة العدد في حالة المصادر: المعدود يوافق العدد والرقم باقٍ ولكل سطر مقابل إنجليزي" python3 tests/test_sources_state_counts.py
t "فجوات الطلبات القديمة: قوس CSS الجوال · حاجزا المعجم · أسماء السفن ذات المقطع الواحد من الدفتر" python3 tests/test_old_repo_gaps.py
t "جدول الإصلاح الذاتي سليم: صنف وإجراء معروفان ولا عطل محتوى بإجراء تقني" python3 tools/auto_heal.py check
t "الإصلاح الذاتي: إعادة الخطوة المتأثرة وحدها · عزل الإنجليزية · احتجاز المتن · قبول المدموج فقط" python3 -W ignore tests/test_auto_heal.py

echo "15) التسليم: النشر وتلغرام والتقدير"
t "سكربتات التسليم (بلا إرسال)" bash tests/test_delivery_scripts.sh
t "لا نشر خارج المحرّك" bash tests/test_no_publish_without_runbook.sh
t "رموز EST- مسجَّلة" python3 tests/test_register_estimate_check.py
t "G030: رموز EST الحالية ومعناها واختبار المنع السالب" python3 tests/test_g030_code_spaces.py

echo "16) مطابقة عناوين PDF (قلب لام-ألف)"
t "heading_present" python3 tests/test_pdf_heading_match.py
t "المحاذاة في الطباعة تتجاهل المحجوب (no-print)" python3 tests/test_print_alignment_hidden.py

echo "17) GitHub مصدر الشيفرة"
t "كل مسار مصنَّف code/data" python3 tools/code_paths.py check
t "apply_from_github: تعارض · أرشفة · استعادة" python3 tests/test_apply_from_github.py
t "النسخ الاحتياطي لا يكتب الشيفرة فوق GitHub" python3 tests/test_backup_code_safety.py
t "حاجز النسخ الاحتياطي يمنع الدفع المباشر إلى main" python3 tests/test_backup_push_safety.py
t "فهرس التقارير" python3 tests/test_reports_index.py
t "ملف الأسرار: قراءة وقالب وتصنيف" python3 tests/test_secrets_file.py


echo "18) مدقّقات الجولة الجديدة (طلب فهد 2026-10-24)"
t "بوابة الأسرار: الأنواع الثلاثة + إعفاء مكتوب السبب" python3 tests/test_new_validators.py
t "نطاق التماثل وأسبابه وأرضيته" python3 tests/test_parity_scope.py
t "منع التركيب المعلّق (ك-173)" python3 tests/test_hanging_opener.py

echo "19) السجل الحاكم للمفردات وتغطية الأسطح (طلب فهد 2026-10-27)"
t "السجل الحاكم: صلاحية · إنفاذ كل بند · سبب ومصدر · منع التعديل اليدوي · تغطية الأسطح" python3 tests/test_vocab_registry.py
t "G036: حالات كل مدخل وموجب وسالب وحدود الكلمات" python3 -m pytest -q tests/test_g036_vocabulary_contract.py tests/test_vocabulary_word_boundary.py
t "حاجز ألفاظ مولّد الإضافات: موجب + سالب" python3 "$SITE/tests/test_g001_forbidden_terms.py"
echo "20) قنوات المصادر (ك-237): الفحص كان يُشغَّل بلا احتساب رمز خروجه"
t "قنوات المصادر: الهوية والمسارات والفجوة وعدم التراجع" python3 validators/check_closure.py --brain "$B" || bad "بوابة الإغلاق: الحلقة غير مغلقة"
python3 tests/test_closure_gate.py || bad "اختبار بوابة الإغلاق"
python3 "$B/tests/test_sync_guard.py" || fail=1
python3 tests/test_source_channels.py

echo "21) سطح «إضافات» (ك-234): سطح قارئ جديد بلا حارس = خطر فقد أو تكرار"
t "سطح إضافات: العناوين المنقولة في صفحتها وحدها" python3 validators/check_additions_surface.py --date "$SURFACE_DATE"
t "أمانة المحتوى: أعمدة الجداول وأعداد المصادر من الدفتر" python3 validators/check_content_fidelity.py --date "$SURFACE_DATE"

echo "22) اقتراحات البوابة (كانت بعد exit 0 = كود ميت)"
t "اقتراحات البوابة" python3 tests/test_gate_suggestions.py

echo "23) أهم الأخبار المتعلقة بالأمن البحري (ك-239): سكربت الروابط كان يُفرغ الصف عند غياب القسم"
t "أهم الأخبار المتعلقة بالأمن البحري: كل صف نصًّا ورابطًا صالحًا على السطحين" python3 validators/check_decision_card.py --date "$SURFACE_DATE"

echo "24) عقد الدليل الحرفي لعلاقات دفتر الأحداث"
t "علاقات الدفتر: دليل حرفي ومكوّنات وفشل مغلق للأهداف" python3 tests/test_ledger_link_contract.py

echo "25) معجم المفردات المشتق (ك-328): تحذيرات كاذبة كانت تخفي العيوب الحقيقية"
t "المعجم المشتق مطابق للمصادر + لفظ مصطنع يُكتشف" python3 tests/test_lexicon_gate.py
t "شكل معجم النسخة الإنجليزية (ك-491)" python3 validators/check_glossary_shape.py
t "عقد بيان exact-only مع بقاء الرفض المغلق للمفاتيح الجذرية" python3 tests/test_glossary_shape_contract.py
t "مفردات حقل الموقع: أسماء المناطق البحرية وصيغة «الموقع - المنطقة» (ك-492)" python3 validators/check_area_vocabulary.py
t "محاذاة متن التقرير العربي والإنجليزي (عدد ونوع كل سطر)" env BRAIN_DIR="$B" python3 "$SITE/tests/test_i18n_alignment.py"
t "حدود وسوم LTR ومفاتيح المعجم السياقية" python3 "$B/../site/tests/test_i18n_ltr_tag_boundary.py"
t "بقاء العناوين الديناميكية ذات المقابل المسند" python3 "$B/../site/tests/test_i18n_master_backed_dynamic_content.py"

echo "26) أرضية الأصول الحاكمة (ك-483): أي نقص في أصل معتمد يمنع التسليم"
t "أرضية الأصول: قصّ يمنع · نموّ يرفع · قبول بسبب يُدوَّن · حذف يمنع" python3 tests/test_asset_floor.py

# ك-484: هذان الفحصان كانا بعد exit 0 (كود ميت) فلا يُنفَّذان في أي جولة.
echo "27) بوابات كانت معطَّلة فعليًا (ك-484)"
t "بوابة أسرار المستودع" python3 validators/check_repo_secrets.py
if python3 "$B/validators/check_python_syntax.py" >"$TMP/pysyn.txt" 2>&1; then
  ok "حارس ترجمة الشيفرة (لا ملف Python معطوب)"
else
  bad "حارس ترجمة الشيفرة"; tail -4 "$TMP/pysyn.txt" | sed 's/^/      /'
fi
# حارس ك-484: لا فحوص مكتوبة بعد exit 0 في هذا المشغّل (فحوص معطَّلة بصمت)
exit_line=$(grep -n '^exit 0' "$B/tests/run_checks.sh" | head -1 | cut -d: -f1)
if [ -n "$exit_line" ] && tail -n +"$((exit_line + 1))" "$B/tests/run_checks.sh" | grep -qE '^[[:space:]]*(t |python3|bash|validators/)'; then
  bad "فحوص بعد exit 0 = معطَّلة بصمت (ك-484)"
else
  ok "لا فحوص بعد exit 0 (ك-484)"
fi

echo "28) عقود الحراس: موجب + سالب لكل حارس مرشَّح"
t "عقود الحراس الستة عشر" python3 "$B/tests/test_gate_guard_contracts.py"

t "لا وسيط خارجي في مسار الإرسال" python3 tests/test_no_external_relay_20261107.py
t "تماثل الأرقام المرئية: موجب + سالب" python3 "$B/tests/test_en_parity_visible_numbers.py"
echo "29) عقد مهارة فرز ملاحظات المالك بالقياس"
t "بنية وتماثل وأداتان موجب وسالب" python3 "$B/tests/test_owner_notes_triage_skill_contract.py"
echo "30) عقد مهارة بوابة الانطلاق المحكوم"
t "بنية وتماثل وأداتان موجب وسالب" python3 "$B/tests/test_owner_approval_launch_gate_skill_contract.py"
echo "31) عقد مهارة فرز مسارات المصادر"
t "بنية وتماثل وتصنيف موجب وسالب وبوابة حداثة" python3 tests/test_source_route_triage_skill_contract.py
echo "32) فصل موثوقية المصدر عن الثقة التحليلية ومرساة الدليل"
t "وسمان منفصلان ومرساة دليل عميقة" python3 "$B/tests/test_reliability_and_evidence_anchor.py"

echo "33) نطاق قياس بنية التماثل: بنود القوائم في المتن لا في هيكل الصفحة (ك-617)"
t "موجب يمرّ وسالبان يُمنعان" python3 "$B/tests/test_en_parity_structure_scope.py"

echo "----- الحصيلة -----"
printf '  نجح: %s · فشل: %s\n' "$PASS" "$FAIL"
[ "$CACHED" -eq 0 ] || printf '  منها نتائج مخزّنة لم تتغير مدخلاتها: %s (RUN_CHECKS_CACHE)\n' "$CACHED"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
