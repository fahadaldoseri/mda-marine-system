#!/usr/bin/env bash
# بوابة التسليم النهائية — فشل مغلق
# بند 5 و6 من التدقيق المستقل (19 أكتوبر 2026): بوابات الفحص كانت خارج خط التشغيل،
# وكانت معلّقة بوجود ملف PDF مبنٍ من جولة سابقة. هذه البوابة تجمعها في مسار واحد
# بترتيب صحيح: يبني ← يُصدّر PDF ← يفحص، وأي مخالفة مانعة تُسقط التسليم.
#
# سلّم رموز الخروج الموحّد: 0 = نجاح · 1 = نجاح مع تحذير · 2 = مانع (يوقف التسليم)
# الاستخدام: bash tools/final_gate.sh <YYYY-MM-DD> [--no-build]
set -uo pipefail
B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SITE="${SITE_DIR:-$(dirname "$B")/seawatch}"
D="${1:-$(date -u +%F)}"
BUILD=1
for a in "$@"; do [ "$a" = "--no-build" ] && BUILD=0; done

LOGDIR="$B/logs/gate-$D"; mkdir -p "$LOGDIR"
REP="$LOGDIR/report.txt"; : > "$REP"
WORST=0
N=0

step() {            # step "<اسم الفحص>" <رمز المانع عند الفشل> <الأمر...>
  local name="$1"; shift
  local blockrc="$1"; shift
  N=$((N+1))
  local log="$LOGDIR/$(printf '%02d' "$N")-$(echo "$name" | tr ' /' '__').log"
  "$@" >"$log" 2>&1
  local rc=$?
  local status="ok"
  if [ "$rc" -ge "$blockrc" ]; then status="block"; WORST=2
  elif [ "$rc" -gt 0 ]; then status="warn"; [ "$WORST" -lt 1 ] && WORST=1; fi
  printf '%-34s %-6s (رمز %s) %s\n' "$name" "$status" "$rc" "$(basename "$log")" >> "$REP"
  printf '  %-34s %-6s (رمز %s)\n' "$name" "$status" "$rc"
  return 0
}

echo "===== بوابة التسليم النهائية — $D — $(date -u +%FT%TZ) ====="
echo "السلّم: 0 نجاح · 1 تحذير · 2 مانع" | tee -a "$REP"

if [ ! -f "$B/reports/$D-sectioned.md" ] || [ ! -f "$B/web/meta/$D.json" ]; then
  echo "  ✘ ناقص: reports/$D-sectioned.md أو web/meta/$D.json — لا تسليم بلا نص وواجهة." | tee -a "$REP"
  WORST=2
fi

# تنظيف المحتوى الداخلي آليًا قبل البناء — يضمن ألا يتوقف النشر بسبب صنف معروف.
# التنظيف لا يمنع التسليم (رمز 3)؛ والبوابة أدناه هي التي تمنع الجديد فقط.
step "تنظيف المحتوى الداخلي" 3 python3 "$B/tools/scrub_internal.py" --date "$D" --apply

# دمج بنك التعريفات المعياري: يضمن أن كل رمز مستخدم له تعريف يراه القارئ،
# ويسبق البناء حتى يصل التعريف إلى الصفحة وPDF وبوابة الفهم معًا.
step "دمج بنك التعريفات" 2 python3 "$B/tools/merge_glossary.py" --date "$D"
if [ "$BUILD" = "1" ]; then
  step "بناء الصفحة (مزامنة + بناء)" 2 python3 "$SITE/generator/sync_from_brain.py" --date "$D"
  step "تصدير PDF المعتمد" 2 python3 "$B/tools/export_report_assets.py" --date "$D" --only pdf
  # جودة الطباعة (ك-104 · ك-105): تُقاس على PDF النهائي وبوسائط print نفسها التي يُبنى بها.
  # عرض/ارتفاع كتلة الخريطة وتصفير كل كتل المتن = بند مانع يوقف النشر وتلغرام.
  step "جودة الطباعة (الخريطة والتصفير على PDF)" 2 python3 "$B/validators/check_print_quality.py" \
    --pdf "$SITE/dist/reports/pdf/$D.pdf" --page "$SITE/dist/reports/$D.html" --date "$D"
  # نسخة Word طبق الأصل: بوابة المخرج 9 تمنع التسليم بلا نسخة Word، فتُبنى هنا آليًا
  step "نسخة Word طبق الأصل" 2 python3 "$B/tools/build_report_docx_exact.py" --date "$D"
