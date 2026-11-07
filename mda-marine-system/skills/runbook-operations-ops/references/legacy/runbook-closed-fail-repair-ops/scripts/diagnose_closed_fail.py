#!/usr/bin/env python3
"""تشخيص توقف الكتيب برمز 2 (فشل مغلق) أو 1 (فشل اختبار) وتصنيف الإصلاح المقترح.

قراءة فقط: يقرأ سجل التشغيل الأخير، ويستخرج الخطوة الفاشلة ورمز الخروج،
ويطبع ذيل سجل الخطوة، ويصنّف المنع من **أسطر الفشل وحدها** إلى أحد الأصناف الأربعة.

رموز الخروج:
  0 = وُجد توقف فاشل وصُنّف
  1 = لا يوجد توقف فاشل في السجل المعطى
  2 = وسيط غير صالح أو ملف غير موجود
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

# الأنماط تُطبَّق على أسطر الفشل وحدها (سطور تبدأ بـ✘ أو تليها تفاصيلها)
PATTERNS = [
    (
        "تعارض سجل بيانات مع الدفتر",
        [r"يوم موسوم no_material وله مادة", r"no_material"],
        "عدّل سجل الاستثناءات (cumulative-2026/no-material.json أو مثيله) ليطابق الواقع الموثّق، "
        "ولا تحذف وقائع رسمية. أعد تشغيل الحارس وحده قبل إعادة الكتيب.",
    ),
    (
        "حلقة إغلاق غير مكتملة",
        [r"الحلقة غير مغلقة", r"مغلق بلا درس مطابق", r"مغلق بمعرّف حاجز غير صالح"],
        "أكمل الحلقة: شغّل python3 tools/closure_round.py --apply، وأضف درسًا مطابقًا لكل عطل مغلق "
        "بلا درس في memory/learning-log.jsonl، ثم أعد validators/check_closure.py حتى «النتيجة: مجتاز».",
    ),
    (
        "نقص في أرضية الأصول الحاكمة",
        [r"أصل حاكم مفقود أو خارج النطاق", r"نقص في أصل معتمد", r"النتيجة: منع — نقص"],
        "استعد الملف المفقود من المرآة /home/ubuntu/mda-marine-system ثم من تاريخ Git، "
        "ولا تُدرج المستعاد في قرار القبول.",
    ),
    (
        "أرضية متقادمة لتعديل مقصود",
        [r"قرار على مسار غير معروف في الأرضية", r"نقص مقبول"],
        "سجّل قرارًا صريحًا بالسبب: python3 validators/check_asset_floor.py "
        "--decisions <file> --reason \"<سبب + دليل المزامنة>\" ثم --update.",
    ),
    (
        "عطل حقيقي في شيفرة أو اختبار",
        [r"Traceback", r"NameError", r"ModuleNotFoundError", r"SyntaxError",
         r"AssertionError", r"FAILED", r"فشل:", r"رمز 1\):"],
        "أصلح الشيفرة أو الاختبار، وأضف اختبار انحدار، واربطه بالمانيفست، ثم أعد الكتيب.",
    ),
]

FAIL_RE = re.compile(r"✘ توقف عند ([A-Za-z0-9_]+): رمز الخروج (\d+)")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False
    )
    parser.add_argument("--brain", required=True, type=pathlib.Path, help="جذر مشروع العقل")
    parser.add_argument("--date", required=True, help="تاريخ التشغيل YYYY-MM-DD")
    parser.add_argument("--log", type=pathlib.Path, default=None, help="سجل التشغيل (افتراضي /tmp/rb-<date>.log)")
    parser.add_argument("--tail", type=int, default=25, help="عدد أسطر ذيل سجل الخطوة")
    return parser.parse_args(argv)


def failure_lines(text: str) -> list[str]:
    """أسطر الفشل وحدها: كل سطر يبدأ بـ✘ مع أسطر التفاصيل التابعة له."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("✘") or stripped.startswith("✗"):
            out.append(stripped)
        elif out and stripped and not stripped.startswith(("✔", "▶", "-----", "نجح:", "الحصيلة")):
            out.append(stripped)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    brain: pathlib.Path = args.brain
    try:
        ok_brain = brain.is_dir()
    except OSError as exc:
        print(f"   ✘ تعذّر قراءة الجذر: {brain} ({exc.__class__.__name__})")
        return 2
    if not ok_brain:
        print(f"   ✘ جذر غير صالح: {brain}")
        return 2

    log = args.log or pathlib.Path(f"/tmp/rb-{args.date}.log")
    if not log.is_file():
        print(f"   ✘ سجل التشغيل غير موجود: {log}")
        return 2

    text = log.read_text(encoding="utf-8", errors="replace")
    matches = FAIL_RE.findall(text)
    if not matches:
        print("   ✔ لا يوجد سطر توقف فاشل في السجل المعطى.")
        return 1

    step, code = matches[-1]
    print(f"   ══ الخطوة الفاشلة: {step} · رمز الخروج: {code} ══")

    step_log = brain / "logs" / "runbook" / args.date / f"{step}.log"
    step_text = ""
    if step_log.is_file():
        step_text = step_log.read_text(encoding="utf-8", errors="replace")
        print(f"   ── ذيل سجل الخطوة ({step_log}) ──")
        for line in step_text.splitlines()[-args.tail :]:
            print("   " + line[:190])
    else:
        print(f"   ⚠ لا سجل للخطوة في: {step_log}")

    haystack = "\n".join(failure_lines(step_text) + failure_lines(text))
    print("   ── التصنيف (من أسطر الفشل) ──")
    for name, patterns, fix in PATTERNS:
        if any(re.search(p, haystack) for p in patterns):
            print(f"   ▸ الصنف: {name}")
            print(f"     الإصلاح: {fix}")
            return 0
    print("   ▸ الصنف: غير مصنّف — اقرأ مخرج الخطوة الحرفي وأضف نمطًا جديدًا إلى الأداة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
