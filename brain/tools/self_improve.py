#!/usr/bin/env python3
"""محرّك التعلّم الذاتي — يُشغَّل بعد كل إصدار، لا بعد كل جولة يدوية.

الوظيفة:
1) يقرأ سجل الأعطال وسجل الدروس وسجلات البوابات لآخر الإصدارات.
2) يكشف الأنماط المتكررة: عطل يتكرر، تحذير يظهر في عدة أيام، درس بلا مُفعِّل.
3) يتحقق أن كل درس صار له **مُفعِّل** (بوابة أو قاعدة في مهارة)، لا مجرد تدوين.
4) يكتب «موجز التحسين» ويُدرج بنودًا في طابور التحسين للدورة القادمة.

القاعدة: الدرس الذي لا يتحوّل إلى بوابة يعود. لذلك يُقاس التعلّم بعدد الدروس المُفعَّلة لا بعدد المسجّلة.
الاستخدام: python3 tools/self_improve.py [--date YYYY-MM-DD] [--window 7]
رمز الخروج: 0 دائمًا (استشاري) — الترقية إلى مانع تكون بقرار مرحلي.
"""
import re
FAULT_ROW = re.compile(r'^\\|\\s*[\\u0621-\\u064A]{1,3}-\\d')
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date as _date
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SKILLS_ROOT = Path(__import__("os").environ.get("SKILLS_DIR", str(Path.home() / "skills")))
FAULTS = B / "audit" / "سجل-الأعطال-والثغرات.md"
LESSONS = B / "memory" / "learning-log.jsonl"
QUEUE = B / "memory" / "improvement-queue.jsonl"
GATES = B / "logs"
ENFORCERS = [B / "validators", B / "tools", B / "sections", B / "appendices", SKILLS_ROOT / "marine-news-brain", SKILLS_ROOT / "military-arabic-editing"]


def fault_rows() -> list[dict]:
    if not FAULTS.exists():
        return []
    out = []
    for line in FAULTS.read_text(encoding="utf-8").splitlines():
        if not FAULT_ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 6:
            out.append({"code": cells[0], "title": cells[1], "evidence": cells[2], "root": cells[3], "rule": cells[4], "date": cells[5]})
    return out


def lessons() -> list[dict]:
    if not LESSONS.exists():
        return []
    out = []
    for line in LESSONS.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def enforcement_index() -> str:
    """نص كل الملفات القادرة على إنفاذ قاعدة: البوابات والأدوات والأقسام والمهارات."""
    buf = []
    for root in ENFORCERS:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file() and f.suffix in {".py", ".md", ".json", ".sh"}:
                try:
                    buf.append(f.read_text(encoding="utf-8", errors="ignore"))
                except Exception:
                    continue
    return "\n".join(buf)


def gate_warnings(window: int) -> Counter:
    c = Counter()
    runs = sorted(GATES.glob("gate-*"), reverse=True)[:window]
    for run in runs:
        for log in run.glob("*.log"):
            try:
                text = log.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for line in text.splitlines():
                if "✘" in line or "•" in line or "تحذير" in line:
                    c[re.sub(r"\s+", " ", line.strip())[:90]] += 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(_date.today()))
    ap.add_argument("--window", type=int, default=7)
    a = ap.parse_args()

    faults = fault_rows()
    les = lessons()
    idx = enforcement_index()

    # 1) الدروس بلا مُفعِّل: رمز الدرس لا يظهر في أي بوابة أو أداة أو مهارة
    unenforced = [l for l in les if l.get("code") and str(l["code"]) not in idx]
    # 2) الأعطال التي قاعدتها المانعة لا تظهر في أي مُفعِّل
    rule_orphans = [f for f in faults if f["code"] not in idx]
    # 3) تكرار: رمز عطل واحد يظهر في أكثر من يوم
    by_code = Counter(f["code"] for f in faults)
    repeat_codes = {c: n for c, n in by_code.items() if n > 1}
    # 4) تحذيرات متكررة في آخر جولات
    warns = gate_warnings(a.window)
    recurring_warns = [(w, n) for w, n in warns.most_common(8) if n > 1]

    covered = len(les) - len(unenforced)
    pct = round(100 * covered / len(les)) if les else 100

    lines = [f"# موجز التحسين الذاتي — {a.date}", "",
             f"**تغطية الدروس بمُفعِّل:** {covered} من {len(les)} ({pct}%) · "
             f"**أعطال مسجّلة:** {len(faults)} · **تحذيرات متكررة:** {len(recurring_warns)}", ""]
    if unenforced:
        lines += ["## دروس بلا مُفعِّل (لم تتحوّل إلى بوابة — ستتكرر)", ""]
        for l in unenforced[:12]:
            lines.append(f"- `{l.get('code')}` {str(l.get('lesson'))[:110]}")
        lines.append("")
    if rule_orphans:
        lines += ["## أعطال قاعدتها المانعة غير مربوطة بمُفعِّل", ""]
        for f in rule_orphans[:12]:
            lines.append(f"- `{f['code']}` {f['title'][:90]}")
        lines.append("")
    if repeat_codes:
        lines += ["## رموز أعطال متكررة (سبب جذري لم يُغلق)", ""]
        lines += [f"- `{c}` × {n}" for c, n in sorted(repeat_codes.items(), key=lambda x: -x[1])[:10]]
        lines.append("")
    if recurring_warns:
        lines += ["## تحذيرات تتكرر بين الجولات (مرشّحة للترقية إلى مانع)", ""]
        lines += [f"- ×{n} {w}" for w, n in recurring_warns]
        lines.append("")
    if not (unenforced or rule_orphans or repeat_codes or recurring_warns):
        lines += ["لا بند مفتوحًا: كل درس له مُفعِّل، ولا تكرار في الرموز أو التحذيرات.", ""]

    out = B / "audit" / f"موجز-التحسين-{a.date}.md"
    out.write_text("\n".join(lines), encoding="utf-8")

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE.open("a", encoding="utf-8") as fh:
        for l in unenforced[:20]:
            fh.write(json.dumps({"date": a.date, "kind": "lesson_unenforced", "code": l.get("code"),
                                 "action": "ربط الدرس بمُفعِّل في بوابة أو قاعدة مهارة"}, ensure_ascii=False) + "\n")
        for w, n in recurring_warns:
            fh.write(json.dumps({"date": a.date, "kind": "recurring_warning", "count": n, "what": w,
                                 "action": "ترقية تدريجية إلى بند مانع بعد ثبوت التكرار"}, ensure_ascii=False) + "\n")

    print(f"  • تغطية الدروس بمُفعِّل: {covered}/{len(les)} ({pct}%)")
    print(f"  • دروس بلا مُفعِّل: {len(unenforced)} · أعطال بلا مُفعِّل: {len(rule_orphans)} · رموز متكررة: {len(repeat_codes)} · تحذيرات متكررة: {len(recurring_warns)}")
    print(f"  • الموجز: {out.relative_to(B)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
