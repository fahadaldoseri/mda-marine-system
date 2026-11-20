#!/usr/bin/env python3
"""عقد جدول أزمنة المراحل (المقترح ٤، 20 نوفمبر 2026) على نسخة مؤقتة من المحرّك.

بعد `run`: كل سطر سكربت في السجل يحمل elapsed_s، ويُكتب logs/runbook/D/timings.md تلقائيًا بصفوف
المراحل وزمن الإعادة منفصلًا، وزمن خطوة الوكيل من تسليمها إلى إتمامها، والتوقف بفشل يكتب الجدول أيضًا،
ورمز خروج التشغيل لا يتغير بسبب الجدول.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
FAILS = []
D = "2030-01-01"


def expect(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAILS.append(msg)


def step(sid, phase, cmd):
    return {"id": sid, "title": sid, "kind": "script", "phase": phase,
            "command": ["bash", "-lc", cmd],
            "assert": [{"type": "cmd", "command": ["bash", "-lc", f"test -s logs/runbook/{{date}}/{sid}.log"]}],
            "links": {"rules": ["ق"], "files": ["tools/runbook.py"], "folders": [], "gates": [], "tests": []},
            "on_fail": "stop"}


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)
        (t / "tools").mkdir()
        (t / "runbook" / "prompts").mkdir(parents=True)
        (t / "docs").mkdir()
        (t / "reports").mkdir()
        shutil.copy(B / "tools" / "runbook.py", t / "tools")
        (t / "runbook" / "prompts" / "w.md").write_text("اكتب reports/{date}-sectioned.md\n", encoding="utf-8")
        agent = {"id": "W1", "title": "كتابة", "kind": "agent", "phase": "write", "prompt": "runbook/prompts/w.md",
                 "writes": ["reports/{date}-sectioned.md"],
                 "assert": [{"type": "min_bytes", "path": "reports/{date}-sectioned.md", "n": 10}],
                 "links": {"rules": ["ق"], "files": ["runbook/prompts/w.md"], "folders": [], "gates": [], "tests": []},
                 "on_fail": "stop"}
        manifest = {"version": 1, "ledger_dir": "logs/runbook", "phase_order": ["ingest", "write", "gates"],
                    "exempt": ["reports/*", "runbook/*", "docs/*", "tools/runbook.py"],
                    "exempt_reasons": {"reports/*": "مخرجات", "runbook/*": "المحرّك", "docs/*": "كتيب",
                                       "tools/runbook.py": "المحرّك"},
                    "steps": [step("S1", "ingest", "sleep 0.3; echo ok"), agent,
                              step("G1", "gates", "test -f ok.flag && echo ok || { echo blocked; exit 2; }")],
                    "sections": []}
        (t / "runbook" / "runbook.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        def rb(*args):
            return subprocess.run([sys.executable, "tools/runbook.py", *args, "--date", D, "--no-auto-redo"]
                                  if args[0] == "run" else [sys.executable, "tools/runbook.py", *args, "--date", D],
                                  cwd=t, capture_output=True, text=True)

        subprocess.run([sys.executable, "tools/runbook.py", "handbook"], cwd=t, capture_output=True)
        r = rb("run")
        expect(r.returncode == 10, f"التوقف عند خطوة الوكيل برمز 10 (الواقع {r.returncode})")
        (t / "reports" / f"{D}-sectioned.md").write_text("نص كافٍ للتقرير " * 3, encoding="utf-8")
        rb("complete", "W1")
        r = rb("run")
        expect(r.returncode == 2, "فشل البوابة يبقى رمز 2 مع كتابة الجدول")
        tm = t / "logs" / "runbook" / D / "timings.md"
        expect(tm.is_file() and "⏱ جدول الأزمنة" in r.stdout, "الجدول يُكتب ويُعلن عند التوقف بفشل")
        (t / "ok.flag").write_text("1")
        r = rb("run", "--redo", "S1")
        expect(r.returncode == 0, "الاستئناف بعد الإصلاح يكتمل برمز 0")
        led = [json.loads(x) for x in (t / "logs" / "runbook" / f"{D}.jsonl").read_text(encoding="utf-8").splitlines()]
        scripts = [e for e in led if e.get("step") in ("S1", "G1") and e.get("status") in ("done", "failed")]
        expect(scripts and all(isinstance(e.get("elapsed_s"), (int, float)) for e in scripts),
               "كل سطر سكربت يحمل elapsed_s")
        s1 = [e["elapsed_s"] for e in led if e.get("step") == "S1" and e.get("status") == "done"]
        expect(len(s1) == 2 and all(x >= 0.3 for x in s1), "زمن S1 مقيس في التشغيل والإعادة (≥ 0.3 ث)")
        text = tm.read_text(encoding="utf-8")
        rows = {ln.split("|")[1].strip(): ln for ln in text.splitlines() if ln.startswith("| ") and ln.count("|") >= 7}
        expect(all(p in rows for p in ("ingest", "write", "gates")), "صف لكل مرحلة بترتيب المانيفست")
        expect("| S1 | ingest | 2 |" in text, "S1 بتشغيلين (أول تشغيل + إعادة منفصلة)")
        expect("| G1 | gates | 2 |" in text and "| 1 |" in text.split("| G1 |")[1].splitlines()[0],
               "G1 بتشغيلين أحدهما فاشل")
        expect("| W1 | write | 1 |" in text, "خطوة الوكيل تُحسب من تسليمها إلى إتمامها")
        r = rb("timings")
        expect(r.returncode == 0 and "# أزمنة التشغيل" in r.stdout, "الأمر timings يطبع الجدول")
    print(f"الحصيلة: فشل {len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
