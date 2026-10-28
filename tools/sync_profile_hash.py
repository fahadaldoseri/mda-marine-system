#!/usr/bin/env python3
"""يزامن بصمة نمط الطباعة في الملف التعريفي مع المولّد الحالي (للمعايرة فقط)."""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")
import hashlib, json
from pathlib import Path
B = Path(f'{BRAIN}')
src = Path(f'{SITE}/generator/build_report.py').read_text(encoding='utf-8')
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
