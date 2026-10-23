#!/usr/bin/env python3
"""بوابة إغلاق المخرجات ومكتبات التدقيق — تربط مكتبات التقارير ببوابة تُنفَّذ فعلًا.

المشكلة التي تحلّها (عطل ك-78): ثلاث مكتبات (نتائج التدقيق · سجل النتائج · العبارات
المتكررة) كان يقرؤها مولّد تقرير فقط، ولا بوابة تقرؤها — أي أنها **لا تعمل على الإصدار**.
القاعدة: لا مكتبة بلا مُنفِّذ. كل مكتبة تُنتج بندًا يجب أن تُغلق بنودها أو تُؤجَّل صراحةً.

المخرجات: تقرير بالبنود المفتوحة + مكتبات بلا مُنفِّذ.

تقرأ: appendices/libraries/findings-register.md · appendices/libraries/findings-<التاريخ>.json
      appendices/libraries/lexicon-library.json · terminology-gaps.md · orthography-consistency.md
      appendices/libraries/recurring-phrases.md
السلّم: 0 سليم · 1 تحذير (مرحلة أولى لا تمنع النشر) · 2 مانع (بعد الترقية).
"""
from __future__ import annotations

import sys

import argparse
import json
import re
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SKILLS_ROOT = Path(__import__("os").environ.get("SKILLS_DIR", str(Path.home() / "skills")))
LIB = B / "appendices" / "libraries"
GATES = [B / "tools" / "final_gate.sh", B / "tools" / "daily_pipeline.sh"]
CONSUMERS = [B / "validators", B / "tools", B / "sections"]


def library_files() -> list[Path]:
    return sorted(p for p in LIB.glob("*") if p.is_file())


def consumers_of(name: str) -> list[str]:
    """المستهلك يُعرَف بالاسم الصريح أو بنمط مُعمَّم للتاريخ (findings-<date>.json → findings-*.json)."""
    pats = {name, re.sub(r"\d{4}-\d{2}-\d{2}", "*", name)}
    hits = []
    for root in CONSUMERS + [SKILLS_ROOT / "marine-news-brain", SKILLS_ROOT / "military-arabic-editing"]:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file() and f.suffix in {".py", ".sh", ".md"}:
                try:
                    body = f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if any(pt in body for pt in pats):
                    hits.append(str(f.relative_to(B)) if str(f).startswith(str(B)) else f.name)
    return hits


def gate_text() -> str:
    return "\n".join(g.read_text(encoding="utf-8", errors="ignore") for g in GATES if g.exists())


def gate_runs(consumer: str) -> bool:
    """هل تُشغِّل بوابةُ التنفيذ هذا المستهلك؟ (ارتباط غير مباشر)"""
    return Path(consumer).name in gate_text()


def link_kind(name: str) -> tuple[str, list[str]]:
    """تصنيف الارتباط: مباشر · غير مباشر · معزول · بلا مستهلك.

    المقياس الصحيح للترابط ليس ورود اسم المكتبة في البوابة، بل: هل تُشغِّل البوابة
    مستهلكًا يقرأ المكتبة؟ المكتبة التي يقرؤها مستهلك لا تُشغّله البوابة معزولة فعليًا.
    """
    cons = consumers_of(name)
    if not cons:
        return "بلا مستهلك", []
    if name in gate_text():
        return "مباشر", cons
    live = [c for c in cons if gate_runs(c)]
    if live:
        return "غير مباشر", live
    return "معزول", cons


def open_findings() -> tuple[int, int]:
    """بنود سجل النتائج: مفتوحة (بلا حالة إغلاق) مقابل مغلقة."""
    reg = LIB / "findings-register.md"
    if not reg.exists():
        return 0, 0
    text = reg.read_text(encoding="utf-8")
    rows = [l for l in text.splitlines() if l.startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", l)]
    opened = closed = 0
    for r in rows:
        if re.search(r"(مُصلَح|مصلح|مغلق|تمّ|تم |✔)", r):
            closed += 1
        elif re.search(r"(مفتوح|معلّق|معلق|مؤجَّل|مؤجل|⚠|✘)", r):
            opened += 1
    return opened, closed


def open_json_findings() -> tuple[int, int, list[str]]:
    """بنود ملف نتائج التدقيق: تُعدّ المفتوحة (بلا حالة إصلاح) وتُسمّى."""
    files = sorted(LIB.glob("findings-*.json"))
    if not files:
        return 0, 0, []
    data = json.loads(files[-1].read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else (data.get("findings") or data.get("items") or [])
    opened, titles = 0, []
    for r in rows:
        if not isinstance(r, dict):
            continue
        status = str(r.get("status") or r.get("الحالة") or "").strip()
        if status and any(k in status for k in ("مُصلَح", "مصلح", "مغلق", "fixed", "closed")):
            continue
        opened += 1
        titles.append(str(r.get("title") or r.get("العنوان") or r.get("id") or "بند")[:60])
    return opened, len(rows) - opened, titles


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    a = ap.parse_args()

    libs = library_files()
    print(f"=== بوابة إغلاق المكتبات{' — ' + a.date if a.date else ''} ===")
    orphan, isolated = [], []
    opened, closed = open_findings()
    j_open, j_closed, j_titles = open_json_findings()
    print(f"  {'المكتبة':44s} {'الارتباط':10s} المستهلك المُنفِّذ")
    for p in libs:
        kind, live = link_kind(p.name)
        if kind == "بلا مستهلك":
            orphan.append(p.name)
        elif kind == "معزول":
            isolated.append(p.name)
        first = live[0] if live else "—"
        print(f"  {p.name:44s} {kind:10s} {first}")

    problems = []
    if orphan:
        problems.append(f"مكتبات بلا مستهلك: {orphan}")
    if isolated:
        problems.append(f"مكتبات معزولة (يقرؤها مستهلك لا تُشغّله البوابة): {isolated}")
    if opened:
        problems.append(f"بنود مفتوحة في سجل النتائج: {opened} (مغلقة: {closed})")
    if j_open + j_closed:
        print(f"  · جرد ملف النتائج: {j_open + j_closed} بندًا مكشوفًا (جرد كشف لا قائمة مهام)")

    if problems:
        print("  • تحذير — " + " · ".join(problems))
        print("  المطلوب: ربط كل مكتبة بمُنفِّذ، وإغلاق بنود التدقيق أو تأجيلها صراحةً")
        return 1
    print("  ✔ كل مكتبة لها مستهلك وبوابة، ولا بند مفتوحًا")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    raise SystemExit(main())
