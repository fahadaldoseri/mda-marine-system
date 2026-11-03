#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار بوابة عقد بطاقة سجل الأحداث: موجب · سالب · مفقود (فشل مغلق)."""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_event_card_contract", ROOT / "validators" / "check_event_card_contract.py")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  ✔ {name}")


def bad(name: str, detail: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  ✘ {name} — {detail}")


def check(name: str, condition: bool, detail: str = "") -> None:
    ok(name) if condition else bad(name, detail)


def row(number: int, label: str, value: str, *, state: str = "shown", extra: str = "") -> str:
    hidden = "" if state == "shown" else " hidden"
    return (f'<div class="ev-field" data-row="{number}" data-row-state="{state}"{hidden}>'
            f'<span class="ev-k">{label}</span><span class="ev-mv">{value}</span>{extra}</div>')


def card(**changes) -> str:
    body = (
        '<article class="ev reveal b-official" id="ev-01" data-event-code="MN-2026-11-01-01" '
        'data-event-date="2026-11-01" data-event-has-time="0" data-relation-key="" data-event-rows="10">'
        '<div class="ev-top"><span class="ev-idx bidi">01</span>'
        '<span class="ev-code ltr">MN-2026-11-01-01</span>'
        '<span class="ev-badge" data-row="2" data-classification="بلاغ رسمي">بلاغ رسمي</span>'
        '<span class="ev-reliability" data-row="3" data-reliability="متوسطة">درجة الموثوقية: متوسطة</span></div>'
        '<p class="ev-what" data-row="1">تحذير UKMTO رقم 190-26</p><div class="ev-meta">'
        + row(4, "التاريخ والوقت", "2026-11-01")
        + row(5, "الموقع", "Z1 · مضيق هرمز")
        + row(6, "المصدر", "حساب UKMTO")
        + row(7, "الرابط الرسمي", "", state="hidden-rule-no-official-link")
        + row(8, "ترجمة المعنى", "الترجمة غير مدرجة في الدفتر")
        + row(9, "النص الأصلي", "مطويّ — افتح للعرض",
              extra='<details class="ev-fold" data-fold="original-text"><summary>النص الأصلي كما في المصدر</summary>'
                    '<span>UKMTO WARNING 190-26</span></details>')
        + '<div class="ev-field" data-row="10" data-row-state="shown" data-branch-status="not-marked">'
          '<span class="ev-k">فرع تابع</span>'
          '<span class="ev-mv">لم يُعثر على الواقعة السابقة في الدفتر المتاح</span></div>'
        + '</div></article>')
    for key, value in changes.items():
        if key == "drop_row":
            body = re.sub(rf'<div class="ev-field" data-row="{value}"[^>]*>.*?</div>',
                          "", body, count=1, flags=re.S)
        else:
            body = body.replace(key, value)
    return body


def main() -> int:
    good = card()
    check("بطاقة مطابقة للعقد تجتاز", GATE.card_violations(good, 1) == [],
          str(GATE.card_violations(good, 1)))
    missing_row = GATE.card_violations(card(drop_row=6), 1)
    check("صف ناقص يُمنع", any("صفوف غائبة" in e for e in missing_row), str(missing_row))
    check("تصنيف خارج القائمة المغلقة يُمنع",
          any("تصنيف خارج" in e for e in GATE.card_violations(
              card(**{'data-classification="بلاغ رسمي"': 'data-classification="تصنيف مخترع"'}), 1)))
    check("موثوقية خارج القائمة المغلقة تُمنع",
          any("موثوقية خارج" in e for e in GATE.card_violations(
              card(**{'data-reliability="متوسطة"': 'data-reliability="مؤكدة"'}), 1)))
    check("شارة الموثوقية الغائبة تُمنع",
          any("درجة الموثوقية غائبة" in e for e in GATE.card_violations(
              card(**{'data-reliability="متوسطة"': 'data-x="y"'}), 1)))
    check("وسم صف مخالف للعقد يُمنع",
          any("لا يطابق العقد" in e for e in GATE.card_violations(
              card(**{'<span class="ev-k">الموقع</span>': '<span class="ev-k">المكان</span>'}), 1)))
    check("مصدر باسم حساب (@) بلا رابط يُمنع",
          any("بلا رابط" in e for e in GATE.card_violations(
              card(**{'<span class="ev-mv">حساب UKMTO</span>':
                      '<span class="ev-mv">حساب @UK_MTO على X</span>'}), 1)))
    check("رابط مختصر ظاهر يُمنع",
          any("رابط مختصر" in e for e in GATE.card_violations(
              card(**{'<span>UKMTO WARNING 190-26</span>':
                      '<span>UKMTO WARNING https://t.co/abc</span>'}), 1)))
    check("وسم (#) ظاهر يُمنع",
          any("وسم (#)" in e for e in GATE.card_violations(
              card(**{'<span>UKMTO WARNING 190-26</span>':
                      '<span>UKMTO WARNING #MarSec</span>'}), 1)))
    # ك-471: الكيانات المشفّرة ليست وسومًا مرئية، والوسم الحقيقي يبقى ممنوعًا.
    check("كيان &#x27; لا يُعدّ وسمًا",
          not any("وسم (#)" in e for e in GATE.card_violations(
              card(**{'<span>UKMTO WARNING 190-26</span>':
                      "<span>Lloyd&#x27;s List — Yemen&#x27;s coast</span>"}), 1)))
    check("وسم # حقيقي يبقى ممنوعًا بعد فك الترميز",
          any("وسم (#)" in e for e in GATE.card_violations(
              card(**{'<span>UKMTO WARNING 190-26</span>':
                      '<span>UKMTO WARNING &#35;MarSec</span>'}), 1)))
    check("عرض المسار الداخلي يُمنع",
          any("المسار الداخلي" in e for e in GATE.card_violations(
              card(**{'<p class="ev-what" data-row="1">تحذير UKMTO رقم 190-26</p>':
                      '<p class="ev-what" data-row="1">تحذير UKMTO رقم 190-26 '
                      '<span>مسار التحقق الداخلي</span></p>'}), 1)))
    check("صف النص الأصلي ظاهرًا بلا طيّ يُمنع",
          any("بلا طيّ" in e for e in GATE.card_violations(
              card(**{'data-fold="original-text"': 'data-fold="y"'}), 1)))
    check("حالة صف غير معروفة تُمنع",
          any("حالة غير معروفة" in e for e in GATE.card_violations(
              card(**{'data-row-state="shown" data-branch-status="not-marked"':
                      'data-row-state="hidden-rule-unknown" data-branch-status="not-marked"'}), 1)))
    errors, codes = GATE.page_violations("<html><body>لا بطاقات</body></html>", "اختبار")
    check("صفحة بلا بطاقات تُمنع", bool(errors) and codes == [], str(errors))
    errors, codes = GATE.page_violations(f"<html>{card()}{card()}</html>", "اختبار")
    check("رمز بطاقة مكرر يُمنع", any("مكررة" in e for e in errors), str(errors))
    single_errors, single_codes = GATE.page_violations(f"<html>{card()}</html>", "اختبار")
    check("بطاقة سليمة تعطي رمزًا واحدًا", single_codes == ["MN-2026-11-01-01"], str(single_codes))
    check("صفحة ببطاقة سليمة لا مخالفات", single_errors == [], str(single_errors))
    check("وسوم النسخة الإنجليزية مقروءة",
          GATE.card_violations(
              card(**{'<span class="ev-k">التاريخ والوقت</span>': '<span class="ev-k">Date and time</span>',
                      '<span class="ev-k">الموقع</span>': '<span class="ev-k">Location</span>',
                      '<span class="ev-k">المصدر</span>': '<span class="ev-k">Source and grade</span>',
                      '<span class="ev-k">الرابط الرسمي</span>': '<span class="ev-k">Official link</span>',
                      '<span class="ev-k">ترجمة المعنى</span>': '<span class="ev-k">Meaning translation</span>',
                      '<span class="ev-k">النص الأصلي</span>': '<span class="ev-k">Original text</span>',
                      '<span class="ev-k">فرع تابع</span>': '<span class="ev-k">Parent report</span>'}), 1,
              GATE.EN_ROW_LABELS) == [])

    print(f"  نجح {PASS} · فشل {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
