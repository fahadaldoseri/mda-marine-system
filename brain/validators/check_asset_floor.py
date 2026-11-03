#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حاجز أرضية الأصول الحاكمة — يمنع أي نقص في أصل معتمد (عطل ك-483).

المبرر المقيس: لقطة الأصول (`evidence/merkle/snapshot.json`) تُبنى في خطوة G000
قبل بوابة G000A، فقارن الحارس الحالة بالحالة نفسها؛ ومعه يمرّ اختصار ملف على
الخادم والمرآة معًا بلا مانع (قيس في جولة ك-483: ثلاثة حرّاس أعادت 0).

القاعدة: لكل أصل حاكم **أرضية** بعدد الأسطر وبالحجم لا تُخفَّض أبدًا إلا بقرار
صريح مسجَّل بالسبب (`--accept --reason`). أي نقص = فشل مغلق برمز 2.

الحالات: 0 سليم · 2 نقص أو أصل مفقود أو نقص غير مسجَّل.
"""
from __future__ import annotations

import argparse
import fnmatch
import glob
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

PROJECT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT / "tools" / "governing-assets.txt"
DEFAULT_FLOOR = PROJECT / "audit" / "asset-floor.json"


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def resolve_scope(config: pathlib.Path) -> tuple[list[pathlib.Path], list[str]]:
    """يقرأ قائمة الأصول الحاكمة ويرجع الملفات المؤهلة والمستثنيات."""
    files: list[pathlib.Path] = []
    excludes: list[str] = []
    for raw in config.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, _, pattern = line.partition(" ")
        pattern = pattern.strip()
        if kind == "GLOB":
            files += [pathlib.Path(p) for p in glob.glob(pattern, recursive=True)]
        elif kind == "FILE":
            files.append(pathlib.Path(pattern))
        elif kind == "DIR":
            files += [p for p in pathlib.Path(pattern).rglob("*") if p.is_file()]
        elif kind == "EXCLUDE":
            excludes.append(pattern)
    keep = []
    for path in files:
        text = path.as_posix()
        if any(fnmatch.fnmatch(text, pat) or fnmatch.fnmatch(text, pat.replace("**/", "")) for pat in excludes):
            continue
        if path.is_file():
            keep.append(path)
    return sorted(set(keep)), excludes


def signature(path: pathlib.Path) -> tuple[int, int, str]:
    data = path.read_bytes()
    return len(data.splitlines()), len(data), hashlib.sha256(data).hexdigest()


def load_floor(path: pathlib.Path) -> dict:
    if not path.exists():
        return {"version": 1, "updated_at": None, "files": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_floor(path: pathlib.Path, floor: dict) -> None:
    floor["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(floor, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    ap.add_argument("--floor", type=pathlib.Path, default=DEFAULT_FLOOR)
    ap.add_argument("--update", action="store_true", help="رفع الأرضيات للنموّ فقط (يُشغَّل بعد نجاح الفحص)")
    ap.add_argument("--accept", default="", help="مسار أصل يُقبل نقصه بقرار صريح")
    ap.add_argument("--reason", default="", help="سبب القبول (إلزامي مع --accept)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    config = args.config
    if not config.exists():
        print(f"   ✘ قائمة الأصول مفقودة: {config}")
        return 2
    files, _ = resolve_scope(config)
    floor = load_floor(args.floor)
    entries: dict[str, dict] = floor.setdefault("files", {})
    blockers: list[str] = []
    grown: list[str] = []

    scope_keys = {p.as_posix() for p in files}
    for key in sorted(set(entries) - scope_keys):
        blockers.append(f"أصل حاكم مفقود أو خارج النطاق: {key}")
    if not files:
        blockers.append("نطاق الأصول فارغ — القائمة لا تطابق أي ملف")
        blockers = sorted(set(blockers))

    for path in files:
        key = path.as_posix()
        # ملف الأرضية نفسه لا يُقاس بأرضيته (وإلا منع إعادة كتابة نفسه عند قبول نقص مسجَّل)
        if path.resolve() == args.floor.resolve():
            continue
        lines, size, sha = signature(path)
        rec = entries.get(key)
        if rec is None:
            entries[key] = {
                "lines": lines, "size": size, "sha256": sha,
                "first_seen": today(), "last_seen": today(), "accepted_reductions": [],
            }
            continue
        rec["last_seen"] = today()
        shrink = lines < int(rec.get("lines", 0)) or size < int(rec.get("size", 0))
        accepted = args.accept and (key == args.accept or key.endswith("/" + args.accept))
        if accepted:
            if not args.reason.strip():
                blockers.append(f"--accept بلا سبب مسجَّل: {key}")
            else:
                rec.setdefault("accepted_reductions", []).append({
                    "date": today(), "reason": args.reason.strip(),
                    "from_lines": rec.get("lines"), "to_lines": lines,
                    "from_size": rec.get("size"), "to_size": size,
                })
                rec.update({"lines": lines, "size": size, "sha256": sha})
        elif shrink:
            blockers.append(
                f"نقص في أصل معتمد: {key} — أسطر {rec.get('lines')}→{lines} · بايت {rec.get('size')}→{size}"
            )
        else:
            if lines > int(rec.get("lines", 0)) or size > int(rec.get("size", 0)):
                grown.append(key)
            rec.update({
                "lines": max(lines, int(rec.get("lines", 0))),
                "size": max(size, int(rec.get("size", 0))),
                "sha256": sha,
            })

    summary = {
        "status": "PASS" if not blockers else "BLOCK",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope_files": len(files),
        "floor_entries": len(entries),
        "grown": len(grown),
        "blockers": blockers,
    }

    if args.update and not blockers:
        save_floor(args.floor, floor)
        summary["floor_written"] = True
    elif args.accept and not blockers:
        save_floor(args.floor, floor)
        summary["floor_written"] = True

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=1))
    elif not args.quiet:
        print("=== حاجز أرضية الأصول الحاكمة ===")
        print(f"   الملفات في النطاق: {len(files)} · مدخلات الأرضية: {len(entries)} · نموّ مسجَّل: {len(grown)}")
        if blockers:
            for item in blockers[:12]:
                print("   ✘ " + item)
        print(f"   النتيجة: {'سليم' if not blockers else 'منع — نقص في أصل معتمد'}")

    return 2 if blockers else 0


if __name__ == "__main__":
    _root = pathlib.Path(__file__).resolve().parent
    sys.path.insert(0, str(_root))
    from _guard import run

    run(main)
