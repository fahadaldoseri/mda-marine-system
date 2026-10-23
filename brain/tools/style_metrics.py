#!/usr/bin/env python3
"""مقياس أسلوب التقرير العربي (للقراءة فقط — لا يعدّل شيئًا).

الاستعمال:  python3 style_metrics.py reports/2026-10-23-sectioned.md [ملفات أخرى...] [--json out.json]
            python3 style_metrics.py --strict reports/2026-10-23-sectioned.md
الخروج:     0 دائمًا، وفي وضع --strict يخرج 2 إذا وُجد لفظ ممنوع أو زادت الجمل المبدوءة بـ«و» عن 25%.
القياس تقريبي (تعبيرات نمطية) ويُراد به الاتجاه، لا الحكم النهائي.
"""
import re
import signal
import sys

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# كلمات جذرها واو أصلية ولا تُعدّ «واو العطف»
ROOT_WAW = {
    "وكالة", "وكالات", "وكيل", "وقت", "وقائع", "واقعة", "وقع", "وقعت", "وقوع", "وصل", "وصلت", "وصول", "وصف",
    "وصفت", "وفاة", "وفيات", "وسائل", "وسيلة", "وسط", "وضع", "وجود", "وجد", "وجدت", "وحدة", "وحدات", "وثيقة",
    "وثائق", "وفق", "وفد", "وقف", "وزارة", "وزير", "واشنطن", "وارد", "واحد", "واحدة", "ولاية", "وطني", "وتيرة",
    "وجهة", "وجهات", "ورد", "وردت", "وزارات", "وزراء", "وقتها", "وضعت", "وضعه", "وفرة", "وعد", "وعود",
}

# ألفاظ وتراكيب يُراد التخلص منها (نص → سبب قصير)
BANNED = [
    ("عبورات", "جمع مصطنع؛ اكتب «عبرت N سفن»"),
    ("عبورتين", "مثنى مصطنع؛ اكتب «عبرت سفينتان»"),
    ("عبورتان", "مثنى مصطنع؛ اكتب «عبرت سفينتان»"),
    ("الواقفة بعيدًا عن المراسي", "ترجمة حرفية؛ «المتوقفة خارج المراسي»"),
    ("الواقفة بعيدا عن المراسي", "ترجمة حرفية"),
    ("أحادي", "ترجمة حرفية؛ «من طرف واحد»"),
    ("أحادية", "ترجمة حرفية؛ «من طرف واحد»"),
    ("ينقض", "ثقيل؛ «يخالف» أو «ينفي»"),
    ("يسند التصنيف", "ثقيل؛ «يقوم على»"),
    ("تُوسم", "مصطنع؛ «يصفها الإعلام بأنها»"),
    ("نافذة", "ممنوع بمعنى الفترة"),
    ("نافذتي", "ممنوع بمعنى الفترة"),
    ("الإسناد:", "عنوان غير مفهوم؛ «المصدر:»"),
    ("غير معلوم", "لفظ غير موحد؛ «غير محدد المصدر»"),
    ("غير معروف", "لفظ غير موحد؛ «غير محدد المصدر»"),
    ("دخل الفترة", "نقل حرفي؛ «صدر خلال الفترة»"),
    ("المراجعة الداخلية", "عبارة عمل داخلي"),
    ("الخط اليومي", "عبارة عمل داخلي"),
    ("سجل الدروس", "عبارة عمل داخلي"),
    ("ACH", "اختصار أجنبي غير مفسّر"),
]
DANGLING = re.compile(r"[،,]\s*\.")
SPACE_BEFORE = re.compile(r"\s+[،؛:.!؟]")
DOUBLE_LETTERS = re.compile(r"(?:ةة|ىى|ئئ|ؤؤ)")


def prose_lines(text):
    """أسطر المتن فقط: بلا عناوين ولا جداول ولا اقتباسات ولا أكواد."""
    in_code = False
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s or s.startswith(("#", "|", ">", "---")):
            continue
        yield n, s


def clean(s):
    s = re.sub(r"\*\*|__|`", "", s)
    s = re.sub(r"^[-*•]\s*", "", s)
    s = re.sub(r"^\d+[.)]\s*", "", s)
    return s.strip()


def sentences(s):
    parts = re.split(r"(?<=[.؟!])\s+", clean(s))
    return [p.strip() for p in parts if len(p.split()) >= 3]


def starts_with_waw(sent):
    first = sent.split()[0]
    first = first.strip("«»\"'()[]")
    return first.startswith("و") and len(first) > 2 and first not in ROOT_WAW


def analyse(path):
    text = open(path, encoding="utf-8").read()
    sents, waw, long_, runs = [], 0, [], 0
    for n, line in prose_lines(text):
        run = 0
        for sent in sentences(line):
            sents.append((n, sent))
            if starts_with_waw(sent):
                waw += 1
                run += 1
                if run == 3:
                    runs += 1
            else:
                run = 0
            if len(sent.split()) > 25:
                long_.append((n, len(sent.split())))
    banned = {}
    for term, why in BANNED:
        hits = [m.start() for m in re.finditer(re.escape(term), text)]
        if hits:
            banned[term] = (len(hits), why)
    heads_en = [(n, l) for n, l in enumerate(text.splitlines(), 1)
                if l.startswith("#") and re.search(r"\b[A-Z]{3,}\b", l)]
    return {
        "file": path,
        "sentences": len(sents),
        "waw_pct": round(100 * waw / len(sents), 1) if sents else 0.0,
        "waw_runs3": runs,
        "long": len(long_),
        "banned": banned,
        "dangling": len(DANGLING.findall(text)),
        "space_before": len(SPACE_BEFORE.findall(text)),
        "double_letters": len(DOUBLE_LETTERS.findall(text)),
        "heads_en": len(heads_en),
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    jpath = None
    if "--json" in sys.argv:
        jpath = sys.argv[sys.argv.index("--json") + 1]
        args = [a for a in args if a != jpath]
    if not args:
        print(__doc__)
        return 0
    worst = 0
    print("| الملف | جمل | مبدوءة بـ«و» % | تتابع 3 «و» | جمل >25 كلمة | ألفاظ ممنوعة | بقايا ترقيم | حروف مضاعفة | عناوين بإنجليزية |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    details = []
    for p in args:
        r = analyse(p)
        nb = sum(c for c, _ in r["banned"].values())
        print(f"| {p.split('/')[-1]} | {r['sentences']} | {r['waw_pct']} | {r['waw_runs3']} | {r['long']} | {nb} | "
              f"{r['dangling'] + r['space_before']} | {r['double_letters']} | {r['heads_en']} |")
        details.append(r)
        if nb or r["waw_pct"] > 25:
            worst = 2
    for r in details:
        if r["banned"]:
            print(f"\nالألفاظ الممنوعة في {r['file'].split('/')[-1]}:")
            for term, (c, why) in sorted(r["banned"].items(), key=lambda x: -x[1][0]):
                print(f"  - «{term}» × {c} — {why}")
    if jpath:
        import json
        slim = [{**r, "banned": {k: v[0] for k, v in r["banned"].items()}} for r in details]
        json.dump(slim, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nالهدف: «و» ≤ 15% · ألفاظ ممنوعة = 0 · بقايا ترقيم = 0 · حروف مضاعفة = 0 · عناوين بإنجليزية = 0")
    return worst if strict else 0


if __name__ == "__main__":
    sys.exit(main())
