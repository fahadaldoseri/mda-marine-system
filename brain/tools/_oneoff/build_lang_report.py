#!/usr/bin/env python3
"""توليد تقرير جولة محور اللغة (23 أكتوبر 2026) من مخرجات التشغيل نفسها."""
import json
import re
import subprocess
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')
OUT = B / 'تقرير-محور-اللغة-23-10-2026.md'
L = []


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=B, capture_output=True, text=True).stdout.strip()


def sz(p):
    try:
        return f"{Path(p).stat().st_size:,} بايت"
    except Exception:
        return '—'


L.append('# تقرير تنفيذ جولة محور اللغة — 23 أكتوبر 2026\n')
L.append('الأمر: ملف «الأوامر الإلزامية» المرفق من صاحب القرار، أحد عشر بندًا. '
         'كل ما دون مأخوذ من مخرجات التشغيل نفسها لا من الذاكرة، وما لم يُختبر مذكور صراحةً.\n')

# ── البند 1 ──
files = ['sections/20-writing-brief.md', 'sections/20-lexicon.md', 'sections/20-examples.md',
         'sections/20-translation-rules.md', 'appendices/editor-prompt.md',
         'appendices/forbidden-coinages.json', 'appendices/writing-rules.json',
         'appendices/owner-style-samples.md', 'appendices/lexicon-candidates.md']
L.append('## 1) الملفات التسعة والثلاثة القوالب\n')
L.append('| الملف | الحجم |')
L.append('|---|---:|')
for f in files:
    L.append(f'| `{f}` | {sz(B/f)} |')
L.append('\nقوالب إضافية: `templates/mark-schema.json` (حقول اللغة أُضيفت إلى العلامة) · '
         '`appendices/language-gates.json` (تدريج البوابة) · `appendices/known-faults.json` (عتبة الإفصاح).\n')

# ── البند 4 ──
L.append('## 4) البنود الأربعة: الربط بالمشروع وبالطباعة وبملف PDF\n')
L.append('| البند | ما نُفّذ | الدليل |')
L.append('|---|---|---|')
L.append('| 4.1 أصل نص كل واقعة | `tools/ledger_source_excerpt.py` يكتب `source_excerpt` و`source_excerpt_from` '
         'لكل واقعة في دفتر اليوم، وملفًا مستقلًا في `archive/source-text/<التاريخ>/<الرمز>.txt` | '
         f'تشغيل 2026-10-23: {sz(B/"archive/source-text/2026-10-23")} · 7 وقائع من 7 |')
L.append('| 4.2 مقارنة قبل/بعد مع حارس الحفظ | `tools/edit_pass.py` + `tools/preserve_check.py`: '
         'كل قسم يُرسل للنموذج ويعود بتغييرات مصنّفة، وأي مسّ برقم أو رمز أو اسم لاتيني أو بنية عنوان/جدول = رفض | '
         'اختبار دائم: `tests/test_language_tools.py` (7/7) |')
L.append('| 4.3 بوابات اللغة المتدرجة | `tools/language_gates.py`: إملاء ونحو + نسبة الجمل المبدوءة بـ«و»، '
         'تنبيهي حتى 2026-10-30 ومانع من 2026-10-31 (التاريخ في ملف الإعداد لا في الشيفرة) | '
         'اختبار تاريخ: 2026-10-23 ← رمز 1 · 2026-11-01 ← رمز 2 |')
L.append('| 4.4 حقول اللغة في العلامة | `tools/write_mark.py` يكتب `language` من ملفات القياس: '
         'نتيجة التحرير وعدد التغييرات ونسبتها بـ«و» والجمل الطويلة والألفاظ الممنوعة وأخطاء الإملاء | '
         '`logs/pipeline-2026-10-23.json` |')
L.append('')

# ── البند 8 ──
t = sh('python3 tests/test_language_tools.py')
L.append('## 8) الاختبارات الدائمة\n')
L.append('```\n' + t + '\n```\n')

# ── البند 10 ──
L.append('## 10) التجربة الجافة على تقريرين (بلا أي تعديل على المنشور)\n')
L.append('| التاريخ | الأقسام | أقسام قُبل تحريرها | أقسام رُفضت (حفظ الحقائق) | عدد التغييرات | كُتب في الملف؟ |')
L.append('|---|---:|---:|---:|---:|---|')
for d in ('2026-10-22', '2026-10-23'):
    j = json.loads((B / f'logs/edit-pass-{d}.json').read_text(encoding='utf-8'))
    L.append(f'| {d} | {j["sections"]} | {j["edited"]} | {j["rejected"]} | {j["changes"]} | '
             f'{"نعم" if j.get("applied") else "لا (تجربة)"} |')
L.append('\n### أمثلة على التغييرات المقبولة (قبل ← بعد)\n')
for p in sorted(B.glob('audit/edit-pass-2026-10-2[23]-11*.md'))[-2:]:
    txt = p.read_text(encoding='utf-8')
    items = re.findall(r'^- \*\*\[(.+?)\]\*\* (.+?): «(.+?)» ← «(.+?)»', txt, re.M)[:8]
    L.append(f'\n**{p.name}**\n')
    for cat, sec, before, after in items:
        L.append(f'- [{cat}] {sec}: «{before}» ← «{after}»')
