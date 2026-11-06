#!/usr/bin/env python3
"""سجّل درس تشغيل وحاجزًا مقترحًا في learning-log.jsonl بلا شبكة."""
from __future__ import annotations

import argparse
import datetime as _dt
import fcntl
import hashlib
import json
from pathlib import Path
import sys

REQUIRED = ("ts", "entry_kind", "cls", "status", "symptom", "cause", "fix", "barrier")


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _fingerprint(entry: dict[str, str]) -> str:
    canonical = "\x1f".join(entry[key].strip() for key in REQUIRED if key != "ts")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_line(raw: str, line_no: int) -> dict[str, str]:
    if not raw.strip():
        raise ValueError(f"السطر {line_no} فارغ")
    try:
        item = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"السطر {line_no} ليس JSON صالحًا") from exc
    if not isinstance(item, dict):
        raise ValueError(f"السطر {line_no} ليس كائن JSON")
    missing = [key for key in REQUIRED if key not in item]
    if missing:
        raise ValueError(f"السطر {line_no} يفتقد الحقول: {', '.join(missing)}")
    bad = [key for key in REQUIRED if not _nonempty(item[key])]
    if bad:
        raise ValueError(f"السطر {line_no} يحوي حقولًا فارغة أو غير نصية: {', '.join(bad)}")
    return {key: item[key] for key in REQUIRED}


def _timestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain", type=Path, help="جذر المشروع؛ الافتراضي يحدد memory/learning-log.jsonl")
    parser.add_argument("--learning", type=Path, help="مسار سجل التعلم؛ يتقدم على --brain")
    for key in ("entry-kind", "cls", "status", "symptom", "cause", "fix", "barrier"):
        parser.add_argument(f"--{key}", required=True)
    args = parser.parse_args()
    if args.learning is None and args.brain is None:
        parser.error("أعطِ --brain أو --learning")
    return args


def _path(args: argparse.Namespace) -> Path:
    if args.learning is not None:
        return args.learning.expanduser().resolve()
    return (args.brain.expanduser().resolve() / "memory" / "learning-log.jsonl")


def _proposal(entry: dict[str, str], fp: str) -> dict[str, str]:
    return {
        "barrier_id": f"runbook-barrier-{fp[:12]}",
        "if_symptom": entry["symptom"],
        "root_cause": entry["cause"],
        "require_before_close": entry["barrier"],
        "rule_to_insert": f"امنع إغلاق الحالة عند ظهور «{entry['symptom']}» ما لم يتحقق: {entry['barrier']}",
    }


def main() -> int:
    args = _parse_args()
    path = _path(args)
    entry = {
        "ts": _timestamp(),
        "entry_kind": args.entry_kind,
        "cls": args.cls,
        "status": args.status,
        "symptom": args.symptom,
        "cause": args.cause,
        "fix": args.fix,
        "barrier": args.barrier,
    }
    if any(not _nonempty(value) for value in entry.values()):
        print("✘ منع مغلق: كل الحقول الثمانية مطلوبة وغير فارغة.", file=sys.stderr)
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.seek(0)
            existing: list[dict[str, str]] = []
            for line_no, raw in enumerate(handle, 1):
                try:
                    existing.append(_validate_line(raw, line_no))
                except ValueError as exc:
                    print(f"✘ منع مغلق: سجل التعلم غير صالح ({exc}). لم يُكتب شيء.", file=sys.stderr)
                    return 2
            fp = _fingerprint(entry)
            if any(_fingerprint(item) == fp for item in existing):
                print(f"⏸ الدرس موجود؛ لم يُكرّر الإدخال (البصمة {fp[:16]}).")
                print("اقتراح التشديد القابل للإدراج:")
                print(json.dumps(_proposal(entry, fp), ensure_ascii=False, indent=2))
                return 0
            handle.seek(0, 2)
            handle.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
    except OSError as exc:
        print(f"✘ منع مغلق: تعذّر فتح سجل التعلم ({exc.__class__.__name__}).", file=sys.stderr)
        return 2
    fp = _fingerprint(entry)
    print(f"✔ سُجّل الدرس في {path} (البصمة {fp[:16]}).")
    print("اقتراح التشديد القابل للإدراج:")
    print(json.dumps(_proposal(entry, fp), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
