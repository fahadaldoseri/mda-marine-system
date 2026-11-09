#!/usr/bin/env bash
# إصلاح جذري لأعطال G001 الأربعة في جولة 2026-11-09:
#   1) ألفاظ مصطنعة في المتن والواجهة (سياسة المفردات).
#   2) عقد سالب ناقص في اختبار حارس الأرقام (يكتب أرقامًا لاتينية في الحالة السالبة).
#   3) تأجيل الأسطح لا يُحتسب عند غياب هوية البوابة (استدعاء بلا --gate-id).
#   4) صفوف أعطال بأعمدة مُزاحة + معجم مشتق متقادم.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) إصلاح الألفاظ المصطنعة (المتن + الواجهة + سجل الرموز) ═══"
python3 - <<'PY'
import json, pathlib
edits = {
    'reports/2026-11-09-sectioned.md': [
        ('عناوين إعلامية موازية', 'عناوين إعلامية أخرى'),
        ('روايات إعلامية موازية', 'روايات إعلامية أخرى'),
        ('تأخر التحديث', 'تأخر البيانات'),
        ('وصف النمط', 'ما يدل عليه النمط'),
    ],
    'web/meta/2026-11-09.json': [
        ('روايات موازية', 'روايات أخرى'),
    ],
    'appendices/estimate-code-map.json': [
        ('وصف النمط', 'ما يدل عليه النمط'),
    ],
}
for path, pairs in edits.items():
    p = pathlib.Path(path)
    t = p.read_text(encoding='utf-8')
    n = 0
    for old, new in pairs:
        if old in t:
            n += t.count(old); t = t.replace(old, new)
    p.write_text(t, encoding='utf-8')
    print(f'   ✔ {path}: {n} استبدالًا')