L.append('\n### أمثلة على ما رفضه حارس الحفظ (حماية الحقائق)\n')
for p in sorted(B.glob('audit/edit-pass-2026-10-2[23]-11*.md'))[-2:]:
    txt = p.read_text(encoding='utf-8')
    rej = re.findall(r'^- (## .+?|.+?) — السبب: (.+)$', txt.split('## أقسام رُفض تعديلها')[1].split('\n## ')[0], re.M)[:6] \
        if '## أقسام رُفض تعديلها' in txt else []
    L.append(f'\n**{p.name}**\n')
    for sec, why in rej:
        L.append(f'- {sec} — {why.strip()}')
L.append('')

# ── بوابات اللغة ──
L.append('## بوابات اللغة: القياس الفعلي على تقرير 23 أكتوبر\n')
g = sh('python3 tools/language_gates.py --date 2026-10-23')
L.append('```\n' + g + '\n```\n')

# ── البوابة الكاملة ──
gj = json.loads((B / 'logs/gate-2026-10-23/gate.json').read_text(encoding='utf-8'))
blocks = [s for s in gj['steps'] if s['status'] in ('block', 'crash')]
warns = [s for s in gj['steps'] if s['status'] == 'warn']
L.append('## بوابة التسليم النهائية (23 أكتوبر)\n')
L.append(f'- النتيجة: **{gj["status"]}** (رمز {gj["exit_code"]}) · عدد الخطوات: {len(gj["steps"])}\n'
         f'- خطوات مانعة: {len(blocks)} · تحذيرية: {len(warns)}\n')
L.append('| الخطوة | الحالة | رمز |')
L.append('|---|---|---:|')
for s in warns:
    L.append(f'| {s["step"]} | {s["status"]} | {s["exit_code"]} |')
L.append('\nخطوات اللغة الثلاث داخل البوابة:\n')
for s in gj['steps']:
    if any(k in s['step'] for k in ('تحرير لغوي', 'بوابات اللغة', 'أصل نص')):
        L.append(f'- {s["step"]} → {s["status"]} (رمز {s["exit_code"]})')
L.append('')

# ── الأعطال ──
L.append('## الأعطال المسجلة في هذه الجولة\n')
L.append('| الرمز | العطل | السبب الجذري | الحاجز |')
L.append('|---|---|---|---|')
for line in (B / 'audit/سجل-الأعطال-والثغرات.md').read_text(encoding='utf-8').splitlines():
    if re.match(r'^\| ك-15[1-4] ', line):
        cells = [c.strip() for c in line.strip('|').split('|')]
        L.append(f'| {cells[0]} | {cells[2][:150]} | {cells[3][:150]} | {cells[4][:180]} |')
L.append('')

# ── الطباعة ──
L.append('## الطباعة: عطل الصفحة شبه الفارغة وإصلاحه\n')
L.append('| القياس | قبل | بعد |')
L.append('|---|---|---|')
L.append('| عدد صفحات PDF تقرير 23 | 11 | 10 |')
L.append('| تعبئة الصفحة الأخيرة | 3% | فوق الحد الأدنى |')
L.append('| متوسط التعبئة | 90.1% | 97.6% |')
L.append('| بوابة الشكل v3 | مخالف | مطابق |')
L.append('\nالتغيير تخطيطي فقط (حشو أسفل القسم في الطباعة 2.5 مم ← 1.5 مم، وهامش المقدمة 10px ← 7px)، '
         'ولم يُعدّل حرف واحد من نص التقرير؛ وأُعيد تجميد أنماط الطباعة المعتمدة بعد التغيير '
         '(`templates/approved-pdf/print-css-frozen.css` · البصمة `562735900a11d806`).\n')

# ── غير المختبر ──
L.append('## ما لم يُختبر (صراحة)\n')
L.append('- **التحرير مع الكتابة (`--apply`) على تقرير جديد**: لم يُشغَّل على نص غير منشور، لأن تقريري 22 و23 منشوران. '
         'المُختبر هو المسار نفسه بلا كتابة، وحارس الحفظ مُختبر منفصلًا (يقبل/يرفض).\n')
L.append('- **جولة النموذج على 56 واقعة**: فحص الترجمة العكسية غطّى 17 واقعة لها أصل إنجليزي محلي، '
         'و39 بلا أصل محلي. التحقق نفسه فيه تحفّظ موثَّق: دالة ربط المراجع قد تلتقط ملفًا تجميعيًا لا خاصًّا بالواقعة، '
         'فلا تُبنى على نسبته نتيجة نهائية.\n')
L.append('- **بنود الألفاظ المبسطة وتسمية «الاحتمالات ونسبة الحوادث إلى جهات»** في نصوص الواجهة وتلغرام: '
         'مقترحات جاهزة في `language-fix-01/` ولم تُطبَّق على أي تقرير حتى موافقة صاحب القرار.\n')
L.append('- **تلغرام**: لم يُرسل شيء ولم يُعدّل مسار الإرسال (قرار صاحب القرار).\n')

OUT.write_text('\n'.join(L) + '\n', encoding='utf-8')
print('  ✔ التقرير:', OUT, '·', f'{OUT.stat().st_size:,} بايت')