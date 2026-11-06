#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار لصياغة ملف الواجهة (G045 / hanging_yabqa)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "normalize_meta_style.py"


def load_module():
    spec = importlib.util.spec_from_file_location("normalize_meta_style", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"تعذّر تحميل المُطبّع: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hanging_yabqa_is_rewritten_as_a_complete_sentence():
    module = load_module()
    source = {
        "gaps": [{"impact": "يبقى الخبر نقلًا إعلاميًا بلا أصل رسمي ظاهر في المواد."}],
        "event_keys": [{"note": "يبقى الخبر قيد المتابعة ولا يثبت قرارًا نافذًا أو مهمة محددة."}],
        "hypotheses": [{"against": "لا تؤكد المواد أضرارًا متعددة أو تعطيلًا كاملًا للممر."}],
        "hero_kpis": [
            {"note": "128 حادثة مؤكدة؛ لا قراءة أحدث في مواد اليوم."},
            {"note": "24 وفاة بين البحّارة؛ لا قراءة أحدث في مواد اليوم."},
        ],
        "indicators": [{"meaning": "لا قراءة أحدث في مواد اليوم."}],
    }
    normalized, changes = module.normalize_object(source)
    assert normalized["gaps"][0]["impact"] == "الخبر نقل إعلامي بلا أصل رسمي ظاهر في المواد."
    assert normalized["event_keys"][0]["note"] == "الخبر قيد المتابعة ولا يثبت قرارًا نافذًا أو مهمة محددة."
    assert normalized["hypotheses"][0]["against"] == "لا تُثبت المواد أضرارًا متعددة أو تعطيلًا كاملًا للممر."
    assert normalized["hero_kpis"][0]["note"] == "128 حادثة مؤكدة؛ لم يرد تحديث أحدث في مواد اليوم."
    assert normalized["hero_kpis"][1]["note"] == "24 وفاة بين البحّارة؛ لم يرد تحديث أحدث في مواد اليوم."
    assert normalized["indicators"][0]["meaning"] == "لا تتوفر قراءة أحدث في مواد اليوم."
    assert len(changes) == 6
    assert "يبقى الخبر" not in str(normalized)
    assert "لا تؤكد المواد" not in str(normalized)


if __name__ == "__main__":
    test_hanging_yabqa_is_rewritten_as_a_complete_sentence()
    print("اختبار مُطبّع الواجهة: نجاح")
