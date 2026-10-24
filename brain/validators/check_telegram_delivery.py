import sys
#!/usr/bin/env python3
"""قناة تنبيه: هل وصل تقرير اليوم على تلغرام؟ (طلب فهد 2026-10-24، البند 14)

لا يُرسل شيئًا. يقرأ سجل الإرسال `logs/telegram-sends.jsonl` ويحكم:
  · لا محاولة لهذا التاريخ            → تحذير (1) — لم يُحاول الإرسال
  · آخر محاولة مرفوضة                 → تحذير (1) + سبب الرفض
  · آخر محاولة أُرسلت                 → نجاح (0)
ويكتب النتيجة في `logs/telegram-delivery-<date>.json` ليقرأها التقرير أو البوابة.

رموز الخروج: 0 أُرسل · 1 تحذير (لم يُرسل) · 2 خطأ.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEND_LOG = ROOT / "logs" / "telegram-sends.jsonl"


def entries(date: str) -> list[dict]:
    if not SEND_LOG.is_file():
        return []
    out = []
    for line in SEND_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("date") == date:
            out.append(e)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    rows = entries(args.date)
    last = rows[-1] if rows else None
    if last is None:
        verdict, status, detail = "لم يُحاول الإرسال لهذا التاريخ", "warn", ""
    elif last.get("decision") == "sent":
        verdict, status, detail = "أُرسل", "ok", str(last.get("detail", ""))[:160]
    else:
        verdict, status = "مرفوض", "warn"
        detail = str(last.get("reason") or last.get("detail") or "")[:200]

    out = ROOT / "logs" / f"telegram-delivery-{args.date}.json"
    out.write_text(json.dumps({"date": args.date, "status": status, "verdict": verdict,
                               "detail": detail, "attempts": len(rows),
                               "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                              ensure_ascii=False, indent=1), encoding="utf-8")

    line = f"تلغرام: {verdict} — {detail}" if detail else f"تلغرام: {verdict}"
    if not args.quiet:
        print(("✔ " if status == "ok" else "⚠ ") + line)
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
