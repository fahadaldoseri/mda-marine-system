#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار لبوابة تغطية المصادر: لا يُقبل المصدر المعطّل إلا بإعلان عطل عابر مُهَل.

الغرض: منع الانزلاق إلى «منع دائم» أو إلى «إفصاح بلا دليل». البوابة تمنع عند:
  · عدد المعطّل أكبر من سقف الإعلان
  · إعلان منتهي المهلة
  · سبب لا يطابق أنماط الإعلان (عطل ليس نقلًا)
  · غياب سبب مقيس في ملف حالة الفحص

الاستعمال: python3 tests/test_source_coverage_transient.py    رمز 0 سليم · 1 فشل
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile

B = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "check_source_daily_coverage", B / "validators" / "check_source_daily_coverage.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)  # type: ignore[union-attr]

DATE = "2026-11-05"


def make_brain(expires: str = "2026-11-30", patterns: list[str] | None = None,
               reasons: dict[int, str] | None = None, with_status: bool = True) -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="src-cov-"))
    (root / "appendices").mkdir(parents=True)
    (root / "appendices" / "known-faults.json").write_text(json.dumps({
        "version": 1,
        "allowed": [{
            "id": "transport-transient",
            "reason_ar": "عطل اتصال مؤقت في جلب مصدرين أو أقل",
            "applies_to": ["feeds"],
            "reason_patterns": patterns if patterns is not None else ["ssl", "connection", "timeout", "dns"],
            "max_items": 2,
            "expires": expires,
            "fault_ref": "ك-137",
            "reason_ar_full": "عطل اتصال مؤقت في جلب مصدرين أو أقل — مرجع العطل ك-137",
        }],
    }, ensure_ascii=False), encoding="utf-8")
    if with_status:
        (root / "feeds").mkdir(parents=True)
        rows = [
            {"num": num, "ok": False, "block_reason": reason}
            for num, reason in (reasons or {27: "all routes failed: primary: ssl UNEXPECTED_EOF"}).items()
        ]
        (root / "feeds" / f"feeds-{DATE}.status.json").write_text(
            json.dumps({"checked_feeds": rows}, ensure_ascii=False), encoding="utf-8")
    return root


def result_with(nums: list[int]) -> dict:
    """نتيجة قياس مكتملة الحقول كما تنتجها أداة القياس، والمعطّل فيها أرقام الحالة."""
    disabled = {int(n) for n in nums}
    sources = [
        {"num": n, "route_state": "معطّل" if n in disabled else "مسار آلي"}
        for n in range(1, 63)
    ]
    return {
        "sources": sources,
        "approved_source_count": 62,
        "checked_union_manual_count": 62,
        "checked_unique_count": 60,
        "status_declared_checked": 60,
        "checked_missing_sources": [],
        "checked_unknown_sources": [],
        "manual_reference": [39, 52],
        "status_manual_reference": [39, 52],
        "manual_reference_reasons": {"39": "سبب", "52": "سبب"},
    }


CASES = []


def case(name: str, nums: list[int], brain: pathlib.Path, expect_block: bool):
    CASES.append((name, nums, brain, expect_block))


case("موجب: مصدر معطّل واحد بإعلان سارٍ ودليل نقل", [27], make_brain(), False)
case("سالب: ثلاثة معطّلين فوق سقف الإعلان", [27, 24, 17], make_brain(
    reasons={27: "ssl", 24: "connection reset", 17: "dns timeout"}), True)
case("سالب: إعلان منتهي المهلة", [27], make_brain(expires="2026-11-01"), True)
case("سالب: سبب لا يطابق أنماط النقل", [27], make_brain(
    reasons={27: "HTTP 404 page not found"}), True)
case("سالب: بلا ملف حالة (لا دليل مقيس)", [27], make_brain(with_status=False), True)


def main() -> int:
    failures = []
    for name, nums, brain, expect_block in CASES:
        res = result_with(nums)
        problems = gate.validate(res, brain, DATE)
        blocked = bool(problems)
        ok = blocked == expect_block
        disclosed = bool(res.get("disclosed_transient"))
        if not ok or (expect_block is False and not disclosed):
            failures.append(name)
        print(f"   {'✔' if ok and (expect_block or disclosed) else '✘'} {name} — "
              f"{'منع' if blocked else 'مرور مُفصح'} · "
              f"{problems[0][:70] if problems else 'لا موانع'}")
    print(f"   النتيجة: {'مجتاز' if not failures else 'فاشل'} · حالات={len(CASES)} · فشل={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
