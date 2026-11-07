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
from datetime import datetime, timezone

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
        except json.JSONDecodeError:   # سطر تالف في السجل يُتجاوَز ولا يُسقط الحكم
            continue
        if row.get("step"):
            last[row["step"]] = row
    return last


def _ts(value: object) -> datetime | None:
    """اقرأ توقيت دفتر الجولة بصيغة UTC، وأعد None عند غياب الدليل."""
    if not value:
        return None
    try:
        out = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return out if out.tzinfo else out.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def stale_gate_reason(
    gate_id: str,
    journal: dict,
    manifest_steps: list[dict],
    delivery_id: str = "D010",
) -> str:
    """اكتشف حكم G011 القديم بعد تغيّر مدخلاته وقبل D010.

    G011 يفحص التقرير المبني وعلامة الخط والنسخة الاحتياطية. لذلك فإن تشغيل
    B010 أو D005 بعد آخر تشغيل له يجعل سجله غير صالح للحكم، حتى لو كان دفتر
    الجولة يسمح بالاستمرار بحالة ``done_warn``. لا نُسقط الحكم ولا نحوّله إلى
    نجاح؛ نُصدر سبب منع صريحًا يُلزم ``--redo G011``.
    """
    if gate_id != "G011":
        return ""
    ids = [str(s.get("id", "")) for s in manifest_steps]
    try:
        gate_i = ids.index(gate_id)
        delivery_i = ids.index(delivery_id)
    except ValueError:
        return f"تعذّر إثبات ترتيب {gate_id} قبل {delivery_id} في المانيفست"
    gate_ts = _ts((journal.get(gate_id) or {}).get("ts"))
    if gate_ts is None:
        return f"سجل {gate_id} بلا توقيت تشغيل صالح — أعد تشغيله عبر --redo {gate_id}"
    for spec in manifest_steps[gate_i + 1 : delivery_i]:
        step_id = str(spec.get("id", ""))
        if not step_id or step_id.startswith("G"):
            continue
        entry = journal.get(step_id)
        if not entry or entry.get("status") == "waiting_agent":
            continue
        step_ts = _ts(entry.get("ts"))
        if step_ts is None:
            return (
                f"سجل {gate_id} غير صالح: الخطوة اللاحقة {step_id} بلا توقيت تشغيل "
                f"— أعد تشغيله عبر --redo {gate_id}"
            )
        if step_ts > gate_ts:
            return (
                f"سجل {gate_id} قديم بعد تشغيل {step_id} عند {entry.get('ts')} "
                f"(آخر تشغيل للبوابة {journal.get(gate_id, {}).get('ts')}) "
                f"— أعد تشغيله عبر --redo {gate_id}"
            )
    return ""


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


def classify(entry: dict, log_text: str, stale_reason: str = "") -> tuple[str, list[str]]:
    why: list[str] = []
    rc = entry.get("rc")
    try:
        rc_i = int(rc) if rc is not None else 0
    except (TypeError, ValueError):   # رمز غير رقمي ⇒ يُعامل صفرًا بلا ابتلاع أخطاء أخرى
        rc_i = 0
    if entry.get("status") == "failed":
        why.append("آخر حالة: failed")
    if rc_i >= 2:
        why.append(f"رمز الخروج {rc_i}")
    b = blocking_in_log(log_text)
    if b:
        why.append(f"حكم مانع في السجل: {b}")
    if stale_reason:
        why.append(stale_reason)
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
    ap.add_argument("--delivery-step", default="D010", help="حدّ التسليم الذي تُقاس قبله قدم G011")
    ap.add_argument("--json", default="")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    brain = pathlib.Path(a.root) if a.root else canonical_brain_root(pathlib.Path(__file__).resolve().parents[1])
    jl = brain / "logs" / "runbook" / f"{a.date}.jsonl"
    steps = journal_latest(jl)
    if not steps:
        print(f"   ✘ إدخال ناقص: لا دفتر جولة في {jl}")
        return 2
    manifest_path = brain / "runbook" / "runbook.json"
    try:
        manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_steps = manifest_doc.get("steps", []) if isinstance(manifest_doc, dict) else manifest_doc
        if not isinstance(manifest_steps, list):
            raise ValueError("steps ليست قائمة")
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"   ✘ إدخال ناقص: تعذّر قراءة مانيفست ترتيب البوابات: {exc}")
        return 2
    gates = sorted(k for k in steps if k.startswith("G"))
    if a.step:
        gates = [g for g in gates if g == a.step]
    verdicts, blockers, warns = {}, [], []
    for g in gates:
        lp = brain / "logs" / "runbook" / a.date / f"{g}.log"
        txt = lp.read_text(encoding="utf-8", errors="ignore") if lp.exists() else ""
        stale = stale_gate_reason(g, steps, manifest_steps, a.delivery_step)
        state, why = classify(steps[g], txt, stale)
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
