#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قياس دقة تقديرات قسم «قراءة الموقف وتحليل المؤشرات» — القاعدة ح10.

يقرأ سجل التقديرات: memory/intel-estimates.jsonl
كل سطر: {"date": "...", "code": "MN-...", "statement": "...", "probability": "يُرجَّح (55–80%)",
        "outcome": "تحقق" | "لم يتحقق" | "لم يتم التأكيد بعد", "cause": "سبب الخطأ إن وُجد"}

يكتب ملخصًا في: appendices/estimate-accuracy-log.md (الربع الجاري) ويطبع النتيجة.

الاستخدام: python3 tools/estimate_accuracy.py [--quarter 2026-Q4]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EST = ROOT / "memory" / "intel-estimates.jsonl"
LOG = ROOT / "appendices" / "estimate-accuracy-log.md"


def quarter_of(d: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})", d or "")
    if not m:
        return "غير محدد"
    y, mo = int(m.group(1)), int(m.group(2))
    return f"{y}-Q{(mo - 1) // 3 + 1}"


def load() -> list[dict]:
    rows = []
    if not EST.exists():
        return rows
    for line in EST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def stamp_report(text: str, generated_at: str) -> str:
    """Add or replace the generation stamp without changing the measured table."""
    marker = f"**آخر توليد (UTC):** {generated_at}"
    text = re.sub(r"\*\*آخر توليد \(UTC\):\*\*[^\n]*\n?", "", text, count=1)
    table = "| عدد التقديرات |"
    pos = text.find(table)
    if pos < 0:
        return text
    line_start = text.rfind("\n", 0, pos) + 1
    return text[:line_start] + marker + "\n\n" + text[line_start:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarter", default=quarter_of(date.today().isoformat()))
    args = ap.parse_args()

    rows = [r for r in load() if quarter_of(r.get("date", "")) == args.quarter]
    total = len(rows)
    confirmed = sum(1 for r in rows if r.get("outcome") == "تحقق")
    refuted = sum(1 for r in rows if r.get("outcome") == "لم يتحقق")
    opened = sum(1 for r in rows if r.get("outcome") == "لم يتم التأكيد بعد")
    causes = Counter((r.get("cause") or "").strip() for r in rows if (r.get("cause") or "").strip())
    top_cause = causes.most_common(1)[0][0] if causes else "غير مسجل بعد"
    rate = f"{confirmed / total * 100:.0f}%" if total else "لا يوجد قياس بعد"

    print(f"===== قياس دقة التقديرات — {args.quarter} =====")
    print(f"  · عدد التقديرات: {total} · تحقق: {confirmed} · لم يتحقق: {refuted} · لم يتم التأكيد بعد: {opened}")
    print(f"  · نسبة التحقق: {rate}")
    print(f"  · أكثر سبب للخطأ: {top_cause}")
    if causes:
        for c, n in causes.most_common(5):
            print(f"    - {c}: {n}")

    if LOG.exists():
        txt = LOG.read_text(encoding="utf-8")
        block = (
            f"| عدد التقديرات | {total} |\n"
            f"| ما تحقق | {confirmed} |\n"
            f"| ما لم يتحقق | {refuted} |\n"
            f"| ما بقي لم يتم التأكيد بعد | {opened} |\n"
            f"| أكثر سبب للخطأ | {top_cause} |"
        )
        new = re.sub(
            r"(\| عدد التقديرات \|.*?\| أكثر سبب للخطأ \|[^\n]*\|)",
            block,
            txt,
            flags=re.S,
        )
        if new != txt:
            new = stamp_report(new, datetime.now(timezone.utc).isoformat())
            LOG.write_text(new, encoding="utf-8")
            print(f"  ✔ حُدّث السجل: {LOG}")
        else:
            print("  ⚠ لم يُطابق نمط الجدول في السجل — راجعه يدويًا")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
