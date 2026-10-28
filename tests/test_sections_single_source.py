#!/usr/bin/env python3
"""اختبار: لا يُكتب عنوان قسم أو ترتيبه حرفيًا خارج سجل الأقسام في المانيفست.
قائمة السماح المعلنة أدناه = مواضع قيد الترحيل إلى السجل (لا تُوسَّع بلا قرار مكتوب)."""
import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
m = json.loads((R / 'runbook/runbook.json').read_text(encoding='utf-8'))
titles = [s['title'] for s in m['sections']]

ALLOW = {
    'runbook/runbook.json': 'السجل نفسه',
    'docs/runbook.md': 'الكتيب المولَّد',
    'sections/30-structure.md': 'المصدر الأصلي — قيد الترحيل إلى السجل',
    'reports/': 'نصوص التقارير (تكتب الأقسام فعليًا)',
    'archive/': 'أصول محفوظة',
    'audit/': 'سجلات تدقيق تاريخية',
    'notes/': 'سجلات عمل',
    'web/': 'ملفات واجهة مولَّدة',
    'design/': 'حزمة تصميم خارجية',
    'feeds/': 'خلاصات المصادر',
    'appendices/': 'ملاحق مرجعية',
}
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'logs', '.venv', 'cumulative-2026', 'watchlist', 'templates', 'tests'}

hits = {}
for d, dirs, files in os.walk(R):
    dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
    for f in files:
        if not f.endswith(('.py', '.sh', '.md', '.json', '.mjs', '.js', '.css', '.html')):
            continue
        p = Path(d) / f
        rel = str(p.relative_to(R))
        if rel in ALLOW or any(rel.startswith(k) for k in ALLOW if k.endswith('/')):
            continue
        try:
            txt = p.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        found = [t for t in titles if t in txt]
        if found:
            hits[rel] = found

if hits:
    print(f'✘ عناوين أقسام مكتوبة حرفيًا خارج السجل في {len(hits)} ملفًا:')
    for rel, found in sorted(hits.items())[:20]:
        print(f'  · {rel}: {len(found)} عنوانًا — مثال: {found[0]}')
    print(f'\nقائمة السماح المعلنة: {len(ALLOW)} موضعًا')
    sys.exit(2)
print('✔ لا عنوان قسم مكتوب حرفيًا خارج سجل الأقسام (خارج قائمة السماح المعلنة)')
sys.exit(0)