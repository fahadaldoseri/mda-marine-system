#!/usr/bin/env python3
"""مطابقة مجموع محسوب من سجلات الدفتر برقم رسمي معلن.

الغاية: لا يُعلن رقم تراكمي إلا بعد مطابقته بالمصدر الرسمي، مع تفسير أي فرق
بفئة صحيحة (مثل استبعاد غير البحّارة) لا بتقدير.

استعمال:
  reconcile_totals.py --records FILE --field casualties.fatalities [--declared 24]
                      [--exclude "class=shipyard_worker"] [--json]

ملاحظات:
  - يقبل ملفًا قائمة، أو قاموسًا فيه records/events/items/incidents/rows.
  - الحقل يُكتب بمسار نقطي: casualties.fatalities أو fatalities.
  - --exclude يُكرَّر: يستبعد السجلات التي يساوي فيها حقلٌ قيمةً معيّنة،
    ويُعرض أثر الاستبعاد منفصلًا.
  - القيمة الغائبة لا تُحسب صفرًا؛ تُعدّ «غير معلنة» وتُعرض في العمود الخاص.
رمز الخروج: 0 تطابق · 2 اختلاف أو غياب رقم معلن.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

RECORD_KEYS = ("records", "events", "items", "incidents", "rows", "entries")


def load_records(path: pathlib.Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in RECORD_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                return value
        collected = []
        for value in data.values():
            if isinstance(value, list):
                collected.extend(value)
            elif isinstance(value, dict):
                collected.append(value)
        return collected
    raise ValueError("بنية ملف غير مفهومة")


def get_path(record, dotted: str):
    """يعيد القيمة في مسار نقطي، أو None إن غابت."""
    node = record
    for part in dotted.split("."):
        if isinstance(node, dict):
            if part not in node:
                return None
            node = node[part]
        else:
            return None
    return node


def to_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        try:
            return float(text)
        except ValueError:
            return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="مطابقة مجموع الدفتر برقم رسمي معلن")
    parser.add_argument("--records", required=True, help="ملف السجلات (JSON)")
    parser.add_argument("--field", required=True, help="مسار الحقل النقطي المراد جمعه")
    parser.add_argument("--declared", type=float, default=None, help="الرقم الرسمي المعلن")
    parser.add_argument("--exclude", action="append", default=[],
                        help='استبعاد فئة: "class=shipyard_worker" (يُكرَّر)')
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = pathlib.Path(args.records).expanduser().resolve()
    if not path.is_file():
        print(f"✘ ملف السجلات غير موجود: {path}", file=sys.stderr)
        return 2
    try:
        records = load_records(path)
    except Exception as exc:
        print(f"✘ تعذّرت قراءة السجلات: {exc}", file=sys.stderr)
        return 2

    excludes = []
    for item in args.exclude:
        if "=" not in item:
            print(f"✘ صيغة استبعاد غير صحيحة: {item}", file=sys.stderr)
            return 2
        key, value = item.split("=", 1)
        # البدائل تُفصل بخط عمودي: "class=a|b" لتغطية اختلاف الترميز بين اللغات.
        alternatives = [part.strip().lower() for part in value.split("|") if part.strip()]
        if not alternatives:
            print(f"✘ استبعاد بلا قيمة: {item}", file=sys.stderr)
            return 2
        excludes.append((key.strip(), alternatives))

    def is_duplicate(record):
        """صف مُعلن تكرارًا لواقعة أخرى: لا يُحتسب، ويُحفظ للتوثيق."""
        if record.get("duplicate_of") or record.get("is_duplicate") is True:
            return True
        return record.get("counted") is False

    def is_excluded(record):
        for key, alternatives in excludes:
            got = get_path(record, key)
            if got is not None and str(got).strip().lower() in alternatives:
                return True
        return False

    total = 0.0
    counted = 0
    undeclared = 0
    excluded_sum = 0.0
    excluded_count = 0
    duplicate_sum = 0.0
    duplicate_count = 0

    for record in records:
        if not isinstance(record, dict):
            continue
        value = to_number(get_path(record, args.field))
        if value is None:
            undeclared += 1
            continue
        if is_duplicate(record):
            duplicate_sum += value
            duplicate_count += 1
            continue
        if is_excluded(record):
            excluded_sum += value
            excluded_count += 1
            continue
        total += value
        counted += 1

    after = total - excluded_sum  # المجموع قبل الاستبعاد ناقص المستبعد
    # الإجمالي الخام = المحتسب + المستبعد بفئة + المُعلن تكرارًا
    gross = total + excluded_sum + duplicate_sum

    declared = args.declared
    match = (declared is not None) and (abs(total - declared) < 1e-9)
    match_gross = (declared is not None) and (abs(gross - declared) < 1e-9)

    if args.json:
        print(json.dumps({
            "field": args.field, "records": len(records),
            "counted_records": counted, "undeclared_records": undeclared,
            "sum_after_exclusions": total, "sum_before_exclusions": gross,
            "excluded_records": excluded_count, "excluded_sum": excluded_sum,
            "duplicate_records": duplicate_count, "duplicate_sum": duplicate_sum,
            "declared": declared, "match": match, "match_before_exclusions": match_gross,
            "difference": None if declared is None else total - declared,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"   الحقل: {args.field} · سجلات الملف: {len(records)}")
        print(f"   سجلات محسوبة: {counted} · بلا قيمة معلنة: {undeclared}")
        if duplicate_count:
            print(f"   مُعلن تكرارًا (لا يُحتسب): {duplicate_count} سجلًا بمجموع {duplicate_sum:g}")
        if excludes:
            print(f"   مستبعد: {excluded_count} سجلًا بمجموع {excluded_sum:g}")
            print(f"   المجموع قبل الاستبعاد: {gross:g} · بعد الاستبعاد: {total:g}")
        else:
            print(f"   المجموع: {total:g} · الخام مع التكرار: {gross:g}")
        if declared is None:
            print("   ⚠ لم يُعطَ رقم رسمي معلن للمطابقة")
        else:
            print(f"   المعلن رسميًا: {declared:g} · الفرق: {total - declared:+g}")
            if match:
                print("   ✔ تطابق المجموع مع الرقم الرسمي")
            elif match_gross:
                print("   ✔ تطابق المجموع الخام مع الرقم الرسمي (والاستبعاد يفسّر الفئة)")
            else:
                print("   ✘ اختلاف يحتاج تفسيرًا بفئة صحيحة لا بتقدير")

    if declared is None:
        return 2
    return 0 if (match or match_gross) else 2


if __name__ == "__main__":
    sys.exit(main())
