#!/usr/bin/env python3
"""ك-146/ك-148: حصر عدّ المصادر في دالة قابلة للاختبار، وإصلاح مجمّع الاختبارات بعد إدراج بندي العدّ والعنوان اليتيم."""
import ast
import re
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')

# ── 1) دالة count_sources في فاحص التغذيات ──
p = B / 'tools/check_feeds.py'
t = p.read_text(encoding='utf-8')
FUNC = '''def count_sources(res, browser_only_nums=()):
    """عدّ المصادر لا الصفوف (البند هـ): مصدر نجح على مسار وفشل على آخر لا يُحسب مرتين.

    ك-146: كان المنطق مضمَّنًا في main بمتغيّر غير معرّف فانهار الفحص على الشبكة؛ صار دالة
    تُختبر بلا شبكة في tests/test_feed_counters.py.
    """
    attempted = {r['num'] for r in res} | set(browser_only_nums or ())
    ok_nums = {r['num'] for r in res if r['ok']}
    failed_nums = attempted - ok_nums
    assert len(attempted) == len(ok_nums) + len(failed_nums), (
        f"عدادات التغذيات غير متسقة: {len(attempted)} != {len(ok_nums)}+{len(failed_nums)}")
    return attempted, ok_nums, failed_nums


'''
if 'def count_sources(' not in t:
    t = t.replace('def main():', FUNC + 'def main():', 1)

inline_old = """    attempted = {r['num'] for r in res} | set(BROWSER_ONLY)
    ok_nums = {r['num'] for r in res if r['ok']}
    failed_nums = attempted - ok_nums
    n_src = len(attempted)
    n_ok = len(ok_nums)
    n_fail = len(failed_nums)"""
inline_new = """    attempted, ok_nums, failed_nums = count_sources(res, BROWSER_ONLY)
    n_src = len(attempted)
    n_ok = len(ok_nums)
    n_fail = len(failed_nums)"""
if inline_old in t:
    t = t.replace(inline_old, inline_new, 1)
p.write_text(t, encoding='utf-8')
ast.parse(t)
print('  ✔ count_sources مفصولة ومستدعاة في main')

# ── 2) اختبار العدّادات ──
(B / 'tests/test_feed_counters.py').write_text('''#!/usr/bin/env python3
"""ك-146: عدّ المصادر بلا شبكة — يثبت الثابت (مفحوصة = ناجحة + متعذّرة) وعدم الحساب المزدوج."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("cf", ROOT / 'tools/check_feeds.py')
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)

# مصدر واحد نجح على مسار وفشل على آخر (46) + مصدر فشل (10) + مصدر بمسار متصفحي (3)
res = [{"num": 46, "ok": True}, {"num": 46, "ok": False}, {"num": 10, "ok": False}, {"num": 3, "ok": True}]
a, o, f = cf.count_sources(res, {3, 9})
assert a == {46, 10, 3, 9}, a
assert o == {46, 3} and f == {10, 9}, (o, f)
assert len(a) == len(o) + len(f)
print(f"  · مفحوصة {len(a)} = ناجحة {len(o)} + متعذّرة {len(f)} · والحساب المزدوج ممتنع")
''', encoding='utf-8')
print('  ✔ tests/test_feed_counters.py')

# ── 3) إعادة بناء ذيل مجمّع الاختبارات بسطور سليمة ──
p = B / 'tests/run_checks.sh'
lines = p.read_text(encoding='utf-8').splitlines()
cut = next(i for i, l in enumerate(lines) if 'test_feed_counters' in l or 'test_orphan_rule' in l)
# نعود خطوة إلى ما قبل أول بند مكرر/معطوب
while cut > 0 and lines[cut - 1].strip().startswith('echo "1'):
    cut -= 1
if cut > 0 and lines[cut - 1].strip().startswith('python3 tests/test_'):
    cut -= 1
if cut > 0 and lines[cut - 1].strip().startswith('echo "1'):
    cut -= 1
head = lines[:cut]
TAIL = r'''
echo "9) عدّادات التغذيات (ك-146): تُحسب بعدد المصادر ولا تفقد مصدرًا"
python3 tests/test_feed_counters.py && ok "عدّادات التغذيات متسقة" || bad "عدّادات التغذيات غير متسقة"

echo "10) قاعدة العنوان اليتيم (ك-148): تكتشف عنوان ذيل الصفحة وتتجاهل التذييل"
python3 tests/test_orphan_rule.py && ok "قاعدة العنوان اليتيم صحيحة" || bad "قاعدة العنوان اليتيم لا تعمل"

echo "----- الحصيلة -----"
printf '  نجح: %s · فشل: %s\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
'''
p.write_text("\n".join(head).rstrip() + "\n" + TAIL.lstrip("\n"), encoding='utf-8')
print(f'  ✔ ذيل المجمّع أُعيد بناؤه ({len(head)} سطرًا + بندان + الحصيلة)')