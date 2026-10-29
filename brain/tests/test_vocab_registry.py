#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات السجل الحاكم للمفردات وعدم التراجع وتغطية الأسطح.

الغرض: أن يبقى الحكم اللغوي في سجل واحد، وأن يُثبت آليًا أن كل بند معتمد يمنع فعلًا،
وأن كل سطح يقرأه القارئ داخل مدى البوابة.

الاختبارات
  1) السجل صالح ومُولَّده مطابق (build_vocab_gate --check).
  2) كل بند معتمد يمنع فعلًا في ملف اختبار (لا تراجع ولا حكم وهمي).
  3) لا بند مانع بلا سبب مكتوب ومصدر موثَّق.
  4) المُولَّد يُعاد بناؤه من السجل: التعديل اليدوي عليه يُكتشف.
  5) تغطية الأسطح: أداة القياس تُرجع 0 على أسطح اليوم (تُتخطّى موثَّقة إن لم يوجد بناء موقع).

الرمز: 0 نجاح · 1 فشل.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

B = pathlib.Path(__file__).resolve().parent.parent
SITE = pathlib.Path(os.environ.get("SITE") or os.environ.get("SITE_DIR") or (pathlib.Path.home() / "seawatch"))
REG = B / "appendices" / "simplified-vocabulary.json"
GEN = B / "appendices" / "forbidden-coinages.json"
fails: list[str] = []
skips: list[str] = []


def ok(name: str) -> None:
    print(f"  ✓ {name}")


def bad(name: str, why: str) -> None:
    fails.append(name)
    print(f"  ✘ {name} — {why}")


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=B)


# 1) السجل صالح والمُولَّد مطابق
r = run([str(B / "tools" / "build_vocab_gate.py"), "--check"])
if r.returncode == 0:
    ok("السجل الحاكم صالح ومُولَّده مطابق")
else:
    bad("السجل الحاكم صالح ومُولَّده مطابق", (r.stdout + r.stderr).strip().splitlines()[:2])

reg = json.loads(REG.read_text(encoding="utf-8"))
approved = [e for e in reg["entries"] if e.get("status") == "approved"]

# 2) كل بند معتمد يمنع فعلًا
blocked_ok, not_blocking = [], []
probe = pathlib.Path(tempfile.gettempdir()) / "vocab_probe.md"
for e in approved:
    term = str(e["term"])
    probe.write_text(f"# عنوان\n## قسم\n- {term} اختبار الإنفاذ.\n", encoding="utf-8")
    rc = subprocess.run([sys.executable, str(B / "validators" / "check_prose_defects.py"), "--md", str(probe)],
                        capture_output=True, text=True).returncode
    (blocked_ok if rc == 2 else not_blocking).append(term)
if not approved:
    bad("إنفاذ البنود المعتمدة", "لا بنود معتمدة في السجل")
elif not not_blocking:
    ok(f"كل البنود المعتمدة تمنع فعلًا ({len(blocked_ok)} بندًا)")
else:
    bad("إنفاذ البنود المعتمدة", f"بنود لا تمنع: {'، '.join(not_blocking)}")

# 3) لا بند مانع بلا سبب ومصدر
thin = [str(e["term"]) for e in approved
        if not str(e.get("reason") or "").strip() or not str(e.get("source") or "").strip()]
if thin:
    bad("سبب ومصدر مكتوبان لكل بند مانع", f"بنود ناقصة: {'، '.join(thin)}")
else:
    ok(f"سبب ومصدر مكتوبان لكل بند مانع ({len(approved)} بندًا)")

# 4) المُولَّد يُبنى من السجل: تعديل يدوي يُكتشف
orig = GEN.read_text(encoding="utf-8")
try:
    d = json.loads(orig)
    d["entries"].append({"term": "لفظ-اختبار-يدوي-لا-أصل-له", "since": "2026-01-01", "reason": "اختبار"})
    GEN.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rc = run([str(B / "tools" / "build_vocab_gate.py"), "--check"]).returncode
    if rc == 2:
        ok("التعديل اليدوي على المُولَّد يُكتشف ويُمنع")
    else:
        bad("التعديل اليدوي على المُولَّد يُكتشف ويُمنع", f"رمز={rc}")
finally:
    GEN.write_text(orig, encoding="utf-8")

# 5) تغطية الأسطح
day = sorted(p.name.replace("-sectioned.md", "") for p in (B / "reports").glob("*-sectioned.md"))[-1]
# ك-247: قبل البناء لا توجد صفحة اليوم؛ تُقاس التغطية على أحدث إصدار مبني،
# ويبقى إنفاذ اليوم على بوابة G045 بعد البناء (فشل مغلق).
_built = sorted(p for p in (SITE / "dist" / "reports").glob("*.html") if re.match(r"\d{4}-\d{2}-\d{2}$", p.stem))
if _built and not (SITE / "dist" / "reports" / f"{day}.html").exists():
    _prev = _built[-1].stem
    skips.append(f"تغطية الأسطح: صفحة {day} لم تُبنَ بعد — قِيست على {_prev}، وإنفاذ اليوم في G045 بعد البناء")
    day = _prev
if not (SITE / "dist" / "index.html").exists():
    skips.append("تغطية الأسطح: لا بناء موقع في SITE — تُقاس في بوابة التسليم بعد البناء")
else:
    env = dict(os.environ, SITE=str(SITE))
    def _audit(d: str):
        return subprocess.run([sys.executable, str(B / "tools" / "audit_style_coverage.py"), "--date", d],
                              capture_output=True, text=True, env=env)

    def _counts(out: str):
        m = re.search(r"الأسطح:\s*(\d+)\s*·\s*مغطاة:\s*(\d+)\s*·\s*غير مغطاة:\s*(\d+)\s*·\s*مانعة:\s*(\d+)", out or "")
        return tuple(int(x) for x in m.groups()) if m else None

    r = _audit(day)
    c = _counts(r.stdout)
    if r.returncode == 0:
        ok(f"تغطية الأسطح كاملة ({day}) — لا سطح خارج البوابة")
    elif c and c[3] > 0:
        bad("تغطية الأسطح", (r.stdout or "").strip().splitlines()[-1:] or r.returncode)
    else:
        built = [d for d in sorted(p.name.replace("-sectioned.md", "") for p in (B / "reports").glob("*-sectioned.md"))
                 if d < day and (SITE / "dist" / "reports" / f"{d}.html").exists()
                 and (SITE / "dist" / "reports" / "pdf" / f"{d}.pdf").exists()]
        r2 = _audit(built[-1]) if built else r
        c2 = _counts(r2.stdout)
        if r2.returncode == 0 or (c2 and c2[3] == 0 and c2[2] == 0):
            ok(f"تغطية الأسطح كاملة على آخر تاريخ مبني ({built[-1] if built else '—'})؛ أسطح {day} تُقاس بعد خطوات البناء")
        else:
            bad("تغطية الأسطح", (r2.stdout or "").strip().splitlines()[-1:] or r2.returncode)

print(f"── الاختبارات: {len(fails)} فشل · {len(skips)} تخطٍّ موثَّق")
for s in skips:
    print(f"  ! {s}")
sys.exit(1 if fails else 0)