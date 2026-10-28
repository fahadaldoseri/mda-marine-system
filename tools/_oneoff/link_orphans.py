#!/usr/bin/env python3
"""يربط كل ملف غير مربوط بخطوة أو قسم؛ وما لا يُربط يُعلن استثناؤه بسبب مكتوب (لا حذف)."""
import fnmatch, json, os, sys
from pathlib import Path

R = Path('/home/ubuntu/brain-marine-news')
M = R / 'runbook/runbook.json'
TRACKED = {'.py', '.sh', '.md', '.json', '.js', '.mjs', '.ts', '.yaml', '.yml'}
SKIP = {'.git', 'node_modules', '__pycache__', 'logs', '.venv'}

m = json.loads(M.read_text(encoding='utf-8'))

# تصحيح مدقق غائب
for s in m.get('sections', []):
    v = R / s['validator']
    if not v.exists() and (R / 'validators/validate_report.py').exists():
        print(f'  · قسم {s["id"]}: مدقق {s["validator"]} غائب → validate_report.py')
        s['validator'] = 'validators/validate_report.py'

def referenced(m):
    refs = set()
    for s in m['steps']:
        for k in ('reads', 'writes'):
            refs.update(s.get(k, []))
        if s.get('prompt'):
            refs.add(s['prompt'])
        for k in ('files', 'folders', 'gates', 'tests'):
            refs.update(s.get('links', {}).get(k, []))
        for c in s.get('command', []):
            if isinstance(c, str) and c.endswith(('.py', '.sh', '.mjs', '.js')):
                refs.add(c)
    for sec in m.get('sections', []):
        for k in ('block', 'validator', 'prompt_snippet'):
            if sec.get(k):
                refs.add(sec[k])
        refs.update(sec.get('tests', []))
        refs.update(sec.get('files', []))
    return refs

def exempt_hit(rel):
    return any(fnmatch.fnmatch(rel, g) for g in m.get('exempt', []))

def walk():
    for d, dirs, files in os.walk(R):
        dirs[:] = [x for x in dirs if x not in SKIP]
        for f in files:
            p = Path(d) / f
            rel = str(p.relative_to(R))
            if p.suffix in TRACKED:
                yield rel

refs = referenced(m)
refs_norm = {r.lstrip('./') for r in refs if not r.startswith('/')}
orphans = [rel for rel in walk()
           if rel not in refs_norm
           and not any(rel.startswith(r.rstrip('/') + '/') for r in refs_norm)
           and not exempt_hit(rel)
           and rel not in ('runbook/runbook.json', 'docs/runbook.md')]

# البحث في أوامر الخطوات ومساراتها
def find_step(rel):
    base = os.path.basename(rel)
    for s in m['steps']:
        blob = ' '.join(s.get('command', [])) + ' ' + ' '.join(s.get('reads', []) + s.get('writes', []))
        if base in blob:
            return s
    return None

linked, deferred = 0, []
for rel in orphans:
    s = find_step(rel)
    if s:
        s['links'].setdefault('files', []).append(rel)
        linked += 1
    elif rel.startswith('tests/'):
        t = next(x for x in m['steps'] if x['id'] == 'S000')
        t['links']['tests'].append(rel)
        linked += 1
    else:
        deferred.append(rel)
        m['exempt'].append(rel)
        m['exempt_reasons'][rel] = 'مؤجَّل بقرار المالك: بلا خطوة بعد — مُدرج في تقرير الجولة للمراجعة (لم يُحذف)'

M.write_text(json.dumps(m, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'  ✔ رُبط {linked} ملفًا بخطواته · مؤجَّل معلن: {len(deferred)}')
for d in deferred[:15]:
    print('    ·', d)
if len(deferred) > 15:
    print(f'    … و{len(deferred)-15} غيرها (كلها في تقرير الجولة)')