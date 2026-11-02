#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قياس تغطية الربط: كل ملف في الشجرة المحكومة له مالك معلن أو استثناء مكتوب.

العلّة (ك-462): جردٌ بالبحث النصي العام صنّف 6729 ملفًا «يتيمًا» لأنه عدّ المرآة
وسجلات التشغيل والنسخ الأرشيفية أصولًا تحتاج مالكًا. القياس الصحيح يميّز:
  * مُدخل حاكم  → يذكره الكتيب أو بوابة أو قسم أو أداة أو مهارة.
  * مُخرَج مُعلن → داخل مجلد مخرج معلن في المانيفست (يوميات · تقارير · واجهة...).
  * مستثنى      → سجل تشغيل · أرشيف · نسخة · ذاكرة مؤقتة · مرآة، بسبب مكتوب.
  * يتيم فعلي   → لا مالك ولا استثناء: عطل ربم منع.

الخروج: 0 مطابق · 1 تحذير (يتامى محدودة) · 2 مانع (يتامى غير مفسّرة كثيرة).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# مجلدات الأصول المحكومة (ما يجب أن يكون له مالك أو استثناء)
GOVERNED = ["validators", "tools", "sections", "appendices", "web", "reports",
            "runbook", "docs", "tests", "cumulative-2026", "sources", "generator"]

# استثناءات بأسباب مكتوبة (مسارات نسبية أو بادئات)
EXEMPT_RULES = [
    ("audit/", "سجل التدقيق والنسخ الأرشيفية — يُقرأ بالتاريخ لا بالمالك اليومي"),
    ("logs/", "سجلات تشغيل اليوم — مخرجات خطوة لا أصول"),
    ("archive/", "أرشيف تاريخي مقفل"),
    ("memory/", "سجل التعلم الذاتي — يُكتب آليًا كل جولة"),
    ("__pycache__", "ذاكرة ترجمة مؤقتة"),
    (".pytest_cache", "ذاكرة اختبارات مؤقتة"),
    ("node_modules", "حزم خارجية"),
    (".git/", "بيانات الإصدارة"),
    ("INDEX.md", "فهرس المشروع: يذكر كل شيء ولا يُشار إليه"),
]

OWNER_SOURCES = ["runbook/runbook.json", "docs/runbook.md"]
SECTION_GLOB = "sections/*.md"
CODE_GLOBS = ["validators/*.py", "tools/*.py", "tools/*.sh", "tests/*"]
SKILL_ROOTS = [pathlib.Path("/home/ubuntu/skills")]


def read(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def load_owner_corpus() -> tuple[str, list[str]]:
    """نص كل المصادر التي تُثبت الملكية + قائمة مجلدات المخرجات المعلنة."""
    parts: list[str] = []
    for rel in OWNER_SOURCES:
        parts.append(read(ROOT / rel))
    for p in sorted(ROOT.glob(SECTION_GLOB)):
        parts.append(read(p))
    for g in CODE_GLOBS:
        for p in sorted(ROOT.glob(g)):
            if p.is_file():
                parts.append(read(p))
    outputs: list[str] = []
    try:
        rb = json.loads(read(ROOT / "runbook" / "runbook.json"))
    except json.JSONDecodeError:
        rb = {}
    manifest_exempt = [str(x) for x in (rb.get("exempt") or [])]
    manifest_reasons = rb.get("exempt_reasons") or {}
    for pattern in manifest_exempt:
        reason = manifest_reasons.get(pattern) or "مُعلَن في المانيفست"
        DECLARED_RULES.append((pattern, str(reason)[:120]))
    for step in rb.get("steps", []):
        for entry in step.get("outputs", []) or []:
            outputs.append(str(entry))
    parts.append(json.dumps(rb, ensure_ascii=False))
    return "\n".join(parts), outputs


def is_exempt(rel: str) -> str | None:
    for prefix, reason in EXEMPT_RULES:
        if rel.startswith(prefix) or f"/{prefix}" in rel or prefix in rel:
            return reason
    for pattern, reason in DECLARED_RULES:
        base = pattern.rstrip("*").rstrip("/")
        if not base:
            continue
        if rel == base or rel.startswith(base + "/"):
            return f"مانيفست: {reason}"
    return None


DECLARED_RULES: list[tuple[str, str]] = []


def is_declared_output(rel: str, outputs: list[str]) -> bool:
    for out in outputs:
        out = out.strip().lstrip("./")
        if not out:
            continue
        if rel == out or rel.startswith(out.rstrip("*").rstrip("/") + "/"):
            return True
    return False


def name_referenced(rel: str, corpus: str) -> bool:
    base = os.path.basename(rel)
    if base and base in corpus:
        return True
    stem = rel.lstrip("./")
    return stem in corpus and len(stem) > 3


def main() -> int:
    global ROOT
    ap = argparse.ArgumentParser(description="قياس تغطية الربط للمشروع")
    ap.add_argument("--brain", default=str(ROOT))
    ap.add_argument("--json", default="")
    ap.add_argument("--show", type=int, default=15, help="عدد اليتامى المعروضين")
    a = ap.parse_args()

    corpus, outputs = load_owner_corpus()
    bound, declared, exempt, orphans = [], [], [], []
    for top in GOVERNED:
        base = ROOT / top
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(ROOT))
            reason = is_exempt(rel)
            if reason:
                exempt.append((rel, reason))
            elif name_referenced(rel, corpus):
                bound.append(rel)
            elif is_declared_output(rel, outputs):
                declared.append(rel)
            else:
                orphans.append(rel)

    total = len(bound) + len(declared) + len(exempt) + len(orphans)
    print(f"   ══ تغطية الربط — {ROOT.name} ══")
    print(f"   | الملفات المحكومة المفحوصة: {total}")
    print(f"   | مالك مذكور صريحًا:        {len(bound)}")
    print(f"   | مخرج معلن في المانيفست:   {len(declared)}")
    print(f"   | مستثنى بسبب مكتوب:        {len(exempt)}")
    print(f"   | يتيم بلا مالك ولا استثناء: {len(orphans)}")
    for rel in orphans[: a.show]:
        print(f"   | ✘ {rel}")
    verdict = 0
    if orphans:
        verdict = 2 if len(orphans) > 25 else 1
    print(f"   النتيجة: {'مطابق' if verdict == 0 else ('تحذير' if verdict == 1 else 'مانع')}"
          f" — {len(orphans)} يتيمًا")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "brain": str(ROOT), "total": total, "bound": len(bound),
            "declared_output": len(declared), "exempt": len(exempt),
            "orphans": orphans, "verdict": verdict,
            "samples": {"bound": bound[:20], "exempt": exempt[:10]}}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    return verdict


if __name__ == "__main__":
    sys.exit(main())
