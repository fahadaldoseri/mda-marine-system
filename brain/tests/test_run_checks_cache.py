#!/usr/bin/env python3
"""عقد ذاكرة فحوص G001 (المقترح ١، 20 نوفمبر 2026): لا تُعاد نتيجة مخزّنة إلا إن لم يتغير أي مدخل.

موجب: فحص بايثون قرأ ملفًا لم يتغير ← النتيجة المخزّنة صالحة.
سوالب (كلها تُعيد الفحص): تعديل ملف مقروء · ظهور ملف استُعلم عن غيابه · ملف جديد في دليل مسرود ·
عملية غير بايثون · بايثون فرعي بلا متتبّع · خروج بلا atexit · رمز غير صفري · مفتاح مختلف.
وعقد الربط: الذاكرة لا تعمل إلا من أمر G001، ولا تمرّرها بوابة التسليم.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
TOOL = B / "tools" / "run_checks_cache.py"
TRACER = B / "tools" / "checks_trace"
FAILS = []


def expect(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAILS.append(msg)


def run_check(work: Path, cache: Path, code: str, name: str = "c") -> int:
    meta = cache.parent
    key = meta / f"{name}.key"
    key.write_bytes(f"{name}\0{code}".encode())
    trace = meta / f"{name}.trace"
    trace.write_text("")
    env = dict(os.environ, CHECKS_TRACE=str(trace), PYTHONPATH=str(TRACER))
    rc = subprocess.run([sys.executable, "-c", code], cwd=work, env=env).returncode
    subprocess.run([sys.executable, str(TOOL), "record", str(cache), str(key), str(trace), str(rc)],
                   capture_output=True, check=True)
    return rc


def cached(work: Path, cache: Path, name: str = "c", code: str | None = None) -> bool:
    key = cache.parent / f"{name}.key"
    if code is not None:
        key.write_bytes(f"{name}\0{code}".encode())
    return subprocess.run([sys.executable, str(TOOL), "lookup", str(cache), str(key)]).returncode == 0


def main() -> int:
    if not TOOL.is_file() or not (TRACER / "sitecustomize.py").is_file():
        print("  ✘ أداة الذاكرة أو المتتبّع غير موجودة")
        return 1
    with tempfile.TemporaryDirectory() as d:
        w = Path(d) / "work"
        w.mkdir()
        (Path(d) / "meta").mkdir()
        cache = Path(d) / "meta" / "cache.json"
        fresh = Path(d) / "absent-dir" / "c.json"
        (Path(d) / "absent-dir-key").write_bytes(b"k")
        subprocess.run([sys.executable, str(TOOL), "record", str(fresh), str(Path(d) / "absent-dir-key"),
                        str(Path(d) / "none.trace"), "0"], capture_output=True)
        expect(fresh.is_file(), "دليل الذاكرة يُنشأ عند أول تسجيل (لا ضياع صامت للذاكرة)")
        data = w / "data.txt"
        data.write_text("أ")

        code = "open('data.txt').read()"
        expect(run_check(w, cache, code) == 0 and cached(w, cache), "موجب: ملف مقروء لم يتغير ← نتيجة مخزّنة")
        expect(not cached(w, cache, code="open('data.txt').read() "), "مفتاح مختلف (أمر آخر) ← يُعاد")
        data.write_text("ب")
        expect(not cached(w, cache, code=code), "تعديل الملف المقروء ← يُعاد")

        code = "import os; os.path.exists('later.txt')"
        run_check(w, cache, code, "s")
        expect(cached(w, cache, "s"), "استعلام عن غياب ملف ← مخزّن ما دام غائبًا")
        (w / "later.txt").write_text("x")
        expect(not cached(w, cache, "s"), "ظهور الملف الذي استُعلم عن غيابه ← يُعاد")

        (w / "dir").mkdir()
        code = "import os; os.listdir('dir')"
        run_check(w, cache, code, "l")
        expect(cached(w, cache, "l"), "سرد دليل لم يتغير ← مخزّن")
        (w / "dir" / "new.md").write_text("x")
        expect(not cached(w, cache, "l"), "ملف جديد في الدليل المسرود ← يُعاد")

        run_check(w, cache, "import subprocess; subprocess.run(['true'])", "x")
        expect(not cached(w, cache, "x"), "عملية غير بايثون (لا تتبع لما تقرؤه) ← لا تخزين")

        run_check(w, cache, "import subprocess,sys; subprocess.run([sys.executable,'-c','1'], env={})", "e")
        expect(not cached(w, cache, "e"), "بايثون فرعي بلا متتبّع ← لا تخزين")

        run_check(w, cache, "import subprocess,sys; subprocess.run([sys.executable,'-I','-c','1'])", "i")
        expect(not cached(w, cache, "i"), "بايثون معزول -I يتجاوز المتتبّع ← لا تخزين")

        run_check(w, cache, "import os; open('data.txt').read(); os._exit(0)", "q")
        expect(not cached(w, cache, "q"), "خروج بلا atexit (تتبع ناقص) ← لا تخزين")

        run_check(w, cache, "import sys; open('data.txt').read(); sys.exit(1)", "f")
        expect(not cached(w, cache, "f"), "فحص فاشل ← لا تخزين")

        run_check(w, cache, "import subprocess,sys; subprocess.run([sys.executable,'-c',\"open('data.txt').read()\"])", "p")
        expect(cached(w, cache, "p"), "بايثون فرعي مُتتبَّع ← مخزّن")
        data.write_text("ج")
        expect(not cached(w, cache, "p"), "تعديل ملف قرأه البايثون الفرعي ← يُعاد")

        cache.write_text("{تالف")
        expect(not cached(w, cache, code=code), "ذاكرة تالفة ← يُعاد (فشل مغلق)")

    rc_sh = (B / "tests" / "run_checks.sh").read_text(encoding="utf-8")
    expect('if [ -z "${RUN_CHECKS_CACHE:-}" ]; then' in rc_sh, "run_checks.sh بلا RUN_CHECKS_CACHE يشغّل كل فحص")
    expect("RUN_CHECKS_CACHE" not in (B / "tools" / "final_gate.sh").read_text(encoding="utf-8"),
           "بوابة التسليم final_gate.sh تشغّل run_checks كاملًا بلا ذاكرة")
    steps = json.loads((B / "runbook" / "runbook.json").read_text(encoding="utf-8"))["steps"]
    users = [s["id"] for s in steps if "RUN_CHECKS_CACHE" in json.dumps(s.get("command"), ensure_ascii=False)]
    expect(users == ["G001"], f"الذاكرة يمرّرها أمر G001 وحده (الواقع: {users})")
    print(f"الحصيلة: فشل {len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
