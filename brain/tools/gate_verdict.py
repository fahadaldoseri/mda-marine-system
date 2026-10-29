#!/usr/bin/env python3
"""حكم البوابات — يمنع النشر عند حكم مانع (ك-312).

المشكلة التي يحلّها: `gates-status` يقبل الخطوة بحالة `done_warn`، وبعض البوابات تكتب في
سجلّها حكمًا مانعًا صريحًا ("الحكم: ممنوع التسليم" أو "مخالفة مانعة" بعدد موجب) مع رمز
خروج 1. فكان النشر يمرّ رغم حكم مانع في السجل.

القاعدة: لكل خطوة بوابة، تُقرأ **آخر** حالة لها من دفتر الجولة (`logs/runbook/<DATE>.jsonl`)،
ويُقرأ سجلّها الحالي (`logs/runbook/<DATE>/<STEP>.log`)، وتُصنَّف:
  · مانع  — آخر حالة `failed` · أو رمز خروج >= 2 · أو حكم صريح «ممنوع التسليم» في السجل
  · تحذير — رمز خروج 1 بلا حكم مانع · أو حالة `done_warn`
  · سليم  — غيرهما
الخروج: 0 لا مانع · 1 يوجد مانع (لا نشر) · 2 إدخال ناقص.

الاستعمال: python3 tools/gate_verdict.py --date 2026-10-29 [--step G011] [--json out.json]
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, sys

BLOCK_VERDICTS = ("ممنوع التسليم", "الحكم: ممنوع", "منع التسليم")
BLOCK_PATTERNS = (re.compile(r"مخالفة مانعة\s*[:：]?\s*([1-9]\d*)\b"),)
OK_MARKERS = ("لا مخالفات مانعة", "مخالفة مانعة: 0", "المخالفات المانعة: 0")
LABELS = ("الحكم:", "النتيجة:", "الحصيلة:", "verdict:")


def _root(env: str, base: pathlib.Path, *names: str) -> pathlib.Path:
    v = os.environ.get(env)
    if v:
        return pathlib.Path(v)
    for n in names:
        if (base / n).is_dir():
            return base / n
    return base / names[0]


def journal_latest(path: pathlib.Path) -> dict:
    last: dict = {}
    if not path.exists():
        return last
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("step"):
            last[row["step"]] = row
    return last


def _strip_labels(line: str) -> str:
    """يُنزع وسم الحكم وأي رموز رائدة ليبقى نص الحكم في أول السطر."""
    s = line.strip().lstrip("·-*•#> ").strip()
    changed = True
    while changed:
        changed = False
        for lab in LABELS:
            if s.startswith(lab):
                s = s[len(lab):].strip()
                changed = True
    return s


def blocking_in_log(text: str) -> str:
    """حكم مانع = سطر **يبدأ** بالحكم، لا ذِكر عبارة داخل وصف اختبار (ك-325).

    مثال على الإيجابية الكاذبة التي يمنعها هذا الشرط: سطر اختبار يقول
    «5) رمز الانهيار 70 (حارس موحّد) يمنع التسليم» — وصفٌ لا حكم.
    """
    for m in BLOCK_PATTERNS:
        hit = m.search(text)
        if hit and not any(k in text for k in OK_MARKERS):
            return f"مخالفة مانعة ({hit.group(1)})"
    for v in BLOCK_VERDICTS:
        if v == "الحكم: ممنوع":
            for line in text.splitlines():
                if _strip_labels(line).startswith("ممنوع"):
                    return v
            continue
        for line in text.splitlines():
            if _strip_labels(line).startswith(v):
                return v
    return ""


def classify(entry: dict, log_text: str) -> tuple[str, list[str]]:
    why: list[str] = []
    rc = entry.get("rc")
    try:
        rc_i = int(rc) if rc is not None else 0
    except Exception:
        rc_i = 0
    if entry.get("status") == "failed":
        why.append("آخر حالة: failed")
    if rc_i >= 2:
        why.append(f"رمز الخروج {rc_i}")
    b = blocking_in_log(log_text)
    if b:
        why.append(f"حكم مانع في السجل: {b}")
    if why:
        return "مانع", why
    if entry.get("status") == "done_warn" or rc_i == 1:
        w = []
        if entry.get("status") == "done_warn":
            w.append("done_warn")
        if rc_i == 1:
            w.append("رمز الخروج 1")
        return "تحذير", w
    return "سليم", []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--root", default="")
    ap.add_argument("--step", default="", help="خطوة واحدة فقط")
    ap.add_argument("--json", default="")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    brain = pathlib.Path(a.root) if a.root else _root("BRAIN_DIR", pathlib.Path(__file__).resolve().parents[1].parent, "brain-marine-news", "brain")
    jl = brain / "logs" / "runbook" / f"{a.date}.jsonl"
    steps = journal_latest(jl)
    if not steps:
        print(f"   ✘ إدخال ناقص: لا دفتر جولة في {jl}")
        return 2
    gates = sorted(k for k in steps if k.startswith("G"))
    if a.step:
        gates = [g for g in gates if g == a.step]
    verdicts, blockers, warns = {}, [], []
    for g in gates:
        lp = brain / "logs" / "runbook" / a.date / f"{g}.log"
        txt = lp.read_text(encoding="utf-8", errors="ignore") if lp.exists() else ""
        state, why = classify(steps[g], txt)
        verdicts[g] = {"state": state, "why": why, "rc": steps[g].get("rc"), "ts": steps[g].get("ts"), "log": str(lp.name)}
        if state == "مانع":
            blockers.append((g, why))
        elif state == "تحذير":
            warns.append((g, why))
    if not a.quiet:
        print(f"   حكم البوابات {a.date}: فُحصت {len(gates)} بوابة · مانعة {len(blockers)} · تحذير {len(warns)}")
        for g, why in blockers:
            print(f"   ✘ {g}: " + " · ".join(why))
        for g, why in warns[:12]:
            print(f"   ⚠ {g}: " + " · ".join(why))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"date": a.date, "verdicts": verdicts}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if blockers:
        print(f"   ✘ النتيجة: ممنوع — {len(blockers)} بوابة بحكم مانع. لا نشر حتى الإصلاح وإعادة تشغيل البوابة.")
        return 1
    print("   ✔ النتيجة: لا حكم مانع في بوابات " + a.date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
