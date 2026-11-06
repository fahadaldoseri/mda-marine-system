#!/usr/bin/env bash
# اختبار تكامل معزول لأداة إغلاق الجولة `round_close_check.sh` مع حارس وصفات الإغلاق.
#
# الفكرة: الأداة تحكم بأربعة فحوص (تماثل · حارس إغلاق · سلامة مهارات · وصفات إغلاق).
# هذا الاختبار يبني دماغًا وهميًا في /tmp، ويُفشل فحصًا واحدًا في كل حالة،
# ثم يتحقق أن الحكم انقلب بالاسم الصحيح. إن لم ينقلب، فالحكم تجميلي لا قياسي.
#
# الاستعمال: bash close_check_selftest.sh
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REAL="$SKILL_DIR/scripts/round_close_check.sh"
REAL_LINT="$SKILL_DIR/scripts/recipe_lint.py"
ROOT="/tmp/cc-selftest"
DATE="2026-11-02"
PASS=0; FAIL=0

stub() { # stub <file> <env-key>
  mkdir -p "$(dirname "$1")"
  printf 'import os, sys\nsys.exit(int(os.environ.get("%s", "0")))\n' "$2" > "$1"
}

build_brain() { # build_brain <dir>
  local B="$1"; rm -rf "$B"; mkdir -p "$B/validators" "$B/tools" "$B/audit"
  stub "$B/validators/check_backup_parity.py" FAKE_PARITY
  stub "$B/validators/check_closure.py" FAKE_CLOSURE
  stub "$B/validators/check_skills_integrity.py" FAKE_SKILLS
  printf 'import sys\nprint("  حالة تجريبية")\nsys.exit(0)\n' > "$B/tools/runbook.py"
  printf '| ك-000 | 2026-11-02 | تجربة | عَرَض | سبب | إصلاح | تشديد | مفتوح | منفَّذ | متحقق | مطبَّق | مغلق |\n' > "$B/audit/سجل-الأعطال-والثغرات.md"
}

run_case() { # run_case <name> <expect-substring> <env assignments...>
  local name="$1" expect="$2"; shift 2
  local out="$ROOT/out.md"
  rm -f "$out"
  env "$@" bash "$ROOT/scripts/round_close_check.sh" --date "$DATE" \
      --brain "$ROOT/brain" --site "$ROOT/site" --url "http://127.0.0.1:9" > "$ROOT/last.log" 2>&1
  local verdict
  verdict=$(grep -a "غير جاهز\|قابلة للإعلان" "$out" 2>/dev/null | tail -1)
  if printf '%s' "$verdict" | grep -qF "$expect"; then
    PASS=$((PASS+1)); printf '   ✔ %s → «%s»\n' "$name" "$expect"
  else
    FAIL=$((FAIL+1)); printf '   ✘ %s → المتوقع «%s» · الحكم: %s\n' "$name" "$expect" "${verdict:-بلا حكم}"
  fi
}

[ -f "$REAL" ] || { echo "   ✘ أداة الإغلاق غير موجودة: $REAL" >&2; exit 2; }
rm -rf "$ROOT"; mkdir -p "$ROOT/scripts" "$ROOT/references" "$ROOT/site"
cp "$REAL_LINT" "$ROOT/scripts/recipe_lint.py"
cp "$SKILL_DIR/references/playbook.md" "$ROOT/references/playbook.md"
sed 's|^OUT="/home/ubuntu/audit-${DATE}/round-close-${DATE}.md"|OUT="/tmp/cc-selftest/out.md"|' \
    "$REAL" > "$ROOT/scripts/round_close_check.sh"
grep -q 'OUT="/tmp/cc-selftest/out.md"' "$ROOT/scripts/round_close_check.sh" \
  || { echo "   ✘ تعذّر توجيه مخرج الاختبار إلى /tmp — عُدّل مسار OUT في الأداة؟" >&2; exit 2; }
build_brain "$ROOT/brain"

echo "   ══ مصفوفة العزل: كل فحص يُقلب الحكم وحده ══"
run_case "الكل سليم"                 "قابلة للإعلان"        FAKE_PARITY=0 FAKE_CLOSURE=0 FAKE_SKILLS=0
run_case "التماثل فاشل"              "التماثل=2"            FAKE_PARITY=2 FAKE_CLOSURE=0 FAKE_SKILLS=0
run_case "حارس الإغلاق فاشل"          "حارس الإغلاق=2"        FAKE_PARITY=0 FAKE_CLOSURE=2 FAKE_SKILLS=0
run_case "سلامة المهارات فاشلة"       "سلامة المهارات=2"      FAKE_PARITY=0 FAKE_CLOSURE=0 FAKE_SKILLS=2

# وصفة فاسدة: خلية فارغة في المرجع المحلي للاختبار
cp "$ROOT/references/playbook.md" "$ROOT/references/playbook.ok.md"
printf '| Z | عرض |  | إصلاح | `python3 tools/runbook.py verify` |\n' >> "$ROOT/references/playbook.md"
run_case "وصفة إغلاق فاسدة"           "وصفات الإغلاق=2"       FAKE_PARITY=0 FAKE_CLOSURE=0 FAKE_SKILLS=0
mv "$ROOT/references/playbook.ok.md" "$ROOT/references/playbook.md"

# حارس الوصفات مفقود
mv "$ROOT/scripts/recipe_lint.py" "$ROOT/scripts/recipe_lint.py.off"
run_case "حارس الوصفات مفقود"         "وصفات الإغلاق=64"      FAKE_PARITY=0 FAKE_CLOSURE=0 FAKE_SKILLS=0
mv "$ROOT/scripts/recipe_lint.py.off" "$ROOT/scripts/recipe_lint.py"

# ك-452: يجب أن يحمل التقرير حكمًا واحدًا (صورة للحالة اللحظية)، لا أحكامًا متراكمة.
NV=$(grep -ac "قابلة للإعلان\|غير جاهز" "$ROOT/out.md" 2>/dev/null || echo 0)
if [ "$NV" -eq 1 ]; then
  PASS=$((PASS+1)); echo "   ✔ حكم واحد في التقرير (لا تراكم)"
else
  FAIL=$((FAIL+1)); echo "   ✘ عدد الأحكام في التقرير: ${NV} (المتوقع 1)"
fi

echo "   ─────────────────────────────"
if [ "$FAIL" -eq 0 ]; then
  echo "   ✔ تكامل سليم: ${PASS}/${PASS} حالة — الحكم يقيس الفحوص الأربعة لا يجمّلها"
  exit 0
fi
echo "   ✘ فشل التكامل: ${FAIL} حالة من $((PASS+FAIL))"
exit 2
