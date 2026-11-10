#!/usr/bin/env python3
"""اجعل site/ مرجعًا وحيدًا لأصول الإنجليزية، وزامن نسخة التشغيل ذريًا ثم قارن SHA-256."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
from dataclasses import dataclass

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


@dataclass(frozen=True)
class Asset:
    label: str
    source: pathlib.Path
    target: pathlib.Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_assets(brain: pathlib.Path, site: pathlib.Path, date: str) -> tuple[list[Asset], int]:
    repo_root = brain.resolve().parent
    canonical = repo_root / "site" / "sources" / "i18n" / "en"
    operational = site.resolve() / "sources" / "i18n" / "en"
    assets = [
        Asset("glossary", canonical / "glossary.json", operational / "glossary.json"),
        Asset(
            "english-master",
            canonical / f"{date}-sectioned.en.md",
            operational / f"{date}-sectioned.en.md",
        ),
    ]

    for asset in assets:
        if not asset.source.is_file() or asset.source.stat().st_size == 0:
            print(f"✘ CANONICAL_ASSET_MISSING: {asset.source}")
            return [], 2
    try:
        glossary = json.loads(assets[0].source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"✘ CANONICAL_GLOSSARY_INVALID: {exc}")
        return [], 2
    entries = glossary.get("entries") if isinstance(glossary, dict) else None
    if not isinstance(entries, dict) or not entries:
        print(f"✘ CANONICAL_GLOSSARY_INVALID: entries must be a non-empty object: {assets[0].source}")
        return [], 2
    return assets, len(entries)


def check_assets(assets: list[Asset], *, entries: int) -> int:
    mismatch = False
    for asset in assets:
        try:
            source_bytes = asset.source.read_bytes()
            target_bytes = asset.target.read_bytes()
        except OSError as exc:
            print(f"✘ I18N_ASSET_READ_ERROR: {asset.label}: {exc}")
            mismatch = True
            continue
        source_hash, target_hash = digest(source_bytes), digest(target_bytes)
        if source_hash != target_hash:
            print(
                f"✘ I18N_ASSET_MISMATCH: {asset.label} "
                f"canonical={source_hash} runtime={target_hash}"
            )
            mismatch = True
        else:
            print(f"✔ I18N_ASSET_MATCH: {asset.label} sha256={source_hash} bytes={len(source_bytes)}")
    if mismatch:
        return 2
    print(f"✔ I18N_ASSET_PARITY=PASS glossary_entries={entries} assets={len(assets)}")
    return 0


def atomic_copy(source: pathlib.Path, target: pathlib.Path, *, source_mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise OSError(f"refusing symlink target: {target}")
    target_root = target.parents[3].resolve()
    target_resolved = target.resolve(strict=False)
    expected_target = target_root / "sources" / "i18n" / "en" / target.name
    if target_resolved != expected_target:
        raise OSError(f"target escaped or changed below site root: {target}")

    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else source_mode
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{target.name}.", dir=target.parent, delete=False) as handle:
            temp_name = handle.name
            with source.open("rb") as src:
                while chunk := src.read(1024 * 1024):
                    handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, target)
        temp_name = None
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sync", action="store_true", help="copy canonical assets into the runtime site")
    mode.add_argument("--check", action="store_true", help="fail closed on any byte-level difference")
    parser.add_argument("--brain", type=pathlib.Path, required=True)
    parser.add_argument("--site", type=pathlib.Path, required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    if not DATE_RE.fullmatch(args.date):
        print(f"✘ INVALID_DATE: expected YYYY-MM-DD, got {args.date!r}")
        return 2
    assets, entries = load_assets(args.brain, args.site, args.date)
    if not assets:
        return 2

    if args.check:
        return check_assets(assets, entries=entries)

    try:
        # مصادر كل الملفات تُقرأ وتُتحقق قبل أي كتابة؛ كل وجهة تُستبدل ذريًا.
        for asset in assets:
            source_mode = stat.S_IMODE(asset.source.stat().st_mode)
            atomic_copy(asset.source, asset.target, source_mode=source_mode)
    except OSError as exc:
        print(f"✘ I18N_ASSET_SYNC_FAILED: {exc}")
        return 2

    print("✔ I18N_ASSET_SYNC=COMPLETED direction=repository-site-to-runtime-site")
    return check_assets(assets, entries=entries)


if __name__ == "__main__":
    sys.exit(main())
