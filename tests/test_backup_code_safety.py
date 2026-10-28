#!/usr/bin/env python3
"""github_backup.py لا يكتب الشيفرة فوق المستودع (GitHub مصدرها): ملف شيفرة مختلف على الخادم يبقى كما في المستودع ويُبلَّغ كانحراف ·
ملف شيفرة جديد على الخادم يُنسخ ويُعلَن · البيانات تُنسخ وما حُذف من الخادم يُحذف من النسخة.
الاستعمال: python3 tests/test_backup_code_safety.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
T = Path(tempfile.mkdtemp())
brain, site, out = T / "brain", T / "seawatch", T / "mda-marine-system"
fails = 0


def ok(c, n):
    global fails
    print(("  ✔ " if c else "  ✘ ") + n)
    fails += not c


def w(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8")


spec = (HERE / "appendices" / "code-paths.json").read_text(encoding="utf-8")
for base in (brain, out / "brain"):
    w(base / "appendices" / "code-paths.json", spec)
w(brain / "tools" / "a.py", "نسخة الخادم القديمة\n")
w(out / "brain" / "tools" / "a.py", "نسخة GitHub الجديدة\n")
w(brain / "tools" / "new_server_tool.py", "جديد من الخادم\n")
w(brain / "reports" / "2099-01-01-sectioned.md", "تقرير اليوم\n")
w(out / "brain" / "reports" / "old.md", "حُذف من الخادم\n")
w(site / "generator" / "g.py", "site-server\n")
w(out / "site" / "generator" / "g.py", "site-github\n")
w(out / "AGENTS.md", "ملف جذر المستودع\n")
env = dict(os.environ, BRAIN_DIR=str(brain), SITE_DIR=str(site), BACKUP_REPO_DIR=str(out))
r = subprocess.run([sys.executable, str(HERE / "tools" / "github_backup.py")], capture_output=True, text=True, env=env)
ok(r.returncode == 0, f"التشغيل ينجح {r.stderr[-200:]}")
ok((out / "brain" / "tools" / "a.py").read_text(encoding="utf-8") == "نسخة GitHub الجديدة\n", "شيفرة GitHub لم تُكتب فوقها نسخة الخادم")
ok((out / "site" / "generator" / "g.py").read_text(encoding="utf-8") == "site-github\n", "شيفرة الموقع كذلك")
ok("brain/tools/a.py" in r.stdout and "انحراف" in r.stdout, "الانحراف يُعلَن في المخرج")
ok((out / "brain" / "tools" / "new_server_tool.py").exists() and "new_server_tool.py" in r.stdout, "شيفرة جديدة من الخادم تُنسخ وتُعلَن")
ok((out / "brain" / "reports" / "2099-01-01-sectioned.md").exists(), "البيانات تُنسخ")
ok(not (out / "brain" / "reports" / "old.md").exists(), "ما حُذف من الخادم يُحذف من النسخة (بيانات)")
ok((out / "AGENTS.md").exists(), "ملفات جذر المستودع باقية")
shutil.rmtree(T)
sys.exit(1 if fails else 0)
