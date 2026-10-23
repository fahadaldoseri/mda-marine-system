#!/usr/bin/env bash
# اختبارات مراجعة صاحب القرار الثانية (23 أكتوبر 2026) — بنود: أ · ب · ج · د · هـ · ز
set -u
B="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
D="${1:-2026-10-23}"
cd "$B" || exit 1
pass=0; fail=0
ok()   { echo "  ✔ $1"; pass=$((pass+1)); }
bad()  { echo "  ✘ $1"; fail=$((fail+1)); }

echo "── (ب) ربط الحارس الموحّد: تحليل شيفرة (ast) لا بحث نصي"
python3 - <<'PY'
import ast, sys
from pathlib import Path
bad, good = [], 0
for p in sorted(Path('validators').glob('*.py')):
    if p.name == '_guard.py':
        continue
    src = p.read_text(encoding='utf-8')
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        bad.append(f"{p.name}: خطأ صياغة {e}"); continue
    if not any(isinstance(n, ast.If) and "__main__" in ast.dump(n.test) for n in tree.body):
        continue                                    # لا كتلة تنفيذ: لا يُشترط
    ok = False
    for n in tree.body:
        if not (isinstance(n, ast.If) and "__main__" in ast.dump(n.test)):
            continue
        for sub in ast.walk(n):
            # استيراد run من _guard فعلًا
            if isinstance(sub, ast.ImportFrom) and (sub.module or '').endswith('_guard'):
                if any(a.name == 'run' for a in sub.names):
                    # ثم نداء run(...) داخل الكتلة
                    ok = any(isinstance(c, ast.Call) and getattr(c.func, 'id', '') == 'run'
                             for c in ast.walk(n))
    if ok:
        good += 1
    else:
        bad.append(f"{p.name}: كتلة التنفيذ لا تستدعي run من _guard فعليًا")
print('مخالفات:', bad)
print(f'ملفات موصولة فعليًا: {good}')
sys.exit(1 if bad else 0)
PY
if [ $? -ne 0 ]; then bad "ملف مدقق غير موصول بالحارس"; else ok "كل المدققات موصولة بالحارس (ast)"; fi
# إثبات أن الاختبار يكشف ملفًا غير موصول (حالة مصطنعة) + ملفًا يذكر الحارس في تعليق فقط
cat > validators/_tmp_nowire.py <<'PY'
#!/usr/bin/env python3
# سنربطه بـ _guard لاحقًا (تعليق لا يستدعي الحارس)
import sys
def main():
    return 0
if __name__ == "__main__":
    sys.exit(main())
PY
python3 - <<'PY'
import ast, sys
from pathlib import Path
src = Path('validators/_tmp_nowire.py').read_text(encoding='utf-8')
tree = ast.parse(src)
ok = False
for n in tree.body:
    if isinstance(n, ast.If) and "__main__" in ast.dump(n.test):
        for sub in ast.walk(n):
            if isinstance(sub, ast.ImportFrom) and (sub.module or '').endswith('_guard') \
               and any(a.name == 'run' for a in sub.names):
                ok = any(isinstance(c, ast.Call) and getattr(c.func, 'id', '') == 'run' for c in ast.walk(n))
print('  · الحالة المصطنعة (تعليق فقط):', 'كُشفت ✘' if not ok else 'مرّت خطأً')
sys.exit(0 if not ok else 2)
PY
if [ $? -eq 0 ]; then ok "الاختبار يكشف التعليق الكاذب (استيراد لم يحدث)"; else bad "الاختبار لم يكشف التعليق الكاذب"; fi
rm -f validators/_tmp_nowire.py

echo "── (د) حصر الاستثناءات العامة: لا موقع جديد بلا تصنيف"
python3 - <<'PY' && ok "لا استثناء عام جديد خارج القائمة المقبولة" || bad "استثناء عام جديد خارج القائمة المقبولة"
import json, subprocess, sys
from pathlib import Path
rows = json.loads(subprocess.run(['python3','tools/audit_broad_excepts.py','--json'],
                                 capture_output=True, text=True).stdout)
acc = {x['site'] for x in json.loads(Path('appendices/broad-excepts-baseline.json').read_text(encoding='utf-8'))['accepted']}
new = [f"{r['file']}:{r['line']}" for r in rows if f"{r['file']}:{r['line']}" not in acc]
print('جديدة:', new)
sys.exit(1 if new else 0)
PY

echo "── (د) حقن خطأ: المدقق لا يُخرج نجاحًا ولا تحذيرًا"
printf '{"date": "غير صالح"' > /tmp/inj-meta.json
python3 validators/validate_report.py /tmp/inj-meta.json >/tmp/inj.log 2>&1; rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ]; then ok "حقن خطأ ⇒ رمز $rc (فشل مغلق)"; else bad "حقن خطأ أعطى رمز $rc (يجب ألا يكون 0 أو 1)"; fi

