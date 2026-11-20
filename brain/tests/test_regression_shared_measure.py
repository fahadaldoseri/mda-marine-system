#!/usr/bin/env python3
"""مدير الانحدار يقيس كل سطح بمتصفح مرة واحدة، ويحكم كل بند بفحوصه هو.

السبب المقيس (20 نوفمبر 2026): كانت G064 تفتح المتصفح ست مرات (ب-01 ب-02 ب-03 ب-04 ب-13 ب-14)
بكلفة ثابتة نحو 31 ثانية للمرة، فبلغت البوابة 252 ثانية. والقياس الواحد يحمل كل الفحوص
(G065 تقيس خمسة فحوص في 31 ثانية). وأداة التغطية كانت تعدّ كل اسم في النص كله
(`str.count`) 238 مرة، نحو 12 ثانية في كل نداء من أربعة.

موجب: سطحان (عربي وإنجليزي) = نداءان فقط · البند يُحكم بفحوصه لا بفحوص غيره ·
       الفحص الإعلامي (--soft) لا يُسقط بنده · ملف --out لكل بند يُكتب بمخالفاته هو.
سالب: انهيار القياس المشترك ⇒ كل بنود السطح ساقطة (فشل مغلق).
زمن: تغطية البوابات على الجذر الحقيقي أقل من 5 ثوانٍ (كانت 12).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAKE = r'''
import argparse, json, os, sys
from pathlib import Path
def judge(data, checks):
    return [f"مخالفة {c}" for c in checks if c in data.get("fail", [])]
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root"); ap.add_argument("--site-root"); ap.add_argument("--en", action="store_true")
    ap.add_argument("--check", action="append", default=[]); ap.add_argument("--soft", action="append", default=[])
    ap.add_argument("--out")
    a = ap.parse_args()
    with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as f:
        f.write(json.dumps({"en": a.en, "checks": a.check, "soft": a.soft}) + "\n")
    if os.environ.get("FAKE_CRASH"):
        sys.exit(70)
    fail = [c for c in os.environ.get("FAKE_FAIL", "").split(",") if c]
    data = {"widths": {"1440": {}}, "fail": fail, "en": a.en}
    bad = judge(data, [c for c in a.check if c not in a.soft])
    data["checks"] = a.check; data["soft_checks"] = a.soft; data["violations"] = bad
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print("✘ القياس البصري: مخالفة" if bad else "✔ القياس البصري: صفر مخالفة في الفحوص المطلوبة")
    sys.exit(2 if bad else 0)
'''


def bm(*extra: str, out: str) -> list[str]:
    return ["python3", "tools/browser_measure.py", "--root", "{root}", "--site-root", "{site}/dist",
            *extra, "--out", out]


def make_root(t: Path) -> Path:
    (t / "tools").mkdir()
    (t / "runbook").mkdir()
    (t / "site" / "dist").mkdir(parents=True)
    (t / "tools" / "browser_measure.py").write_text(FAKE, encoding="utf-8")
    items = [
        {"id": "أ", "title": "بند أ", "phase": "1", "kind": "cmd", "argv": bm("--check", "overflow", out="audit/m/a.json")},
        {"id": "ب", "title": "بند ب", "phase": "1", "kind": "cmd", "argv": bm("--check", "anchor", out="audit/m/b.json")},
        {"id": "ج", "title": "بند ج", "phase": "1", "kind": "cmd", "argv": bm("--en", "--check", "overflow", out="audit/m/c.json")},
        {"id": "د", "title": "بند د", "phase": "1", "kind": "cmd", "blocking": False,
         "argv": bm("--check", "readiness", "--soft", "readiness", out="audit/m/d.json")},
        {"id": "هـ", "title": "بند هـ", "phase": "1", "kind": "cmd", "argv": ["bash", "-lc", "true"]},
    ]
    (t / "runbook" / "regression-items.json").write_text(
        json.dumps({"phase_order": ["1"], "items": items}, ensure_ascii=False), encoding="utf-8")
    return t


def run_gate(t: Path, **env) -> tuple[subprocess.CompletedProcess, list[dict], dict]:
    log = t / "calls.log"
    e = dict(os.environ, SITE_DIR=str(t / "site"), FAKE_LOG=str(log), **env)
    e.pop("SITE", None)
    out = t / "reg.json"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "regression_gate.py"), "--root", str(t),
                        "--until", "الكل", "--out", str(out)], cwd=t, env=e, capture_output=True, text=True,
                       timeout=120)
    calls = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    res = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    return r, calls, res


class SharedMeasure(unittest.TestCase):
    def test_one_browser_pass_per_surface_and_per_item_verdicts(self):
        with tempfile.TemporaryDirectory() as d:
            t = make_root(Path(d))
            r, calls, res = run_gate(t, FAKE_FAIL="anchor,readiness")
            self.assertEqual(len(calls), 2, f"نداءات المتصفح: {calls}\n{r.stdout}")
            self.assertEqual(sorted(c["en"] for c in calls), [False, True])
            ar = next(c for c in calls if not c["en"])
            self.assertEqual(sorted(ar["checks"]), ["anchor", "overflow", "readiness"])
            states = {row["id"]: row["state"] for row in res["rows"]}
            self.assertEqual(states, {"أ": "ناجح", "ب": "ساقط", "ج": "ناجح", "د": "ناجح", "هـ": "ناجح"})
            self.assertEqual(r.returncode, 2)
            self.assertEqual(res["blockers"], ["ب"])
            b = json.loads((t / "audit/m/b.json").read_text(encoding="utf-8"))
            a = json.loads((t / "audit/m/a.json").read_text(encoding="utf-8"))
            dd = json.loads((t / "audit/m/d.json").read_text(encoding="utf-8"))
            self.assertEqual((a["checks"], a["violations"]), (["overflow"], []))
            self.assertEqual((b["checks"], b["violations"]), (["anchor"], ["مخالفة anchor"]))
            self.assertEqual((dd["soft_checks"], dd["violations"]), (["readiness"], []))

    def test_shared_measure_crash_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            t = make_root(Path(d))
            r, calls, res = run_gate(t, FAKE_CRASH="1")
            states = {row["id"]: row["state"] for row in res["rows"]}
            self.assertEqual(states["أ"], "ساقط")
            self.assertEqual(states["ب"], "ساقط")
            self.assertEqual(states["ج"], "ساقط")
            self.assertEqual(states["هـ"], "ناجح")
            self.assertEqual(r.returncode, 2)


class CoverageSpeed(unittest.TestCase):
    def test_gate_coverage_under_five_seconds(self):
        t0 = time.time()
        r = subprocess.run([sys.executable, "tools/gate_coverage.py", "--root", ".", "--summary"],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        took = time.time() - t0
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertLess(took, 5.0, f"تغطية البوابات استغرقت {took:.1f} ثانية")


class G065Reuse(unittest.TestCase):
    """G065 تعيد قياس G064 المشترك فقط إن طابق تمامًا؛ وإلا تقيس حيًّا (السبب: تكرار ~31 ثانية)."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("bm_under_test", ROOT / "tools" / "browser_measure.py")
        self.bm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bm)
        self._d = tempfile.TemporaryDirectory()
        self.d = Path(self._d.name)
        (self.d / "dist").mkdir()
        (self.d / "dist" / "a.html").write_text("x", encoding="utf-8")
        from datetime import datetime, timezone
        self.fp = self.bm.dist_fingerprint(str(self.d / "dist"))
        self.data = {"url": "file:///p.html", "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "checks": ["overflow", "console", "anchor", "decision", "readiness"],
                     "dist_fingerprint": self.fp,
                     "widths": {"1440": {"readiness": [{"q": "س1", "found": True}], "phrases": [{"p": "هجمات مؤكدة"}]},
                                "1920": {"readiness": [{"q": "س1", "found": True}], "phrases": [{"p": "هجمات مؤكدة"}]}}}
        self.f = self.d / "shared.json"
        self.f.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self._d.cleanup()

    def call(self, **kw):
        a = dict(path=str(self.f), url="file:///p.html", widths=[1440, 1920], questions=["س1"],
                 phrases=["هجمات مؤكدة"], checks=["overflow", "anchor"], fingerprint=self.fp)
        a.update(kw)
        return self.bm.reusable(**a)[0]

    def test_exact_match_is_reused(self):
        self.assertIsNotNone(self.call())

    def test_rebuilt_site_is_measured_live(self):
        (self.d / "dist" / "a.html").write_text("changed", encoding="utf-8")
        self.assertIsNone(self.call(fingerprint=self.bm.dist_fingerprint(str(self.d / "dist"))))

    def test_other_page_checks_or_questions_are_measured_live(self):
        self.assertIsNone(self.call(url="file:///other.html"))
        self.assertIsNone(self.call(checks=["phrases"]))
        self.assertIsNone(self.call(questions=["س2"]))
        self.assertIsNone(self.call(widths=[1440]))
        self.assertIsNone(self.call(fingerprint=None))

    def test_old_or_missing_measure_is_measured_live(self):
        self.data["at"] = "2020-01-01T00:00:00+00:00"
        self.f.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        self.assertIsNone(self.call())
        self.assertIsNone(self.call(path=str(self.d / "none.json")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
