#!/usr/bin/env python3
"""بوابة سطح «إضافات» (ك-234).

تُثبت حيًّا:
- كل عنوان في required_in_additions يظهر مرة واحدة في dist/additions.html
- لا يظهر أي منها في سطح التقرير اليومي
- كل عنوان في required_in_report حاضر في سطح التقرير اليومي
- لا تناقض في السياسة (عنوان مطلوب في التقرير ومخفي معًا)

الفشل مغلق: أي نقص أو تكرار أو حضور في السطح الخطأ ⇒ رمز 2.

الاستعمال: python3 validators/check_additions_surface.py [--date YYYY-MM-DD] [--site /home/ubuntu/seawatch]
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

BRAIN = Path(__file__).resolve().parent.parent


def load_policy() -> dict:
    for c in (BRAIN / "appendices" / "report-sections-policy.json",
              BRAIN / "sources" / "report-sections-policy.json"):
        if c.is_file():
            return json.loads(c.read_text(encoding="utf-8"))
    raise SystemExit("لم تُعثر سياسة الأقسام")


def headings(p: Path) -> list:
    if not p.is_file():
        return []
    t = p.read_text(encoding="utf-8")
    return [html.unescape(re.sub(r"<[^>]+>", "", x).strip())
            for x in re.findall(r"<h2[^>]*>(.*?)</h2>", t, re.S)]


def emit(errs, warns, n_add_head, n_req) -> int:
    print(f"سطح إضافات: {n_add_head} عنوانًا · المطلوب نقله: {n_req}")
    for w in warns:
        print("  ! " + w)
    if errs:
        for e in errs:
            print("  × " + e)
        print("النتيجة: مخالف — سطح «إضافات» لا يطابق السياسة (فشل مغلق)")
        return 2
    print("  ✓ العناوين المنقولة مرة واحدة في صفحتها · ولا واحد منها في سطح التقرير · والمطلوب في التقرير حاضر")
    print("النتيجة: مطابق")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--site", default="/home/ubuntu/seawatch")
    a = ap.parse_args()
    dist = Path(a.site) / "dist"
    pol = load_policy()
    adds = list(pol.get("required_in_additions") or pol.get("additions_sections") or [])
    hidden = set(pol.get("hidden_sections") or [])
    req = list(pol.get("required_in_report") or [])
    errs, warns = [], []

    clash = sorted(set(req) & hidden)
    if clash:
        errs.append("سياسة متناقضة: " + " · ".join(clash) + " مطلوبة في التقرير ومخفية معًا")
    if not adds:
        errs.append("السياسة بلا required_in_additions — لا يمكن فحص سطح «إضافات»")
        return emit(errs, warns, 0, 0)

    add_file = dist / "additions.html"
    if not add_file.is_file():
        errs.append(f"صفحة «إضافات» غير مبنية: {add_file}")
        return emit(errs, warns, 0, len(adds))

    add_head = headings(add_file)
    for t in adds:
        n = sum(1 for h in add_head if t in h)
        if n == 0:
            errs.append(f"عنوان منقول غائب عن صفحة إضافات: «{t}»")
        elif n > 1:
            errs.append(f"عنوان منقول مكرر {n} مرات في صفحة إضافات: «{t}»")

    rep_date = a.date
    if not rep_date:
        mds = sorted((BRAIN / "reports").glob("*-sectioned.md"))
        rep_date = mds[-1].name.replace("-sectioned.md", "") if mds else ""
    rep = dist / "reports" / f"{rep_date}.html" if rep_date else None
    if rep is not None and not rep.is_file():
        errs.append(f"صفحة التقرير غير مبنية: {rep}")
    elif rep is not None:
        rh = headings(rep)
        for t in adds:
            if any(t in h for h in rh):
                errs.append(f"عنوان منقول ما زال ظاهرًا في سطح التقرير اليومي: «{t}»")
        for t in req:
            if not any(t in h for h in rh):
                errs.append(f"عنوان مطلوب في التقرير غائب: «{t}»")

    extra = [h for h in add_head if not any(t in h for t in adds)]
    if extra:
        warns.append("عناوين إضافية في صفحة إضافات خارج السياسة: " + " · ".join(extra[:4]))
    return emit(errs, warns, len(add_head), len(adds))


if __name__ == "__main__":
    sys.exit(main())
