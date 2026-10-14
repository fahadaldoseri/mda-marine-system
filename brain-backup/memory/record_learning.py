#!/usr/bin/env python3
"""Append a normalized adaptive-learning event to the Brain JSONL log."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lesson", required=True)
    parser.add_argument("--category", choices=["linguistic", "formatting", "source", "calculation", "analysis", "operational"], required=True)
    parser.add_argument("--origin", choices=["user", "validator", "recurrence", "review"], required=True)
    parser.add_argument("--replacement", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--status", choices=["candidate", "confirmed", "rejected", "promoted"], default="candidate")
    parser.add_argument("--log", default="/home/ubuntu/brain-marine-news/memory/learning-log.jsonl")
    args = parser.parse_args()

    normalized = " ".join(args.lesson.split()).casefold()
    lesson_id = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    event = {
        "lesson_id": lesson_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "lesson": args.lesson.strip(),
        "replacement": args.replacement.strip(),
        "category": args.category,
        "origin": args.origin,
        "evidence": args.evidence.strip(),
        "status": args.status,
    }
    path = Path(args.log)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(json.dumps(event, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
