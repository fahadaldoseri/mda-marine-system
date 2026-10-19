#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""التعلم والتطوير الذاتي لقسم «التحليل الاستخباري» — تنفّذ القاعدة ح12.

يقرأ: سجل التعلم العام، وسجل تعلم القسم، وسجل دقة التقديرات.
يكتب: memory/intel-adaptation.md — التعديلات المطبَّقة تلقائيًا (مستوى منخفض)،
       وما هو قيد الترقية (متوسط)، وما يحتاج اعتمادًا صريحًا (عالي).

الاستخدام: python3 tools/intel_self_review.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERAL_LOG = ROOT / "memory" / "learning-log.jsonl"
INTEL_LOG = ROOT / "memory" / "intel-learning.jsonl"
ACC_LOG = ROOT / "appendices" / "estimate-accuracy-log.md"
OUT = ROOT / "memory" / "intel-adaptation.md"

INTEL_KEYS = ("تحليل", "استخبار", "تقدير", "فرض", "افتراض", "مؤشر")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def classify(lesson: str, explicit: str | None) -> int:
    """يحدد مستوى التغيير: 1 منخفض · 2 متوسط · 3 عالي (ح12)."""
    if explicit in {"1", "2", "3"}:
        return int(explicit)
    high = ("سلّم", "لغة الاحتمال", "تعريف المؤشر", "منهج الإسناد", "موضع القسم", "حذف قسم")
    mid = ("أسلوب", "وزن", "أولوية مؤشر", "درجة الثقة", "ترتيب")
    for k in high:
        if k in lesson:
            return 3
    for k in mid:
        if k in lesson:
            return 2
    return 1


def read_accuracy() -> dict:
    """يستخرج ملخص دقة التقديرات من السجل الربعي إن وُجد."""
    out = {"estimates": 0, "confirmed": 0, "refuted": 0, "open": 0, "top_cause": ""}
    if not ACC_LOG.exists():
        return out
    txt = ACC_LOG.read_text(encoding="utf-8")
    m = re.search(r"عدد التقديرات[^\d]*(\d+)", txt)
    if m:
        out["estimates"] = int(m.group(1))
    m = re.search(r"ما تحقق[^\d]*(\d+)", txt)
    if m:
        out["confirmed"] = int(m.group(1))
    m = re.search(r"ما لم يتحقق[^\d]*(\d+)", txt)
    if m:
        out["refuted"] = int(m.group(1))
    m = re.search(r"غير محسوم[^\d]*(\d+)", txt)
    if m:
        out["open"] = int(m.group(1))
    causes = re.findall(r"سبب[^\n:：]*[:：]\s*(.+)", txt)
    if causes:
        out["top_cause"] = Counter(c.strip() for c in causes).most_common(1)[0][0]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()

    general = load_jsonl(GENERAL_LOG)
    intel = load_jsonl(INTEL_LOG)

    # دروس ذات صلة بالقسم من السجل العام
    relevant = []
    for r in general:
        blob = " ".join(str(r.get(k, "")) for k in ("lesson", "note", "category", "title"))
        if any(k in blob for k in INTEL_KEYS):
            relevant.append(r)

    counter = Counter()
    for r in relevant + intel:
        text = (r.get("lesson") or r.get("note") or "").strip()
        if text:
            counter[text] += 1

    auto, promote, needs_approval = [], [], []
    for lesson, count in counter.most_common():
        level = classify(lesson, str(r.get("level")) if r.get("level") is not None else None)
        if level == 1:
            auto.append((lesson, count))
        elif level == 2:
            (promote if count >= 2 else needs_approval).append((lesson, count))
        else:
            needs_approval.append((lesson, count))

    acc = read_accuracy()

    lines = [
        "# التكيّف الذاتي لقسم التحليل الاستخباري",
        "",
        f"**تاريخ التوليد:** {args.date} · **الأداة:** `tools/intel_self_review.py` · **القاعدة:** ح12",
        f"**الدروس المقروءة:** {len(general)} في السجل العام · {len(intel)} في سجل القسم · "
        f"{len(relevant)} ذات صلة بالقسم",
        "",
        "> يُقرأ هذا الملف **قبل** كتابة قسم التحليل الاستخباري في كل تشغيل، ويُطبَّق ما فيه ثم يُسجَّل الدرس الجديد.",
        "",
        "## 1) تعديلات مطبَّقة تلقائيًا (منخفض المخاطر)",
        "",
    ]
    if auto:
        for lesson, count in auto[:12]:
            lines.append(f"- {lesson} — (تكرار: {count})")
    else:
        lines.append("- لا تعديلات جديدة.")

    lines += ["", "## 2) قيد الترقية — تُطبَّق بعد تكرارها مرتين بدليل (متوسط)", ""]
    if promote:
        for lesson, count in promote[:10]:
            lines.append(f"- {lesson} — (تكرار: {count}) ✔ استوفى شرط الترقية")
    else:
        lines.append("- لا شيء.")

    lines += ["", "## 3) تحتاج اعتمادًا صريحًا من صاحب القرار (عالي المخاطر)", ""]
    if needs_approval:
        for lesson, count in needs_approval[:10]:
            lines.append(f"- {lesson} — (تكرار: {count})")
    else:
        lines.append("- لا شيء.")

    lines += [
        "",
        "## 4) قياس دقة التقديرات (المصدر: سجل القياس الربعي)",
        "",
        f"- عدد التقديرات: **{acc['estimates']}** · تحقق: **{acc['confirmed']}** · "
        f"لم يتحقق: **{acc['refuted']}** · غير محسوم: **{acc['open']}**",
        f"- أكثر سبب للخطأ: {acc['top_cause'] or 'غير مسجل بعد'}",
        "",
        "> لا يُرقّى أسلوب تحليلي ولا تُعدَّل قاعدة تحليلية بلا سجل قياس دقة يسبقه (ح10).",
        "",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("===== التكيّف الذاتي لقسم التحليل الاستخباري =====")
    print(f"  · دروس ذات صلة: {len(relevant)} · مطبَّق تلقائيًا: {len(auto)} · "
          f"قيد الترقية: {len(promote)} · يحتاج اعتمادًا: {len(needs_approval)}")
    print(f"  · دقة التقديرات: {acc['estimates']} تقديرًا — تحقق {acc['confirmed']} · "
          f"لم يتحقق {acc['refuted']} · غير محسوم {acc['open']}")
    print(f"  ✔ كُتب: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())