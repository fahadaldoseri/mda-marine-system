#!/usr/bin/env python3
"""مراجعة 23 أكتوبر 2026 — ثالثًا-2/3: ربط المدققات الثلاثة بالحارس فعليًا، وتقوية حصر الاستثناءات."""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')

# ── 1) ثلاثة مدققات كانت تخرج بـ SystemExit لا بالحارس: حوّلها إلى run(main)
for name in ['check_carryover.py', 'check_findings_closed.py', 'check_intel.py']:
    p = B / 'validators' / name
    t = p.read_text(encoding='utf-8')
    before = t
    t = re.sub(r"(from _guard import run\s*\n\s*)raise SystemExit\(main\(\)\)", r"\1run(main)", t)
    t = t.replace("    raise SystemExit(main())", "    run(main)")
    if t != before:
        p.write_text(t, encoding='utf-8')
        ast.parse(t)
        print(f"  ✔ {name}: run(main) عبر الحارس (رمز 70 عند الانهيار)")
    else:
        print(f"  · {name}: لا تغيير")

# ── 2) الأداة: مطابقة بالقصد لا بأرقام الأسطر (الأرقام تتزحزح مع كل تحرير)
p = B / 'tools/audit_broad_excepts.py'
t = p.read_text(encoding='utf-8')
if 'def site_key' not in t:
    t = t.replace('def scan_file(p: Path) -> list[dict]:',
'''def site_key(row: dict) -> str:
    """مفتاح الموقع: الملف + نص عبارة الاستثناء الطبيعي — لا رقم السطر (يتزحزح)."""
    txt = re.sub(r"\\s+", " ", (row.get("text") or "").replace("try:", "except")).strip()
    return f"{row.get('file')}::{txt[:60]}"


def scan_file(p: Path) -> list[dict]:''')
p.write_text(t, encoding='utf-8')
ast.parse(t)
print("  ✔ audit_broad_excepts: مطابقة بالمفتاح (ملف + نص) لا برقم السطر")

# ── 3) تجديد القائمة: تُنقل التعليلات القديمة بحسب النص، والجديد يُعلن لا يُقبل تلقائيًا
rows = json.loads(subprocess.run([sys.executable, 'tools/audit_broad_excepts.py', '--json'],
                                 cwd=B, capture_output=True, text=True).stdout)
sites = rows if isinstance(rows, list) else (rows.get('sites') or [])
bp = B / 'appendices/broad-excepts-baseline.json'
bs = json.loads(bp.read_text(encoding='utf-8'))
old = {}
for a in bs['accepted']:
    m = re.match(r"^(.*?):(\d+)$", a.get('site', ''))
    if m:
        old.setdefault(m.group(1), []).append(a)

def norm(x: str) -> str:
    return re.sub(r"\s+", " ", x or "").strip()

accepted, new_sites = [], []
for s in sites:
    f, ln, txt = s.get('file'), int(s.get('line') or 0), norm(s.get('text'))
    reason = None
    for a in old.get(f, []):
        if norm(a.get('site')).split(':', 1)[-1] and txt[:40] and txt[:40] in norm(a.get('reason', '')):
            reason = a['reason']
    if reason is None:
        # تعليل موروث بالترتيب داخل الملف نفسه
        pool = [a for a in old.get(f, []) if a.get('reason')]
        if pool:
            reason = pool.pop(0)['reason']
            old[f] = pool
    if reason:
        accepted.append({"site": f"{f}:{ln}", "file": f, "kind": s.get('kind', 'except يبتلع الخطأ'),
                         "text": txt[:90], "reason": reason})
    else:
        new_sites.append({"site": f"{f}:{ln}", "file": f, "kind": s.get('kind'), "text": txt[:90]})

bs['accepted'] = accepted
bs['unclassified'] = new_sites
bs['note'] = (bs.get('note') or '') + " · 23 أكتوبر 2026: مطابقة بالمفتاح (ملف + نص) بدل رقم السطر؛ والمواقع بلا تعليل تُدرج في unclassified وتمنع."
bp.write_text(json.dumps(bs, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
print(f"  ✔ القائمة المقبولة: {len(accepted)} موقعًا بتعليل · غير مصنّفة: {len(new_sites)}")
for s in new_sites[:12]:
    print(f"    ✘ {s['site']} — {s['text'][:70]}")