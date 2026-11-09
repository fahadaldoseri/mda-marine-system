#!/usr/bin/env python3
"""عقد قابل للاختبار لمهارة `pre-execution-plan-audit-ops` (قرار المالك 2026-11-10 · D-0645).

يُثبت بأدلة موجبة وسالبة، وبلا شبكة:
  1) البنية: SKILL.md + أداتان + مرجع + قالبان — في مجلد المهارات الحيّ وفي نسخة المستودع، متطابقتان بايت-ببايت.
  2) الترويسة: `name` و`description` معلنان، وحدّ عدم التداخل مع المهارات المجاورة مكتوب، وحلقة التعلّم الذاتي قائمة.
  3) أداة تدقيق التداخل: تمرّ على خطة سليمة (rc=0)، وتمنع خطة فيها بند في مرحلتين (rc=2)،
     وتمنع خطة فيها ملف في مرحلتين وبناء ونشر متكرر (rc=2).
  4) أداة التحقق من الادعاءات: تمرّ عند غياب العبارة (rc=0)، وتفشل عند وجودها والمتوقع صفر (rc=2)،
     وتمرّ عند وجودها والمتوقع وجود (rc=0).
الخروج: 0 سليم · 1 فشل.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SKILL = "pre-execution-plan-audit-ops"
LIVE = (Path(os.environ["SKILLS_DIR"]) if os.environ.get("SKILLS_DIR")
        else Path("/home/ubuntu/skills") if Path("/home/ubuntu/skills").is_dir()
        else B.parent / "skills") / SKILL
REPO = (Path(os.environ["BACKUP_REPO_DIR"]) / "skills" / SKILL
        if os.environ.get("BACKUP_REPO_DIR") else B.parent / "skills" / SKILL)
REQUIRED = [
    "SKILL.md",
    "scripts/audit_plan_duplication.py",
    "scripts/verify_claims.py",
    "references/measurement-discipline.md",
    "templates/decision-entry.json",
    "templates/assignment-table.md",
]
NEIGHBOURS = ("owner-notes-measured-triage", "gate-strictness-hardening-ops", "skill-adoption-governance-ops")

fails: list[str] = []


def check_structure() -> None:
    for base, label in ((LIVE, "المهارات الحيّ"), (REPO, "المستودع")):
        for rel in REQUIRED:
            if not (base / rel).is_file():
                fails.append(f"{label}: ملف مفقود {rel}")
    if LIVE.is_dir() and REPO.is_dir():
        for rel in REQUIRED:
            a, b = LIVE / rel, REPO / rel
            if a.is_file() and b.is_file() and a.read_bytes() != b.read_bytes():
                fails.append(f"تماثل: {rel} مختلف بين المجلد الحيّ والمستودع")


def check_frontmatter() -> None:
    f = LIVE / "SKILL.md"
    if not f.is_file():
        return
    text = f.read_text(encoding="utf-8")
    head = text.split("---")[1] if text.startswith("---") else ""
    for key in ("name:", "description:"):
        if key not in head:
            fails.append(f"الترويسة: {key} غير معلن")
    if f"name: {SKILL}" not in head:
        fails.append("الترويسة: الاسم لا يطابق مجلد المهارة")
    if "حلقة التعلّم الذاتي" not in text:
        fails.append("المحتوى: حلقة التعلّم الذاتي غير مكتوبة")
    if not any(n in text for n in NEIGHBOURS):
        fails.append("المحتوى: حدّ عدم التداخل مع المهارات المجاورة غير مكتوب")


def run(script: Path, args: list[str]) -> int:
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True, timeout=120).returncode


def check_audit_tool() -> None:
    tool = LIVE / "scripts/audit_plan_duplication.py"
    if not tool.is_file():
        return
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp) / "clean.md"
        clean.write_text(
            "## جدول الإسناد\n| المرحلة | البنود | الملفات |\n|---|---|---|\n"
            "| أ — الحوكمة | م-01 · م-02 | tools/a.py |\n"
            "| ب — الرئيسية | م-03 | tools/b.py |\n", encoding="utf-8")
        if run(tool, ["--plan", str(clean)]) != 0:
            fails.append("أداة التداخل: خطة سليمة لم تمرّ (المتوقع rc=0)")

        dup_item = Path(tmp) / "dup_item.md"
        dup_item.write_text(
            "## جدول الإسناد\n| المرحلة | البنود | الملفات |\n|---|---|---|\n"
            "| أ — الحوكمة | م-05 | tools/a.py |\n"
            "| ب — الرئيسية | م-05 | tools/b.py |\n", encoding="utf-8")
        if run(tool, ["--plan", str(dup_item)]) != 2:
            fails.append("أداة التداخل: بند في مرحلتين لم يُمنع (المتوقع rc=2)")

        dup_mix = Path(tmp) / "dup_mix.md"
        dup_mix.write_text(
            "## المرحلة أ — الأولى\nالبند م-07 يُعدّل generator/build_site.py · وفيه بناء الموقع.\n"
            "## المرحلة ب — الثانية\nالبند م-08 يُعدّل generator/build_site.py · وفيه نشر الموقع.\n",
            encoding="utf-8")
        if run(tool, ["--plan", str(dup_mix)]) != 2:
            fails.append("أداة التداخل: ملف مكرر وبناء متكرر لم يُمنعا (المتوقع rc=2)")


def check_claims_tool() -> None:
    tool = LIVE / "scripts/verify_claims.py"
    if not tool.is_file():
        return
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        out.mkdir()
        (out / "page.html").write_text("محتوى سليم بلا العبارة الممنوعة", encoding="utf-8")
        if run(tool, ["--target", str(out), "--claim", "نفّذوا", "--expect", "absent"]) != 0:
            fails.append("أداة الادعاءات: غياب العبارة لم يمرّ (المتوقع rc=0)")
        (out / "page.html").write_text("هنا كلمة نفّذوا موجودة", encoding="utf-8")
        if run(tool, ["--target", str(out), "--claim", "نفّذوا", "--expect", "absent"]) != 2:
            fails.append("أداة الادعاءات: وجود العبارة والمتوقع صفر لم يُمنع (المتوقع rc=2)")
        if run(tool, ["--target", str(out), "--claim", "نفّذوا", "--expect", "present"]) != 0:
            fails.append("أداة الادعاءات: وجود العبارة والمتوقع وجود لم يمرّ (المتوقع rc=0)")


def main() -> int:
    check_structure()
    check_frontmatter()
    check_audit_tool()
    check_claims_tool()
    if fails:
        print(f"  ✘ عقد مهارة {SKILL}: {len(fails)} فشل")
        for f in fails:
            print(f"     - {f}")
        return 1
    print(f"  ✔ عقد مهارة {SKILL}: بنية · تماثل · ترويسة · تداخل موجب وسالب · ادعاءات موجب وسالب")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())