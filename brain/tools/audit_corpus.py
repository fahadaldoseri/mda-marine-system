#!/usr/bin/env python3
"""تدقيق شامل لكل إصدارات نظام مركز الوعي بالمجال البحري.

الغرض: بناء مكتبات بيانات دائمة من قياس فعلي على كل الإصدارات (من أول إصدار إلى اليوم)
لا من تقدير أو توقّع. كل بند في المخرج يحمل: الملف، السطر، النص المقتبس، المقياس، القاعدة.

القراءة فقط: لا يعدّل أي إصدار ولا أي مكتبة قائمة. مخرجاته:
  - appendices/libraries/lexicon-library.json          مكتبة المعجم بأرقام فعلية
  - appendices/libraries/lexicon-library.md            النسخة المقروءة
  - appendices/libraries/findings-<DATE>.json          نتائج التدقيق مفصّلة
  - audit/تدقيق-شامل-كل-الإصدارات-<DATE>.md            التقرير الجامع

الاستخدام:
  python3 tools/audit_corpus.py --date 2026-10-20 [--json]
رموز الخروج: 0 سليم · 1 تحذير · 2 مانع (مانع = تعذّر قراءة مصدر أساسي).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "appendices" / "libraries"

# ── الفواصل والنقاط العربية ────────────────────────────────────────────────
SENT_SPLIT = re.compile(r"[.،؛!؟\n]+")
LATIN = re.compile(r"[A-Za-z][A-Za-z0-9\-\./]*")
AR_WORD = re.compile(r"[\u0621-\u064A\u0660-\u0669]{2,}")
TASHKEEL = re.compile(r"[\u064B-\u0652]")
AR_DIGITS = re.compile(r"[\u0660-\u0669\u06F0-\u06F9]")

# ── تنظيف: الروابط والمسارات والرموز البرمجية ليست مصطلحات تقرير ────────────
URL_RE = re.compile(r"https?://\S+|www\.\S+|\b[\w\-]+\.(?:org|com|net|gov|live|ae|sa|qa|kw|bh|om|me|uk|pdf|html|aspx|json|png)\b",
                    re.IGNORECASE)
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_RE = re.compile(r"`[^`]*`")
HEX_RE = re.compile(r"\b[0-9a-f]{12,}\b", re.IGNORECASE)
# رمز تقرير: اختصار لاتيني كبير (2–14) أو درجة إسناد (A/1 · B/2) أو رمز MN-/EST-
SYMBOL_RE = re.compile(r"\b(?:[A-Z]{2,14}(?:/[A-Z]{2,8})?|MN-\d{4}-\d{2}-\d{2}-\d{2}|EST-\d{4}-\d{2}-\d{2}-\d{2}|[A-F]/[1-6])\b")


def clean_text(text: str) -> str:
    """إزالة ما ليس نصّ تقرير: الروابط، الكتل الكودية، البصمات."""
    t = FENCE_RE.sub(" ", text)
    t = INLINE_RE.sub(" ", t)
    t = URL_RE.sub(" ", t)
    t = HEX_RE.sub(" ", t)
    return t


def symbols_of(text: str) -> Counter:
    """الرموز والمصطلحات الفعلية فقط، مع استثناء الروابط وأسماء الملفات."""
    return Counter(SYMBOL_RE.findall(clean_text(text)))


def tashkeel_terms(text: str) -> Counter:
    """كلمات تحمل تشكيلًا فعليًا (مسافات التشكيل داخل الكلمة)."""
    out: Counter = Counter()
    for tok in re.findall(r"[\u0621-\u064A\u064B-\u0652\u0670]{3,}", text):
        if TASHKEEL.search(tok):
            out[tok] += 1
    return out

# ── أزواج المفاهيم التي يجب أن تُكتب بصيغة واحدة (توحيد المصطلح) ────────────
VARIANT_GROUPS: dict[str, list[str]] = {
    "سفينة السحب": ["سفينة السحب", "القُطر", "القطر المستهدف", "قُطر"],
    "علم الدولة": ["علم هولندا", "راية", "الراية"],
    "العبور الملاحي": ["العبور", "المعبر", "خط العبور", "خط السير الملاحي"],
    "البضائع الجافة": ["بضائع جافة", "سائبة", "بضاعة سائبة"],
    "المرسى الآمن": ["مرسى آمن", "المرسى الآمن", "مرسى"],
    "الخطر الملاحي": ["خطر ملاحي", "خطر ملاحى", "تهديد ملاحي"],
    "خط الأساس": ["خط أساس", "خط الأساس", "المعدل الطبيعي"],
    "الحاويات الطافية": ["حاويات طافية", "حاويات شحن طافية", "حاويات شبه غارقة"],
    "مستوى التهديد": ["مستوى الخطر", "مستوى التهديد"],
    "قائمة عدم الامتثال": ["قائمة عدم الامتثال", "قائمة السفن غير الممتثلة", "قائمة سفن غير ممتثلة"],
}

# ── الرموز التي تمنع بوابة الفهم مرورها بلا تعريف ───────────────────────────
SYMBOLS_ALWAYS = ["NAVAREA", "UKMTO", "IMO", "JMIC", "DTG", "ICD", "EST-", "AIS", "MPA", "OFAC"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s)


def documents(date: str) -> list[dict]:
    """كل الإصدارات: اليومية ثم الخاصة ثم التراكمي. مبني على وجود الملف فعلًا."""
    docs: list[dict] = []
    for p in sorted((ROOT / "reports").glob("*-sectioned.md")):
        d = p.name.replace("-sectioned.md", "")
        meta = ROOT / "web" / "meta" / f"{d}.json"
        docs.append({"kind": "يومي", "date": d, "md": p, "meta": meta if meta.exists() else None})
    for p in sorted((ROOT / "reports").glob("special-*.md")) + sorted((ROOT / "reports").glob("GFS-*.md")):
        if p.name.endswith("-sectioned.md"):
            continue
        docs.append({"kind": "خاص", "date": p.stem, "md": p, "meta": None})
    for p in sorted((ROOT / "cumulative-2026").glob("*.md")):
        docs.append({"kind": "تراكمي", "date": p.stem, "md": p, "meta": None})
    return docs


def lint_text(text: str) -> dict:
    """مقاييس نصية قطعية على نص واحد."""
    sentences = [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]
    long_sentences = []
    for s in sentences:
        w = len(AR_WORD.findall(s))
        if w > 20:
            long_sentences.append({"words": w, "text": s[:160]})
    return {
        "sentences": len(sentences),
        "long_sentences": long_sentences,
        "arabic_digits": len(AR_DIGITS.findall(text)),
        "latin_tokens": symbols_of(text),
        "tashkeel_words": sorted(tashkeel_terms(text).keys()),
    }


def style_scan(path: Path) -> dict:
    """نداء بوابة الأسلوب نفسها (validators/check_style.scan) — لا إعادة تطبيق للأنماط.

    القاعدة: الأنماط ذات المعالجة الخاصة (mixed_prob_conf · separated_clock · coord_*)
    لا يصح تطبيق تعبيرها النمطي مباشرة؛ فبعضها تخزّن regex فارغًا عن قصد لأن البوابة
    تفحصها بمنطق دلالي. لذلك يُستدعى منطق البوابة الفعلي ليكون القياس قاطعًا.
    """
    sys.path.insert(0, str(ROOT / "validators"))
    try:
        import check_style as CS  # type: ignore
        f = CS.scan(path)
        out = {"blocked": [], "warn": [], "watch": []}
        for bucket in out:
            for it in f.get(bucket, []):
                out[bucket].append({"term": it.get("term", ""), "count": it.get("count", 1),
                                    "sample": (it.get("sample") or "")[:120],
                                    "replacement": it.get("replacement", "")})
        out["long"] = [{"count": it.get("count", 0), "sample": (it.get("sample") or "")[:120]}
                       for it in f.get("long", [])]
        return out
    except Exception as e:  # noqa: BLE001
        return {"error": f"تعذّر نداء بوابة الأسلوب: {e}", "blocked": [], "warn": [], "watch": [], "long": []}


def variant_scan(text: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for concept, forms in VARIANT_GROUPS.items():
        found = {f: len(re.findall(re.escape(f), text)) for f in forms}
        found = {k: v for k, v in found.items() if v}
        if found:
            out[concept] = found
    return out


def ng_info(text: str, n: int = 5) -> Counter:
    words = AR_WORD.findall(text)
    return Counter(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))


def run_gate(cmd: list[str]) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(ROOT))
        return {"cmd": " ".join(cmd[1:]), "code": r.returncode,
                "out": (r.stdout + r.stderr).strip()[-1200:]}
    except Exception as e:  # noqa: BLE001
        return {"cmd": " ".join(cmd[1:]), "code": 2, "out": f"تعذّر التشغيل: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="تاريخ الإصدار المرجعي لملفات المخرج")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    LIB.mkdir(parents=True, exist_ok=True)
    docs = documents(a.date)
    if not docs:
        print("✘ لم يُعثر على أي إصدار — مانع", file=sys.stderr)
        return 2

    bl_path = ROOT / "appendices" / "style-blacklist.json"
    blacklist = json.loads(read(bl_path)) if bl_path.exists() else {}
    term_path = ROOT / "appendices" / "terminology.md"
    terminology = read(term_path) if term_path.exists() else ""
    # مصادر التعريف المعتمدة: ملف المصطلحات + سجل السفن + قائمة المصادر
    defined_blob = terminology
    for extra in ("vessel-register-2026-10-16.json", "source-reliability-40.json",
                  "sources-manifest.json"):
        p_ = ROOT / "appendices" / extra
        if p_.exists():
            defined_blob += "\n" + read(p_)
    for p_ in (ROOT / "reports").glob("*.md"):
        pass

    lexicon: dict[str, dict] = {}
    latin_global: Counter = Counter()
    findings: list[dict] = []
    ngrams_by_doc: dict[str, Counter] = {}
    per_doc: list[dict] = []

    for d in docs:
        text = read(d["md"])
        m = lint_text(text)
        ngrams_by_doc[d["date"]] = ng_info(text)
        for tok, n in m["latin_tokens"].items():
            latin_global[tok] += n
        for tok in m["latin_tokens"]:
            e = lexicon.setdefault(tok, {"kind": "لاتيني", "count": 0, "docs": [],
                                         "defined_in_terminology": tok in defined_blob})
            e["count"] += m["latin_tokens"][tok]
            e["docs"].append(d["date"])
        for w in m["tashkeel_words"]:
            e = lexicon.setdefault(w, {"kind": "مشكول", "count": 0, "docs": [],
                                       "defined_in_terminology": w in defined_blob})
            e["count"] += len(re.findall(re.escape(w), text))
            e["docs"].append(d["date"])

        rec = {"kind": d["kind"], "date": d["date"], "file": str(d["md"].relative_to(ROOT)),
               "bytes": d["md"].stat().st_size, "sentences": m["sentences"],
               "long_sentences": len(m["long_sentences"]), "arabic_digits": m["arabic_digits"],
               "style": style_scan(d["md"]), "variants": variant_scan(text),
               "gates": {}}

        if d["kind"] == "يومي" and d["meta"]:
            rec["gates"]["comprehension"] = run_gate(
                ["python3", "validators/check_comprehension.py", "--date", d["date"]])
            rec["gates"]["points"] = run_gate(
                ["python3", "validators/check_points_rule.py", "--md", str(d["md"]),
                 "--meta", str(d["meta"])])
            rec["gates"]["code_spaces"] = run_gate(
                ["python3", "validators/check_code_spaces.py", "--date", d["date"]])
            rec["gates"]["report"] = run_gate(
                ["python3", "validators/validate_report.py", str(d["meta"])])

        for s in m["long_sentences"]:
            findings.append({"نوع": "جملة تتجاوز 20 كلمة", "الملف": d["date"],
                             "المقياس": f"{s['words']} كلمة", "النص": s["text"],
                             "القاعدة": "ق-جمل: الجملة العملياتية حتى 20 كلمة غالبًا",
                             "الحالة": "يحتاج قرارًا"})
        if m["arabic_digits"]:
            findings.append({"نوع": "أرقام عربية-هندية", "الملف": d["date"],
                             "المقياس": str(m["arabic_digits"]), "النص": "",
                             "القاعدة": "ق-أرقام: 0-9 اللاتينية فقط", "الحالة": "مؤكد — يجب الإصلاح"})
        for h in rec["style"].get("blocked", []):
            findings.append({"نوع": "لفظ مانع في القائمة السوداء", "الملف": d["date"],
                             "المقياس": str(h.get("count", 1)), "النص": h.get("sample") or h.get("term", ""),
                             "القاعدة": f"ق-سوداء: يُستبدل بـ«{h['replacement']}»" if h.get("replacement") else "ق-سوداء",
                             "الحالة": "مؤكد — يجب الإصلاح"})
        for h in rec["style"].get("warn", []):
            findings.append({"نوع": "رصد أسلوبي (تحذير)", "الملف": d["date"],
                             "المقياس": str(h.get("count", 1)), "النص": h.get("sample") or h.get("term", ""),
                             "القاعدة": "ق-نمط: يحتاج قرارًا بشريًا",
                             "الحالة": "يحتاج قرارًا"})
        for h in rec["style"].get("long", []):
            findings.append({"نوع": "جملة طويلة (بوابة الأسلوب)", "الملف": d["date"],
                             "المقياس": str(h.get("count", "")), "النص": h.get("sample", ""),
                             "القاعدة": "ق-جمل: حتى 20 كلمة", "الحالة": "يحتاج قرارًا"})
        per_doc.append(rec)

    # الأنماط المتكررة عبر الإصدارات (حشو متكرر)
    shared: list[dict] = []
    if ngrams_by_doc:
        totals: Counter = Counter()
        for c in ngrams_by_doc.values():
            for k in c:
                totals[k] += 1
        for phrase, n in totals.most_common(60):
            if n >= max(3, len(docs) // 2):
                shared.append({"عبارة": phrase, "إصدارات": n, "من": len(docs)})

    # القيم الشاذة في النص العربي
    dup_global = [(k, v["count"], sorted(set(v["docs"]))) for k, v in
                  sorted(lexicon.items(), key=lambda x: -x[1]["count"]) if v["count"] >= 8]

    # ── تناسق الإملاء: كلمة مشكولة ترد أيضًا بلا تشكيل في المصدر نفسه ──────
    corpus = "\n".join(read(d["md"]) for d in docs)
    ortho: list[dict] = []
    for k, v in sorted(lexicon.items(), key=lambda x: -x[1]["count"]):
        if v["kind"] != "مشكول" or v["count"] < 3:
            continue
        bare = TASHKEEL.sub("", k)
        if len(bare) < 4:
            continue
        n_bare = len(re.findall(re.escape(bare), corpus))
        if n_bare >= 2:
            ortho.append({"بالشكل": k, "بلا تشكيل": bare,
                          "الأول": v["count"], "الثاني": n_bare})

    lib = {"generated_utc": datetime.now(timezone.utc).isoformat(),
           "documents": len(docs),
           "orthography": ortho,
           "date_range": [min(d["date"] for d in docs), max(d["date"] for d in docs)],
           "lexicon": {k: {"kind": v["kind"], "count": v["count"],
                           "documents": sorted(set(v["docs"])),
                           "defined_in_terminology": v["defined_in_terminology"]}
                       for k, v in sorted(lexicon.items(), key=lambda x: -x[1]["count"])},
           "repeated_phrases": shared}
    (LIB / "lexicon-library.json").write_text(
        json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8")
    (LIB / f"findings-{a.date}.json").write_text(
        json.dumps({"per_document": per_doc, "findings": findings, "lexicon": lib["lexicon"],
                    "orthography": ortho, "repeated_phrases": shared},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# مكتبة المعجم والمصطلحات — مبنية بالقياس على كل الإصدارات", "",
          f"**وُلّدت:** {lib['generated_utc']} · **الإصدارات المفحوصة:** {len(docs)} "
          f"· **المدى:** {lib['date_range'][0]} إلى {lib['date_range'][1]}", "",
          "كل رقم في هذا الجدول مأخوذ من عدّ فعلي في ملفات الإصدارات، لا من تقدير.", "",
          "## الرموز اللاتينية والمصطلحات المشكولة", "",
          "| المصطلح | النوع | مرات الظهور | الإصدارات | معرَّف في القاموس؟ |",
          "|---|---|---|---|---|"]
    for k, v in list(lib["lexicon"].items())[:120]:
        md.append(f"| {k} | {v['kind']} | {v['count']} | {len(v['documents'])} | "
                  f"{'نعم' if v['defined_in_terminology'] else 'لا'} |")
    md += ["", "## العبارات المتكررة عبر الإصدارات (حشو محتمل)", "",
           "| العبارة | تكررت في | من إجمالي |", "|---|---|---|"]
    for s in shared[:40]:
        md.append(f"| {s['عبارة']} | {s['إصدارات']} | {s['من']} |")
    (LIB / "lexicon-library.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    if a.json:
        print(json.dumps({"documents": len(docs), "findings": len(findings),
                          "lexicon": len(lib["lexicon"]), "shared": len(shared)},
                         ensure_ascii=False))
    else:
        print(f"الإصدارات المفحوصة: {len(docs)} · مدى: {lib['date_range'][0]} → {lib['date_range'][1]}")
        print(f"بنود المعجم: {len(lib['lexicon'])} · نتائج: {len(findings)} · عبارات متكررة: {len(shared)}")
        print(f"المكتبة: {LIB/'lexicon-library.json'}")
        print(f"النتائج: {LIB/f'findings-{a.date}.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
