#!/usr/bin/env bash
# ك-591: حارس المفردات المبسطة طابق «سند» داخل «تُسند» (مطابقة جزئية) وأسقط بوابة G036 بلا مخالفة حقيقية،
#        وكان يعرض البديل فارغًا لأن السجل الحاكم يستخدم الحقل plain لا alternative.
set -u
B=/home/ubuntu/mda-marine-system/brain
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) إصلاح المطابقة وعرض البديل ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('validators/check_vocabulary.py')
t = p.read_text(encoding='utf-8')
if '_AR_LETTER' not in t:
    t = t.replace('''VOCAB = B / "appendices" / "simplified-vocabulary.json"''',
'''VOCAB = B / "appendices" / "simplified-vocabulary.json"

# ك-591: مطابقة على حدود الكلمة العربية بعد إسقاط التشكيل والتطويل.
# لا تُطابق «سند» داخل «تُسند»، ولا تُعتبر لاحقة/سابقة كلمة قائمة بذاتها.
_AR_LETTER = "\\u0621-\\u064a\\u0671-\\u06d3"
_TASHKEEL = "\\u064b-\\u0652\\u0670\\u0640\\u06d6-\\u06dc\\u0640"


def _strip_tashkeel(value: str) -> str:
    import re as _re
    return _re.sub(f"[{_TASHKEEL}]", "", value or "")


def _word_hit(hard: str, text: str) -> bool:
    import re as _re
    hard_n = _strip_tashkeel(hard).strip()
    if not hard_n:
        return False
    pattern = f"(?<![{_AR_LETTER}]){_re.escape(hard_n)}(?![{_AR_LETTER}])"
    return _re.search(pattern, _strip_tashkeel(text)) is not None


def _alternative(it: dict) -> str:
    """البديل من السجل الحاكم: alternative/easy/simple أو الحقل المعتمد plain."""
    easy = it.get("alternative") or it.get("easy") or it.get("simple")
    if easy:
        return str(easy)
    plain = it.get("plain")
    if isinstance(plain, list):
        return "؛ ".join(str(x) for x in plain if str(x).strip())
    return str(plain or "")''', 1)
old = '''    for it in items:
        hard = it.get("as_written") or it.get("term") or it.get("hard") or ""
        easy = it.get("alternative") or it.get("easy") or it.get("simple") or ""
        if hard and hard in text:
            hits.append((hard, easy))'''
new = '''    for it in items:
        hard = it.get("as_written") or it.get("term") or it.get("hard") or ""
        easy = _alternative(it)
        if hard and _word_hit(hard, text):
            hits.append((hard, easy))'''
if old in t:
    t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')
print('   ✔ صُلح الحارس')
PY
python3 -c "import ast,pathlib;ast.parse(pathlib.Path('validators/check_vocabulary.py').read_text(encoding='utf-8'));print('   ✔ صياغة سليمة')"

echo "   ═══ 2) اختبار انحدار موجب وسالب ═══"
cat > tests/test_vocabulary_word_boundary.py <<'PY'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ك-591: حدود الكلمة العربية — «سند» لا تُطابق داخل «تُسند»، والبديل يُقرأ من plain."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

BRAIN = pathlib.Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "cv", BRAIN / "validators" / "check_vocabulary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WordBoundaryTests(unittest.TestCase):
    def test_verb_containing_term_is_not_a_hit(self):
        self.assertFalse(_module()._word_hit("سند", "لا تُسند المصادر الإعلامية واقعةً وحدها."))

    def test_standalone_term_is_a_hit(self):
        self.assertTrue(_module()._word_hit("سند", "وقد صار سندًا للواقعة."))

    def test_plain_field_supplies_alternative(self):
        self.assertEqual(
            _module()._alternative({"term": "سند", "plain": ["مصدر التقدير", "الأساس"]}),
            "مصدر التقدير؛ الأساس")


if __name__ == "__main__":
    unittest.main()
PY
timeout 300 python3 tests/test_vocabulary_word_boundary.py -q 2>&1 | tail -3 | cut -c1-165 | sed 's/^/   /'
printf "   %-30s" "حارس المفردات على متن اليوم:"; timeout 300 python3 validators/check_vocabulary.py --md reports/2026-11-09-sectioned.md >/tmp/vc.txt 2>&1; echo "rc=$?"
tail -2 /tmp/vc.txt | cut -c1-175 | sed 's/^/     /'

echo "   ═══ 3) استئناف الجولة ═══"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909r.log 2>&1
echo "   rc=$?"
tail -20 /tmp/run0909r.log | cut -c1-185 | sed 's/^/   /'