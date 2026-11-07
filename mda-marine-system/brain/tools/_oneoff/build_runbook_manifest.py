#!/usr/bin/env python3
"""يبني runbook/runbook.json من الواقع: خطوات الخط اليومي، وكل بوابة في final_gate.sh،
وخطوات الكتابة والبناء والنشر، وسجل الأقسام — ويولّد برومتات الخطوات واختبارات الأقسام."""
import json
import os
import re
from pathlib import Path

R = Path('/home/ubuntu/brain-marine-news')
SITE = Path('/home/ubuntu/seawatch')

# ── 1) الأقسام من 30-structure.md ──
struct = (R / 'sections/30-structure.md').read_text(encoding='utf-8')
rows = re.findall(r'^\| (\d+) \| ([^|]+?) \| ([^|]*)\|', struct, re.M)
SECTIONS = [(int(n), t.strip(), d.strip()) for n, t, d in rows if 1 <= int(n) <= 17]
assert len(SECTIONS) == 17, f'عدد الأقسام {len(SECTIONS)} لا 17'

SLUG = {
 1: 'what-changed', 2: 'summary', 3: 'general', 4: 'incident-map', 5: 'indicators',
 6: 'threat-level', 7: 'directives', 8: 'new-incidents', 9: 'warnings', 10: 'imo-log',
 11: 'intel-analysis', 12: 'attribution', 13: 'traffic', 14: 'open-questions',
 15: 'monitoring', 16: 'background', 17: 'sources',
}
VALIDATOR = {
 1: 'validators/check_carryover.py', 2: 'validators/check_report.py', 3: 'validators/check_comprehension.py',
 4: 'validators/check_pdf_format.py', 5: 'validators/check_style.py', 6: 'validators/check_intel.py',
 7: 'validators/check_points_rule.py', 8: 'validators/check_language.py', 9: 'validators/check_code_spaces.py',
 10: 'validators/check_carryover.py', 11: 'validators/check_intel.py', 12: 'validators/check_comprehension.py',
 13: 'validators/check_style.py', 14: 'validators/check_comprehension.py', 15: 'validators/check_style.py',
 16: 'validators/check_carryover.py', 17: 'validators/check_sources_count.py',
}

prompt_dir = R / 'runbook/prompts/sections'
prompt_dir.mkdir(parents=True, exist_ok=True)
test_dir = R / 'tests/sections'
test_dir.mkdir(parents=True, exist_ok=True)
blocks_file = '/home/ubuntu/seawatch/generator/blocks.py'
if not Path(blocks_file).exists():
    blocks_file = '/home/ubuntu/seawatch/generator/build_report.py'

sections = []
for n, title, desc in SECTIONS:
    sid = SLUG[n]
    p = prompt_dir / f'{sid}.md'
    p.write_text(
        f'# مقتطف برومت — القسم {n}: {title}\n\n'
        f'الترتيب الملزم: {n}.\n\nما يُكتب فيه: {desc}\n\n'
        'قواعد ملزمة: عربية بسيطة مباشرة · أرقام لاتينية 0-9 · «الفترة» لا «النافذة» · '
        'التعداد نقاطًا لا فقرة · كل رقم أو واقعة لها مصدرها · لا ألفاظ مصطنعة.\n',
        encoding='utf-8')
    t = test_dir / f'test_{sid}.sh'
    t.write_text(
        '#!/usr/bin/env bash\n'
        f'# اختبار القسم {n} ({sid}): وجوده في تقرير اليوم ووجود كتلته ومدققه\n'
        'set -u\nD="${1:-$(date -u +%F)}"\n'
        'R="$(cd "$(dirname "$0")/../.." && pwd)"\n'
        f'grep -q "{title}" "$R/reports/$D-sectioned.md" || {{ echo "✘ القسم {title} غائب عن تقرير $D"; exit 2; }}\n'
        f'test -f "{blocks_file}" || {{ echo "✘ كتلة التوليد غائبة"; exit 2; }}\n'
        f'test -f "$R/{VALIDATOR[n]}" || {{ echo "✘ مدقق القسم غائب"; exit 2; }}\n'
        f'echo "✔ القسم {title} مرتبط"\n'
        'exit 0\n', encoding='utf-8')
    os.chmod(t, 0o755)
    sections.append({'id': sid, 'title': title, 'order': n, 'block': blocks_file,
                     'validator': VALIDATOR[n], 'prompt_snippet': f'runbook/prompts/sections/{sid}.md',
                     'tests': [f'tests/sections/test_{sid}.sh'], 'files': []})

