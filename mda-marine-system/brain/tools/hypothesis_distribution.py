#!/usr/bin/env python3
"""اشتقاق توزيع نقطي للفرضيات من نطاقات احتمالات معلنة.

القاعدة الحاكمة: منتصف كل نطاق، ثم إعادة تسوية المنتصفات إلى 100 بأكبر
البواقي، مع إبقاء النطاق الأصلي ظاهرًا كهامش. النتيجة نقاط مئوية صحيحة مجموعها 100.

الاستخدام:
  python3 tools/hypothesis_distribution.py --meta web/meta/2026-11-06.json --write
  python3 tools/hypothesis_distribution.py --meta web/meta/2026-11-06.json --check
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

RULE = "منتصف كل نطاق ثم إعادة تسوية إلى 100 بأكبر البواقي (largest remainder)؛ الإصدار 1"
RANGE_KIND = "range"
POINT_FROM_RANGE_KIND = "point_from_range"
SUPPORTED_OUTPUT_KIND = POINT_FROM_RANGE_KIND
RANGE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*–\s*(\d+(?:\.\d+)?)\s*%$")
POINT_RE = re.compile(r"^(\d+)%$")


class DistributionError(ValueError):
    """خطأ عقدي يمنع اشتقاقًا أو تحققًا غير قابل لإعادة التشغيل."""


def parse_range(value: Any) -> tuple[float, float]:
    """حلل نطاقًا عربيًا معياريًا وأعد الحدين بعد التحقق من المجال والترتيب."""
    raw = value if isinstance(value, str) else ""
    match = RANGE_RE.fullmatch(raw.strip())
    if not match:
        raise DistributionError(
            f"صيغة نطاق غير معيارية (رقمان بشرطة – ونسبة مئوية): {value!r}"
        )
    lower, upper = (float(part) for part in match.groups())
    if not (math.isfinite(lower) and math.isfinite(upper)):
        raise DistributionError(f"حدود النطاق غير منتهية: {value!r}")
    if not (0.0 <= lower <= 100.0 and 0.0 <= upper <= 100.0):
        raise DistributionError(f"حدود النطاق خارج 0–100: {value!r}")
    if lower >= upper:
        raise DistributionError(f"الحد الأدنى للنطاق يجب أن يكون أصغر من الأعلى: {value!r}")
    return lower, upper


def parse_point(value: Any) -> int:
    """حلل نسبة نقطية صحيحة بصيغة NN%."""
    raw = value if isinstance(value, str) else ""
    match = POINT_RE.fullmatch(raw.strip())
    if not match:
        raise DistributionError(f"صيغة نسبة نقطية غير معيارية (يجب NN%): {value!r}")
    point = int(match.group(1))
    if not 0 <= point <= 100:
        raise DistributionError(f"النسبة النقطية خارج 0–100: {value!r}")
    return point


def calculate_distribution(ranges: list[str]) -> list[int]:
    """احسب نقاطًا صحيحة من النطاقات بمنتصفها وأكبر البواقي.

    يبدأ الحساب بحصة كل منتصف من مجموع المنتصفات. ثم تُحوَّل الحصص إلى
    نقاط صحيحة بأكبر البواقي. النطاق الأصلي محفوظ كمرجع ظاهر ولا يُعاد
    تفسيره كقيد على النقطة بعد إعادة التسوية؛ وإلا تعذّر تطبيق قرار المالك
    المعتمد عندما تتجاوز مجموعات النطاقات 100 قبل إعادة التسوية.
    """
    if not ranges:
        raise DistributionError("لا توجد نطاقات للفرضيات")

    bounds = [parse_range(raw) for raw in ranges]
    midpoints = [(lower + upper) / 2.0 for lower, upper in bounds]
    midpoint_total = sum(midpoints)
    if not math.isfinite(midpoint_total) or midpoint_total <= 0:
        raise DistributionError("مجموع منتصفات النطاقات يجب أن يكون موجبًا")

    quotas = [(midpoint / midpoint_total) * 100.0 for midpoint in midpoints]
    floors = [math.floor(quota) for quota in quotas]
    allocation = floors[:]
    fractions = [quota - floor for quota, floor in zip(quotas, floors)]

    while sum(allocation) < 100:
        index = max(range(len(allocation)), key=lambda i: (fractions[i], -i))
        allocation[index] += 1

    while sum(allocation) > 100:
        index = min(range(len(allocation)), key=lambda i: (fractions[i], i))
        allocation[index] -= 1

    if sum(allocation) != 100:
        raise DistributionError("فشل ضمان مجموع التوزيع 100")
    return allocation


def _hypotheses(data: dict[str, Any]) -> list[dict[str, Any]]:
    hypotheses = data.get("hypotheses")
    if not isinstance(hypotheses, list) or not hypotheses:
        raise DistributionError("حقل hypotheses غير موجود أو فارغ")
    if not all(isinstance(item, dict) for item in hypotheses):
        raise DistributionError("كل فرضية يجب أن تكون كائنًا")
    return hypotheses


def _kind_set(hypotheses: list[dict[str, Any]]) -> set[Any]:
    return {item.get("likelihood_kind") for item in hypotheses}


def _source_ranges(hypotheses: list[dict[str, Any]]) -> list[str]:
    kinds = _kind_set(hypotheses)
    if len(kinds) != 1:
        raise DistributionError(f"خلط أنواع الاحتمال غير مسموح: {sorted(map(str, kinds))}")
    kind = next(iter(kinds))
    if kind == RANGE_KIND:
        values = [item.get("likelihood") for item in hypotheses]
    elif kind == POINT_FROM_RANGE_KIND:
        values = [item.get("likelihood_range") for item in hypotheses]
    else:
        raise DistributionError(f"نوع احتمال غير معتمد: {kind!r}")
    for value in values:
        parse_range(value)
    return [str(value) for value in values]


def _validate_stored(data: dict[str, Any]) -> list[int]:
    hypotheses = _hypotheses(data)
    kinds = _kind_set(hypotheses)
    if kinds != {SUPPORTED_OUTPUT_KIND}:
        if len(kinds) > 1:
            raise DistributionError(f"خلط أنواع الاحتمال غير مسموح: {sorted(map(str, kinds))}")
        raise DistributionError(f"نوع احتمال غير معتمد: {next(iter(kinds), None)!r}")
    if data.get("distribution_rule") != RULE:
        raise DistributionError("distribution_rule مفقود أو لا يطابق الإصدار المعتمد")
    ranges = []
    points = []
    for item in hypotheses:
        raw_range = item.get("likelihood_range")
        parse_range(raw_range)
        ranges.append(str(raw_range))
        points.append(parse_point(item.get("likelihood")))
    expected = calculate_distribution(ranges)
    if points != expected:
        raise DistributionError(f"النسب المخزنة {points} لا تساوي الاشتقاق {expected}")
    return expected


def check_data(data: dict[str, Any]) -> list[int]:
    """تحقق صارم من ملف واجهة مكتمل ومشتق."""
    return _validate_stored(data)


def write_data(data: dict[str, Any]) -> list[int]:
    """حوّل نطاقات المصدر إلى تمثيل نقطي مشتق، أو أعد اشتقاق تمثيل قائم."""
    hypotheses = _hypotheses(data)
    ranges = _source_ranges(hypotheses)
    points = calculate_distribution(ranges)
    for item, raw_range, point in zip(hypotheses, ranges, points):
        item["likelihood"] = f"{point}%"
        item["likelihood_range"] = raw_range
        item["likelihood_kind"] = SUPPORTED_OUTPUT_KIND
    data["distribution_rule"] = RULE
    return points


def load_meta(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DistributionError(f"الملف غير موجود: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DistributionError(f"JSON غير صالح: {exc}") from exc
    if not isinstance(data, dict):
        raise DistributionError("ملف الواجهة يجب أن يكون كائن JSON")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="اشتقاق توزيع احتمالات الفرضيات من نطاقاتها")
    parser.add_argument("--meta", required=True, help="مسار ملف الواجهة JSON")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true", help="اشتقاق القيم وكتابتها")
    modes.add_argument("--check", action="store_true", help="التحقق من القيم المخزنة")
    args = parser.parse_args(argv)
    path = Path(args.meta)
    try:
        data = load_meta(path)
        if args.write:
            points = write_data(data)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"✔ اشتُق توزيع الفرضيات: {', '.join(f'{point}%' for point in points)} · المجموع=100")
            print(f"   القاعدة: {RULE}")
            return 0
        points = check_data(data)
        print(f"✔ توزيع الفرضيات مطابق للاشتقاق: {', '.join(f'{point}%' for point in points)} · المجموع=100")
        return 0
    except DistributionError as exc:
        print(f"✘ فشل مغلق: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
