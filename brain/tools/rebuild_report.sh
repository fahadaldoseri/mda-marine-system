#!/usr/bin/env bash
# ═══ إعادة بناء التقرير بالتسلسل الإلزامي + تحقق أن المخرج تغيّر فعلًا ═══
# الأساس: عطل ك-44 — عُدّل القاموس في بيانات Brain ولم يتغيّر PDF لأن التصدير يقرأ
# من مصادر الموقع، فمرّت دورة كاملة بإنذار كاذب بالإصلاح.
# القاعدة: الترتيب أدناه هو الوحيد المسموح، وكل إصلاح يُثبت بتغيّر المخرج.
#
# الاستخدام: bash tools/rebuild_report.sh 2026-10-20 [--expect-change]
set -uo pipefail
_B="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_S="$(dirname "$_B")/seawatch"
D="${1:?التاريخ مطلوب: YYYY-MM-DD}"
EXPECT=0; for a in "$@"; do [ "$a" = "--expect-change" ] && EXPECT=1; done
FAIL=0
say() { printf '\n───── %s ─────\n' "$1"; }

if [ "$EXPECT" = "1" ]; then
  say "0) بصمة ما قبل التعديل"
  python3 "$_B/tools/pdf_change_guard.py" --date "$D" --snapshot || FAIL=1
fi

say "1) دمج بنك التعريفات"
python3 "$_B/tools/merge_glossary.py" --date "$D" --force 2>&1 | tail -2 || FAIL=1

say "2) مزامنة بيانات Brain إلى الموقع"
python3 "$_S/generator/sync_from_brain.py" --date "$D" 2>&1 | tail -1 || FAIL=1

say "3) بناء الموقع"
( cd "$_S" && python3 generator/build_site.py 2>&1 | tail -1 ) || FAIL=1

say "4) تصدير PDF"
python3 "$_B/tools/export_report_assets.py" --date "$D" --only pdf 2>&1 | tail -2 || FAIL=1

if [ "$EXPECT" = "1" ]; then
  say "5) هل تغيّر المخرج فعلًا؟"
  python3 "$_B/tools/pdf_change_guard.py" --date "$D" --verify
  [ "$?" = "2" ] && { echo "  ✘ دورة بلا أثر — راجع التسلسل"; FAIL=1; }
fi

say "6) مطابقة الشكل v3"
python3 "$_B/validators/check_pdf_format.py" --pdf "$_S/dist/reports/pdf/$D.pdf" 2>&1 | tail -3
[ "${PIPESTATUS[0]}" = "2" ] && FAIL=1

say "7) جودة الطباعة — عرض الخريطة وتصفير المتن (ك-104 · ك-105)"
python3 "$_B/validators/check_print_quality.py" --pdf "$_S/dist/reports/pdf/$D.pdf" \
  --page "$_S/dist/reports/$D.html" --date "$D" 2>&1 | tail -5
[ "${PIPESTATUS[0]}" = "2" ] && FAIL=1

say "8) ميزانية الصفحات"
python3 "$_B/tools/page_budget.py" --date "$D" --adding "${ADDING:-0}" 2>&1 | tail -5

[ "$FAIL" = "0" ] && echo -e "\n✔ إعادة البناء مكتملة ومثبتة بالأثر" || echo -e "\n✘ إعادة البناء ناقصة"
exit "$FAIL"
