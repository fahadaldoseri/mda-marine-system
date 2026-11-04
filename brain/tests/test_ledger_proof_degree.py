#!/usr/bin/env python3
"""اختبار نقل proof_degree من event_keys إلى دفتر اليوم بلا اختلاق."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ledger_proof_degree import apply_day  # noqa: E402


def make_root(root: Path, *, missing_status: bool = False) -> None:
    (root / "cumulative-2026" / "daily").mkdir(parents=True)
    (root / "web" / "meta").mkdir(parents=True)
    rows = [
        {"code": "MN-2026-11-03-01", "title": "أ", "confidence": "منخفضة"},
        {"code": "MN-2026-11-03-02", "title": "ب", "confidence": "عالية"},
    ]
    keys = [
        {"code": "MN-2026-11-03-01", "status": "بلاغ رسمي والنص غير متاح"},
        {"code": "MN-2026-11-03-02"} if missing_status else {"code": "MN-2026-11-03-02", "status": "نص رسمي كامل"},
    ]
    (root / "cumulative-2026" / "daily" / "2026-11-03.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    (root / "web" / "meta" / "2026-11-03.json").write_text(json.dumps({"event_keys": keys, "keep": 7}, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="proof-degree-") as tmp:
        root = Path(tmp)
        make_root(root)
        summary = apply_day(root, "2026-11-03", write=True)
        rows = json.loads((root / "cumulative-2026" / "daily" / "2026-11-03.json").read_text(encoding="utf-8"))
        assert summary["updated"] == 2 and summary["unavailable"] == 0
        assert rows[0]["proof_degree"] == "بلاغ رسمي والنص غير متاح"
        assert rows[1]["proof_degree"] == "نص رسمي كامل"

    with tempfile.TemporaryDirectory(prefix="proof-degree-negative-") as tmp:
        root = Path(tmp)
        make_root(root, missing_status=True)
        summary = apply_day(root, "2026-11-03", write=True)
        rows = json.loads((root / "cumulative-2026" / "daily" / "2026-11-03.json").read_text(encoding="utf-8"))
        assert summary["updated"] == 1 and summary["unavailable"] == 1
        assert "proof_degree" not in rows[1], "لا يجوز اختلاق نص عند غياب الحالة"

    print("  ✔ مطابقة الرمز نقلت درجة الإثبات إلى الدفتر")
    print("  ✔ السجل بلا درجة في المصدر بقي بلا نص وسُجّل متعذرًا")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
