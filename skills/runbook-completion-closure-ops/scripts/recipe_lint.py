#!/usr/bin/env python3
"""حارس جودة مرجع المصائد: لا وصفة بلا أمر إثبات قابل للتشغيل، ولا أمر يشير إلى أداة غير موجودة.

السبب (جولة 2026-11-02): مرجع المصائد ينمو مع كل عطل مُغلق، فإذا دخلته وصفة
بخلايا ناقصة أو بلا أمر إثبات صار «الإغلاق وثيقة بلا دليل» — وهو ما يمنعه
حارس الإغلاق في المشروع. وإذا أشار الأمر إلى أداة أُعيدت تسميتها أو حُذفت
صار الدليل غير قابل لإعادة التشغيل. هذه الأداة تجعل القاعدتين مقيسَتين.

الاستعمال:
  python3 scripts/recipe_lint.py                       # فحص المرجع الحاكم
  python3 scripts/recipe_lint.py --playbook PATH       # فحص مرجع آخر
  python3 scripts/recipe_lint.py --check-paths         # + التحقق من وجود الأدوات المُشار إليها
  python3 scripts/recipe_lint.py --selftest            # إثبات أن الحارس يميّز الصحيح من الفاسد

يفشل مغلقًا (رمز 2) عند: خلية فارغة · `TODO` · أمر إثبات بلا أمر قابل للتشغيل ·
مسار أداة غير موجود (مع `--check-paths`) · مرجع بلا وصفات.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve()
DEFAULT = HERE.parents[1] / "references" / "playbook.md"
CMD = re.compile(r"\b(python3|bash|gh|sh|curl)\b")
TOKEN = re.compile(r"[A-Za-z0-9_./\u0600-\u06FF-]+\.(?:py|sh|json|md|html)\b")
SKIP_TOKEN = re.compile(r"^[A-Za-z0-9_-]+\.(?:py|sh|json|md|html)$")  # اسم ملف بلا مسار


def roots() -> list[pathlib.Path]:
    """جذور البحث عن الأدوات: الدماغ والموقع، من البيئة أو من المسارات المعتادة."""
    out = []
    for k in ("BRAIN_DIR", "SITE_DIR"):
        v = os.environ.get(k)
        if v:
            out.append(pathlib.Path(v))
    out += [pathlib.Path("/home/ubuntu/brain-marine-news"), pathlib.Path("/home/ubuntu/seawatch")]
    return [p for p in out if p.is_dir()]


def scan(path: pathlib.Path, check_paths: bool, base: list[pathlib.Path]) -> tuple[list[str], int]:
    bad: list[str] = []
    rows = 0
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s.startswith("|") or set(s) <= set("|-: "):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and cells[0] in ("الخطوة", "المصيدة", "الرقم"):
            continue
        if len(cells) != 5:
            bad.append(f"سطر {i}: عدد الخلايا {len(cells)} بدل 5")
            continue
        rows += 1
        empty = [j + 1 for j, c in enumerate(cells) if not c]
        if empty:
            bad.append(f"سطر {i}: خلايا فارغة ({', '.join(map(str, empty))})")
        if "TODO" in s:
            bad.append(f"سطر {i}: يحتوي TODO")
        if not CMD.search(cells[4]):
            bad.append(f"سطر {i}: «أمر الإثبات» بلا أمر قابل للتشغيل: {cells[4][:60]}")
            continue
        if check_paths:
            for t in set(TOKEN.findall(cells[4])):
                if SKIP_TOKEN.match(t) or "<" in t or t.startswith("/"):
                    continue
                if not any((r / t).exists() for r in base):
                    bad.append(f"سطر {i}: مسار غير موجود في أي جذر: {t}")
    if rows == 0:
        bad.append("لا وصفات في المرجع (قاعدة الفشل المغلق)")
    return bad, rows


def selftest() -> int:
    """إثبات سلوك الحارس: موجب حقيقي وسالبة حقيقية على ملفات مؤقتة."""
    import tempfile

    cases = [
        ("صحيحة", "| S010 | عرض | سبب | إصلاح | `python3 tools/runbook.py verify` |\n", 0),
        ("خلايا ناقصة", "| S010 | عرض |  | إصلاح | `python3 tools/runbook.py verify` |\n", 2),
        ("بلا أمر", "| S010 | عرض | سبب | إصلاح | راجع السجل |\n", 2),
        ("تحمل TODO", "| S010 | TODO | سبب | إصلاح | `python3 tools/runbook.py verify` |\n", 2),
        ("جدول فارغ", "# بلا وصفات\n", 2),
    ]
    fails = 0
    with tempfile.TemporaryDirectory() as td:
        for name, body, want in cases:
            p = pathlib.Path(td) / f"{abs(hash(name))}.md"
            p.write_text(body, encoding="utf-8")
            bad, _ = scan(p, False, [])
            got = 2 if bad else 0
            ok = got == want
            fails += 0 if ok else 1
            print(f"   {'✔' if ok else '✘'} {name}: rc={got} (المتوقع {want})")
    if fails:
        print(f"   ✘ فشل الاختبار الذاتي: {fails} حالة")
        return 2
    print(f"   ✔ الاختبار الذاتي: {len(cases)}/{len(cases)} حالة صحيحة")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--playbook", default=str(DEFAULT))
    ap.add_argument("--check-paths", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    path = pathlib.Path(a.playbook)
    if not path.is_file():
        print(f"   ✘ منع: مرجع المصائد غير موجود: {path}")
        return 2

    base = roots()
    bad, rows = scan(path, a.check_paths, base)
    for b in bad:
        print(f"   ✘ {b}")
    if bad:
        print(f"   ✘ منع: {len(bad)} خللًا في {rows} وصفة")
        return 2
    if not rows:
        print("   ✘ منع: لا وصفات في المرجع")
        return 2
    extra = f" · وُجدت كل الأدوات في {len(base)} جذر" if a.check_paths else ""
    print(f"   ✔ {rows} وصفة مكتملة، وكلها تحمل أمر إثبات قابلًا للتشغيل{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
