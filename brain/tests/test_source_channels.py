#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار خريطة قنوات المصادر (ك-212): كل معتمد له قناة واحدة، والمجموع = المعتمد.

يُثبت الحالة الصحيحة، ويُثبت أيضًا أن الفجوة تُمنع (اختبار عدم تراجع): نحذف قناة مصدر
من نسخة مؤقتة ثم نتوقّع مانعًا باسم المصدر — فلا يعود السقوط الصامت من العدّاد.
"""
from __future__ import annotations

import json
import re
import subprocess as sp
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B / "tools"))
FAIL: list[str] = []


def t(name: str, ok: bool, miss: str = "") -> None:
    print(f"  {'✔' if ok else '✘'} {name}" + (f" — {miss}" if not ok and miss else ""))
    if not ok:
        FAIL.append(name)


import source_channels as sc  # noqa: E402

ch = sc.channels()
total, approved, gap, dup = sc.identity()
t("الهوية: مجموع القنوات = المعتمد", total == approved, f"{total} ≠ {approved}")
t("لا مصدر معتمد بلا قناة", not gap, f"بلا قناة: {gap}")
t("لا مصدر في قناتين", not dup, f"مكرّر: {dup}")

# ── التوقّعات تُشتق من سجل اليوم نفسه (ك-247: أرقام مثبّتة (40/22/29) تعفّنت بعد ترقية
# المسارات، فصار الاختبار يمنع يومًا سليمًا بلا سبب) ──
status_files = sorted((B / "feeds").glob("feeds-*.status.json"))
if status_files:
    st = json.loads(status_files[-1].read_text(encoding="utf-8"))
    t("عدد المسار الآلي = ما رمزه سجل اليوم",
      len(ch["rss"]) == int(st.get("checked", -1)),
      f'{len(ch["rss"])} ≠ {st.get("checked")}')
    man_status = {int(n) for n in (st.get("manual_reference") or []) if str(n).isdigit()}
    t("عدد المرجعية اليدوية = ما رمزه سجل اليوم",
      man_status == set(ch["browser"]),
      f'{sorted(ch["browser"])} ≠ {sorted(man_status)}')
else:
    t("سجل اليوم موجود لاشتقاق الأعداد", False, "لا ملف feeds-*.status.json")

routes = getattr(sc, "BROWSER_ROUTES", {})
missing_route = sorted(n for n in ch["browser"] if n not in routes or not routes[n].get("url"))
t("لكل مصدر مرجعية يدوية مسار مرجعي معلن", not missing_route, f"بلا مسار: {missing_route}")

# ── عدم التراجع: إسقاط أي مصدر مرجعي ⇒ البوابة تمنع باسمه (يُختار من السجل لا من قائمة مثبّتة) ──
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    import shutil as _sh
    _sh.copytree(B / "tools", td / "tools")
    for d in ("sections", "appendices"):
        if (B / d).exists():
            _sh.copytree(B / d, td / d, dirs_exist_ok=True)
    (td / "validators").mkdir(exist_ok=True)
    f = td / "tools" / "source_channels.py"
    text = f.read_text(encoding="utf-8")
    target = sorted(ch["browser"])[0]
    block = re.search(r"MANUAL_REFERENCE: set\[int\] = \{[^}]*\}", text)
    assert block, "لم أستطع بناء نسخة الاختبار (تعذّر العثور على قائمة المرجعية)"
    keep = [n for n in sorted(ch["browser"]) if n != target]
    newset = "MANUAL_REFERENCE: set[int] = {" + ", ".join(str(n) for n in keep) + ",}"
    f.write_text(text[:block.start()] + newset + text[block.end():], encoding="utf-8")
    code = ("import sys; sys.path.insert(0, r'%s/tools'); import source_channels as s; "
            "t,a,g,d = s.identity(); print(g); raise SystemExit(0 if g else 3)" % td)
    r = sp.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(td))
    t(f"اختبار عدم تراجع: المصدر {target} يُكشف فجوة عند إسقاطه",
      r.returncode == 0 and str(target) in r.stdout,
      f"rc={r.returncode} out={r.stdout.strip()[:60]} err={r.stderr.strip()[-80:]}")

print(f"\n  النتيجة: {'نجح' if not FAIL else f'فشل {len(FAIL)}'}")
raise SystemExit(0 if not FAIL else 2)
