#!/usr/bin/env python3
"""تسجيل عطل لغوي/حارس واقتراح تشديد يمنع تكراره — حلقة التعلم الذاتي.

يُلحق مدخلًا في سجل التعلم (JSONL) ويطبع قائمة تشديد مقترحة بحسب نوع السبب.
لا يُغلق عطل قبل أن يقابله منع آلي أو قاعدة مكتوبة.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

HARDENING = {
    "scope": "ضمّ المنشئ/البنّاء إلى نطاق المرشّح، ووسّع قائمة الأسطح لتشمل المخرجات المشتقة.",
    "self_block": "امنع الكتابة على ملفّي الحُكم، وأضف فحصًا تقاطعيًا: term لا يساوي أي plain.",
    "derived": "ابنِ السطح المشتق من مصدره لحظة الفحص بدل قراءة ملف مخزَّن.",
    "extraction": "طبّع النص المشتق (NFKC + إزالة الكشيدة وعلامات الاتجاه + تصحيح مواضع الترقيم).",
    "attestation": "احكم على PDF بالإسناد (رموز البلاغ والمصطلحات اللاتينية) لا بتشابه النص.",
    "registry": "كل بند يحتاج plain غير فارغ وterm != plain، وحالة معتمدة تحتاج reason وsince.",
    "other": "حوّل العطل إلى فحص آلي داخل بوابة التسليم قبل إغلاقه.",
}


def classify(cause: str) -> str:
    c = cause.lower()
    if any(k in c for k in ("نطاق", "scope", "بنّاء", "builder", "tools")):
        return "scope"
    if any(k in c for k in ("حُكم", "حكم", "self", "تضارب", "بديل")):
        return "self_block"
    if any(k in c for k in ("مشتق", "derived", "تلغرام", "digest")):
        return "derived"
    if any(k in c for k in ("استخراج", "extract", "pdf", "مسافات", "كشيدة")):
        return "extraction"
    if any(k in c for k in ("إسناد", "attest")):
        return "attestation"
    if any(k in c for k in ("سجل", "registry", "plain", "status")):
        return "registry"
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser(description="تسجيل عطل وتشديد مقترح")
    ap.add_argument("--log", required=True, help="سجل التعلم JSONL")
    ap.add_argument("--surface", required=True)
    ap.add_argument("--symptom", required=True)
    ap.add_argument("--cause", required=True)
    ap.add_argument("--action", required=True, help="التشديد الذي يمنع التكرار")
    ap.add_argument("--evidence", default="", help="الأمر ومخرجه")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()

    kind = classify(a.cause)
    rec = {"date": a.date, "surface": a.surface, "symptom": a.symptom, "cause": a.cause,
           "action": a.action, "evidence": a.evidence, "class": kind,
           "hardening": HARDENING[kind]}
    p = Path(a.log)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  ✔ سُجل العطل في {p} (التصنيف: {kind})")
    print(f"  → تشديد مقترح: {HARDENING[kind]}")
    print("  → لا يُغلق العطل قبل ربط التشديد ببوابة التسليم وإثباته بتشغيل حي.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
