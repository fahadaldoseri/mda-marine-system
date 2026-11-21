#!/usr/bin/env python3
"""اختبار الإصلاح الذاتي (اعتماد فهد 21 نوفمبر 2026) على جذر مؤقت لا يلمس المشروع الحقيقي.

يثبت بالتشغيل:
  1. الجدول الحقيقي سليم، والحاجز يرفض عطل محتوى بإجراء تقني أو قاعدة بلا عطل مقيس.
  2. عطل تقني معروف (صفحة 0 بايت) يُصلح وتُعاد الخطوة المتأثرة وحدها، مرة واحدة فقط في اليوم.
  3. عطل ترجمة يعزل النسخة الإنجليزية: خطوتها تُتخطّى، والبناء لا يربط إليها، والحكم لا يكون سليمًا،
     ورسالة اليوم تحمل التنبيه.
  4. عطل محتوى في المتن العربي يحتجز التشغيل (لا نشر)، ويُرفع الاحتجاز عند نجاح الخطوة بعد التصحيح.
  5. قبول نقص أصل معتمد فقط إن طابق الملف نسخة main المدموجة؛ وإن خالفها (تلف من التشغيل) يبقى المنع.
  6. عطل في أداة الإصلاح نفسها لا يُسقط الخط ولا يخفف مانعًا.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
import auto_heal  # noqa: E402
import runbook  # noqa: E402

DATE = "2026-11-21"
GEN = HERE.parent / "site" / "generator"


def _step(sid, cmd, phase="build"):
    return {"id": sid, "title": sid, "kind": "script", "phase": phase, "command": ["bash", "-lc", cmd],
            "on_fail": "stop", "links": {"rules": [], "files": [], "tests": []}}


class Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(prefix="auto-heal-")
        self.root = Path(self.td.name) / "brain"
        self.site = Path(self.td.name) / "site"
        (self.root / "runbook").mkdir(parents=True)
        (self.site / "dist" / "reports" / "en").mkdir(parents=True)
        shutil.copy2(HERE / auto_heal.TABLE, self.root / auto_heal.TABLE)
        self.env = {k: os.environ.get(k) for k in ("SITE_DIR", "SITE", "BRAIN_DIR")}
        os.environ["SITE_DIR"] = str(self.site)
        os.environ.pop("SITE", None)
        os.environ["BRAIN_DIR"] = str(self.root)

    def tearDown(self):
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.td.cleanup()

    def manifest(self, steps):
        m = {"version": 1, "ledger_dir": "logs/runbook", "gate_phases": ["gates"], "steps": steps}
        (self.root / "runbook" / "runbook.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")

    def run_engine(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = runbook.run(str(self.root), DATE)
        return rc, buf.getvalue()

    def ledger(self):
        return [json.loads(x) for x in (self.root / "logs" / "runbook" / f"{DATE}.jsonl").read_text(encoding="utf-8").splitlines()]


class TableTests(Base):
    def test_real_table_is_valid_against_real_manifest(self):
        m = json.loads((HERE / "runbook" / "runbook.json").read_text(encoding="utf-8"))
        self.assertEqual(auto_heal.check_table(auto_heal.load_table(HERE), {s["id"] for s in m["steps"]}), [])

    def test_guard_rejects_content_fault_with_technical_action(self):
        t = auto_heal.load_table(HERE)
        t["rules"].append({"id": "X1", "class": "content", "evidence": "e", "steps": ["B010"],
                           "match": "", "action": "remove_empty_dated_page", "then": "retry"})
        t["rules"].append({"id": "X2", "class": "technical", "evidence": "", "steps": ["B010"],
                           "match": "", "action": "remove_empty_dated_page", "then": "retry"})
        t["rules"].append({"id": "X3", "class": "content", "evidence": "e", "steps": ["G054"],
                           "match": "", "action": "hold"})
        errs = " ".join(auto_heal.check_table(t))
        self.assertIn("X1: عطل محتوى بإجراء", errs)
        self.assertIn("X2: قاعدة بلا عطل مقيس", errs)
        self.assertIn("X3: احتجاز بلا تعليمة", errs)


class TechnicalHealTests(Base):
    def test_empty_page_is_removed_and_only_that_step_is_retried_once(self):
        page = self.site / "dist" / "reports" / f"{DATE}.html"
        page.write_text("", encoding="utf-8")
        counter = self.root / "count-B"
        self.manifest([
            _step("A", f"echo a >> {self.root}/count-A"),
            _step("B", f"echo b >> {counter}; test ! -e {page} -o -s {page}"),
            _step("C", "true"),
        ])
        rc, out = self.run_engine()
        self.assertEqual(rc, 0, out)
        self.assertFalse(page.exists())
        self.assertEqual(counter.read_text().count("b"), 2)  # محاولة فاشلة + إعادة واحدة بعد الإصلاح
        self.assertEqual((self.root / "count-A").read_text().count("a"), 1)  # ما قبلها لم يُعد
        done_b = [e for e in self.ledger() if e["step"] == "B" and e["status"] == "done"]
        self.assertEqual(done_b[-1].get("healed"), "AH-T1")
        # الرصيد مرة واحدة في اليوم: صفحة فارغة جديدة لا تُصلح ثانية للخطوة نفسها
        page.write_text("", encoding="utf-8")
        d = auto_heal.decide(self.root, DATE, "B", 1, "")
        self.assertEqual(d["then"], "none")

    def test_unknown_fault_keeps_failure(self):
        self.manifest([_step("B", "exit 1")])
        rc, _ = self.run_engine()
        self.assertEqual(rc, 2)
        self.assertEqual(self.ledger()[-1]["status"], "failed")

    def test_broken_heal_tool_never_lifts_a_block(self):
        (self.root / auto_heal.TABLE).write_text("{ليس json", encoding="utf-8")
        page = self.site / "dist" / "reports" / f"{DATE}.html"
        page.write_text("", encoding="utf-8")
        self.manifest([_step("B", f"test ! -e {page} -o -s {page}")])
        rc, _ = self.run_engine()
        self.assertEqual(rc, 2)
        self.assertTrue(page.exists())


class IsolationTests(Base):
    def test_translation_fault_isolates_english_and_never_sound(self):
        self.manifest([
            _step("B004A", "true"),
            _step("B009", "echo 'توقّف: وحدة عربية بلا مقابل إنجليزي'; exit 2"),
            _step("B005", f"touch {self.root}/B005-ran"),
            _step("G100", "true", phase="gates"),
        ])
        rc, out = self.run_engine()
        self.assertEqual(rc, 0, out)
        led = {e["step"]: e for e in self.ledger()}
        self.assertEqual(led["B009"]["status"], "skipped")
        self.assertEqual(led["B009"]["isolated"], "en")
        self.assertEqual(led["B005"]["isolated"], "en")
        self.assertFalse((self.root / "B005-ran").exists())  # خطوة السطح المعزول لا تُنفَّذ
        self.assertTrue(auto_heal.isolated(self.root, DATE, "en"))
        self.assertIn("النسخة الإنجليزية", auto_heal.owner_note(self.root, DATE))
        # البناء: لا عزل = رابط إلى الإنجليزية؛ عزل = لا رابط
        sys.path.insert(0, str(GEN))
        import site_chrome  # noqa: E402
        self.assertTrue(site_chrome.en_isolated(DATE))
        self.assertFalse(site_chrome.en_isolated("2026-11-20"))

    def test_isolated_gate_step_counts_as_warning_not_ok(self):
        self.manifest([_step("B010", "echo 'فشل مغلق: نصوص عربية بلا ترجمة في additions.html'; exit 1", phase="gates")])
        state = auto_heal.load_state(self.root, DATE)
        state["isolated"]["en"] = {"rule": "AH-C1", "step": "B010"}
        auto_heal._save_state(self.root, DATE, state)
        with redirect_stdout(io.StringIO()):
            runbook.append(str(self.root), runbook.load(str(self.root)), DATE,
                           {"step": "B010", "status": "skipped", "isolated": "en", "rc": 1})
            runbook.gate_json(str(self.root), DATE)
        gate = json.loads((self.root / "logs" / f"gate-{DATE}" / "gate.json").read_text(encoding="utf-8"))
        self.assertEqual(gate["exit_code"], 1)

    def test_publish_verdict_is_disclosed_when_isolated_and_blocked_when_held(self):
        import publish_verdict
        logs = self.root / "logs" / f"gate-{DATE}"
        logs.mkdir(parents=True)
        (self.root / "reports").mkdir()
        rep = self.root / "reports" / f"{DATE}-sectioned.md"
        rep.write_text("نص\n", encoding="utf-8")
        import hashlib
        (logs / "gate.json").write_text(json.dumps({"date": DATE, "stage": "final", "exit_code": 0, "steps": []}))
        (self.root / "logs" / f"pipeline-{DATE}.json").write_text(
            json.dumps({"date": DATE, "overall": "ok", "final_gate": {"exit_code": 0}}))
        (logs / f".text-hash-{DATE}.json").write_text(json.dumps({"sha256": hashlib.sha256(rep.read_bytes()).hexdigest()}))
        self.assertEqual(publish_verdict.verdict(self.root, DATE)["verdict"], 0)
        state = auto_heal.load_state(self.root, DATE)
        state["isolated"]["en"] = {"rule": "AH-C1", "step": "B010"}
        auto_heal._save_state(self.root, DATE, state)
        self.assertEqual(publish_verdict.verdict(self.root, DATE)["verdict"], 3)
        auto_heal.decide(self.root, DATE, "G054", 2, "موانع: 1")
        self.assertEqual(publish_verdict.verdict(self.root, DATE)["verdict"], 2)
        self.assertEqual(auto_heal.resolve_holds(self.root, DATE, "G054"), 1)
        self.assertEqual(publish_verdict.verdict(self.root, DATE)["verdict"], 3)


class OwnerAlertTests(Base):
    def test_daily_message_carries_isolation_alert_in_third_person(self):
        (self.root / "web" / "meta").mkdir(parents=True)
        shutil.copy2(HERE / "web" / "meta" / "2026-10-23.json", self.root / "web" / "meta" / f"{DATE}.json")
        out = Path(self.td.name) / "d.html"
        cmd = [sys.executable, str(HERE / "tools" / "make_tg_digest.py"), "--date", DATE, "--out", str(out),
               "--base-url", "http://x"]
        env = {**os.environ, "SITE_DIR": str(HERE.parent / "site")}
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("تنبيه:", out.read_text(encoding="utf-8"))  # لا عزل = لا تنبيه
        state = auto_heal.load_state(self.root, DATE)
        state["isolated"]["en"] = {"rule": "AH-C1", "step": "B010"}
        auto_heal._save_state(self.root, DATE, state)
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)  # يمرّ حاجز صيغة الأمر والسقف
        text = out.read_text(encoding="utf-8")
        self.assertIn("<b>تنبيه:</b>", text)
        self.assertIn("عُزلت النسخة الإنجليزية", text)
        # حالة تالفة = فشل مغلق، لا رسالة تُخفي عزلًا
        (self.root / "logs" / "auto-heal" / f"{DATE}.json").write_text("{تالف", encoding="utf-8")
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


class HoldTests(Base):
    def test_content_fault_in_arabic_body_holds_then_clears_on_fix(self):
        fixed = self.root / "fixed"
        self.manifest([_step("G054", f"test -e {fixed} || {{ echo 'موانع: 1'; exit 2; }}", phase="gates")])
        rc, out = self.run_engine()
        self.assertEqual(rc, 2)
        self.assertIn("احتجاز ذاتي AH-C2", out)
        self.assertEqual(len(auto_heal.load_state(self.root, DATE)["holds"]), 1)
        self.assertIn("يُصحَّح الرقم", (self.root / "logs" / "auto-heal" / f"{DATE}.md").read_text(encoding="utf-8"))
        fixed.write_text("1")
        rc, out = self.run_engine()
        self.assertEqual(rc, 0, out)
        self.assertEqual(auto_heal.load_state(self.root, DATE)["holds"], [])


class MergedShrinkTests(Base):
    def _git(self, *a):
        subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True)

    def setUp(self):
        super().setUp()
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@example.invalid")
        self._git("config", "user.name", "t")
        (self.root / "asset.md").write_text("سطر\nسطر ثان\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        (self.root / "asset.md").write_text("سطر\n", encoding="utf-8")
        self._git("commit", "-qam", "merged fix")
        (self.root / "validators").mkdir()
        (self.root / "validators" / "check_asset_floor.py").write_text(
            "import sys,pathlib\npathlib.Path(sys.argv[0]).with_name('called').write_text(' '.join(sys.argv[1:]))\n",
            encoding="utf-8")
        self.log = f"   ✘ نقص في أصل معتمد: {self.root}/asset.md — أسطر 2→1 · بايت 22→9"

    def test_shrink_matching_main_is_accepted_with_written_reason(self):
        d = auto_heal.decide(self.root, DATE, "G000", 2, self.log)
        self.assertEqual(d["then"], "retry", d)
        dec = (self.root / "audit" / f"asset-floor-decisions-{DATE}.txt").read_text(encoding="utf-8")
        self.assertIn(f"{self.root}/asset.md | تعديل مدموج في main", dec)
        self.assertIn("--reason", (self.root / "validators" / "called").read_text(encoding="utf-8"))

    def test_shrink_made_by_the_run_itself_stays_blocked(self):
        (self.root / "asset.md").write_text("س\n", encoding="utf-8")  # تلف من التشغيل لا من الدمج
        d = auto_heal.decide(self.root, DATE, "G000", 2, self.log)
        self.assertEqual(d["then"], "none")
        self.assertFalse((self.root / "audit").exists())
        self.assertFalse((self.root / "validators" / "called").exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
