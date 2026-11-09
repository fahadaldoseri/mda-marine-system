#!/usr/bin/env python3
"""التحقق من ادّعاء مكتوب في تقرير مقابل المخرج الفعلي.

القاعدة: لا ادّعاء بلا مخرج. كل جملة فيها «صفر» أو «تم» أو رقم تُفحص على مخرج حقيقي.

الاستعمال:
  python3 verify_claims.py --target <ملف أو مجلد> --claim "نفّذوا" [--claim "..."] \
      [--expect absent|present] [--max-show 3] [--json-out out.json]

  --expect absent  (افتراضي): الادّعاء يقول «غير موجود» → يجب أن يكون العدد 0.
  --expect present           : الادّعاء يقول «موجود» → يجب أن يكون العدد > 0.

رمز الخروج: 0 = كل الادعاءات مطابقة للمخرج · 2 = ادّعاء مخالف للمخرج.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".woff", ".woff2", ".ttf", ".ico"}


def targets(root: pathlib.Path) -> list[pathlib.Path]:
    if root.is_file():
        return [root]
    return [p for p in sorted(root.rglob("*")) if p.is_file() and p.suffix.lower() not in SKIP_SUFFIX]


def count_claim(root: pathlib.Path, claim: str) -> tuple[int, list[str]]:
    total, where = 0, []
    for f in targets(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        n = text.count(claim)
        if n:
            total += n
            if len(where) < 5:
                where.append(str(f))
    return total, where


def main() -> int:
    ap = argparse.ArgumentParser(description="تحقق من ادّعاء مقابل المخرج")
    ap.add_argument("--target", required=True, help="ملف أو مجلد المخرج")
    ap.add_argument("--claim", action="append", required=True, help="نص الادّعاء (يتكرر)")
    ap.add_argument("--expect", choices=["absent", "present"], default="absent")
    ap.add_argument("--max-show", type=int, default=3)
    ap.add_argument("--json-out")
    a = ap.parse_args()

    root = pathlib.Path(a.target)
    if not root.exists():
        print(f"✘ المخرج غير موجود: {root}", file=sys.stderr)
        return 2

    rows, bad = [], 0
    print(f"المخرج: {root} · عدد الملفات المفحوصة: {len(targets(root))}")
    for claim in a.claim:
        total, where = count_claim(root, claim)
        ok = (total == 0) if a.expect == "absent" else (total > 0)
        rows.append({"claim": claim, "count": total, "expect": a.expect, "ok": ok, "files": where})
        mark = "✔" if ok else "✘"
        print(f"   {mark} «{claim}» — المواضع: {total} (المتوقع: {'صفر' if a.expect == 'absent' else 'أكبر من صفر'})")
        for w in where[: a.max_show]:
            print(f"        {w}")
        if not ok:
            bad += 1

    if a.json_out:
        pathlib.Path(a.json_out).write_text(json.dumps({"target": str(root), "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    if bad:
        print(f"\nالنتيجة: {bad} ادّعاء مخالف للمخرج — صحّح التقرير أو أصلح المخرج، ولا تُبقِ ادّعاءً بلا سند.")
        return 2
    print("\nالنتيجة: كل الادعاءات مطابقة للمخرج.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())