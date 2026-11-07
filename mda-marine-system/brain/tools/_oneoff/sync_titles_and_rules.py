#!/usr/bin/env python3
"""الخطوة 3: تحديث المهارتين وقواعد الكتابة، وتزامن العناوين والبادئات في ملفات الإنتاج.

مستثنى بالكامل: reports/ · archive/ · cumulative-2026/ · dist/ · logs/ · feeds/ · audit/ · notes/
والملفات الجديدة الثلاثة (20-writing-brief · 20-lexicon · 20-examples) لأنها تحوي «لا تكتب» أمثلةً.
"""
import json
import re
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')
S = Path('/home/ubuntu/seawatch')

# ── 1) خريطة التوحيد: قديم → جديد ──
# العناوين والبادئات فقط. **لا تُمسّ صيغ المنع** («النافذة» · «عبورات» · «غير معلوم» · «يُوسم إعلاميًا»
# · «ينقضه») لأنها قواعد مانعة داخل المدققات، واستبدالها يُلغي البوابة نفسها.
TITLES = [
    ('مؤشرات الإنذار المبكر', 'علامات الإنذار المبكر'),
    ('مؤشرات تحذير مبكر', 'علامات إنذار مبكر'),
    ('الاحتمالات والإسناد', 'الاحتمالات ونسبة الحوادث إلى جهات'),
    ('المصادر المستشهد بها', 'المصادر المذكورة'),
    ('قراءة النمط', 'وصف النمط'),
    ('تحليل الفرضيات المتنافسة', 'اختبار الفرضيات المتنافسة'),
    ('الإسناد:', 'نسبة الحادث إلى جهة:'),
    ('ما وقع:', 'ما حدث:'),
    ('الحصيلة:', 'الأثر:'),
    ('سند:', 'المستند:'),
]
EXCLUDE_DIRS = ('/reports/', '/archive/', '/cumulative-2026/', '/dist/', '/logs/', '/feeds/', '/audit/', '/notes/', '/.git/', '/_oneoff/')
EXCLUDE_NAMES = {'20-writing-brief.md', '20-lexicon.md', '20-examples.md', 'editor-prompt.md',
                 'style_metrics.py', 'repair_prose.py', 'event-code-map.json', 'plan-language-fix-01-2026-10-23.md'}

def targets():
    out = []
    for root, pats in [(B, ('validators/*.py', 'tools/*.py', 'templates/*.json', 'templates/*.md',
                            'sections/*.md', 'appendices/*.md', 'appendices/*.json', 'tests/*.sh')),
                       (S, ('generator/*.py',))]:
        for pat in pats:
            out += sorted(root.glob(pat))
    return out

changed = {}
for p in targets():
    ps = str(p)
    if any(d in ps for d in EXCLUDE_DIRS) or p.name in EXCLUDE_NAMES:
        continue
    if not p.is_file():
        continue
    try:
        t = p.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    orig = t
    hits = {}
    for a, b in TITLES:
        n = t.count(a)
        if n:
            t = t.replace(a, b)
            hits[a] = n
    if t != orig:
        p.write_text(t, encoding='utf-8')
        changed[str(p).replace('/home/ubuntu/', '')] = hits

print('  ── ملفات الإنتاج المعدّلة (توحيد العناوين والبادئات) ──')
tot = 0
for f, h in sorted(changed.items()):
    tot += sum(h.values())
    print(f'    {f:62s} {sum(h.values()):3d} · ' + ' · '.join(f'{k}×{v}' for k, v in list(h.items())[:4]))
print(f'  المجموع: {len(changed)} ملفًا · {tot} استبدالًا')