fi

step "فحص ما قبل التشغيل" 2 python3 "$B/tools/preflight_check.py" "$D"
step "مدقق التقرير (الواجهة)" 2 python3 "$B/validators/validate_report.py" "$B/web/meta/$D.json" --md "$B/reports/$D-sectioned.md"
step "بوابة الأسلوب" 2 python3 "$B/validators/check_style.py" "$B/reports/$D-sectioned.md"
step "بوابة اللغة" 2 python3 "$B/validators/check_language.py" "$B/reports/$D-sectioned.md"
# بوابة الفهم: رموز بلا تعريف · اصطلاحات حاجبة · محتوى داخلي منشور · التباس «قُطر/قطر» · تعارض أرقام
# المرحلة تُقرأ من appendices/comprehension-stages.json: 0 تحذيري · 1 يمنع ف3 · 2 يضيف ف4+ف5 · 3 يضيف ف1 · 4 يمنع الكل
COMP_STAGE=$(python3 -c "import json;print(json.load(open('$B/appendices/comprehension-stages.json'))['stage'])" 2>/dev/null || echo 0)
# ── بوابات ملزمة: الترابط والتماثل (قرار المستخدم — مانع لا تحذير) ──────────
# القاعدة: كل مكتبة وكل مهارة مرتبطة ببوابة تنفيذ، ولا اختلاف بين النسخ.
# مقياس blockrc: 1 = أي فشل يوقف · 2 = الفشل المانع فقط.
step "بوابة إغلاق المكتبات" 1 python3 validators/check_findings_closed.py --date "$D"
step "ترابط المكتبات والمهارات" 2 python3 validators/check_libraries_skills.py
step "تماثل المهارات والمكتبات (مزامنة فورية)" 1 bash tools/restore_skills.sh --check
step "سلامة المهارات" 1 python3 validators/check_skills_integrity.py
step "بوابة الفهم (مرحلة $COMP_STAGE)" 2 python3 "$B/validators/check_comprehension.py" --date "$D"
step "بوابة التحليل الاستخباري" 2 python3 "$B/validators/check_intel.py" "$B/reports/$D-sectioned.md" "$B/web/meta/$D.json"
# فحص العقوبات يُحدَّث لحظة البوابة، فالتقرير قد يُكتب أو يُعدَّل بعد الخط اليومي
python3 "$B/tools/ofac_targets_from_report.py" --date "$D" >/dev/null 2>&1 || true
python3 "$B/tools/ofac_screen.py" "$B/watchlist/ofac-targets.txt" >/dev/null 2>&1 || true
step "تغطية فحص العقوبات" 2 python3 "$B/validators/check_ofac_coverage.py" --date "$D"
step "استعمال المكتبات (المعجم والبنك والفجوات)" 2 python3 "$B/validators/check_library_use.py" --date "$D"
step "عدد المصادر (مصدر واحد)" 2 python3 "$B/validators/check_sources_count.py"
step "قابلية النقل (مسارات)" 2 python3 "$B/validators/check_portable_paths.py"
step "الأرقام (0-9 لاتينية)" 2 python3 "$B/validators/check_numerals.py"
# تنبيهي فعليًا: الانحراف (رمز 1) تحذير قبل الدفع؛ ولا يوقف إلا فقدان المستودع (رمز 3)
# عطل ك-70: المطابقة كانت تُشغَّل قبل خطوة النسخ فتظهر انحرافًا في كل إصدار بلا معنى.
# نُقلت إلى سلسلة التسليم بعد النسخ (tools/daily_pipeline.sh) لتصبح تحققًا حقيقيًا.
# قاعدة دائمة: حصاد الألفاظ والرموز الجديدة قبل أي تسليم (موقع أو PDF)
step "حصاد الألفاظ الجديدة" 2 python3 "$B/tools/harvest_terms.py" --date "$D"
step "سياسة الرموز في المخرجات" 2 python3 "$B/validators/check_code_policy.py" "$SITE/dist"
step "فصل فضاءات الرموز MN-/EST-" 2 python3 "$B/validators/check_code_spaces.py" --date "$D"
step "قاعدة النقاط في المصدر" 2 python3 "$B/validators/check_points_rule.py" --md "$B/reports/$D-sectioned.md" --meta "$B/web/meta/$D.json"
# فاحص النقل بين الإصدارات: سنة أو اسم سفينة خارج الفترة · نقل حرفي · حقل إسناد وزمن
# الأساس: حادثة BW RHINE (وصف 2019 نُقل كواقعة 2026) — الاعتماد على السجل التراكمي لا على الحدس
step "فاحص النقل بين الإصدارات" 2 python3 "$B/validators/check_carryover.py" --date "$D"
# ── تدقيق المكتبات اللغوية — أسبوعيًا (تنبيهي، لا يوقف النشر) ──────────────
AUDIT_STAMP="$B/logs/.audit-last"
if [ ! -f "$AUDIT_STAMP" ] || [ $(( ( $(date -u +%s) - $(date -u -r "$AUDIT_STAMP" +%s 2>/dev/null || echo 0) ) / 86400 )) -ge 6 ]; then
  step "تدقيق المكتبات اللغوية (أسبوعي)" 3 python3 "$B/tools/audit_corpus.py" --date "$D"
  date -u +%FT%TZ > "$AUDIT_STAMP" 2>/dev/null || true
