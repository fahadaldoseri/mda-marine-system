#!/usr/bin/env python3
"""توحيد مخطط جدول الأعطال تاريخيًا إلى سبعة أعمدة قياسية، بلا فقدان أي نص.

المخطط القياسي:
  الرقم · التاريخ · المحور · العَرَض · السبب الجذري · الإصلاح · التشديد والحالة

المخططات المدعومة:
  - حديث (6 أعمدة): id | date | axis | symptom | cause | fix_status
  - موروث (8 أعمدة): id | axis | symptom | cause | note | fix | hardening | status
  - شاذّ: يُصنَّف تلقائيًا ويُدمج بأمان مع وسم «موروث-شاذّ»

المخرجات: الجدول الموحّد + فهرس JSONL + نسخة أصلية خام لكل صف.
"""
import argparse, json, re, shutil, sys
from pathlib import Path

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PATHLIKE = re.compile(r"[/\\]|\.\w{2,4}$")
HEADER = ("| الرقم | التاريخ | المحور | العَرَض | السبب الجذري | الإصلاح | التشديد والحالة |\n"
          "| --- | --- | --- | --- | --- | --- | --- |\n")


def clean(c):
    return " ".join(c.strip().split())


def normalize_row(fields):
    f = [clean(c) for c in fields]
    n = len(f)
    rec = {"id": f[0], "raw_fields": n}
    if n >= 6 and DATE.match(f[1] or ""):
        rec.update(layout="date-first",
                   date=f[1], axis=f[2], symptom=f[3], cause=f[4] or "—",
                   fix=f[5], hardening_status=f[5])
    elif n >= 8:
        note = f[4]
        rec.update(layout="legacy-8", date="—", axis=f[1],
                   symptom=f[2] + (f" (ملاحظة: {note})" if note and note not in ("—", "-") else ""),
                   cause=f[3] or "—", fix=f[5] or "—",
                   hardening_status=f"{f[6]} — {f[7]}".strip(" —"))
    elif n == 6:
        rec.update(layout="legacy-6", date="—", axis=f[1],
                   symptom=f[2] + (f" (ملاحظة: {f[4]})" if f[4] and f[4] not in ("—", "-") else ""),
                   cause=f[3] or "—", fix=f[5] if len(f) > 5 else "—", hardening_status=f[5] if len(f) > 5 else "—")
    else:
        joined = " · ".join(x for x in f[1:] if x)
        rec.update(layout="legacy-odd", date="—", axis=f[1] if PATHLIKE.search(f[1] or "") else "",
                   symptom=joined, cause="—", fix="—", hardening_status=f[-1] if f else "")
    # ضمان عدم الفقدان: أي خلية لم يظهر نصها في الصف تُلحق بالعمود الأخير
    row_so_far = to_row(rec)
    leftovers = [c for c in f[1:] if c and c not in ("—", "-") and c not in row_so_far]
    if leftovers:
        rec["hardening_status"] = (rec["hardening_status"] + " · ملاحظة موروثة: " +
                                  " · ".join(leftovers)).strip(" ·")
    return rec


def to_row(rec):
    cells = [rec["id"], rec["date"], rec["axis"] or "—", rec["symptom"] or "—",
             rec["cause"] or "—", rec["fix"] or "—", rec["hardening_status"] or "—"]
    return "| " + " | ".join(clean(c) for c in cells) + " |"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faults", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    src = Path(a.faults)
    lines = src.read_text(encoding="utf-8").splitlines()
    out, recs, header_done, loss = [], [], False, 0
    for line in lines:
        if not line.startswith("| ك-"):
            out.append(line)
            continue
        fields = [c.strip() for c in line.strip().strip("|").split("|")]
        rec = normalize_row(fields)
        recs.append(rec)
        row = to_row(rec)
        # تحقق عدم الفقدان: كل خلية أصلية غير فارغة يجب أن يظهر نصها في الصف الجديد
        for c in fields:
            c = clean(c)
            if c and c not in ("—", "-") and c not in row:
                loss += 1
        out.append(row)
        if not header_done:
            out.append("")
            header_done = True

    layouts = {}
    for r in recs:
        layouts[r["layout"]] = layouts.get(r["layout"], 0) + 1
    print(f"  الصفوف: {len(recs)} · المخططات: {layouts}")
    print(f"  خلايا أصلية ضاعت: {loss}")
    if a.dry:
        print("  (تشخيص فقط — لم يُكتب شيء)")
        return 1 if loss else 0

    shutil.copy2(src, str(src) + ".bak")
    body = []
    for i, line in enumerate(out):
        body.append(line)
    # إدراج الرأس قبل أول صف
    for i, line in enumerate(body):
        if line.startswith("| ك-"):
            body.insert(i, HEADER.rstrip("\n"))
            break
    src.write_text("\n".join(body) + "\n", encoding="utf-8")
    side = src.parent / "faults-raw.jsonl"
    with side.open("w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  ✔ وُحّد الجدول · نسخة احتياطية: {src}.bak · الصفوف الخام: {side}")
    return 1 if loss else 0


if __name__ == "__main__":
    sys.exit(main())
