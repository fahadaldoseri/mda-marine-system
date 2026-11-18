"""ledger_totals يحترم فجوة النقل الموثقة بقرار المالك (2026-11-17).

قبل الإصلاح: أيام 13-17 نوفمبر بلا دفاتر يومية، فيتوقف S070 بـ
«ملف الدفتر غير موجود». بعده: اليوم الموثق فجوةً يُتخطى ويُفصح عنه في
``range.migration_gap_days``، ويوم ناقص خارج الفجوة يبقى فشلًا مغلقًا،
ويوم فجوة له دفتر تعارض يُرفض كما في حارس الاستمرارية.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN))
import tools.ledger_totals as lt  # noqa: E402

GAP = {
    "migration_gaps": [
        {
            "from": "2026-03-02",
            "to": "2026-03-03",
            "reason": "اختبار",
            "decided_by": "owner",
            "decision_date": "2026-11-17",
        }
    ]
}


class LedgerTotalsMigrationGapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.daily = self.root / "cumulative-2026" / "daily"
        self.daily.mkdir(parents=True)
        for patcher in (
            mock.patch.object(lt, "ROOT", self.root),
            mock.patch.object(lt, "DAILY_DIR", self.daily),
            mock.patch.object(lt, "START_DATE", dt.date(2026, 2, 28)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def write_day(self, iso: str) -> None:
        (self.daily / f"{iso}.json").write_text(
            json.dumps([{"code": f"MN-{iso}-01", "date": iso}]), encoding="utf-8"
        )

    def write_gap(self) -> None:
        (self.root / "cumulative-2026" / "migration-gaps.json").write_text(
            json.dumps(GAP, ensure_ascii=False), encoding="utf-8"
        )

    def test_documented_gap_days_are_skipped_and_disclosed(self):
        for iso in ("2026-02-28", "2026-03-01", "2026-03-04"):
            self.write_day(iso)
        self.write_gap()
        rows, days_total, _dups, gap_days = lt.load_daily(dt.date(2026, 3, 4))
        self.assertEqual([r["code"] for r in rows],
                         ["MN-2026-02-28-01", "MN-2026-03-01-01", "MN-2026-03-04-01"])
        self.assertEqual(days_total, 3)
        self.assertEqual(gap_days, ["2026-03-02", "2026-03-03"])

    def test_missing_day_outside_gap_still_fails_closed(self):
        for iso in ("2026-02-28", "2026-03-04"):
            self.write_day(iso)
        self.write_gap()
        with self.assertRaises(lt.LedgerError) as ctx:
            lt.load_daily(dt.date(2026, 3, 4))
        self.assertIn("2026-03-01.json", str(ctx.exception))

    def test_without_gap_file_behaviour_is_unchanged(self):
        for iso in ("2026-02-28", "2026-03-01", "2026-03-04"):
            self.write_day(iso)
        with self.assertRaises(lt.LedgerError) as ctx:
            lt.load_daily(dt.date(2026, 3, 4))
        self.assertIn("2026-03-02.json", str(ctx.exception))

    def test_gap_day_with_a_ledger_file_is_a_conflict(self):
        for iso in ("2026-02-28", "2026-03-01", "2026-03-02", "2026-03-04"):
            self.write_day(iso)
        self.write_gap()
        with self.assertRaises(lt.LedgerError) as ctx:
            lt.load_daily(dt.date(2026, 3, 4))
        self.assertIn("2026-03-02", str(ctx.exception))

    def test_malformed_gap_file_fails_closed(self):
        self.write_day("2026-02-28")
        (self.root / "cumulative-2026" / "migration-gaps.json").write_text(
            json.dumps({"migration_gaps": [{"from": "2026-03-02"}]}), encoding="utf-8"
        )
        with self.assertRaises(lt.LedgerError):
            lt.load_daily(dt.date(2026, 2, 28))


if __name__ == "__main__":
    unittest.main()
