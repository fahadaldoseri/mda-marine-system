#!/usr/bin/env python3
"""بصمة الأرقام — كل رقم معروض للقارئ مع سياقه وموضعه.

الغاية: كشف أربعة أنواع خطأ لا يكشفها غيرها — رقم تغيّر بلا سبب · رقم ظهر بلا مصدر ·
رقم اختفى · رقم انتقل من قسم إلى آخر.

الاستعمال:
  number_fingerprint.py --date 2026-11-05          يبني بصمة اليوم في logs/fingerprints/
  number_fingerprint.py --compare <ملف>            يعرض الفروق مصنَّفة
  number_fingerprint.py --compare <ملف> --require-unchanged   يفشل عند أي فرق

رمز الخروج: 0 سليم · 2 فرق غير مسموح (مع --require-unchanged).
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from datetime import date
from pathlib import Path

from surface_fingerprint import surfaces, visible  # لا تكرار لمنطق الأسطح

NUM = re.compile(r"\d[\d,.\u0660-\u0669]*")
DIGIT_MAP = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669", "0123456789")


def values(text: str, window: int = 44) -> list[dict]:
    out = []
    for m in NUM.finditer(text):
        raw = m.group(0).translate(DIGIT_MAP)
        try:
            val = float(raw.replace(",", ""))
        except ValueError:
            continue
        ctx = text[max(0, m.start() - window):m.end() + window].replace("\n", " ")
        out.append({"v": raw, "n": val, "ctx": ctx.strip()})
    return out


def measure(root: Path, site: Path) -> dict:
    out: dict = {"generated": date.today().isoformat(), "surfaces": {}}
    for name, path in surfaces(root, site):
        if not path.is_file():
            continue
        vals = values(visible(path))
        out["surfaces"][name] = {"path": str(path), "count": len(vals), "values": vals}
    return out


def _sig(item: dict) -> str:
    return re.sub(r"\s+", " ", item["ctx"])[:80]


def compare(root: Path, site: Path, baseline: str) -> tuple[int, list[str]]:
    base = json.loads(Path(baseline).read_text(encoding="utf-8"))
    now = measure(root, site)
    changed: list[str] = []
    print(f"   بصمة الأرقام — الأساس: {baseline}")
    for name, cur in now["surfaces"].items():
        old = base["surfaces"].get(name, {})
        old_vals, new_vals = old.get("values", []), cur["values"]
        old_sigs = {_sig(x) for x in old_vals}
        new_sigs = {_sig(x) for x in new_vals}
        added, removed = new_sigs - old_sigs, old_sigs - new_sigs
        if not added and not removed and old.get("count") == cur.get("count"):
            print(f"   • {name}: لم يتغيّر ({cur['count']} رقمًا)")
            continue
        changed.append(name)
        print(f"   ! {name}: {old.get('count', '—')} → {cur['count']} رقمًا · ظهر {len(added)} · اختفى {len(removed)}")
        for s in sorted(added)[:4]:
            print(f"        + {s}")
        for s in sorted(removed)[:4]:
            print(f"        - {s}")
    print(f"   الخلاصة: {len(changed)} سطحًا تغيّرت أرقامه من {len(now['surfaces'])}")
    return (2 if changed else 0), changed


def main() -> int:
    ap = argparse.ArgumentParser(description="بصمة الأرقام المعروضة")
    ap.add_argument("--root", default=".", help="جذر النظام")
    ap.add_argument("--site", default="/home/ubuntu/seawatch", help="جذر الموقع")
    ap.add_argument("--date", default=date.today().isoformat(), help="تاريخ البصمة أو وسمها")
    ap.add_argument("--out", help="مسار ملف البصمة")
    ap.add_argument("--compare", help="ملف بصمة للمقارنة")
    ap.add_argument("--require-unchanged", action="store_true", help="فشل عند أي فرق")
    args = ap.parse_args()
    root, site = Path(args.root).resolve(), Path(args.site).resolve()

    if args.compare:
        rc, _ = compare(root, site, args.compare)
        return rc if args.require_unchanged else 0

    data = measure(root, site)
    data["tag"] = args.date
    dst = Path(args.out) if args.out else root / "logs" / "fingerprints" / f"numbers-{args.date}.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(s["count"] for s in data["surfaces"].values())
    print(f"✔ بصمة الأرقام: {total} رقمًا في {len(data['surfaces'])} سطحًا → {dst}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
