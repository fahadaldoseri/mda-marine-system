#!/usr/bin/env python3
"""إصلاح المصلح المفسد وتوحيد قائمة الكلمات — مراجعة 23 أكتوبر 2026، ثالثًا-1/5/6."""
import ast
import json
import re
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')

# ── 1) قائمة واحدة مشتركة
src = (B / 'validators/check_prose_defects.py').read_text(encoding='utf-8')
block = src.split('DUPLICATE_LETTER_WHITELIST = {')[1].split('}')[0]
wl = sorted({w.strip().strip('",') for w in block.replace('\n', ',').split(',') if w.strip()})
shared = {
    "source": "قائمة واحدة يقرأها المصلح والكاشف — لا تُكرَّر في مكانين (مراجعة 23 أكتوبر 2026 ثالثًا-1)",
    "whitelist": wl,
    "forbidden_fixed": ["ةة"],
    "forbidden_repeat_min": 3,
    "note": "«دد» و«يي» و«وو» و«اا» تكرارات صحيحة في كلمات عربية شائعة، فأُخرجت من الإصلاح الآلي نهائيًا.",
}
(B / 'appendices/doubled-letters.json').write_text(json.dumps(shared, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
print(f"  ✔ appendices/doubled-letters.json · {len(wl)} كلمة في القائمة")

# ── 2) الكاشف يقرأ القائمة المشتركة
p = B / 'validators/check_prose_defects.py'
t = p.read_text(encoding='utf-8')
t = re.sub(r"DUPLICATE_LETTER_WHITELIST = \{.*?\n\}",
           'DUPLICATE_LETTER_WHITELIST = set(json.loads((Path(__file__).resolve().parent.parent / "appendices" / "doubled-letters.json").read_text(encoding="utf-8"))["whitelist"])',
           t, count=1, flags=re.S)
if 'import json' not in t:
    t = t.replace('import re', 'import json\nimport re', 1)
p.write_text(t, encoding='utf-8')
ast.parse(t)
print("  ✔ الكاشف يقرأ القائمة المشتركة")

# ── 3) المصلح: لا تكرار صحيح · قائمة واحدة · بلا مساس بالجداول
p = B / 'tools/repair_prose.py'
t = p.read_text(encoding='utf-8')
t = t.replace('RULES = B / "appendices" / "writing-rules.json"',
              'RULES = B / "appendices" / "writing-rules.json"\nDOUBLED = B / "appendices" / "doubled-letters.json"')
new_funcs = '''def fix_punctuation(text: str) -> tuple[str, int]:
    """الترقيم داخل السطر فقط — لا يعبر نهايات الأسطر (البند ز-3).

    صفوف الجداول المُنشئة (| :--- | · | --- |) لا تُمسّ: تغييرها يُفسد الجدول (مراجعة ثالثًا-6).
    """
    n = 0
    header = re.compile(r"^\\s*\\|[\\s:|-]*\\|[\\s:|-]*\\|?\\s*$")
    pats = [
        (r"[ \\t]+([،؛:.!؟])", r"\\1"),          # مسافة/مسافات قبل علامة ترقيم
        (r"([،؛!؟])\\1+", r"\\1"),               # علامة مكرّرة
        (r"([،؛])[ \\t]*([.،؛])", r"\\1"),       # علامتان متجاورتان
        (r"\\.{2,}(?!\\.)", r"."),               # نقاط متعددة
    ]
    out = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\\n")
        if header.match(body):
            out.append(line)
            continue
        for pat, rep in pats:
            body, k = re.subn(pat, rep, body)
            n += k
        out.append(body + ("\\n" if line.endswith("\\n") else ""))
    return "".join(out), n


def fix_doubled_letters(text: str, rules: dict) -> tuple[str, int]:
    """الحروف المضاعفة: «ةة» فقط، وأي حرف تكرّر ثلاثًا فأكثر.

    «دد» و«يي» و«وو» و«اا» لا تُمسّ: تكرارات صحيحة في كلمات شائعة
    («عدد» · «تقييم» · «تهدد» · «الالتزامات») — مراجعة 23 أكتوبر 2026 ثالثًا-1.
    والقائمة المشتركة واحدة يقرأها المصلح والكاشف من appendices/doubled-letters.json.
    """
    sh = json.loads(DOUBLED.read_text(encoding="utf-8"))
    wl = set(sh["whitelist"])
    fixed = sh.get("forbidden_fixed") or ["ةة"]
    minrep = int(sh.get("forbidden_repeat_min") or 3)
    n = 0
    out = []
    for word in re.split(r"(\\s+)", text):
        if not word.strip() or word in wl:
            out.append(word)
            continue
        new = word
        for f in fixed:
            new, k = re.subn(re.escape(f) + r"+", f[0], new)
            n += k
        new, k2 = re.subn(r"([\\w\\u0600-\\u06FF])\\1{" + str(minrep - 1) + r",}", r"\\1", new)
        n += k2
        out.append(new)
    return "".join(out), n


'''
start = t.index('def fix_punctuation')
end = t.index('def fix_fixed_terms')
t = t[:start] + new_funcs + t[end:]
p.write_text(t, encoding='utf-8')
ast.parse(t)
print("  ✔ المصلح: «ةة» وتكرار ثلاثي فقط · بلا مساس بالتكرار الصحيح · بلا مساس بصفوف الجداول")

# ── 4) قواعد الكتابة: إخراج التكرار الصحيح + المثنى في القائمة اليدوية
p = B / 'appendices/writing-rules.json'
w = json.loads(p.read_text(encoding='utf-8'))
w['doubled_letters_forbidden'] = ["ةة"]
w['doubled_letters_allowed'] = ["ةة"]
w['doubled_letters_note'] = "«دد» و«يي» و«وو» و«اا» أُخرجت من الإصلاح الآلي: تكرارات صحيحة. القائمة المشتركة في appendices/doubled-letters.json."
w.setdefault('manual_only', [])
for term in ["عبورتين", "عبورتان"]:
    if not any(x.get('term') == term for x in w['manual_only']):
        w['manual_only'].append({
            "term": term,
            "replacement": "عمليات عبور (تُعاد صياغتها بالمعنى)",
            "stop_on_hit": True, "auto": False,
            "reason": "المثنى يتأثر بالتركيب ⇒ لا إصلاح آلي (مراجعة ثالثًا-5)"})
p.write_text(json.dumps(w, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
print(f"  ✔ writing-rules: forbidden = {w['doubled_letters_forbidden']} · manual_only = {len(w['manual_only'])} بندًا")

# ── 5) إصلاح التفسد الواقع فعلًا في تقرير 23
p = B / 'reports/2026-10-23-sectioned.md'
t = p.read_text(encoding='utf-8')
fixes = [("انخفاض عد السفن", "انخفاض عدد السفن"),
         ("وعد السفن المتحفظة", "وعدد السفن المتحفظة"),
         ("**تقيم دقة تقديرات أمس.**", "**تقييم دقة تقديرات أمس.**")]
done = [(a, b) for a, b in fixes if a in t]
for a, b in done:
    t = t.replace(a, b)
p.write_text(t, encoding='utf-8')
print(f"  ✔ تقرير 23: أُصلح {len(done)} موضعًا من التفسد: {[a for a, _ in done]}")