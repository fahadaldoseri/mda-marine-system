#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار لعقدين في مولّد النسخة الإنجليزية (ك-592).

العطل الذي يمنعه:
  1) عقدة نصية تبدأ بعد وسم لاتيني داخل العنصر نفسه
     («<span class="ltr">IMO</span> — سجل الحوادث المؤكدة؛ أحدث تاريخ ظاهر ... 29 سبتمبر.»)
     كانت تُطابق مفتاحًا أقصر فيُقتطع المعنى بصمت، فتظهر البطاقة الإنجليزية ناقصة
     وترفض بوابة التماثل النشر.
  2) الاقتطاع الصامت كان يمرّ لأن فحص الوحدة يبحث عن العربية المتبقية فقط، ولا يلحظ
     ضياع رقم. القاعدة الآن: أي رقم في الأصل غاب عن الترجمة = فشل مغلق.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import i18n_en as T  # noqa: E402

DATE = "2026-11-09"


def _tr():
    return T.make_translator(T.build_tm(DATE), T.load_glossary())


def test_ltr_prefix_keeps_full_sentence():
    """موجب: البادئة اللاتينية تُضمّ إلى المفتاح فيبقى المعنى والرقم كاملين."""
    node = " — سجل الحوادث المؤكدة؛ أحدث تاريخ ظاهر في القائمة هو 29 سبتمبر."
    out = _tr()(node, "IMO")
    assert "29 September" in out, out
    assert "confirmed-incident register" in out, out
    assert not T.ARABIC.search(out), out


def test_translate_page_keeps_number_with_ltr_span():
    """موجب على مستوى الصفحة: العقدة بعد وسم ltr تُترجم كاملة مع رقمها."""
    frag = ('<div class="dg-v"><span class="ltr">IMO</span>'
            ' — سجل الحوادث المؤكدة؛ أحدث تاريخ ظاهر في القائمة هو 29 سبتمبر.</div>')
    page, missing, _total = T.translate_page(frag, DATE, T.build_tm(DATE), T.load_glossary())
    assert "29 September" in page, page
    assert not missing, missing


def test_dropped_number_is_fail_closed():
    """سالب: ترجمة تُسقط رقمًا من الأصل تُعدّ ناقصة وتُبلَّغ كي تمنع البناء."""
    frag = ('<div class="dg-v"><span class="ltr">IMO</span>'
            ' — سجل الحوادث المؤكدة؛ أحدث تاريخ ظاهر في القائمة هو 29 سبتمبر.</div>')
    tm = dict(T.build_tm(DATE))
    key = "IMO — سجل الحوادث المؤكدة؛ أحدث تاريخ ظاهر في القائمة هو 29 سبتمبر."
    tm[key] = "IMO — confirmed-incident register."  # ترجمة بلا الرقم
    _page, missing, _total = T.translate_page(frag, DATE, tm, T.load_glossary())
    assert missing, "يجب أن تُبلَّغ الوحدة التي فقدت رقمها"
    assert "29" in missing[0], missing