#!/usr/bin/env python3
"""جرد الأسطح والخردة والمجلدات الفارغة وبصمات التكرار — للقراءة والقياس فقط، بلا أي تعديل.

الاستعمال:
  python3 surface_fingerprint.py --surface project=/path --surface skills=/path \
      [--surface mirror=/path] [--pair project=mirror] [--json out.json] [--top 15]

الخرج:
  1. لكل سطح: عدد الملفات · الحجم · عدد الأدوات/البوابات (ملفات .py/.sh في tools وvalidators).
  2. الخردة المفترضة: *.bak · .DS_Store · *~ · *.orig · *.tmp · __pycache__.
  3. المجلدات الفارغة.
  4. أحدث/أقدم تعديل، وأكبر 10 مجلدات.
  5. لمقارنة زوج: ملفات زائدة · ناقصة · مختلفة المحتوى (sha256).
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import pathlib
import sys

JUNK_PATTERNS = ["*.bak", ".DS_Store", "*~", "*.orig", "*.tmp", "*.swp"]
SKIP = {".git", "__pycache__", "node_modules", ".pytest_cache", "dist"}


def walk(root: pathlib.Path) -> list[pathlib.Path]:
    out = []
    for p in root.rglob("*"):
        if p.is_file() and not (SKIP & set(p.parts)):
            out.append(p)
    return out


def sha(p: pathlib.Path, cache: dict) -> str:
    key = str(p)
    if key not in cache:
        cache[key] = hashlib.sha256(p.read_bytes()).hexdigest()
    return cache[key]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("--surface", action="append", default=[], help="اسم=مسار (يتكرر)")
    ap.add_argument("--pair", action="append", default=[], help="اسم1=اسم2 لمقارنة سطحين (يتكرر)")
    ap.add_argument("--json", type=pathlib.Path, default=None)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    surfaces: dict[str, pathlib.Path] = {}
    for item in args.surface:
        name, _, path = item.partition("=")
        surfaces[name] = pathlib.Path(path)

    report: dict = {"surfaces": {}, "pairs": {}}
    cache: dict = {}

    for name, root in surfaces.items():
        files = walk(root)
        junk, empties, by_dir = [], [], {}
        for p in files:
            rel = str(p.relative_to(root))
            if any(fnmatch.fnmatch(p.name, g) for g in JUNK_PATTERNS):
                junk.append({"path": rel, "bytes": p.stat().st_size})
            top = rel.split("/")[0] if "/" in rel else "."
            by_dir[top] = by_dir.get(top, 0) + p.stat().st_size
        for d in root.rglob("*"):
            if d.is_dir() and not (SKIP & set(d.parts)) and not any(d.iterdir()):
                empties.append(str(d.relative_to(root)))
        total = sum(p.stat().st_size for p in files)
        report["surfaces"][name] = {
            "root": str(root), "files": len(files), "bytes": total,
            "junk": junk, "junk_bytes": sum(j["bytes"] for j in junk),
            "empty_dirs": empties,
            "largest_dirs": sorted(by_dir.items(), key=lambda kv: -kv[1])[: args.top],
        }
        print(f"   [{name}] ملفات={len(files)} · حجم={total/1048576:.2f} ميغابايت · "
              f"خردة={len(junk)} ({sum(j['bytes'] for j in junk)/1024:.0f} كيلوبايت) · "
              f"مجلدات فارغة={len(empties)}")
        for j in junk[: args.top]:
            print(f"      خردة: {j['path']} ({j['bytes']} بايت)")
        for d, b in report["surfaces"][name]["largest_dirs"]:
            print(f"      أكبر مجلد: {d} ({b/1048576:.2f} ميغابايت)")

    for item in args.pair:
        a, _, b = item.partition("=")
        if a not in surfaces or b not in surfaces:
            continue
        ra, rb = surfaces[a], surfaces[b]
        fa = {str(p.relative_to(ra)): sha(p, cache) for p in walk(ra)}
        fb = {str(p.relative_to(rb)): sha(p, cache) for p in walk(rb)}
        only_a = sorted(set(fa) - set(fb))
        only_b = sorted(set(fb) - set(fa))
        diff = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
        report["pairs"][f"{a}={b}"] = {"only_in_" + a: only_a, "only_in_" + b: only_b, "different": diff}
        print(f"   [{a} ↔ {b}] زائد عند {a}={len(only_a)} · ناقص من {a}={len(only_b)} · مختلف={len(diff)}")
        for k in diff[: args.top]:
            print(f"      مختلف: {k}")

    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"   الحفظ: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
