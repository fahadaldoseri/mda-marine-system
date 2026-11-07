#!/usr/bin/env python3
"""ك-146: عدّادات التغذيات كانت مضمَّنة في main بمتغيّر غير معرّف (browser_only) ⇒ انهيار الفحص على الشبكة."""
import ast
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')

HELPER = '''
def counters(res, browser_only_nums=None):
    """ثابت العدّ (البند هـ): مفحوصة = ناجحة + متعذّرة، والمسارات الثلاثة تُحسب كلها.

    ك-146: كان المنطق مضمَّنًا في main بمتغيّر غير معرّف (browser_only) فانهار الفحص على
    الشبكة. فُصل هنا ليُختبر بلا شبكة، ويُثبت أن المجموع لا يفقد مصدرًا.
    """
    extra = set(browser_only_nums or BROWSER_ONLY or ())
    attempted = {r['num'] for r in res} | extra
    ok_nums = {r['num'] for r in res if r['ok']}
    failed_nums = attempted - ok_nums
    ok = [r for r in res if r['ok']]
    failed = [r for r in res if not r['ok'] and r['num'] in failed_nums]
    assert len(attempted) == len(ok_nums) + len(failed_nums), \\
        f"عدادات التغذيات غير متسقة: {len(attempted)} != {len(ok_nums)}+{len(failed_nums)}"
    via_browser = {r['num'] for r in res if 'browser' in str(r.get('via', '')).lower()}
    return attempted, ok_nums, failed_nums, ok, failed, sorted(via_browser | extra)


'''

p = B / 'tools/check_feeds.py'
t = p.read_text(encoding='utf-8')
if 'def counters(' not in t:
    t = t.replace('def main():', HELPER + 'def main():', 1)
if "attempted = {r['num'] for r in res}" in t:
    start = t.index("    attempted = {r")
    end = t.index("    n_src = len(attempted)")
    t = t[:start] + "    attempted, ok_nums, failed_nums, ok, failed, browser_only = counters(res, set(BROWSER_ONLY))\n" + t[end:]
t = t.replace("'browser_only': sorted({r['num'] for r in browser_only}),", "'browser_only': browser_only,")
p.write_text(t, encoding='utf-8')
ast.parse(t)
print("  ✔ ك-146: دالة counters مفصولة · main يستدعيها · ولا متغيّر غير معرّف")

TEST = '''
echo "9) عدّادات التغذيات (ك-146): دالة العدّ تعمل بلا شبكة ولا تفقد مصدرًا"
python3 tests/test_feed_counters.py && ok "عدّادات التغذيات متسقة ومختبرة" || bad "عدّادات التغذيات غير متسقة"
'''
p = B / 'tests/run_checks.sh'
s = p.read_text(encoding='utf-8')
if 'test_feed_counters' not in s:
    p.write_text(s.rstrip() + "\n" + TEST, encoding='utf-8')
    print("  ✔ اختبار العدّادات أُدرج في tests/run_checks.sh (بند 9)")

(B / 'tests/test_feed_counters.py').write_text('''#!/usr/bin/env python3
"""ك-146: اختبار عدّادات التغذيات بلا شبكة — يثبت الثابت وعدم فقد أي مصدر."""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
spec = importlib.util.spec_from_file_location("cf", Path(__file__).resolve().parent.parent / 'tools/check_feeds.py')
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)

res = [{"num": 1, "ok": True, "via": "primary"},
       {"num": 2, "ok": False, "via": "primary"},
       {"num": 3, "ok": True, "via": "browser"}]
a, o, f, ok, failed, bo = cf.counters(res, {4})
assert len(a) == 4 and o == {1, 3} and f == {2, 4}, (a, o, f)
assert bo == [3, 4] and len(ok) == 2 and len(failed) == 1
assert len(res) + 1 == len(a), "المسارات الثلاثة لا تُحسب كلها"
print(f"  · مفحوصة {len(a)} = ناجحة {len(o)} + متعذّرة {len(f)} · المسارات المتصفحية {bo}")
''', encoding='utf-8')
print("  ✔ tests/test_feed_counters.py")