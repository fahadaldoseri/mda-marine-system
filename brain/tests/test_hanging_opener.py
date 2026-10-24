#!/usr/bin/env python3
"""اختبار منع التركيب المعلّق (ك-173): القاعدة في القسم + البوابة تمنع وتمرّ بعد الإصلاح."""
import subprocess, sys, tempfile
from pathlib import Path
B = Path(__file__).resolve().parent.parent
rule_file = B / "sections" / "20-language.md"
if "قاعدة التركيب المعلّق" not in rule_file.read_text(encoding="utf-8"):
    print("  ✘ القاعدة غير موجودة في sections/20-language.md"); raise SystemExit(1)
print("  ✔ القاعدة موجودة في القسم")
gate = B / "validators" / "check_style.py"
def rc(text):
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "r.md"; f.write_text(text, encoding="utf-8")
        return subprocess.run([sys.executable, str(gate), str(f)], capture_output=True, text=True).returncode
bad = "## مستوى التهديد\n\nيبقى العدد المثبت في التقرير السابق 119 حادثة مؤكدة و24 وفاة.\n"
good = "## مستوى التهديد\n\nالعدد المثبت في التقرير السابق 119 حادثة مؤكدة و24 وفاة، ولم يتوفر تحديث جديد.\n"
r1, r2 = rc(bad), rc(good)
print(("  ✔ " if r1 != 0 else "  ✘ ") + f"البوابة تمنع التركيب المعلّق (رمز {r1})")
print(("  ✔ " if r2 == 0 else "  ✘ ") + f"البوابة تمرّ بعد الإصلاح (رمز {r2})")
raise SystemExit(0 if (r1 != 0 and r2 == 0) else 1)
