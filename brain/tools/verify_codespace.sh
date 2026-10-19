#!/usr/bin/env bash
# تحقّق وظيفي كامل من النظام داخل بيئة جديدة (GitHub Codespaces أو أي جهاز آخر).
# الغرض: إثبات أن السلسلة تعمل فعليًا من المشروع المستنسخ وحده — لا من نسخة Manus.
#
# الاستخدام:
#   bash brain/tools/verify_codespace.sh                 يختبر أحدث إصدار موجود
#   bash brain/tools/verify_codespace.sh 2026-10-19      يختبر إصدارًا محددًا
#
# رمز الخروج: 0 كل الفحوص المانعة نجحت · 2 فشل مانع واحد أو أكثر
set -u

B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SITE="${SITE_DIR:-$(dirname "$B")/seawatch}"
PY="${PYTHON_BIN:-python3}"
DATE="${1:-}"

if [ -z "$DATE" ]; then
  DATE=$(ls -1 "$B/web/meta"/*.json 2>/dev/null | sed 's/.*\///;s/\.json$//' | sort | tail -1)
fi
[ -z "$DATE" ] && { echo "✘ لا إصدارات في web/meta — مرّر تاريخًا صريحًا"; exit 2; }

MD="$B/reports/$DATE-sectioned.md"
META="$B/web/meta/$DATE.json"
PDF="$SITE/dist/reports/pdf/$DATE.pdf"

PASS=0; WARN=0; FAILN=0
RESULT_LOG=$(mktemp)
ok()   { printf '  ✔ %s\n' "$*"; PASS=$((PASS+1)); }
warn() { printf '  • %s\n' "$*"; WARN=$((WARN+1)); }
bad()  { printf '  ✘ %s\n' "$*"; FAILN=$((FAILN+1)); }
log()  { printf '\n\033[1m%s\033[0m\n' "$*"; }

# run <اسم> <رمز مخالفة مانع|تنبيه> <أمر...>
run() {
  local name="$1" tolerate="$2"; shift 2
  local out rc
  out=$("$@" 2>&1); rc=$?
  printf '%-34s' "  $name"
  if [ "$rc" -eq 0 ]; then echo "✔ نجح"; PASS=$((PASS+1))
  elif [ "$rc" -eq "$tolerate" ]; then echo "• تحذير (رمز $rc)"; WARN=$((WARN+1))
  else echo "✘ فشل (رمز $rc)"; FAILN=$((FAILN+1))
  fi
  printf '%s\t%s\t%s\n' "$name" "$rc" "$(echo "$out" | tail -1 | cut -c1-120)" >> "$RESULT_LOG"
}

log "0) بيئة التشغيل"
echo "  المسار: $B"
echo "  التاريخ: $DATE"
for c in soffice pdftoppm pdftotext pdfinfo; do
  command -v "$c" >/dev/null && ok "$c" || bad "$c غير مثبّت (يحتاجه Word/PDF)"
done
if command -v fc-list >/dev/null && fc-list :lang=ar family 2>/dev/null | grep -q .; then
  ok "خطوط عربية: $(fc-list :lang=ar family 2>/dev/null | sort -u | head -2 | paste -sd', ')"
else
  bad "لا خط عربي — PDF العربي سيخرج بمربعات"
fi
if ls "$HOME"/.cache/ms-playwright/chromium* >/dev/null 2>&1; then
  ok "متصفح Playwright مثبّت"
else
  bad "متصفح Playwright غير مثبّت — نفّذ: $PY -m playwright install chromium --with-deps"
fi
[ -f "$MD" ] && ok "مصدر التقرير موجود: $DATE" || bad "مصدر التقرير مفقود: $MD"

log "1) تصريف كل ملفات بايثون (النظام + الموقع)"
"$PY" - "$B" "$SITE" <<'PY'
import py_compile, sys
from pathlib import Path
bad = 0; n = 0
for root in sys.argv[1:]:
    for p in Path(root).rglob("*.py"):
        if any(x in p.parts for x in ("__pycache__", ".git", "backup-repo", "dist", "_oneoff")):
            continue
        n += 1
        try:
            py_compile.compile(str(p), doraise=True, cfile="/tmp/_c.pyc")
        except Exception as e:
            bad += 1; print(f"    ✘ {p}: {e}")
print(f"    ملفات: {n} · أخطاء: {bad}")
raise SystemExit(1 if bad else 0)
PY
[ $? -eq 0 ] && ok "لا خطأ صياغة في أي ملف" || bad "ملف واحد أو أكثر لا يُصرَّف"

log "2) البوابات العامة"
run "عدد المصادر"                 1 "$PY" "$B/validators/check_sources_count.py"
run "الأرقام الإنجليزية"          1 "$PY" "$B/validators/check_numerals.py"
run "قابلية النقل (لا مسار مطلق)" 2 "$PY" "$B/validators/check_portable_paths.py"
run "سياسة الرموز"               2 "$PY" "$B/validators/check_code_policy.py" "$SITE"

log "3) بوابات الإصدار $DATE"
run "بوابة الأسلوب"      2 "$PY" "$B/validators/check_style.py" "$MD"
run "بوابة اللغة"        2 "$PY" "$B/validators/check_language.py" "$MD"
run "مدقق التقرير"       2 "$PY" "$B/validators/validate_report.py" "$META" --md "$MD"
run "التحليل الاستخباري" 2 "$PY" "$B/validators/check_intel.py" "$MD" "$META"
run "قاعدة النقاط"       2 "$PY" "$B/validators/check_points_rule.py" --md "$MD" --meta "$META"
run "فضاء الرموز"        2 "$PY" "$B/validators/check_code_spaces.py" --date "$DATE" --report "$MD" --meta "$META"
run "تغطية فحص العقوبات" 2 "$PY" "$B/validators/check_ofac_coverage.py" --date "$DATE" --report "$MD"

log "4) بناء الموقع من البيانات"
run "بناء الموقع" 2 "$PY" "$SITE/generator/build_site.py"
PAGES=$(ls -1 "$SITE"/dist/reports/*.html 2>/dev/null | wc -l)
[ "$PAGES" -gt 0 ] && ok "صفحات الإصدارات المبنية: $PAGES" || bad "لم تُبنَ أي صفحة إصدار"

log "5) توليد PDF المعتمد (يشمل بوابة الشكل)"
run "تصدير PDF" 2 "$PY" "$B/tools/export_report_assets.py" --date "$DATE" --only pdf
if [ -f "$PDF" ]; then
  ok "ملف PDF: $(du -h "$PDF" | cut -f1) · $(pdfinfo "$PDF" 2>/dev/null | awk '/^Pages/{print $2" صفحة"}')"
else
  bad "ملف PDF لم يُنتج"
fi

log "6) نسخة Word طبق الأصل"
run "توليد Word" 2 "$PY" "$B/tools/build_report_docx_exact.py" --date "$DATE"
DOCX=$(ls -1t "$B/reports/docx/"*"$DATE"*.docx 2>/dev/null | head -1)
[ -n "$DOCX" ] && ok "ملف Word: $(basename "$DOCX") · $(du -h "$DOCX" | cut -f1)" || warn "لم يُعثر على ملف Word لهذا التاريخ"

log "النتيجة"
echo "  نجح: $PASS · تحذير: $WARN · فشل مانع: $FAILN"
echo "  سجل مفصّل: $RESULT_LOG"
if [ "$FAILN" -eq 0 ]; then
  echo "  ✔ البيئة صالحة لتشغيل النظام كاملًا (بناء · PDF · Word · البوابات)."
  exit 0
fi
echo "  ✘ راجع البنود المعلّمة بـ ✘ أعلاه قبل الاعتماد على هذه البيئة."
exit 2