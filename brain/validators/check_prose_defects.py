#!/usr/bin/env python3
"""بوابة عيوب الصياغة العربية في تقرير واحد.

الفحوص الأربعة الأولى مانعة. وفحص المعجم تحذيري لأن قائمة الكلمات المتاحة
قد لا تغطي كل أسماء السفن والمصطلحات الجديدة.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARABIC_WORD = re.compile(r"[ء-يٱآأإؤئـ]+")
ARABIC_BASE = re.compile(r"[\u0621-\u063A\u0641-\u064A\u0671\u0679\u0688\u0691\u06A4\u06AF\u06CC]")
SPACE_BEFORE_PUNCT = re.compile(r"[ \t]+([،.:؛؟!])")
ARABIC_DIACRITICS = {chr(n) for n in range(0x064B, 0x0660)} | {"ـ"}

# قائمة بيضاء معلنة: ألفاظ عربية ذات تضاعف مشروع أو بادئة صرفية مشروعة.
# لا تُستعمل لإخفاء «معلنةة»؛ فالطاء المربوطة المكررة في آخر الكلمة خطأ.
DUPLICATE_LETTER_WHITELIST = set(json.loads((Path(__file__).resolve().parent.parent / "appendices" / "doubled-letters.json").read_text(encoding="utf-8"))["whitelist"])

COMMON_ARABIC_WORDS = {
    "هذه", "هذا", "تلك", "ذلك", "التي", "الذي", "الذين", "من", "في", "إلى", "على",
    "عن", "مع", "بين", "بعد", "قبل", "حتى", "كما", "وهو", "وهي", "هو", "هي", "هم",
    "أن", "إن", "لا", "لم", "لن", "قد", "ما", "لايزال", "مازال", "بأن", "بلا", "ولا",
    "و", "أو", "ثم", "لكن", "بل", "إذا", "كان", "كانت", "يكون", "تكون", "تم", "جرى",
    "قال", "قالت", "أفادت", "أعلنت", "أكدت", "يُعلن", "يعلن", "ورد", "ذكرت", "بحسب",
    "جهة", "جهةً", "المصدر", "مصدر", "رسمي", "رسمية", "البحرية", "بحري", "البحرية",
    "السفينة", "سفينة", "السفن", "رحلتها", "واصلت", "حادث", "حادثة", "النص", "الفقرة",
    "حركة", "المياه", "اليوم", "الفترة", "الجديدة", "الجديد", "المعتاد", "مستوى",
    "الله", "المشروع", "كلمة", "هذه", "وخلل",
}


def normalize_word(word: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFC", word) if ch not in ARABIC_DIACRITICS)


def strip_markup(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"!?(?:\[[^\]]*\])\([^)]*\)", " ", text)
    text = re.sub(r"[*_>#|]", " ", text)
    return text


def load_project_dictionary() -> set[str]:
    """يبني قاموسًا من الملفات الموجودة فعليًا، لا من قائمة مخترعة."""
    paths = [ROOT / "appendices" / "terminology.md", ROOT / "appendices" / "style-blacklist.json"]
    paths.extend(sorted((ROOT / "appendices" / "libraries").rglob("*")))
    known = set(COMMON_ARABIC_WORDS) | set(DUPLICATE_LETTER_WHITELIST)
    for path in paths:
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if path.suffix.lower() == ".json":
            try:
                raw = json.dumps(json.loads(raw), ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        for word in ARABIC_WORD.findall(raw):
            normalized = normalize_word(word)
            if len(normalized) >= 2:
                known.add(normalized)
    return known


def lexicon_duplicate_whitelist() -> set[str]:
    known = set(DUPLICATE_LETTER_WHITELIST)
    for word in load_project_dictionary():
        base = normalize_word(word)
        if any(base[i] == base[i + 1] for i in range(len(base) - 1)):
            known.add(base)
    return known


def line_excerpt(line: str, start: int, end: int) -> str:
    left = max(0, start - 35)
    right = min(len(line), end + 35)
    return line[left:right].strip()


def find_punctuation_defects(text: str) -> dict[str, list[dict]]:
    result = defaultdict(list)
    for line_no, line in enumerate(text.splitlines(), 1):
        for token, label in (("، .", "فاصلة ثم نقطة"), (".،", "نقطة ثم فاصلة"),
                             ("،،", "فاصلتان"), ("..", "نقطتان")):
            for match in re.finditer(re.escape(token), line):
                result["علامات ترقيم متجاورة"].append({
                    "line": line_no, "sample": line_excerpt(line, match.start(), match.end()),
                    "reason": label,
                })
        for match in SPACE_BEFORE_PUNCT.finditer(line):
            result["مسافة قبل علامة ترقيم"].append({
                "line": line_no, "sample": line_excerpt(line, match.start(), match.end()),
                "reason": f"مسافة قبل «{match.group(1)}»",
            })
    return result


def find_duplicate_letters(text: str) -> list[dict]:
    whitelist = lexicon_duplicate_whitelist()
    found = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for match in ARABIC_WORD.finditer(line):
            raw = match.group()
            word = normalize_word(raw)
            if len(word) < 2:
                continue
            positions = [i for i in range(len(word) - 1) if word[i] == word[i + 1]]
            # «يةان» تركيب صرفي غير سليم: يسبق اللاحقة الدالة على المثنى حرف التاء.
            if word.endswith("يةان"):
                found.append({"line": line_no, "word": raw, "reason": "لاحقة «يةان» غير سليمة صرفيًا"})
                continue
            if not positions or word in whitelist:
                continue
            for pos in positions:
                repeated = word[pos : pos + 2]
                # البادئات والتضعيفات الموثقة في القائمة البيضاء لا تُعد عيبًا.
                if pos == 0 and repeated in {"لل", "مم", "تت", "وو", "بب"}:
                    continue
                # المانع: تسلسلات لا تصحّ عربيًا («ةة» · «اا» · «وو» · «ىى» · «ئئ» · «ؤؤ»)
                # أو حرف تكرّر ثلاث مرات. أما تضاعف حرفين في كلمة عربية سليمة
                # («عدده» · «مخطط» · «وتحقق» · «وتغيير») فتنبيهي لا مانع — تصحيح ك-134.
                blocking = (repeated in {"ةة", "اا", "وو", "ىى", "ئئ", "ؤؤ"}
                            or word.count(word[pos]) >= 3)
                found.append({
                    "line": line_no, "word": raw, "blocking": blocking,
                    "reason": f"تكرار الحرف «{word[pos]}» داخل الكلمة"
                              + ("" if blocking else " — مشروع عربيًا، تنبيهي"),
                })
                break
    return found


def load_forbidden() -> list[dict]:
    path = ROOT / "appendices" / "forbidden-coinages.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("entries", []) if isinstance(data, dict) else []


def find_forbidden(text: str, report_date: str | None = None) -> list[dict]:
    found = []
    lines = text.splitlines()
    for entry in load_forbidden():
        term = str(entry.get("term", "")).strip()
        if not term:
            continue
        # تاريخ السريان: لفظ أُضيف اليوم لا يمنع نصًا منشورًا قبله (قرار صاحب القرار 2026-10-23).
        since = str(entry.get("since", "") or "")
        blocking = not (report_date and since and report_date < since)
        for line_no, line in enumerate(lines, 1):
            for match in re.finditer(re.escape(term), line):
                found.append({
                    "line": line_no, "term": term, "blocking": blocking,
                    "replacement": entry.get("replacement", "راجع قائمة المفردات المبسطة"),
                    "reason": entry.get("reason", "لفظ مصطنع ممنوع")
                              + ("" if blocking else f" — ساري من {since} (نص أقدم منه: تنبيهي)"),
                })
    return found


def normalize_sentence(sentence: str) -> str:
    sentence = strip_markup(sentence).lower()
    sentence = re.sub(r"[0-90-9]+", " ", sentence)
    sentence = re.sub(r"https?://\S+|[A-Za-z][A-Za-z0-9_./-]*", " ", sentence)
    # الأسماء المقتبسة وأسماء السفن تُحذف كي يبقى قالب الجملة.
    sentence = re.sub(r"[«“\"].*?[»”\"]", " ", sentence)
    sentence = re.sub(r"#[\w-]+", " ", sentence)
    sentence = re.sub(r"\b(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر)\b", " ", sentence)
    # ما بعد الشرطة في قالب التوجيه يختلف باختلاف الوجهة، لا باختلاف القالب.
    sentence = re.sub(r"\bنفّذوا\s*[—–-].*", "نفّذوا —", sentence)
    sentence = re.sub(r"\s+", " ", sentence).strip(" ،؛:")
    return sentence


def find_repeated_templates(text: str) -> list[dict]:
    candidates = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if "|" in line:
            continue  # أسطر الجداول: تكرار الخلية بنية جدول لا قالب جملة (معايرة 23 أكتوبر)
        clean_line = strip_markup(line).strip()
        if not clean_line or clean_line.startswith("#"):
            continue
        # bullets تمثل جملًا مستقلة حتى إن لم تنته بعلامة ترقيم.
        for sentence in re.split(r"(?<=[.!؟؛])\s+|\s*\n\s*", clean_line):
            normalized = normalize_sentence(sentence)
            has_marker = any(marker in normalized for marker in ("نفّذوا", "بلاغ من", "لا بلاغ جديد"))
            has_sentence_end = sentence.rstrip().endswith((".", "؟", "!", "؛"))
            if len(normalized) >= 4 and (has_marker or has_sentence_end):
                candidates.append((normalized, line_no, sentence.strip()))
    groups: dict[str, list[dict]] = defaultdict(list)
    for normalized, line_no, sample in candidates:
        groups[normalized].append({"line": line_no, "sample": sample[:120]})
    return [
        {"template": template, "count": len(items), "occurrences": items}
        for template, items in sorted(groups.items())
        if len(items) > 2
    ]


def find_unknown_words(text: str) -> list[str]:
    known = load_project_dictionary()
    words = Counter()
    for raw in ARABIC_WORD.findall(strip_markup(text)):
        word = normalize_word(raw)
        if len(word) < 3 or word in known:
            continue
        # الكلمات ذات الأعلام والأرقام والمصطلحات الأجنبية لا تدخل هذا التحذير.
        if any(ch.isdigit() for ch in raw):
            continue
        words[word] += 1
    return [word for word, _ in words.most_common()]


def print_findings(title: str, findings: list[dict]) -> None:
    if not findings:
        return
    print(f"{title}: {len(findings)}")
    for item in findings[:20]:
        where = f"السطر {item['line']}"
        detail = item.get("sample") or item.get("word") or item.get("term") or item.get("reason", "")
        print(f"  - {where}: {detail} — {item.get('reason', '')}")
    if len(findings) > 20:
        print(f"  - ... و{len(findings) - 20} موضعًا آخر")


def main() -> int:
    parser = argparse.ArgumentParser(description="بوابة عيوب الصياغة العربية")
    parser.add_argument("path", nargs="?", help="مسار التقرير")
    parser.add_argument("--md", dest="md", help="مسار التقرير بصيغة Markdown")
    args = parser.parse_args()
    chosen = args.md or args.path
    if not chosen:
        print("الاستخدام: check_prose_defects.py --md <ملف التقرير>")
        return 2
    path = Path(chosen)
    if not path.exists():
        print(f"الملف غير موجود: {path}")
        return 2
    text = path.read_text(encoding="utf-8")
    punctuation = find_punctuation_defects(text)
    duplicates = find_duplicate_letters(text)
    _m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    forbidden = find_forbidden(text, _m.group(1) if _m else None)
    templates = find_repeated_templates(text)
    unknown = find_unknown_words(text)
    counts = {
        "علامات ترقيم متجاورة": len(punctuation.get("علامات ترقيم متجاورة", [])),
        "مسافة قبل علامة ترقيم": len(punctuation.get("مسافة قبل علامة ترقيم", [])),
        "حرف عربي مضاعف": sum(1 for d in duplicates if d.get("blocking")),
        "ألفاظ مصطنعة ممنوعة": sum(1 for f in forbidden if f.get("blocking")),
        "ألفاظ أُضيفت اليوم (تحذير)": sum(1 for f in forbidden if not f.get("blocking")),
        "قالب جملة متكرر أكثر من مرتين": len([x for x in templates if x["count"] > 2]),
        "كلمات خارج المعجم (تحذير)": len(unknown),
    }
    print("=== بوابة عيوب الصياغة ===")
    print(f"الملف: {path}")
    print("| النوع | العدد | الحكم |")
    print("|---|---:|---|")
    for name, count in counts.items():
        الحكم = "تحذير" if "(تحذير)" in name else ("مانع" if count else "سليم")
        print(f"| {name} | {count} | {الحكم} |")
    print_findings("علامات الترقيم المتجاورة", punctuation.get("علامات ترقيم متجاورة", []))
    print_findings("المسافات قبل الترقيم", punctuation.get("مسافة قبل علامة ترقيم", []))
    print_findings("الحروف العربية المضاعفة (مانع)", [d for d in duplicates if d.get("blocking")])
    print_findings("حروف مضاعفة مشروعة (تنبيهي)", [d for d in duplicates if not d.get("blocking")])
    print_findings("الألفاظ المصطنعة (مانع)", [f for f in forbidden if f.get("blocking")])
    print_findings("ألفاظ أُضيفت اليوم (تنبيهي)", [f for f in forbidden if not f.get("blocking")])
    if templates:
        print(f"قوالب الجمل المتكررة: {len(templates)}")
        for item in templates[:20]:
            print(f"  - {item['count']}× «{item['template']}»؛ أول موضع السطر {item['occurrences'][0]['line']}")
    if unknown:
        print(f"تحذير المعجم: {len(unknown)} كلمة مشتبهة — " + "، ".join(unknown[:40]))
    blocking = sum(v for k, v in counts.items() if "(تحذير)" not in k)
    if blocking:
        print("النتيجة: مانع — لا يُسلَّم التقرير قبل المعالجة (لا تعديل آلي).")
        return 2
    if unknown:
        print("النتيجة: تحذير — لا توجد مخالفة مانعة، راجع الكلمات المشتبهة.")
        return 1
    print("النتيجة: نجاح — لا عيوب مانعة ولا كلمات مشتبهة.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
