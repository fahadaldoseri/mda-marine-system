#!/usr/bin/env python3
"""نقل محكوم إلى الحجر (quarantine): لا حذف نهائي، وسجل استرجاع لكل عنصر.

الاستعمال:
  python3 quarantine_move.py --plan plan.json --root <جذر> [--quarantine <مجلد>]
  python3 quarantine_move.py --plan plan.json --apply  [--restore] [--stamp NAME]
  python3 quarantine_move.py --plan plan.json --decide --floor <ملف أرضية> --reason "..."

صيغة الخطة (JSON):
{"groups":[{"name":"...","reason":"...","mode":"delete|empty_dirs","paths":["مسار نسبي","/مسار مطلق","مجلد/*.bak"]}]}

السلوك:
- معاينة بلا --apply. ومع --apply يُنقل كل ملف/مجلد إلى <quarantine>/<stamp>/ مع manifest.json.
- يكتب cleanup-removed-all.txt لكل المسارات، وcleanup-decisions.txt لمسارات الأرضية الحاكمة فقط.
- --restore يُعيد كل ما في manifest الحجر إلى مواضعه الأصلية.
- يحمي: .git · runbook.json · INDEX.md · asset-floor.json · governing-assets.txt
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
from datetime import datetime, timezone

PROTECTED_NAMES = {"runbook.json", "INDEX.md", "asset-floor.json", "governing-assets.txt"}
DEFAULT_QUARANTINE = "audit/quarantine"


def expand(root: pathlib.Path, pat: str) -> list[pathlib.Path]:
    p = pathlib.Path(pat)
    base = p if p.is_absolute() else (root / p)
    if any(ch in pat for ch in "*?["):
        return sorted(q for q in base.parent.glob(base.name) if q.exists())
    return [base] if base.exists() else []


def protected(path: pathlib.Path) -> str | None:
    if ".git" in path.parts:
        return "داخل .git"
    if path.name in PROTECTED_NAMES:
        return "ملف حاكم محمي"
    return None


def sig(d: pathlib.Path) -> dict[str, str]:
    import hashlib
    out = {}
    for p in d.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            out[str(p.relative_to(d))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("--plan", type=pathlib.Path, required=True)
    ap.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    ap.add_argument("--quarantine", type=pathlib.Path, default=None)
    ap.add_argument("--stamp", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--decide", action="store_true",
                    help="توليد ملف القرارات فقط من الخطة (بلا نقل)")
    ap.add_argument("--floor", type=pathlib.Path, default=None,
                    help="ملف أرضية الأصول؛ قرارات القرارات تُحصر بمدخلاته")
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    stamp = args.stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    qroot = args.quarantine or (args.root / DEFAULT_QUARANTINE)
    qdir = qroot / stamp
    manifest = qdir / "manifest.json"

    if args.restore:
        if not manifest.exists():
            print(f"✘ لا سجل حجر: {manifest}")
            return 2
        rec = json.loads(manifest.read_text(encoding="utf-8"))
        n = 0
        for item in rec["moved"]:
            src, dst = pathlib.Path(item["quarantine"]), pathlib.Path(item["original"])
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                n += 1
        print(f"أُعيد {n} عنصرًا من الحجر {stamp}")
        return 0

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    moved, rows, decisions = [], [], []
    stats = {"files": 0, "dirs": 0, "bytes": 0, "empty": 0}

    for group in plan["groups"]:
        for pat in group.get("paths", []):
            for t in expand(args.root, pat):
                why = protected(t)
                if why or not t.exists():
                    rows.append({"path": str(t), "group": group["name"],
                                 "status": f"محمي: {why}" if why else "غير موجود"})
                    continue
                if group.get("mode") == "empty_dirs":
                    if t.is_dir() and not any(t.iterdir()):
                        stats["empty"] += 1
                        if args.apply:
                            t.rmdir()
                    continue
                files = [t] if t.is_file() else [p for p in t.rglob("*") if p.is_file()]
                stats["files"] += len(files)
                stats["bytes"] += sum(p.stat().st_size for p in files)
                stats["dirs"] += 1 if t.is_dir() else 0
                rows.append({"path": str(t), "group": group["name"], "status": "نُقل إلى الحجر"})
                decisions += [(str(p), group["name"]) for p in files] if t.is_dir() else [(str(t), group["name"])]
                if args.apply:
                    rel = t.relative_to(args.root) if str(t).startswith(str(args.root)) else pathlib.Path(t.name)
                    dst = qdir / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if dst.exists():
                        dst = dst.with_name(dst.name + f".{len(moved)}")
                    shutil.move(str(t), str(dst))
                    moved.append({"original": str(t), "quarantine": str(dst), "group": group["name"]})

    governed = set()
    if args.floor and args.floor.exists():
        governed = set(json.loads(args.floor.read_text(encoding="utf-8")).get("files", {}))
    governed_rows = [(p, n) for p, n in sorted(set(decisions)) if (not governed or p in governed)]

    if args.apply or args.decide:
        qdir.mkdir(parents=True, exist_ok=True)
        (qdir / "manifest.json").write_text(
            json.dumps({"stamp": stamp, "reason": args.reason, "moved": moved},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        (args.root / "cleanup-removed-all.txt").write_text(
            "\n".join(f"{p}\t{n}" for p, n in sorted(set(decisions))) + "\n", encoding="utf-8")
        (args.root / "cleanup-decisions.txt").write_text(
            "# قرارات تنظيف — مسار حاكم ثم السبب\n"
            + "\n".join(f"{p} — {n}" for p, n in governed_rows) + "\n", encoding="utf-8")

    print(f"الخطة: {len(plan['groups'])} مجموعة · عناصر مُعالجة: {len(rows)}")
    print(f"ملفات: {stats['files']} · مجلدات: {stats['dirs']} · حجم: {stats['bytes']/1048576:.2f} ميغابايت · مجلدات فارغة: {stats['empty']}")
    print(f"قرارات حاكمة: {len(governed_rows)} من {len(set(decisions))}")
    if args.apply:
        print(f"نُقل إلى الحجر: {len(moved)} · السجل: {manifest}")
    else:
        print("(معاينة فقط — أضف --apply للتنفيذ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
