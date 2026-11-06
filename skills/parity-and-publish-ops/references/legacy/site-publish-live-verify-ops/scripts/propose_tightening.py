#!/usr/bin/env python3
"""استخرج أصناف الثغرات من JSONL واقترح اختبارات سلبية وتشديدات."""
from __future__ import annotations
import argparse, json, os, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
DEFAULT_BRAIN = Path(os.environ.get("BRAIN_DIR", str(SKILL / "../../brain-marine-news"))).resolve()
RULES = [
    ("التوصيل والنشر", ("delivery", "publish", "live", "انتشار", "نشر", "دفع", "توصيل"),
     "أثبت commit المشروع ثم قرار النشر، وقِس ظهور المؤشر الحي بدل الاكتفاء برمز HTTP.",
     "شغّل فحصًا على نشر قديم يرد 200 وتحقق من أنه يخرج 2 ولا يعلن نجاحًا."),
    ("الأسطح والمسارات", ("surface", "route", "path", "صفحة", "سطح", "مسار", "إضافات"),
     "ثبّت مصفوفة المسارات والعناوين المطلوبة لكل سطح، وارفض النقص والتكرار والحضور في السطح الخطأ.",
     "احذف مسارًا أو انقل عنوانًا إلى السطح القديم في نسخة مؤقتة وتحقق من فشل البوابة."),
    ("المقارنة والتماثل", ("parity", "compare", "diff", "تماثل", "انحراف", "بصمة", "hash"),
     "قارن بصمات الملفات المحلية والحيّة وسجّل أول فرق، ولا تعتبر 200 دليلًا على النسخة الجديدة.",
     "بدّل ملفًا محليًا أو اختبر استجابة قديمة وتحقق من تسجيل diff وخروج 2."),
    ("قابلية النقل", ("portable", "absolute", "مسار", "محمول", "مطلق"),
     "استنتج الجذور من الملف أو اقبل --brain و--site و--date، واختبر تشغيلًا خارج المسارات الأصلية.",
     "شغّل السكربت من مجلد مؤقت مع جذور صريحة وتحقق من عدم استعمال مسار ثابت."),
    ("الطباعة والـPDF", ("pdf", "print", "طباعة", "PDF", "ورق"),
     "اربط سياسة الإخفاء بالطباعة، وافحص ظهور العناوين المنقولة وغيابها من PDF بعد إعادة البناء.",
     "ضع عنوانًا منقولًا في PDF أو استخدم PDF قديمًا وتحقق من أن الفحص يميز الحالة ولا يخفيها."),
    ("التحقق والتشغيل", ("gate", "verify", "test", "بوابة", "تحقق", "اختبار", "فحص"),
     "شغّل كل خطوة على مخرج مبني حديثًا، وسجّل رمز الخروج والسبب الجذري، واجعل الفشل مغلقًا.",
     "أدخل ملفًا ناقصًا أو خطوة بعد exit وتحقق من أن الاختبار السلبي يوقف السلسلة."),
]

def files_from_args(args):
    if args.fault_log:
        return [Path(x).expanduser() for x in args.fault_log]
    audit = DEFAULT_BRAIN / "audit"
    return sorted(audit.glob("faults*.jsonl"))

def records(paths):
    for p in paths:
        if not p.is_file():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            try:
                obj=json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                obj["_file"]=str(p); obj["_line"]=n; yield obj

def classify(obj):
    hay=" ".join(str(obj.get(k, "")) for k in ("area","axis","surface","symptom","cause","fix_status","status_tail")).lower()
    hits=[]
    for label, words, _, _ in RULES:
        if any(w.lower() in hay for w in words): hits.append(label)
    return hits or ["عام"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--brain", default=str(DEFAULT_BRAIN))
    ap.add_argument("--fault-log", action="append")
    ap.add_argument("--output", default=str(SKILL/"references/proposed-tightening.md"))
    a=ap.parse_args()
    paths=files_from_args(a)
    rows=list(records(paths)); counts=Counter(c for r in rows for c in classify(r))
    lines=["# مخرج propose_tightening", "", f"- وقت الاستخراج {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
           f"- السجلات المقروءة {', '.join(map(str, paths)) or 'لا يوجد'}", f"- السجلات الصالحة {len(rows)}", "",
           "| الصنف | العدد | التشديد المقترح | الاختبار السلبي |", "|---|---:|---|---|"]
    for label, _, harden, negative in RULES:
        lines.append(f"| {label} | {counts.get(label, 0)} | {harden} | {negative} |")
    if counts.get("عام"):
        lines.append(f"| عام | {counts['عام']} | أضف سببًا جذريًا وقاعدة واختبارًا قبل إغلاق أي سجل. | أدخل سجلًا بلا صنف وتحقق من ظهوره للمراجعة. |")
    lines += ["", "## أدلة الاستخراج", "", "لا تُنسخ السجلات إلى المهارة؛ تُستخدم هذه الخلاصة لتحديد الاختبار السلبي التالي."]
    out=Path(a.output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print("\n".join(lines))
    return 0
if __name__ == "__main__": raise SystemExit(main())