# ── 2) برومتات خطوات الوكيل ──
pd = R / 'runbook/prompts'
pd.mkdir(parents=True, exist_ok=True)
(R / 'sections/20-writing-brief.md').exists()
(pd / 'write-report.md').write_text(
    '# خطوة: كتابة التقرير اليومي\n\n'
    'اقرأ بهذا الترتيب ثم اكتب: `sections/20-writing-brief.md` · `sections/20-lexicon.md` · '
    '`sections/20-examples.md` · `sections/20-language.md` · `sections/75-style.md` · '
    '`appendices/editor-prompt.md` · ثم دفتر اليوم `cumulative-2026/daily/{date}.json` '
    'والتغذيات `feeds/feeds-{date}.md`.\n\n'
    'اكتب `reports/{date}-sectioned.md` بأقسام السجل `sections` في `runbook/runbook.json` وبترتيبه.\n'
    'قواعد: عربية بسيطة مباشرة · أرقام لاتينية · «الفترة» لا «النافذة» · التعداد نقاطًا · '
    'كل واقعة بمصدرها · لا صياغة أكاديمية ولا ألفاظ مصطنعة.\n\n'
    'لا تعلن الإتمام إلا بعد كتابة الملف: المحرّك يتحقق من وجوده وحجمه ونصه.\n', encoding='utf-8')
(pd / 'write-meta.md').write_text(
    '# خطوة: بناء ملف واجهة التقرير\n\n'
    'اكتب `web/meta/{date}.json` بالحقول المعتمدة (الخلاصة · بطاقة القرار · المؤشرات · '
    'مستوى الخطر · الرموز) مستخرجة من `reports/{date}-sectioned.md` نفسه، لا من الذاكرة.\n'
    'المخطط المرجعي: `templates/mark-schema.json` ومفاتيح ملف واجهة أمس `web/meta/` كقالب.\n', encoding='utf-8')

# ── 3) الخطوات ──
def st(i, title, kind, phase, **kw):
    d = {'id': i, 'title': title, 'kind': kind, 'phase': phase,
         'assert': kw.pop('assert', []), 'links': kw.pop('links', {'rules': [], 'files': [], 'folders': [], 'gates': [], 'tests': []}),
         'on_fail': kw.pop('on_fail', 'stop')}
    d.update(kw)
    return d

def cmd(c, ok=None, warn=None):
    return {'command': ['bash', '-lc', f'B="$PWD"; SITE=/home/ubuntu/seawatch; export B SITE; {c}; rc=$?; exit $rc'],
            'ok_rc': ok or [0], 'warn_rc': warn or []}

steps = []
steps.append(st('S000', 'فحص المانيفست (verify) قبل أي خطوة', 'script', 'verify',
    **cmd('python3 tools/runbook.py verify'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'test -s docs/runbook.md']}]},
    links={'rules': ['الأمر التنفيذي: كتيب الإجراءات'], 'files': ['tools/runbook.py', 'runbook/runbook.json', 'docs/runbook.md'],
           'folders': [], 'gates': [], 'tests': ['tests/test_runbook_engine.sh']}))

