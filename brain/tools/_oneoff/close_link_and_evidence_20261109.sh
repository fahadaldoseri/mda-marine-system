#!/usr/bin/env bash
# حلقة إتمام: تشديد شرط الإغلاق على النجاح فقط، ثم دفعة أدلة D2، ثم قياس الأثر.
set -u
cd /home/ubuntu/mda-marine-system/brain || exit 1

echo "   ═══ 1) تشديد شرط الإغلاق (إزاحة صحيحة) ═══"
python3 - <<'PY'
import pathlib, re
p = pathlib.Path('tools/closure_round.py')
t = p.read_text(encoding='utf-8')
if 'SUCCESS = re.compile' not in t:
    m = re.search(r'^(\s*)OUTCOME = re\.compile\(', t, re.M)
    assert m, 'لم يُعثر على سطر OUTCOME'
    ind = m.group(1)
    add = (f"{ind}SUCCESS = re.compile(r'(?i:\\brc\\s*=\\s*0\\b)|خرج\\s*0|رمز\\s*0|"
           f"فاشل\\s*0|صفر فاشل|بصمة\\s*[0-9a-f]{{6,}}')\n")
    t = t[:m.start()] + add + t[m.start():]
old = "if f_fix == 'منفَّذ' and f_bar in ('مطبَّق', 'فعّال') and f_ver == 'تحقق تشغيلي ناجح':"
new = ("if f_fix == 'منفَّذ' and f_bar in ('مطبَّق', 'فعّال') "
       "and f_ver == 'تحقق تشغيلي ناجح' and SUCCESS.search(blob):")
assert t.count(old) == 1, f'عدد المواضع {t.count(old)}'
t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('   ✔ الإغلاق صار يشترط نجاحًا صريحًا')
PY

echo "   ═══ 2) اختبار خط الربط (RED ثم GREEN) ═══"
APPLY_TOOL=/tmp/old_apply_tool.py timeout 300 python3 -m pytest tests/test_batch_result_row_link.py -q 2>&1 | tail -1 | cut -c1-95 | sed 's/^/   RED: /'
timeout 300 python3 -m pytest tests/test_batch_result_row_link.py -q 2>&1 | tail -1 | cut -c1-95 | sed 's/^/   GREEN: /'

echo "   ═══ 3) دفعة أدلة D2 ═══"
timeout 1800 python3 tools/measurement_batch_runner.py --root . --batch D2 --timeout 120 --write-every 5 2>&1 | tail -8 | cut -c1-150 | sed 's/^/   /'

echo "   ═══ 4) تطبيق النتائج وإعادة الاشتقاق ═══"
timeout 300 python3 tools/apply_batch_results.py --root . --apply 2>&1 | grep -E "مطبَّق|تعبئة" | head -3 | cut -c1-130 | sed 's/^/   /'
timeout 600 python3 tools/closure_round.py --apply 2>&1 | grep -E "الحالة التشغيلية" | cut -c1-140 | sed 's/^/   /'

echo "   ═══ 5) الحارس والميزانية ═══"
timeout 300 python3 validators/check_closure.py --brain . 2>&1 | tail -3 | cut -c1-140 | sed 's/^/   /'
timeout 300 python3 validators/check_exceptions_burndown.py 2>&1 | tail -2 | cut -c1-140 | sed 's/^/   /'
echo "   ═══ 6) الصفوف بلا أمر دليل ═══"
python3 -c "
import json,pathlib
p=pathlib.Path('audit/measurements/batches/no-command-rows.json')
print('   بلا أمر:', len(json.loads(p.read_text(encoding='utf-8')).get('rows',[])))
"