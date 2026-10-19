#!/usr/bin/env python3
"""يزامن بصمة نمط الطباعة في الملف التعريفي مع المولّد الحالي (للمعايرة فقط)."""
import hashlib, json
from pathlib import Path
B = Path('/home/ubuntu/brain-marine-news')
src = Path('/home/ubuntu/seawatch/generator/build_report.py').read_text(encoding='utf-8')
k = src.find('@media print'); d = 0; m = k
while m < len(src):
    if src[m] == '{': d += 1
    elif src[m] == '}':
        d -= 1
        if d == 0: break
    m += 1
css = src[k:m+1]
p = B / 'templates' / 'approved-pdf' / 'print-profile.json'
prof = json.loads(p.read_text(encoding='utf-8'))
prof['print_css_sha16'] = hashlib.sha256(css.encode()).hexdigest()[:16]
p.write_text(json.dumps(prof, ensure_ascii=False, indent=1), encoding='utf-8')
print('  بصمة النمط الحالية:', prof['print_css_sha16'])
