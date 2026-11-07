#!/usr/bin/env python3
"""فحص مكمّل لفاحص التماثل (طلب فهد 2026-10-24، البند 6):
يمنع وجود ملف شيفرة على الخادم غير متتبَّع في المستودع، إلا ما هو في قائمة معلَّلة.

العلّة: شيفرة تعمل على الخادم ولا أصل لها في المستودع = فقدان الشيفرة عند أي استرداد،
وانحراف صامت عن المستودع لا يكتشفه فحص المحتوى (لأنه يقارن الملفات المتتبَّعة فقط).

الاستخدام:
  python3 validators/check_server_code_tracking.py [--root <brain>] [--repo <مستودع>]
رموز الخروج: 0 نظيف · 70 ملف شيفرة غير متتبَّع (منع) · 2 خطأ.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from repo_root import RepoRootError, find_git_root

CODE_EXT = {".py", ".sh", ".js", ".mjs", ".ts", ".yaml", ".yml", ".sql", ".pl"}
SKIP_DIRS = {"logs", "__pycache__", ".venv", "node_modules", ".git", "shots",
             "archive", "dist", ".mypy_cache", ".pytest_cache", "_oneoff"}
ALLOWLIST = "appendices/untracked-code-allowlist.json"


def tracked_in_repo(repo: Path) -> set[str]:
    out = subprocess.run(["git", "-C", str(repo), "ls-files"],
                         capture_output=True, text=True).stdout.split()
    return {p[len("brain/"):] for p in out if p.startswith("brain/")}


def load_allowlist(root: Path) -> dict[str, str]:
    p = root / ALLOWLIST
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for item in data.get("allowed", []):
        out[item["path"]] = item.get("reason", "")
    return out


def default_repo_for(root: Path) -> Path:
    """يقيس جذر Git من المسار الممرر، ويرفض النسخة المضاعفة."""
    try:
        return find_git_root(root, reject_duplicate=True)
    except RepoRootError:
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--repo", default=None, help="مستودع GitHub المحلي (افتراضيًا Git الأب أو الشقيق القديم)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    repo = Path(args.repo).resolve() if args.repo else default_repo_for(root)
    if not (repo / ".git").exists():
        print(f"✘ لا مستودع في {repo} — تعذّر الفحص (رمز 2)")
        return 2

    tracked = tracked_in_repo(repo)
    allowed = load_allowlist(root)

    untracked: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix not in CODE_EXT:
                continue
            rel = str(p.relative_to(root))
            if rel in tracked or rel in allowed:
                continue
            untracked.append(rel)

    if untracked:
        print(f"✘ ملفات شيفرة على الخادم غير متتبَّعة في المستودع: {len(untracked)} — منع")
        for rel in sorted(untracked)[:25]:
            print(f"   · {rel}")
        print("   العلاج: انقل الملف إلى المستودع عبر فرع وطلب دمج، أو أدرجه في "
              f"{ALLOWLIST} بسبب مكتوب.")
        return 70
    print(f"✔ كل ملفات الشيفرة على الخادم متتبَّعة في المستودع (المستثنى المعلَّل: {len(allowed)})")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
