#!/usr/bin/env bash
# إضافة قسم تجريبي ثم حذفه على نسخة مؤقتة من المشروع (لا الإنتاج) — بتأكيدات حقيقية لا عرض.
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
T="$(mktemp -d)"; C="$T/brain"; S="$T/site"; trap 'rm -rf "$T"' EXIT
mkdir -p "$C" "$S"
tar -C "$B" --exclude=.git --exclude=logs --exclude=design --exclude=reports --exclude='*.pdf' --exclude='*.docx' -cf - . | tar -C "$C" -xf -
tar -C "$B/../site" --exclude=.git --exclude=node_modules --exclude=__pycache__ --exclude=.pytest_cache --exclude=dist -cf - . | tar -C "$S" -xf -
mkdir -p "$C/reports" "$S/dist"; cp "$(ls "$B"/reports/*-sectioned.md | tail -1)" "$C/reports/"
unset SITE SITE_DIR SITE_CANDIDATES
. "$C/tools/site_root.sh"
PASS=0; FAIL=0
ok() { if [ "$1" = 0 ]; then PASS=$((PASS+1)); echo "  ✔ $2"; else FAIL=$((FAIL+1)); echo "  ✘ $2"; fi; }
if SITE= SITE_DIR= SITE_CANDIDATES="$T/site-missing" site_root_resolve "$C"; then
  FAIL=$((FAIL+1)); echo "  ✘ جذر الموقع الغائب يمرّ بدل الفشل المغلق"
else
  root_rc=$?
  if [ "$root_rc" = 2 ]; then PASS=$((PASS+1)); echo "  ✔ جذر الموقع الغائب يفشل مغلقًا (rc=2)"; else FAIL=$((FAIL+1)); echo "  ✘ رمز جذر الموقع الغائب غير متوقع: $root_rc"; fi
fi
export SITE_CANDIDATES="$S"
if ! site_root_resolve "$C"; then site_root_message; exit 2; fi
export SITE_DIR="$SITE"
unset SITE_CANDIDATES
cd "$C" || exit 2
export BRAIN_DIR="$C"
python3 tools/runbook.py verify >/dev/null 2>&1; ok $? "الأساس سليم قبل التجربة"
python3 tools/runbook.py section-add --id next-notes --title "ملاحظات الغد" --after summary >/dev/null 2>&1
python3 tools/runbook.py handbook >/dev/null 2>&1
python3 tools/runbook.py verify >/dev/null 2>&1; [ $? -eq 2 ]; ok $? "قسم جديد بلا روابط يفشل verify"
mkdir -p blocks runbook/prompts/sections
BLK="blk_$$"   # اسم يُبنى وقت التشغيل كي لا يكون مذكورًا حرفيًا في هذا الملف المربوط
echo "def block_x(): pass" > "blocks/$BLK.py"
echo "# مقتطف برومت — ملاحظات الغد" > runbook/prompts/sections/next-notes.md
python3 - "$BLK" <<'PY'
import json, sys
from pathlib import Path
p = Path('runbook/runbook.json'); m = json.loads(p.read_text(encoding='utf-8'))
for s in m['sections']:
    if s['id'] == 'next-notes':
        s['block'] = 'blocks/' + sys.argv[1] + '.py'; s['validator'] = 'validators/validate_report.py'
        s['prompt_snippet'] = 'runbook/prompts/sections/next-notes.md'; s['tests'] = ['tests/test_sections_registry_vs_report.py']
p.write_text(json.dumps(m, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
PY
python3 tools/runbook.py handbook >/dev/null 2>&1
python3 tools/runbook.py verify >/dev/null 2>&1; ok $? "اكتمال الروابط يجعل verify ينجح"
python3 tests/test_sections_registry_vs_report.py >/dev/null 2>&1; ok $? "اختبار السجل مقابل التقرير يقبل القسم الجديد (بلا عنوان)"
python3 tools/runbook.py section-remove --id next-notes >/dev/null 2>&1
python3 tools/runbook.py handbook >/dev/null 2>&1
out="$(python3 tools/runbook.py verify 2>&1)"; rc=$?
[ $rc -ne 0 ] && echo "$out" | grep -q "$BLK"; ok $? "بعد حذف القسم تظهر ملفاته غير مربوطة"
echo "الحصيلة: نجح $PASS · فشل $FAIL"
[ "$FAIL" = 0 ]
