#!/usr/bin/env python3
"""مدقق سلامة مهارات المشروع عبر الأسطح الحاكمة.

النطاق الحاكم هو مجلد `brain/skills` داخل المشروع؛ وتقارن كل مهارة فيه
بنسخة الخادم ومرآة المستودع ونسخة الدماغ في المرآة. تُستبعد ملفات
`__pycache__/*.pyc` لأنها مشتقات تنفيذية لا أصول مصدرية.

الخروج: 0 سليم · 2 عائق.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
from pathlib import Path

# لا نعدّ السجل التاريخي لمسار مهارة أخرى (`other-skill/references/x.md`)
# إحالةً محلية؛ الإحالة التنفيذية تبدأ مباشرةً بـ`references/` داخل المهارة.
REFERENCE_RE = re.compile(r"(?<![A-Za-z0-9_./-])references/[A-Za-z0-9_.-]+\.md")


def source_files(root: Path) -> dict[str, Path]:
    """أعد ملفات المصدر فقط، دون مشتقات Python الثنائية."""
    if not root.is_dir():
        return {}
    result: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        result[path.relative_to(root).as_posix()] = path
    return result


def signature(path: Path) -> tuple[int, int, str]:
    data = path.read_bytes()
    lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    return lines, len(data), hashlib.sha256(data).hexdigest()[:16]


def parser() -> argparse.ArgumentParser:
    project = Path(__file__).resolve().parent.parent
    parent = project.parent
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("--brain", type=Path, default=project / "skills")
    ap.add_argument("--server", type=Path, default=Path(os.environ.get("SKILLS_DIR", "/home/ubuntu/skills")))
    ap.add_argument("--mirror", type=Path, default=parent / "mda-marine-system" / "skills")
    ap.add_argument("--mirror-brain", type=Path, default=parent / "mda-marine-system" / "brain" / "skills")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    surfaces = {
        "server": args.server.expanduser(),
        "brain": args.brain.expanduser(),
        "mirror": args.mirror.expanduser(),
        "mirror_brain": args.mirror_brain.expanduser(),
    }
    project_skills = sorted(
        path.parent.name for path in (surfaces["brain"]).glob("*/SKILL.md")
    )
    blockers: list[str] = []
    if not project_skills:
        blockers.append(f"نطاق المشروع فارغ أو مفقود: {surfaces['brain']}")

    checked_files = 0
    print("=== سلامة مهارات المشروع — مقارنة مصدرية عبر 4 أسطح ===")
    print("النطاق الحاكم: " + str(surfaces["brain"]))
    print("الأسطح: " + " · ".join(f"{name}={root}" for name, root in surfaces.items()))

    for skill in project_skills:
        canonical_root = surfaces["brain"] / skill
        canonical = source_files(canonical_root)
        checked_files += len(canonical)
        if "SKILL.md" not in canonical:
            blockers.append(f"{skill}: SKILL.md مفقود في نسخة الدماغ")
            continue
        skill_text = canonical["SKILL.md"].read_text(encoding="utf-8", errors="replace")
        if not skill_text.strip():
            blockers.append(f"{skill}: SKILL.md فارغ")
        if not skill_text.startswith("---"):
            blockers.append(f"{skill}: SKILL.md بلا frontmatter")
        else:
            frontmatter = skill_text.split("---", 2)[1]
            for marker in ("name:", "description:"):
                if marker not in frontmatter:
                    blockers.append(f"{skill}: frontmatter بلا {marker}")
        for ref in sorted(set(REFERENCE_RE.findall(skill_text))):
            if ref not in canonical:
                blockers.append(f"{skill}: مرجع مذكور ومفقود {ref}")

        for surface, root in surfaces.items():
            current_root = root / skill
            current = source_files(current_root)
            if not current_root.is_dir():
                blockers.append(f"{skill}: مجلد مفقود على سطح {surface}")
                continue
            missing = sorted(set(canonical) - set(current))
            extra = sorted(set(current) - set(canonical))
            changed = sorted(
                rel for rel in set(canonical) & set(current)
                if canonical[rel].read_bytes() != current[rel].read_bytes()
            )
            if missing:
                blockers.append(f"{skill}/{surface}: ملفات ناقصة {missing[:3]}")
            if extra:
                blockers.append(f"{skill}/{surface}: ملفات مصدرية زائدة {extra[:3]}")
            if changed:
                details = []
                for rel in changed[:3]:
                    details.append(f"{rel} {signature(canonical[rel])}!={signature(current[rel])}")
                blockers.append(f"{skill}/{surface}: محتوى منحرف؛ " + " · ".join(details))
        print(f"  {'✘' if any(skill in item for item in blockers) else '✔'} {skill} · ملفات المصدر={len(canonical)}")

    print(f"المهارات المشروعية المفحوصة: {len(project_skills)} · ملفات المصدر المفحوصة: {checked_files} · العوائق: {len(blockers)}")
    if blockers:
        for item in blockers:
            print("  ✘ " + item)
        return 2
    print("  ✔ كل مهارات المشروع مكتملة ومتطابقة عبر الأسطح الأربعة")
    return 0


if __name__ == "__main__":
    import sys as _sys, pathlib as _pl
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
