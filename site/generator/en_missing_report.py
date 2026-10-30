#!/usr/bin/env python3
"""يجمع كل نص عربي في صفحة الإصدار العربية لا يجد له المترجم ترجمة — بلا سقف.

الغرض (ك-337): بناء النسخة الإنجليزية يفشل مغلقًا عند أي نص بلا ترجمة، وكانت القائمة
المطبوعة محدودة بـ15 بندًا فيُصلَح نص ويظهر غيره. هذه الأداة تُخرج المجموعة الكاملة
مع سياقها، ليُترجم الجميع في مرة واحدة.

الاستعمال: python3 generator/en_missing_report.py --date 2026-10-29 [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import i18n_en as I  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARABIC = re.compile(r"[\u0600-\u06FF]")


def collect(date: str) -> list[dict]:
    page = (ROOT / "dist" / "reports" / f"{date}.html").read_text(encoding="utf-8")
    # استثناء كتل الأنماط والسكربتات: تعليقات CSS العربية ليست نصًا معروضًا
    page = re.sub(r"<style[^>]*>.*?</style>", " ", page, flags=re.S | re.I)
    page = re.sub(r"<script[^>]*>.*?</script>", " ", page, flags=re.S | re.I)
    tm = I.build_tm(date)
    gl = I.load_glossary()
    tr = I.make_translator(tm, gl)
    found: dict[str, str] = {}
    for m in re.finditer(r">([^<>]*[\u0600-\u06FF][^<>]*)<", page):
        raw = m.group(1)
        if not ARABIC.search(raw):
            continue
        out = tr(raw)
        if ARABIC.search(out):
            # اطبع الجزء العربي المتبقي فقط، مع سياقه
            left = " ".join(re.findall(r"[\u0600-\u06FF][\u0600-\u06FF\s،؛:.…«»()0-9A-Za-z\-]*", out))
            key = I.norm(raw)
            found.setdefault(key, left.strip() or I.norm(raw))
    return [{"text": k, "remaining": v} for k, v in found.items()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    rows = collect(a.date)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── نصوص بلا ترجمة: {len(rows)} ──")
    for r in rows:
        print("   - " + r["text"][:220])
    return 0 if not rows else 2


if __name__ == "__main__":
    sys.exit(main())