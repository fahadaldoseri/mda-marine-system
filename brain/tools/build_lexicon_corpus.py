#!/usr/bin/env python3
"""مولّد معجم المفردات العربية من المتن المعتمد.

المشكلة التي يحلّها: بوابة `check_prose_defects.py` كانت تبني قاموسها من ملفين
فقط (terminology.md و style-blacklist.json)، فأبلغت عن 147 كلمة عربية سليمة
(تطبيق، المدني، تفتيش …) بوصفها «خارج المعجم»، فصارت التحذيرات ضجيجًا يخفي
العيوب الحقيقية.

القاعدة: لا توسيع بالتقدير. المعجم يُشتق حصريًا من مصادر معتمدة داخل المشروع:
  1) متون الإصدارات المعتمدة reports/*-sectioned.md
  2) كتل الأقسام المعتمدة sections/*.md
  3) قوائم المصطلحات المعتمدة appendices/terminology.md و style-blacklist.json
     و simplified-vocabulary.json و lexicon-exceptions.json
ثم تُطبَّع الكلمات (إزالة التشكيل والتطويل) وتُسقَط كلمات الوقف، ويُكتب الناتج
في appendices/lexicon-corpus.json مع بصمة ومصادر وأعداد، ليقارنها المدقق.

الاستعمال:
  python3 tools/build_lexicon_corpus.py --apply     # توليد/تحديث المعجم
  python3 tools/build_lexicon_corpus.py --check      # التحقق من مطابقة المعجم للمصادر
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "appendices" / "lexicon-corpus.json"
VERSION = 1

ARABIC_DIACRITICS = set(
    "\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652\u0653\u0654\u0655\u0670\u0640"
)
ARABIC_WORD = re.compile(r"[\u0621-\u064A]{3,}")
# كلمات وظيفية لا تدخل المعجم (وجودها لا يعني اعتمادًا اصطلاحيًا)
STOPWORDS = {
    "هذه", "هذا", "هؤلاء", "تلك", "ذلك", "التي", "الذي", "الذين", "من", "في", "إلى", "على",
    "عن", "أن", "إن", "كان", "كانت", "يكون", "تكون", "لا", "لم", "لن", "قد", "ما", "هو",
    "هي", "هم", "ثم", "أو", "أي", "كل", "بعض", "بين", "عند", "حتى", "إذا", "كما", "لكن",
    "بعد", "قبل", "خلال", "حول", "دون", "مع", "نحو", "وفق", "ضمن", "عبر", "بها", "به",
    "لها", "له", "فيه", "فيها", "منها", "منه", "عليها", "عليه", "إليها", "إليه", "أيضا",
    "أيضًا", "جدا", "جدًا", "نفس", "ذات", "غير", "سوى", "إلا", "أما", "أم", "بل", "أنها",
    "أنه", "إنها", "إنه", "وهو", "وهي", "وهم", "وقد", "وكان", "وكانت", "ولا", "ولم",
}

APPROVED_SOURCES = [
    ROOT / "appendices" / "terminology.md",
    ROOT / "appendices" / "style-blacklist.json",
    ROOT / "appendices" / "simplified-vocabulary.json",
    ROOT / "appendices" / "lexicon-exceptions.json",
]


def normalize(word: str) -> str:
    word = unicodedata.normalize("NFC", word)
    return "".join(ch for ch in word if ch not in ARABIC_DIACRITICS)


def collect_text(paths: list[pathlib.Path]) -> str:
    chunks: list[str] = []
    for p in paths:
        if not p.exists():
            continue
        raw = p.read_text(encoding="utf-8", errors="ignore")
        if p.suffix.lower() == ".json":
            try:
                raw = json.dumps(json.loads(raw), ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        chunks.append(raw)
    return "\n".join(chunks)


def source_paths() -> list[pathlib.Path]:
    paths = list(APPROVED_SOURCES)
    paths += sorted((ROOT / "reports").glob("*-sectioned.md"))
    paths += sorted((ROOT / "sections").glob("*.md"))
    return [p for p in paths if p.exists()]


def build() -> dict:
    paths = source_paths()
    text = collect_text(paths)
    words: set[str] = set()
    for raw in ARABIC_WORD.findall(text):
        w = normalize(raw)
        if len(w) < 3 or w in STOPWORDS:
            continue
        words.add(w)
    payload = {
        "version": VERSION,
        "policy": "معجم مشتق من المتن المعتمد فقط؛ لا توسيع بالتقدير.",
        "sources": [str(p.relative_to(ROOT)) for p in paths],
        "count": len(words),
        "fingerprint": hashlib.sha256("\n".join(sorted(words)).encode("utf-8")).hexdigest()[:16],
        "words": sorted(words),
    }
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="مولّد معجم المفردات من المتن المعتمد")
    ap.add_argument("--apply", action="store_true", help="توليد المعجم وكتابته")
    ap.add_argument("--check", action="store_true", help="التحقق من مطابقة المعجم للمصادر")
    args = ap.parse_args()

    fresh = build()
    if args.apply:
        OUT.write_text(json.dumps(fresh, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"   كُتب {OUT.relative_to(ROOT)} · كلمات={fresh['count']} · بصمة={fresh['fingerprint']}")
        return 0

    if args.check:
        if not OUT.exists():
            print("   ✘ المعجم غير موجود — شغّل --apply")
            return 2
        old = json.loads(OUT.read_text(encoding="utf-8"))
        if old.get("fingerprint") != fresh["fingerprint"]:
            print(
                f"   ✘ المعجم غير مطابق للمصادر: المخزّن={old.get('fingerprint')} · "
                f"المحسوب={fresh['fingerprint']} · كلمات المخزّن={old.get('count')} · المحسوب={fresh['count']}"
            )
            return 1
        print(f"   ✓ المعجم مطابق للمصادر · كلمات={fresh['count']} · بصمة={fresh['fingerprint']}")
        return 0

    print(json.dumps({"count": fresh["count"], "fingerprint": fresh["fingerprint"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())