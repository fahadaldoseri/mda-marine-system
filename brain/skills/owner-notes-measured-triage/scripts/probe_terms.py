#!/usr/bin/env python3
"""مسح عبارات في موقع مبني (HTML) — إثبات وجود نص أو غيابه، ويصلح حارسًا.

الاستخدام:
    python3 probe_terms.py --root dist "ما تغيّر" "نفّذوا"
    python3 probe_terms.py --root dist "أهم الأخبار" --context 90 --pages "reports/*.html"
    python3 probe_terms.py --root dist --forbid "لا تُنفذوا" --forbid "نفّذوا"
    python3 probe_terms.py --root dist --require "أهم الأخبار المتعلقة بالأمن البحري"

السلوك:
  - يحسب ظهور كل عبارة في كل صفحة مبنية، ويطبع المجموع والملفات وعيّنة سياق.
  - `--forbid`: يفشل إن وُجدت العبارة (يفيد حارسًا يمنع صيغة ممنوعة).
  - `--require`: يفشل إن غابت العبارة (يفيد حارسًا يثبت عنصرًا إلزاميًا).

رموز الخروج: 0 سليم · 2 فشل شرط أو عبارة غير موجودة.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib
import sys


def pages_of(root: pathlib.Path, pattern: str | None) -> list[pathlib.Path]:
    if pattern:
        return sorted(pathlib.Path(p) for p in glob.glob(str(root / pattern), recursive=True))
    return sorted(root.rglob("*.html"))


def count_in(text: str, term: str, regex: bool) -> int:
    if not regex:
        return text.count(term)
    import re
    return len(re.findall(term, text))


def main() -> int:
    ap = argparse.ArgumentParser(description="مسح عبارات في موقع مبني")
    ap.add_argument("--root", required=True, help="جذر المخرج المبنى (مثال: dist)")
    ap.add_argument("terms", nargs="*", help="عبارات تُقاس (وجود/غياب/عدد)")
    ap.add_argument("--regex", action="store_true", help="اعتبر العبارات أنماطًا نظامية")
    ap.add_argument("--context", type=int, default=0, help="طباعة سياق بعدد المحارف حول كل إصابة")
    ap.add_argument("--pages", help="نمط صفحات محدّد، مثل 'reports/*.html'")
    ap.add_argument("--forbid", action="append", default=[], help="عبارة ممنوعة (فشل إن وُجدت)")
    ap.add_argument("--require", action="append", default=[], help="عبارة إلزامية (فشل إن غابت)")
    ap.add_argument("--json", help="كتابة النتيجة إلى ملف JSON")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    if not root.is_dir():
        print(f"   ✘ الجذر غير موجود: {root}", file=sys.stderr)
        return 2

    files = pages_of(root, args.pages)
    if not files:
        print("   ✘ لا صفحات مطابقة", file=sys.stderr)
        return 2

    cache: dict[pathlib.Path, str] = {}
    result: dict = {"root": str(root), "pages": len(files), "terms": {}, "forbid": {}, "require": {}}

    def text_of(p: pathlib.Path) -> str:
        if p not in cache:
            cache[p] = p.read_text(encoding="utf-8", errors="replace")
        return cache[p]

    print(f"═══ مسح العبارات — {root} · صفحات: {len(files)} ═══")
    for term in args.terms:
        hits = collections.Counter()
        for p in files:
            n = count_in(text_of(p), term, args.regex)
            if n:
                hits[str(p.relative_to(root))] = n
        total = sum(hits.values())
        result["terms"][term] = {"total": total, "files": dict(hits)}
        mark = "✔" if total else "—"
        print(f"   {mark} «{term}» → {total} مرة في {len(hits)} صفحة")
        for rel, n in list(hits.items())[:6]:
            print(f"        {rel} → {n}")
        if args.context and total:
            for p in files:
                t = text_of(p)
                idx = t.find(term) if not args.regex else -1
                if idx >= 0:
                    seg = t[max(0, idx - args.context): idx + len(term) + args.context]
                    print(f"        … {seg.replace(chr(10), ' ')[:220]}")
                    break

    failed = False
    for term in args.forbid:
        found = {str(p.relative_to(root)): count_in(text_of(p), term, args.regex)
                 for p in files if count_in(text_of(p), term, args.regex)}
        result["forbid"][term] = found
        print(f"   {'✘' if found else '✔'} منع «{term}» → {'موجودة في ' + str(len(found)) + ' صفحة' if found else 'غير موجودة'}")
        for rel, n in list(found.items())[:6]:
            print(f"        {rel} → {n}")
        failed = failed or bool(found)

    for term in args.require:
        missing = [str(p.relative_to(root)) for p in files if not count_in(text_of(p), term, args.regex)]
        result["require"][term] = {"missing_in": missing}
        print(f"   {'✔' if not missing else '✘'} إلزام «{term}» → {'موجودة في كل الصفحات' if not missing else 'غائبة في ' + str(len(missing)) + ' صفحة'}")
        for rel in missing[:6]:
            print(f"        {rel}")
        failed = failed or bool(missing)

    print("═══ النتيجة: " + ("✘ فشل شرط" if failed else "✔ سليم") + " ═══")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   حُفظ التقرير: {args.json}")
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())