else
  echo "  • تدقيق المكتبات: أُجري خلال آخر 6 أيام — تخطٍّ" | tee -a "$REP"
fi

step "بوابات المخرج العشر" 2 python3 "$B/tools/qa_gates.py" --date "$D"

echo "----- الخلاصة -----" | tee -a "$REP"
cat "$REP" | tail -14
python3 - "$D" "$WORST" "$LOGDIR" "$B" <<'PY'
import json, sys, datetime
from pathlib import Path
d, worst, logdir = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
B = Path(sys.argv[4])
status = {0: 'ok', 1: 'warn', 2: 'block'}[worst]
steps = []
for line in (logdir / 'report.txt').read_text(encoding='utf-8').splitlines():
    parts = line.split()
    idx = next((i for i, t in enumerate(parts) if t in ('ok', 'warn', 'block')), None)
    if idx:  # اسم الفحص قد يحوي مسافات — الموضع يُحدَّد بأول رمز حالة
        steps.append({'step': ' '.join(parts[:idx]), 'status': parts[idx],
                      'exit_code': parts[idx + 2] if len(parts) > idx + 2 and parts[idx + 1] == '(رمز' else None,
                      'log': parts[-1]})
result = {'date': d, 'status': status, 'exit_code': worst, 'steps': steps,
          'log_dir': str(logdir), 'finished_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
(logdir / 'gate.json').write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
mark = B / f'logs/pipeline-{d}.json'
if mark.exists():
    try:
        m = json.loads(mark.read_text(encoding='utf-8'))
        m['final_gate'] = {'status': status, 'exit_code': worst, 'dir': f'logs/gate-{d}',
                           'blocked_steps': [s['step'] for s in steps if s['status'] == 'block'],
                           'note': 'نتيجة بوابة التسليم النهائية — مسجّلة بعد كتابة التقرير.'}
        mark.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"  · سُجّلت نتيجة البوابة في العلامة: logs/pipeline-{d}.json")
    except Exception as e:
        print(f"  · تعذر تحديث العلامة ({e}) — النتيجة محفوظة في gate.json")
PY
echo "===== نهاية البوابة: $([ "$WORST" = "0" ] && echo 'نجاح' || { [ "$WORST" = "1" ] && echo 'نجاح مع تحذير' || echo 'مانع — التسليم موقوف'; }) (رمز $WORST) ====="
echo "السجلات: $LOGDIR"
exit "$WORST"
