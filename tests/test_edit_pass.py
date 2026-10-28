#!/usr/bin/env python3
"""tools/edit_pass.py بعميل نموذج وهمي (بلا شبكة): يحفظ ما قبل أول عنوان `##` عند --apply · يرفض قسمًا غُيّر رقمه ·
يطبّق قسمًا سليمًا · يقبل مسار العميل من LLM_CLIENT_CMD ويقرأ النموذج من EDIT_PASS_MODEL.
الاستعمال: python3 tests/test_edit_pass.py"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
T = Path(tempfile.mkdtemp())
fails = 0

FAKE = r'''
import json, sys
a = sys.argv[1:]
get = lambda k: a[a.index(k) + 1]
rows = [json.loads(l) for l in open(get("--input"), encoding="utf-8") if l.strip()]
open(get("--out") + ".model", "w").write(get("--model"))
out = []
for i, t in enumerate(rows):
    rev = t.replace("كثيرا", "كثيرًا").replace("27 هجومًا", "28 هجومًا")
    out.append({"index": i, "input": t, "output": json.dumps({"revised": rev, "changes": [{"before": "x", "after": "y", "category": "أسلوب", "why": "ت"}]}, ensure_ascii=False)})
open(get("--out"), "w", encoding="utf-8").write("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n")
'''
(T / "fake.py").write_text(FAKE, encoding="utf-8")
pad = "جملة عادية للحشو تتكرر لتتجاوز الحد الأدنى. " * 12
report = f"# التقرير اليومي\nسطر تمهيدي مهم.\n\n## القسم الأول\nارتفع الطلب كثيرا. {pad}\n\n## القسم الثاني\nسُجّل 27 هجومًا في الشهر. {pad}\n"
rp = T / "2099-01-01-sectioned.md"
rp.write_text(report, encoding="utf-8")
env = dict(os.environ, LLM_CLIENT_CMD=f"{sys.executable} {T / 'fake.py'}", EDIT_PASS_MODEL="model-x", BRAIN_DIR=str(T))
(T / "appendices").mkdir()
(T / "logs").mkdir()
r = subprocess.run([sys.executable, str(HERE / "tools" / "edit_pass.py"), "--report", str(rp), "--apply", "--out-dir", str(T / "audit")],
                   capture_output=True, text=True, env=env)


def ok(c, n):
    global fails
    print(("  ✔ " if c else "  ✘ ") + n)
    fails += not c


after = rp.read_text(encoding="utf-8")
ok(r.returncode == 0, f"التشغيل ينجح ({r.returncode}) {r.stdout[-200:] if r.returncode else ''}")
ok("# التقرير اليومي" in after and "سطر تمهيدي مهم." in after, "ما قبل أول `##` محفوظ عند --apply")
ok("كثيرًا" in after, "تعديل القسم السليم طُبّق")
ok("27 هجومًا" in after and "28 هجومًا" not in after, "قسم تغيّر رقمه رُفض وبقي أصله")
ok(after.count("## ") == 2, "عدد العناوين ثابت")
ok((T / "audit").is_dir() and any((T / "audit").glob("edit-pass-*.md")), "تقرير التحرير كُتب")
sys.exit(1 if fails else 0)
