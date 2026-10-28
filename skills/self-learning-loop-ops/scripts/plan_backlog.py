#!/usr/bin/env python3
"""جدولة متأخرات حلقة التعلم: الأعطال الحديثة المُغلقة بلا درس مطابق أو بلا تشديد مسجَّل.

تخرج خطة Markdown بدفعات مرتّبة، ومع كل عطل أمرُ الإغلاق الجاهز وحقولُ الدرس المطلوب تعبئتها.
"""
import argparse, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

ALIAS = {"action": ("action", "hardening", "barrier", "lesson", "fix", "rule", "prevention"),
         "symptom": ("symptom", "trigger", "fault", "defect", "issue")}


def val(e, key):
    for k in ALIAS[key]:
        v = e.get(k)
        if v not in (None, "", [], {}):
            return str(v).strip()
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--learning", required=True)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = [json.loads(l) for l in Path(a.index).read_text(encoding="utf-8").splitlines() if l.strip()]
    entries = [json.loads(l) for l in Path(a.learning).read_text(encoding="utf-8").splitlines() if l.strip()]
    modern = [r for r in rows if r.get("date")][-a.limit:]

    pending = []
    for r in modern:
        date, sym = r.get("date", ""), r.get("symptom", "")
        same = [e for e in entries if e.get("date") == date]
        sym_ok = [e for e in same if sym and val(e, "symptom")[:12] == sym[:12]]
        tailored = [e for e in sym_ok if val(e, "action")]
        if r.get("closed") and not tailored:
            kind = "بلا درس مطابق بالعَرَض" if not sym_ok else "درس مطابق بلا تشديد"
            pending.append({"id": r["id"], "axis": r.get("axis", ""), "symptom": sym,
                            "cause": r.get("cause", ""), "fix": r.get("fix_status", ""),
                            "date": date, "kind": kind})

    by_axis = defaultdict(list)
    for p in pending:
        by_axis[p["axis"] or "غير مصنّف"].append(p)
    batches, cur = [], []
    for axis, items in sorted(by_axis.items(), key=lambda kv: -len(kv[1])):
        for it in items:
            cur.append(it)
            if len(cur) >= a.batch:
                batches.append(cur)
                cur = []
    if cur:
        batches.append(cur)

    L = ["# خطة إغلاق متأخرات حلقة التعلم", "",
         f"- الأعطال الحديثة المفحوصة: {len(modern)}",
         f"- المكتملة الإغلاق: {len(modern) - len(pending)}",
         f"- المتأخرات: {len(pending)} في {len(batches)} دفعة (حتى {a.batch} لكل دفعة)",
         f"- التصنيفات: {dict(Counter(p['kind'] for p in pending))}", "",
         "## قاعدة الإغلاق", "",
         "لكل عطل: سبب جذري مكتوب · درس مطابق بالعَرَض يحمل تشديدًا · إثبات بأمر ومخرجه · ثم يُحدَّث حاله.", ""]
    for i, b in enumerate(batches, 1):
        L += [f"## الدفعة {i} — {len(b)} أعطال", ""]
        for p in b:
            L += [f"### {p['id']} · {p['axis']}", "",
                  f"- العَرَض: {p['symptom']}",
                  f"- السبب المسجَّل: {p['cause']}",
                  f"- الإصلاح والحالة: {p['fix']}",
                  f"- النقص: {p['kind']}", "- المطلوب: تشديد آلي مُختبَر بكسر متعمَّد + درس مطابق بالعَرَض", ""]
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"  المتأخرات: {len(pending)} · الدفعات: {len(batches)} · الملف: {a.out}")
    print("  الأرقام: " + " ".join(p["id"] for p in pending))
    return 0


if __name__ == "__main__":
    sys.exit(main())
