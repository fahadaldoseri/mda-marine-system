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
  fi
  python3 validators/check_mark_schema.py --date "$D" >"$TMP/cms.txt" 2>&1
  check "$?" "0" "مخطط العلامة مطابق (حقول وأنواع وأرقام)"
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

echo "12) قائمة المهارات موحّدة (ك-150): النسخ الاحتياطي يقرأها من المزامنة"
python3 tests/test_backup_skills.py && ok "قائمة المهارات موحّدة" || bad "قائمتا المهارات مختلفتان"

# ── مرحلة 24 أكتوبر 2026: أدوات اللغة · المحرّك · التسليم · PDF · البنية على GitHub ─────────────
t() {  # t "الوصف" أمر...  — يمرّ إن كان رمز الخروج 0
  local name="$1"; shift
  if "$@" >"$TMP/t.out" 2>&1; then ok "$name"; else bad "$name"; sed 's/^/      /' "$TMP/t.out" | tail -6; fi
}
cd "$B" || exit 1
echo "13) أدوات اللغة: حارس الحفظ · الإملاء · التحرير الآلي"
t "أدوات اللغة (اختبار قديم)" python3 tests/test_language_tools.py
t "حارس الحفظ: ترقيم ملاصق · عناوين · مسموح الحذف" python3 tests/test_preserve_check.py
t "فاحص الإملاء بلا إنذار كاذب" python3 tests/test_orthography.py
t "التحرير الآلي يحفظ التمهيد ويرفض تغيّر الأرقام" python3 tests/test_edit_pass.py

echo "14) محرّك الكتيب والمانيفست"
t "تقوية المحرّك (مسارات · ترتيب · gate-json · إتمام بالدليل)" python3 tests/test_runbook_hardening.py
t "اختبارات المحرّك الأصلية" bash tests/test_runbook_engine.sh
t "إضافة قسم ثم حذفه على نسخة مؤقتة" bash tests/test_section_registry.sh
t "سجل الأقسام متسق مع التقرير والسياسة" python3 tests/test_sections_registry_vs_report.py --selftest
t "السجل مقابل أحدث تقرير" python3 tests/test_sections_registry_vs_report.py
t "برومت الكتابة يحمل المعجم والأمثلة والأقسام" python3 tests/test_write_prompt.py
t "final_gate.sh متسق مع المانيفست" python3 tests/test_final_gate_vs_manifest.py
t "أوامر المانيفست: سكربتات وخيارات موجودة" python3 tests/test_manifest_commands.py
t "verify على المانيفست الحقيقي" python3 tools/runbook.py verify

echo "15) التسليم: النشر وتلغرام والتقدير"
t "سكربتات التسليم (بلا إرسال)" bash tests/test_delivery_scripts.sh
t "لا نشر خارج المحرّك" bash tests/test_no_publish_without_runbook.sh
t "رموز EST- مسجَّلة" python3 tests/test_register_estimate_check.py

echo "16) مطابقة عناوين PDF (قلب لام-ألف)"
t "heading_present" python3 tests/test_pdf_heading_match.py
t "المحاذاة في الطباعة تتجاهل المحجوب (no-print)" python3 tests/test_print_alignment_hidden.py

echo "17) GitHub مصدر الشيفرة"
t "كل مسار مصنَّف code/data" python3 tools/code_paths.py check
t "apply_from_github: تعارض · أرشفة · استعادة" python3 tests/test_apply_from_github.py
t "النسخ الاحتياطي لا يكتب الشيفرة فوق GitHub" python3 tests/test_backup_code_safety.py
t "فهرس التقارير" python3 tests/test_reports_index.py
t "ملف الأسرار: قراءة وقالب وتصنيف" python3 tests/test_secrets_file.py


echo "18) مدقّقات الجولة الجديدة (طلب فهد 2026-10-24)"
t "بوابة الأسرار: الأنواع الثلاثة + إعفاء مكتوب السبب" python3 tests/test_new_validators.py
t "نطاق التماثل وأسبابه وأرضيته" python3 tests/test_parity_scope.py
t "منع التركيب المعلّق (ك-173)" python3 tests/test_hanging_opener.py

echo "19) السجل الحاكم للمفردات وتغطية الأسطح (طلب فهد 2026-10-27)"
t "السجل الحاكم: صلاحية · إنفاذ كل بند · سبب ومصدر · منع التعديل اليدوي · تغطية الأسطح" python3 tests/test_vocab_registry.py
echo "20) قنوات المصادر (ك-237): الفحص كان يُشغَّل بلا احتساب رمز خروجه"
t "قنوات المصادر: الهوية والمسارات والفجوة وعدم التراجع" python3 tests/test_source_channels.py

echo "21) سطح «إضافات» (ك-234): سطح قارئ جديد بلا حارس = خطر فقد أو تكرار"
t "سطح إضافات: العناوين المنقولة في صفحتها وحدها" python3 validators/check_additions_surface.py --date "$(date -u +%F)"

echo "22) اقتراحات البوابة (كانت بعد exit 0 = كود ميت)"
t "اقتراحات البوابة" python3 tests/test_gate_suggestions.py

echo "----- الحصيلة -----"
printf '  نجح: %s · فشل: %s\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
