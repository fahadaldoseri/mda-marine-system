#!/usr/bin/env python3
"""بناء فهرس آلي لسجل الأعطال من جدول مختلط المخطط، بلا إعادة كتابة الملف الأصلي.

يقرأ الصفوف التي تبدأ بـ «| ك-»، ويصنّف كل صف إلى مخططه (تاريخ-أولًا أو موروث)،
ثم يكتب فهرسًا JSONL يمكن لأدوات التحقق والتقارير قراءته بثقة.
"""
import argparse, json, re, sys
from pathlib import Path

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CLOSED = ("مغلق", "closed", "اغلق", "done", "تم", "مكتمل", "مكتملة", "ثبت", "منجز", "verified")
DIAC = dict.fromkeys(map(ord, "\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652\u0640"), None)


def parse(line):
    f = [c.strip() for c in line.strip().strip("|").split("|")]
    if not f or not f[0].startswith("ك-"):
        return None
    rec = {"id": f[0]}
    if len(f) > 1 and DATE.match(f[1]):
        rec.update(layout="date-first", date=f[1],
                   axis=f[2] if len(f) > 2 else "",
                   symptom=f[3] if len(f) > 3 else "",
                   cause=f[4] if len(f) > 4 else "",
                   fix_status=(f[5] if len(f) > 5 else "") + " " + (f[6] if len(f) > 6 else ""))
    else:
        rec.update(layout="legacy", date="",
                   surface=f[1] if len(f) > 1 else "",
                   area=f[2] if len(f) > 2 else "",
                   symptom=f[3] if len(f) > 3 else "",
                   cause="",
                   fix_status=f[4] if len(f) > 4 else "",
                   status_tail=f[5] if len(f) > 5 else "")
    tail = (rec.get("fix_status", "") + " " + rec.get("status_tail", "")).translate(DIAC)
    rec["closed"] = "مُغلق" in rec.get("fix_status","") or any(m in tail for m in CLOSED)
    rec["fields"] = len(f)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faults", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows, bad = [], 0
    for line in Path(a.faults).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ك-"):
            continue
        r = parse(line)
        if r:
            rows.append(r)
        else:
            bad += 1
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with Path(a.out).open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    layouts = {}
    for r in rows:
        layouts[r["layout"]] = layouts.get(r["layout"], 0) + 1
    closed = sum(1 for r in rows if r["closed"])
    print(f"  الصفوف: {len(rows)} · الأسطر غير القابلة للقراءة: {bad}")
    print(f"  المخططات: {layouts} · المُغلق: {closed} · المفتوح: {len(rows) - closed}")
    print(f"  ✔ الفهرس: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
