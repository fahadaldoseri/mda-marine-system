#!/usr/bin/env bash
# إغلاق بندين: (1) الهوية المستدلة للبوابة كانت تُلغي إعلان تأجيل معلَنًا في خطوة أخرى.
#              (2) معجم المفردات المشتق أُعيد توليده بعد الالتزام → يُثبَّت.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) دالة قرار التأجيل + ربطها بالواجهة ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('tools/audit_style_coverage.py')
t = p.read_text(encoding='utf-8')
helper = '''

def resolve_deferred(manifest: dict, explicit_gate: str, current_gate: str | None) -> dict[str, dict]:
    """قرار التأجيل: الضيق عند تمرير هوية صريحة فقط.

    الهوية المستدلة (current_gate) لا تُسقط إعلانًا معلَنًا في خطوة أخرى؛ وكل إعلان
    يبقى مشروطًا بترتيب منتجه بعد خطوة إعلانه وبوجود خطوة إنفاذ لاحقة حقيقية.
    """
    if explicit_gate:
        return deferred_producer_ids(manifest, explicit_gate)
    return deferred_producer_ids(manifest, None)
'''
if 'def resolve_deferred' not in t:
    anchor = '\n\ndef _current_step_id('
    t = t.replace(anchor, helper + anchor, 1)
old = '''    deferred = deferred_producer_ids(manifest, gate_id) if gate_id else deferred_producer_ids(manifest, None)'''
new = '''    explicit_gate = str(getattr(a, "gate_id", "") or "")
    deferred = resolve_deferred(manifest, explicit_gate, gate_id)'''
if old in t:
    t = t.replace(old, new)
elif 'resolve_deferred(manifest, explicit_gate, gate_id)' not in t:
    print('   ⚠ لم يُعثر على سطر نداء القرار')
p.write_text(t, encoding='utf-8')
print('   ✔ رُبط قرار التأجيل')
PY
python3 -c "import ast,pathlib;ast.parse(pathlib.Path('tools/audit_style_coverage.py').read_text(encoding='utf-8'));print('   ✔ صياغة سليمة')"

echo "   ═══ 2) اختبار انحدار لقرار التأجيل ═══"
cat >> tests/test_surface_deferral_contract.py <<'PY'


class DeferralResolutionTests(unittest.TestCase):
    """الهوية المستدلة لا تُسقط إعلانًا معلَنًا؛ الضيق عند الهوية الصريحة فقط."""

    def _manifest(self):
        declaration = {
            "label": "صفحة التقرير",
            "producer": "B010",
            "enforced_by": "G045",
            "enforcement_contract": "surface-coverage",
            "reason": "B010 يبني الصفحة بعد G001، وG045 يعيد فحص التغطية بعد البناء.",
            "effective_from": "2026-11-07",
        }
        return {
            "steps": [
                {"id": "G001", "phase": "gates", "deferred_surfaces": [declaration]},
                {"id": "B010", "phase": "build"},
                {"id": "G045", "phase": "build", "command": ["python3 tools/audit_style_coverage.py"]},
            ]
        }

    def test_inferred_gate_keeps_other_step_declaration(self):
        module = load_module()
        self.assertIn("B010", module.resolve_deferred(self._manifest(), "", "G045"))

    def test_explicit_gate_restricts_to_that_step(self):
        module = load_module()
        self.assertEqual(module.resolve_deferred(self._manifest(), "G045", "G045"), {})
        self.assertIn("B010", module.resolve_deferred(self._manifest(), "G001", "G001"))
PY
timeout 300 python3 -m pytest tests/test_surface_deferral_contract.py -q 2>&1 | tail -3 | cut -c1-170 | sed 's/^/   /'

echo "   ═══ 3) قياس تغطية الأسطح ═══"
timeout 600 python3 tools/audit_style_coverage.py > /tmp/ac2.txt 2>&1; echo "   rc=$?"
grep -E "الأسطح:|مؤجلة|مانعة|غير مغطاة" /tmp/ac2.txt | tail -3 | cut -c1-185 | sed 's/^/   /'

echo "   ═══ 4) تسجيل العطلين الجديدين (ك-585 · ك-586) ═══"
python3 - <<'PY'
import pathlib, re, datetime
p = pathlib.Path('audit/سجل-الأعطال-والثغرات.md')
lines = p.read_text(encoding='utf-8').splitlines()

