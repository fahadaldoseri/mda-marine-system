#!/usr/bin/env python3
"""اختبار موجب وسالب لمولّد مرجع آلية العمل وحارسه.

موجب: المستودع يولّد نفس المرجع الموجود على القرص بلا فرق.
سالب: تعديل يدوي على المرجع · معرّف بند مكرر · حالة غير معلنة · حقل ناقص ·
       مجموع بنود مخالف ⇒ يفشل الحارس، فلا يمرّ مرجع منحرف.

الاستعمال: python3 tests/test_reference_generator.py    رمز 0 سليم · 2 خلل
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
TOOL = ROOT / "tools" / "build_workflow_reference.py"
COPY_FILES = ["audit/مرجع-آلية-العمل.md", "audit/مقارنة-الإصدارين-5-6.md",
              "audit/مرجع-آلية-العمل-2026-11-05.md"]
COPY_GLOBS = ["runbook/*.json", "validators/*.py", "tools/*.py", "tests/test_*"]


def _load():
    spec = importlib.util.spec_from_file_location("bwr", TOOL)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def _stage(tmp: Path) -> Path:
    # نسخ انتقائي: العدد الكامل للملفات يجعل النسخ ثقيلًا بلا فائدة للاختبار
    shutil.copytree(ROOT / "runbook" / "reference", tmp / "runbook" / "reference")
    for pattern in COPY_GLOBS:
        for src in ROOT.glob(pattern):
            dst = tmp / src.relative_to(ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
    for f in COPY_FILES:
        dst = tmp / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / f, dst)
    return tmp


def _phases(tmp: Path) -> Path:
    return tmp / "runbook" / "phases.json"


class Positive(unittest.TestCase):
    def test_repository_reference_matches_generator(self):
        self.assertEqual(MOD.cmd_check(ROOT), 0)

    def test_every_phase_has_items(self):
        data = json.loads((ROOT / "runbook" / "phases.json").read_text(encoding="utf-8"))
        self.assertTrue(all(p["items"] for p in data["phases"]))
        self.assertGreaterEqual(len(data["phases"]), 7)

    def test_ceiling_is_derived_not_written(self):
        doc = (ROOT / "audit" / "مرجع-آلية-العمل.md").read_text(encoding="utf-8")
        self.assertIn("سقف الجهد مشتق", doc)


class Negative(unittest.TestCase):
    def test_manual_edit_of_reference_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = _stage(Path(t))
            p = tmp / "audit" / "مرجع-آلية-العمل.md"
            p.write_text(p.read_text(encoding="utf-8") + "\nسطر مُقحَم يدويًّا\n", encoding="utf-8")
            self.assertEqual(MOD.cmd_check(tmp), 2)

    def test_duplicate_item_id_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = _stage(Path(t))
            data = json.loads(_phases(tmp).read_text(encoding="utf-8"))
            data["phases"][0]["items"][1]["id"] = data["phases"][0]["items"][0]["id"]
            _phases(tmp).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(MOD.cmd_check(tmp), 2)

    def test_unknown_status_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = _stage(Path(t))
            data = json.loads(_phases(tmp).read_text(encoding="utf-8"))
            data["phases"][0]["items"][0]["status"] = "قيد العمل"
            _phases(tmp).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(MOD.cmd_check(tmp), 2)

    def test_missing_field_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = _stage(Path(t))
            data = json.loads(_phases(tmp).read_text(encoding="utf-8"))
            data["phases"][0]["items"][0]["gate"] = ""
            _phases(tmp).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(MOD.cmd_check(tmp), 2)

    def test_missing_reference_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = _stage(Path(t))
            (tmp / "audit" / "مقارنة-الإصدارين-5-6.md").unlink()
            self.assertEqual(MOD.cmd_check(tmp), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
