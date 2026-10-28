#!/usr/bin/env python3
"""توحيد مخطط سجل التعلم بلا فقدان أي نص: يضيف الحقول القياسية ويُبقي المفاتيح الأصلية كلها.

القياسي: date · surface · symptom · cause · cls · action · evidence
يُقرأ من الأسماء البديلة (عربية وإنجليزية)، ويُوسم kind بحسب نوع المدخل:
  lesson (درس عطل) · vocabulary (قرار مفردات) · gate (سجل بوابة/تشغيل) · other
"""
import argparse, json, shutil, sys
from pathlib import Path

ALIAS = {
    "surface": ("surface", "area", "code", "scope", "component", "module", "target", "الموضع", "السطح"),
    "symptom": ("symptom", "trigger", "fault", "defect", "issue", "problem", "finding", "العَرَض", "العرض"),
    "cause": ("cause", "root_cause", "reason", "diagnosis", "root", "السبب", "السبب الجذري"),
    "cls": ("cls", "class", "type", "category", "classification", "التصنيف"),
    "action": ("action", "hardening", "barrier", "lesson", "fix", "rule", "prevention", "التشديد", "الدرس", "الإصلاح"),
    "evidence": ("evidence", "proof", "verification", "replacement", "report_sha16", "الدليل"),
}
VOCAB_KEYS = ("lesson_id", "replacement", "origin")


def pick(e, key):
    for k in ALIAS[key]:
        v = e.get(k)
        if v not in (None, "", [], {}):
            return str(v).strip()
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--learning", required=True)
    ap.add_argument("--source", help="الملف الأصلي (افتراضيًا النسخة الاحتياطية .bak)")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    p = Path(a.learning)
    src = Path(a.source) if a.source else Path(str(p) + ".bak")
    if not src.exists():
        print(f"  ✘ لا يوجد ملف مصدر: {src}")
        return 2
    original = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    current = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []

    def key(e):
        return (e.get("date", ""), (e.get("symptom") or e.get("trigger") or e.get("fault") or "")[:25])

    known = {key(e) for e in original}
    extra = [e for e in current if key(e) not in known]

    out, stats, lost = [], {"lesson": 0, "vocabulary": 0, "gate": 0, "other": 0}, 0
    for e in original + extra:
        rec = dict(e)  # إبقاء كل المفاتيح الأصلية
        for k in ("surface", "symptom", "cause", "cls", "action", "evidence"):
            v = pick(rec, k)
            if v:
                rec.setdefault(k, v)
        if any(rec.get(k) for k in VOCAB_KEYS) and not rec.get("symptom"):
            rec["entry_kind"] = "vocabulary"
        elif rec.get("gate_status") or rec.get("steps") or rec.get("skill"):
            rec["entry_kind"] = "gate"
        elif rec.get("symptom") and rec.get("cause"):
            rec["entry_kind"] = "lesson"
        else:
            rec["entry_kind"] = "other"
        stats[rec["entry_kind"]] = stats.get(rec["entry_kind"], 0) + 1
        out.append(rec)
        for k, v in e.items():  # تحقق: لا قيمة أصلية غابت
            if v not in (None, "", [], {}) and rec.get(k) != v:
                lost += 1

    print(f"  الأسطر: {len(out)} (أصلية {len(original)} + مستجدة {len(extra)})")
    print(f"  الأنواع: {stats}")
    print(f"  قيم أصلية غابت: {lost}")
    incomplete = sum(1 for e in out if e["entry_kind"] == "lesson" and not (e.get("symptom") and e.get("cause") and e.get("action")))
    print(f"  دروس ناقصة (سبب أو تشديد): {incomplete}")
    if a.dry:
        print("  (تشخيص فقط — لم يُكتب شيء)")
        return 1 if lost else 0

    shutil.copy2(p, str(p) + ".pre-unify") if p.exists() else None
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    print(f"  ✔ وُحّد السجل بحفظ النص · نسخة: {p}.pre-unify")
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
