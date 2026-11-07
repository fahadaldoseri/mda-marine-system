#!/usr/bin/env python3
"""بوابة فشل مغلق لسلامة الأصول الحاكمة."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT.parents[1]
CONFIG_DEFAULT = PROJECT_ROOT / "tools" / "governing-assets.txt"
LEDGER_DEFAULT = PROJECT_ROOT / "evidence" / "merkle" / "ledger.jsonl"
MIRROR_SKILLS = Path("/home/ubuntu/mda-marine-system/skills").resolve()
LOCAL_SKILLS = Path("/home/ubuntu/skills").resolve()

sys.path.insert(0, str(SCRIPT.parent))
import append_only_ledger as ledger  # noqa: E402
import governing_assets_merkle as merkle  # noqa: E402


def latest_snapshot(path: Path, date: str | None) -> tuple[dict | None, list[str], bool]:
    ok, errors, entries = ledger.verify_ledger(path)
    snaps = [entry for entry in entries if entry.get("kind") == "snapshot"]
    if date:
        snaps = [entry for entry in snaps if str(entry.get("ts", "")).startswith(date)]
    return (snaps[-1] if snaps else None), errors, ok


def snapshot_file_for_entry(entry: dict, root: Path) -> Path | None:
    # Ledger entries deliberately carry the root/count only; locate the newest JSON
    # snapshot with the same root and file count, then verify its own root below.
    candidates = []
    for path in sorted((root / "evidence" / "merkle").glob("*.json")):
        try:
            value = merkle.load_snapshot(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if value.get("root") == entry.get("root") and value.get("file_count") == entry.get("files"):
            candidates.append(path)
    return candidates[-1] if candidates else None


def content_signature(record: dict) -> tuple:
    return (record.get("exists"), record.get("lines"), record.get("sha256"), record.get("size"))


def path_in_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def mirror_expected(config: Path) -> list[Path]:
    specs, excludes = merkle.parse_config(config)
    rewritten = []
    for kind, argument in specs:
        # The mirror root contains only the configured skill assets. Brain assets
        # are checked against the local snapshot, not treated as mirror paths.
        if not (argument == str(LOCAL_SKILLS) or argument.startswith(str(LOCAL_SKILLS) + "/")):
            continue
        argument = str(MIRROR_SKILLS) + argument[len(str(LOCAL_SKILLS)):]
        rewritten.append((kind, argument))
    rewritten_excludes = excludes
    return merkle.collect_paths(rewritten, rewritten_excludes)


def run_gate(config: Path, ledger_path: Path, mirror: Path, date: str | None) -> dict:
    violations: list[str] = []
    snapshot_entry, ledger_errors, ledger_ok = latest_snapshot(ledger_path, date)
    if not ledger_ok:
        violations.extend(f"ledger: {error}" for error in ledger_errors)
    if snapshot_entry is None:
        violations.append("ledger: no snapshot entry for requested date/latest")

    current = merkle.build_snapshot(config)
    snapshot_path = snapshot_file_for_entry(snapshot_entry, PROJECT_ROOT) if snapshot_entry else None
    recorded = None
    if snapshot_path is None and snapshot_entry is not None:
        violations.append("snapshot: JSON evidence for latest ledger entry not found")
    elif snapshot_path is not None:
        try:
            recorded = merkle.load_snapshot(snapshot_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            violations.append(f"snapshot: unreadable: {exc}")

    if recorded is not None:
        if current["root"] != recorded.get("root"):
            violations.append(f"snapshot root mismatch: current {current['root']} != recorded {recorded.get('root')}")
        current_map = {item["path"]: item for item in current["files"]}
        recorded_map = {item["path"]: item for item in recorded.get("files", [])}
        for path in sorted(set(current_map) | set(recorded_map)):
            if path not in recorded_map:
                violations.append(f"snapshot missing recorded path: {path}")
            elif path not in current_map:
                violations.append(f"current missing path: {path}")
            elif content_signature(current_map[path]) != content_signature(recorded_map[path]):
                violations.append(f"snapshot content mismatch: {path}")

    # The repository mirror comparison is intentionally limited to configured skill assets;
    # brain assets have no path-equivalent under /home/ubuntu/mda-marine-system/skills.
    for local_record in current["files"]:
        local_path = Path(local_record["path"])
        if not path_in_root(local_path, LOCAL_SKILLS):
            continue
        relative = local_path.relative_to(LOCAL_SKILLS)
        mirror_path = mirror / relative
        mirror_record = merkle.file_record(mirror_path)
        if content_signature(local_record) != content_signature(mirror_record):
            violations.append(f"mirror mismatch: {relative.as_posix()} (local vs {mirror_path})")

    current_skill_paths = {
        Path(item["path"]).relative_to(LOCAL_SKILLS).as_posix()
        for item in current["files"]
        if path_in_root(Path(item["path"]), LOCAL_SKILLS)
    }
    for mirror_path in mirror_expected(config):
        relative = mirror_path.relative_to(MIRROR_SKILLS).as_posix()
        if relative not in current_skill_paths:
            violations.append(f"mirror-only or local-missing asset: {relative}")

    return {
        "status": "PASS" if not violations else "BLOCK",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "date": date,
        "current_root": current["root"],
        "current_files": current["file_count"],
        "ledger": ledger_path.as_posix(),
        "ledger_verified": ledger_ok,
        "snapshot_entry": snapshot_entry,
        "snapshot_file": snapshot_path.as_posix() if snapshot_path else None,
        "mirror": mirror.as_posix(),
        "violations": violations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--date", help="select snapshot entries whose UTC timestamp starts YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT, help=argparse.SUPPRESS)
    parser.add_argument("--ledger", type=Path, default=LEDGER_DEFAULT, help=argparse.SUPPRESS)
    parser.add_argument("--mirror", type=Path, default=MIRROR_SKILLS, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        parser.error("--date must be YYYY-MM-DD")
    try:
        result = run_gate(args.config, args.ledger, args.mirror.resolve(), args.date)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"status": "BLOCK", "violations": [f"measurement error: {exc}"]}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']} · root {result.get('current_root', 'unknown')} · files {result.get('current_files', 'unknown')}")
        for violation in result.get("violations", []):
            print(f"- {violation}")
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
