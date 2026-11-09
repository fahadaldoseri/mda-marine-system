#!/usr/bin/env python3
"""قياس جاهزية الانطلاق قبل تنفيذ خطة متعددة المراحل.

يقيس أربعة بنود ويطبع كل قياس برقمه ودليله:
  1) تغطية البنود: كل معرّف في الجرد له مرجع في الخطة (والمدموج يُطبع مدموجًا لا ناقصًا).
  2) تداخل الخطة: يستدعي أداة المهارة الجارة pre-execution-plan-audit-ops إن وُجدت.
  3) قرار الاعتماد: قرار في الدفتر يذكر الجرد أو نطاق المعرّفات.
  4) البنود المعلّقة: قسم معلن يسمّي المعلّق وحالته.

الاستعمال:
    check_launch_readiness.py --plan خطة.md [--inventory جرد.md] [--registry registry.json] \
        [--neighbor-scripts /home/ubuntu/skills/pre-execution-plan-audit-ops/scripts]

الخروج: 0 جاهز · 2 مانع يمنع الانطلاق · 64 خطأ استعمال.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ID_RE = re.compile(r'[مخد][\-\u2010-\u2015\u2212]\s?(\d{2})')
# حدّ الكلمة إلزامي: «بعد-2026» ليست «د-20»، و«مقد-05» ليست معرّفًا.
PREFIXED_RE = re.compile(r'(?<![\u0621-\u064A])([مخد])[\-\u2010-\u2015\u2212]\s?(\d{2})(?!\d)')
MERGE_WORDS = ("مدموج", "مدمج", "يشمل البند")


def ids_in(text: str) -> set[str]:
    return {f"{p}-{n}" for p, n in PREFIXED_RE.findall(text)}


def merged_ids(inventory: str) -> set[str]:
    """معرّفات مذكورة بصيغة «مدموج في …» — ليست فجوة."""
    out: set[str] = set()
    for line in inventory.splitlines():
        if any(w in line for w in MERGE_WORDS):
            out |= ids_in(line)
    return out


# التغطية تُقاس على بنود الملاحظات (م-xx) وعيوب القياس (خ-xx) لأنها وحدها ما يُسنَد إلى مرحلة.
# أما القرارات (د-xx) فتُذكر إخباريًا: القرار يُنفَّذ عبر بنوده لا عبر رقمه.
COVERAGE_PREFIXES = ("م", "خ")


def check_coverage(plan: str, inventory: str) -> list[str]:
    blockers: list[str] = []
    inv = {i for i in ids_in(inventory) if i[0] in COVERAGE_PREFIXES}
    decisions = {i for i in ids_in(inventory) if i[0] not in COVERAGE_PREFIXES}
    plan_ids = ids_in(plan)
    missing = sorted(inv - plan_ids, key=lambda x: (x[0], int(x.split("-")[1])))
    merged = merged_ids(inventory)
    real = [m for m in missing if m not in merged]
    print(f"   1) تغطية البنود: الجرد {len(inv)} · الخطة {len(plan_ids & inv)} · ناقص {len(missing)}")
    if decisions:
        print(f"      · قرارات مذكورة (إخباريًا لا تُسنَد إلى مرحلة): {len(decisions)}")
    if missing:
        for m in missing:
            print(f"      · {m}: {'مدموج في بند آخر — ليست فجوة' if m in merged else 'غير مسنَد إلى أي مرحلة'}")
    for m in real:
        blockers.append(f"بند بلا مرحلة: {m}")
    return blockers


def check_duplication(plan: Path, neighbor: Path | None) -> list[str]:
    tool = None
    if neighbor:
        cand = neighbor / "audit_plan_duplication.py"
        if cand.is_file():
            tool = cand
    if not tool:
        print("   2) تداخل الخطة: غير مُقاس — أداة الجارة غير موجودة (سجّل ذلك ولا تدّعِ نظافة)")
        return []
    r = subprocess.run([sys.executable, str(tool), "--plan", str(plan)],
                       capture_output=True, text=True, timeout=300)
    print(f"   2) تداخل الخطة: rc={r.returncode}")
    if r.returncode != 0:
        tail = (r.stdout or r.stderr).strip().splitlines()[-3:]
        for line in tail:
            print(f"      · {line.strip()}")
        return ["تداخل في الخطة يمنع الانطلاق"]
    return []


def check_approval(registry: Path | None, inventory: Path | None) -> list[str]:
    if not registry or not registry.is_file():
        print("   3) قرار الاعتماد: غير مُقاس — لا دفتر قرارات (سجّل ذلك)")
        return []
    reg = json.loads(registry.read_text(encoding="utf-8"))
    hay = json.dumps(reg, ensure_ascii=False)
    key = inventory.name if inventory else ""
    hit = [d for d in reg.get("decisions", [])
           if (key and key in json.dumps(d, ensure_ascii=False)) or
           ("اعتماد" in d.get("title_ar", "") and "ملاحظات" in d.get("title_ar", ""))]
    print(f"   3) قرار الاعتماد: {len(hit)} قرارًا يذكر الجرد أو اعتماد الملاحظات")
    for d in hit:
        print(f"      · {d['id']} · {d['status']} · {d['title_ar'][:70]}")
    return [] if hit else ["لا قرار اعتماد مرقّم للجرد — الانطلاق بلا سند"]


def check_pending(plan: str) -> list[str]:
    lines = plan.splitlines()
    head = [i for i, l in enumerate(lines) if re.match(r'^#{2,3}.*(ينتظر|انطلق|معلّق)', l)]
    pend = [l for l in lines if "معلّق" in l and l.strip().startswith("|")]
    print(f"   4) البنود المعلّقة: قسم معلن {'موجود' if head else 'غير موجود'} · بنود بحالة معلّق {len(pend)}")
    for l in pend[:6]:
        cells = [c.strip() for c in l.strip("|").split("|")]
        print(f"      · {cells[0][:60]} — {cells[1][:30] if len(cells) > 1 else ''}")
    if not head:
        return ["لا قسم معلن للبنود المعلّقة — المعلّق المخفي مانع"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--inventory")
    ap.add_argument("--registry")
    ap.add_argument("--neighbor-scripts", default="/home/ubuntu/skills/pre-execution-plan-audit-ops/scripts")
    a = ap.parse_args()

    plan_p = Path(a.plan)
    if not plan_p.is_file():
        print(f"  ✘ الخطة غير موجودة: {plan_p}")
        return 64
    plan = plan_p.read_text(encoding="utf-8")
    inventory = Path(a.inventory).read_text(encoding="utf-8") if a.inventory and Path(a.inventory).is_file() else ""

    print(f"  خطة: {plan_p.name} · أسطر {len(plan.splitlines())}")
    blockers: list[str] = []
    blockers += check_coverage(plan, inventory) if inventory else []
    if not inventory:
        print("   1) تغطية البنود: غير مُقاسة — لا جرد مُمرَّر")
    blockers += check_duplication(plan_p, Path(a.neighbor_scripts) if a.neighbor_scripts else None)
    blockers += check_approval(Path(a.registry) if a.registry else None,
                              Path(a.inventory) if a.inventory else None)
    blockers += check_pending(plan)

    if blockers:
        print(f"  ✘ الجاهزية: {len(blockers)} مانع")
        for b in blockers:
            print(f"     - {b}")
        return 2
    print("  ✔ الجاهزية: لا مانع — يمكن الانطلاق بالمرحلة الأولى")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())