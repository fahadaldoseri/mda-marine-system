#!/usr/bin/env python3
"""حارس تماثل شجرة المهارات: المجلد الحي ↔ المستودع ↔ مهارات المشروع في الدماغ ↔ فهرس المشروع.

السبب الجذري لإنشائه (2026-11-10): مهارة `bilingual-surface-parity-ops` أُنشئت حيًّا ولم تُنسخ
إلى المستودع ولا إلى `brain/skills` ولا إلى الفهرس — فمرّت بلا كشف لأن المدقق السابق كان يفحص
ثلاثة أسماء مكتوبة بيده (`SKILL_NAMES`) لا الشجرة كلها. القاعدة: القياس على الشجرة لا على قائمة منتقاة.

يفشل مغلقًا (رمز 2) إذا:
  1) مهارة في المجلد الحي وليست في المستودع، أو العكس — إلا استثناء معلن بسبب في `EXCEPTIONS`.
  2) مهارة في مهارات المشروع (`brain/skills`) وليست في الحي أو في المستودع.
  3) مهارة في جدول «المهارات المعتمدة في المشروع» وليست في `brain/skills`.
  4) انحراف بايت-ببايت في `SKILL.md` بين مهارات المشروع والمجلد الحي.

ويُنبّه (رمز 1) إذا كانت مهارة في `brain/skills` بلا سطر في جدول فهرس المشروع.

الاستعمال: python3 validators/check_skills_tree_parity.py [--quiet]
رمز الخروج: 0 سليم · 1 تحذير · 2 عائق.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
INDEX = B / "INDEX.md"
BRAIN_SKILLS = B / "skills"

# استثناءات معلنة بسبب — لا تُوسَّع بلا سبب مكتوب
EXCEPTIONS: dict[str, str] = {}

# صفوف في فهرس المشروع لمهارات مدموجة/متقاعدة: تُقبل بلا مجلد، بسبب معلن (لا يُحذف قرار)
RETIRED: dict[str, str] = {
    "measured-defect-closure-ops": "مدموجة في fault-closure-and-learning-ops (`D-0614`)",
    "fail-closed-guard-hardening-ops": "مدموجة في gate-lifecycle-ops (`D-0616`)",
    "gate-strictness-hardening-ops": "مدموجة في gate-lifecycle-ops (`D-0620`)",
    "live-visual-audit-ops": "مدموجة في report-surface-and-print-ops/references/legacy (`D-0625`)",
}


def _live_dir() -> Path:
    if os.environ.get("SKILLS_DIR"):
        return Path(os.environ["SKILLS_DIR"])
    if Path("/home/ubuntu/skills").is_dir():
        return Path("/home/ubuntu/skills")
    return B.parent / "skills"


def _repo_dir() -> Path:
    if os.environ.get("BACKUP_REPO_DIR"):
        return Path(os.environ["BACKUP_REPO_DIR"]) / "skills"
    return B.parent / "skills"


def _dirs(p: Path) -> set[str]:
    if not p.is_dir():
        return set()
    return {x.name for x in p.iterdir() if x.is_dir() and not x.name.startswith(".")}


def _index_skills() -> list[str]:
    if not INDEX.is_file():
        return []
    text = INDEX.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^\| `([a-z0-9\-]+)` \|", text, re.M)))


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس تماثل شجرة المهارات")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    live, repo, brain = _live_dir(), _repo_dir(), BRAIN_SKILLS
    blockers: list[str] = []
    warns: list[str] = []

    L, R, K = _dirs(live), _dirs(repo), _dirs(brain)
    print("=== تماثل شجرة المهارات ===")
    print(f"  الحي: {len(L)} · المستودع: {len(R)} · مهارات المشروع: {len(K)}")

    for name in sorted((L ^ R) - set(EXCEPTIONS)):
        side = "في المستودع وليست حيًّا" if name in R else "حيّة وليست في المستودع"
        blockers.append(f"{name}: {side} — انحراف تماثل")

    for name in sorted(K - (L & R)):
        where = "غير موجودة حيًّا" if name not in L else "غير موجودة في المستودع"
        blockers.append(f"{name}: مهارة مشروع {where}")

    rows = _index_skills()
    for name in rows:
        if name not in K and name not in RETIRED:
            blockers.append(f"{name}: مسجّلة في فهرس المشروع وليست في brain/skills")

    for name in sorted(K):
        if name not in rows:
            warns.append(f"{name}: في brain/skills بلا سطر في جدول فهرس المشروع")

    drift = []
    for name in sorted(K & L):
        f_live, f_brain = live / name / "SKILL.md", brain / name / "SKILL.md"
        if f_live.is_file() and f_brain.is_file() and f_live.read_bytes() != f_brain.read_bytes():
            drift.append(name)
    for name in drift:
        blockers.append(f"{name}: SKILL.md مختلف بين مشروع المشروع والمجلد الحي")

    print(f"  فهرس المشروع: {len(rows)} مهارة · brain/skills: {len(K)}")
    print(f"  النتيجة: {len(blockers)} عائق · {len(warns)} تحذير")
    if not a.quiet:
        for m in blockers:
            print(f"  ✘ {m}")
        for m in warns:
            print(f"  • {m}")
    if blockers:
        return 2
    return 1 if warns else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:
        def run(fn):
            raise SystemExit(fn())
    run(main)
