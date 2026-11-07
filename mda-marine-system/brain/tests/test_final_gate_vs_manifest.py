#!/usr/bin/env python3
"""اتساق البوابة القديمة (tools/final_gate.sh) مع المانيفست: كل سكربت تستدعيه خطوة فيها يجب أن تستدعيه خطوة في المانيفست،
وإلا صار للنظام مرجعان يختلفان (حدث ذلك: virgin وWord الدقيق والتدقيق الأسبوعي غابت عن المانيفست).
الاستعمال: python3 tests/test_final_gate_vs_manifest.py    رمز 0 سليم · 2 فرق"""
import json
import os
import re
import sys
from pathlib import Path

B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parent.parent)
text = (B / "tools" / "final_gate.sh").read_text(encoding="utf-8")
refs = set()
for line in text.splitlines():
    if re.match(r"^\s*step(_strict)?\s", line) or line.strip().startswith(('python3 "$B', 'bash "$B')):
        refs |= set(re.findall(r"\$B/((?:tools|validators|tests)/[\w./-]+)", line))
        refs |= set(re.findall(r"\$SITE/(generator/[\w./-]+)", line))
m = json.loads((B / "runbook" / "runbook.json").read_text(encoding="utf-8"))
cmds = " ".join(" ".join(s.get("command") or []) for s in m["steps"])
missing = sorted(r for r in refs if r.split("/")[-1] not in cmds)
for r in missing:
    print(f"✘ تستدعيه final_gate.sh ولا تستدعيه أي خطوة في المانيفست: {r}")
if not missing:
    print(f"✔ كل ما تستدعيه final_gate.sh ({len(refs)} سكربتًا) موجود في أوامر المانيفست")
sys.exit(2 if missing else 0)