echo "── (هـ) الثابت: مفحوصة = ناجحة + متعذّرة"
python3 - <<'PY' && ok "الثابت يُكشف عند اختلافه" || bad "الثابت لا يُكشف"
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('sc', 'tools/source_counts.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
bad = m.check('2026-10-23', {'date':'2026-10-23','approved':62,'checked':35,'ok':33,'failed':3,
                             'failed_names':[],'reasons':{}})
hit = any('الثابت' in x for x in bad)
print('النتيجة:', bad[:2])
sys.exit(0 if hit else 1)
PY

echo "── (ز) الإصلاح الآلي: لا مساس بالنحو ولا عبور لنهايات الأسطر"
cat > /tmp/fixture-prose.md <<'MD'
## قسم
السفن تُوسم إعلاميًا بأنها خطر.
النافذة الزمنية غير صحيحة.
سطر ينتهي بنقطة
، ثم فاصلة في بداية السطر التالي.
- **نفّذوا** — واحد.
- **نفّذوا** — اثنان.
- **نفّذوا** — ثلاثة.
MD
python3 tools/repair_prose.py --date 2026-10-23 --dry-run >/tmp/rp.log 2>&1
python3 - <<'PY' && ok "الإصلاح الآلي لا يعبر الأسطر ولا يستبدل ما يتأثر بالنحو" || bad "الإصلاح الآلي خالف القاعدة"
import re, sys
from pathlib import Path
txt = Path('/tmp/fixture-prose.md').read_text(encoding='utf-8')
sys.path.insert(0, 'tools')
import repair_prose as rp
rules = rp.load_rules()
out, _ = rp.fix_punctuation(txt)
bad = []
if re.search(r"\.\s*،", out): bad.append('عبور نهاية سطر في الترقيم')
out2, _ = rp.fix_fixed_terms(out, rules)
if 'بأنها بأنها' in out2: bad.append('استبدال يُنتج «بأنها بأنها»')
if 'المحددة' in out2: bad.append('استبدال يُنتج «المحددة الزمنية» (بديل مركّب)')
if 'الفترة الزمنية' not in out2: bad.append('لم يُستبدل «النافذة» بـ«الفترة»')
if 'تُوسم إعلاميًا' not in out2: bad.append('استُبدل لفظ يتأثر بالنحو')
print('المخالفات:', bad)
sys.exit(1 if bad else 0)
PY
if python3 tools/repair_prose.py --date 2026-10-23 --md /tmp/fixture-prose.md --dry-run >/tmp/rp2.log 2>&1; then bad "تكرار القالب لم يوقف التسليم"; else ok "تكرار القالب يوقف التسليم (رمز 2)"; fi

echo "── (أ) حارس بصمة النص: اختلاف النص بعد البناء = منع"
python3 tools/text_hash_guard.py --date "$D" --stage record >/dev/null 2>&1
cp "reports/$D-sectioned.md" /tmp/md-backup.md
printf '\nسطر اختباري\n' >> "reports/$D-sectioned.md"
python3 tools/text_hash_guard.py --date "$D" --stage verify >/tmp/thg.log 2>&1; rc=$?
cp /tmp/md-backup.md "reports/$D-sectioned.md"
if [ "$rc" -eq 70 ]; then ok "اختلاف النص ⇒ منع (70)"; else bad "اختلاف النص لم يمنع (رمز $rc)"; fi
python3 tools/text_hash_guard.py --date "$D" --stage record >/dev/null 2>&1
if python3 tools/text_hash_guard.py --date "$D" --stage verify >/dev/null 2>&1; then
  bad "مخرجات أقدم من النص لم تُمنع (يجب إعادة البناء)"
else ok "المخرجات الأقدم من النص تمنع حتى يُعاد البناء"; fi
S="${SITE_DIR:-$B/../seawatch}/dist"
touch "$S/reports/$D.html" "$S/reports/pdf/$D.pdf" "reports/docx/التقرير-اليومي-$D-طبق-الأصل.docx" 2>/dev/null
python3 tools/text_hash_guard.py --date "$D" --stage verify >/dev/null 2>&1 && ok "بعد إعادة البناء يمرّ الحارس" || bad "بعد إعادة البناء لا يمرّ"

echo "── (ج) عنوان يتيم في PDF اصطناعي"
python3 - <<'PY' >/tmp/fixture.log 2>&1
from pathlib import Path
html = """<html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>
body{font-family:serif;font-size:12pt}h2{font-size:16pt;margin:0 0 6mm}
</style></head><body>
<div style="height:252mm">متن يملأ الورقة الأولى كاملة حتى آخرها بلا عنوان يتيم.</div>
<h2>عنوان يتيم في آخر الورقة</h2>
<div style="page-break-before:always">الصفحة الثانية: محتوى.</div>
</body></html>"""
Path('/tmp/orphan.html').write_text(html, encoding='utf-8')
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page()
    pg.goto('file:///tmp/orphan.html')
    pg.pdf(path='/tmp/orphan.pdf', format='A4', print_background=True)
    b.close()
print('أُنتج /tmp/orphan.pdf')
PY
if python3 validators/check_pdf_format.py --pdf /tmp/orphan.pdf --date "$D" >/tmp/orphan.log 2>&1; then
  bad "العنوان اليتيم لم يُمنع"
else
  if grep -q "يتيم" /tmp/orphan.log; then ok "العنوان اليتيم يمنع (وذُكر في المخرج)"; else bad "منع بلا ذكر العنوان اليتيم"; fi
fi

echo "── الحصيلة: نجح $pass · فشل $fail"
[ "$fail" -eq 0 ]
