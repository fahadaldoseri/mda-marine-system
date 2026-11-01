#!/usr/bin/env python3
"""حارس بصمة النص — البند (أ) من مراجعة صاحب القرار 2026-10-23.

المشكلة التي يعالجها: كانت خطوات تعدّل نص التقرير تعمل بعد بناء الصفحة وPDF وWord،
فيُنشر مخرج مبني من نص قبل الإصلاح. الحارس يثبت أن ما بُني هو النص النهائي:

  1) `--stage record`: تُسجَّل بصمة نص التقرير وزمن تعديله لحظة ما قبل البناء.
  2) `--stage verify`: تُقارن البصمة بعد كل الخطوات؛ أي اختلاف = منع (رمز 70).
     ويُتحقق أيضًا أن مخرجات البناء (HTML · PDF · Word) أحدث من النص،
     فإن كان المخرج أقدم فمعناه أنه بُني قبل آخر تعديل ⇒ منع.
"""
from __future__ import annotations
import os

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
def _pick_site() -> Path:
    """ك-175: جذر الموقع (بلا dist) من أول مرشّح يحمل dist/reports فعليًا."""
    for c in (os.environ.get("SITE_DIR"), os.environ.get("SITE"), str(B.parent / "seawatch")):
        if c and (Path(c) / "dist" / "reports").is_dir():
            return Path(c)
    return B.parent / "seawatch"


SITE = _pick_site()
CRASH = 70


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stamp_path(date: str, logdir: Path) -> Path:
    return logdir / f".text-hash-{date}.json"


def print_disabled() -> bool:
    """هل خط الطباعة معطّل بطلب المالك في المانيفست الحاكم؟ (استثناء معلن لا إخفاء عطل)"""
    try:
        rb = json.loads((B / "runbook" / "runbook.json").read_text(encoding="utf-8"))
    except Exception:
        return False
    if isinstance(rb.get("print"), dict) and rb["print"].get("disabled") is True:
        return True
    if isinstance(rb.get("print"), dict) and rb["print"].get("enabled") is False:
        return True
    for step in rb.get("steps", []):
        if step.get("id") in ("B020", "B030"):
            return step.get("disabled") is True
    return False


def outputs(date: str) -> list[Path]:
    """المخرجات الملزمة: الصفحة والنسخة المطابقة. PDF يُلزم فقط حين الطباعة مسلَّحة."""
    outs = [SITE / "dist" / "reports" / f"{date}.html"]
    if not print_disabled():
        outs.append(SITE / "dist" / "reports" / "pdf" / f"{date}.pdf")
    if not print_disabled():
        outs.append(B / "reports" / "docx" / f"التقرير-اليومي-{date}-طبق-الأصل.docx")
    return outs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--stage", choices=["record", "verify"], required=True)
    ap.add_argument("--logdir", default=None)
    a = ap.parse_args()
    logdir = Path(a.logdir) if a.logdir else B / "logs" / f"gate-{a.date}"
    logdir.mkdir(parents=True, exist_ok=True)
    md = B / "reports" / f"{a.date}-sectioned.md"
    if not md.exists():
        print(f"  ✘ لا نص تقرير: {md}")
        return CRASH
    sp = stamp_path(a.date, logdir)

    if a.stage == "record":
        data = {
            "date": a.date,
            "md": str(md.relative_to(B)),
            "sha256": sha(md),
            "mtime": md.stat().st_mtime,
            "recorded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  · بصمة النص قبل البناء: {data['sha256'][:16]} — {data['recorded_utc']}")
        return 0

    if not sp.exists():
        print(f"  ✘ لا بصمة مسجّلة قبل البناء ({sp}) — لا يثبت أن المخرج من النص النهائي")
        return CRASH
    rec = json.loads(sp.read_text(encoding="utf-8"))
    now = sha(md)
    bad: list[str] = []
    if now != rec["sha256"]:
        bad.append(f"نص التقرير تغيّر بعد البناء: {rec['sha256'][:16]} → {now[:16]}")
    for out in outputs(a.date):
        if not out.exists():
            bad.append(f"مخرج مفقود: {out.name}")
            continue
        if out.stat().st_mtime + 1 < rec["mtime"]:
            bad.append(f"مخرج أقدم من النص (بُني قبل آخر تعديل): {out.name}")
    if bad:
        for x in bad:
            print(f"  ✘ {x}")
        print("  ✘ النص المبني ليس النص النهائي — منع (البند أ)")
        return CRASH
    print(f"  ✓ النص النهائي هو المبني: {now[:16]} · كل مخرج ملزم أحدث من النص ({len(outputs(a.date))} مخرجًا)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
