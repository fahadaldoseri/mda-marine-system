#!/usr/bin/env python3
"""سطر «الإجراء المطلوب» في رسالة تلغرام بصيغة المصدر لا الأمر (قرار المالك، 19 نوفمبر 2026).

يبني الرسالة لمعطيات فيها بنود أمر («ارفعوا…»، «راجعوا… وأبلغوا…») ويتحقق أن:
- السطر يبدأ بالمصدر («رفع التأهب…») ولا يبقى فيه فعل أمر،
- لا تظهر البادئة «نفّذوا —»،
- الحارس يكشف الفعل المسبوق بواو العطف («وأبلغوا»).
"""
import importlib.util
import os
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]
SITE = Path(os.environ.get("SITE_DIR") or B.parent / "site")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    tp_path = SITE / "generator" / "third_person.py"
    if not tp_path.is_file():
        print(f"✘ خطأ بيئة: {tp_path} غير موجود")
        return 3
    os.environ.setdefault("SITE_DIR", str(SITE))
    tp = load("tp", tp_path)
    dig = load("dig", B / "tools" / "make_tg_digest.py")
    fails = []
    cases = {
        "ارفعوا التأهب عند عبور مضيق هرمز، وخاصة بين 6 و13 ميلًا بحريًا شمال خصب.":
            "رفع التأهب عند عبور مضيق هرمز، وخاصة بين 6 و13 ميلًا بحريًا شمال خصب.",
        "راجعوا آخر بلاغات UKMTO قبل كل عبور، وأبلغوا فورًا عن أي إصابة.":
            "مراجعة آخر بلاغات UKMTO قبل كل عبور، والإبلاغ فورًا عن أي إصابة.",
        "عزّزوا المراقبة في بحر العرب.": "تعزيز المراقبة في بحر العرب.",
        "ترفع السفن التأهب عند عبور مضيق هرمز.": "ترفع السفن التأهب عند عبور مضيق هرمز.",
    }
    for src, want in cases.items():
        got = dig.action_line(src)
        if got != want:
            fails.append(f"المصدر: «{got}» ≠ «{want}»")
        if tp.masdar_leftovers(got):
            fails.append(f"بقي فعل أمر: {tp.masdar_leftovers(got)}")
    if "وأبلغوا" not in tp.masdar_leftovers("راجعوا البلاغ، وأبلغوا فورًا"):
        fails.append("الحارس لا يكشف «وأبلغوا»")
    meta = {"title": "ت", "version": "و ب 1", "generated_label": "2026-11-19T03:40:00Z", "threat_level": "متوسط",
            "changes": [], "decision_card": {"action": ["ارفعوا التأهب عند عبور مضيق هرمز."]}}
    try:
        text = dig.build(meta, "2026-11-19", "https://mda-bh.pages.dev")
    except Exception as exc:  # noqa: BLE001
        fails.append(f"تعذّر البناء: {exc}")
        text = ""
    if "نفّذوا" in text:
        fails.append("بقيت البادئة «نفّذوا —»")
    if "رفع التأهب عند عبور مضيق هرمز." not in text:
        fails.append("سطر الإجراء ليس بصيغة المصدر")
    for f in fails:
        print("✘", f)
    if not fails:
        print("✔ سطر الإجراء في رسالة تلغرام بصيغة المصدر، والحارس يكشف أفعال الأمر المعطوفة")
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
