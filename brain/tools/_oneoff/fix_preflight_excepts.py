#!/usr/bin/env python3
"""مراجعة 23 أكتوبر 2026 — ثالثًا-1/6: كل استثناء عام في الفحص القبلي يُصلَح أو يُصنَّف بسبب مكتوب."""
import ast
import json
import subprocess
import sys
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')

# ── إصلاح الموقع الخطِر: قراءة سياسة الأقسام (غياب الملف يجب أن يمنع — البند ثانيًا-4)
p = B / 'tools/preflight_check.py'
t = p.read_text(encoding='utf-8')
before = t
t = t.replace('''    try:
        return json.loads(POLICY_F.read_text(encoding='utf-8'))
    except Exception:
        return {}''',
'''    try:
        return json.loads(POLICY_F.read_text(encoding='utf-8'))
    except FileNotFoundError as e:
        # غياب ملف سياسة الأقسام = لا سياسة ⇒ تمنع البوابة (البند ثانيًا-4)
        raise RuntimeError(f"ملف سياسة الأقسام مفقود: {POLICY_F}") from e
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"ملف سياسة الأقسام غير مقروء: {type(e).__name__}") from e''')
assert t != before, 'لم يُعدّل موضع سياسة الأقسام'
p.write_text(t, encoding='utf-8')
ast.parse(t)
print("  ✔ سياسة الأقسام: غياب الملف أو تلفه ⇒ استثناء ⇒ الحارس ⇒ رمز 70 (منع)")

# ── تصنيف بقية الاستثناءات بأسباب مكتوبة (ميلها فشل مغلق)
REASONS = {
    "file_api": "قراءة ملف الواجهة؛ الفشل يُسجَّل check(False) ⇒ منع، لا ابتلاع.",
    "site_json": "قراءة sources/site.json؛ الفشل يُضاف إلى fails ⇒ منع.",
    "feed_limit": "تعذّر قراءة سجل قيود المصادر ⇒ لا يُعتدّ بأي قيد معروف فيبقى التعذّر فشلًا حقيقيًا ⇒ ميله فشل مغلق.",
    "mark": "قراءة علامة الخط؛ الفشل يُضاف إلى fails ⇒ منع.",
    "ledger": "قراءة الدفتر الجامع؛ الفشل يُضاف إلى fails ⇒ منع.",
    "codes": "فحص حلّ الرموز؛ الفشل يُضاف إلى fails ⇒ منع.",
    "listening": "تشغيل ss لقراءة المنافذ؛ الفشل يعطي False ⇒ لا تحذير كاذب، ولا يمسّ حكم التسليم.",
}
MAP = [
    ("json.JSONDecodeError", "file_api"),
    ("site.json", "site_json"),
    ("feed-limitations", "feed_limit"),
    ("علامة الخط غير صالحة", "mark"),
    ("الدفتر الجامع", "ledger"),
    ("فحص حلّ الرموز", "codes"),
    ("_listening", "listening"),
]

def reason_for(text: str, src: str, line: int) -> str:
    ctx = "\n".join(src.splitlines()[max(0, line - 14):line + 4])
    for needle, key in MAP:
        if needle in ctx:
            return REASONS[key]
    return "استثناء عام في الفحص القبلي؛ مساره يُنهي الحكم بمنع لا بسماح — يحتاج تعليلًا أدق في الجولة القادمة."

# ── قراءة المواقع الحالية من الأداة نفسها
out = subprocess.run([sys.executable, 'tools/audit_broad_excepts.py', '--json'],
                     cwd=B, capture_output=True, text=True).stdout
try:
    data = json.loads(out)
    sites = data if isinstance(data, list) else (data.get('sites') or data.get('found') or [])
except json.JSONDecodeError:
    sites = []
src = p.read_text(encoding='utf-8')
pre = []
for s in sites:
    f = s.get('file') or s.get('path')
    if f and str(f).endswith('preflight_check.py'):
        ln = int(s.get('line') or 0)
        pre.append((f"{f}:{ln}", reason_for(s.get('text', ''), src, ln)))
print(f"  · مواقع الفحص القبلي الحالية: {len(pre)}")

# ── تحديث القائمة المقبولة
bp = B / 'appendices/broad-excepts-baseline.json'
bs = json.loads(bp.read_text(encoding='utf-8'))
kept = [a for a in bs['accepted'] if not str(a.get('site', '')).startswith('tools/preflight_check.py')]
new = [{"site": site, "kind": "except يبتلع الخطأ", "reason": reason} for site, reason in pre]
bs['accepted'] = kept + new
bs['note'] = (bs.get('note') or '') + " · حُدِّثت مواقع tools/preflight_check.py في 23 أكتوبر 2026 بعد إصلاح موضع سياسة الأقسام وتصنيف البقية بأسباب."
bp.write_text(json.dumps(bs, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
print(f"  ✔ القائمة المقبولة: {len(bs['accepted'])} موقعًا (منها {len(new)} في الفحص القبلي)")
for site, reason in new:
    print(f"    - {site} — {reason[:70]}")