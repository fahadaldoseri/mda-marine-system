#!/usr/bin/env python3
"""فاحص إملاء وتركيب أساسي للتقرير العربي (للقراءة فقط).

الاستعمال:  python3 check_orthography.py ملف.md [ملفات...]        # يطبع الأخطاء
            python3 check_orthography.py --strict ملف.md           # يخرج 2 إذا وُجد خطأ
            python3 check_orthography.py --json out.json ملف.md    # يكتب النتائج
يفحص المتن والجداول (ويتجاوز الروابط والأكواد). القياس بتعبيرات نمطية: يكشف الأخطاء الشائعة لا كلها.
"""
import json
import re
import signal
import sys
from pathlib import Path

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

AR = r"ء-ي"
CHECKS = [
    ("حرف مكرر ثلاث مرات فأكثر", re.compile(rf"([{AR}])\1{{2,}}")),
    ("حرفان مكرران لا يصحان", re.compile(r"(?:ةة|ىى|ئئ|ؤؤ|أأ|إإ|ءء)")),
    ("تاء مربوطة وسط الكلمة مع لاحقة (مثل استشاريةان)", re.compile(rf"(?<![{AR}])[{AR}]+ة(?:ان|ين|ون)(?![{AR}])")),
    ("تنوين فتح على تاء مربوطة", re.compile(r"ةًا|ةا(?![ء-ي])")),
    ("تنوين فتح بعد حرف جر أو «بلا/دون/غير» (يجب الجر)", re.compile(
        rf"(?<![{AR}])[وف]?(?:بلا|دون|غير|عن|في|من|على|إلى|مع|عند|بعد|حتى)\s+[{AR}]+ًا(?![{AR}])")),
    ("كلمة مكررة متتالية", re.compile(rf"(?<![{AR}\d])([{AR}]{{2,}})\s+\1(?![{AR}\d])")),
    # لا تُعدّ اللاحقة ".." من علامة الحذف "..." خطأ؛ نطابق نقطتين مستقلتين فقط.
    ("فاصلة أو نقطة معلّقة (بقايا قالب)", re.compile(r"[،,]\s*\.|[،,]\s*[،,]|(?<!\.)\.\s*\.(?!\.)")),
    ("مسافة قبل علامة ترقيم", re.compile(r"[{ar}\d)]\s+[،؛.؟!](?!\d)".format(ar=AR))),
    ("علامة ترقيم بلا مسافة بعدها", re.compile(rf"[،؛](?=[{AR}])")),
    ("أرقام هندية-عربية (ممنوعة؛ الأرقام لاتينية)", re.compile(r"[\u0660-\u0669\u06F0-\u06F9]")),
    ("مسافتان متتاليتان بين كلمتين", re.compile(rf"(?<=[{AR}])  +(?=[{AR}])")),
]
# أخطاء إملائية شائعة (خطأ → الصواب)
SLIPS = {
    "الى": "إلى", "اكتوبر": "أكتوبر", "اذا": "إذا", "هاذا": "هذا", "لاكن": "لكن", "الذى": "الذي", "التى": "التي",
    "مسئول": "مسؤول", "مسئولية": "مسؤولية", "اسرائيل": "إسرائيل", "امريكا": "أمريكا", "اوروبا": "أوروبا",
}
SLIP_RE = re.compile(rf"(?<![{AR}])(" + "|".join(map(re.escape, SLIPS)) + rf")(?![{AR}])")


def body_lines(text):
    in_code = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line.strip():
            continue
        s = re.sub(r"\]\([^)]*\)", "]", line)       # روابط
        s = re.sub(r"https?://\S+", " ", s)
        s = re.sub(r"`[^`]*`", " ", s)
        s = re.sub(r"\*\*|__", "", s)
        yield n, s


def analyse(path):
    text = open(path, encoding="utf-8").read()
    found = {}
    for n, s in body_lines(text):
        for name, rx in CHECKS:
            for m in rx.finditer(s):
                found.setdefault(name, []).append((n, m.group(0).strip()[:40]))
        for m in SLIP_RE.finditer(s):
            found.setdefault("إملاء شائع خاطئ", []).append((n, f"{m.group(1)} ← {SLIPS[m.group(1)]}"))
    return found


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    jpath = None
    if "--json" in sys.argv:
        i = sys.argv.index("--json")
        jpath = sys.argv[i + 1]
        args = [a for a in args if a != jpath]
    if not args:
        print(__doc__)
        return 0
    total, out = 0, {}
    for p in args:
        f = analyse(p)
        n = sum(len(v) for v in f.values())
        total += n
        out[p] = {k: v for k, v in f.items()}
        print(f"\n{p.split('/')[-1]}: {n} خطأ")
        for name, hits in f.items():
            print(f"  - {name}: {len(hits)}")
            for ln, frag in hits[:5]:
                print(f"      السطر {ln}: «{frag}»")
    if jpath:
        json.dump({"total": total, "files": out}, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nالمجموع: {total}  (الهدف: 0)")
    return 2 if (strict and total) else 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
