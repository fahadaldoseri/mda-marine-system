#!/usr/bin/env python3
"""الخطوة 3.1 و3.2 و3.5 (توافق المدققات): تحديث المهارتين، وجعل المدققات تقبل الصيغة القديمة والجديدة."""
from pathlib import Path

BRAIN = Path('/home/ubuntu/brain-marine-news')
SK_BRAIN = Path('/home/ubuntu/skills/marine-news-brain/SKILL.md')
SK_EDIT = Path('/home/ubuntu/skills/military-arabic-editing/SKILL.md')

BLOCK_BRAIN = """- **ترتيب القراءة الإلزامي قبل أي سطر**: `sections/20-writing-brief.md` ← `sections/20-lexicon.md` ← `sections/20-examples.md`. ونصّها الثلاثة مضمَّن في الأمر اليومي نفسه، فهي أول ما يُقرأ، لا تُختصر ولا تُعاد صياغتها.
- **القواعد الـ13** (ملخّصها؛ النص الكامل في مختصر الكتابة): جملة قصيرة ≤20 كلمة غالبًا · لا تبدأ الجملة بـ«و» (أكثر من جملة من كل خمس ممنوعة) · النقاط لأربعة عناصر أو أكثر · كل نقطة في سطر مستقل ببادئة ثابتة · العنوان قصير بلا نقطة · الفقرة فكرة واحدة · المصطلح الموحّد مرة واحدة عند أول ظهور · بلا حشو · بلا مبني للمجهول · بلا تعبير بلا معنى · الأرقام لاتينية 0–9 · لا تُخترع معلومة · أعد قراءة النص قبل التسليم.
- **قائمة المنع الواحدة**: `appendices/writing-rules.json` وتكملها `appendices/forbidden-coinages.json`. لا قائمة ثانية في أي ملف، والبوابات تعمل عليها.
- **الصيغة الجديدة تُكتب والقديم يُقبل**: العناوين والبادئات الموحّدة في `sections/20-lexicon.md`؛ تُكتب في كل نص جديد، ويُقبل الشكل القديم في المصادر المنشورة والاقتباسات.
"""

BLOCK_EDIT = """## قواعد الكلمة والجملة والنحو (أمر 23 أكتوبر 2026)
- المرجع الأول: `sections/20-writing-brief.md` (القواعد الـ13) · `sections/20-lexicon.md` (عمود «اكتب» وعمود «لا تكتب» وجدول العناوين والبادئات) · `sections/20-examples.md` (قبل/بعد).
- **مستوى الجملة**: جملة قصيرة ≤20 كلمة غالبًا · لا تبدأ الجملة بـ«و» · لا تتابع ثلاث جمل مبدوءة بحرف عطف · الجملة الطويلة تُقسم.
- **مستوى الكلمة**: مصطلح واحد لكل معنى · لا مفردة اصطناعية («عبورات» ← «عمليات عبور» · «النافذة» ← «الفترة») · لا ترجمة حرفية · الرسم الموحّد (ط14).
- **مستوى النحو**: مطابقة العدد والجنس · حروف الجر الصحيحة («بلا/دون/غير» + اسم مجرور، لا منصوب) · الترقيم: لا فاصلة ونقطة متجاورتين، لا مسافة قبل الترقيم، لا حرف مضاعف بلا سبب.
- **الترجمة بالمعنى** لا كلمة بكلمة (ط16-2)، والخبر المباشر (ط16-1).
- **نسبة الحادث إلى جهة**: تُكتب بهذه الصيغة في المتن والتحليل معًا، بدل «الإسناد».

"""

def insert_after(path: Path, anchor: str, block: str) -> str:
    t = path.read_text(encoding='utf-8')
    if block.split('\n')[0] in t:
        return 'موجود مسبقًا'
    if anchor not in t:
        return f'✘ لم أجد المرساة: {anchor[:40]}'
    t = t.replace(anchor, anchor + '\n' + block, 1)
    path.write_text(t, encoding='utf-8')
    return '✔ أُدرج'

print('  ── المهارات ──')
print('   Brain   :', insert_after(SK_BRAIN, '## قواعد قبل الكتابة (ملزمة — 23 أكتوبر 2026)', BLOCK_BRAIN))
print('   Editing :', insert_after(SK_EDIT, '## قواعد دلالية', BLOCK_EDIT))

# ── توافق المدققات: قبول الصيغة القديمة والجديدة ──
print('  ── توافق المدققات ──')
p = BRAIN / 'validators/check_intel.py'
t = p.read_text(encoding='utf-8')
old = '        if "علامات الإنذار المبكر" not in body:\n            errors.append("بقاء-1: «علامات الإنذار المبكر» غير ظاهرة بعد الحذف الجزئي")'
new = ('        if not any(k in body for k in ("علامات الإنذار المبكر", "مؤشرات الإنذار المبكر", "مؤشرات تحذير مبكر")):\n'
       '            errors.append("بقاء-1: «علامات الإنذار المبكر» غير ظاهرة بعد الحذف الجزئي (تُقبل الصيغة القديمة أيضًا)")')
if old in t:
    p.write_text(t.replace(old, new, 1), encoding='utf-8'); print('   check_intel.py: ✔ يقبل الصيغتين')
else:
    print('   check_intel.py: ⚠ لم أطابق النص (راجع يدويًا)')

p = BRAIN / 'validators/check_comprehension.py'
t = p.read_text(encoding='utf-8')
old = '"ACH": ["اختبار الفرضيات المتنافسة", "الفرضيات المتنافسة"],'
new = '"ACH": ["اختبار الفرضيات المتنافسة", "تحليل الفرضيات المتنافسة", "الفرضيات المتنافسة"],'
if old in t:
    p.write_text(t.replace(old, new, 1), encoding='utf-8'); print('   check_comprehension.py: ✔ يقبل الصيغتين')
else:
    print('   check_comprehension.py: ⚠ لم أطابق النص')

p = BRAIN / 'validators/check_code_spaces.py'
t = p.read_text(encoding='utf-8')
old = 'ANALYSIS_HEADS = ("التحليل الاستخباري", "الاحتمالات ونسبة الحوادث إلى جهات", "الخلاصة", "مؤشرات الموقف")'
new = 'ANALYSIS_HEADS = ("التحليل الاستخباري", "الاحتمالات ونسبة الحوادث إلى جهات", "الاحتمالات والإسناد", "الخلاصة", "مؤشرات الموقف")'
if old in t:
    p.write_text(t.replace(old, new, 1), encoding='utf-8'); print('   check_code_spaces.py: ✔ يقبل الصيغتين')
else:
    print('   check_code_spaces.py: ⚠ لم أطابق النص')

# فحص الصياغة
import ast
for f in ['validators/check_intel.py', 'validators/check_comprehension.py', 'validators/check_code_spaces.py']:
    ast.parse((BRAIN / f).read_text(encoding='utf-8'))
print('  ✔ صياغة المدققات الثلاثة سليمة')