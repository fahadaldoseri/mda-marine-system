#!/usr/bin/env python3
"""حارس شجرة النسخ الاحتياطي: سجلات التشغيل لا تمنع، والشيفرة/البيانات تمنع.

يقرأ فئة ``operational_logs`` من runbook/parity-scope.json. كل تغيير خارج
الفئة المعلنة يُعامل كتغيير حاكم ويفشل مغلقًا قبل أي تطبيق أو دفع.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_BRAIN = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])


class ContractError(RuntimeError):
    pass


def load_runtime_scope(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"تعذّرت قراءة عقد النطاق {path}: {type(exc).__name__}: {exc}") from exc
    categories = document.get("categories") if isinstance(document, dict) else None
    if not isinstance(categories, list):
        raise ContractError("عقد النطاق بلا categories")
    # يُحترم كل فئة معلَنة بسياسة informational: سجلات التشغيل + المخرجات المولَّدة.
    # السبب: خطوات الجولة تُعيد كتابة مخرجاتها (فهرس التقارير · مكتبات المعجم ·
    # مصفوفة التتبع · موجز التحسين) بعد النسخة الاحتياطية، وهي مشتقة لا مصدر حاكم.
    honored = ("operational_logs", "generated")
    prefixes: list[str] = []
    exact: list[str] = []
    for wanted in honored:
        item = next((value for value in categories if value.get("id") == wanted), None)
        if not isinstance(item, dict) or item.get("policy") != "informational":
            raise ContractError(f"عقد النطاق يجب أن يعلن {wanted} بسياسة informational")
        item_prefixes = item.get("prefixes")
        item_exact = item.get("exact", [])
        if not isinstance(item_prefixes, list) or not all(isinstance(v, str) and v for v in item_prefixes):
            raise ContractError(f"{wanted}.prefixes غير صالح")
        if not isinstance(item_exact, list) or not all(isinstance(v, str) and v for v in item_exact):
            raise ContractError(f"{wanted}.exact غير صالح")
        prefixes.extend(item_prefixes)
        exact.extend(item_exact)
    return tuple(prefixes), tuple(exact)


def runtime_path(path: str, prefixes: tuple[str, ...], exact: tuple[str, ...]) -> bool:
    return path in exact or any(path.startswith(prefix) for prefix in prefixes)


def changed_paths(repo: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ContractError(f"تعذّرت قراءة حالة Git في {repo}: {type(exc).__name__}: {exc}") from exc
    paths: list[str] = []
    records = result.stdout.decode("utf-8", "replace").split("\0")
    for record in records:
        if not record:
            continue
        if len(record) < 4:
            raise ContractError(f"سجل Git غير صالح: {record!r}")
        path = record[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return sorted(set(paths))


def digest(repo: Path, rel: str) -> str:
    path = repo / rel
    if not path.is_file():
        return "deleted"
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("BACKUP_REPO_DIR", ""))
    parser.add_argument("--brain", default=str(DEFAULT_BRAIN))
    parser.add_argument("--scope", default="")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else DEFAULT_BRAIN.parent.resolve()
    brain = Path(args.brain).resolve()
    scope = Path(args.scope).resolve() if args.scope else brain / "runbook" / "parity-scope.json"
    try:
        prefixes, exact = load_runtime_scope(scope)
        paths = changed_paths(repo)
    except ContractError as exc:
        print(f"✘ فشل مغلق — حارس شجرة النسخ: {exc}")
        return 2

    runtime = [path for path in paths if runtime_path(path, prefixes, exact)]
    governing = [path for path in paths if path not in runtime]
    print(f"حارس شجرة النسخ: تغييرات Git={len(paths)} · سجلات تشغيل معلنة={len(runtime)} · تعديلات حاكمة={len(governing)}")
    for path in runtime:
        print(f"  ✔ سجل تشغيل معلن: {path} · sha256={digest(repo, path)}")
    for path in governing:
        print(f"  ✘ تعديل حاكم: {path} · sha256={digest(repo, path)}")
    if governing:
        print("✘ فشل مغلق: توجد تعديلات شيفرة/بيانات حقيقية خارج سجلات التشغيل المعلنة")
        return 2
    print("✔ شجرة النسخ تمر: سجلات التشغيل المحلية لا تمنع النسخة الاحتياطية")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
