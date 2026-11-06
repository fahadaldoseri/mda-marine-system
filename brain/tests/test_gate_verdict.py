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


def test_gate_log_stale_after_delivery_prep_is_blocked():
    """لا يُعاد استعمال حكم بوابة سبقته خطوة غيّرت مدخلاتها قبل D010."""
    journal = {
        "G011": {"status": "done_warn", "ts": "2026-11-06T08:37:25Z"},
        "B010": {"status": "done", "ts": "2026-11-06T12:49:46Z"},
        "D005": {"status": "done", "ts": "2026-11-06T17:39:32Z"},
    }
    manifest = [
        {"id": "G011", "phase": "gates"},
        {"id": "B010", "phase": "build"},
        {"id": "D005", "phase": "deliver"},
        {"id": "D010", "phase": "deliver"},
    ]
    reason = gv.stale_gate_reason("G011", journal, manifest, "D010")
    assert reason and "B010" in reason


def test_gate_log_current_after_delivery_prep_is_not_stale():
    journal = {
        "G011": {"status": "done", "ts": "2026-11-06T20:43:00Z"},
        "D005": {"status": "done", "ts": "2026-11-06T17:39:32Z"},
    }
    manifest = [
        {"id": "G011", "phase": "gates"},
        {"id": "D005", "phase": "deliver"},
        {"id": "D010", "phase": "deliver"},
    ]
    assert gv.stale_gate_reason("G011", journal, manifest, "D010") == ""


def main() -> int:
    bad = 0
    for desc, text, want in CASES:
        got = bool(gv.blocking_in_log(text))
        mark = "✔" if got == want else "✘"
        if got != want:
            bad += 1
        print(f"  {mark} {desc}: مانع={got} (المتوقع {want})")
    try:
        test_gate_log_stale_after_delivery_prep_is_blocked()
        print("  ✔ سجل G011 القديم بعد B010/D005 يُمنع")
        test_gate_log_current_after_delivery_prep_is_not_stale()
        print("  ✔ سجل G011 الحديث بعد B010/D005 لا يُمنع بقدم السجل")
    except AssertionError as exc:
        bad += 1
        print(f"  ✘ اختبار صلاحية سجل البوابة: {exc}")
    except AttributeError as exc:
        bad += 1
        print(f"  ✘ عقد صلاحية سجل البوابة غير موجود: {exc}")
    print(f"  الحصيلة: {'كل الحالات صحيحة' if not bad else f'{bad} حالة خاطئة'}")
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
