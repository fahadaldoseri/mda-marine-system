#!/usr/bin/env bash
# اختبار مستقل لإصلاحات OFAC — لا يتصل بالشبكة ولا يكتب أسرارًا.
set -uo pipefail

ROOT="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); printf '✔ %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf '✘ %s\n' "$1"; }

# 1) لا تُحوِّل كلمة DOLPHIN وحدها اسم PETRO DOLPHIN إلى تطابق.
out=$(PYTHONPATH="$ROOT/tools" python3 - <<'PY' 2>&1
from ofac_screen import match_target

result = match_target("PETRO DOLPHIN", [{"name": "DOLPHIN", "imos": []}])
assert result["result"] == "no_match", result
assert result["match_type"] is None, result
print("no_false_match")
PY
)
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q '^no_false_match$'; then
  ok "PETRO DOLPHIN لا يطابق DOLPHIN وحدها"
else
  bad "تطابق خاطئ للاسم PETRO DOLPHIN: $out"
fi

# 2) رقم IMO يُفحص قبل الاسم، ولو اختلف اسم السفينة.
out=$(PYTHONPATH="$ROOT/tools" python3 - <<'PY' 2>&1
from ofac_screen import match_target

result = match_target(
    "اسم مختلف تمامًا (IMO 1234567)",
    [{"name": "اسم مدرج آخر", "imos": ["1234567"]}],
)
assert result["result"] == "match", result
assert result["match_type"] == "imo", result
assert result["match_score"] == 100, result
print("imo_first")
PY
)
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q '^imo_first$'; then
  ok "رقم IMO يطابق أولًا رغم اختلاف الاسم"
else
  bad "فشل تطابق IMO: $out"
fi

# 3) فشل الاستخراج لا يمرّ برمز صفر، ومسار التشغيل يوسمه failed بدل الاستمرار الصامت.
set +e
extract_out=$(BRAIN_DIR="$TMP" python3 "$ROOT/tools/ofac_targets_from_report.py" --date 2026-10-23 2>&1)
extract_rc=$?
set -e
if [ "$extract_rc" -ne 0 ]; then
  ok "فشل استخراج أهداف OFAC يعيد رمزًا غير صفري ($extract_rc)"
else
  bad "فشل الاستخراج أعاد رمزًا صفريًا: $extract_out"
fi

if grep -Fq 'OFAC_EXTRACT_RC=' "$ROOT/tools/daily_pipeline.sh" \
   && grep -Fq 'S_OFAC="failed"' "$ROOT/tools/daily_pipeline.sh" \
   && ! grep -Fq 'ofac_targets_from_report.py --date "$D" >>"$LOG" 2>&1 \\n  ||' "$ROOT/tools/daily_pipeline.sh"; then
  ok "فشل الاستخراج يُصنَّف failed ويمنع التشغيل المنقوص"
else
  bad "مسار التشغيل لا يثبت تصنيف فشل استخراج OFAC كتشغيل منقوص"
fi

printf 'الأثر: نجح %s · فشل %s\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
