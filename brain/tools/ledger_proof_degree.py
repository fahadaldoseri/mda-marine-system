#!/usr/bin/env python3
"""انقل درجة الإثبات من event_keys في الواجهة إلى دفتر اليوم بلا اختلاق.

المصدر الوحيد للقيمة هو `web/meta/<DATE>.json -> event_keys[].status`، والمطابقة
بـ `code` فقط. السجل الذي لا توجد له حالة يبقى بلا proof_degree ويظهر في التقرير.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

SUPPORTED_DATES = {"2026-10-31", "2026-11-03", "2026-11-04"}
# القيم المعتمدة التي ظهرت في عقد اليوم؛ تُحفظ الصيغة المصدرية ولا تُعاد صياغتها.
PROOF_DEGREES = {
    "نص رسمي كامل",
    "بلاغ رسمي غير مفصَّل",
    "بلاغ رسمي والنص غير متاح",
    "غير مؤكد من طرف واحد",
    "غير مؤكد بانتظار بيان رسمي",
    "غير مؤكد رسميًا",
    "موقف سياسي لا يُحتسب واقعة",
    "معلومة ناقصة تحت المراقبة",
    "نقل بري غير مؤكد",
    # صيغ مصدرية قائمة في الأيام المطلوبة؛ لا تُحوّل بالتخمين.
    "بلاغ رسمي",
    "بلاغ رسمي متأخر",
    "نقل مهني؛ مرجح",
    "نقل إعلامي غير مؤكد",
    "بلاغ طرفي غير مؤكد",
    "بلاغ رسمي، والنص غير متاح",
    "غير مؤكد",
    "غير مؤكد ولا يمس الملاحة",
    "تحذير أمني بحري، والنص الكامل والموقع غير متاحين",
    "بلاغ رسمي مختصر، والموقع الكامل والتفاصيل غير متاحة",
    "بلاغ غير مؤكد رسميًا",
}


class ProofDegreeError(ValueError):
    """خطأ يمنع النقل عند فساد المصدر أو بنية السجل."""


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProofDegreeError(f"تعذّرت قراءة {path}: {exc}") from exc


def _rows_container(ledger: Any) -> tuple[list[dict[str, Any]], str]:
    if isinstance(ledger, list):
        rows = ledger
        return rows, "list"
    if isinstance(ledger, dict) and isinstance(ledger.get("events"), list):
        return ledger["events"], "events"
    raise ProofDegreeError("جذر دفتر اليوم يجب أن يكون قائمة أو كائنًا يحوي events")


def apply_day(root: Path, date: str, *, write: bool = False) -> dict[str, Any]:
    if date not in SUPPORTED_DATES:
        raise ProofDegreeError(f"التاريخ خارج نطاق قرار المالك: {date}")
    ledger_path = root / "cumulative-2026" / "daily" / f"{date}.json"
    meta_path = root / "web" / "meta" / f"{date}.json"
    ledger = _read(ledger_path)
    meta = _read(meta_path)
    rows, _ = _rows_container(ledger)
    keys = meta.get("event_keys") if isinstance(meta, dict) else None
    if not isinstance(keys, list):
        raise ProofDegreeError("event_keys غير موجودة أو ليست قائمة")

    statuses: dict[str, str | None] = {}
    for item in keys:
        if not isinstance(item, dict) or not isinstance(item.get("code"), str):
            raise ProofDegreeError("كل event_keys يحتاج code نصيًا")
        code = item["code"]
        if code in statuses:
            raise ProofDegreeError(f"رمز مكرر في event_keys: {code}")
        status = item.get("status")
        statuses[code] = status if isinstance(status, str) and status.strip() else None

    output = copy.deepcopy(ledger)
    out_rows, _ = _rows_container(output)
    seen_ledger: set[str] = set()
    unavailable: list[dict[str, str]] = []
    updated = 0
    unchanged = 0
    for row in out_rows:
        if not isinstance(row, dict) or not isinstance(row.get("code"), str):
            raise ProofDegreeError("كل سجل في الدفتر يحتاج code نصيًا")
        code = row["code"]
        if code in seen_ledger:
            raise ProofDegreeError(f"رمز مكرر في الدفتر: {code}")
        seen_ledger.add(code)
        if code not in statuses:
            unavailable.append({"code": code, "reason": "لا توجد درجة إثبات لهذا الرمز في event_keys"})
            continue
        status = statuses[code]
        if status is None:
            unavailable.append({"code": code, "reason": "status مفقود في event_keys؛ لم يُختلق نص"})
            continue
        if status not in PROOF_DEGREES:
            unavailable.append({"code": code, "reason": f"قيمة status خارج القيم المغلقة: {status}"})
            continue
        if row.get("proof_degree") == status:
            unchanged += 1
        else:
            row["proof_degree"] = status
            updated += 1

    summary = {
        "date": date,
        "updated": updated,
        "unchanged": unchanged,
        "unavailable": len(unavailable),
        "unavailable_records": unavailable,
        "ledger_records": len(out_rows),
        "source_event_keys": len(keys),
        "source": f"web/meta/{date}.json:event_keys[].status",
    }
    if write and updated:
        ledger_path.write_text(json.dumps(output, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", action="append", required=True)
    parser.add_argument("--brain", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        for date in args.date:
            summary = apply_day(args.brain.resolve(), date, write=args.write)
            print(json.dumps(summary, ensure_ascii=False))
        return 0
    except (ProofDegreeError, OSError) as exc:
        print(f"فشل نقل درجة الإثبات: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
