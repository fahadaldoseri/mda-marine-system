#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس استثناء وسم الصف المُهيكل في قياس القوالب المتكررة (عطل ك-564).

السبب المقيس: صفحة الإضافات تعرض صفوفًا مبدوءة بوسم الحقل «المصدر والحدود» ثم نص الصف
(مثل «straits.live وقناة العربية؛ 2 ناقلتان بلا أسماء…»). فكان الوسم المتكرر يُعلن
«قالب جملة متكرر» مانعًا، فتُمنع بوابة الأسلوب (G045) التسليم بلا عيب صياغة حقيقي.

القاعدة المقيسة هنا:
1) الصف المبدوء بوسم حقل مُهيكل لا يُقاس وسْمُه قالبًا؛ ويُقاس نص الصف بعده.
2) الجملة الإنشائية المتكررة أكثر من مرتين تبقى مانعة كما كانت.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_VALIDATOR = ROOT / "validators" / "check_prose_defects.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("check_prose_defects", _VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_label_led_rows_are_structure_not_template():
    module = _load_validator()
    text = "\n".join([
        "المصدر والحدود UKMTO؛ نقل قناة العربية يذكر شرق خورفكان، بينما مقتطف UKMTO لا يعرض الموقع الكامل",
        "المصدر والحدود straits.live وقناة العربية؛ 2 ناقلتان بلا أسماء أو أرقام IMO أو تأكيد UKMTO",
        "المصدر والحدود straits.live وقناة العربية؛ لا يكفي لتحديد الواقعة أو صلتها ببلاغ UKMTO",
        "المصدر والحدود straits.live وقناة العربية؛ اتجاه إعلامي غير كاف للإحصاء",
    ])
    assert module.find_repeated_templates(text) == []


def test_plain_repeated_sentence_still_blocks():
    module = _load_validator()
    sentence = "أوردت الجهة المصدر عنوانًا عن حادث بحري قريبًا من ساحل الإمارات دون تأكيد رسمي."
    text = "\n".join([sentence] * 3)
    found = module.find_repeated_templates(text)
    assert len(found) == 1, found
    assert found[0]["count"] == 3, found


def test_label_only_rows_do_not_count_as_sentences():
    module = _load_validator()
    text = "\n".join(["المصدر والحدود"] * 4)
    assert module.find_repeated_templates(text) == []