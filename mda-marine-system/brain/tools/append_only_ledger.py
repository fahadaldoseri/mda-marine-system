#!/usr/bin/env python3
"""سجل ملحق: hash = SHA-256 للحقول السابقة بما فيها prev_hash."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT.parents[1]
LEDGER_DEFAULT = PROJECT_ROOT / "evidence" / "merkle" / "ledger.jsonl"
FIELDS = ("seq", "ts", "kind", "root", "files", "prev_hash")
KINDS = ("snapshot", "restore", "incident")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def entry_hash(entry: dict) -> str:
    body = {field: entry.get(field) for field in FIELDS}
    return hashlib.sha256(canonical(body)).hexdigest()


def read_entries(path: Path) -> tuple[list[tuple[int, dict | None]], list[str]]:
    if not path.exists():
        return [], [f"ledger missing: {path}"]
    rows: list[tuple[int, dict | None]] = []
    errors: list[str] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            errors.append(f"line {line_no}: blank line")
            rows.append((line_no, None))
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON: {exc.msg}")
            rows.append((line_no, None))
            continue
        if not isinstance(value, dict):
            errors.append(f"line {line_no}: JSON value is not an object")
            rows.append((line_no, None))
        else:
            rows.append((line_no, value))
    return rows, errors


def verify_ledger(path: Path) -> tuple[bool, list[str], list[dict]]:
    rows, errors = read_entries(path)
    entries: list[dict] = []
    expected_seq = 1
    previous_hash = ""
    for line_no, entry in rows:
        if entry is None:
            continue
        missing = [field for field in (*FIELDS, "hash") if field not in entry]
        if missing:
            errors.append(f"line {line_no}: missing fields {','.join(missing)}")
            continue
        if entry.get("seq") != expected_seq:
            errors.append(f"line {line_no}: sequence gap/rewind: expected {expected_seq}, got {entry.get('seq')}")
            expected_seq = entry.get("seq") if isinstance(entry.get("seq"), int) else expected_seq
        if entry.get("prev_hash") != previous_hash:
            errors.append(f"line {line_no}: prev_hash mismatch (expected {previous_hash}, got {entry.get('prev_hash')})")
        computed = entry_hash(entry)
        if entry.get("hash") != computed:
            errors.append(f"line {line_no}: hash mismatch (expected {computed}, got {entry.get('hash')})")
        previous_hash = entry.get("hash") if isinstance(entry.get("hash"), str) else previous_hash
        expected_seq += 1
        entries.append(entry)
    if not rows:
        errors.append("ledger empty: no chain to verify")
    return not errors, errors, entries


def append_entry(path: Path, kind: str, root: str, files: int) -> dict:
    ok, errors, entries = verify_ledger(path)
    if path.exists() and not ok:
        raise ValueError("existing ledger is invalid: " + " | ".join(errors))
    previous = entries[-1] if entries else None
    entry = {
        "seq": (previous["seq"] + 1) if previous else 1,
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "root": root,
        "files": files,
        "prev_hash": previous["hash"] if previous else "",
    }
    entry["hash"] = entry_hash(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=False, separators=(",", ":")) + "\n")
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--append", action="store_true", help="append one chain entry")
    modes.add_argument("--verify", action="store_true", help="verify every ledger line")
    parser.add_argument("--kind", choices=KINDS, help="entry kind for --append")
    parser.add_argument("--root", help="Merkle root for --append")
    parser.add_argument("--files", type=int, default=0, help="file count for --append")
    parser.add_argument("--ledger", type=Path, default=LEDGER_DEFAULT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.append:
            if not args.kind or not args.root or args.files < 0:
                parser.error("--append requires --kind, --root and non-negative --files")
            entry = append_entry(args.ledger, args.kind, args.root, args.files)
            print(json.dumps(entry, ensure_ascii=False, sort_keys=False))
            return 0
        ok, errors, entries = verify_ledger(args.ledger)
        if ok:
            print(f"verify: OK · entries {len(entries)}")
            return 0
        print("verify: FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
