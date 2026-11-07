#!/usr/bin/env python3
"""أرشفة نص ملخص تلغرام (طلب فهد 2026-10-24، البند 13).

العلّة: نص الرسالة المرسلة على تلغرام كان يُكتب في ملف مؤقت يُحذف، فلا يمكن لاحقًا
معرفة ما أُرسل حرفيًا. هذا السجل يحفظ النص كما أُرسل.

الاستخدام:
  python3 tools/archive_tg_digest.py --date 2026-10-24 --file /tmp/tg-digest.html
  python3 tools/archive_tg_digest.py --date 2026-10-24 --from-logs     # يستنتج من سجل الإرسال
رموز الخروج: 0 أُرشف · 3 لا نص لأرشفته (لا يُمنع التسليم) · 2 خطأ.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "logs" / "telegram-archive"
SEND_LOG = ROOT / "logs" / "telegram-sends.jsonl"
CANDIDATES = ("/tmp/tg-digest-{date}.html", "/tmp/tg-digest.html", "/tmp/digest-{date}.html")


def find_digest(date: str) -> Path | None:
    for pattern in CANDIDATES:
        p = Path(pattern.format(date=date))
        if p.is_file():
            return p
    return None


def sent_meta(date: str) -> dict:
    """آخر إرسال ناجح لتاريخ معيّن من سجل الإرسال (بلا أي سرّ)."""
    if not SEND_LOG.is_file():
        return {}
    last: dict = {}
    for line in SEND_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("date") == date and e.get("decision") == "sent":
            last = e
    return last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--file")
    ap.add_argument("--from-logs", action="store_true")
    args = ap.parse_args()

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    src = Path(args.file) if args.file else find_digest(args.date)
    if not src or not src.is_file():
        print(f"⚠ لا نص ملخص موجود لأرشفته للتاريخ {args.date} — لم يُنشأ ملف (لا منع)")
        return 3

    stamp = time.strftime("%Y-%m-%dT%H%M%SZ", time.gmtime())
    out = ARCHIVE / f"{args.date}-{stamp}.html"
    shutil.copyfile(src, out)
    meta = sent_meta(args.date)
    (ARCHIVE / f"{args.date}-{stamp}.meta.json").write_text(json.dumps({
        "date": args.date, "archived_at": stamp, "source": str(src),
        "sent_ts": meta.get("ts"), "detail": meta.get("detail"), "bytes": out.stat().st_size,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✔ أُرشف نص الملخص: {out.relative_to(ROOT)} ({out.stat().st_size} بايت)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())