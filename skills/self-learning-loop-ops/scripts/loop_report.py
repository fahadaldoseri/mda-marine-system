#!/usr/bin/env python3
"""عرض آخر حلقات التعلم: يجمع صفوف الأعطال مع مدخلات التعلم ويرتّبهما زمنيًا."""
import argparse, json, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faults", required=True)
    ap.add_argument("--learning", required=True)
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--out", help="ملف Markdown للمخرَج")
    a = ap.parse_args()

    rows = [l for l in Path(a.faults).read_text(encoding="utf-8").splitlines() if l.startswith("| ك-")]
    rows = rows[-a.limit:]
    entries = []
    for l in Path(a.learning).read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                entries.append(json.loads(l))
            except Exception:
                pass

    out = [f"# آخر {len(rows)} حلقات تعلم", ""]
    for r in rows:
        cols = [c.strip() for c in r.split("|")[1:-1]]
        fid, date, cls = (cols + ["", "", ""])[:3]
        sym, cause, fix = (cols + ["", "", "", ""])[3:6]
        out += [f"## {fid} · {date} · {cls}", "",
                f"- العَرَض: {sym}", f"- السبب الجذري: {cause}", f"- الإصلاح: {fix}"]
        def v(e, *keys):
            for k in keys:
                if e.get(k):
                    return str(e[k])
            return ""
        same = [e for e in entries if e.get("date") == date]
        sym_ok = [e for e in same if sym and v(e, "symptom", "defect", "issue")[:12] == sym[:12]]
        m = sym_ok
        weak = False
        if not m:
            m = same
            weak = True
        for e in m[-2:]:
            act = e.get("action") or e.get("hardening") or e.get("lesson") or e.get("fix") or ""
            ev = e.get("evidence") or e.get("proof") or e.get("verification") or ""
            tag = "" if e.get("action") else " (موروث)"
            if weak:
                out += ["- ⚠ لا درس مطابق بالعَرَض — الموجود مدخلات اليوم نفسها (لا تُنسب إليه)"]
                break
            out += [f"- الدرس{tag}: {act}", f"- الدليل: {ev}"]
        if not m:
            out += ["- ⚠ لا مدخل تعلم مطابق"]
        out.append("")
    text = "\n".join(out)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"  ✔ التقرير: {a.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
