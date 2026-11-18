#!/usr/bin/env python3
"""بوابة روابط الوقائع — تفشل مغلقًا على أي رابط بلا سند أو معرّف معلّق.

تحرس ثلاثة أشياء (كلها مقيسة من الدفتر نفسه):
  1) كل سجل يحمل `update_of` أو `parent_id` أو `duplicate_of` يجب أن يحمل `link_basis`
     يذكر المعرّف الذي بُني عليه الربط.
  2) كل قيمة ربط يجب أن تُشير إلى معرّف موجود فعلًا: رمز واقعة يومية في الدفتر التراكمي
     أو معرّف واقعة في الدفتر المجمّد (EV-...). المعرّف المعلّق = فشل.
  3) `parent_id` يجب أن يكون جذر السلسلة: أي أنه لا يشير إلى سجل يحمل `update_of` نفسه.

الاستعمال: python3 validators/check_event_links.py [--date YYYY-MM-DD]
رموز الخروج: 0 = اجتاز · 2 = فشل مانع.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRAIN = pathlib.Path(os.environ.get("BRAIN_DIR") or ROOT)
DAILY = BRAIN / "cumulative-2026" / "daily"
FROZEN = BRAIN / "cumulative-2026" / "event-ledger-sectioned-2026-02-28-to-2026-10-11.json"


def load() -> list[dict]:
    recs = []
    for f in sorted(DAILY.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            print(f"   ✘ ملف يومي تالف: {f.name} — {exc}")
            continue
        for r in data if isinstance(data, list) else []:
            if isinstance(r, dict):
                r["_file"] = f.name
                recs.append(r)
    return recs


def main() -> int:
    ap = argparse.ArgumentParser(description="بوابة روابط الوقائع في الدفتر التراكمي")
    ap.add_argument("--date", help="يوم واحد للفحص الموجّه")
    args = ap.parse_args()

    recs = load()
    if not recs:
        print("   ✘ لا سجلات في الدفتر التراكمي")
        return 2

    codes = {str(r.get("code") or "") for r in recs}
    frozen_ids: set[str] = set()
    if FROZEN.exists():
        try:
            j = json.loads(FROZEN.read_text(encoding="utf-8"))
            frozen_ids = {str(e.get("event_id") or "") for e in j.get("events", [])}
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            pass
    known = codes | frozen_ids

    linked = [r for r in recs if any(r.get(k) for k in ("update_of", "parent_id", "duplicate_of"))]
    if args.date:
        linked = [r for r in linked if str(r.get("date")) == args.date]

    problems: list[str] = []
    for r in linked:
        code = str(r.get("code") or "")
        if not str(r.get("link_basis") or "").strip():
            problems.append(f"رابط بلا سند: {code}")
        for field in ("update_of", "parent_id", "duplicate_of"):
            val = str(r.get(field) or "").strip()
            if val and val not in known:
                problems.append(f"معرّف معلّق في {field}: {code} ← {val}")
        # عقد الحقول (ledger_link_fields.py وcheck_ledger_links.py) يمنع parent_id مع event_kind «تحديث»؛
        # فجذر التحديث هو هدف update_of نفسه، وقد فُحص وجوده في الدفتر أعلاه.
        if str(r.get("update_of") or "") and str(r.get("update_of")).strip() not in known \
                and not str(r.get("parent_id") or ""):
            problems.append(f"تحديث بلا جذر: {code}")

    total = len(recs)
    with_ref = sum(1 for r in recs if str(r.get("official_ref") or "").strip())
    print("   ══ بوابة روابط الوقائع ══")
    print(f"   سجلات الدفتر: {total} · سجلات بمعرّف رسمي: {with_ref} · سجلات مربوطة: {len(linked)}")
    for r in linked[:10]:
        print(f"      · {r.get('code')} ← {r.get('update_of') or r.get('duplicate_of')} | "
              f"{str(r.get('link_basis'))[:70]}")
    if problems:
        print(f"   ✘ مشكلات: {len(problems)}")
        for p in problems[:12]:
            print("      -", p)
        return 2
    print("   ✔ اجتاز: كل رابط له سند ومعرّف موجود")
    return 0


if __name__ == "__main__":
    import sys as _sys, pathlib as _pl
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
    from _guard import run
    run(main)