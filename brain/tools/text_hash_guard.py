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
SITE = Path(os.environ.get("SITE_DIR") or os.environ.get("SITE")
            or str(Path(__file__).resolve().parents[1].parent / "seawatch")) / "dist"
CRASH = 70


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stamp_path(date: str, logdir: Path) -> Path:
    return logdir / f".text-hash-{date}.json"


def outputs(date: str) -> list[Path]:
    return [
        SITE / "dist" / "reports" / f"{date}.html",
        SITE / "dist" / "reports" / "pdf" / f"{date}.pdf",
        B / "reports" / "docx" / f"التقرير-اليومي-{date}-طبق-الأصل.docx",
    ]


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
    print(f"  ✓ النص النهائي هو المبني: {now[:16]} · المخرجات الثلاثة أحدث من النص")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
