#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قياس نواقص الترجمة في أرشيف الموقع كاملًا — دليل قابل لإعادة التشغيل.

يقيس كل صفحة بتاريخها (ذاكرة المحاذاة تخص تاريخها)، ويطبع ملخصًا JSON.
الخروج 0 إذا كان المجموع صفرًا، و2 إن وُجدت نواقص (فشل مغلق).

الاستخدام:
  python3 tools/measure_archive_units.py --out /tmp/archive_units.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))


def main() -> int:
    ap = argparse.ArgumentParser(description="قياس نواقص الترجمة في الأرشيف")
    ap.add_argument("--out", default=None, help="ملف JSON للنتيجة")
    ap.add_argument("--include-additions", action="store_true", default=True)
    a = ap.parse_args()

    import i18n_en as I

    gl = I.load_glossary()
    units_by_page: dict[str, int] = {}
    missing_by_page: dict[str, list[str]] = {}
    no_master: list[str] = []
    not_bilingual: list[str] = []
    en_dir = ROOT / "dist" / "reports" / "en"
    for page in sorted((ROOT / "dist" / "reports").glob("*.html")):
        if not page.stem[:4].isdigit():
            continue
        date = page.stem
        # العقد ثنائي اللغة يسري على الصفحات المنشورة بلغتين؛ ما لا نظير له لا يُقاس عيبًا.
        if not (en_dir / f"{date}.html").is_file():
            not_bilingual.append(date)
            continue
        try:
            tm = I.build_tm(date)
        except FileNotFoundError:
            # تواريخ بلا متن إنجليزي حاكم: تُقاس بالمعجم وحده، ولا تُعدّ عيبًا.
            no_master.append(date)
            tm = {}
        _out, miss, total = I.translate_page(page.read_text(encoding="utf-8"), date, tm, gl)
        units_by_page[date] = int(total)
        if miss:
            missing_by_page[date] = sorted(set(miss))

    additions = ROOT / "dist" / "additions.html"
    if a.include_additions and additions.is_file():
        date = "2026-11-09"
        _out, miss, total = I.translate_page(additions.read_text(encoding="utf-8"), date, I.build_tm(date), gl)
        units_by_page["additions"] = int(total)
        if miss:
            missing_by_page["additions"] = sorted(set(miss))

    missing_total = sum(len(v) for v in missing_by_page.values())
    report = {
        "pages": len(units_by_page),
        "units_total": sum(units_by_page.values()),
        "missing_total": missing_total,
        "per_page_missing": {k: len(v) for k, v in missing_by_page.items()},
        "pages_without_en_master": no_master,
        "pages_not_bilingual": not_bilingual,
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0 if missing_total == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
