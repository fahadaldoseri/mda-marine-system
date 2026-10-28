#!/usr/bin/env python3
"""reports_index.py: يفهرس الأيام ويفرّق بين ما في المستودع وما تجاوز مدة الاحتفاظ، ويذكر مسار الأرشيف الخاص.
الاستعمال: python3 tests/test_reports_index.py"""
import json, os, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
T = Path(tempfile.mkdtemp())
(T / "reports").mkdir(); (T / "appendices").mkdir()
for d in ("2026-09-01", "2026-10-20"):
    (T / "reports" / f"{d}-sectioned.md").write_text("x", encoding="utf-8")
(T / "appendices" / "reports-archive.json").write_text(json.dumps({"retain_days_in_repo": 30, "device_archive": {"path": "D:/Seawatch", "status": "ok", "naming": "n"}}), encoding="utf-8")
env = dict(os.environ, BRAIN_DIR=str(T))
r = subprocess.run([sys.executable, str(HERE / "tools" / "reports_index.py"), "--today", "2026-10-23"], capture_output=True, text=True, env=env)
t = (T / "docs" / "reports-index.md").read_text(encoding="utf-8")
f = 0
for ok, n in ((r.returncode == 0, "يعمل"), ("D:/Seawatch" in t, "يذكر مسار الأرشيف الخاص"),
              (("2026-09-01" in t and "الأرشيف الخاص (يجب نقله)" in t.split("2026-09-01")[1].splitlines()[0]), "ما تجاوز 30 يومًا يُعلَّم"),
              (("2026-10-20" in t and "المستودع" in t.split("2026-10-20")[1].splitlines()[0]), "الحديث في المستودع")):
    print(("  ✔ " if ok else "  ✘ ") + n); f += not ok
sys.exit(1 if f else 0)
