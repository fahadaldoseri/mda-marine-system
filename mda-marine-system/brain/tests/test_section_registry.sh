#!/usr/bin/env bash
# إضافة قسم تجريبي ثم حذفه على نسخة مؤقتة من المشروع (لا الإنتاج) — بتأكيدات حقيقية لا عرض.
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
C="$(mktemp -d)"; trap 'rm -rf "$C"' EXIT
tar -C "$B" --exclude=.git --exclude=logs --exclude=design --exclude=reports --exclude='*.pdf' --exclude='*.docx' -cf - . | tar -C "$C" -xf -
mkdir -p "$C/reports"; cp "$(ls "$B"/reports/*-sectioned.md | tail -1)" "$C/reports/"
[ -d "$B/../site" ] && export SITE_DIR="$(cd "$B/../site" && pwd)" || export SITE_DIR="$(cd "$B/../seawatch" && pwd)"
cd "$C" || exit 2
PASS=0; FAIL=0
ok() { if [ "$1" = 0 ]; then PASS=$((PASS+1)); echo "  ✔ $2"; else FAIL=$((FAIL+1)); echo "  ✘ $2"; fi; }
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
