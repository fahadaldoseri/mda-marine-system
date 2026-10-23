#!/usr/bin/env bash
# اختبارات قبول محرّك الكتيب على نسخة مؤقتة من المشروع (لا الإنتاج).
# يقابل: 2 (إتمام قبل تشغيل) · 3 (إتمام بلا ملف/بملف أصغر) · 4 (فشل بوابة يوقف السلسلة)
#         5 (كتيب معدّل يدويًا) · 6 (ملف جديد في tools بلا ربط) · 7 (خطوة وكيل بلا برومت) · 9 (الاستئناف)
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
T="${TMPDIR:-/tmp}/rb-test-$$"
pass=0; fail=0
say() { if [ "$1" = ok ]; then echo "  ✔ $2"; pass=$((pass+1)); else echo "  ✘ $2"; fail=$((fail+1)); fi; }

rm -rf "$T"; mkdir -p "$T/tools" "$T/runbook/prompts" "$T/reports" "$T/docs"
cp "$B/tools/runbook.py" "$T/tools/"
cat > "$T/runbook/prompts/w.md" <<'EOF'
اكتب التقرير في reports/{date}-sectioned.md
EOF
cat > "$T/runbook/runbook.json" <<'EOF'
{"version":1,"ledger_dir":"logs/runbook","exempt":["reports/*","runbook/*","docs/*","tools/runbook.py"],
 "steps":[
  {"id":"S1","title":"تحضير","kind":"script","command":["bash","-lc","echo ok; rc=$?; exit $rc"],
   "assert":[{"type":"cmd","command":["bash","-lc","test -s logs/runbook/{date}/S1.log"]}],
   "links":{"rules":["ق1"],"files":["tools/runbook.py"],"folders":[],"gates":[],"tests":[]},"on_fail":"stop"},
  {"id":"S2","title":"كتابة","kind":"agent","prompt":"runbook/prompts/w.md","writes":["reports/{date}-sectioned.md"],
   "assert":[{"type":"min_bytes","path":"reports/{date}-sectioned.md","n":50}],
   "links":{"rules":["ق2"],"files":["runbook/prompts/w.md"],"folders":[],"gates":[],"tests":[]},"on_fail":"stop"},
  {"id":"S3","title":"بوابة تفشل","kind":"script","command":["bash","-lc","exit 2"],
   "assert":[{"type":"cmd","command":["bash","-lc","true"]}],
   "links":{"rules":["ق3"],"files":["tools/runbook.py"],"folders":[],"gates":[],"tests":[]},"on_fail":"stop"},
  {"id":"S4","title":"نشر","kind":"script","command":["bash","-lc","echo published; rc=$?; exit $rc"],
   "assert":[{"type":"cmd","command":["bash","-lc","test -s logs/runbook/{date}/S4.log"]}],
   "links":{"rules":["ق4"],"files":["tools/runbook.py"],"folders":[],"gates":[],"tests":[]},"on_fail":"stop"}],
 "sections":[]}
EOF
D=2026-01-01
cd "$T" && python3 tools/runbook.py handbook >/dev/null 2>&1

# 2) إتمام خطوة كتابة قبل أي تشغيل → رفض
python3 tools/runbook.py complete S2 --date $D >/dev/null 2>&1 && say bad "قبل التشغيل: قُبل (يجب الرفض)" || say ok "قبل التشغيل: رُفض"

# 9) تشغيل: يتوقف عند خطوة الوكيل (رمز 10)
python3 tools/runbook.py run --date $D >/dev/null 2>&1; rc=$?
[ "$rc" = 10 ] && say ok "التوقف عند خطوة الوكيل (رمز 10)" || say bad "رمز التوقف $rc لا 10"

# 3) إتمام بلا ملف → رفض
python3 tools/runbook.py complete S2 --date $D >/dev/null 2>&1 && say bad "بلا ملف: قُبل" || say ok "بلا ملف: رُفض"
# 3ب) بملف أصغر من الحد → رفض
echo صغير > reports/$D-sectioned.md
python3 tools/runbook.py complete S2 --date $D >/dev/null 2>&1 && say bad "ملف أصغر من الحد: قُبل" || say ok "ملف أصغر من الحد: رُفض"
# 3ج) بالحجم الكافي → قبول
python3 -c "open('reports/$D-sectioned.md','w').write('نص كافٍ ' * 20)"
python3 tools/runbook.py complete S2 --date $D >/dev/null 2>&1 && say ok "بملف مطابق: قُبل" || say bad "بملف مطابق: رُفض"

# 4) فشل بوابة يوقف السلسلة ولا ينفّذ ما بعدها
python3 tools/runbook.py run --date $D >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ] && say ok "فشل البوابة أوقف السلسلة (رمز 2)" || say bad "رمز فشل البوابة $rc"
grep -q '"step": "S4"' logs/runbook/$D.jsonl 2>/dev/null && say bad "نُفّذ النشر بعد فشل البوابة" || say ok "لم يُنفّذ النشر بعد فشل البوابة"

# 9ب) الاستئناف: بعد إصلاح البوابة يكمل من S3 دون إعادة S1/S2
python3 - <<'PY'
import json
from pathlib import Path
p = Path('runbook/runbook.json'); m = json.loads(p.read_text(encoding='utf-8'))
m['steps'][2]['command'] = ['bash', '-lc', 'echo fixed; rc=$?; exit $rc']
p.write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
PY
python3 tools/runbook.py handbook >/dev/null 2>&1
python3 tools/runbook.py run --date $D >/dev/null 2>&1
n1=$(grep -c '"step": "S1"' logs/runbook/$D.jsonl)
[ "$n1" = 1 ] && say ok "الاستئناف لم يُعِد الخطوات المكتملة (S1 مرة واحدة)" || say bad "الاستئناف أعاد خطوات (S1=$n1)"

# 5) تعديل الكتيب يدويًا → verify يفشل
echo "تعديل يدوي" >> docs/runbook.md
python3 tools/runbook.py verify >/dev/null 2>&1 && say bad "كتيب معدّل يدويًا: قُبل" || say ok "كتيب معدّل يدويًا: رُفض"
python3 tools/runbook.py handbook >/dev/null 2>&1

# 6) ملف جديد في tools بلا ربط → verify يفشل
echo "print(1)" > tools/أداة-جديدة.py
python3 tools/runbook.py verify >/dev/null 2>&1 && say bad "ملف غير مربوط: قُبل" || say ok "ملف غير مربوط في tools: رُفض"
rm tools/أداة-جديدة.py

# 7) خطوة وكيل بلا برومت → verify يفشل
python3 - <<'PY'
import json
from pathlib import Path
p = Path('runbook/runbook.json'); m = json.loads(p.read_text(encoding='utf-8'))
m['steps'][1]['prompt'] = ''
p.write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
PY
python3 tools/runbook.py handbook >/dev/null 2>&1
python3 tools/runbook.py verify >/dev/null 2>&1 && say bad "خطوة وكيل بلا برومت: قُبلت" || say ok "خطوة وكيل بلا برومت: رُفضت"
python3 - <<'PY'
import json
from pathlib import Path
p = Path('runbook/runbook.json'); m = json.loads(p.read_text(encoding='utf-8'))
m['steps'][1]['prompt'] = 'runbook/prompts/w.md'
p.write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
PY
python3 tools/runbook.py handbook >/dev/null 2>&1
python3 tools/runbook.py verify >/dev/null 2>&1 && say ok "verify نجح بعد إعادة الربط" || say bad "verify فشل بعد إعادة الربط"

rm -rf "$T"
echo "  الحصيلة: نجح $pass · فشل $fail"
[ "$fail" = 0 ]