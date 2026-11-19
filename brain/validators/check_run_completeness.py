#!/usr/bin/env python3
"""بوابة اكتمال التشغيل — التشغيل المنقوص قاعدة آلية لا حكم (ح-4 · قرار 2026-10-23).

القاعدة:
  • overall = ok ⇒ نجاح.
  • overall = degraded/failed ⇒ كل عطل يجب أن يكون في قائمة الأعطال المعروفة
    (appendices/known-faults.json) وأن يكون مُفصحًا عنه في متن التقرير نفسه.
  • أي عطل خارج القائمة، أو عطل معروف غير مُفصح ⇒ منع (رمز 2).

الاستخدام: python3 validators/check_run_completeness.py --date 2026-10-23
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(B / "tools"))
from known_faults import classify_component, degraded_components  # noqa: E402

# ك-590: متن عربي لا يُطالَب بكتابة معرّف إنجليزي؛ تُقبل التسمية العربية للمكوّن مع لفظ الإفصاح.
COMPONENT_LABELS_AR = {
    "feeds": ("التغذية", "التغذيات", "المصادر"),
    "ofac": ("العقوبات", "قوائم العقوبات"),
    "originals": ("النصوص الأصلية", "الأصول"),
    "ledger_merge": ("دفتر الأحداث", "الدفتر"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    mark_p = B / "logs" / f"pipeline-{a.date}.json"
    if not mark_p.exists():
        print(f"  ✘ لا علامة تشغيل لليوم: {mark_p} — لا تسليم بلا علامة")
        return 2
    mark = json.loads(mark_p.read_text(encoding="utf-8"))
    overall = str(mark.get("overall") or "")
    # ك-XX: لا يُحكم على علامة قديمة — تُقارن أولًا بالمخرجات الفعلية (مصدر واحد للحقيقة)
    sys.path.insert(0, str(B / "tools"))
    try:
        from mark_components import DERIVERS  # noqa: E402
        stale: list[str] = []
        for c, fn in DERIVERS.items():
            status, _note, _items, _detail = fn(a.date)
            cur = str((mark.get(c) or {}).get("status") or "")
            if cur and cur != status:
                stale.append(f"{c}: العلامة «{cur}» والمخرجات «{status}»")
        if stale:
            for s in stale:
                print(f"  ✘ علامة قديمة — {s}")
            print("  ✘ حدّث العلامة: python3 tools/mark_components.py --date " + a.date)
            return 2
    except Exception as exc:  # انهيار التحقق = منع (لا ابتلاع)
        print(f"  ✘ تعذّر التحقق من مطابقة العلامة للمخرجات: {type(exc).__name__}: {exc}")
        return 2
    comps = degraded_components(mark)

    md = B / "reports" / f"{a.date}-sectioned.md"
    body = md.read_text(encoding="utf-8") if md.exists() else ""
    if not body:
        print(f"  ✘ لا نص تقرير: {md}")
        return 2

    if overall == "ok" and not comps:
        print("  ✓ التشغيل مكتمل (overall = ok) ولا أعطال")
        return 0

    blockers: list[str] = []
    allowed: list[str] = []
    for comp, st, text, items in comps:
        r = classify_component(comp, st, text, items, today=a.date)
        if not r["allowed"]:
            blockers.append(f"{comp} ({st}): " + "؛ ".join(r["uncovered"])[:200])
            continue
        # الإفصاح: نصّه في متن التقرير (السطر المُولَّد آليًا يحمل سبب النقص)
        tag = r.get("reason_ar_full") or r["reason_ar"] or st
        short = r["reason_ar"] or st
        disclosed = (short in body) or (tag in body) or (f"{comp}" in body and "تعذّر" in body)
        if not disclosed:
            blockers.append(f"{comp} ({st}): عطل معروف لكنه غير مُفصح عنه في متن التقرير")
        else:
            allowed.append(f"{comp} ({st}) — {tag}")

    if blockers:
        for x in blockers:
            print(f"  ✘ {x}")
        print(f"النتيجة: تشغيل منقوص بأعطال غير مسموح بها — مانع ({len(blockers)})")
        return 2
    for x in allowed:
        print(f"  ✓ عطل معروف مُفصح: {x}")
    print(f"  · الحالة العامة: {overall} — يُسلَّم بإفصاح مكتوب في المتن")
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)