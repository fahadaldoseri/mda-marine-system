#!/usr/bin/env python3
"""اختبار موجب وسالب لحارس دفتر القرارات.

موجب: الدفتر الفعلي يمرّ بلا خلل.
سالب: إسقاط الدليل عن قرار منفَّذ · حالة غير معلنة · معرّف مكرر · قرار غائب ·
       عدّاد مغلوط · دفتر غائب ⇒ يفشل الحارس، فلا يمكن إعلان تنفيذ بلا سند.

الاستعمال: python3 tests/test_decisions_registry.py    رمز 0 سليم · 2 خلل
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validators" / "check_decisions_registry.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_decisions_registry", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def _stage(tmp: Path) -> Path:
    (tmp / "decisions").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "decisions" / "registry.json", tmp / "decisions" / "registry.json")
    return tmp


def _mutate(tmp: Path, fn) -> Path:
    p = tmp / "decisions" / "registry.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    fn(data)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return tmp


class Positive(unittest.TestCase):
    def test_repository_registry_passes(self):
        self.assertEqual(MOD.check(ROOT), [])

    def test_declared_zero_status_count_is_valid(self):
        registry = json.loads((ROOT / "decisions" / "registry.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["counts"].get("يحتاج قرارًا"), 0)
        self.assertEqual(MOD.check(ROOT), [])

    def test_contract_line_stable(self):
        self.assertIn("دفتر القرارات", MOD.OK_LINE)

    def test_all_sixteen_present(self):
        reg = json.loads((ROOT / "decisions" / "registry.json").read_text(encoding="utf-8"))
        # القرارات لا تُحذف: الحد الأدنى 16، ويجوز أن تنمو مع قرارات جديدة موثّقة
        self.assertGreaterEqual(len(reg["decisions"]), 16)
        for d in reg["decisions"]:
            self.assertTrue(str(d.get("title_ar", "")).strip(), d.get("id"))

    def test_d0620_file_evidence_resolves(self):
        reg = json.loads((ROOT / "decisions" / "registry.json").read_text(encoding="utf-8"))
        decision = next(d for d in reg["decisions"] if d.get("id") == "D-0620")
        missing = [
            e["ref"]
            for e in decision.get("evidence", [])
            if e.get("kind") == "file" and not (ROOT / str(e["ref"])).exists()
        ]
        self.assertEqual(missing, [], f"D-0620 evidence paths must resolve: {missing}")


class Negative(unittest.TestCase):
    def test_done_without_evidence_fails(self):
        def edit(d):
            for x in d["decisions"]:
                if x["status"] == "منفَّذ":
                    x["evidence"] = []
                    break
        with tempfile.TemporaryDirectory() as t:
            errs = MOD.check(_mutate(_stage(Path(t)), edit))
            self.assertTrue(any("بلا دليل" in e for e in errs), errs)

    def test_unknown_status_fails(self):
        def edit(d):
            d["decisions"][0]["status"] = "قيد التنفيذ"
        with tempfile.TemporaryDirectory() as t:
            errs = MOD.check(_mutate(_stage(Path(t)), edit))
            self.assertTrue(any("غير معلنة" in e for e in errs), errs)

    def test_duplicate_id_fails(self):
        def edit(d):
            d["decisions"][1]["id"] = d["decisions"][0]["id"]
        with tempfile.TemporaryDirectory() as t:
            errs = MOD.check(_mutate(_stage(Path(t)), edit))
            self.assertTrue(any("مكرر" in e or "غائب" in e for e in errs), errs)

    def test_missing_decision_fails(self):
        def edit(d):
            d["decisions"] = [x for x in d["decisions"] if x["id"] != "D-09"]
        with tempfile.TemporaryDirectory() as t:
            errs = MOD.check(_mutate(_stage(Path(t)), edit))
            self.assertTrue(any("D-09" in e for e in errs), errs)

    def test_wrong_counter_fails(self):
        def edit(d):
            d["counts"]["منفَّذ"] = 99
        with tempfile.TemporaryDirectory() as t:
            errs = MOD.check(_mutate(_stage(Path(t)), edit))
            self.assertTrue(any("عدّاد" in e for e in errs), errs)

    def test_missing_file_evidence_fails(self):
        def edit(d):
            for x in d["decisions"]:
                if x["status"] in ("منفَّذ", "منفَّذ جزئيًّا"):
                    x["evidence"] = [{"kind": "file", "ref": "لا/يوجد.md"}]
                    break
        with tempfile.TemporaryDirectory() as t:
            errs = MOD.check(_mutate(_stage(Path(t)), edit))
            self.assertTrue(any("غير موجود" in e for e in errs), errs)

    def _waive(self, waiver: dict) -> tuple[list[str], list[str]]:
        def edit(d):
            for x in d["decisions"]:
                if x["status"] in ("منفَّذ", "منفَّذ جزئيًّا"):
                    x["evidence"] = [{"kind": "file", "ref": "لا/يوجد.md"}]
                    break
            d["evidence_waivers"] = [dict(waiver, ref="لا/يوجد.md")]
        warns: list[str] = []
        with tempfile.TemporaryDirectory() as t:
            errs = MOD.check(_mutate(_stage(Path(t)), edit), warns, today="2026-11-20")
        return [e for e in errs if "لا/يوجد.md" in e], warns

    def test_active_owner_waiver_turns_missing_file_into_warning(self):
        errs, warns = self._waive({"decided_by": "فهد الدوسري", "decided_at": "2026-11-18", "expires": "2026-11-25"})
        self.assertEqual(errs, [])
        self.assertTrue(any("مستثنى" in w for w in warns), warns)

    def test_expired_waiver_blocks(self):
        errs, warns = self._waive({"decided_by": "فهد الدوسري", "expires": "2026-11-19"})
        self.assertTrue(errs, "انتهاء الاستثناء يعيد الدليل الغائب مانعًا")
        self.assertEqual(warns, [])

    def test_waiver_without_owner_or_expiry_blocks(self):
        self.assertTrue(self._waive({"expires": "2026-11-25"})[0])
        self.assertTrue(self._waive({"decided_by": "فهد الدوسري"})[0])

    def test_absent_registry_fails(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(MOD.check(Path(t)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
