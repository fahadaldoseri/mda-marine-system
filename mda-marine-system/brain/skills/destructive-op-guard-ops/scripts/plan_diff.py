#!/usr/bin/env python3
"""Measure a source/target synchronization plan without changing either tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, Tuple


Entry = Tuple[str, str]


def _fingerprint(path: Path) -> Entry:
    """Return a type and content digest without following symlinks."""
    if path.is_symlink():
        target = os.readlink(path)
        return ("symlink", hashlib.sha256(target.encode("utf-8", "surrogateescape")).hexdigest())
    if path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return ("file", digest.hexdigest())
    return ("other", "")


def _inventory(root: Path) -> Dict[str, Entry]:
    """Index files and symlinks as POSIX relative paths."""
    result: Dict[str, Entry] = {}
    for directory, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        # Do not descend through symlinked directories, but do compare the link itself.
        for name in list(dirnames):
            candidate = directory_path / name
            if candidate.is_symlink():
                relative = candidate.relative_to(root).as_posix()
                result[relative] = _fingerprint(candidate)
                dirnames.remove(name)
        for name in filenames:
            candidate = directory_path / name
            relative = candidate.relative_to(root).as_posix()
            result[relative] = _fingerprint(candidate)
    return result


def _normalise_prefix(value: str) -> str:
    if not value or value == ".":
        return ""
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError("--scope-prefix must be a relative path without '..'")
    return pure.as_posix().strip("/")


def _target_path(prefix: str, source_relative: str) -> str:
    return f"{prefix}/{source_relative}" if prefix else source_relative


def _under_prefix(relative: str, prefix: str) -> bool:
    return bool(prefix) and (relative == prefix or relative.startswith(prefix + "/"))


def _print_paths(label: str, paths: Iterable[str]) -> None:
    values = list(paths)
    print(f"{label}: {len(values)}")
    for value in values:
        print(f"  - {value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="قِس خطة مزامنة مصدر/هدف دون تعديل الملفات، وارفض الحذف الواسع أو خارج النطاق."
    )
    parser.add_argument("--source", required=True, type=Path, help="جذر المصدر")
    parser.add_argument("--target", required=True, type=Path, help="جذر الهدف")
    parser.add_argument(
        "--delete-cap",
        "--max-deletes",
        dest="delete_cap",
        type=int,
        default=20,
        help="السقف الأقصى لملفات الحذف داخل النطاق (الافتراضي 20)",
    )
    parser.add_argument(
        "--scope-prefix",
        default="",
        help="المجلد النسبي داخل الهدف الذي تديره الشجرة المصدرية؛ اتركه فارغًا إذا كان الهدف مرآة مباشرة",
    )
    parser.add_argument("--json", action="store_true", help="اطبع النتيجة كـ JSON بدل التقرير العربي")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.delete_cap < 0:
        print("خطأ: يجب أن يكون --delete-cap صفرًا أو أكبر.", file=sys.stderr)
        return 2
    try:
        prefix = _normalise_prefix(args.scope_prefix)
    except ValueError as exc:
        print(f"خطأ: {exc}", file=sys.stderr)
        return 2

    source = args.source.expanduser().resolve()
    target = args.target.expanduser().resolve()
    if not source.is_dir() or not target.is_dir():
        print("خطأ: يجب أن يكون المصدر والهدف مجلدين موجودين.", file=sys.stderr)
        return 2

    source_entries = _inventory(source)
    target_entries = _inventory(target)
    expected = {_target_path(prefix, relative): relative for relative in source_entries}

    new_files = sorted(relative for relative in expected if relative not in target_entries)
    updated = sorted(
        relative
        for relative in expected
        if relative in target_entries and source_entries[expected[relative]] != target_entries[relative]
    )
    deleted = sorted(relative for relative in target_entries if relative not in expected and _under_prefix(relative, prefix))
    outside_scope = sorted(relative for relative in target_entries if relative not in expected and not _under_prefix(relative, prefix))

    delete_over_cap = len(deleted) > args.delete_cap
    unsafe = delete_over_cap or bool(outside_scope)
    result = {
        "source": str(source),
        "target": str(target),
        "scope_prefix": prefix or ".",
        "new": new_files,
        "updated": updated,
        "deleted": deleted,
        "outside_scope": outside_scope,
        "delete_cap": args.delete_cap,
        "delete_over_cap": delete_over_cap,
        "safe": not unsafe,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("خطة الفرق (تجربة جافة؛ لم تُعدّل الملفات)")
        print(f"المصدر: {source}")
        print(f"الهدف: {target}")
        print(f"نطاق الهدف: {prefix or '.'}")
        _print_paths("جديد", new_files)
        _print_paths("محدّث", updated)
        _print_paths("محذوف ضمن النطاق", deleted)
        _print_paths("خارج نطاق المصدر", outside_scope)
        print(f"سقف الحذف: {args.delete_cap}")
        if delete_over_cap:
            print("السبب: تجاوز عدد الحذف سقف الحماية.")
        if outside_scope:
            print("السبب: توجد ملفات في الهدف خارج النطاق المعلن للمصدر.")
        if unsafe:
            print("القرار: غير آمن (خرج 2)")
            print("اقتراح الحاجز: أوقف التنفيذ، صحّح جذر الهدف أو --scope-prefix، وراجع الخطة قبل أي حذف.")
        else:
            print("القرار: آمن مبدئيًا (خرج 0؛ ما زالت المراجعة البشرية مطلوبة).")

    return 2 if unsafe else 0


if __name__ == "__main__":
    raise SystemExit(main())
