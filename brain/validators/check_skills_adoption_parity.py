#!/usr/bin/env python3
"""حارس اعتماد المهارات: كل مهارة في جدول فهرس المشروع لها قرار اعتماد مُنفَّذ يذكر اسمها في دفتر القرارات.

السبب الجذري لإنشائه (2026-11-10): جدول «المهارات المعتمدة في المشروع» كان يسرد اثنتي عشرة مهارة
بحالة «معتمدة»، بينما دفتر القرارات يحمل خمسة قرارات اعتماد فقط — فسقط سبعة اعتمادات بلا صف قرار،
وهو ما يجعل «معتمدة» ادّعاءً غير قابل للتتبع.

يفشل مغلقًا (رمز 2) إذا:
  1) مهارة في الجدول بلا قرار يذكر اسمها (في العنوان أو الصياغة أو ملاحظة دليل).
  2) قرار اعتماد مهارة غير بحالة «منفَّذ».
  3) قرار اعتماد يذكر مهارة ليست في الجدول ولا في الاستثناءات المعلنة.
  4) دفتر القرارات أو الفهرس غير قابل للقراءة.

الاستعمال: python3 validators/check_skills_adoption_parity.py [--quiet]
رمز الخروج: 0 سليم · 2 عائق.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
INDEX = B / "INDEX.md"
REGISTRY = B / "decisions" / "registry.json"
ADOPT_KEY = "اعتماد مهارة"
# مهارات تُستدعى ولا تُعتمد اعتمادًا مستقلًّا — بسبب معلن
EXCEPTIONS: dict[str, str] = {}


def skills_from_index() -> list[str]:
    text = INDEX.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^\| `([a-z0-9\-]+)` \|", text, re.M)))


def decision_blob(d: dict) -> str:
    parts = [str(d.get("title_ar", "")), str(d.get("wording_ar", "")), str(d.get("governing_file", ""))]
    for e in d.get("evidence") or []:
        if isinstance(e, dict):
            parts += [str(e.get("ref", "")), str(e.get("note", ""))]
    return " \n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس اعتماد المهارات في دفتر القرارات")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    blockers: list[str] = []
    if not REGISTRY.is_file():
        print("✘ دفتر القرارات غير موجود")
        return 2
    try:
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"✘ دفتر القرارات غير قابل للقراءة: {exc}")
        return 2
    if not INDEX.is_file():
        print("✘ فهرس المشروع غير موجود")
        return 2

    rows = skills_from_index()
    decisions = reg.get("decisions") or []
    adopted = [d for d in decisions if ADOPT_KEY in str(d.get("title_ar", ""))]

    print("=== اعتماد المهارات: الفهرس ↔ دفتر القرارات ===")
    print(f"  مهارات في فهرس المشروع: {len(rows)} · قرارات اعتماد: {len(adopted)}")

    for name in rows:
        if name in EXCEPTIONS:
            continue
        hits = [d for d in decisions if name in decision_blob(d)]
        if not hits:
            blockers.append(f"{name}: في فهرس المشروع بلا قرار يذكرها")
            continue
        done = [d for d in hits if d.get("status") == "منفَّذ"]
        if not done:
            blockers.append(f"{name}: قرارها ليس بحالة «منفَّذ» ({', '.join(d['id'] for d in hits)})")

    for d in adopted:
        named = [n for n in rows if n in decision_blob(d)]
        if not named:
            blockers.append(f"{d.get('id')}: قرار اعتماد لا يذكر مهارة من فهرس المشروع")

    print(f"  النتيجة: {len(blockers)} عائق")
    if not a.quiet:
        for m in blockers:
            print(f"  ✘ {m}")
    return 2 if blockers else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:
        def run(fn):
            raise SystemExit(fn())
    run(main)
