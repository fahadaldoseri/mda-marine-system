#!/usr/bin/env python3
"""فاحص الإملاء: يلتقط الخطأ الحقيقي ولا ينذر كذبًا على «قُبل علنًا» (فعل ماضٍ لا حرف جر).
الاستعمال: python3 tests/test_orthography.py"""
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "validators" / "check_orthography.py"
T = Path(tempfile.mkdtemp())
fails = 0


def total(text):
    p = T / "t.md"
    p.write_text(text, encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOL), str(p)], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("المجموع:"):
            return int(line.split(":")[1].split()[0])
    return -1


def ok(c, n):
    global fails
    print(("  ✔ " if c else "  ✘ ") + n)
    fails += not c


ok(total("قال المتحدث إن الطلب قبل علنًا في الجلسة.\n") == 0, "«قبل علنًا» لا يُعدّ خطأ")
ok(total("بقي الوضع بلا تغييرًا يذكر.\n") >= 1, "«بلا تغييرًا» يُكتشف")
ok(total("اكتوبر هذا الشهر.\n") >= 1, "«اكتوبر» تُكتشف")
ok(total("عبرت سفينة سفينة واحدة.\n") >= 1, "تكرار كلمة يُكتشف")
ok(total('نقلت القناة عنوانًا: "military...".\n') == 0, "علامة الحذف الإنجليزية لا تُعدّ نقطتين معلّقتين")
ok(total("ارتفع برنت 3.2 دولارًا إلى 113 دولارًا.\n") == 0, "تنوين النصب بعد العدد سليم")
sys.exit(1 if fails else 0)
