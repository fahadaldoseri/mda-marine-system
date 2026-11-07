#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يبني بيانات ملحق موثوقية المصادر من جدول مصادر التقرير + سجل الموثوقية الثابت.
الاستخدام: python3 tools/build_source_reliability.py <تقرير.md> <ملف-الواجهة.json> [<ملف-الواجهة2.json> ...]"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)
import json, re, sys
from pathlib import Path

ROOT = Path(f'{BRAIN}')
REG = {r[0]: r for r in json.loads((ROOT / 'appendices/source-reliability-40.json').read_text(encoding='utf-8'))}

def main():
    md_path, metas = Path(sys.argv[1]), [Path(a) for a in sys.argv[2:]]
    rows = {}
    for line in md_path.read_text(encoding='utf-8').splitlines():
        m = re.match(r'^\|\s*(\d+)\s*\|\s*\[(.+?)\]\((\S+?)\)\s*\|\s*(.+?)\s*\|\s*$', line.strip())
        if m:
            rows[int(m.group(1))] = {'name': m.group(2), 'url': m.group(3), 'status': re.sub(r'\*\*', '', m.group(4))}
    cited = []
    for num in sorted(rows):
        st = rows[num]['status']
        if 'استُشهد به' in st:
            reg = REG.get(num)
            cited.append({
                'num': num,
                'name': (reg[1] if reg else rows[num]['name']),
                'url': rows[num]['url'],
                'rel': reg[4] if reg else '—',
                'cred': reg[5] if reg else '—',
                'basis': (reg[6] if reg else '') + (' · حالة التشغيل: ' + st.split('؛')[-1].strip()[:110] if '؛' in st else ''),
            })
    data = {'checked': len(rows), 'cited': len(cited), 'rows': cited}
    for p in metas:
        d = json.loads(p.read_text(encoding='utf-8'))
        d['source_reliability'] = data
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"  ✔ {p.name}: {len(cited)} مستشهدًا من {len(rows)} مفحوصًا")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