pipe = [
 ('S010', 'استعادة المهارات وفحص التماثل', 'bash tools/restore_skills.sh', ['tools/restore_skills.sh'], [0]),
 ('S020', 'فحص التغذيات (40 مصدرًا)', 'python3 tools/check_feeds.py --date {date}', ['tools/check_feeds.py'], [0, 1]),
 ('S030', 'ترقيم التغذيات (أرقام لاتينية)', 'python3 tools/normalize_digits.py', ['tools/normalize_digits.py'], [0]),
 ('S040', 'توليد أهداف العقوبات من التقرير', 'python3 tools/ofac_targets_from_report.py --date {date}', ['tools/ofac_targets_from_report.py'], [0]),
 ('S050', 'فحص العقوبات (OFAC)', 'python3 tools/ofac_screen.py watchlist/ofac-targets.txt', ['tools/ofac_screen.py'], [0, 1]),
 ('S060', 'حفظ الأصول الرسمية', 'python3 tools/archive_originals.py {date} watchlist/originals-urls.txt', ['tools/archive_originals.py'], [0, 1]),
 ('S070', 'دمج الذاكرة التراكمية (دفتر اليوم)', 'python3 tools/merge_ledger_daily.py', ['tools/merge_ledger_daily.py'], [0]),
 ('S080', 'فرز التغذيات بالنموذج (اختياري)', 'python3 tools/llm_triage.py --input feeds/feeds-{date}.md', ['tools/llm_triage.py'], [0]),
 ('S090', 'مراجعة التقرير بالنموذج (اختياري)', 'python3 tools/llm_review.py --report reports/{date}-sectioned.md --limit 25', ['tools/llm_review.py'], [0]),
]
for i, t, c, files, oks in pipe:
    opt = i in ('S080', 'S090')
    d = st(i, t, 'script', 'ingest', **cmd(c, ok=[oks[0]], warn=oks[1:] if len(oks) > 1 else []),
           links={'rules': ['أ1 — سلسلة التشغيل اليومي'], 'files': files + ['sections/90-automation.md'],
                  'folders': [], 'gates': [], 'tests': []})
    if opt:
        d['optional'] = True
        d['on_fail'] = 'continue'
        d['assert'] = [{'type': 'cmd', 'command': ['bash', '-lc', 'true']}]
    else:
        d['assert'] = [{'type': 'cmd', 'command': ['bash', '-lc', f'test -s logs/runbook/{{date}}/{i}.log']}]
    steps.append(d)

steps.append(st('W010', 'كتابة التقرير اليومي', 'agent', 'write',
    prompt='runbook/prompts/write-report.md',
    reads=['sections/20-writing-brief.md', 'sections/20-lexicon.md', 'sections/20-examples.md',
           'sections/20-language.md', 'sections/75-style.md', 'appendices/editor-prompt.md',
           'cumulative-2026/daily/{date}.json', 'feeds/feeds-{date}.md'],
    writes=['reports/{date}-sectioned.md'],
    **{'assert': [{'type': 'min_bytes', 'path': 'reports/{date}-sectioned.md', 'n': 6000},
                  {'type': 'contains', 'path': 'reports/{date}-sectioned.md', 'text': '## '}]},
    links={'rules': ['أ2 — قواعد الكتابة', 'ل1 — أسلوب اللغة'], 'files': ['sections/20-writing-brief.md', 'sections/20-lexicon.md'],
           'folders': [], 'gates': [], 'tests': ['tests/test_runbook_engine.sh']}))
steps.append(st('W020', 'بناء ملف واجهة التقرير', 'agent', 'write',
    prompt='runbook/prompts/write-meta.md',
    reads=['reports/{date}-sectioned.md', 'templates/mark-schema.json'],
    writes=['web/meta/{date}.json'],
    **{'assert': [{'type': 'min_bytes', 'path': 'web/meta/{date}.json', 'n': 1500}]},
    links={'rules': ['ب2 — ترتيب الأقسام'], 'files': ['templates/mark-schema.json'],
           'folders': [], 'gates': [], 'tests': []}))

# ── 4) البوابات: كل سطر step في final_gate.sh يصير خطوة ──
fg = (R / 'tools/final_gate.sh').read_text(encoding='utf-8')
gate_lines = []
for line in fg.splitlines():
    m = re.match(r'^step(?:_strict)? "([^"]+)" (\d) (.*)$', line)
    if m:
        gate_lines.append((m.group(1), int(m.group(2)), m.group(3).strip(), False))
        continue
    m = re.match(r'^step_strict "([^"]+)" (.*)$', line)
    if m:
        gate_lines.append((m.group(1), 2, m.group(2).strip(), True))
gates = []
for n, (title, rc, command, strict) in enumerate(gate_lines, 1):
    gid = f'G{n:03d}'
    ok = [0]
    warn = [] if strict else ([1] if rc >= 2 else [])
    gates.append(st(gid, title, 'script', 'gates', **cmd(command, ok=ok, warn=warn),
        **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', f'test -s logs/runbook/{{date}}/{gid}.log']}]},
        links={'rules': ['ف1–ف5 — بوابة التحقق'], 'files': ['tools/final_gate.sh'],
               'folders': [], 'gates': [], 'tests': []}, gate_title=title))
