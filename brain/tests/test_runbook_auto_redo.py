#!/usr/bin/env python3
"""المحرّك يعيد بعد التوقف الخطوات التي تغيّرت مدخلاتها وحدها، ولا يتخطى خطوة قديمة (اعتماد فهد 20 نوفمبر 2026).

السبب المقيس: بعد كل خطأ يوم 20 نوفمبر أُعيدت السلسلة من S065 إلى G054 كاملة (75 خطوة، 5–11 دقيقة)
حتى حين كان الإصلاح ملف شيفرة واحدًا تستعمله بوابة واحدة.

موجب: تعديل شيفرة خطوة ⇒ تُعاد هي والخطوة الفاشلة فقط · تعديل وحدة مستوردة ⇒ تُعاد الخطوة المستوردة ·
       لا تغيير ⇒ لا إعادة.
سالب (محافظ): تعديل ملف بيانات ⇒ كل المكتمل يُعاد · شيفرة لا تقع في سلسلة أي خطوة ⇒ كل المكتمل يُعاد ·
       خطوة أُعيدت فغيّرت بيانات ⇒ تُعاد المكتملة بعدها · غياب اللقطة ⇒ كل المكتمل يُعاد ·
       --no-auto-redo ⇒ السلوك القديم.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2099-02-02"

STEP_PY = r'''
import os, sys
from pathlib import Path
here = Path(__file__).resolve().parents[1]
(here / "logs").mkdir(exist_ok=True)
with open(here / "logs" / "calls.txt", "a", encoding="utf-8") as f:
    f.write(sys.argv[1] + "\n")
VERSION = 1
'''


def step(i: str, script: str) -> dict:
    return {"id": i, "title": f"خطوة {i}", "kind": "script", "phase": "gates",
            "command": ["python3", f"tools/{script}", i], "assert": [],
            "links": {"rules": [], "files": [f"tools/{script}"], "gates": [], "tests": []}, "on_fail": "stop"}


def make(t: Path) -> Path:
    (t / "tools").mkdir()
    (t / "runbook").mkdir()
    (t / "data").mkdir()
    (t / "site").mkdir()
    shutil.copy(ROOT / "tools" / "runbook.py", t / "tools" / "runbook.py")
    (t / "tools" / "helper.py").write_text("X = 1\n", encoding="utf-8")
    (t / "tools" / "a.py").write_text("import helper\n" + STEP_PY, encoding="utf-8")
    (t / "tools" / "b.py").write_text(STEP_PY, encoding="utf-8")
    (t / "tools" / "c.py").write_text(STEP_PY + "if (here / 'logs' / 'flag').exists():\n    sys.exit(2)\n",
                                      encoding="utf-8")
    (t / "tools" / "w.py").write_text(STEP_PY + "(here / 'data' / 'out.json').write_text('{\"v\": 1}')\n",
                                      encoding="utf-8")
    (t / "tools" / "stray.py").write_text("print('x')\n", encoding="utf-8")
    (t / "data" / "x.json").write_text('{"a": 1}\n', encoding="utf-8")
    m = {"version": 1, "sections": [], "steps": [step("G1", "a.py"), step("G2", "b.py"), step("G3", "c.py")]}
    (t / "runbook" / "runbook.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    return t


def run(t: Path, *extra: str) -> tuple[int, list[str], str]:
    calls = t / "logs" / "calls.txt"
    if calls.exists():
        calls.unlink()
    env = {k: v for k, v in os.environ.items() if k not in {"BRAIN_DIR"}}
    env["SITE_DIR"] = str(t / "site")
    r = subprocess.run([sys.executable, str(t / "tools" / "runbook.py"), "run", "--date", DATE, "--root", str(t),
                        *extra], capture_output=True, text=True, env=env, timeout=120)
    got = calls.read_text(encoding="utf-8").split() if calls.exists() else []
    return r.returncode, got, r.stdout + r.stderr


def bump(p: Path, old: str, new: str) -> None:
    p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


class AutoRedo(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.t = make(Path(self._d.name))
        (self.t / "logs").mkdir(exist_ok=True)
        (self.t / "logs" / "flag").write_text("1")
        rc, got, out = run(self.t)
        self.assertEqual((rc, got), (2, ["G1", "G2", "G3"]), out)
        (self.t / "logs" / "flag").unlink()  # «الإصلاح» خارج الملفات المراقبة

    def tearDown(self):
        self._d.cleanup()

    def test_fix_outside_inputs_resumes_at_failed_step_only(self):
        rc, got, out = run(self.t)
        self.assertEqual((rc, got), (0, ["G3"]), out)
        rc, got, out = run(self.t)
        self.assertEqual((rc, got), (0, []), out)

    def test_code_change_reruns_only_dependent_step(self):
        bump(self.t / "tools" / "b.py", "VERSION = 1", "VERSION = 2")
        rc, got, out = run(self.t)
        self.assertEqual((rc, got), (0, ["G2", "G3"]), out)

    def test_imported_module_change_reruns_importer(self):
        bump(self.t / "tools" / "helper.py", "X = 1", "X = 2")
        rc, got, out = run(self.t)
        self.assertEqual((rc, got), (0, ["G1", "G3"]), out)

    def test_data_change_reruns_everything_done(self):
        bump(self.t / "data" / "x.json", '"a": 1', '"a": 2')
        rc, got, out = run(self.t)
        self.assertEqual((rc, got), (0, ["G1", "G2", "G3"]), out)

    def test_unknown_code_change_reruns_everything_done(self):
        bump(self.t / "tools" / "stray.py", "'x'", "'y'")
        rc, got, out = run(self.t)
        self.assertEqual((rc, got), (0, ["G1", "G2", "G3"]), out)

    def test_missing_snapshot_reruns_everything_done(self):
        (self.t / "logs" / "runbook" / DATE / "stale-snapshot.json").unlink()
        rc, got, out = run(self.t)
        self.assertEqual((rc, got), (0, ["G1", "G2", "G3"]), out)

    def test_opt_out_keeps_old_behaviour(self):
        bump(self.t / "tools" / "b.py", "VERSION = 1", "VERSION = 2")
        rc, got, out = run(self.t, "--no-auto-redo")
        self.assertEqual((rc, got), (0, ["G3"]), out)


class Cascade(unittest.TestCase):
    def test_rerun_step_that_changes_data_reruns_later_done_steps(self):
        with tempfile.TemporaryDirectory() as d:
            t = make(Path(d))
            m = json.loads((t / "runbook" / "runbook.json").read_text(encoding="utf-8"))
            m["steps"] = [step("G1", "w.py"), step("G2", "b.py"), step("G3", "c.py")]
            (t / "runbook" / "runbook.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
            (t / "logs").mkdir(exist_ok=True)
            (t / "logs" / "flag").write_text("1")
            self.assertEqual(run(t)[:2], (2, ["G1", "G2", "G3"]))
            (t / "logs" / "flag").unlink()
            bump(t / "tools" / "w.py", '"v": 1', '"v": 2')
            rc, got, out = run(t)
            self.assertEqual((rc, got), (0, ["G1", "G2", "G3"]), out)

    def test_self_evidence_written_by_rerun_step_does_not_cascade(self):
        with tempfile.TemporaryDirectory() as d:
            t = make(Path(d))
            (t / "tools" / "e.py").write_text(
                STEP_PY + "import time\n(here / 'audit').mkdir(exist_ok=True)\n"
                "(here / 'audit' / 'proof.json').write_text(str(time.time_ns()))\n", encoding="utf-8")
            m = json.loads((t / "runbook" / "runbook.json").read_text(encoding="utf-8"))
            m["steps"] = [step("G1", "e.py"), step("G2", "b.py"), step("G3", "c.py")]
            (t / "runbook" / "runbook.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
            (t / "logs").mkdir(exist_ok=True)
            (t / "logs" / "flag").write_text("1")
            self.assertEqual(run(t)[:2], (2, ["G1", "G2", "G3"]))
            (t / "logs" / "flag").unlink()
            bump(t / "tools" / "e.py", "VERSION = 1", "VERSION = 2")
            rc, got, out = run(t)
            self.assertEqual((rc, got), (0, ["G1", "G3"]), out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
