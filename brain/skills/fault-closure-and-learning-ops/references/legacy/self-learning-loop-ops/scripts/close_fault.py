#!/usr/bin/env python3
"""إغلاق عطل: كتابة صف في سجل الأعطال + مدخل في سجل التعلم + طباعة التشديد المقترح."""
import argparse, json, re, sys
from pathlib import Path

HARDENING = {
    "scope": "وسّع نطاق الأداة ليغطي كل الأسطح (المحتوى · البنّاءات · القوالب)، وأضف فحصًا يمنع أي سطح خارج التغطية.",
    "gate-semantics": "ارفع الحكم من تحذير إلى مانع، واجعل شرط الإغلاق صريحًا في البوابة.",
    "derivation": "أعِد بناء المخرَج المشتق قبل الفحص، واستعمل تطبيعًا أو دليلًا بديلًا للقياس.",
    "schema": "أضف تحقق مخطط يمنع البناء عند حقل فارغ أو متعارض.",
    "dependency": "قيّد التبعية كحدّ مخطط، وأفصح للقارئ بدل تجاوز الحماية.",
    "data": "اجعل لكل رقم مصدر حقيقة واحدًا، وأضف فحص تناسق العدّادات.",
    "process": "انقل الخطوة إلى المخطط وامنع تنفيذها يدويًا أو بترتيب مخالف.",
}


def next_id(text):
    ids = [int(m.group(1)) for m in re.finditer(r"ك-(\d+)", text)]
    return f"ك-{max(ids)+1}" if ids else "ك-1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faults", required=True)
    ap.add_argument("--learning", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--class", dest="cls", required=True, choices=sorted(HARDENING))
    for k in ("surface", "symptom", "cause", "fix", "action", "evidence"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--status", default="مغلق")
    ap.add_argument("--id", dest="fid")
    ap.add_argument("--force", action="store_true", help="اسجّل حتى لو وُجد عَرَض مطابق بالتاريخ نفسه")
    a = ap.parse_args()

    fp, lp = Path(a.faults), Path(a.learning)
    for p in (fp, lp):
        if not p.exists():
            print(f"  ✘ الملف غير موجود: {p}"); return 2
    ftext = fp.read_text(encoding="utf-8")
    rows = [l for l in ftext.splitlines() if l.startswith("| ك-")]
    if not a.force and any(a.symptom[:40] in r and a.date in r for r in rows):
        print("  ✘ عَرَض مطابق بالتاريخ نفسه مسجَّل مسبقًا (استخدم --force للتسجيل صريحًا)"); return 1

    fid = a.fid or next_id(ftext)
    ncols = len([c for c in rows[-1].split("|")[1:-1]]) if rows else 7
    vals = [fid, a.date, a.cls, a.symptom, a.cause, f"{a.fix} — {a.status}"]
    vals = vals[:ncols] + [""] * max(0, ncols - len(vals))
    row = "| " + " | ".join(v.replace("|", "/") for v in vals) + " |"
    if not ftext.endswith("\n"):
        ftext += "\n"
    fp.write_text(ftext + row + "\n", encoding="utf-8")

    entry = {"date": a.date, "surface": a.surface, "symptom": a.symptom, "cause": a.cause,
             "cls": a.cls, "action": a.action, "evidence": a.evidence}
    with lp.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"  ✔ صف العطل: {fid} ({a.cls}) في {fp}")
    print(f"  ✔ مدخل التعلم في {lp}")
    print(f"  → تشديد مقترح: {HARDENING[a.cls]}")
    print("  → لا يُغلق العطل قبل اختبار التشديد بمحاولة كسر متعمَّدة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
