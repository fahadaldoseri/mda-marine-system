#!/usr/bin/env python3
"""اختبار موجب وسالب لحارس سياسة التسليم المتصل (قرار المالك «أ»).

موجب: السياسة الفعلية في المستودع تمرّ بلا خلل.
سالب: نسخة معدَّلة في مجلد مؤقت تُسقط الوضع أو عنصرًا من السلسلة أو حارسًا أو خطوة تسليم
       ⇒ يفشل الحارس (خلل مُعلَن)، وهو ما يمنع إسقاط السلوك بصمت.

الاستعمال: python3 tests/test_delivery_policy.py    رمز 0 سليم · 2 خلل
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
VALIDATOR = ROOT / "validators" / "check_delivery_policy.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_delivery_policy", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


MOD = _load_module()


def _stage(tmp: Path) -> Path:
    """ينسخ عقد السياسة والمانيفست الفعليين إلى جذر مؤقت للتجريب السلبي."""
    (tmp / "runbook").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "runbook" / "delivery-policy.json", tmp / "runbook" / "delivery-policy.json")
    shutil.copy(ROOT / "runbook" / "runbook.json", tmp / "runbook" / "runbook.json")
    return tmp


def _mutate(tmp: Path, fn) -> Path:
    p = tmp / "runbook" / "delivery-policy.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    fn(data)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return tmp


class DeliveryPolicyPositive(unittest.TestCase):
    def test_repository_policy_passes(self):
        errs = MOD.check(ROOT)
        self.assertEqual(errs, [], f"سياسة التسليم في المستودع لا تمرّ: {errs}")

    def test_contract_line_is_stable(self):
        self.assertIn("✔ سياسة التسليم المتصل", MOD.OK_LINE)

    def test_required_manifest_steps_exist_now(self):
        ids = {s["id"] for s in json.loads((ROOT / "runbook" / "runbook.json").read_text(encoding="utf-8"))["steps"]}
        for sid in MOD.REQUIRED_MANIFEST_STEPS:
            self.assertIn(sid, ids, f"خطوة تسليم غائبة: {sid}")


class DeliveryPolicyNegative(unittest.TestCase):
    def test_wrong_mode_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = _mutate(_stage(Path(d)), lambda p: p.update({"mode": "B"}))
            self.assertTrue(MOD.check(root), "تغيير الوضع إلى «ب» لم يُرفض")

    def test_missing_sequence_item_fails(self):
        def edit(p):
            p["sequence"] = [s for s in p["sequence"] if s != "publish"]
        with tempfile.TemporaryDirectory() as d:
            root = _mutate(_stage(Path(d)), edit)
            errs = MOD.check(root)
            self.assertTrue(any("سلسلة" in e for e in errs), f"سقوط «publish» لم يُرفض: {errs}")

    def test_reordered_sequence_fails(self):
        def edit(p):
            p["sequence"] = ["publish", "branch", "pr", "merge", "push", "live_verify", "telegram", "report"]
        with tempfile.TemporaryDirectory() as d:
            root = _mutate(_stage(Path(d)), edit)
            errs = MOD.check(root)
            self.assertTrue(any("ترتيب" in e for e in errs), f"اختلال الترتيب لم يُرفض: {errs}")

    def test_missing_forbidden_guard_fails(self):
        def edit(p):
            p["forbidden"] = [g for g in p["forbidden"] if g != "force_push"]
        with tempfile.TemporaryDirectory() as d:
            root = _mutate(_stage(Path(d)), edit)
            errs = MOD.check(root)
            self.assertTrue(any("حراس" in e for e in errs), f"سقوط حارس force_push لم يُرفض: {errs}")

    def test_non_permanent_policy_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = _mutate(_stage(Path(d)), lambda p: p["decision"].update({"permanent": False}))
            errs = MOD.check(root)
            self.assertTrue(any("دائمة" in e for e in errs), f"سياسة غير دائمة لم تُرفض: {errs}")

    def test_missing_manifest_delivery_step_fails(self):
        def edit(p):
            p["manifest_delivery_steps"] = [s for s in p["manifest_delivery_steps"] if s != "D010"]
        with tempfile.TemporaryDirectory() as d:
            root = _mutate(_stage(Path(d)), edit)
            # إسقاط D010 من إعلان السياسة يُبقيه في المانيفست: لا خلل
            self.assertEqual(MOD.check(root), [])
        with tempfile.TemporaryDirectory() as d:
            root = _stage(Path(d))
            man = root / "runbook" / "runbook.json"
            data = json.loads(man.read_text(encoding="utf-8"))
            data["steps"] = [s for s in data["steps"] if s["id"] != "D010"]
            man.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            errs = MOD.check(root)
            self.assertTrue(any("غائبة" in e for e in errs), f"غياب D010 من المانيفست لم يُرفض: {errs}")

    def test_absent_policy_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(MOD.check(Path(d)), "غياب عقد السياسة لم يُرفض")


if __name__ == "__main__":
    unittest.main(verbosity=2)
