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

    def test_contract_line_stable(self):
        self.assertIn("دفتر القرارات", MOD.OK_LINE)

    def test_all_sixteen_present(self):
        reg = json.loads((ROOT / "decisions" / "registry.json").read_text(encoding="utf-8"))
        self.assertEqual(len(reg["decisions"]), 16)


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

    def test_absent_registry_fails(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(MOD.check(Path(t)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
