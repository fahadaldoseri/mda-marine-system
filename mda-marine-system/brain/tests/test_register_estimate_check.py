#!/usr/bin/env python3
"""`register_estimate.py --check --date D` يمنع تقريرًا فيه رمز EST- غير مسجَّل ويقبل المسجَّل (D060 كان يستدعي خيارًا غير موجود)."""
import os, subprocess, sys, tempfile, json, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
T = Path(tempfile.mkdtemp())
(T / "tools").mkdir(); (T / "appendices").mkdir(); (T / "reports").mkdir()
shutil.copy(HERE / "tools" / "register_estimate.py", T / "tools")
(T / "appendices" / "estimate-code-map.json").write_text(json.dumps({"codes": {"EST-2099-01-01-01": {"statement": "س"}}}), encoding="utf-8")
def run(text):
    (T / "reports" / "2099-01-01-sectioned.md").write_text(text, encoding="utf-8")
    return subprocess.run([sys.executable, str(T / "tools" / "register_estimate.py"), "--check", "--date", "2099-01-01"], capture_output=True, text=True)
f = 0
r = run("تقدير EST-2099-01-01-01 هنا"); ok = r.returncode == 0 and "رمز تقدير مسجّل" in r.stdout; f += not ok; print(("  ✔ " if ok else "  ✘ ") + "رمز مسجَّل يُقبل")
r = run("تقدير EST-2099-01-01-09 هنا"); ok = r.returncode == 2 and "EST-2099-01-01-09" in r.stdout; f += not ok; print(("  ✔ " if ok else "  ✘ ") + "رمز غير مسجَّل يُرفض")
r = run("لا رموز"); ok = r.returncode == 0; f += not ok; print(("  ✔ " if ok else "  ✘ ") + "تقرير بلا تقديرات يمرّ")
shutil.rmtree(T)
sys.exit(1 if f else 0)
