#!/usr/bin/env python3
"""حارس حفظ الحقائق (tools/preserve_check.py): لا إنذار كاذب على علامات الترقيم الملاصقة للاتيني، وتغيّر نص العنوان يُكشف،
وحذف مصطلح مسموح الحذف (appendices/removable-latin.json) لا يمنع، وحذف غيره يمنع.
الاستعمال: python3 tests/test_preserve_check.py"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOL = HERE / "tools" / "preserve_check.py"
T = Path(tempfile.mkdtemp())
fails = 0


def run(a, b, extra=None):
    (T / "a.md").write_text(a, encoding="utf-8")
    (T / "b.md").write_text(b, encoding="utf-8")
    return subprocess.run([sys.executable, str(TOOL), str(T / "a.md"), str(T / "b.md")] + (extra or []), capture_output=True, text=True)


def ok(c, n):
    global fails
    print(("  ✔ " if c else "  ✘ ") + n)
    fails += not c


r = run("## الخلاصة\nالوقت 0400Z. ثم بلاغ.\n", "## الخلاصة\nالوقت 0400Z ثم بلاغ.\n")
ok(r.returncode == 0, "«Z.» قبل نقطة الجملة لا تُعدّ كلمة لاتينية مختلفة")
r = run("## الخلاصة\nأعلن UKMTO (USNI).\n", "## الخلاصة\nأعلن UKMTO USNI\n")
ok(r.returncode == 0, "قوس/نقطة ملاصقة للاتيني لا تغيّره")
r = run("## الخلاصة\nنص\n", "## ملخص\nنص\n")
ok(r.returncode == 2 and "عنوان" in r.stdout, "تغيير نص العنوان يُمنع")
r = run("## الخلاصة\nنص UKMTO\n", "## الخلاصة\nنص\n")
ok(r.returncode == 2, "حذف اسم لاتيني عادي يُمنع")
r = run("## الخلاصة\nنص ACH\n", "## الخلاصة\nنص\n", ["--removable", str(T / "rm.json")])
(T / "rm.json").write_text(json.dumps({"ACH": "قرار المالك 2026-10-21: حُذف السرد"}), encoding="utf-8")
r = run("## الخلاصة\nنص ACH\n", "## الخلاصة\nنص\n", ["--removable", str(T / "rm.json")])
ok(r.returncode == 0, "حذف مصطلح مسموح الحذف (بسبب مكتوب) لا يمنع")
r = run("## الخلاصة\nرقم 27\n", "## الخلاصة\nرقم 28\n", ["--removable", str(T / "rm.json")])
ok(r.returncode == 2, "تغيّر الرقم يُمنع دائمًا")
sys.exit(1 if fails else 0)
