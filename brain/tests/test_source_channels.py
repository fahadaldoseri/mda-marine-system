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
    # ك-237: النسخة السابقة كانت تنسخ ملفًا واحدًا فقط، فينهار الاستيراد في المجلد المؤقت (rc=1 بلا مخرج)
    # وتبقى الحالة السلبية بلا إثبات. الآن تُنسخ شجرة الأدوات والبيانات كاملة ثم يُحذف الرمز 29.
    import shutil
    shutil.copytree(B / "tools", td / "tools")
    # جداول المسارات تُقرأ من sections/ وappendices/ داخل المجلد المؤقت، فتُنسخ كاملة
    for d in ("sections", "appendices"):
        if (B / d).exists():
            shutil.copytree(B / d, td / d, dirs_exist_ok=True)
    (td / "validators").mkdir(exist_ok=True)
    f = td / "tools" / "source_channels.py"
    src = f.read_text(encoding="utf-8")
    before = "1, 5, 13, 15, 18, 19, 21, 23, 27, 29, 34, 39,"
    after = "1, 5, 13, 15, 18, 19, 21, 23, 27, 34, 39,"
    assert before in src, "لم أستطع بناء نسخة الاختبار (تعذّر حذف الرمز 29)"
    f.write_text(src.replace(before, after), encoding="utf-8")
    assert after in f.read_text(encoding="utf-8"), "لم أستطع بناء نسخة الاختبار"
    code = ("import sys; sys.path.insert(0, r'%s/tools'); import source_channels as s; "
            "t,a,g,d = s.identity(); print(g); raise SystemExit(0 if g else 3)" % td)
    r = sp.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(td))
    t("اختبار عدم تراجع: المصدر 29 يُكشف فجوة عند الإزالة",
      r.returncode == 0 and "29" in r.stdout,
      f"rc={r.returncode} out={r.stdout.strip()[:60]} err={r.stderr.strip()[-80:]}")

print(f"\n  النتيجة: {'نجح' if not FAIL else f'فشل {len(FAIL)}'}")
raise SystemExit(0 if not FAIL else 2)
