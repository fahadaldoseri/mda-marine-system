#!/usr/bin/env python3
"""توحيد مخطط سجل التعلم: قراءة الأسماء البديلة للحقول وإعادة كتابة كل مدخل بالمخطط القياسي.

ينسخ الملف الأصلي إلى <ملف>.bak قبل أي كتابة، ويدعم --dry للتشخيص فقط.
"""
import argparse, json, shutil, sys
from pathlib import Path

ALIAS = {"surface": ("surface", "area", "component", "module", "scope", "target"),
         "symptom": ("symptom", "defect", "issue", "problem", "finding", "observation", "error"),
         "cause": ("cause", "root_cause", "reason", "diagnosis", "root"),
         "action": ("action", "hardening", "lesson", "fix", "rule", "prevention", "gate"),
         "evidence": ("evidence", "proof", "verification", "evidence_detail"),
         "cls": ("cls", "class", "type", "category")}
CANON = ("date", "surface", "symptom", "cause", "cls", "action", "evidence")


def pick(e, key):
    for k in ALIAS[key]:
        if e.get(k):
            return str(e[k]).strip()
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--learning", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    p = Path(a.learning)
    out, stats = [], {"total": 0, "unified": 0, "legacy": 0, "bad": 0}
    for l in p.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        stats["total"] += 1
        try:
            e = json.loads(l)
        except Exception:
            stats["bad"] += 1
            out.append(l)
            continue
        rec = {"date": str(e.get("date", "")).strip()}
        for k in ("surface", "symptom", "cause", "cls", "action", "evidence"):
            rec[k] = pick(e, k)
        if all(rec[k] for k in ("surface", "symptom", "cause", "action")):
            stats["unified"] += 1
        else:
            rec["legacy"] = True
            stats["legacy"] += 1
        out.append(json.dumps(rec, ensure_ascii=False))

    print(f"  المدخلات: {stats['total']} · مكتملة بعد التوحيد: {stats['unified']}"
          f" · موروثة ناقصة: {stats['legacy']} · أسطر تالفة: {stats['bad']}")
    if a.dry:
        print("  (تشخيص فقط — لم يُكتب شيء)")
        return 0
    shutil.copy2(p, str(p) + ".bak")
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"  ✔ وُحّد المخطط · نسخة احتياطية: {p}.bak")
    return 0


if __name__ == "__main__":
    sys.exit(main())