steps += gates

steps.append(st('B010', 'بناء الموقع من البيانات', 'script', 'build',
    **cmd('cd "$SITE" && python3 generator/sync_from_brain.py --date {date} && python3 generator/build_site.py'),
    **{'assert': [{'type': 'file_exists', 'path': '/home/ubuntu/seawatch/dist/reports/{date}.html'}]},
    links={'rules': ['س1 — النشر'], 'files': ['/home/ubuntu/seawatch/generator/build_site.py', '/home/ubuntu/seawatch/generator/sync_from_brain.py'],
           'folders': ['/home/ubuntu/seawatch/generator'], 'gates': [], 'tests': []}))
steps.append(st('B020', 'تصدير PDF المعتمد', 'script', 'build',
    **cmd('python3 tools/export_report_assets.py --date {date} --only pdf'),
    **{'assert': [{'type': 'min_bytes', 'path': '/home/ubuntu/seawatch/dist/reports/pdf/{date}.pdf', 'n': 100000}]},
    links={'rules': ['س1 — النشر'], 'files': ['tools/export_report_assets.py'],
           'folders': [], 'gates': [], 'tests': []}))
steps.append(st('B030', 'بوابتا جودة الطباعة على PDF نفسه', 'script', 'build',
    **cmd('python3 validators/check_pdf_format.py --pdf /home/ubuntu/seawatch/dist/reports/pdf/{date}.pdf && '
          'python3 validators/check_print_quality.py --pdf /home/ubuntu/seawatch/dist/reports/pdf/{date}.pdf --date {date}'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'test -s logs/runbook/{date}/B030.log']}]},
    links={'rules': ['ف5 — شكل PDF وجودة الطباعة'],
           'files': ['validators/check_pdf_format.py', 'validators/check_print_quality.py'],
           'folders': [], 'gates': [], 'tests': []}))
steps.append(st('B040', 'نسخة Word طبق الأصل (اختيارية)', 'script', 'build', optional=True, on_fail='continue',
    **cmd('python3 tools/export_report_assets.py --date {date} --only word'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'true']}]},
    links={'rules': ['س1 — النشر'], 'files': ['tools/export_report_assets.py'],
           'folders': [], 'gates': [], 'tests': []}))

steps.append(st('D010', 'نشر الموقع (بعد كل البوابات)', 'script', 'deliver',
    **cmd('bash tools/publish_site.sh {date}'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'test -s logs/publish-{date}.json']}]},
    links={'rules': ['س2 — الإغلاق والدفع'], 'files': ['tools/publish_site.sh'],
           'folders': [], 'gates': [], 'tests': ['tests/test_no_publish_without_runbook.sh']}))
steps.append(st('D020', 'التحقق الحي من النشر (قراءة فقط)', 'script', 'deliver',
    **cmd('bash tools/check_live.sh {date}'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'test -s logs/live-{date}.json']}]},
    links={'rules': ['س2 — الإغلاق والدفع'], 'files': ['tools/check_live.sh'],
           'folders': [], 'gates': [], 'tests': []}))
steps.append(st('D030', 'إرسال الملخص وPDF على تلغرام', 'script', 'deliver', optional=True, on_fail='continue',
    **cmd('bash tools/publish_site.sh --telegram {date}'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'true']}]},
    links={'rules': ['س4 — قناة التسليم'], 'files': ['tools/telegram_send.py'],
           'folders': [], 'gates': [], 'tests': ['tests/test_no_publish_without_runbook.sh']}))
steps.append(st('D040', 'النسخة الاحتياطية والتحقق من التماثل', 'script', 'deliver',
    **cmd('bash tools/github_backup.sh && python3 validators/check_backup_parity.py --mode strict'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'test -s logs/runbook/{date}/D040.log']}]},
    links={'rules': ['س2 — الإغلاق والدفع'], 'files': ['tools/github_backup.sh', 'validators/check_backup_parity.py'],
           'folders': [], 'gates': [], 'tests': []}))
steps.append(st('D050', 'التعلم الذاتي وتسجيل الدروس', 'script', 'deliver',
    **cmd('python3 tools/self_improve.py --date {date} --window 7; python3 tools/skill_lessons.py --date {date}'),
    **{'assert': [{'type': 'file_exists', 'path': 'memory/learning-log.jsonl'}]},
    links={'rules': ['س2 — الإغلاق والدفع'], 'files': ['tools/self_improve.py', 'tools/skill_lessons.py'],
           'folders': [], 'gates': [], 'tests': ['tests/test_skill_lessons.py']}))
