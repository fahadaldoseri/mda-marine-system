#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تسجيل رمز تقدير جديد في فضاء EST- (appendices/estimate-code-map.json).

القاعدة: الرمز يُمنح مرة واحدة ومعناه ثابت (لا إعادة إسناد).
الاستخدام:
    python3 tools/register_estimate.py --date 2026-10-20 --seq 1 \
        --section "قراءة الموقف وتحليل المؤشرات" --statement "…" --confidence "مرجّح (55–80%)" \
        --reliability "UKMTO A/2" --support "…"
    python3 tools/register_estimate.py --list
رموز الخروج: 0 نجاح · 2 رفض (تعارض أو إعادة إسناد)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]
MAP = B / "appendices" / "estimate-code-map.json"


def load() -> dict:
    return json.loads(MAP.read_text(encoding="utf-8"))


def save(d: dict) -> None:
    d["generated_utc"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    MAP.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--seq", type=int)
    ap.add_argument("--section", default="قراءة الموقف وتحليل المؤشرات")
    ap.add_argument("--statement", default="")
    ap.add_argument("--confidence", default="")
    ap.add_argument("--reliability", default="")
    ap.add_argument("--support", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true", help="يتحقق أن كل رمز EST- في تقرير --date مسجَّل (رمز 2 إن وُجد رمز غير مسجَّل)")
    a = ap.parse_args()

    d = load()
    codes = d.setdefault("codes", {})

    if a.check:
        import re
        md = B / "reports" / f"{a.date}-sectioned.md"
        if not a.date or not md.is_file():
            print(f"✘ لا تقرير للفحص: {md}")
            return 2
        used = sorted(set(re.findall(r"EST-\d{4}-\d{2}-\d{2}-\d{2}", md.read_text(encoding="utf-8"))))
        missing = [c for c in used if c not in codes]
        for c in missing:
            print(f"✘ رمز تقدير غير مسجَّل: {c}")
        if missing:
            return 2
        print(f"✔ {len(used)} رمز تقدير مسجّل في تقرير {a.date}")
        return 0

    if a.list or not (a.date and a.seq and a.statement):
        print(f"=== فضاء التقديرات EST- — {len(codes)} رمزًا مسجَّلًا ===")
        for k, v in codes.items():
            print(f"  {k} · {v.get('section','')} · {v.get('confidence','')} · {v.get('statement','')[:60]}")
        return 0

    code = f"EST-{a.date}-{a.seq:02d}"
    if code in codes:
        old = codes[code]
        if old.get("statement") != a.statement:
            print(f"  ✘ إعادة إسناد مرفوضة: {code} معناه الحالي «{old.get('statement')}».")
            return 2
        print(f"  ◐ {code} مسجَّل مسبقًا بالمعنى نفسه — لا تغيير.")
        return 0

    codes[code] = {
        "section": a.section,
        "statement": a.statement,
        "confidence": a.confidence,
        "reliability": a.reliability,
        "support": a.support,
        "status": "قائم",
        "first_seen": a.date,
    }
    save(d)
    print(f"  ✔ سُجّل {code} — {a.statement[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())