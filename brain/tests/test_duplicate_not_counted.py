#!/usr/bin/env python3
"""صف التكرار لا يُحتسب، ومصادره تُدمج في واقعته الأصلية (S072 + S074، 21 نوفمبر 2026).

يحرس ثلاثة أمور مقيسة على الدفتر الحقيقي:
1) derive_event_links: صف ينتهي بـduplicate_of يصير «تكرار» وcounts_as_new=false بحقل علاقة واحد
   (كان MN-2026-11-18-03 و-04 «جديد» محتسبًا).
2) classify_zones.is_qualifying: صف التكرار غير مؤهّل (18 نوفمبر: 9 → 7).
3) merge_event_sources --ledger: الجذر عبر الأيام يأخذ sources من تكراره، ولا يُلمس source،
   وإعادة التشغيل لا تغيّر شيئًا.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import derive_event_links as del_  # noqa: E402
from classify_zones import is_qualifying  # noqa: E402
from merge_event_sources import merge_ledger  # noqa: E402

FAIL: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAIL.append(msg)


def rows() -> tuple[dict, dict]:
    base = {"code": "MN-2026-11-14-01", "date": "2026-11-14", "title": "هجوم على ناقلة",
            "source": "UKMTO — الحوادث الأخيرة", "source_excerpt": "Tanker struck by projectile",
            "source_url": "https://www.ukmto.org/recent-incidents#x", "class": "بلاغ رسمي",
            "event_kind": "جديد", "counts_as_new": True}
    dup = dict(base, code="MN-2026-11-18-03", date="2026-11-18", source="UKMTO — التحذيرات 2026",
               source_excerpt="13/11/2026 Attack: time-late report")
    return base, dup


def main() -> int:
    base, dup = rows()
    days = [(Path("2026-11-14.json"), [dict(base)]), (Path("2026-11-18.json"), [dict(dup)])]
    edits, report = del_.derive(days)
    f = edits["2026-11-18"]["MN-2026-11-18-03"]
    check(f.get("duplicate_of") == "MN-2026-11-14-01", "S072 يكتب duplicate_of بالدليل (الرابط + العنوان)")
    check(f.get("event_kind") == "تكرار" and f.get("counts_as_new") is False,
          "صف التكرار: event_kind=تكرار وcounts_as_new=false")
    check(f.get("update_of") is None and f.get("parent_id") is None, "حقل علاقة واحد فقط")
    check("MN-2026-11-14-01" not in edits.get("2026-11-14", {}) or
          not edits["2026-11-14"]["MN-2026-11-14-01"].get("duplicate_of"), "الجذر لا يُعلَّم تكرارًا")

    reg = json.loads((ROOT / "appendices" / "zone-registry.json").read_text(encoding="utf-8"))
    marked = dict(dup, duplicate_of="MN-2026-11-14-01", counts_as_new=False, event_kind="تكرار")
    q, _conf, why = is_qualifying(marked, reg, {})
    check(q is False and "تكرار" in why, "صف التكرار غير مؤهّل في العدّاد")
    q2, _c, _w = is_qualifying(dict(base), reg, {})
    check(q2 is True, "الواقعة الأصلية تبقى مؤهّلة")

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "2026-11-14.json").write_text(json.dumps([base], ensure_ascii=False, indent=1), encoding="utf-8")
        (d / "2026-11-18.json").write_text(json.dumps([marked], ensure_ascii=False, indent=2), encoding="utf-8")
        r1 = merge_ledger(d, apply=True)
        root = json.loads((d / "2026-11-14.json").read_text(encoding="utf-8"))[0]
        check(r1["roots"] == ["MN-2026-11-14-01"], "الدمج يعبر الأيام إلى الجذر")
        check(len(root.get("sources") or []) == 2, "sources في الجذر فيها المصدران")
        check(root["source"] == base["source"], "الحقل source لا يُلمس")
        check((d / "2026-11-14.json").read_text(encoding="utf-8").startswith('[\n {'), "تنسيق الملف محفوظ")
        r2 = merge_ledger(d, apply=True)
        check(r2["changed_files"] == [], "إعادة التشغيل لا تغيّر شيئًا")
        bad = dict(marked, code="MN-2026-11-18-09", source_excerpt="")
        (d / "2026-11-19.json").write_text(json.dumps([dict(bad, duplicate_of="MN-2026-11-14-01")],
                                                       ensure_ascii=False), encoding="utf-8")
        r3 = merge_ledger(d, apply=False)
        check(r3["skipped"] and r3["skipped"][0]["root"] == "MN-2026-11-14-01",
              "مجموعة فيها مقتطف ناقص تُسجَّل متروكة ولا توقف الدفتر")
    if FAIL:
        print(f"  ✘ {len(FAIL)} إخفاق")
        return 1
    print("  ✔ التكرار لا يُحتسب والدمج يعمل")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
