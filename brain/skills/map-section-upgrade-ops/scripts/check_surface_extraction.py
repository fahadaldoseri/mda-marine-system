#!/usr/bin/env python3
"""إعادة إنتاج ما تراه بوابة تغطية الأسلوب على سطح مفرد.

السبب: البوابة تُسطّح قيم JSON إلى نص قبل فحص الصياغة، فقد يمنع السطح بسبب
نصّ في مرجع بيانات لا يظهر في الصفحة. هذا السكربت يعيد إنتاج ذلك القياس.
"""
from __future__ import annotations

import os
import argparse, json, pathlib, subprocess, sys

BRAIN = pathlib.Path(os.environ.get("BRAIN") or os.environ.get("BRAIN_DIR") or ".")
SITE = pathlib.Path(os.environ.get("SITE") or os.environ.get("SITE_DIR") or "seawatch")


def flatten(obj, out: list[str]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            flatten(v, out)
    elif isinstance(obj, list):
        for v in obj:
            flatten(v, out)
    elif isinstance(obj, str):
        out.append(obj)


def target(surface: str, day: str) -> pathlib.Path:
    if surface == "meta":
        return BRAIN / "web" / "meta" / f"{day}.json"
    if surface == "md":
        return BRAIN / "reports" / f"{day}-sectioned.md"
    if surface == "page":
        return SITE / "dist" / "reports" / f"{day}.html"
    raise SystemExit(f"سطح غير معروف: {surface}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--surface", default="meta", choices=["meta", "md", "page"])
    a = ap.parse_args()
    src = target(a.surface, a.date)
    if not src.exists():
        print(f"✘ المصدر غير موجود: {src}")
        return 2
    tmp = pathlib.Path("/tmp/surface_extract.txt")
    if a.surface == "meta":
        vals: list[str] = []
        flatten(json.loads(src.read_text(encoding="utf-8")), vals)
        tmp.write_text("\n".join(vals), encoding="utf-8")
    else:
        tmp.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    gate = BRAIN / "validators" / "check_prose_defects.py"
    r = subprocess.run([sys.executable, str(gate), "--md", str(tmp)],
                       capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    print(f"=== سطح {a.surface} · {a.date} · رمز {r.returncode} ===")
    for ln in out.splitlines():
        if any(k in ln for k in ("مصطنعة", "النتيجة", "✗", "الأسطر", "السطر", "×")):
            print("  " + ln.strip())
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
