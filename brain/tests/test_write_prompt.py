#!/usr/bin/env python3
"""اختبار عقد كتابة W010: المصادر الخام، المعجم، التسجيل، وحاجز الإتمام."""
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


def ok(condition, name):
    global fails
    print(("  ✔ " if condition else "  ✘ ") + name)
    fails += not condition


brief = (B / "sections" / "20-writing-brief.md").read_text(encoding="utf-8").splitlines()[0]
ok(brief in text, "مختصر الكتابة مضمَّن نصًّا")
lex = [line for line in (B / "sections" / "20-lexicon.md").read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
ok(bool(lex) and lex[0] in text and lex[-1] in text, "المعجم مضمَّن نصًّا (أول سطر وآخره)")
examples = [line for line in (B / "sections" / "20-examples.md").read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
ok(bool(examples) and examples[0] in text, "الأمثلة مضمَّنة نصًّا")
heads = [section["heading"] for section in m["sections"] if section.get("heading")]
ok(all(heading in text for heading in heads), f"كل عناوين الأقسام المكتوبة ({len(heads)}) في البرومت")
ok("{{" not in text, "لا رمز {{...}} متروك بلا تصيير")
ok("editor-prompt" not in text, "برومت المحرر الآلي ليس من قراءات الكاتب")
ok("2026-10-23" in text and "{date}" not in text, "التاريخ مُستبدَل")

required_reads = {
    "web/meta/{date}.json",
    "appendices/estimate-code-map.json",
    "tools/register_estimate.py",
}
ok(required_reads.issubset(set(step.get("reads", []))), "W010 يقرأ ملف الواجهة وخريطة الرموز وأداة التسجيل")
ok("appendices/estimate-code-map.json" in step.get("writes", []), "W010 يعلن خريطة التقديرات ضمن مخرجاته")
assertions = step.get("assert", [])
check = [a for a in assertions if a.get("type") == "cmd" and a.get("command") == ["python3", "tools/register_estimate.py", "--check", "--date", "{date}"]]
ok(bool(check), "إتمام W010 يفشل مغلقًا حتى تنجح أداة تسجيل EST")
ok("register_estimate.py" in text and "--check --date 2026-10-23" in text, "برومت W010 يطلب التسجيل والتحقق قبل الإتمام")
runner = (B / "tests" / "run_checks.sh").read_text(encoding="utf-8")
ok("tests/test_g030_code_spaces.py" in runner, "اختبار G030 الفعلي موصول بمشغل G001")
sys.exit(1 if fails else 0)
