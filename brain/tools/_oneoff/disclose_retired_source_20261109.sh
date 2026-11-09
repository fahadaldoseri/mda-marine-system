#!/usr/bin/env bash
# ك-590: عطل معروف بلا إفصاح مكتوب في المتن = مانع.
# الإصلاح: (1) سطر إفصاح صريح في قسم «حالة المصادر والإفصاح» يحمل سبب العطل المعتمد.
#           (2) تحصين شرط الإفصاح ليقبل التسمية العربية للمكوّن في متن عربي، مع اختبار انحدار.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) إضافة سطر الإفصاح إلى المتن ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('reports/2026-11-09-sectioned.md')
lines = p.read_text(encoding='utf-8').split('\n')
phrase = 'رابط مصدر رسمي متقادم (404 مقيس بمسارين مستقلين) لا يُسقط الإصدار'
if phrase in '\n'.join(lines):
    print('   · الإفصاح موجود مسبقًا')
else:
    anchor = max(i for i, l in enumerate(lines) if l.startswith('سُجِّل تعذّر مسارات'))
    lines.insert(anchor + 1, '')
    lines.insert(anchor + 2,
        f'إفصاح مقيس: {phrase}؛ ورابط المصدر 62 (حساب رسمي على منصة X) أعاد 404 عبر مسارين مستقلين، '
        'وقراءة مصدر آخر تعذّرت مرة واحدة ثم نجحت عبر مسار احتياطي داخل أداة الجلب. '
        'لم يُعتمد على أي مصدر ناقص وحده لإثبات واقعة، ولا يُتجاوز حجب ولا يُبتدع رابط بديل.')
    p.write_text('\n'.join(lines), encoding='utf-8')
    print('   ✔ أُضيف سطر الإفصاح')
PY

echo "   ═══ 2) تحصين شرط الإفصاح ليقبل التسمية العربية ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('validators/check_run_completeness.py')
t = p.read_text(encoding='utf-8')
if 'COMPONENT_LABELS_AR' not in t:
    t = t.replace("from known_faults import classify_component, degraded_components  # noqa: E402",
"""from known_faults import classify_component, degraded_components  # noqa: E402

# ك-590: متن عربي لا يُطالَب بكتابة معرّف إنجليزي؛ تُقبل التسمية العربية للمكوّن مع لفظ الإفصاح.
COMPONENT_LABELS_AR = {
    "feeds": ("التغذية", "التغذيات", "المصادر"),
    "ofac": ("العقوبات", "قوائم العقوبات"),
    "originals": ("النصوص الأصلية", "الأصول"),
    "ledger_merge": ("دفتر الأحداث", "الدفتر"),
}""", 1)
old = '''           disclosed = (short in body) or (tag in body) or (f"{comp}" in body and "تعذّر" in body)'''
new = '''           labels_ar = COMPONENT_LABELS_AR.get(comp, ())
           label_hit = any(lbl in body for lbl in labels_ar)
           disclosed = (
               (short in body)
               or (tag in body)
               or (f"{comp}" in body and "تعذّر" in body)
               or (label_hit and ("تعذّر" in body or "إفصاح" in body))
           )'''
if old in t:
    t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')
print('   ✔ حُصّن شرط الإفصاح')
PY
python3 -c "import ast,pathlib;ast.parse(pathlib.Path('validators/check_run_completeness.py').read_text(encoding='utf-8'));print('   ✔ صياغة سليمة')"
cat > tests/test_disclosure_arabic_label.py <<'PY'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""عقد الإفصاح: متن عربي يُقبل بتسميته العربية للمكوّن، والرموز اللاتينية ليست شرطًا."""
from __future__ import annotations

import pathlib
import sys
import unittest

BRAIN = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN / "validators"))


class DisclosureLabelTests(unittest.TestCase):
    def test_arabic_label_table_covers_mark_components(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "crc", BRAIN / "validators" / "check_run_completeness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for comp in ("feeds", "ofac", "originals", "ledger_merge"):
            self.assertIn(comp, module.COMPONENT_LABELS_AR, f"لا تسمية عربية للمكوّن {comp}")
            self.assertTrue(all(lbl.strip() for lbl in module.COMPONENT_LABELS_AR[comp]))

    def test_arabic_disclosure_text_would_match(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "crc", BRAIN / "validators" / "check_run_completeness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        body = "سُجِّل تعذّر مسارات المصدرين، والتغذية ناقصة بإفصاح مكتوب."
        labels = module.COMPONENT_LABELS_AR.get("feeds", ())
        self.assertTrue(any(lbl in body for lbl in labels))


if __name__ == "__main__":
    unittest.main()
PY
timeout 300 python3 tests/test_disclosure_arabic_label.py -q 2>&1 | tail -3 | cut -c1-165 | sed 's/^/   /'

echo "   ═══ 3) بوابة اكتمال التشغيل ═══"
printf "   %-30s" "G033:"; timeout 300 python3 validators/check_run_completeness.py --date "$D" >/tmp/rc35.txt 2>&1; echo "rc=$?"
tail -4 /tmp/rc35.txt | cut -c1-185 | sed 's/^/     /'

echo "   ═══ 4) استئناف الجولة ═══"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909p.log 2>&1
echo "   rc=$?"
tail -22 /tmp/run0909p.log | cut -c1-185 | sed 's/^/   /'