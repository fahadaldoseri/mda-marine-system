#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قياس أداء عائلات الوحدات في ترجمة النسخة الإنجليزية — دليل قابل لإعادة التشغيل.

الغرض: إعطاء رقم صادق لكل عائلة من عائلات الوحدات التي كانت تُمنع الترجمة، بعد
إصلاح المسار. يُقاس كل مثال محفوظ بإعادة تشغيل المترجم عليه فعليًا، لا بالاستنتاج.

الاستخدام:
  python3 tools/measure_translation_families.py --units /tmp/units597.txt --date 2026-11-09
  python3 tools/measure_translation_families.py --units <file> --date <YYYY-MM-DD> --out <json>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

FAMILIES: list[tuple[str, str]] = [
    ("عناوين مؤرّخة", r"^(عنوان|عنوانًا|عنواناً)"),
    ("إضافات ومرفقات", r"^إضافات|^· إضافات"),
    ("أسماء أقسام وواجهة", r"^(سجل|مستوى|مؤشر|الخلاصة|الإضافات|المصادر)"),
    ("عوامل التغيير والثبات", r"^(عوامل التغيير|سبب الثبات|لماذا لم يرتفع|ما يرفعه|ما يخالفه)"),
    ("صفوف الوقائع", r"^(الواقعة|واقعة|أعلن|أعلنت)"),
    ("المسافات والاتجاهات", r"أميال بحرية|كيلومتر|على بعد"),
    ("العدّادات والأرقام", r"\d+\s*(بلاغ|واقعة|مصاب|قضية)|بنود"),
    ("المناطق والفترات", r"مضيق|خليج|البحر|الفترة|بتوقيت"),
]


def family_of(unit: str) -> str:
    for name, pattern in FAMILIES:
        if re.search(pattern, unit):
            return name
    return "غير مصنّف"


def load_units(path: pathlib.Path) -> list[str]:
    units: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        unit = line.split("\t")[0].strip()
        if unit:
            units.append(unit)
    return units


def main() -> int:
    ap = argparse.ArgumentParser(description="قياس عائلات الوحدات المترجمة")
    ap.add_argument("--units", required=True, help="ملف الوحدات المحفوظة (وحدة ثم تاريخ)")
    ap.add_argument("--date", required=True, help="تاريخ يُبنى منه المعجم وذاكرة المحاذاة")
    ap.add_argument("--out", default=None, help="مسار ملف JSON للنتيجة")
    a = ap.parse_args()

    import i18n_en as I

    tm, gl = I.build_tm(a.date), I.load_glossary()
    tr = I.make_translator(tm, gl)
    units = load_units(pathlib.Path(a.units))

    totals: dict[str, int] = {}
    passed: dict[str, int] = {}
    fails: dict[str, list[str]] = {}
    for unit in units:
        fam = family_of(unit)
        out = tr(unit)
        ok = bool(out) and not I.ARABIC.search(I.norm(out))
        totals[fam] = totals.get(fam, 0) + 1
        if ok:
            passed[fam] = passed.get(fam, 0) + 1
        else:
            fails.setdefault(fam, []).append(unit[:100])

    print(f"   ═══ أداء عائلات الوحدات ({a.date}) ═══")
    print(f"   الوحدات المقيسة: {len(units)} · المعجم: {len(gl)} · ذاكرة المحاذاة: {len(tm)}")
    for fam in sorted(totals, key=lambda k: -totals[k]):
        done, total = passed.get(fam, 0), totals[fam]
        pct = (done / total * 100) if total else 0
        print(f"   ■ {fam}: {done}/{total} مترجمة ({pct:.0f}%)")
        for unit in fails.get(fam, [])[:2]:
            print(f"      ✘ {unit}")

    if a.out:
        report = {fam: {"total": totals[fam], "translated": passed.get(fam, 0),
                        "failed_samples": fails.get(fam, [])} for fam in totals}
        pathlib.Path(a.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"   ✔ حُفظت النتيجة: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
