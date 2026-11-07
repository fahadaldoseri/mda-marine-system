#!/usr/bin/env python3
"""تقرير حالة شامل للسجلات والقوائم المعتمدة — بعد أي إغلاق حارس.

يمسح مجلدات مشروع، ويُخرج لكل ملف: النوع · عدد البنود · توزيع الحالات · البصمة (sha256) ·
آخر تعديل. ويُنشئ ملف Markdown وأخرى Excel إن توفّرت openpyxl.

الاستعمال:
  python3 status_report.py --scan brain/appendices brain/memory --out حالة-السجلات.md \
      --title "حالة السجلات بعد إغلاق الحارس" --xlsx حالة-السجلات.xlsx
"""
from __future__ import annotations

import argparse
import hashlib
import json
import datetime as dt
from collections import Counter
from pathlib import Path

SKIP = {"__pycache__", ".git", "node_modules"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def entries_of(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("entries", "items", "terms", "words", "codes", "sources", "records"):
            if isinstance(obj.get(k), list):
                return obj[k]
    return None


def describe(p: Path) -> dict:
    row = {"file": str(p), "kind": p.suffix.lstrip(".").lower(), "items": None,
           "statuses": "", "sha256": sha(p)[:16], "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
    if p.suffix.lower() == ".json":
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            items = entries_of(obj)
            if items is not None:
                row["items"] = len(items)
                st = Counter(str(e.get("status") or e.get("state") or "") for e in items if isinstance(e, dict))
                row["statuses"] = " · ".join(f"{k}:{v}" for k, v in st.most_common() if k)
            elif isinstance(obj, dict):
                row["items"] = len(obj)
                row["statuses"] = "مفاتيح: " + ", ".join(list(obj)[:6])
        except Exception as e:  # ملف JSON غير صالح: يُذكر السبب ولا يُسكت
            row["statuses"] = f"تعذّر القراءة: {type(e).__name__}"
    elif p.suffix.lower() == ".jsonl":
        n = sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))
        row["items"] = n
    elif p.suffix.lower() == ".md":
        t = p.read_text(encoding="utf-8", errors="ignore")
        row["items"] = t.count("\n| ك-") or t.count("\n|")
        row["statuses"] = f"{len(t.splitlines())} سطرًا"
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="تقرير حالة السجلات والقوائم")
    ap.add_argument("--scan", nargs="+", required=True)
    ap.add_argument("--out", required=True, help="ملف Markdown")
    ap.add_argument("--xlsx", default="", help="ملف Excel اختياري")
    ap.add_argument("--title", default="حالة السجلات والقوائم المعتمدة")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()

    rows: list[dict] = []
    for d in a.scan:
        root = Path(d)
        if root.is_file():
            rows.append(describe(root)); continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or any(x in p.parts for x in SKIP):
                continue
            if p.suffix.lower() in (".json", ".jsonl", ".md", ".csv"):
                rows.append(describe(p))

    lines = [f"# {a.title}", "", f"- التاريخ: {a.date}", f"- المجلدات الممسوحة: {' · '.join(a.scan)}",
             f"- عدد الملفات: {len(rows)}", "",
             "| الملف | النوع | عدد البنود | توزيع الحالات | بصمة (16) | آخر تعديل |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| `{r['file']}` | {r['kind']} | {r['items'] if r['items'] is not None else '—'} | {r['statuses']} | `{r['sha256']}` | {r['mtime']} |")
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  ✔ التقرير: {a.out} · {len(rows)} ملفًا")

    if a.xlsx:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font
            wb = Workbook(); ws = wb.active; ws.title = "حالة السجلات"; ws.sheet_view.rightToLeft = True
            hdr = ["الملف", "النوع", "عدد البنود", "توزيع الحالات", "بصمة (16)", "آخر تعديل"]
            ws.append(hdr)
            for c in ws[1]:
                c.font = Font(bold=True); c.alignment = Alignment(horizontal="center")
            for r in rows:
                ws.append([r["file"], r["kind"], r["items"], r["statuses"], r["sha256"], r["mtime"]])
            for col, w in zip("ABCDEF", (58, 8, 11, 34, 20, 18)):
                ws.column_dimensions[col].width = w
            wb.save(a.xlsx); print(f"  ✔ الإكسل: {a.xlsx}")
        except ImportError:
            print("  — openpyxl غير مثبّتة: أُنتج Markdown فقط")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
