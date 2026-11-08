#!/usr/bin/env python3
"""يُجدّد البوابات المتقادمة قبل النشر بدل رفض النشر بسببها.

المنع يبقى كما هو: أي بوابة بحكم مانع حقيقي تُبقي النشر موقوفًا. أما البوابة التي
صار سجلها «قديمًا» لأن خطوة أُعيد تشغيلها بعدها، فتُعاد هي نفسها عبر المحرّك
(--redo Gxxx) ثم يُعاد الحكم — وهذا ما يمنع الانتقال الصامت إلى القناة البديلة.

الاستخدام: python3 tools/refresh_stale_gates.py --date YYYY-MM-DD [--root .] [--rounds 1]
الخروج: 0 لا مانع بعد التجديد · 2 يوجد مانع باقٍ أو فشل التجديد.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

REDO_RE = re.compile(r"--redo\s+([A-Za-z]\d+)")


def verdict(date: str, root: pathlib.Path, out: pathlib.Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(root / "tools" / "gate_verdict.py"),
         "--date", date, "--root", str(root), "--delivery-step", "D010", "--json", str(out)],
        cwd=root, text=True, capture_output=True)
    try:
        doc = json.loads(out.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doc = {}
    return proc.returncode, doc


def stale_gate_ids(doc: dict) -> list[str]:
    ids: set[str] = set()
    verdicts = doc.get("verdicts") or {}
    items = verdicts.values() if isinstance(verdicts, dict) else verdicts
    for item in items:
        if not isinstance(item, dict):
            continue
        why = item.get("why") or []
        if isinstance(why, str):
            why = [why]
        for text in why:
            for hit in REDO_RE.finditer(str(text)):
                ids.add(hit.group(1))
    return sorted(ids)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--rounds", type=int, default=1)
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    out = root / "logs" / f"gate-verdict-{a.date}.json"

    for attempt in range(a.rounds + 1):
        rc, doc = verdict(a.date, root, out)
        if rc == 0:
            print("   ✔ لا بوابة بحكم مانع" + (" بعد التجديد" if attempt else ""))
            return 0
        ids = stale_gate_ids(doc)
        if not ids:
            print("   ✘ مانع غير قابل للتجديد — النشر يبقى موقوفًا")
            return 2
        if attempt == a.rounds:
            print(f"   ✘ بوابة متقادمة بعد التجديد: {' '.join(ids)}")
            return 2
        print(f"   ↻ تجديد البوابات المتقادمة: {' '.join(ids)}")
        proc = subprocess.run(
            [sys.executable, str(root / "tools" / "runbook.py"), "run",
             "--date", a.date, "--redo", ",".join(ids)],
            cwd=root, text=True, capture_output=True)
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-4:]
        for line in tail:
            print("     " + line.strip()[:150])
        if proc.returncode != 0:
            print(f"   ✘ فشل تجديد البوابات (رمز {proc.returncode})")
            return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())