#!/usr/bin/env bash
# اختبار 8: إضافة قسم تجريبي ثم حذفه — على نسخة مؤقتة من المشروع (لا الإنتاج).
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
C=/tmp/rb-prod-copy
rm -rf "$C"; mkdir -p "$C"
tar -C "$B" --exclude=.git --exclude=logs --exclude=design --exclude=skills --exclude='*.pdf' -cf - . | tar -C "$C" -xf -
cd "$C" || exit 2
echo '═══ (1) إضافة القسم التجريبي ═══'
python3 tools/runbook.py section-add --id next-notes --title "ملاحظات الغد" --after summary
echo '═══ (2) verify بعد الإضافة (يجب أن يفشل) ═══'
python3 tools/runbook.py verify; echo "exit=$?"
echo '═══ (3) إكمال الروابط ثم verify ═══'
mkdir -p blocks prompts
echo "def block_next_notes(): pass" > blocks/next-notes.py
echo "# مقتطف برومت — ملاحظات الغد" > prompts/next-notes.md
echo '#!/usr/bin/env bash' > tests/sections/test_next-notes.sh
echo 'echo "✔ قسم ملاحظات الغد"; exit 0' >> tests/sections/test_next-notes.sh
chmod +x tests/sections/test_next-notes.sh
python3 - <<'PY'
import json
from pathlib import Path
p = Path('runbook/runbook.json'); m = json.loads(p.read_text(encoding='utf-8'))
for s in m['sections']:
    if s['id'] == 'next-notes':
        s['block'] = 'blocks/next-notes.py'; s['validator'] = 'validators/validate_report.py'
        s['prompt_snippet'] = 'prompts/next-notes.md'; s['tests'] = ['tests/sections/test_next-notes.sh']
p.write_text(json.dumps(m, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
PY
python3 tools/runbook.py handbook >/dev/null
python3 tools/runbook.py verify; echo "exit=$?"
echo '═══ (4) اختبار القسم الجديد ═══'
bash tests/sections/test_next-notes.sh; echo "exit=$?"
echo '═══ (5) مرحلة البوابات على النسخة المؤقتة (مع القسم الجديد) ═══'
timeout 900 python3 tools/runbook.py gates --date 2026-10-23 2>&1 | tail -12; echo "exit=$?"
echo '═══ (6) حذف القسم ═══'
python3 tools/runbook.py section-remove --id next-notes
python3 tools/runbook.py verify 2>&1 | grep -E "غير مربوط|نتيجة التحقق|متسق" | head -8; echo "exit=$?"