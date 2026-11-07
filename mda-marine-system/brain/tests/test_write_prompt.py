#!/usr/bin/env python3
"""برومت الكتابة المُصيَّر (كما يراه الوكيل) يجب أن يحمل فعلًا: المختصر والمعجم والأمثلة وكل أقسام السجل التي يكتبها الوكيل،
ولا يحيل إلى «المعجم أدناه» وهو غير مضمَّن (عيب الصياغة السابقة).
الاستعمال: python3 tests/test_write_prompt.py    رمز 0 سليم · 1 فشل"""
import importlib.util
import json
import os
import sys
from pathlib import Path

B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parent.parent)
spec = importlib.util.spec_from_file_location("runbook", B / "tools" / "runbook.py")
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)
m = rb.load(str(B))
step = next(s for s in m["steps"] if s["id"] == "W010")
text = rb.render_prompt(str(B), step["prompt"], "2026-10-23")
fails = 0


def ok(c, n):
    global fails
    print(("  ✔ " if c else "  ✘ ") + n)
    fails += not c


brief = (B / "sections" / "20-writing-brief.md").read_text(encoding="utf-8").splitlines()[0]
ok(brief in text, "مختصر الكتابة مضمَّن نصًّا")
lex = [l for l in (B / "sections" / "20-lexicon.md").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
ok(bool(lex) and lex[0] in text and lex[-1] in text, "المعجم مضمَّن نصًّا (أول سطر وآخره)")
ex = [l for l in (B / "sections" / "20-examples.md").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
ok(bool(ex) and ex[0] in text, "الأمثلة مضمَّنة نصًّا")
heads = [s["heading"] for s in m["sections"] if s.get("heading")]
ok(all(h in text for h in heads), f"كل عناوين الأقسام المكتوبة ({len(heads)}) في البرومت")
ok("{{" not in text, "لا رمز {{...}} متروك بلا تصيير")
ok("editor-prompt" not in text, "برومت المحرر الآلي ليس من قراءات الكاتب")
ok("2026-10-23" in text and "{date}" not in text, "التاريخ مُستبدَل")
sys.exit(1 if fails else 0)