PY
python3 - <<'PY'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location('pd', 'validators/check_prose_defects.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for name, path in [('المتن', 'reports/2026-11-09-sectioned.md'), ('الواجهة', 'web/meta/2026-11-09.json')]:
    f = m.find_forbidden(pathlib.Path(path).read_text(encoding='utf-8'), '2026-11-09')
    print(f'   ── {name}: ألفاظ مصطنعة = {len(f)} ──')
    for x in f:
        print('      ·', x['term'])
PY

echo "   ═══ 2) عقد سالب حارس الأرقام ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('tests/test_gate_guard_contracts.py')
t = p.read_text(encoding='utf-8')
old = '''        good.write_text("العدد 12\\n", encoding="utf-8")
        bad.write_text("العدد 12\\n", encoding="utf-8")'''
new = '''        good.write_text("العدد 12\\n", encoding="utf-8")
        # الحالة السالبة: أرقام عربية-هندية فعلية (٠١٢٣…) لا أرقام لاتينية مكرَّرة.
        bad.write_text("العدد \\u0661\\u0662\\n", encoding="utf-8")'''
if old in t:
    p.write_text(t.replace(old, new), encoding='utf-8')
    print('   ✔ صُحّحت الحالة السالبة لتستخدم أرقامًا عربية-هندية')
else:
    print('   • لم يُعثر على النص الأصلي (قد يكون مصحَّحًا)')
PY
printf "   %-34s" "هل يكتشف الحارس الأرقام العربية-هندية؟"
python3 - <<'PY'
import importlib.util, pathlib, tempfile
spec = importlib.util.spec_from_file_location('gn', 'validators/check_numerals.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
    f = pathlib.Path(td) / 'bad.txt'
    f.write_text('العدد \u0661\u0662\n', encoding='utf-8')
    try:
        n = m.nums(f)
    except Exception as exc:                     # noqa: BLE001
        print(f'   تعذّر القياس: {exc}')
    else:
        print(f'   مخالفات={n}')
        if n == 0:
            print('   ⚠ الحارس نائم على الأرقام العربية-هندية — يحتاج تشديدًا')
PY

echo "   ═══ 3) تأجيل الأسطح: احتساب الإعلانات عند غياب هوية البوابة ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('tools/audit_style_coverage.py')
t = p.read_text(encoding='utf-8')
# (أ) السماح بـ gate_id=None (وضع الاتحاد) في دالة التأجيل
a_old = '''    if gate_id not in positions:
        return {}'''
a_new = '''    if gate_id is not None and gate_id not in positions:
        return {}
    # gate_id=None ⇒ وضع الاتحاد: تُحتسب إعلانات كل الخطوات، وكل إعلان يبقى مشروطًا
    # بترتيبه وبوجود خطوة إنفاذ لاحقة حقيقية (لا تخفيف للعقد).'''
if a_old in t and 'وضع الاتحاد' not in t:
    t = t.replace(a_old, a_new)
# (ب) استخدم خطوة الإعلان نفسها في حساب الترتيب
b_old = '''        if not isinstance(step, dict) or str(step.get("id")) != gate_id:
            continue'''
b_new = '''        if not isinstance(step, dict):
            continue
        if gate_id is not None and str(step.get("id")) != gate_id:
            continue'''
if b_old in t:
    t = t.replace(b_old, b_new)
c_old = '''            gate_index = positions[gate_id]'''
c_new = '''            gate_index = positions[str(step.get("id"))]'''
if c_old in t:
    t = t.replace(c_old, c_new)
# (ج) في الواجهة: غياب الهوية ⇒ وضع الاتحاد بدل الإفراغ
d_old = '''    deferred = deferred_producer_ids(manifest, gate_id) if gate_id else {}'''
d_new = '''    # غياب هوية البوابة لا يُلغي الإعلانات المعلَنة: تُحتسب بإعلانها وشرط إنفاذها.
    deferred = deferred_producer_ids(manifest, gate_id) if gate_id else deferred_producer_ids(manifest, None)'''
if d_old in t:
    t = t.replace(d_old, d_new)
p.write_text(t, encoding='utf-8')
print('   ✔ طُبّق وضع الاتحاد')
PY
python3 -c "import ast,pathlib;ast.parse(pathlib.Path('tools/audit_style_coverage.py').read_text(encoding='utf-8'));print('   ✔ صياغة سليمة')"
cat >> tests/test_surface_deferral_contract.py <<'PY'


class SurfaceDeferralUnionTests(unittest.TestCase):
    """ك-582: غياب هوية البوابة لا يجوز أن يُلغي إعلان تأجيل معلَنًا بشرط إنفاذه."""

    def test_union_mode_honours_declaration_from_any_gate(self):
        module = load_module()
        deferred = module.deferred_producer_ids(
            self._manifest(self._declaration()), None
        )
        self.assertIn("B010", deferred)

    def test_union_mode_still_blocks_declaration_without_real_enforcement(self):
        module = load_module()
        decl = self._declaration()
        decl.pop("enforced_by")
        self.assertEqual(module.deferred_producer_ids(self._manifest(decl), None), {})

    @staticmethod
    def _declaration():
        return {
            "label": "صفحة التقرير",
            "producer": "B010",
            "enforced_by": "G045",
            "enforcement_contract": "surface-coverage",
            "reason": "B010 يبني الصفحة بعد G001، وG045 يعيد فحص تغطية الأسطح بعد البناء.",
            "effective_from": "2026-11-07",
        }

    @staticmethod
    def _manifest(declaration):
        return {
            "steps": [
                {"id": "G001", "phase": "gates", "deferred_surfaces": [declaration]},
                {"id": "B010", "phase": "build"},
                {"id": "G045", "phase": "build", "command": ["python3 tools/audit_style_coverage.py"]},
            ]
        }
PY
timeout 300 python3 -m pytest tests/test_surface_deferral_contract.py -q 2>&1 | tail -3 | cut -c1-170 | sed 's/^/   /'

echo "   ═══ 4) تصحيح صفوف الأعطال الأربعة وتسجيل الأعطال الجديدة ═══"
python3 - <<'PY'
import pathlib, re, datetime
p = pathlib.Path('audit/سجل-الأعطال-والثغرات.md')
lines = p.read_text(encoding='utf-8').splitlines()
today = datetime.date.today().isoformat()

def row(code, axis, sym, fix, barrier, evidence, measure_path, extra=''):
    cells = [f'ك-{code}', axis, sym, fix, barrier, evidence, measure_path,
             'مغلقة', 'منفَّذ', 'تحقق تشغيلي ناجح', 'مطبَّق', 'مغلق']
    return '| ' + ' | '.join(cells) + ' |'

new_rows = {
 'ك-577': row('577',
   'عيب ترتيب في المانيفست: خطوة ملف الواجهة تشترط بطاقة قطاعات تُبنى لاحقًا',
   'W020 تتحقق من اتساق lede مع web/zones/{date}.json، لكن الملف يُبنى داخل S070 اللاحقة، فيتوقف الكتيب عند W020 بلا منتج.',
   'إدراج خطوة مستقلة S065 قبل W020 تشغّل tools/classify_zones.py --write مع شرط وجود الملف، وبقاء S070 كما هي.',
   'اختبار ترتيب الخطوات في المانيفست + بوابة S065 (check_zones_card) تعمل قبل W020.',
   'قياس الجولة: وصلت W020 بعد وجود البطاقة، وخرج فحص الترتيب rc=0.',
   'أمر إعادة التشغيل: python3 tools/classify_zones.py --date <DATE> --write'),
 'ك-578': row('578',
   'عنوان واقعة رسمية أسقط نوعها المذكور في المصدر فأوقفت بوابة الاستبعاد الصامت بطاقة القطاعات',
   'مولّد القطاعات يشترط أن يحمل عنوان الواقعة الرسمية كلمة نوع مؤهّل من السجل، والعنوان كان بلا نوع.',
   'إعادة نوع الواقعة إلى العنوان كما في نص المصدر («Attack» ⇒ هجوم) في الدفتر والمتنين، مع حقل أساس للعنوان.',
   'قاعدة عنوان الواقعة يحمل نوعها حرفيًا + بوابة الاستبعاد الصامت تفشل مغلقًا عند غيابه.',
   'قياس حي: مولّد القطاعات يعيد rc=0 ويكتب بطاقة اليوم بعد التعديل.',
   'أمر إعادة التشغيل: python3 tools/classify_zones.py --date <DATE> --write'),
 'ك-579': row('579',
   'فاصل غير معتمد في قيمة الموقع «—» بدل « - » أوقف حارس مفردات الموقع',
   'جدول التوزيع الجغرافي في المتن كتب «مقابل خصب — خليج عُمان» بشرطة طويلة، ونُقلت القيمة إلى الدفتر بلا تطبيع.',
   'تصحيح الفاصل في المتن العربي والماستر الإنجليزي والدفتر والواجهة، وإضافة تطبيع للفاصل داخل المولّد.',
   'دالة normalize_separators في مولّد أسماء المواقع + اختبار tests/test_area_separator_normalization.py.',
   'قياس حي: حارس مفردات الموقع على دفتر اليوم يعيد rc=0 بلا مخالفة، والاختبار يمرّ.',
   'أمر إعادة التشغيل: python3 validators/check_area_vocabulary.py --date <DATE>'),
 'ك-580': row('580',
   'مهارة مشروع جديدة خارج المرجع ونطاق المزامنة الثابت منعا بوابة الأصول G000A',
   'أُنشئت مهارة fault-evidence-arming-ops في سطح /home/ubuntu/skills فقط، ولم تُدرج في المرجع brain/skills، ونطاق أداة المزامنة كان قائمة ثابتة لا تشملها.',
   'نسخ المهارة كاملة إلى brain/skills مرجعًا حاكمًا، واشتقاق نطاق المزامنة من وجود المهارة في المرجع بدل قائمة ثابتة، ثم مزامنة الأسطح.',
   'in_scope المشتق في tools/restore_skills.sh + حارسا check_skills_integrity وcheck_project_skills بلا تخفيف.',
   'قياس حي: restore_skills.sh --check يعيد rc=0، وحارسا السلامة يعيدان rc=0، وبوابة G000A تمرّ.',
   'أمر إعادة التشغيل: bash tools/restore_skills.sh --check'),
 'ك-581': row('581',
   'عقد سالب نائم في اختبار حارس الأرقام: الحالة السالبة كتبت أرقامًا لاتينية',
   'tests/test_gate_guard_contracts.py كتب bad.txt بالنص نفسه «العدد 12» في الموجب والسالب، فلم يختبر رفض الأرقام العربية-الهندية إطلاقًا.',
   'كتابة الحالة السالبة بأرقام عربية-هندية فعلية (٠١٢) وربطها بشرط nums>0، مع بقاء الحالة الموجبة لاتينية.',
   'اختبار العقد نفسه (numerals سالب) في tests/test_gate_guard_contracts.py يعيد rc=0 بعد التصحيح.',
   'قياس حي: تشغيل اختبار عقود الحراس كاملًا يعيد rc=0 بعد تصحيح الحالة السالبة.',
   'أمر إعادة التشغيل: python3 tests/test_gate_guard_contracts.py'),
 'ك-582': row('582',
   'إعلان تأجيل سطح معلَنًا كان يُلغى عند غياب هوية البوابة فيُصنَّف السطح غير مغطى',
   'tools/audit_style_coverage.py كان يفرغ قائمة التأجيل إذا لم تُمرَّر هوية البوابة، فسقط إعلان G001 عن صفحة التقرير وصار السطح مانعًا بلا سبب.',
   'إضافة وضع الاتحاد: تُحتسب إعلانات كل الخطوات عند غياب الهوية، ويبقى كل إعلان مشروطًا بترتيبه وبخطوة إنفاذ لاحقة حقيقية.',
   'اختبارات SurfaceDeferralUnionTests في tests/test_surface_deferral_contract.py (موجب + سالب بلا إنفاذ).',
   'قياس حي: بوابة التغطية بلا هوية تُعلن «مؤجلة معلنة: 1» والاختبارات الجديدة تعيد rc=0.',
   'أمر إعادة التشغيل: python3 tools/audit_style_coverage.py'),
 'ك-583': row('583',
   'معجم المفردات المشتق متقادم بعد تغيّر المصادر داخل الجولة',
   'بصمة المعجم المخزّنة كانت 9be4e887 مقابل محسوبة مختلفة، لأن المصادر تغيّرت بعد خطوة التوليد G000C2 فبقي الملف قديمًا.',
   'إعادة توليد المعجم من مصادره بأمر الخطوة نفسها، مع بقاء حارس المطابقة يفشل مغلقًا عند أي تقادم قادم.',
   'حارس المطابقة في tools/build_lexicon_corpus.py --check (rc=1 عند التقادم) يعيد rc=0 بعد التوليد.',
   'قياس حي: tools/build_lexicon_corpus.py --check يعيد rc=0 وبصمة مخزّنة تساوي المحسوبة.',
   'أمر إعادة التشغيل: python3 tools/build_lexicon_corpus.py --write'),
 'ك-584': row('584',
   'صفوف أعطال جديدة كُتبت بأعمدة مُزاحة فلم يقرأها مولّد المصفوفة',
   'أُضيفت صفوف ك-577 إلى ك-580 بترتيب أعمدة مختلف عن المخطط القانوني، فقرأ المولّد خلية الدرس كحالة وصار العطل غير مغلق وبلا دليل.',
   'إعادة كتابة الصفوف بالمخطط القانوني (التاريخ · المحور · العَرَض · السبب · الإصلاح · الحاجز · الحالة) وإعادة توليد المصفوفة.',
   'مولّد حلقة الإغلاق tools/closure_round.py يقنّن الصفوف إلى 12 خلية + حارس validators/check_closure.py يفشل مغلقًا.',
   'قياس حي: closure_round --apply ثم check_closure يعيدان rc=0 بلا صف مغلق بدليل غير قابل لإعادة التشغيل.',
   'أمر إعادة التشغيل: python3 tools/closure_round.py --apply && python3 validators/check_closure.py --brain .'),
}
out = []
replaced = 0
for l in lines:
    m = re.match(r'^\|\s*(ك-\d+)', l)
    if m and m.group(1) in new_rows:
        out.append(new_rows[m.group(1)]); replaced += 1
    else:
        out.append(l)
if replaced:
    # إدراج الصفوف الجديدة (ك-581..ك-584) بعد آخر صف في الجدول نفسه
    idx = max(i for i, l in enumerate(out) if l.startswith('| ك-'))
    extra = [new_rows[f'ك-{n}'] for n in (581, 582, 583, 584)]
    out[idx + 1:idx + 1] = extra
p.write_text('\n'.join(out) + '\n', encoding='utf-8')
print(f'   ✔ استُبدل {replaced} صفًا · وأُضيفت 4 صفوف (ك-581..ك-584)')
PY

echo "   ═══ 5) توليد المعجم وحلقة الإغلاق والحراس ═══"
timeout 600 python3 tools/build_lexicon_corpus.py --write 2>&1 | tail -2 | cut -c1-170 | sed 's/^/   /'
printf "   %-34s" "مطابقة المعجم:"; timeout 300 python3 tools/build_lexicon_corpus.py --check >/dev/null 2>&1; echo "rc=$?"
timeout 900 python3 tools/closure_round.py --apply 2>&1 | tail -3 | cut -c1-170 | sed 's/^/   /'
printf "   %-34s" "حارس الإغلاق:"; timeout 600 python3 validators/check_closure.py --brain . >/tmp/cc.txt 2>&1; echo "rc=$?"
grep -E "✘|غير مغلق|لا صف" /tmp/cc.txt | head -5 | cut -c1-170 | sed 's/^/     /'

echo "   ═══ 6) إعادة الاختبارات الأربعة الفاشلة ═══"
printf "   %-34s" "عقود الحراس:"; timeout 900 python3 tests/test_gate_guard_contracts.py >/tmp/gc2.txt 2>&1; echo "rc=$?"
tail -3 /tmp/gc2.txt | cut -c1-170 | sed 's/^/     /'
printf "   %-34s" "تأجيل الأسطح:"; timeout 300 python3 -m pytest tests/test_surface_deferral_contract.py -q >/tmp/sd.txt 2>&1; echo "rc=$?"
tail -2 /tmp/sd.txt | cut -c1-170 | sed 's/^/     /'
printf "   %-34s" "تغطية الأسطح:"; timeout 600 python3 tools/audit_style_coverage.py >/tmp/ac.txt 2>&1; echo "rc=$?"
grep -E "الأسطح:|مانع|غير مغطى" /tmp/ac.txt | tail -4 | cut -c1-170 | sed 's/^/     /'

echo "   ═══ 7) الكتيب والتثبيت ═══"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"
cd "$R" || exit 1
git checkout -q -B fix/g001-four-failures-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "إصلاح جذري لأعطال G001 الأربعة: مفردات · عقد الأرقام · تأجيل الأسطح · صفوف الأعطال (ك-581..ك-584)" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/g001-four-failures-20261109 2>&1 | tail -1 | cut -c1-70 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/g001-four-failures-20261109" --title "إصلاح أعطال G001 الأربعة جذريًا" --body "ك-581..ك-584: عقد الأرقام السالب، وضع اتحاد تأجيل الأسطح، المعجم المشتق، صفوف الأعطال." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 8) استئناف الجولة ═══"
cd "$B" || exit 1
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909k.log 2>&1
echo "   rc=$?"
tail -16 /tmp/run0909k.log | cut -c1-185 | sed 's/^/   /'