steps.append(st('D060', 'تسجيل رموز التقدير والأحداث', 'script', 'deliver',
    **cmd('python3 tools/register_estimate.py --date {date} --check'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'true']}]},
    links={'rules': ['ب2 — ترتيب الأقسام'], 'files': ['tools/register_estimate.py'],
           'folders': [], 'gates': [], 'tests': []}))
steps.append(st('Q010', 'تدقيق المكتبات والمهارات (أسبوعي)', 'script', 'maintenance', schedule='weekly',
    **cmd('python3 validators/check_library_use.py --date {date}; python3 validators/check_libraries_skills.py'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'test -s logs/runbook/{date}/Q010.log']}]},
    links={'rules': ['ف3 — بوابات المكتبات'], 'files': ['validators/check_library_use.py', 'validators/check_libraries_skills.py'],
           'folders': [], 'gates': [], 'tests': []}))
steps.append(st('Q020', 'قياس دقة التقدير (ربع سنوي)', 'script', 'maintenance', schedule='quarterly',
    **cmd('python3 tools/estimate_accuracy.py'),
    **{'assert': [{'type': 'cmd', 'command': ['bash', '-lc', 'true']}]},
    links={'rules': ['ف4 — قراءة الموقف وتحليل المؤشرات'], 'files': ['tools/estimate_accuracy.py'],
           'folders': [], 'gates': [], 'tests': []}))

manifest = {
 'version': 1,
 'ledger_dir': 'logs/runbook',
 'sections': sections,
 'exempt': [
   'reports/*', 'web/*', 'feeds/*', 'archive/*', 'cumulative-2026/*', 'memory/*', 'notes/*', 'audit/*',
   'docs/*', 'watchlist/*', 'logs/*', 'templates/*', 'appendices/*', 'skills/*', 'tools/_oneoff/*',
   'runbook/*', 'design/*', '*.txt', '*.pdf', '*.docx', '*.png', '*.jpg',
 ],
 'exempt_reasons': {
   'reports/*': 'مخرجات: نصوص التقارير المولَّدة (يكتبها محرّك/الوكيل في خطوة W010)',
   'web/*': 'مخرجات: ملفات واجهة التقارير',
   'feeds/*': 'بيانات: خلاصات المصادر الخام',
   'archive/*': 'بيانات: أصول رسمية محفوظة',
   'cumulative-2026/*': 'بيانات: الدفتر التراكمي',
   'memory/*': 'بيانات: سجلات التعلم والذاكرة',
   'notes/*': 'سجلات عمل مؤقتة',
   'audit/*': 'سجلات: الأعطال والتدقيق',
   'docs/*': 'وثائق مولَّدة (منها الكتيب)',
   'watchlist/*': 'بيانات: قوائم المراقبة',
   'logs/*': 'مخرجات تشغيل',
   'templates/*': 'قوالب: مرتبطة بالخطوات التي تستعملها',
   'appendices/*': 'ملاحق مرجعية: مربوطة بالخطوات عبر links.files',
   'skills/*': 'نسخة المهارات داخل المستودع',
   'tools/_oneoff/*': 'أدوات تاريخية لمرة واحدة (مُبقاة للسجل)',
   'runbook/runbook.json': 'المصدر الوحيد للحقيقة (يستثني نفسه من التغطية)',
   'tools/runbook.py': 'المحرّك نفسه',
   'docs/runbook.md': 'الكتيب المولَّد من المانيفست',
   '*.txt': 'ملفات نصية مساعدة', '*.pdf': 'مخرجات', '*.docx': 'مخرجات', '*.png': 'صور', '*.jpg': 'صور',
 },
 'steps': steps,
}
out = R / 'runbook/runbook.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'  ✔ المانيفست: {len(steps)} خطوة ({len(gates)} بوابة) · {len(sections)} قسمًا · {len(manifest["exempt"])} نمط استثناء')
print(f'  ✔ برومتات الأقسام: {len(list(prompt_dir.glob("*.md")))} · اختبارات الأقسام: {len(list(test_dir.glob("*.sh")))}')