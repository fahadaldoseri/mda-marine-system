#!/usr/bin/env python3
"""عقد قابل للاختبار لمهارة `owner-notes-measured-triage` (قرار المالك 2026-11-10 · D-0623).

يُثبت بأدلة موجبة وسالبة، وبلا شبكة:
  1) بنية المهارة: SKILL.md + أداتان + مرجعان + قالبان — في مجلد المهارات وفي نسخة المستودع، متطابقة بايت-ببايت.
  2) الترويسة: `name` و`description` معلنان، وحدّ عدم التداخل مع المهارة المجاورة مكتوب.
  3) أداة الروابط: تمرّ على مخرج سليم (rc=0)، وتفشل مغلقًا على معرّف مكسور (rc=2)،
     وتفشل على رابط فارغ في النمط الصارم (rc=2).
  4) أداة مسح العبارات: تمرّ عند غياب الممنوع (rc=0)، وتفشل عند وجوده (rc=2)، وتفشل عند غياب الإلزامي (rc=2).

الخروج: 0 سليم · 1 فشل.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SKILL = "owner-notes-measured-triage"
LIVE = (Path(os.environ["SKILLS_DIR"]) if os.environ.get("SKILLS_DIR")
        else Path("/home/ubuntu/skills") if (os.access("/home/ubuntu/skills", os.R_OK | os.X_OK) and Path("/home/ubuntu/skills").is_dir())
        else B.parent / "skills") / SKILL
REPO = (Path(os.environ["BACKUP_REPO_DIR"]) / "skills" / SKILL
        if os.environ.get("BACKUP_REPO_DIR") else B.parent / "skills" / SKILL)

REQUIRED = [
    "SKILL.md",
    "scripts/audit_links.py",
    "scripts/probe_terms.py",
    "references/measurement-recipes.md",
    "references/intake-and-gates.md",
    "templates/item-ledger.md",
    "templates/before-after.html",
]

fails: list[str] = []


def run(cmd: list[str]) -> int:
    return subprocess.run(cmd, capture_output=True, text=True).returncode


def check(condition: bool, ok_msg: str, fail_msg: str) -> None:
    print(f"  {'✔' if condition else '✘'} {ok_msg if condition else fail_msg}")
    if not condition:
        fails.append(fail_msg)


# 1) البنية والتطابق مع نسخة المستودع
for rel in REQUIRED:
    check((LIVE / rel).is_file(), f"موجود في مجلد المهارات: {rel}", f"مفقود في مجلد المهارات: {rel}")
    check((REPO / rel).is_file(), f"موجود في نسخة المستودع: {rel}", f"مفقود في نسخة المستودع: {rel}")
same = all((LIVE / rel).read_bytes() == (REPO / rel).read_bytes() for rel in REQUIRED if (LIVE / rel).is_file() and (REPO / rel).is_file())
check(same, "نسخة المستودع مطابقة بايت-ببايت", "نسخة المستودع تخالف مجلد المهارات (تماثل مكسور)")

# 2) الترويسة وحدّ عدم التداخل
head = (LIVE / "SKILL.md").read_text(encoding="utf-8")
front = head.split("---")[1] if head.startswith("---") else ""
check("name:" in front and "description:" in front, "الترويسة تحمل name وdescription", "الترويسة ناقصة")
check("owner-ui-notes-contract-ops" in head, "حدّ عدم التداخل مكتوب مع المهارة المجاورة",
      "لا حدّ عدم تداخل مع المهارة المجاورة")

audit = str(LIVE / "scripts" / "audit_links.py")
probe = str(LIVE / "scripts" / "probe_terms.py")

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    # مخرج سليم: رابط داخلي ومعرّفه موجود، ورابط نسبي لملف موجود
    (root / "ok.html").write_text(
        '<html><body><a href="#sec">x</a><h2 id="sec">قسم</h2>'
        '<a href="/other.html">ص</a><a href="https://example.org">خ</a></body></html>',
        encoding="utf-8")
    (root / "other.html").write_text("<html><body>ص</body></html>", encoding="utf-8")
    check(run([sys.executable, audit, "--root", str(root)]) == 0,
          "أداة الروابط: مخرج سليم يمرّ (rc=0)", "أداة الروابط: مخرج سليم لم يمرّ")

    # معرّف مكسور + هدف نسبي مفقود ⇒ فشل مغلق
    (root / "dead.html").write_text('<html><body><a href="#ghost">x</a><a href="/nope.html">y</a></body></html>',
                                    encoding="utf-8")
    check(run([sys.executable, audit, "--root", str(root)]) == 2,
          "أداة الروابط: معرّف مكسور وهدف مفقود يُمنعان (rc=2)", "أداة الروابط لم تمنع الخلل")
    (root / "dead.html").unlink()

    # رابط فارغ في النمط الصارم ⇒ فشل مغلق، وفي العادي يمرّ
    (root / "empty.html").write_text('<html><body><a href="#">x</a></body></html>', encoding="utf-8")
    check(run([sys.executable, audit, "--root", str(root)]) == 0,
          "أداة الروابط: النمط العادي يتجاوز الرابط الفارغ (rc=0)", "النمط العادي منع الرابط الفارغ خطأً")
    check(run([sys.executable, audit, "--root", str(root), "--strict"]) == 2,
          "أداة الروابط: النمط الصارم يمنع الرابط الفارغ (rc=2)", "النمط الصارم لم يمنع الرابط الفارغ")
    (root / "empty.html").unlink()

    # مسح العبارات: موجب وسالب
    (root / "term.html").write_text("<html><body>نفّذوا: ارفعوا التأهب</body></html>", encoding="utf-8")
    check(run([sys.executable, probe, "--root", str(root), "--forbid", "نفّذوا"]) == 2,
          "مسح العبارات: الممنوع الموجود يُمنع (rc=2)", "مسح العبارات لم يمنع عبارة موجودة")
    check(run([sys.executable, probe, "--root", str(root), "--forbid", "لا تُنفذوا"]) == 0,
          "مسح العبارات: غياب الممنوع يمرّ (rc=0)", "مسح العبارات منع عبارة غير موجودة")
    check(run([sys.executable, probe, "--root", str(root), "--require", "أهم الأخبار"]) == 2,
          "مسح العبارات: الإلزامي الغائب يُمنع (rc=2)", "مسح العبارات لم يمنع غياب الإلزامي")

print()
if fails:
    print("  ✘ فشل العقد:")
    for f in fails:
        print("    ·", f)
    sys.exit(1)
print("  ✔ عقد مهارة فرز ملاحظات المالك بالقياس سليم (بنية · تماثل · أداتان موجب وسالب)")
sys.exit(0)