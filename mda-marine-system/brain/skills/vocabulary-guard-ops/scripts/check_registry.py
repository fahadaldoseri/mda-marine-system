#!/usr/bin/env python3
"""تحقق من صحة «السجل الحاكم» و«القائمة المُولَّدة» لكلمات المنع وبدائلها.

يُستعمل فوق أي مشروع: يُمرَّر مسار السجل (JSON فيه قائمة entries) ومسار المُولَّد.
يرجع 0 عند السلامة، و1 عند وجود خلل — ليصلح للربط ببوابة تسليم (فشل مغلق).

الفحوص:
  1) كل بند يحمل term/plain/status/reason/since بحسب حالته.
  2) term لا يساوي أيًّا من بدائله plain (لا يمنع اللفظ نفسه).
  3) لا يوجد تقاطع: term أي بند لا يساوي plain بند آخر (وإلا صار البديل مانعًا).
  4) تكرار term بحالتين مختلفتين = خلل.
  5) المُولَّد يطابق ما يُشتق من السجل (approved فقط، ترتيب ثابت).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED = ("term", "plain", "status")
STATUSES = ("approved", "watch", "candidate", "rejected", "proposed")


def load_entries(path: Path) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(d, dict):
        for key in ("entries", "items", "terms", "words"):
            if isinstance(d.get(key), list):
                return d[key]
        raise SystemExit(f"✘ لا قائمة بنود في {path}")
    if isinstance(d, list):
        return d
    raise SystemExit(f"✘ شكل غير مدعوم في {path}")


def validate(entries: list[dict]) -> list[str]:
    errs: list[str] = []
    seen: dict[str, str] = {}
    for i, e in enumerate(entries, 1):
        for k in REQUIRED:
            if k == "plain":
                pl = e.get("plain")
                if not isinstance(pl, list) or not [p for p in pl if str(p).strip()]:
                    errs.append(f"البند {i} ({e.get('term')}): «plain» قائمة بدائل فارغة")
            elif not str(e.get(k) or "").strip():
                errs.append(f"البند {i}: الحقل «{k}» مطلوب")
        st = str(e.get("status") or "")
        if st and st not in STATUSES:
            errs.append(f"البند {i} ({e.get('term')}): حالة غير معروفة «{st}»")
        if st == "approved":
            for k in ("reason", "since"):
                if not str(e.get(k) or "").strip():
                    errs.append(f"البند {i} ({e.get('term')}): المانع يحتاج «{k}»")
        term = str(e.get("term") or "").strip()
        if term and term in [str(p).strip() for p in (e.get("plain") or [])]:
            errs.append(f"البند {i}: اللفظ «{term}» وارد ضمن بدائله — تناقض")
        if term in seen and seen[term] != st:
            errs.append(f"اللفظ «{term}» بحالتين مختلفتين: {seen[term]} و{st}")
        seen[term] = st
    # 3) التقاطع بين أسماء المنع وبدائلها
    plains = {str(p).strip() for e in entries for p in (e.get("plain") or [])}
    for e in entries:
        t = str(e.get("term") or "").strip()
        if t in plains:
            errs.append(f"تقاطع: اللفظ المانع «{t}» يساوي بديلًا معتمدًا في السجل — البديل سيُمنع بلا سبب")
    return errs


def derive(entries: list[dict]) -> list[dict]:
    out = [e for e in entries if e.get("status") == "approved"]
    out.sort(key=lambda e: (str(e.get("since") or ""), str(e.get("term") or "")))
    return [{"term": e["term"], "plain": [p for p in e["plain"] if str(p).strip()],
             "reason": e.get("reason", ""), "source": e.get("source", "")} for e in out]


def main() -> int:
    ap = argparse.ArgumentParser(description="تحقق من السجل الحاكم ومُولَّده")
    ap.add_argument("--registry", required=True)
    ap.add_argument("--generated", required=True)
    ap.add_argument("--json", action="store_true", help="إخراج JSON للربط الآلي")
    a = ap.parse_args()

    reg = load_entries(Path(a.registry))
    errs = validate(reg)
    want = derive(reg)
    gen = load_entries(Path(a.generated)) if Path(a.generated).exists() else []
    gen_keys = [str(e.get("term")) for e in gen]
    want_keys = [str(e.get("term")) for e in want]
    if gen_keys != want_keys:
        miss = [t for t in want_keys if t not in gen_keys]
        extra = [t for t in gen_keys if t not in want_keys]
        if miss:
            errs.append(f"المُولَّد ناقص {len(miss)} بندًا: {miss[:5]}")
        if extra:
            errs.append(f"المُولَّد يحمل {len(extra)} بندًا غير مشتق من السجل: {extra[:5]}")
        if not miss and not extra:
            errs.append("ترتيب المُولَّد لا يطابق الترتيب الثابت للسجل")

    report = {"registry_entries": len(reg), "approved": len(want),
              "generated_entries": len(gen_keys), "errors": errs}
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"  السجل: {len(reg)} بندًا · المعتمد: {len(want)} · المُولَّد: {len(gen_keys)}")
        for e in errs:
            print(f"  ✘ {e}")
        print("  ✓ السجل والمُولَّد سليمان ومتطابقان" if not errs else "  ✘ خلل يمنع الاعتماد")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
