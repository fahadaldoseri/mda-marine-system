#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار لقاعدة «سنة المفتاح تظهر في القيمة» في معجم النسخة الإنجليزية (ك-596).

السبب المقيس: قاعدة الاشتقاق الآلي في `generator/make_en_glossary.py` تأخذ أول جملة
من مفتاح أطول عند غياب الوحدة، فأسندت إلى «آخر تحديث سبتمبر 2026» القيمة
«For public information» — وهي ترجمة عبارة أخرى. فترجم المفتاحُ بلا سنة، فرُفض في
حارس ك-592 (كل رقم في الأصل يجب أن يظهر في الترجمة) وأوقف بناء الإصدارات التاريخية.

الحالات:
  1. سالبة: المفتاح المؤرخ مع قيمة أجنبية يُعدّ مخالفًا.
  2. موجبة: المفتاح المؤرخ مع قيمة تحمل السنة يمرّ.
  3. مفتاح بلا سنة يمرّ دائمًا.
  4. prune يحذف المخالف ويُبقي السليم.
  5. المعجم الحيّ خالٍ من أي مخالفة (يفشل الاختبار قبل الإصلاح — دورة RED).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GL = ROOT / "sources" / "i18n" / "en" / "glossary.json"

spec = importlib.util.spec_from_file_location("make_en_glossary", ROOT / "generator" / "make_en_glossary.py")
G = importlib.util.module_from_spec(spec)
sys.modules["make_en_glossary"] = G
spec.loader.exec_module(G)


def test_negative_dated_key_with_foreign_value():
    assert G.year_violation("آخر تحديث سبتمبر 2026", "For public information") is True


def test_positive_dated_key_keeps_year():
    assert G.year_violation("آخر تحديث سبتمبر 2026", "Last updated September 2026") is False


def test_key_without_year_always_passes():
    assert G.year_violation("نسب التهديد", "Threat shares") is False


def test_prune_removes_only_violating_entry():
    d = {
        "entries": {
            "آخر تحديث سبتمبر 2026": "For public information",
            "آخر تحديث أكتوبر 2026": "Last updated October 2026",
            "نسب التهديد": "Threat shares",
        },
        "_derived": {"آخر تحديث سبتمبر 2026": "اشتقاق آلي بمحاذاة ذاكرة الترجمة"},
    }
    bad = G.prune(d)
    assert bad == ["آخر تحديث سبتمبر 2026"]
    assert "آخر تحديث سبتمبر 2026" not in d["entries"]
    assert "آخر تحديث سبتمبر 2026" not in d["_derived"]
    assert d["entries"]["آخر تحديث أكتوبر 2026"] == "Last updated October 2026"
    assert d["entries"]["نسب التهديد"] == "Threat shares"


def test_live_glossary_has_no_year_violation():
    d = json.loads(GL.read_text(encoding="utf-8"))
    offenders = [k for k, v in d.get("entries", {}).items()
                 if isinstance(v, str) and G.year_violation(k, v)]
    assert offenders == [], f"مدخلات مخالفة لقاعدة السنة: {offenders}"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"   ✔ {name}")
            except AssertionError as exc:
                fails += 1
                print(f"   ✘ {name}: {exc}")
    print(f"   النتيجة: {'كل الحالات ناجحة' if fails == 0 else f'فشل {fails}'}")
    sys.exit(1 if fails else 0)
