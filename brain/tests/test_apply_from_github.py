#!/usr/bin/env python3
"""apply_from_github.py على مستودع git مؤقت: تعارض يمنع · --accept-repo يطبّق مع أرشفة · تحديث نظيف بلا تعارض ·
البيانات لا تُلمس · فشل verify يستعيد · لا حذف.
الاستعمال: python3 tests/test_apply_from_github.py"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE / "tools"
T = Path(tempfile.mkdtemp())
repo, brain, site = T / "repo", T / "srv-brain", T / "srv-site"
fails = 0


def ok(c, n):
    global fails
    print(("  ✔ " if c else "  ✘ ") + n)
    fails += not c


def w(p, txt):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")


def git(*a):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *a], capture_output=True, text=True)


def apply(*extra):
    return subprocess.run([sys.executable, str(TOOLS / "apply_from_github.py"), "--repo", str(repo), "--brain", str(brain),
                           "--site", str(site), "--skills", str(T / "skills"), "--no-verify", *extra], capture_output=True, text=True)


subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
spec = json.loads((HERE / "appendices" / "code-paths.json").read_text(encoding="utf-8"))
w(repo / "brain" / "appendices" / "code-paths.json", json.dumps(spec, ensure_ascii=False))
w(repo / "brain" / "tools" / "a.py", "v1\n")
w(repo / "brain" / "reports" / "r.md", "بيانات المستودع\n")
w(repo / "site" / "generator" / "g.py", "g1\n")
git("add", "-A"); git("commit", "-qm", "c1")
w(brain / "tools" / "a.py", "محلي مختلف\n")
w(brain / "reports" / "r.md", "بيانات الخادم\n")

r = apply()
ok(r.returncode == 3 and (brain / "tools" / "a.py").read_text(encoding="utf-8") == "محلي مختلف\n", "تعارض أول مرة يمنع ولا يغيّر شيئًا")
r = apply("--accept-repo")
ok(r.returncode == 0 and (brain / "tools" / "a.py").read_text() == "v1\n", "--accept-repo يطبّق نسخة المستودع")
arch = list((brain / "logs").glob("apply-*/brain/tools/a.py"))
ok(len(arch) == 1 and arch[0].read_text(encoding="utf-8") == "محلي مختلف\n", "نسخة الخادم المستبدلة مؤرشفة")
ok((brain / "reports" / "r.md").read_text(encoding="utf-8") == "بيانات الخادم\n", "البيانات لم تُلمس")
ok((site / "generator" / "g.py").read_text() == "g1\n", "ملفات الموقع طُبّقت")

w(repo / "brain" / "tools" / "a.py", "v2\n"); git("add", "-A"); git("commit", "-qm", "c2")
r = apply()
ok(r.returncode == 0 and (brain / "tools" / "a.py").read_text() == "v2\n", "تحديث ملف لم يُعدَّل محليًا يمرّ بلا تعارض")

w(brain / "tools" / "a.py", "تعديل محلي جديد\n")
w(repo / "brain" / "tools" / "a.py", "v3\n"); git("add", "-A"); git("commit", "-qm", "c3")
r = apply()
ok(r.returncode == 3 and (brain / "tools" / "a.py").read_text(encoding="utf-8") == "تعديل محلي جديد\n", "تعديل محلي + تغيير في المستودع = تعارض يمنع")

shutil.copy(HERE / "tools" / "runbook.py", brain / "tools" / "runbook.py")
w(repo / "brain" / "tools" / "b.py", "x\n"); git("add", "-A"); git("commit", "-qm", "c4")
w(brain / "tools" / "a.py", "v3\n")  # يطابق المستودع فلا تعارض
bad = subprocess.run([sys.executable, str(TOOLS / "apply_from_github.py"), "--repo", str(repo), "--brain", str(brain), "--site", str(site), "--skills", str(T / "skills")],
                     capture_output=True, text=True)
ok(bad.returncode == 2 and not (brain / "tools" / "b.py").exists(), "فشل verify (لا مانيفست) يستعيد ولا يترك ملفًا جديدًا")
shutil.rmtree(T)
sys.exit(1 if fails else 0)
