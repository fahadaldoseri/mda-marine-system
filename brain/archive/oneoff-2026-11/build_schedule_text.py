#!/usr/bin/env python3
"""يبني نص الأمر المجدول الجديد من: (1) تعليمات الكتابة أ+ب+ج حرفيًا، (2) الأمر التشغيلي الحالي بعد الاستبدالات.

المخرجات: /tmp/sched-new.txt · /tmp/sched-diff.txt · تقرير على الشاشة.
لا يعدّل المهمة المجدولة؛ التحديث بأمر منفصل.
"""
import difflib
import hashlib
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')
OLD = Path('/tmp/sched-command.txt')
NEW = Path('/tmp/sched-new.txt')
DIFF = Path('/tmp/sched-diff.txt')

writing = []
for f, label in [('sections/20-writing-brief.md', 'أ'),
                 ('sections/20-lexicon.md', 'ب'),
                 ('sections/20-examples.md', 'ج')]:
    t = (B / f).read_text(encoding='utf-8').rstrip('\n')
    writing.append(t)

old = OLD.read_text(encoding='utf-8').rstrip('\n')

# ── الاستبدالات المطلوبة في الأمر (وما يوافقها من العناوين الجديدة) ──
REPL = [
    ('بنافذتي 48 و72 ساعة', 'بفترتي 48 و72 ساعة'),
    ('النقل الإعلامي يُوسم إعلاميًا', 'النقل الإعلامي يُذكر على أنه نقل إعلامي'),
    ('وسجّل وسم الأسلوب في ملف الواجهة', 'وأثبت قيمة حقل الأسلوب في ملف الواجهة، لا في متن التقرير'),
    # العناوين والبادئات الموحّدة (الخطوة 3.5) داخل قائمة ترتيب الأقسام
    ('مؤشرات الموقف', 'مؤشرات الموقف'),
    ('مؤشرات الإنذار المبكر', 'علامات الإنذار المبكر'),
    ('و3–5 مؤشرات تحذير مبكر', 'و3–5 علامات إنذار مبكر'),
    ('الاحتمالات والإسناد', 'الاحتمالات ونسبة الحوادث إلى جهات'),
    ('للمصادر المستشهد بها فقط', 'للمصادر المذكورة فقط'),
]
new_ops = old
applied = []
for a, b in REPL:
    if a in new_ops and a != b:
        n = new_ops.count(a)
        new_ops = new_ops.replace(a, b)
        applied.append(f'  · «{a}» ← «{b}» ({n} موضعًا)')

head = ('تعليمات الكتابة — اقرأها قبل أي شيء\n'
        'هذه التعليمات مُلزمة على كل سطر تكتبه. النصوص التالية حرفية، لا تُختصر ولا تُعاد صياغتها.\n\n'
        + '\n\n'.join(writing)
        + '\n\nقاعدة مرافقة: لا تُقرأ ملفات الأسلوب كلها قبل الكتابة. '
          'تُستدعى عند الحاجة: appendices/terminology.md والمكتبات وقوائم المنع، والبوابات تعمل عليها.\n\n'
          '─' * 20 + '\n\n')

new = head + new_ops
NEW.write_text(new, encoding='utf-8')

d = difflib.unified_diff(old.splitlines(), new_ops.splitlines(), 'الأمر قبل', 'الأمر بعد',
                         lineterm='', n=1)
DIFF.write_text('\n'.join(d), encoding='utf-8')

print('  ✔ بُني النص الجديد')
print(f'  · القديم: {len(old)} حرفًا · {old.count(chr(10))+1} سطرًا · بصمة {hashlib.sha256(old.encode()).hexdigest()[:12]}')
print(f'  · الجديد: {len(new)} حرفًا · {new.count(chr(10))+1} سطرًا · بصمة {hashlib.sha256(new.encode()).hexdigest()[:12]}')
print('  الاستبدالات المطبَّقة على الأمر التشغيلي:')
print('\n'.join(applied) if applied else '    (لا شيء)')
print('  طول تعليمات الكتابة المضمّنة:', sum(len(w) for w in writing), 'حرفًا')
# تحقق: هل بقي أمر بقراءة ملفات الأسلوب؟
for bad in ['75-style', '20-language', 'اقرأ ملفات الأسلوب']:
    print(f'  · «{bad}» في النص الجديد: {new.count(bad)}')
