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
import re
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
    # ك-566: الحكم يتبع سياسة العقد لا قائمة مثبَّتة في الحارس. كل فئة معلَنة
    # ``informational`` (سجلات تشغيل · مخرجات مولَّدة · قياسات أدلة) لا تمنع النسخة،
    # وكل فئة ``strict`` تمنع. والفئات المعلَنة بعلامات كتل (generated_blocks)
    # تُقاس بالفرق لا بالبادئة، فلا تدخل قائمة البادئات.
    required = ("operational_logs", "generated")
    prefixes: list[str] = []
    exact: list[str] = []
    for wanted in required:
        item = next((value for value in categories if value.get("id") == wanted), None)
        if not isinstance(item, dict) or item.get("policy") != "informational":
            raise ContractError(f"عقد النطاق يجب أن يعلن {wanted} بسياسة informational")
    for item in categories:
        if not isinstance(item, dict):
            raise ContractError("بنية categories غير صالحة")
        if item.get("policy") != "informational" or item.get("markers"):
            continue
        item_prefixes = item.get("prefixes", [])
        item_exact = item.get("exact", [])
        if not isinstance(item_prefixes, list) or not all(isinstance(v, str) and v for v in item_prefixes):
            raise ContractError(f"{item.get('id')}.prefixes غير صالح")
        if not isinstance(item_exact, list) or not all(isinstance(v, str) and v for v in item_exact):
            raise ContractError(f"{item.get('id')}.exact غير صالح")
        prefixes.extend(item_prefixes)
        exact.extend(item_exact)
    return tuple(prefixes), tuple(exact)


def runtime_path(path: str, prefixes: tuple[str, ...], exact: tuple[str, ...]) -> bool:
    return path in exact or any(path.startswith(prefix) for prefix in prefixes)


def load_generated_blocks(path: Path) -> tuple[tuple[str, str], ...]:
    """كتل الملفات المولَّدة آليًا داخل ملفات حاكمة (ك-566).

    السبب المقيس: خطوة المانيفست ``tools/skill_lessons.py`` تكتب كتلة الدروس
    التراكمية داخل ``skills/**/SKILL.md``، فيظهر ملف المهارة في حالة Git كتعديل
    حاكم فيمنع النسخة الاحتياطية، مع أن المتغيّر مقطع مولَّد لا مصدر يدوي.
    القاعدة هنا: ملف يُعدّ سجلًا معلنًا إذا وقعت كل أسطره المتغيّرة داخل كتلة
    معلَنة بعلامات بداية ونهاية، وإلا بقي مانعًا (فشل مغلق).
    """
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"تعذّرت قراءة عقد النطاق {path}: {type(exc).__name__}: {exc}") from exc
    item = next((c for c in document.get("categories", []) if c.get("id") == "generated_blocks"), None)
    if item is None:
        return ()
    if item.get("policy") != "informational":
        raise ContractError("generated_blocks يجب أن تُعلن بسياسة informational")
    pairs: list[tuple[str, str]] = []
    for block in item.get("markers") or []:
        start, end = block.get("start"), block.get("end")
        if not (isinstance(start, str) and start and isinstance(end, str) and end):
            raise ContractError("generated_blocks.markers غير صالح")
        pairs.append((start, end))
    return tuple(pairs)


def _block_lines(text: str, pairs: tuple[tuple[str, str], ...]) -> set[int]:
    lines = text.splitlines()
    inside: set[int] = set()
    for start, end in pairs:
        open_at: int | None = None
        for index, line in enumerate(lines, 1):
            if open_at is None and start in line:
                open_at = index
            elif open_at is not None and end in line:
                inside.update(range(open_at, index + 1))
                open_at = None
    return inside


def only_generated_block_changes(repo: Path, rel: str, pairs: tuple[tuple[str, str], ...]) -> bool:
    """يقيس أن كل فرق الملف واقع داخل كتلة مولَّدة معلَنة."""
    if not pairs:
        return False
    path = repo / rel
    new_text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    new_blocks = _block_lines(new_text, pairs)
    try:
        old = subprocess.run(["git", "-C", str(repo), "show", f"HEAD:{rel}"],
                             capture_output=True, check=False)
        old_text = old.stdout.decode("utf-8", "replace") if old.returncode == 0 else ""
        diff = subprocess.run(["git", "-C", str(repo), "diff", "-U0", "--no-color", "--", rel],
                              capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ContractError(f"تعذّر قياس فرق {rel}: {type(exc).__name__}: {exc}") from exc
    old_blocks = _block_lines(old_text, pairs)
    old_changed: set[int] = set()
    new_changed: set[int] = set()
    for line in diff.stdout.decode("utf-8", "replace").splitlines():
        if not line.startswith("@@"):
            continue
        head = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if not head:
            raise ContractError(f"ترويسة فرق غير مفهومة في {rel}: {line}")
        old_start, old_len = int(head.group(1)), int(head.group(2) or 1)
        new_start, new_len = int(head.group(3)), int(head.group(4) or 1)
        old_changed.update(range(old_start, old_start + old_len))
        new_changed.update(range(new_start, new_start + new_len))
    if not old_changed and not new_changed:
        return False
    return old_changed <= old_blocks and new_changed <= new_blocks


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
        blocks = load_generated_blocks(scope)
        paths = changed_paths(repo)
    except ContractError as exc:
        print(f"✘ فشل مغلق — حارس شجرة النسخ: {exc}")
        return 2

    runtime = [path for path in paths if runtime_path(path, prefixes, exact)]
    generated: list[str] = []
    governing: list[str] = []
    for path in paths:
        if path in runtime:
            continue
        try:
            if only_generated_block_changes(repo, path, blocks):
                generated.append(path)
                continue
        except ContractError as exc:
            print(f"✘ فشل مغلق — حارس شجرة النسخ: {exc}")
            return 2
        governing.append(path)
    print(f"حارس شجرة النسخ: تغييرات Git={len(paths)} · سجلات تشغيل معلنة={len(runtime)}"
          f" · كتل مولَّدة={len(generated)} · تعديلات حاكمة={len(governing)}")
    for path in runtime:
        print(f"  ✔ سجل تشغيل معلن: {path} · sha256={digest(repo, path)}")
    for path in generated:
        print(f"  ✔ كتلة مولَّدة معلنة: {path} · sha256={digest(repo, path)}")
    for path in governing:
        print(f"  ✘ تعديل حاكم: {path} · sha256={digest(repo, path)}")
    if governing:
        print("✘ فشل مغلق: توجد تعديلات شيفرة/بيانات حقيقية خارج سجلات التشغيل المعلنة")
        return 2
    print("✔ شجرة النسخ تمر: سجلات التشغيل المحلية لا تمنع النسخة الاحتياطية")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
