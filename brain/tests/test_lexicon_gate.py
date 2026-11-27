#!/usr/bin/env python3
"""اختبار بوابة العيوب اللغوية ومعجمها المشتق (ك-328).

الحالة الموجبة: متن التقرير المعتمد يجب أن يخرج بصفر كلمات مشتبهة.
الحالة السالبة: لفظ مصطنع مُدسّ يجب أن يُكتشف ويُسمّى في المخرج.
بهذا لا يمكن «إسكات» البوابة بتوسيع المعجم بلا دليل.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
GATE = ROOT / "validators" / "check_prose_defects.py"
CORPUS_TOOL = ROOT / "tools" / "build_lexicon_corpus.py"
REPORT = ROOT / "reports" / "2026-10-29-sectioned.md"


def run(args: list[str]) -> tuple[int, str]:
    p = subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=ROOT)
    return p.returncode, (p.stdout + p.stderr)


def main() -> int:
    failures: list[str] = []

    rc, out = run([str(CORPUS_TOOL), "--check"])
    if rc != 0:
        failures.append(f"معجم المفردات غير مطابق للمصادر (رمز {rc}): {out.strip()[-160:]}")
        try:  # تشخيص: الكلمات الزائدة/الناقصة والمصادر الحاضرة (يظهر في سجل G001)
            sys.path.insert(0, str(ROOT / "tools"))
            import json as _j
            import build_lexicon_corpus as _b
            _stored = set(_j.loads((ROOT / "appendices" / "lexicon-corpus.json").read_text(encoding="utf-8"))["words"])
            _fresh = set(_b.build()["words"])
            import subprocess as _s
            _d = ROOT / "logs" / "runbook"
            _d.mkdir(parents=True, exist_ok=True)
            (_d / "diag-lexicon.txt").write_text(
                "EXTRA: " + " | ".join(sorted(_fresh - _stored)[:30]) + "\nMISSING: " + " | ".join(sorted(_stored - _fresh)[:30])
                + "\nGIT:\n" + _s.run(["git", "status", "--short", "reports", "sections", "appendices"], capture_output=True, text=True, cwd=ROOT).stdout
                + "\nSRC:\n" + "\n".join(str(p.relative_to(ROOT)) for p in _b.source_paths()), encoding="utf-8")
            print("   تشخيص المصادر:", [str(p.relative_to(ROOT)) for p in _b.source_paths() if "sectioned" in p.name][-4:])
        except Exception as e:  # noqa: BLE001
            print("   تعذّر التشخيص:", e)
    else:
        print(f"   ✔ المعجم المشتق مطابق: {out.strip().splitlines()[-1][:110]}")

    if REPORT.is_file():
        rc, out = run([str(GATE), str(REPORT)])
        if "كلمات مشتبهة" in out and "| كلمات خارج المعجم (تحذير) | 0" not in out:
            failures.append(f"تحذيرات كاذبة في المتن المعتمد: {out.strip().splitlines()[-1][:120]}")
        elif rc not in (0, 1):
            failures.append(f"بوابة العيوب انهارت على المتن (رمز {rc})")
        else:
            print("   ✔ صفر كلمات مشتبهة على متن اليوم")
    else:
        print("   … لا متن لليوم — تُختبر الحالة السالبة وحدها")

    with tempfile.TemporaryDirectory() as tmp:
        sample = pathlib.Path(tmp) / "neg.md"
        sample.write_text("# اختبار\n\nواصلت السفينة ترفيم الحمولة عبر ممر مضيّق.\n", encoding="utf-8")
        rc, out = run([str(GATE), str(sample)])
        if "ترفيم" not in out:
            failures.append("اللفظ المصطنع «ترفيم» لم يُكتشف — البوابة أُسكِتت")
        else:
            print("   ✔ اللفظ المصطنع «ترفيم» يُكتشف (الحالة السالبة ناجحة)")

    if failures:
        print("\n   ✘ فشل:")
        for f in failures:
            print(f"     - {f}")
        return 1
    print("\n   النتيجة: ناجح")
    return 0


if __name__ == "__main__":
    sys.exit(main())