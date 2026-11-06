#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص تماثل ملفات المهارات المعتمدة بين المصدر ومرآة brain.

رموز الخروج: 0 تماثل كامل · 2 اختلاف أو ملف مفقود أو تعذّر القياس.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__"}
SKIP_SUFFIXES = {".pyc"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(skill_root: Path, skill: str) -> dict[str, str]:
    base = skill_root / skill
    if not base.is_dir():
        return {}
    result: dict[str, str] = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.is_symlink() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        result[path.relative_to(base).as_posix()] = sha256(path)
    return result


def approved_names(root: Path, skills_arg: str, skills_file: Path | None) -> list[str]:
    if skills_arg.strip():
        return sorted({name.strip() for name in skills_arg.split(",") if name.strip()})
    if skills_file and skills_file.is_file():
        data = json.loads(skills_file.read_text(encoding="utf-8"))
        values = data.get("skills", []) if isinstance(data, dict) else data
        if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError("ملف المهارات المعتمدة يجب أن يكون قائمة أسماء أو كائنًا بحقل skills")
        return sorted(set(value.strip() for value in values))
    mirror = root / "skills"
    return sorted(path.name for path in mirror.iterdir() if path.is_dir() and path.name not in SKIP_DIRS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="قارن بصمات ملفات المهارات المعتمدة بين المصدر والمرآة")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help="جذر brain")
    parser.add_argument("--source-root", default="", help="جذر المصدر، افتراضيًا SKILLS_DIR أو /home/ubuntu/skills")
    parser.add_argument("--mirror-root", default="", help="جذر المرآة، افتراضيًا <root>/skills")
    parser.add_argument("--skills", default="", help="أسماء المهارات مفصولة بفواصل؛ يتغلب على ملف القائمة")
    parser.add_argument("--skills-file", default="", help="JSON يحوي قائمة المهارات المعتمدة")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    source = Path(args.source_root).expanduser().resolve() if args.source_root else None
    if source is None:
        configured = os.environ.get("SKILLS_DIR")
        source = Path(configured).expanduser().resolve() if configured else Path("/home/ubuntu/skills")
        if not source.is_dir():
            source = (root.parent / "skills").resolve()
    mirror = Path(args.mirror_root).expanduser().resolve() if args.mirror_root else (root / "skills").resolve()
    skills_file = Path(args.skills_file).expanduser().resolve() if args.skills_file else (root / "runbook" / "approved-skills.json").resolve()

    if not source.is_dir() or not mirror.is_dir():
        print(f"✘ فشل مغلق — جذر المهارات غير قابل للقياس: المصدر={source} · المرآة={mirror}")
        return 2
    try:
        names = approved_names(root, args.skills, skills_file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"✘ فشل مغلق — تعذّر قراءة قائمة المهارات المعتمدة: {type(exc).__name__}: {exc}")
        return 2
    if not names:
        print("✘ فشل مغلق — قائمة المهارات المعتمدة فارغة")
        return 2

    differences: list[str] = []
    total_files = 0
    missing_files = 0
    extra_files = 0
    for skill in names:
        src = inventory(source, skill)
        dst = inventory(mirror, skill)
        if not (source / skill).is_dir():
            differences.append(f"{skill}/ (مفقود في المصدر)")
            missing_files += 1
            continue
        if not (mirror / skill).is_dir():
            differences.append(f"{skill}/ (مفقود في المرآة)")
            missing_files += 1
            total_files += len(src)
            continue
        for rel in sorted(set(src) | set(dst)):
            total_files += 1
            if rel not in dst:
                missing_files += 1
                differences.append(f"{skill}/{rel} (مفقود في المرآة)")
            elif rel not in src:
                extra_files += 1
                differences.append(f"{skill}/{rel} (زائد في المرآة)")
            elif src[rel] != dst[rel]:
                differences.append(f"{skill}/{rel} (بصمة مختلفة: {src[rel][:12]}… != {dst[rel][:12]}…)")

    print(f"المهارات: {len(names)} · الملفات: {total_files} · المختلف: {len(differences)} · المفقود: {missing_files} · الزائد: {extra_files}")
    if differences:
        print("✘ فشل مغلق — اختلاف بصمة المهارات:")
        for item in differences:
            print(f"  - {item}")
        return 2
    print("✔ تماثل المهارات: كل الملفات المعتمدة متطابقة SHA-256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
