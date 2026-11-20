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


def collect(date: str, page_path: pathlib.Path | None = None) -> list[dict]:
    """كل نص ناقص بالمفتاح الذي يُضاف إلى المعجم كما هو (ك-إ3).

    بعد منع المطابقة الجزئية لا يُكمَّل جزء ولا يُقتطع، فالمفتاح الصحيح للجملة التي يقطعها
    رمز لاتيني («أبلغت <UKMTO> عن…») هو الجملة كلها برموزها، وقيمتها الإنجليزية تحمل الرموز
    حرفيًا. تُستعمل هنا مسارات المترجم نفسه، فما تذكره الأداة هو ما يرفضه البناء.
    """
    path = page_path or (ROOT / "dist" / "reports" / f"{date}.html")
    html = path.read_text(encoding="utf-8")
    tm = I.build_tm(date)
    gl = I.load_glossary()
    _, missing, _ = I.translate_page(html, date, tm, gl)
    missing_set = {I.norm(m) for m in missing}
    prepared = I._element_governed_overrides(I._preserve_master_dynamic_fields(html, date), tm, gl)
    c = I._Collector()
    c.feed(prepared)
    _, positions = I._html_unit_contexts(c)
    rows: dict[str, dict] = {}
    used: set[str] = set()
    for group in I._inline_tag_groups(c, positions):
        start, end = int(group["start"]), int(group["end"])
        parts = [I.norm(c.units[i]) for i in range(start, end + 1)]
        hit = [u for u in parts if u in missing_set]
        if not hit:
            continue
        key = I.norm("".join(c.units[start : end + 1]))
        tokens = [I.norm(t) for t, _, _ in group["spans"]]
        rows.setdefault(key, {"text": key, "kind": "sentence", "keep_tokens": tokens, "fragments": hit})
        used.update(hit)
    for unit in sorted(missing_set - used):
        rows.setdefault(unit, {"text": unit, "kind": "unit", "keep_tokens": [], "fragments": [unit]})
    return list(rows.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    rows = collect(a.date)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── نصوص بلا ترجمة: {len(rows)} (المفتاح الكامل الذي يُضاف إلى glossary.json) ──")
    for r in rows:
        tokens = f"  [رموز تبقى حرفيًا: {' · '.join(r['keep_tokens'])}]" if r["keep_tokens"] else ""
        print("   - " + r["text"][:400] + tokens)
    return 0 if not rows else 2


if __name__ == "__main__":
    sys.exit(main())