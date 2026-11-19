#!/usr/bin/env python3
"""البوابة الواحدة والتسليم السحابي (2026-11-19، قرار المالك «نفّذه في طلب جديد»).

العطل المقيس: الخط يشغّل كل بوابات المانيفست، ثم تُعاد `final_gate.sh` كاملة لأن حكم النشر
لا يقرأ إلا gate.json بمرحلة final، وهي لا تُكتب إلا منها. فتُعاد الاختبارات والبناء، وتعدّل
خطواتها المحرِّرة النص بعد البناء فتكسر G042 وتفرض إعادة البناء (تشغيل 19 نوفمبر).

1. `runbook.py gate-json --final` يكتب stage=final من سجل المحرّك، ويرفض إن بقيت بوابة بعد --through.
2. G069 في المانيفست: آخر بوابة قبلها هي --through نفسها، فلا تسقط بوابة من الحكم.
3. `cloud_deliver.plan`: ملفات اليوم والأسطح المشتركة تُنسخ، والصفحات القديمة المختلفة انحراف لا يُنسخ.
4. `cloud_deliver` يمنع قبل أي استنساخ أو نسخ إن كان حكم النشر يمنع.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE / "tools"))
import test_runbook_hardening as H  # noqa: E402
import cloud_deliver as CD  # noqa: E402


def test_gate_json_final_from_ledger() -> None:
    m = dict(H.BASE, gate_phases=["gates", "finalize"],
             steps=[H.step("G1", phase="gates", command=["echo", "ok"], gate_title="فحص أول"),
                    H.step("G2", phase="finalize", command=["bash", "-c", "echo w; exit 0"], gate_title="فحص ثانٍ")])
    top, root = H.project(m)
    try:
        H.eng(root, "run", "--date", "2026-10-24")
        gp = root / "logs" / "gate-2026-10-24" / "gate.json"
        r = H.eng(root, "gate-json", "--date", "2026-10-24", "--final")
        assert r.returncode == 2 and "--through" in r.stdout, r.stdout
        r = H.eng(root, "gate-json", "--date", "2026-10-24", "--through", "G1", "--final")
        assert r.returncode == 2 and "G2" in r.stdout, "بوابة بعد --through يجب أن تمنع الحكم النهائي"
        r = H.eng(root, "gate-json", "--date", "2026-10-24", "--through", "G2", "--final")
        g = json.loads(gp.read_text(encoding="utf-8"))
        assert r.returncode == 0 and g["stage"] == "final" and g["exit_code"] == 0, g
        H.eng(root, "gate-json", "--date", "2026-10-24", "--through", "G1")
        assert json.loads(gp.read_text(encoding="utf-8"))["stage"] == "provisional"
    finally:
        shutil.rmtree(top)


def test_manifest_final_step_covers_every_gate() -> None:
    m = json.loads((HERE / "runbook" / "runbook.json").read_text(encoding="utf-8"))
    ids = [s["id"] for s in m["steps"]]
    g069 = m["steps"][ids.index("G069")]
    cmd = " ".join(g069["command"])
    assert "--final" in cmd and "publish_verdict.py" in cmd
    through = cmd.split("--through", 1)[1].split()[0]
    phases = m["gate_phases"]
    before = [s for s in m["steps"][:ids.index("G069")] if s.get("phase") in phases]
    assert before[-1]["id"] == through, f"--through {through} ليست آخر بوابة قبل G069 ({before[-1]['id']})"
    after = [s["id"] for s in m["steps"][ids.index("G069") + 1:] if s.get("phase") in phases and not s.get("disabled")]
    assert not after, f"بوابات بعد الحكم النهائي: {after}"


def test_plan_copies_today_and_shared_only() -> None:
    top = Path(tempfile.mkdtemp(prefix="cd-"))
    try:
        dist, live = top / "dist", top / "live"
        files = {"reports/2026-11-20.html": "new", "index.html": "home2", "reports/2026-11-12.html": "old2",
                 "assets/site.css": "css2", "reports/2026-11-18.html": "same"}
        for rel, txt in files.items():
            (dist / rel).parent.mkdir(parents=True, exist_ok=True)
            (dist / rel).write_text(txt, encoding="utf-8")
        for rel, txt in {"index.html": "home1", "reports/2026-11-12.html": "old1", "assets/site.css": "css1",
                         "reports/2026-11-18.html": "same", "fonts/x.woff2": "keep"}.items():
            (live / rel).parent.mkdir(parents=True, exist_ok=True)
            (live / rel).write_text(txt, encoding="utf-8")
        p = CD.plan(dist, live, "2026-11-20")
        assert p["copy"] == ["assets/site.css", "index.html", "reports/2026-11-20.html"], p
        assert p["drift"] == ["reports/2026-11-12.html"] and p["unchanged"] == 1, p
    finally:
        shutil.rmtree(top)


def test_blocked_verdict_stops_before_clone() -> None:
    top = Path(tempfile.mkdtemp(prefix="cd-"))
    try:
        brain = top / "brain"
        (brain / "tools").mkdir(parents=True)
        shutil.copy(HERE / "tools" / "publish_verdict.py", brain / "tools" / "publish_verdict.py")
        live = top / "live-not-created"
        rc = CD.main(["--date", "2026-11-20", "--brain", str(brain), "--site", str(top / "site"),
                      "--live-dir", str(live), "--push"])
        out = json.loads((brain / "logs" / "deliver-2026-11-20.json").read_text(encoding="utf-8"))
        assert rc == 2 and not live.exists(), out
        assert "حكم النشر يمنع" in out["message"], out
    finally:
        shutil.rmtree(top)


if __name__ == "__main__":
    for t in (test_gate_json_final_from_ledger, test_manifest_final_step_covers_every_gate,
              test_plan_copies_today_and_shared_only, test_blocked_verdict_stops_before_clone):
        t()
        print(f"  ✔ {t.__name__}")
    print("✔ البوابة الواحدة والتسليم السحابي")
