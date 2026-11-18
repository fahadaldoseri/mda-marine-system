"""قرار المالك (2026-11-18): بلاغ UKMTO الرسمي عن هجوم يُحتسب إصابة مؤكدة في سلّم التهديد.

قبل القرار كان «بلاغ رسمي» يُنزَّل إلى غير مؤكد ما لم تكن حالة الدليل
confirmed_effect_or_attack، فأعطت البلاغات الست عن إصابة ناقلات يوم
18 نوفمبر مستوى «متوسط» للنطاق Z1. الفيكستشر نسخة طبق الأصل من دفتر ذلك اليوم.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tools.classify_zones as cz

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "daily-2026-11-18-ukmto.json"
SIX_ATTACKS = [f"MN-2026-11-18-0{n}" for n in (1, 2, 3, 4, 5, 7)]


def _governed():
    return cz.load_governed()


class UkmtoOfficialConfirmedTests(unittest.TestCase):
    def test_six_ukmto_attack_reports_are_confirmed(self):
        reg, _scale, _levels, _ovr = _governed()
        events = {e["code"]: e for e in json.loads(FIXTURE.read_text(encoding="utf-8"))}
        for code in SIX_ATTACKS:
            _q, conf, _why = cz.is_qualifying(events[code], reg, {})
            self.assertEqual(conf, "confirmed", code)

    def test_six_reports_raise_the_zone_above_medium(self):
        reg, scale, levels, ovr = _governed()
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(FIXTURE, Path(tmp) / "2026-11-18.json")
            with mock.patch.object(cz, "LEDGER_DIR", Path(tmp)):
                out = cz.classify_day("2026-11-18", reg, scale, levels, ovr, carry=False)
        z1 = next(z for z in out["zones"] if z["id"] == "Z1")
        self.assertGreater(z1["rank"], levels["متوسط"]["rank"], z1["level"])
        self.assertGreaterEqual(z1["confirmed"], 6)
        self.assertGreater(out["overall"]["rank"], levels["متوسط"]["rank"])

    def test_ukmto_suspicious_activity_is_not_upgraded(self):
        reg, _scale, _levels, _ovr = _governed()
        events = {e["code"]: e for e in json.loads(FIXTURE.read_text(encoding="utf-8"))}
        for code in ("MN-2026-11-18-06", "MN-2026-11-18-08"):
            self.assertNotEqual(cz.canonical_confirmed(events[code]), True, code)

    def test_official_report_from_other_source_stays_demoted(self):
        reg, _scale, _levels, _ovr = _governed()
        event = {
            "code": "T-1", "class": "بلاغ رسمي", "incident_kind": "هجوم",
            "source": "وزارة الدفاع — بيان", "title": "هجوم على ناقلة في مضيق هرمز",
        }
        _q, conf, _why = cz.is_qualifying(event, reg, {})
        self.assertEqual(conf, "unconfirmed")

    def test_media_report_from_ukmto_mention_is_not_upgraded(self):
        event = {
            "code": "T-2", "class": "نقل إعلامي", "incident_kind": "هجوم",
            "source": "UKMTO عبر وكالة أنباء", "title": "هجوم على ناقلة",
        }
        self.assertFalse(cz.canonical_confirmed(event))


if __name__ == "__main__":
    unittest.main()
