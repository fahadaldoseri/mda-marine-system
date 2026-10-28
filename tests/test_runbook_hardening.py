#!/usr/bin/env python3
"""اختبارات تقوية محرّك الكتيب (مرحلة 24 أكتوبر 2026): مسارات محمولة · تضمين البرومت · ربط حقيقي ·
ترتيب المراحل · شروط إتمام غير تافهة · متغيرات البيئة للخطوات.
كل اختبار يعمل على مشروع مؤقت صغير ولا يلمس المشروع الحقيقي.
الاستعمال: python3 tests/test_runbook_hardening.py    (رمز 0 = نجح الكل)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ENGINE = HERE / "tools" / "runbook.py"
PASS = FAIL = 0


def ok(cond, name):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✔ {name}")
    else:
        FAIL += 1
        print(f"  ✘ {name}")


def project(manifest, files=None, site_dir="seawatch"):
    """يبني مشروعًا مؤقتًا: brain/ + شجرة موقع شقيقة، ويعيد جذر brain."""
    top = Path(tempfile.mkdtemp(prefix="rbh-"))
    root = top / "brain"
    (root / "tools").mkdir(parents=True)
    (root / "runbook").mkdir()
    (root / "docs").mkdir()
    shutil.copy(ENGINE, root / "tools" / "runbook.py")
    (top / site_dir / "generator").mkdir(parents=True)
    (top / site_dir / "generator" / "build.py").write_text("print('built')\n", encoding="utf-8")
    for rel, txt in (files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    (root / "runbook" / "runbook.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run([sys.executable, str(root / "tools" / "runbook.py"), "handbook", "--root", str(root)], capture_output=True)
    return top, root


def eng(root, *args, env=None):
    e = dict(os.environ)
    e.pop("SITE_DIR", None)
    e.pop("BRAIN_DIR", None)
    e.update(env or {})
    return subprocess.run([sys.executable, str(root / "tools" / "runbook.py"), *args, "--root", str(root)],
                          capture_output=True, text=True, env=e)


def step(i, **kw):
    s = {"id": i, "title": f"خطوة {i}", "kind": "script", "phase": "gates", "command": ["true"],
         "assert": [{"type": "cmd", "command": ["bash", "-lc", f"test -s logs/runbook/{{date}}/{i}.log"]}],
         "links": {"rules": ["ق"], "files": [], "folders": [], "gates": [], "tests": []}, "on_fail": "stop"}
    if "asserts" in kw:
        s["assert"] = kw.pop("asserts")
    s.update(kw)
    if s.get("command") is None:
        s.pop("command", None)
    return s


BASE = {"version": 1, "ledger_dir": "logs/runbook", "exempt": ["runbook/*", "docs/*", "tools/runbook.py"], "exempt_reasons": {"runbook/*": "ملفات المحرّك", "docs/*": "كتيب مولَّد", "tools/runbook.py": "المحرّك نفسه"},
        "phase_order": ["verify", "ingest", "write", "gates", "build", "outputs", "finalize", "deliver"], "sections": []}


def test_env_and_placeholders():
    m = dict(BASE, steps=[step("S1", command=["bash", "-lc", "echo D=$D; echo SITE=$SITE_DIR; echo B=$BRAIN_DIR; ls {site}/generator"],
                               asserts=[{"type": "file_exists", "path": "{site}/generator/build.py"},
                                       {"type": "cmd", "command": ["bash", "-lc", "grep -q 'D=2026-10-24' logs/runbook/{date}/S1.log"]}],
                               links={"rules": ["ق"], "files": ["{site}/generator/build.py"], "folders": ["{site}/generator"], "gates": [], "tests": []})])
    top, root = project(m)
    r = eng(root, "run", "--date", "2026-10-24")
    ok(r.returncode == 0, "الأمر يرى D وSITE_DIR وBRAIN_DIR ويحل {site}")
    log = (root / "logs/runbook/2026-10-24/S1.log").read_text(encoding="utf-8") if (root / "logs/runbook/2026-10-24/S1.log").exists() else ""
    ok("D=2026-10-24" in log and "SITE=" in log and "build.py" in log, "سجل الخطوة يثبت المتغيرات")
    ok(eng(root, "verify").returncode == 0, "verify يحل {site} في الروابط (مجلد الموقع seawatch)")
    shutil.rmtree(top)
    top, root = project(m, site_dir="site")
    ok(eng(root, "verify").returncode == 0, "verify يكتشف مجلد الموقع الشقيق باسم site أيضًا")
    shutil.rmtree(top)


def test_include():
    m = dict(BASE, steps=[step("W1", kind="agent", phase="write", prompt="runbook/prompts/w.md", command=None,
                               asserts=[{"type": "min_bytes", "path": "reports/{date}.md", "n": 5}],
                               links={"rules": ["ق"], "files": ["sections/brief.md"], "folders": [], "gates": [], "tests": []})])
    top, root = project(m, {"runbook/prompts/w.md": "ابدأ\n{{include sections/brief.md}}\nانتهى {date}\n",
                            "sections/brief.md": "نص-المختصر-الفريد\n"})
    r = eng(root, "run", "--date", "2026-10-24")
    ok(r.returncode == 10 and "نص-المختصر-الفريد" in r.stdout and "انتهى 2026-10-24" in r.stdout, "برومت الوكيل يعرض نص الملف المضمَّن")
    (root / "sections/brief.md").unlink()
    r = eng(root, "verify")
    ok(r.returncode == 2 and "brief.md" in r.stdout, "verify يرفض تضمينًا يحيل إلى ملف غائب")
    shutil.rmtree(top)


def test_sections_token():
    secs = [{"id": "b", "title": "القسم الثاني", "order": 2, "heading": "القسم الثاني", "block": "sections/b.md", "validator": "tools/v.py",
             "prompt_snippet": "runbook/prompts/sections/b.md", "tests": ["tests/t.py"], "files": []},
            {"id": "a", "title": "القسم الأول", "order": 1, "heading": "القسم الأول", "block": "sections/a.md", "validator": "tools/v.py",
             "prompt_snippet": "runbook/prompts/sections/a.md", "tests": ["tests/t.py"], "files": []}]
    m = dict(BASE, sections=secs, steps=[step("W1", kind="agent", phase="write", prompt="runbook/prompts/w.md", command=None,
                                              asserts=[{"type": "min_bytes", "path": "reports/{date}.md", "n": 5}])])
    top, root = project(m, {"runbook/prompts/w.md": "ابدأ\n{{sections}}\nانتهى\n",
                            "runbook/prompts/sections/a.md": "# مقتطف أ\nتعليمة-أ-الفريدة\n",
                            "runbook/prompts/sections/b.md": "# مقتطف ب\nتعليمة-ب-الفريدة\n",
                            "sections/a.md": "x", "sections/b.md": "x", "tools/v.py": "x=1", "tests/t.py": "x=1"})
    r = eng(root, "run", "--date", "2026-10-24")
    out = r.stdout
    ok(r.returncode == 10 and out.index("القسم الأول") < out.index("القسم الثاني"), "{{sections}} يعرض أقسام السجل بترتيبها")
    ok("تعليمة-أ-الفريدة" in out and "تعليمة-ب-الفريدة" in out, "{{sections}} يضمّن مقتطف كل قسم")
    shutil.rmtree(top)


def test_reachability():
    files = {"tools/a.py": "import b\nopen('appendices/rules.json')\n", "tools/b.py": "x=1\n", "appendices/rules.json": "{}\n",
             "appendices/orphan.json": "{}\n", "tools/lonely.py": "print(1)\n", "docs/note.md": "x\n"}
    m = dict(BASE, steps=[step("S1", command=["python3", "tools/a.py"], links={"rules": ["ق"], "files": ["tools/a.py"], "folders": [], "gates": [], "tests": []})])
    top, root = project(m, files)
    r = eng(root, "verify")
    out = r.stdout
    ok("appendices/orphan.json" in out, "ملف يتيم داخل appendices يُكشف (لا استثناء شامل للمجلد)")
    ok("tools/lonely.py" in out, "أداة يتيمة تُكشف")
    ok("appendices/rules.json" not in out and "tools/b.py" not in out, "ما تصل إليه خطوة عبر سلسلة إحالات يُعدّ متصلًا (قابلية الوصول)")
    shutil.rmtree(top)


def test_phase_order():
    m = dict(BASE, steps=[step("B1", phase="build"), step("G1", phase="gates")])
    top, root = project(m)
    r = eng(root, "verify")
    ok(r.returncode == 2 and "ترتيب المراحل" in r.stdout, "خطوة بوابة بعد خطوة بناء تُرفض (ترتيب المراحل)")
    shutil.rmtree(top)
    m = dict(BASE, steps=[step("G1", phase="gates"), step("B1", phase="build"), step("O1", phase="outputs")])
    top, root = project(m)
    ok(eng(root, "verify").returncode == 0, "الترتيب gates ثم build ثم outputs مقبول")
    shutil.rmtree(top)


def test_trivial_assert():
    m = dict(BASE, steps=[step("D1", phase="deliver", asserts=[{"type": "cmd", "command": ["bash", "-lc", "true"]}])])
    top, root = project(m)
    r = eng(root, "verify")
    ok(r.returncode == 2 and "شرط تافه" in r.stdout, "شرط إتمام تافه (true) يُرفض")
    shutil.rmtree(top)


def test_gates_status_covers_gate_phases():
    m = dict(BASE, gate_phases=["gates", "outputs", "finalize"],
             steps=[step("G1", phase="gates", command=["true"]), step("B1", phase="build", command=["true"]),
                    step("O1", phase="outputs", command=["false"])])
    top, root = project(m)
    eng(root, "run", "--date", "2026-10-24")
    r = eng(root, "gates-status", "--date", "2026-10-24")
    ok(r.returncode == 2 and "O1" in r.stdout, "gates-status يعدّ مرحلة outputs بوابة ويمنع إن لم تكتمل")
    shutil.rmtree(top)


def test_gate_json_from_ledger():
    m = dict(BASE, gate_phases=["gates", "finalize"],
             steps=[step("G1", phase="gates", command=["echo", "ok"], gate_title="فحص أول"),
                    step("G2", phase="finalize", command=["bash", "-c", "echo bad; exit 5"], gate_title="فحص ثانٍ")])
    top, root = project(m)
    eng(root, "run", "--date", "2026-10-24")
    r = eng(root, "gate-json", "--date", "2026-10-24")
    gp = root / "logs" / "gate-2026-10-24" / "gate.json"
    g = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else {}
    ok(r.returncode == 0 and g.get("status") == "block" and g.get("exit_code") == 2, "gate-json يكتب gate.json من السجل لا من الذاكرة")
    ok([x["step"] for x in g.get("steps", [])] == ["فحص أول", "فحص ثانٍ"], "gate-json يحفظ أسماء البوابات وترتيبها")
    ok(g.get("blocked_steps") == ["فحص ثانٍ"], "gate-json يسجّل الخطوات المانعة")
    eng(root, "gate-json", "--date", "2026-10-24", "--through", "G1")
    g = json.loads(gp.read_text(encoding="utf-8"))
    ok([x["id"] for x in g["steps"]] == ["G1"] and g["status"] == "ok", "gate-json --through يحسب حتى الخطوة المحددة فقط")
    shutil.rmtree(top)


if __name__ == "__main__":
    for t in (test_env_and_placeholders, test_include, test_sections_token, test_reachability, test_phase_order, test_trivial_assert, test_gates_status_covers_gate_phases, test_gate_json_from_ledger):
        print(t.__name__)
        t()
    print(f"\nالحصيلة: نجح {PASS} · فشل {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
