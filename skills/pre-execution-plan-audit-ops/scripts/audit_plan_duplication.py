#!/usr/bin/env python3
"""تدقيق تداخل خطة تنفيذ متعددة المراحل.

يكشف ثلاث علل تسبّب عملًا مكررًا:
  1) رمز بند (م-01 · خ-07 · D-0644) يظهر في أكثر من مرحلة.
  2) مسار ملف يظهر في أكثر من مرحلة (ملف يُعدَّل مرتين).
  3) البناء أو النشر مذكور في أكثر من مرحلة.

يقرأ الخطة من مصدرين:
  · **جدول الإسناد** إن وُجد: كل صف = مرحلة، وخلاياه تحمل البنود والملفات (هذا هو المرجع الحاكم للربط).
  · **أقسام المراحل** (`### المرحلة ب — …`): البنود والملفات وأفعال البناء/النشر.
والأقسام المرجعية (المخاطر · ما لا يُلمس · البنود المغلقة · معايير القبول) مستثناة لأنها تذكر البنود بحكم وظيفتها.

الاستعمال:
  python3 audit_plan_duplication.py --plan plan.md [--json-out out.json]

رمز الخروج: 0 = لا تداخل · 2 = تداخل مانع.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

TATWEEL = "\u0640"
PHASE_RE = re.compile(r"^#{1,4}\s*(?:[^\n]*?)المرحلة\s*[\(\s]*([أ-ي])")
ASSIGN_RE = re.compile(r"^#{1,4}\s*[^\n]*(جدول الإسناد|إسناد البنود)")
NON_PHASE_RE = re.compile(r"^#{1,4}\s*[^\n]*(بنود مغلقة|بنود أُغلقت|ما لا يُلمس|المخاطر|معايير القبول|الحدود|ملحق)")
ITEM_RE = re.compile(r"(?:^|[\s\(\[·،,])([مخدD]\s?[-‑]?\s?\d{1,3})(?=[\s\)\]·،,.،:]|$)")
FILE_RE = re.compile(r"[\w\-./]+\.(?:py|sh|json|md|html|css|js|ts|yaml|yml|toml|txt)")
ROW_PHASE_RE = re.compile(r"^\s*(?:\*\*)?\s*([أ-ي])\s*—")
BUILD_WORDS = ("بناء واحد", "بناء الموقع", "بناء كامل", "نشر الموقع", "نشر واحد", "النشر على", "نُشر على")
BUILD_EXCLUDE = ("منع النشر", "لا نشر", "حارس", "حراس", "خارج المحرّك")


def norm_phase(letter: str) -> str:
    return f"المرحلة {'هـ' if letter == 'ه' else letter}"


def norm_item(raw: str) -> str:
    it = re.sub(r"[\s\-‑]", "-", raw.strip())
    return it.replace("م-", "م-").replace("خ-", "خ-").upper().replace("D-", "D-")


def add(phase: dict, items: list[str], files: list[str]) -> None:
    for it in items:
        if it not in phase["items"]:
            phase["items"].append(it)
    for f in files:
        if f not in phase["files"]:
            phase["files"].append(f)


def load_phases(path: pathlib.Path) -> list[dict]:
    phases: list[dict] = []
    current: dict | None = None
    mode = "prose"

    def flush() -> None:
        if current and (current["items"] or current["files"] or current["build"]):
            phases.append(current)

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().replace(TATWEEL, "")
        if line.startswith("#"):
            if ASSIGN_RE.match(line):
                flush()
                mode, current = "table", None
                continue
            if NON_PHASE_RE.match(line):
                flush()
                mode, current = "skip", None
                continue
            m = PHASE_RE.match(line)
            if m:
                flush()
                mode = "prose"
                current = {"name": norm_phase(m.group(1)), "items": [], "files": [], "build": []}
                continue
            flush()
            mode, current = "prose", None
            continue

        if mode == "skip":
            continue
        if mode == "table":
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2 or set(cells[0]) <= set("-: "):
                continue
            m = ROW_PHASE_RE.match(cells[0])
            if not m:
                continue
            row_phase = {"name": norm_phase(m.group(1)), "items": [], "files": [], "build": []}
            add(row_phase, ITEM_RE.findall(" | ".join(cells[1:])), FILE_RE.findall(" | ".join(cells[1:])))
            if row_phase["items"] or row_phase["files"]:
                phases.append(row_phase)
            continue
        if current is None:
            continue
        add(current, ITEM_RE.findall(line), FILE_RE.findall(line))
        if not any(x in line for x in BUILD_EXCLUDE):
            for w in BUILD_WORDS:
                if w in line and w not in current["build"]:
                    current["build"].append(w)

    flush()
    # دمج صفوف الجدول مع أقسام المراحل بالاسم نفسه
    merged: dict[str, dict] = {}
    for p in phases:
        tgt = merged.setdefault(p["name"], {"name": p["name"], "items": [], "files": [], "build": []})
        add(tgt, p["items"], p["files"])
        for w in p["build"]:
            if w not in tgt["build"]:
                tgt["build"].append(w)
    return list(merged.values())


def audit(phases: list[dict]) -> dict:
    item_phases: dict[str, list[str]] = {}
    file_phases: dict[str, list[str]] = {}
    for p in phases:
        for it in p["items"]:
            item_phases.setdefault(it, []).append(p["name"])
        for f in p["files"]:
            file_phases.setdefault(f, []).append(p["name"])
    dup_items = {k: sorted(set(v)) for k, v in item_phases.items() if len(set(v)) > 1}
    dup_files = {k: sorted(set(v)) for k, v in file_phases.items() if len(set(v)) > 1}
    build_phases = [p["name"] for p in phases if p["build"]]
    return {
        "phases": [{"name": p["name"], "items": len(p["items"]), "files": len(p["files"])} for p in phases],
        "duplicate_items": dup_items,
        "duplicate_files": dup_files,
        "build_phases": build_phases,
        "duplicate_build": len(build_phases) > 1,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="تدقيق تداخل الخطة قبل التنفيذ")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--json-out")
    a = ap.parse_args()

    path = pathlib.Path(a.plan)
    if not path.exists():
        print(f"✘ الخطة غير موجودة: {path}", file=sys.stderr)
        return 2

    res = audit(load_phases(path))
    print(f"خطة: {path.name} · المراحل المكتشفة: {len(res['phases'])}")
    for p in res["phases"]:
        print(f"   · {p['name']}: بنود={p['items']} · ملفات={p['files']}")

    problems = 0
    if res["duplicate_items"]:
        problems += len(res["duplicate_items"])
        print("\n✘ بنود في أكثر من مرحلة:")
        for k, v in sorted(res["duplicate_items"].items()):
            print(f"   {k}: {' ← '.join(v)}")
    if res["duplicate_files"]:
        problems += len(res["duplicate_files"])
        print("\n✘ ملفات في أكثر من مرحلة:")
        for k, v in sorted(res["duplicate_files"].items()):
            print(f"   {k}: {' ← '.join(v)}")
    if res["duplicate_build"]:
        problems += 1
        print("\n✘ البناء أو النشر مذكور في أكثر من مرحلة:")
        for n in res["build_phases"]:
            print(f"   {n}")

    if a.json_out:
        pathlib.Path(a.json_out).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    if problems:
        print(f"\nالنتيجة: تداخل مانع ({problems}) — انقل البند أو الملف إلى مرحلة واحدة قبل الانطلاق.")
        return 2
    print("\nالنتيجة: لا تداخل — كل بند وملف في مرحلة واحدة، والبناء والنشر مرة واحدة.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())