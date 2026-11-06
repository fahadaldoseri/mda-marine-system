#!/usr/bin/env python3
"""التحقق من إغلاق حلقة التعلم: كل عطل حديث مُغلق له درس وتشديد، والموروث يُحصى منفصلًا."""
import argparse, json, sys
from pathlib import Path

ALIAS = {"surface": ("surface", "area", "component", "module", "scope", "target"),
         "symptom": ("symptom", "defect", "issue", "problem", "finding", "observation", "error"),
         "cause": ("cause", "root_cause", "reason", "diagnosis", "root"),
         "action": ("action", "hardening", "lesson", "fix", "rule", "prevention", "gate"),
         "evidence": ("evidence", "proof", "verification", "evidence_detail"),
         "cls": ("cls", "class", "type", "category")}
CLOSED = ("مغلق", "closed", "أُغلق", "done", "تم", "مكتمل", "أُثبت", "منجز")


def val(e, key):
    for k in ALIAS[key]:
        if e.get(k):
            return str(e[k])
    return ""


def load_index(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faults", required=True)
    ap.add_argument("--learning", required=True)
    ap.add_argument("--index", help="فهرس الأعطال الموحّد (يُبنى بـ build_fault_index.py)")
    ap.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()

    rows = load_index(a.index) if a.index else None
    if rows is None:
        bad = [l for l in Path(a.faults).read_text(encoding="utf-8").splitlines() if l.startswith("| ك-")]
        rows = [{"id": l.split("|")[1].strip(), "layout": "unknown", "date": "",
                 "axis": "", "symptom": l.split("|")[4].strip() if l.count("|") > 4 else "",
                 "fix_status": l.split("|")[-2].strip(), "closed": any(c in l for c in CLOSED)} for l in bad]

    bad_lines, entries = [], []
    for i, l in enumerate(Path(a.learning).read_text(encoding="utf-8").splitlines(), 1):
        if not l.strip():
            continue
        try:
            entries.append(json.loads(l))
        except Exception as e:
            bad_lines.append((i, str(e)[:50]))

    modern = [r for r in rows if r.get("date")][-a.limit:]
    legacy = [r for r in rows if not r.get("date")]
    problems = []
    for r in modern:
        date, sym, cls = r.get("date", ""), r.get("symptom", ""), r.get("axis", "")
        same = [e for e in entries if e.get("date") == date]
        sym_ok = [e for e in same if sym and val(e, "symptom")[:12] == sym[:12]]
        cls_ok = [e for e in same if val(e, "cls") == cls]
        match = sym_ok or cls_ok or same
        if r.get("closed") and not match:
            problems.append(f"{r['id']}: مُغلق بلا مدخل تعلم في {date}")
        elif r.get("closed") and match and not val(match[-1], "action"):
            problems.append(f"{r['id']}: مدخل التعلم بلا تشديد مسجَّل")
        elif not r.get("closed") and match:
            problems.append(f"{r['id']}: ما زال مفتوحًا مع وجود درس — حدّث حالته")

    print(f"  الأعطال: {len(rows)} (حديثة مفحوصة {len(modern)} · موروثة بلا تاريخ {len(legacy)})"
          f" · مدخلات التعلم: {len(entries)}"
          f" · مدخلات موروثة ناقصة: {sum(1 for e in entries if not val(e,'symptom'))}")
    for ln, err in bad_lines[:3]:
        print(f"  ✘ سطر JSON غير صالح: {ln} — {err}")
    for p in problems:
        print(f"  ✘ {p}")
    if not problems and not bad_lines:
        print("  ✓ الحلقة مغلقة: كل عطل حديث مُغلق له درس وتشديد")
    else:
        print("  ✗ الحلقة غير مغلقة على الأعطال الحديثة")
    print(f"  ملاحظة: الموروثة ({len(legacy)}) تحتاج توحيدًا تاريخيًا — لا تُحسب فشلًا الآن.")
    return 0 if not problems and not bad_lines else 1


if __name__ == "__main__":
    sys.exit(main())
