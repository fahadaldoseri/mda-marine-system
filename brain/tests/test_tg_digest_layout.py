#!/usr/bin/env python3
"""شكل رسالة تلغرام بعد ملاحظات المالك على رسالة التجربة (19 نوفمبر 2026).

يتحقق أن:
- رمز الواقعة بلا أقواس «…، الرمز MN-…» حتى لا ينقلب في السطر العربي،
- التاريخ الرقمي في آخر العنوان «· 18/11/2026» يصير «في 18 نوفمبر»،
- المؤشرات بصيغة «الاسم: العدد» وبالأسماء المختصرة،
- الإجراءات كلها مرقمة وبصيغة المصدر،
- سطر الوقائع الباقية بعبارة عربية سليمة لا «(و1 غيرها …)».
"""
import importlib.util
import os
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]
SITE = Path(os.environ.get("SITE_DIR") or B.parent / "site")


def main() -> int:
    if not (SITE / "generator" / "third_person.py").is_file():
        print("✘ خطأ بيئة: وحدة third_person.py غير موجودة")
        return 3
    os.environ.setdefault("SITE_DIR", str(SITE))
    spec = importlib.util.spec_from_file_location("mtd", B / "tools" / "make_tg_digest.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    meta = {
        "generated_label": "2026-11-19T04:00:00Z", "title": "التقرير اليومي",
        "version": "و ب 19/11/26", "threat_level": "مرتفع جدًا",
        "event_keys": [{"code": f"MN-2026-11-19-0{i}",
                        "title": f"هجوم — بلاغ رقم {i} · 18/11/2026"} for i in (1, 2, 3, 4)],
        "changes": [{"code": f"MN-2026-11-19-0{i}", "text": f"بلاغ رقم {i}"} for i in (1, 2, 3, 4)],
        "hero_kpis": [
            {"id": "ukmto-reports", "label": "البلاغات الرسمية الظاهرة في متن اليوم", "value": "5"},
            {"id": "qualifying-incidents", "label": "وقائع مستوفية لمعيار الاحتساب", "value": "4"},
            {"id": "unconfirmed-narratives", "label": "روايات لم تتأكد", "value": "2"},
        ],
        "decision_card": {"action": [
            "ارفعوا التأهب عند عبور المضيق.",
            "راجعوا آخر البلاغات، وأبلغوا فورًا عن أي إصابة.",
            "جهّزوا فرق مكافحة الحريق.",
        ]},
    }
    text = m.build(meta, "2026-11-19", "https://example.org", detail=False, max_items=2)
    fails = []
    checks = [
        ("الرمز بلا أقواس", "، الرمز MN-2026-11-19-01." in text and "(MN-" not in text),
        ("التاريخ بالحروف", "في 18 نوفمبر، الرمز" in text and "18/11/2026" not in text),
        ("المؤشرات المختصرة", "البلاغات الرسمية: 5 · الوقائع المحتسبة: 4 · روايات غير مؤكدة: 2" in text),
        ("الإجراءات الثلاثة", "1) رفع التأهب" in text and "2) مراجعة" in text
         and "والإبلاغ فورًا" in text and "3) تجهيز" in text),
        ("الوقائع الباقية", "وواقعة أخرى في التقرير الكامل." in text and "غيرها" not in text),
        ("لا فعل أمر", not m.imperative_violations(text)),
    ]
    for name, ok in checks:
        print(("  ✔ " if ok else "  ✘ ") + name)
        if not ok:
            fails.append(name)
    if fails:
        print(text)
        return 1
    print(f"✔ شكل رسالة تلغرام مطابق لملاحظات المالك ({len(checks)}/{len(checks)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
