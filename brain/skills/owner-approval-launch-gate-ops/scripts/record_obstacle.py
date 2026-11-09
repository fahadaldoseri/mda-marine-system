#!/usr/bin/env python3
"""تسجيل عائق أثناء التنفيذ — بأمر «ممنوع التوقف»: لا يُقبل عائق بلا إجراء.

القاعدة: كل عائق يُغلق بمسارين — إصلاح جذري، أو بديل معلن يعمل فعلًا. التسجيل بلا إجراء،
أو بإجراء يقول «توقفنا» أو «لم نجد حلًا»، يُرفض بـrc=2 ولا يُكتب سطر.

الاستعمال:
    record_obstacle.py --phase أ --obstacle "وصف العرض" --cause "السبب الجذري" \
        --action "إصلاح: ما فعلته" --evidence "أمر → rc=0" [--status مُغلق] [--log path.jsonl]

الخروج: 0 سُجِّل · 2 رُفض (إجراء ناقص) · 64 خطأ استعمال.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_START = ("إصلاح", "بديل", "تحصين", "توحيد", "توسيع")
REFUSED = ("توقف", "توقفنا", "لا حل", "لم نجد", "مستحيل", "بدون حل", "لا يمكن")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--obstacle", required=True)
    ap.add_argument("--cause", required=True)
    ap.add_argument("--action", required=True)
    ap.add_argument("--evidence", default="")
    ap.add_argument("--status", default="مُغلق", choices=["مُغلق", "مفتوح"])
    ap.add_argument("--log", default="")
    a = ap.parse_args()

    action = a.action.strip()
    if not action:
        print("  ✘ رُفض: لا إجراء. أمر المالك: ممنوع التوقف — إصلاح أو بديل.")
        return 2
    if any(w in action for w in REFUSED):
        print(f"  ✘ رُفض: الإجراء يحمل «توقف/لا حل» — {action[:60]}")
        return 2
    if not action.startswith(VALID_START):
        print(f"  ✘ رُفض: الإجراء لا يبدأ بمسار معلن ({' · '.join(VALID_START)}) — {action[:60]}")
        return 2
    if a.status == "مُغلق" and not a.evidence.strip():
        print("  ✘ رُفض: إغلاق بلا دليل (أمر ومخرج). إما مرّر --evidence أو اجعل الحالة «مفتوح».")
        return 2

    row = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": a.phase,
        "obstacle": a.obstacle.strip(),
        "cause": a.cause.strip(),
        "action": action,
        "status": a.status,
        "evidence": a.evidence.strip(),
    }
    log = Path(a.log) if a.log else Path(f"obstacles-{row['date']}.jsonl")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  ✔ سُجِّل العائق ({row['status']}) في {log}")
    print(f"     المسار: {action[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())