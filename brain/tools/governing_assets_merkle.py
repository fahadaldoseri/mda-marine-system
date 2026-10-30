#!/usr/bin/env python3
"""حساب شجرة Merkle قابلة لإعادة التشغيل للأصول الحاكمة.

الأوراق هي SHA-256 لمحتوى الملف؛ الورقة المفقودة هي SHA-256 لوسم غياب ثابت
يضم المسار. تُرتّب الأوراق حسب المسار المطلق. العقد الداخلية SHA-256 لضم
البايتات الخام لتجزئتي الابنين، ويُكرّر الابن الأخير عند العدد الفردي.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCRIPT = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT.parents[1]
CONFIG_DEFAULT = PROJECT_ROOT / "tools" / "governing-assets.txt"
EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "merkle"
SKILLS_ROOT = Path("/home/ubuntu/skills").resolve()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_config(path: Path = CONFIG_DEFAULT) -> tuple[list[tuple[str, str]], list[str]]:
    specs: list[tuple[str, str]] = []
    excludes: list[str] = []
    for no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or parts[0] not in {"GLOB", "FILE", "DIR", "EXCLUDE"}:
            raise ValueError(f"invalid config line {no}: {raw}")
        if parts[0] == "EXCLUDE":
            excludes.append(parts[1].strip())
        else:
            specs.append((parts[0], str(Path(parts[1].strip()).expanduser())))
    if not specs:
        raise ValueError("governing-assets.txt contains no asset selection")
    return specs, excludes


def excluded(path: Path, patterns: Iterable[str]) -> bool:
    text = path.as_posix()
    rel = "/".join(path.parts)
    return any(fnmatch.fnmatch(text, p) or fnmatch.fnmatch(rel, p) for p in patterns)


def collect_paths(specs: list[tuple[str, str]], excludes: list[str]) -> list[Path]:
    found: set[Path] = set()
    for kind, argument in specs:
        target = Path(argument).resolve()
        if kind == "FILE":
            candidates = [target]
        elif kind == "DIR":
            candidates = list(target.rglob("*")) if target.is_dir() else []
        else:
            import glob
            candidates = [Path(p).resolve() for p in glob.glob(argument, recursive=True)]
        for candidate in candidates:
            if candidate.is_file() and not excluded(candidate, excludes):
                found.add(candidate)
    # Explicit FILE entries remain in the list when absent, so absence is hashed and visible.
    for kind, argument in specs:
        if kind == "FILE":
            target = Path(argument).resolve()
            if not excluded(target, excludes):
                found.add(target)
    return sorted(found, key=lambda p: p.as_posix())


def iso_mtime(st_mtime: float) -> str:
    return datetime.fromtimestamp(st_mtime, timezone.utc).isoformat()


def file_record(path: Path) -> dict:
    path = path.resolve()
    try:
        data = path.read_bytes()
        st = path.stat()
    except FileNotFoundError:
        return {
            "path": path.as_posix(), "lines": None, "sha256": None, "size": None,
            "mtime": None, "mtime_ns": None, "exists": False,
        }
    except OSError as exc:
        raise OSError(f"cannot read governing asset {path}: {exc}") from exc
    return {
        "path": path.as_posix(),
        "lines": len(data.splitlines()),
        "sha256": sha256_bytes(data),
        "size": len(data),
        "mtime": iso_mtime(st.st_mtime),
        "mtime_ns": st.st_mtime_ns,
        "exists": True,
    }


def leaf_digest(record: dict) -> bytes:
    if not record["exists"]:
        return hashlib.sha256(("MISSING\\0" + record["path"]).encode("utf-8")).digest()
    return bytes.fromhex(record["sha256"])


def merkle_root(records: list[dict]) -> str:
    nodes = [leaf_digest(r) for r in sorted(records, key=lambda r: r["path"])]
    if not nodes:
        return sha256_bytes(b"")
    while len(nodes) > 1:
        if len(nodes) % 2:
            nodes.append(nodes[-1])
        nodes = [hashlib.sha256(nodes[i] + nodes[i + 1]).digest() for i in range(0, len(nodes), 2)]
    return nodes[0].hex()


def build_snapshot(config: Path = CONFIG_DEFAULT) -> dict:
    specs, excludes = parse_config(config)
    records = [file_record(p) for p in collect_paths(specs, excludes)]
    return {
        "schema": "governing-assets-merkle/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": config.resolve().as_posix(),
        "selection": [f"{kind} {arg}" for kind, arg in specs],
        "excludes": excludes,
        "algorithm": {
            "leaf": "SHA-256(file bytes); missing expected files use SHA-256('MISSING\\0' + absolute path)",
            "order": "absolute path ascending",
            "parent": "SHA-256(left digest bytes || right digest bytes)",
            "odd_level": "duplicate the final node",
            "root": "final single node, hexadecimal lowercase",
        },
        "file_count": len(records),
        "root": merkle_root(records),
        "files": records,
    }


def write_snapshot(snapshot: dict, output: Path | None = None) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = EVIDENCE_DIR / f"{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def load_snapshot(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("files"), list) or not value.get("root"):
        raise ValueError(f"invalid snapshot: {path}")
    return value


def compare_snapshots(first: dict, second: dict) -> list[str]:
    differences: list[str] = []
    if first.get("root") != second.get("root"):
        differences.append(f"root: {first.get('root')} != {second.get('root')}")
    a = {x.get("path"): x for x in first.get("files", [])}
    b = {x.get("path"): x for x in second.get("files", [])}
    for path in sorted(set(a) | set(b)):
        if path not in a:
            differences.append(f"added: {path}")
        elif path not in b:
            differences.append(f"removed: {path}")
        else:
            for field in ("lines", "sha256", "size", "mtime", "exists"):
                if a[path].get(field) != b[path].get(field):
                    differences.append(f"{path}: {field}: {a[path].get(field)!r} != {b[path].get(field)!r}")
    return differences


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--snapshot", action="store_true", help="read configured assets and write one JSON snapshot")
    modes.add_argument("--compare", nargs=2, metavar=("A", "B"), help="compare two snapshot JSON files")
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.snapshot:
            snapshot = build_snapshot(args.config)
            output = write_snapshot(snapshot, args.output)
            print(f"snapshot: {output}")
            print(f"files: {snapshot['file_count']}")
            print(f"root: {snapshot['root']}")
            return 0
        first, second = load_snapshot(Path(args.compare[0])), load_snapshot(Path(args.compare[1]))
        differences = compare_snapshots(first, second)
        if differences:
            print("differences:")
            print("\n".join(f"- {item}" for item in differences))
            return 2
        print(f"identical: root {first['root']} · files {first.get('file_count', len(first['files']))}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
