#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار بوابة مخطط دفتر الوقائع: موجب · سالب · مفقود (فشل مغلق)."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_daily_events_schema", ROOT / "validators" / "check_daily_events_schema.py")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  ✔ {name}")


def bad(name: str, detail: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  ✘ {name} — {detail}")


def check(name: str, condition: bool, detail: str = "") -> None:
    ok(name) if condition else bad(name, detail)


LIVE_RECORD = {
    "code": "MN-2026-11-01-01",
    "date": "2026-11-01",
    "area": "مضيق هرمز",
    "class": "بلاغ رسمي",
    "title": "تحذير UKMTO رقم 190-26",
    "source": "حساب @UK_MTO على X",
    "confidence": "متوسطة",
    "source_excerpt": "UKMTO WARNING 190-26",
    "source_excerpt_from": "feeds/feeds-2026-11-01.json · 15 · item 1",
    "evidence_ref": "feeds/feeds-2026-11-01.json · 15 · item 1",
    "retrieved_at": "2026-11-01T04:00Z",
    "sector_id": "Z1",
}


def live(**changes) -> dict:
    row = dict(LIVE_RECORD)
    row.update(changes)
    return row


def run(rows, label="2026-11-01", known=None):
    return GATE.violations(rows, date_label=label, known_ids=known)


def main() -> int:
    check("سجل حيّ سليم يجتاز", run([live()]) == [], str(run([live()])))
    check("قائمة فارغة تُمنع",
          any("بلا سجلات" in e for e in run([])), str(run([])))
    check("موثوقية خارج القائمة المغلقة تُمنع",
          any("درجة الموثوقية" in e for e in run([live(confidence="عالية للوقائع")])))
    check("رمز بمصغّرات قديمة يُقبل بنيويًّا",
          run([live(code="COVER-2026-05-09-001", date="2026-05-09")], label="2026-05-09") == [])
    check("رمز مخالف للصيغة يُمنع",
          any("نمط الرمز" in e for e in run([live(code="X-2026-11-01-01")])))
    check("رمز النطاق الحيّ يجب أن يبدأ بـ MN",
          any("MN-YYYY-MM-DD-NN" in e for e in run([live(code="IMO-2026-11-01-01")])))
    check("تاريخ بعد يوم الملف يُمنع",
          any("بعد يوم الملف" in e for e in run([live(date="2026-11-02")])))
    check("تاريخ سابق ليوم الملف يُقبل (يوم الحادث ≠ يوم التقرير)",
          run([live(date="2026-10-31")]) == [])
    check("غياب الموضع في النطاق الحيّ يُمنع",
          any("area" in e and "غائب" in e for e in run([live(area="")])))
    check("غياب المقتطف في النطاق الحيّ يُمنع",
          any("source_excerpt" in e for e in run([live(source_excerpt="")])))
    check("قيمة قطاع خارج Z1–Z4 تُمنع",
          any("sector_id" in e for e in run([live(sector_id="Z9")])))
    check("توقيت بصيغة غير DTG يُمنع",
          any("التوقيت" in e for e in run([live(time="18:59")])))
    check("توقيت DTG صحيح يُقبل", run([live(time="1859Z", time_kind="وقوع")]) == [])
    check("رقم IMO غير رقمي يُمنع",
          any("IMO" in e for e in run([live(imo_number="IMO9315159")])))
    check("مرجع ربط معلّق يُمنع",
          any("معلّق" in e for e in run([live(update_of="MN-2026-10-31-99")],
                                        known={"MN-2026-11-01-01"})))
    check("مرجع ربط موجود يُقبل",
          run([live(update_of="MN-2026-10-31-01")],
              known={"MN-2026-11-01-01", "MN-2026-10-31-01"}) == [])
    check("رابط مختصر يُمنع",
          any("مختصر" in e for e in run([live(source_url="https://t.co/abc")])))
    check("رابط غير https يُمنع",
          any("https" in e for e in run([live(source_url="http://imo.org/x")])))
    check("نصّ غياب مخزّن كقيمة يُمنع",
          any("نصّ غياب" in e for e in run([live(area="غير متاح")])))
    check("سجل لا واقعة بلا مصادر يُمنع",
          any("لا واقعة" in e for e in run([{"no_incident": True, "title": "لا واقعة مسجّلة في المصادر الرسمية المفحوصة", "retrieved_at": "2026-11-01T04:00Z"}])))
    check("سجل لا واقعة مكتمل يُقبل",
          run([{"no_incident": True,
                "title": "لا واقعة مسجّلة في المصادر الرسمية المفحوصة",
                "retrieved_at": "2026-11-01T04:00Z",
                "sources_checked": [{"source_id": "ukmto", "url": "https://ukmto.org",
                                     "invoked": True, "result": "لا جديد",
                                     "retrieved_at": "2026-11-01T04:00Z"}]}]) == [])
    archive = [live(code="COVER-2026-05-09-001", date="2026-05-09", **{"title": "", "class": ""})]
    check("فجوة الأرشيف لا تمنع", run(archive, label="2026-05-09") == [])
    check("فجوة الأرشيف تُعدّ وتُطبع",
          len(GATE.historical_gaps(archive, date_label="2026-05-09")) == 2)

    print(f"  نجح {PASS} · فشل {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
