#!/usr/bin/env python3
"""لمسات ختامية لتقرير 2026-10-18: توقيت مزدوج + تسجيل تقديرات قراءة الموقف وتحليل المؤشرات."""
import json
from pathlib import Path

B = Path("/home/ubuntu/brain-marine-news")
MD = B / "reports/2026-10-18-sectioned.md"
JS = B / "web/meta/2026-10-18.json"

PAIRS = [
    ("0022Z من 18 أكتوبر", "0022Z من 18 أكتوبر (03:22 بتوقيت البحرين)"),
    ("1822Z من 17 أكتوبر", "1822Z من 17 أكتوبر (21:22 بتوقيت البحرين)"),
    ("**161550Z** من أكتوبر 2026", "**161550Z** من أكتوبر 2026 (19:50 بتوقيت البحرين)"),
    ("**170300Z**", "**170300Z** (06:00 بتوقيت البحرين)"),
]

for path in (MD, JS):
    text = path.read_text(encoding="utf-8")
    for old, new in PAIRS:
        if old in text and new not in text:
            text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"طُبّق التوقيت المزدوج على: {path.name}")

# تسجيل تقديرات القسم (أ1/8 — memory/intel-estimates.jsonl)
estimates = [
    ("MN-2026-10-18-02", "استمرار الاستهداف المنظم في المضيق وممراته", "يُرجَّح (55–80%)", "غير محسوم"),
    ("MN-2026-10-18-08", "العدّ الرسمي أدنى من الواقع بسبب فجوة التبليغ", "يُرجَّح (55–80%)", "غير محسوم"),
    ("MN-2026-10-18-01", "انتقال ثقل الاستهداف إلى خط الاقتراب الجنوبي", "ممكن (20–45%)", "غير محسوم"),
    ("MN-2026-10-18-02", "تورط ألغام بحرية كسبب رئيسي للإصابات", "غير مُرجَّح (20–45%)", "غير محسوم"),
    ("MN-2026-10-18-06", "عودة العبور الطبيعي قبل تغيّر أمني أو سياسي", "غير حاسم", "غير محسوم"),
]

out = B / "memory/intel-estimates.jsonl"
with out.open("a", encoding="utf-8") as fh:
    for code, statement, probability, outcome in estimates:
        fh.write(json.dumps({
            "date": "2026-10-18",
            "code": code,
            "estimate": statement,
            "probability": probability,
            "outcome": outcome,
            "source_grade": "UKMTO A/2 · NAVAREA IX A/1 · منصة رصد C/3 · رواية طرف D/4",
        }, ensure_ascii=False) + "\n")
print(f"سُجّلت {len(estimates)} تقديرات في {out.name}")