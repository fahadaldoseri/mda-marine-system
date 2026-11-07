#!/usr/bin/env python3
"""بصمة الأسطح الحاكمة — تُقاس على النص الذي يراه القارئ لا على الملف الخام.

الأسطح: الرئيسية · الإضافات · المصادر · أحدث إصدار · التغذية · دفتر اليوم · عقد البطاقات · نص التقرير.
لكل سطح: sha256 لنصّه المرئي بعد إسقاط الوسوم والسكربتات والأنماط وتوحيد المسافات.

الاستعمال:
  surface_fingerprint.py                      يُنشئ بصمة اليوم في logs/fingerprints/
  surface_fingerprint.py --tag before-x       يسم البصمة
  surface_fingerprint.py --compare <ملف>      يقارن ببصمة سابقة ويعرض الفروق
  surface_fingerprint.py --compare <ملف> --require-unchanged   يفشل عند أي فرق

رمز الخروج: 0 سليم · 2 فرق غير مسموح (مع --require-unchanged).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

BRAIN = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
SITE = Path(os.environ.get("SITE_DIR") or BRAIN.parent / "seawatch")

TAGS = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
ANY_TAG = re.compile(r"<[^>]+>")
SPACES = re.compile(r"[ \t\u00a0]+")
BLANKS = re.compile(r"\n{2,}")


def visible(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".xml"}:
        raw = TAGS.sub(" ", raw)
        raw = ANY_TAG.sub(" ", raw)
    return BLANKS.sub("\n", SPACES.sub(" ", raw)).strip()


def surfaces(root: Path, site: Path) -> list[tuple[str, Path]]:
    items: list[tuple[str, Path]] = [
        ("صفحة الرئيسية", site / "dist" / "index.html"),
        ("صفحة الإضافات", site / "dist" / "additions.html"),
        ("صفحة المصادر", site / "dist" / "sources.html"),
        ("التغذية RSS", site / "dist" / "feed.xml"),
    ]
    for glob_pat, name in ((str(root / "reports" / "*-sectioned.md"), "نص التقرير"),
                           (str(root / "cumulative-2026" / "daily" / "*.json"), "دفتر اليوم"),
                           (str(site / "dist" / "reports" / "*.html"), "أحدث إصدار")):
        hits = sorted(glob.glob(glob_pat))
        if hits:
            items.append((name, Path(hits[-1])))
    items.append(("عقد البطاقات", root / "appendices" / "card_registry.json"))
    return items


def measure(root: Path, site: Path) -> dict:
    out: dict = {"generated": date.today().isoformat(), "surfaces": {}}
    for name, path in surfaces(root, site):
        if not path.is_file():
            out["surfaces"][name] = {"path": str(path), "missing": True}
            continue
        text = visible(path)
        out["surfaces"][name] = {
            "path": str(path),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "chars": len(text),
        }
    return out


def write(root: Path, site: Path, tag: str, out_path: str | None) -> Path:
    data = measure(root, site)
    data["tag"] = tag
    dst = Path(out_path) if out_path else root / "audit" / "fingerprints" / f"surfaces-{tag}.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✔ بصمة الأسطح: {len(data['surfaces'])} سطحًا → {dst}")
    return dst


def compare(root: Path, site: Path, baseline: str) -> int:
    base = json.loads(Path(baseline).read_text(encoding="utf-8"))
    now = measure(root, site)
    rows, changed = [], []
    for name, cur in now["surfaces"].items():
        old = base["surfaces"].get(name)
        if old is None:
            rows.append((name, "سطح جديد", "—"))
            changed.append(name)
        elif cur.get("sha256") == old.get("sha256"):
            rows.append((name, "لم يتغيّر", cur.get("chars")))
        else:
            delta = int(cur.get("chars") or 0) - int(old.get("chars") or 0)
            rows.append((name, "تغيّر", f"{delta:+d} حرفًا"))
            changed.append(name)
    for name in base["surfaces"]:
        if name not in now["surfaces"]:
            rows.append((name, "سطح اختفى", "—"))
            changed.append(name)
    print(f"   بصمة الأسطح — الأساس: {baseline}")
    for name, state, note in rows:
        mark = "•" if state == "لم يتغيّر" else "!"
        print(f"   {mark} {name}: {state} ({note})")
    print(f"   الخلاصة: {len(changed)} سطحًا متغيّرًا من {len(now['surfaces'])}")
    if changed:
        print("   المسار: " + " · ".join(changed))
    return 2 if changed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="بصمة الأسطح الحاكمة")
    ap.add_argument("--root", default=str(BRAIN), help="جذر النظام")
    ap.add_argument("--site", default=str(SITE), help="جذر الموقع")
    ap.add_argument("--tag", default=date.today().isoformat(), help="وسم البصمة")
    ap.add_argument("--out", help="مسار ملف البصمة")
    ap.add_argument("--compare", help="ملف بصمة للمقارنة")
    ap.add_argument("--require-unchanged", action="store_true", help="فشل عند أي فرق")
    args = ap.parse_args()
    root, site = Path(args.root).resolve(), Path(args.site).resolve()

    if args.compare:
        return compare(root, site, args.compare)
    write(root, site, args.tag, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