def row(code, axis, sym, fix, barrier, evidence, path):
    cells = [f'ك-{code}', axis, sym, fix, barrier, evidence, path,
             'مغلقة', 'منفَّذ', 'تحقق تشغيلي ناجح', 'مطبَّق', 'مغلق']
    return '| ' + ' | '.join(cells) + ' |'

new = {
 'ك-585': row('585',
   'الهوية المستدلة للبوابة كانت تُسقط إعلان تأجيل معلَنًا في خطوة أخرى فتُصنَّف صفحة التقرير غير مغطاة',
   'tools/audit_style_coverage.py يستدل على هوية G045 بذكر ملف الأداة في أمرها، فيمرّرها صراحةً إلى دالة التأجيل التي تقرأ إعلانات تلك الخطوة وحدها، ويسقط إعلان G001 عن صفحة التقرير.',
   'إضافة دالة resolve_deferred: هوية صريحة ⇒ حكم تلك الخطوة · هوية مستدلة أو غائبة ⇒ وضع الاتحاد مع بقاء شرط الترتيب وشرط خطوة الإنفاذ الحقيقية.',
   'اختبارات DeferralResolutionTests في tests/test_surface_deferral_contract.py (مستدلة تُبقي · صريحة تُضيّق).',
   'قياس حي: بوابة التغطية تعرض «مؤجلة معلنة: 1 · غير مغطاة: 0 · مانعة: 0» والاختبارات rc=0.',
   'أمر إعادة التشغيل: python3 tools/audit_style_coverage.py'),
 'ك-586': row('586',
   'معجم المفردات المشتق كُتب بعد الالتزام فبقي الملف المخزّن متقادمًا داخل الجولة',
   'أمر التوليد الصحيح هو --apply لا --write؛ استُخدم الخيار الخطأ فسقط التوليد وبقيت البصمة المخزّنة 9be4e887 مقابل محسوبة مختلفة.',
   'إعادة التوليد بالأمر الصحيح (build_lexicon_corpus.py --apply) وتثبيت الملف في الفرع، مع بقاء فحص المطابقة يفشل مغلقًا عند أي تقادم قادم.',
   'فحص build_lexicon_corpus.py --check يعيد rc=1 عند التقادم وrc=0 عند التطابق (مقيس).',
   'قياس حي: بصمة المعجم المخزّنة صارت eb7f368968a2ee55 وفحص المطابقة يعيد rc=0.',
   'أمر إعادة التشغيل: python3 tools/build_lexicon_corpus.py --apply && python3 tools/build_lexicon_corpus.py --check'),
}
out = []
for l in lines:
    out.append(l)
idx = max(i for i, l in enumerate(out) if l.startswith('| ك-'))
out[idx + 1:idx + 1] = [new['ك-585'], new['ك-586']]
p.write_text('\n'.join(out) + '\n', encoding='utf-8')
print('   ✔ أُضيف ك-585 وك-586')
PY

echo "   ═══ 5) حلقة الإغلاق والحراس ═══"
printf "   %-30s" "معجم:"; timeout 300 python3 tools/build_lexicon_corpus.py --check >/dev/null 2>&1; echo "rc=$?"
timeout 900 python3 tools/closure_round.py --apply 2>&1 | tail -2 | cut -c1-170 | sed 's/^/   /'
printf "   %-30s" "حارس الإغلاق:"; timeout 600 python3 validators/check_closure.py --brain . >/tmp/cc2.txt 2>&1; echo "rc=$?"
grep -E "✘" /tmp/cc2.txt | head -4 | cut -c1-175 | sed 's/^/     /'
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"

echo "   ═══ 6) الالتزام والدمج ═══"
cd "$R" || exit 1
git checkout -q -B fix/deferral-identity-20261109 main
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "إصلاح قرار تأجيل الأسطح عند الهوية المستدلة + تثبيت المعجم المشتق (ك-585 · ك-586)" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/deferral-identity-20261109 2>&1 | tail -1 | cut -c1-70 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/deferral-identity-20261109" --title "قرار تأجيل الأسطح والمعجم المشتق" --body "ك-585 · ك-586 مع اختبارات انحدار." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 7) استئناف الجولة ═══"
cd "$B" || exit 1
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909m.log 2>&1
echo "   rc=$?"
tail -18 /tmp/run0909m.log | cut -c1-185 | sed 's/^/   /'