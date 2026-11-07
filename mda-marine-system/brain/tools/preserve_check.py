#!/usr/bin/env python3
"""فحص حفظ الحقائق والبنية بين نصين (قبل التحرير وبعده). يمنع إذا تغيّر ما لا يجوز تغييره.

الاستعمال:  python3 preserve_check.py قبل.md بعد.md [--removable ملف.json]
            الملف الاختياري: {"مصطلح لاتيني": "سبب مكتوب"} — حذف هذه الألفاظ مسموح (قرار مالك موثَّق)؛ وما سواها يُمنع حذفه.
            الافتراضي: appendices/removable-latin.json إن وُجد.
الخروج:     0 = محفوظ · 2 = فرق (يُطبع).
يفحص: الأرقام، الرموز MN-/EST-، الأسماء اللاتينية، الروابط، ألفاظ الإسناد واليقين،
      عدد العناوين ومستوياتها، شكل كل جدول (عدد الصفوف والأعمدة).
القياس بتعبيرات نمطية: يكشف التغيّر لا صحة المعنى.
"""
import argparse
import json
import os
import re
import signal
import sys
from collections import Counter

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# ألفاظ تحمل درجة اليقين أو الجهة المصدرة: يجب ألا تُحذف ولا تُضاف (مع التسامح في «ال» وحروف العطف)
HEDGES = {
    "أعلن": r"أعلن\w*", "أكد": r"أكد\w*", "أفاد": r"أفاد\w*", "قال": r"قال\w*", "نقل": r"نقل\w*|نُقل\w*",
    "يرجح": r"يرجح\w*|مرجح\w*", "غير مرجح": r"غير\s+(?:ال)?مرجح\w*", "ممكن": r"ممكن\w*",
    "غير مؤكد": r"غير\s+(?:ال)?مؤكد\w*", "مؤكد": r"(?<!غير )(?<!غير ال)مؤكد\w*",
    "رواية": r"رواية|روايات", "ادعاء": r"ادعاء\w*", "تقدير": r"تقدير\w*", "بلاغ": r"بلاغ\w*",
    "نشرة": r"نشرة|نشرات", "تحذير": r"تحذير\w*", "هجوم": r"هجوم\w*|هجومين|هجومان",
}
TASHKEEL = re.compile(r"[ً-ْٰ]")


def norm(t):
    return TASHKEEL.sub("", t).replace("ـ", "")


def facts(t):
    t = norm(t)
    urls = Counter(re.findall(r"https?://[^\s)>\]]+", t))
    t_nourl = re.sub(r"https?://[^\s)>\]]+", " ", t)
    nums = Counter(re.findall(r"\d+(?:[.,:/-]\d+)*", t_nourl))
    # علامات الترقيم الملاصقة (نقطة الجملة وغيرها) ليست من الكلمة: «0400Z.» هي «0400Z»
    latin = Counter(w.rstrip("./-'’").upper() for w in re.findall(r"[A-Za-z][A-Za-z0-9'’./-]*", t_nourl))
    codes = Counter(re.findall(r"(?:MN|EST)-\d{4}-\d{2}-\d{2}-\d{2}", t_nourl))
    hedges = Counter()
    for k, pat in HEDGES.items():
        c = len(re.findall(rf"(?<![؀-ۿ])[وفبلك]?(?:ال)?(?:{pat})", t_nourl))
        if c:
            hedges[k] = c
    return nums, latin, codes, hedges, urls


def structure(t):
    heads = [len(m.group(1)) for m in re.finditer(r"^(#{1,6})\s", t, re.M)]
    tables, cur = [], []
    for line in t.splitlines():
        if line.strip().startswith("|"):
            cur.append(len([c for c in line.strip().strip("|").split("|")]))
        elif cur:
            tables.append((len(cur), tuple(cur)))
            cur = []
    if cur:
        tables.append((len(cur), tuple(cur)))
    return heads, tables


def diff(a, b, title):
    out = []
    for k in sorted(set(a) | set(b)):
        if a.get(k, 0) != b.get(k, 0):
            out.append(f"  {title}: «{k}» قبل={a.get(k, 0)} بعد={b.get(k, 0)}")
    return out


def heading_texts(t):
    return [norm(m.group(2)).strip() for m in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", t, re.M)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--removable")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    rem_path = a.removable or os.path.join(here, "..", "appendices", "removable-latin.json")
    removable = {}
    if os.path.isfile(rem_path):
        removable = {k.upper() for k in json.load(open(rem_path, encoding="utf-8"))}
    before = open(a.before, encoding="utf-8").read()
    after = open(a.after, encoding="utf-8").read()
    fb, fa = facts(before), facts(after)
    problems = []
    problems += diff(fb[0], fa[0], "رقم")
    lat_b, lat_a = Counter(fb[1]), Counter(fa[1])
    for w in removable:  # المسموح حذفه: يُسقَط من المقارنة إن نقص فقط (الإضافة تبقى ممنوعة)
        if lat_a.get(w, 0) <= lat_b.get(w, 0):
            lat_b.pop(w, None)
            lat_a.pop(w, None)
    problems += diff(lat_b, lat_a, "لاتيني")
    problems += diff(fb[2], fa[2], "رمز")
    problems += diff(fb[4], fa[4], "رابط")
    for k in sorted(set(fb[3]) | set(fa[3])):
        if (k in fb[3]) != (k in fa[3]):
            problems.append(f"  إسناد/يقين: «{k}» قبل={fb[3].get(k, 0)} بعد={fa[3].get(k, 0)}")
    hb, tb = structure(before)
    ha, ta = structure(after)
    if hb != ha:
        problems.append(f"  عناوين: عددها/مستوياتها تغيّرت ({len(hb)} ← {len(ha)})")
    if heading_texts(before) != heading_texts(after):
        problems.append("  عنوان: نص عنوان تغيّر (العناوين عقد مع المولّد والمدققات)")
    if tb != ta:
        problems.append(f"  جداول: شكلها تغيّر (صفوف/أعمدة): قبل={[t[0] for t in tb]} بعد={[t[0] for t in ta]}")
    if problems:
        print("✘ تغيّرت حقائق أو بنية بين النصين:")
        print("\n".join(problems))
        return 2
    print("✔ الأرقام والرموز والأسماء والروابط وألفاظ الإسناد وبنية العناوين والجداول محفوظة")
    return 0


if __name__ == "__main__":
    sys.exit(main())
