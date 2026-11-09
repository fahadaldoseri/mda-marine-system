#!/usr/bin/env python3
"""عقد قابل للاختبار لمهارة `owner-approval-launch-gate-ops` (قرار المالك 2026-11-10 · D-0647).

يُثبت بأدلة موجبة وسالبة، وبلا شبكة:
  1) البنية: SKILL.md + أداتان + مرجع + قالب — في مجلد المهارات وفي نسخة المستودع.
  2) التماثل: كل ملف مطابق بايت-ببايت بين الحيّة والمستودع.
  3) الترويسة: `name` و`description` معلنان، والحدّ الفاصل مع المهارات المجاورة مكتوب.
  4) أداة الجاهزية: تمرّ على خطة مكتملة (rc=0)، وتفشل مغلقًا على بند بلا مرحلة (rc=2)،
     وتفشل على خطة غير موجودة (rc=64) — ولا تُشغّل شبكة.
  5) أداة تسجيل العائق: تكتب سجلًا صالحًا (rc=0)، وتفشل عند نقص وسم مطلوب (rc≠0).

الخروج: 0 سليم · 1 فشل.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SKILL = "owner-approval-launch-gate-ops"
LIVE = (Path(os.environ["SKILLS_DIR"]) if os.environ.get("SKILLS_DIR")
        else Path("/home/ubuntu/skills") if Path("/home/ubuntu/skills").is_dir()
        else B.parent / "skills") / SKILL
REPO = (Path(os.environ["BACKUP_REPO_DIR"]) / "skills" / SKILL
        if os.environ.get("BACKUP_REPO_DIR") else B.parent / "skills" / SKILL)
REQUIRED = [
    "SKILL.md",
    "scripts/check_launch_readiness.py",
    "scripts/record_obstacle.py",
    "references/launch-protocol.md",
    "templates/readiness-report.md",
]
failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'✔' if cond else '✘'} {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def structure() -> None:
    for base, label in ((LIVE, "الحية"), (REPO, "المستودع")):
        check(f"بنية {label}: المجلد موجود", base.is_dir(), str(base))
        for rel in REQUIRED:
            check(f"بنية {label}: {rel}", (base / rel).is_file(), str(base / rel))
    for rel in REQUIRED:
        a, b = LIVE / rel, REPO / rel
        if a.is_file() and b.is_file():
            check(f"تماثل بايت-ببايت: {rel}", a.read_bytes() == b.read_bytes())


def header() -> None:
    if not (LIVE / "SKILL.md").is_file():
        return
    text = (LIVE / "SKILL.md").read_text(encoding="utf-8")
    check("الترويسة: name معلن", bool(re.search(r"^name:\s*\S+", text, re.M)))
    check("الترويسة: description معلن", bool(re.search(r"^description:\s*\S+", text, re.M)))
    check("حدّ عدم التداخل مكتوب", "عدم التداخل" in text or "المهارة المجاورة" in text)


def no_network() -> None:
    for rel in ("scripts/check_launch_readiness.py", "scripts/record_obstacle.py"):
        p = LIVE / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        check(f"بلا شبكة: {rel}", not re.search(r"urllib|requests|socket|http[s]?://", text))


PLAN_OK = """# خطة اختبار

## المرحلة (أ)
| البند | الحالة |
| --- | --- |
| م-01 | منفَّذ |
| م-02 | منفَّذ |
| م-03 | منفَّذ |

## ما ينتظر الانطلاق
لا شيء.
"""

PLAN_BAD = """# خطة اختبار

## المرحلة (أ)
| البند | الحالة |
| --- | --- |
| م-01 | منفَّذ |
"""

INVENTORY = """| المعرّف | الوصف |
| --- | --- |
| م-01 | بند أول |
| م-02 | بند ثانٍ |
| م-03 | بند ثالث |
"""


def readiness_tool() -> None:
    tool = LIVE / "scripts" / "check_launch_readiness.py"
    if not tool.is_file():
        return
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "plan_ok.md").write_text(PLAN_OK, encoding="utf-8")
        (d / "plan_bad.md").write_text(PLAN_BAD, encoding="utf-8")
        (d / "inv.md").write_text(INVENTORY, encoding="utf-8")
        (d / "registry.json").write_text(json.dumps(
            {"decisions": [{"id": "D-9999", "status": "منفَّذ", "title_ar": "اعتماد ملاحظات المالك بالقياس"}]},
            ensure_ascii=False), encoding="utf-8")
        neighbor = d / "no_tools"  # لا أداة للجارة ⇒ «غير مُقاس» بلا مانع كاذب
        neighbor.mkdir()
        base = [sys.executable, str(tool), "--inventory", str(d / "inv.md"),
                "--registry", str(d / "registry.json"), "--neighbor-scripts", str(neighbor)]
        r = subprocess.run(base + ["--plan", str(d / "plan_ok.md")],
                           capture_output=True, text=True, timeout=300)
        check("أداة الجاهزية: خطة مكتملة ⇒ rc=0", r.returncode == 0,
              (r.stdout or r.stderr).strip()[-200:])
        check("أداة الجاهزية: الخطة المكتملة تُطبع صريحة",
              "يمكن الانطلاق" in r.stdout, r.stdout[-160:])
        r2 = subprocess.run(base + ["--plan", str(d / "plan_bad.md")],
                            capture_output=True, text=True, timeout=300)
        check("أداة الجاهزية: بند بلا مرحلة ⇒ rc=2", r2.returncode == 2, r2.stdout[-160:])
        check("أداة الجاهزية: المانع مُسمّى", "بلا مرحلة" in r2.stdout, r2.stdout[-160:])
        r3 = subprocess.run(base + ["--plan", str(d / "missing.md")],
                            capture_output=True, text=True, timeout=300)
        check("أداة الجاهزية: خطة غير موجودة ⇒ rc=64", r3.returncode == 64, r3.stdout[-160:])
        r4 = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True, timeout=120)
        check("أداة الجاهزية: بلا --plan ⇒ خطأ استعمال", r4.returncode != 0)


def obstacle_tool() -> None:
    tool = LIVE / "scripts" / "record_obstacle.py"
    if not tool.is_file():
        return
    with tempfile.TemporaryDirectory() as td:
        log = Path(td) / "obstacles.jsonl"
        r = subprocess.run([sys.executable, str(tool), "--phase", "أ",
                            "--obstacle", "عائق اختبار", "--cause", "سبب",
                            "--action", "إصلاح", "--evidence", "دليل", "--log", str(log)],
                           capture_output=True, text=True, timeout=120)
        check("أداة العائق: تسجيل صالح ⇒ rc=0", r.returncode == 0, (r.stdout or r.stderr)[-160:])
        ok = log.is_file() and len(log.read_text(encoding="utf-8").strip().splitlines()) == 1
        check("أداة العائق: السجل مكتوب مرة واحدة", ok)
        if ok:
            row = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[0])
            check("أداة العائق: حقول السجل كاملة",
                  all(k in row for k in ("phase", "obstacle", "cause", "action", "evidence")))
        r2 = subprocess.run([sys.executable, str(tool), "--phase", "أ", "--obstacle", "بلا سبب"],
                            capture_output=True, text=True, timeout=120)
        check("أداة العائق: نقص وسم مطلوب ⇒ فشل", r2.returncode != 0)


def main() -> int:
    print(f"عقد مهارة {SKILL}")
    structure()
    header()
    no_network()
    readiness_tool()
    obstacle_tool()
    print(f"----- الحصيلة: {'نجح' if not failures else 'فشل'} · إخفاقات {len(failures)} -----")
    for f in failures:
        print(f"  ✘ {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())