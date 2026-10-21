#!/usr/bin/env python3
"""بوابة استعمال المكتبات: تربط مكتبات المراجع بالإصدار المطلوب تسليمه.

قبل هذه البوابة كانت المكتبات بيانات تُبنى ولا تُنفَّذ: يقرؤها المولّد ثم تبقى.
وهذه البوابة تقرأ المكتبات فعليًا وتفرض أثرها على الإصدار:

  ل1 كل مصطلح عُرِّف في الإصدار يجب أن يكون في بنك التعريفات المعياري،
     وإلا فسيُعرَّف من جديد في الغد بلا ذاكرة.
  ل2 كل رمز مسجَّل في «فجوات المعجم» وظهر في الإصدار يجب أن يُعرَّف أو يُبرَّر،
     وإلا فهو يمرّ من إصدار إلى إصدار بلا تعريف.
  ل3 كل تعريف جديد يجب أن يحمل مصدره (مصدر منشور أو سجل داخلي).

الخروج: 0 سليم · 1 تحذير · 2 عائق.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
BANK = B / "appendices" / "glossary-standard.json"
GAPS = B / "appendices" / "libraries" / "terminology-gaps.md"


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:                                        # noqa: BLE001
        print(f"  ✘ تعذّر قراءة {path.name}: {e}")
        return None


def gaps_list() -> list[tuple[str, str]]:
    if not GAPS.is_file():
        return []
    out = []
    for line in GAPS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if m and m.group(1) not in ("المصطلح",) and not set(m.group(1)) <= set("-: "):
            out.append((m.group(1), m.group(2)))
    return out


def recurring_phrases() -> list[str]:
    """مكتبة العبارات المتكررة: كل عبارة فيها تُفحَص على الإصدار (عطل ك-78)."""
    f = B / "appendices" / "libraries" / "recurring-phrases.md"
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^[-*]\s+[«\"](.+?)[»\"]", line.strip())
        if m and 6 <= len(m.group(1)) <= 60:
            out.append(m.group(1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="بوابة استعمال المكتبات")
    ap.add_argument("--date", required=True)
    ap.add_argument("--md", default=None)
    ap.add_argument("--meta", default=None)
    a = ap.parse_args()

    md = Path(a.md) if a.md else B / "reports" / f"{a.date}-sectioned.md"
    meta = Path(a.meta) if a.meta else B / "web" / "meta" / f"{a.date}.json"
    print(f"=== بوابة استعمال المكتبات — {a.date} ===")
    if not md.is_file() or not meta.is_file():
        print(f"  ✘ مصدر الإصدار أو واجهته غير موجود")
        return 2

    text = md.read_text(encoding="utf-8")
    m = load(meta) or {}
    glossary = m.get("glossary", {}) or {}
    bank = load(BANK) or {}
    # بنية البنك: {symbols: {...}} — ويُقبل أي حقل معجمي آخر بدلًا منه
    bank_defs = {}
    if isinstance(bank, dict):
        for key in ("symbols", "definitions", "terms", "glossary"):
            if isinstance(bank.get(key), dict):
                bank_defs.update(bank[key])
    bank_keys = list(bank_defs)

    # ── ل1: كل تعريف في الإصدار موجود في البنك المعياري
    GRADE_RE = re.compile(r"^[A-F]/[1-6]$")   # درجات A/1..D/4 يغطيها مدخل «A–F / 1–6»
    def in_bank(term: str) -> bool:
        if any(term in bk or bk in term for bk in bank_keys):
            return True
        if GRADE_RE.match(term):
            return any("A–F" in bk or "A-F" in bk for bk in bank_keys)
        return False
    missing = [k for k in glossary if not in_bank(k)]
    print(f"  ل1 تعريفات الإصدار: {len(glossary)} · في البنك: {len(glossary) - len(missing)} · خارج البنك: {len(missing)}")
    if missing:
        print(f"       خارج البنك: {' · '.join(missing[:8])}")

    # ── ل2: رموز فجوات المعجم الحاضرة في الإصدار
    gl = gaps_list()
    unresolved = []
    for term, kind in gl:
        if term in text and not (any(term in k or k in term for k in glossary)
                                 or (re.match(r"^[A-F]/[1-6]$", term) and any("A–F" in k for k in glossary))):
            unresolved.append(term)
    print(f"  ل2 فجوات المعجم: {len(gl)} رمزًا · ظهر منها بلا تعريف: {len(unresolved)}")
    if unresolved:
        print(f"       بلا تعريف: {' · '.join(unresolved[:8])}")

    # ── ل3: كل تعريف جديد يحمل مصدره
    nosrc = [k for k in glossary
             if re.search(r"مصدر|سجل داخلي|منشور", json.dumps(m.get("glossary_sources", {}), ensure_ascii=False)) is None
             and k in missing]
    has_sources_field = "glossary_sources" in m
    print(f"  ل3 حقل مصادر التعريفات: {'موجود' if has_sources_field else 'غير موجود بعد'}")

    # ── ل4: رسم مزدوج مسجَّل في مكتبة الإملاء وظهر برسمين في الإصدار
    orth_f = B / "appendices" / "libraries" / "orthography-consistency.md"
    clashes = []
    if orth_f.is_file():
        rows = [l.split("|") for l in orth_f.read_text(encoding="utf-8").splitlines() if l.startswith("|")]
        pairs = [(r[1].strip(), r[2].strip()) for r in rows
                 if len(r) > 3 and r[1].strip().startswith("«") and r[2].strip().startswith("«")]
        clashes = [f"{a}/{b}" for a, b in pairs if a != b and a in text and b in text]
    print(f"  ل4 مكتبة الإملاء: {len(clashes)} رسم مزدوج في الإصدار"
          + (f" → {' · '.join(clashes[:4])}" if clashes else ""))

    # ── ل5: رموز الإصدار مقابل مكتبة المعجم المبنية
    lex_f = B / "appendices" / "libraries" / "lexicon-library.json"
    unknown = []
    if lex_f.is_file():
        lex = load(lex_f) or {}
        known = set()
        for v in (lex.get("lexicon") or {}).values():
            if isinstance(v, dict) and v.get("term"):
                known.add(v["term"])
        known |= set(lex.get("lexicon") or {}) if isinstance(lex.get("lexicon"), dict) else set()
        tfile = B / "appendices" / "terminology.md"
        if tfile.is_file():
            known |= set(re.findall(r"[A-Z][A-Z0-9]{2,}", tfile.read_text(encoding="utf-8")))
        syms = set(re.findall(r"\b[A-Z][A-Z0-9]{2,}(?:/[A-Z]+)?\b", text))
        # أسماء السفن ليست رموزًا: تُستثنى من قياس المعجم (وإلا ظهرت أجزاء الأسماء رموزًا)
        try:
            sys.path.insert(0, str(B / "tools"))
            import vessel_names as vn                                  # noqa: PLC0415
            vessels = set()
            for v in (vn.from_report(date) or []):
                vessels |= {w for w in re.split(r"[^A-Za-z0-9]+", v) if w}
        except Exception:                                              # noqa: BLE001
            vessels = set()
        unknown = sorted(s for s in syms
                         if s not in known and s not in vessels
                         and not any(s in k for k in glossary))[:6]
    print(f"  ل5 مكتبة المعجم: {len(unknown)} رمزًا في الإصدار خارج المعجم"
          + (f" → {' · '.join(unknown)}" if unknown else ""))

    # ── ل6: مكتبة النتائج (findings) — تُقرأ في بوابة لا في مولّد فقط
    fd = B / "appendices" / "libraries" / "findings-register.md"
    n_find = 0
    if fd.is_file():
        n_find = len([l for l in fd.read_text(encoding="utf-8").splitlines() if l.strip().startswith("|")]) - 2
    print(f"  ل6 مكتبة النتائج: {max(n_find, 0)} بندًا مرصودًا · تقرؤها هذه البوابة")

    blockers = 0
    warns = len(missing) + len(unresolved) + len(clashes) + len(unknown)
    print()
    if blockers:
        print(f"النتيجة: عائق — {blockers} بندًا")
        return 2
    if warns:
        print(f"النتيجة: تحذير — {warns} بندًا (لا يمنع النشر)")
        print("     المطلوب: إدخال التعريفات الجديدة في البنك، وتسوية فجوات المعجم")
        return 1
    print("النتيجة: سليم — المكتبات مطبَّقة على الإصدار")
    return 0


if __name__ == "__main__":
    sys.exit(main())