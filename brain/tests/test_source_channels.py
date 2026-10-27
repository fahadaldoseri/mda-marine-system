#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار خريطة قنوات المصادر (ك-212): كل معتمد له قناة واحدة، والمجموع = المعتمد.

يُثبت الحالة الصحيحة، ويُثبت أيضًا أن الفجوة تُمنع (اختبار عدم تراجع): نحذف قناة مصدر
من نسخة مؤقتة ثم نتوقّع مانعًا باسم المصدر — فلا يعود السقوط الصامت من العدّاد.
"""
from __future__ import annotations

import json
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
t("عدد المسار الآلي = ما رمزه في الحالة", len(ch["rss"]) == 40, str(len(ch["rss"])))
t("عدد المرجعية اليدوية = 22", len(ch["browser"]) == 22, str(len(ch["browser"])))
t("المصدر 29 له قناة", 29 in ch["browser"], "29 غير مُسند")

# ── عدم التراجع: حذف قناة مصدر ⇒ البوابة تمنع باسمه ──
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    (td / "tools").mkdir(); (td / "validators").mkdir(); (td / "appendices").mkdir()
    (td / "sections").mkdir()
    src = (B / "tools" / "source_channels.py").read_text(encoding="utf-8")
    src = src.replace("    40, 44, 48, 52, 56, 57, 59, 60, 61, 62,\n", "    40, 44, 48, 52, 56, 57, 59, 60, 61, 62,\n").replace("1, 5, 13, 15, 18, 19, 21, 23, 27, 29, 34, 39,", "1, 5, 13, 15, 18, 19, 21, 23, 27, 34, 39,")
    assert "27, 34, 39," in src, "لم أستطع بناء نسخة الاختبار"
    (td / "tools" / "source_channels.py").write_text(src, encoding="utf-8")
    (td / "appendices" / "source-reliability-40.json").write_text(
        (B / "appendices" / "source-reliability-40.json").read_text(encoding="utf-8"), encoding="utf-8")
    code = ("import sys; sys.path.insert(0, r'%s/tools'); import source_channels as s; "
            "t,a,g,d = s.identity(); print(g); raise SystemExit(0 if g else 3)" % td)
    r = sp.run([sys.executable, "-c", code], capture_output=True, text=True)
    t("اختبار عدم تراجع: المصدر 29 يُكشف فجوة عند الإزالة", r.returncode == 0 and "29" in r.stdout,
      f"rc={r.returncode} out={r.stdout.strip()[:60]}")

print(f"\n  النتيجة: {'نجح' if not FAIL else f'فشل {len(FAIL)}'}")
raise SystemExit(0 if not FAIL else 2)
