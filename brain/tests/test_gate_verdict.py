#!/usr/bin/env python3
"""اختبار حكم البوابات (ك-325): الحكم يُقرأ سطرًا لا ذِكرًا داخل وصف اختبار.

الإيجابية الكاذبة التي أُغلقت: سطر اختبار في سجل G001 يقول
«5) رمز الانهيار 70 (حارس موحّد) يمنع التسليم» فصار السجل كله «مانعًا» وأوقف النشر.
"""
from __future__ import annotations
import pathlib
import sys

B = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B / "tools"))
import gate_verdict as gv  # noqa: E402

CASES = [
    # (الوصف، نص السجل، هل يجب أن يُعدّ حكمًا مانعًا)
    ("وصف اختبار فيه «يمنع التسليم»",
     "5) رمز الانهيار 70 (حارس موحّد) يمنع التسليم\n  ✔ عطل غير معروف في القائمة يمنع التسليم (=2)", False),
    ("حكم صريح بعد وسم",
     "   الحكم: ممنوع التسليم — أصلح الفشل أولًا", True),
    ("حكم صريح بلا وسم",
     "ممنوع التسليم", True),
    ("حكم بصيغة «منع التسليم»",
     "   النتيجة: منع التسليم (3 بوابات)", True),
    ("مخالفة مانعة بعدد موجب",
     "   مخالفة مانعة: 2", True),
    ("مخالفة مانعة بصفر لا تمنع",
     "   مخالفة مانعة: 0", False),
    ("سجل ناجح",
     "   ----- الحصيلة -----\n     نجح: 55 · فشل: 0", False),
]


def main() -> int:
    bad = 0
    for desc, text, want in CASES:
        got = bool(gv.blocking_in_log(text))
        mark = "✔" if got == want else "✘"
        if got != want:
            bad += 1
        print(f"  {mark} {desc}: مانع={got} (المتوقع {want})")
    print(f"  الحصيلة: {'كل الحالات صحيحة' if not bad else f'{bad} حالة خاطئة'}")
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
