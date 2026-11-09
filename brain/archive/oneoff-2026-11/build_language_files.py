#!/usr/bin/env python3
"""يستخرج ملفات الخطوة 1 من نص الأمر التنفيذي حرفيًا (لا كتابة يدوية).

المصدر: /home/ubuntu/upload/Pasted_content_13.txt
القاعدة: يُنسخ المقطع كما هو، بلا تحرير ولا إعادة صياغة.
"""
import re
import sys
from pathlib import Path

SRC = Path('/home/ubuntu/upload/Pasted_content_13.txt')
B = Path('/home/ubuntu/brain-marine-news')

TARGETS = {
    'أ': 'sections/20-writing-brief.md',
    'ب': 'sections/20-lexicon.md',
    'ج': 'sections/20-examples.md',
    'د': 'appendices/editor-prompt.md',
    'هـ': 'tools/style_metrics.py',
    'و': 'tools/preserve_check.py',
    'ز': 'validators/check_orthography.py',
    'ح': 'tools/meaning_compare.py',
    'ط': 'tools/extract_ui_strings.py',
}

lines = SRC.read_text(encoding='utf-8').splitlines()
heads = {}
for i, ln in enumerate(lines):
    m = re.match(r'^## القسم «(.+?)» — `(.+?)`\s*$', ln)
    if m:
        heads[m.group(1)] = (i, m.group(2))
if not heads:
    print('  ✘ لم أجد ترويسات الأقسام'); sys.exit(1)

ok, bad = [], []
for key, target in TARGETS.items():
    if key not in heads:
        bad.append(f'{key}: لا ترويسة'); continue
    i, declared = heads[key]
    # المقطع: من بعد الترويسة حتى فاصل الشيفرة أو سطر «---»
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    body = []
    if lines[j].startswith('~~~'):
        fence = lines[j]
        j += 1
        while j < len(lines) and not lines[j].startswith('~~~'):
            body.append(lines[j]); j += 1
    else:
        while j < len(lines) and lines[j].strip() != '---':
            body.append(lines[j]); j += 1
    while body and not body[-1].strip():
        body.pop()
    text = '\n'.join(body) + '\n'
    if len(body) < 5:
        bad.append(f'{key}: المقطع قصير ({len(body)} سطرًا)'); continue
    dst = B / target
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding='utf-8')
    ok.append((key, target, len(body), len(text.encode()), declared))

print('  الملفات المنشأة من نص الأمر (حرفيًا):')
for key, target, n, b, declared in ok:
    flag = '' if declared == target else f'  ⚠ الترويسة تذكر {declared}'
    print(f'    «{key}» {target:42s} {n:4d} سطرًا · {b:7d} بايت{flag}')
if bad:
    print('  ✘ فشل:'); [print('    ·', b) for b in bad]; sys.exit(1)
print(f'  ✔ {len(ok)} ملفًا')