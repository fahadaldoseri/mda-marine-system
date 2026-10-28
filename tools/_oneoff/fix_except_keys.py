#!/usr/bin/env python3
"""ثالثًا-2/6: مفتاح الموقع يميّز الاستثناء (أول سطر من كتلة try) بدل «try:» المتشابه،
والحكم يُقارن بالقائمة المقبولة لا بعدد المواقع."""
import ast
import json
import subprocess
import sys
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')
p = B / 'tools/audit_broad_excepts.py'
t = p.read_text(encoding='utf-8')

t = t.replace('''def site_key(row: dict) -> str:
    """مفتاح الموقع: الملف + نص عبارة الاستثناء الطبيعي — لا رقم السطر (يتزحزح)."""
    txt = re.sub(r"\\s+", " ", (row.get("text") or "").replace("try:", "except")).strip()
    return f"{row.get('file')}::{txt[:60]}"''',
'''def site_key(row: dict) -> str:
    """مفتاح الموقع: الملف + أول سطر ذي معنى من كتلة try — لا رقم السطر (يتزحزح)."""
    snip = re.sub(r"\\s+", " ", (row.get("snippet") or "")).strip()
    return f"{row.get('file')}::{snip[:70]}"''')

t = t.replace('''            out.append({"file": str(p.relative_to(B)), "line": n.lineno,
                        "kind": "except يبتلع الخطأ", "text": seg.splitlines()[0].strip()})''',
'''            first = next((l.strip() for l in seg.splitlines()[1:] if l.strip()), "")
            out.append({"file": str(p.relative_to(B)), "line": n.lineno,
                        "kind": "except يبتلع الخطأ", "text": seg.splitlines()[0].strip(),
                        "snippet": first})''')

t = t.replace('''    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:''',
'''    base_f = B / "appendices" / "broad-excepts-baseline.json"
    known = set()
    if base_f.exists():
        bs = json.loads(base_f.read_text(encoding="utf-8"))
        known = {site_key(r) for r in (bs.get("accepted") or []) if r.get("snippet")}
    fresh = [r for r in rows if site_key(r) not in known] if known else rows
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    else:''')
t = t.replace('''            print(f"  · استثناءات عامة تبتلع الخطأ: {len(rows)}")''',
'''            print(f"  · استثناءات عامة تبتلع الخطأ: {len(rows)} — غير مصنّفة: {len(fresh)}")''')
t = t.replace('''    return 1 if rows else 0''', '''    return 1 if fresh else 0''')
p.write_text(t, encoding='utf-8')
ast.parse(t)
print("  ✔ الأداة: مفتاح مميّز + حكم بمقارنة القائمة المقبولة")

# ── تجديد القائمة بالمفاتيح الجديدة، مع الحفاظ على التعليلات المكتوبة
rows = json.loads(subprocess.run([sys.executable, 'tools/audit_broad_excepts.py', '--json'],
                                 cwd=B, capture_output=True, text=True).stdout)
bp = B / 'appendices/broad-excepts-baseline.json'
bs = json.loads(bp.read_text(encoding='utf-8'))
old = {}
for a in bs.get('accepted', []):
    old.setdefault(a.get('file'), []).append(a)
PRE = {
    "subprocess.run(['git'": "قراءة مساعد اعتماد الدفع؛ التعذّر يُضاف إلى fails ⇒ منع.",
    "json.loads(POLICY_F": "سياسة الأقسام — صار الغياب والتلف يرفعان استثناءً ⇒ رمز 70 (منع).",
    "json.loads((B / 'appendices' / 'feed-limitations.json')": "تعذّر قراءة سجل قيود المصادر ⇒ لا يُعتدّ بأي قيد ⇒ التعذّر يبقى فشلًا حقيقيًا (فشل مغلق).",
    "json.loads((B / 'cumulative-2026' / 'daily'": "قراءة ملف يوم من الدفتر؛ الفشل يُضاف إلى fails ⇒ منع.",
    "md = json.loads(master.read_text": "قراءة الدفتر الجامع؛ الفشل يُضاف إلى fails ⇒ منع.",
    "known = set(json.loads(cmap.read_text": "فحص حلّ الرموز؛ الفشل يُضاف إلى fails ⇒ منع.",
    "_sp.run(['bash', '-lc', f\"ss -ltn": "قراءة المنافذ؛ الفشل يعطي False ⇒ لا تحذير كاذب ولا أثر على حكم التسليم.",
}
accepted, unclassified = [], []
for r in rows:
    f, snip = r.get('file'), (r.get('snippet') or '')
    reason = None
    for needle, why in PRE.items():
        if needle in snip:
            reason = why
            break
    if reason is None:
        pool = old.get(f, [])
        if pool:
            reason = pool.pop(0).get('reason')
    entry = {"site": f"{f}:{r.get('line')}", "file": f, "kind": r.get('kind'),
             "snippet": snip[:110], "reason": reason}
    (accepted if reason else unclassified).append(entry)
bs['accepted'] = accepted
bs['unclassified'] = unclassified
bs['note'] = (bs.get('note') or '') + " · 23 أكتوبر 2026: المفتاح = الملف + أول سطر من كتلة try؛ والحكم يُقارن بالقائمة المقبولة."
bp.write_text(json.dumps(bs, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
print(f"  ✔ القائمة: {len(accepted)} موقعًا بتعليل · غير مصنّفة: {len(unclassified)}")
for u in unclassified[:10]:
    print(f"    ✘ {u['site']} — {u['snippet'][:70]}")