# ── 2) قائمة المنع الواحدة: كتابة الأشكال الممنوعة في writing-rules.json و forbidden-coinages.json ──
wr_p = B / 'appendices/writing-rules.json'
wr = json.loads(wr_p.read_text(encoding='utf-8'))
ban_new = [
    {'dont': 'مؤشرات الإنذار المبكر', 'do': 'علامات الإنذار المبكر'},
    {'dont': 'مؤشرات تحذير مبكر', 'do': 'علامات إنذار مبكر'},
    {'dont': 'الاحتمالات والإسناد', 'do': 'الاحتمالات ونسبة الحوادث إلى جهات'},
    {'dont': 'المصادر المستشهد بها', 'do': 'المصادر المذكورة'},
    {'dont': 'قراءة النمط', 'do': 'وصف النمط'},
    {'dont': 'ينقضه / ينقضها', 'do': 'ما يضعفه / ما يضعفها'},
    {'dont': 'تحليل الفرضيات المتنافسة', 'do': 'اختبار الفرضيات المتنافسة'},
    {'dont': 'غير معلوم', 'do': 'غير محدد المصدر'},
    {'dont': 'النافذة · نافذتي', 'do': 'الفترة · فترتي'},
    {'dont': 'يُوسم إعلاميًا · تُوسم إعلاميًا', 'do': 'يُذكر على أنه نقل إعلامي · تُذكر على أنها نقل إعلامي'},
    {'dont': 'الإسناد:', 'do': 'نسبة الحادث إلى جهة:'},
    {'dont': 'ما وقع:', 'do': 'ما حدث:'},
    {'dont': 'الحصيلة:', 'do': 'الأثر:'},
    {'dont': 'سند:', 'do': 'المستند:'},
    {'dont': 'و في أول الجملة (أكثر من جملة من كل خمس)', 'do': 'ابدأ بالمعلومة أو بالفاعل مباشرة'},
]
existing = {x.get('dont') for x in wr.get('manual_only', []) if isinstance(x, dict)}
added = []
for e in ban_new:
    if e['dont'] not in existing:
        wr.setdefault('manual_only', []).append(e)
        added.append(e['dont'])
wr['version'] = int(wr.get('version', 2)) + 1
wr['approved'] = '2026-10-23 — أمر تنفيذي: قائمة المنع الواحدة والعناوين والبادئات الموحّدة'
wr['single_source_note'] = 'هذه القائمة هي المصدر الوحيد للألفاظ والعناوين الممنوعة. لا قائمة ثانية في أي ملف.'
wr_p.write_text(json.dumps(wr, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'  ✔ writing-rules.json: أُضيف {len(added)} بندًا · الإصدار {wr["version"]}')

fc_p = B / 'appendices/forbidden-coinages.json'
fc = json.loads(fc_p.read_text(encoding='utf-8'))
fc_add = [
    {'term': 'مؤشرات الإنذار المبكر', 'replacement': 'علامات الإنذار المبكر', 'kind': 'عنوان قسم'},
    {'term': 'الاحتمالات والإسناد', 'replacement': 'الاحتمالات ونسبة الحوادث إلى جهات', 'kind': 'عنوان قسم'},
    {'term': 'المصادر المستشهد بها', 'replacement': 'المصادر المذكورة', 'kind': 'عنوان قسم'},
    {'term': 'قراءة النمط', 'replacement': 'وصف النمط', 'kind': 'بادئة'},
    {'term': 'تحليل الفرضيات المتنافسة', 'replacement': 'اختبار الفرضيات المتنافسة', 'kind': 'مصطلح'},
    {'term': 'غير معلوم', 'replacement': 'غير محدد المصدر', 'kind': 'مصطلح'},
    {'term': 'ينقضه', 'replacement': 'ما يضعفه', 'kind': 'لفظ'},
    {'term': 'سند:', 'replacement': 'المستند:', 'kind': 'بادئة'},
]
have = {e.get('term') for e in fc.get('entries', [])}
for e in fc_add:
    if e['term'] not in have:
        fc.setdefault('entries', []).append(e)
fc['status'] = 'approved'
fc['updated'] = '2026-10-23'
fc['note'] = 'قائمة منع لغوية معتمدة بأمر 23 أكتوبر 2026. الصيغة الجديدة تُكتب، والقديم يُقبل في المصادر المنشورة.'
fc_p.write_text(json.dumps(fc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'  ✔ forbidden-coinages.json: {len(fc["entries"])} بندًا · الحالة {fc["status"]}')
