#!/usr/bin/env python3
"""المعجم المحوكم: مصدر واحد للحقيقة بين المهارتين والسجل الحاكم وبرومت الكتابة.

المشكلة الحقيقية التي عولجت:
  `sections/20-lexicon.md` هو ما يقرأه كاتب التقرير فعلًا (يُضمَّن نصًّا في برومت خطوة الكتابة)،
  لكنه كان ملفًا محرَّرًا يدويًا بلا إسناد، بينما `appendices/simplified-vocabulary.json` سجل حاكم
  يتحقق منه G044. النتيجة: مصدران للحقيقة، وتناقض فعلي مقيس (المعجم يمنع «الفترة الزمنية المحددة»
  والسجل يوصي بها؛ المعجم يمنع «المصادر المذكورة» والسجل يوصي بها).

المعالجة (بلا تراجع عن أي قرار محرَّر):
  1) قرارات المعجم المحرَّرة تُدمج في السجل الحاكم (تُضاف أو يُصحَّح بديلها) بمرجع موثَّق.
  2) قسم «أ) ألفاظ ومعانٍ» يُولَّد من السجل الحاكم وحده (مصدر واحد).
  3) قسمان «ب» و«ج» نصّان محرَّران يُحفظان كما هما.
  4) الرأس يُسمّي المهارتين الحاكمتين وإصدار السجل الحاكم.
  5) `--check` يعيد توليد القسم ويقارنه بالملف بندًا بندًا (تطابق بايتي للنص المولَّد).

الاستعمال: --check (افتراضي) · --apply (دمج + توليد + كتابة)
الخروج: 0 مطابق · 1 خرق · 2 خطأ.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from build_vocab_gate import validate

ROOT = Path(__file__).resolve().parent.parent
LEXICON = ROOT / "sections" / "20-lexicon.md"
REGISTRY = ROOT / "appendices" / "simplified-vocabulary.json"
BLACKLIST = ROOT / "appendices" / "style-blacklist.json"
SECTIONS = ROOT / "sections"
GOVERNING_SKILLS = ("military-arabic-editing", "marine-news-brain")
SEC_B = "## ب)"
SEC_D = "## د)"
HEAD_RE = re.compile(r"^# المعجم الموحّد[^\n]*\n")
ROW_RE = re.compile(r"^\|\s*(?P<meaning>[^|]*?)\s*\|\s*(?P<write>[^|]*?)\s*\|\s*(?P<avoid>[^|]*?)\s*\|\s*$")


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def dump(reg: dict) -> None:
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def split_alternatives(cell: str) -> list[str]:
    cell = norm(cell)
    if not cell or cell == "—":
        return []
    if cell.startswith("("):            # ملاحظة تحريرية لا بديل
        return []
    return [p.strip() for p in re.split(r"[،,·]", cell) if p.strip()]


def parse_lexicon(text: str) -> tuple[str, list[dict], str]:
    """يرجع (الرأس، صفوف قسم أ، ذيل الأقسام ب/ج)."""
    head_match = HEAD_RE.match(text)
    head = head_match.group(0) if head_match else "# المعجم الموحّد\n"
    body = text[len(head):]
    i = body.find(SEC_B)
    if i < 0:
        raise SystemExit("  ✘ قسم «ب)» غير موجود — لا يمكن التوليد بأمان")
    sec_a = body[:i]
    j = body.find(SEC_D, i)
    tail = body[i:j] if j > 0 else body[i:]   # «د» يُولَّد دائمًا، فلا يُقرأ من الملف (يمنع التكرار)
    rows = []
    for line in sec_a.splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        if m.group("meaning") in ("المعنى",) or set(m.group("avoid")) <= {"-", " ", ":"}:
            continue
        rows.append({k: norm(v) for k, v in m.groupdict().items()})
    return head, rows, tail


def merge_curated_into_registry(reg: dict, rows: list[dict]) -> list[str]:
    """يدمج قرارات المعجم المحرَّرة في السجل الحاكم ويصحّح التناقض. يرجع سجل التغييرات."""
    entries = reg.setdefault("entries", [])
    by_term = {norm(e["term"]): e for e in entries}
    changes: list[str] = []
    today = date.today().isoformat()
    for r in rows:
        write = r["write"]
        for banned in split_alternatives(r["avoid"]):
            if write in ("—", ""):
                continue
            e = by_term.get(norm(banned))
            if e is None:
                e = {"term": banned, "plain": [write], "status": "approved", "since": today,
                     "reason": "قرار ورشة اللغة: دمج بند المعجم المحرَّر في السجل الحاكم (مصدر واحد).",
                     "source": "sections/20-lexicon.md — قسم أ"}
                entries.append(e)
                by_term[norm(banned)] = e
                changes.append(f"أُضيف بند «{banned}» → «{write}»")
            elif write not in [norm(p) for p in e.get("plain", [])]:
                old = " · ".join(e.get("plain", []))
                e["plain"] = [write]
                e["since"] = today
                e["reason"] = (f"توحيد المصدر: المعجم المحرَّر يمنع «{old}» ويكتب «{write}» — "
                               f"صُحِّح السجل ليطابق قرار الورشة.")
                e["source"] = "sections/20-lexicon.md — قسم أ"
                changes.append(f"صُحِّح «{banned}»: «{old}» ← «{write}»")
    if changes:
        reg["updated"] = today
        reg["version"] = int(reg.get("version", 1)) + 1
        reg["note"] = (reg.get("note", "") + " · وحُّد مع المعجم المحرَّر (tools/lexicon_wiring.py).").strip(" ·")
    return changes


def render(reg: dict, tail: str, head_note: str) -> str:
    approved = [e for e in reg["entries"] if str(e.get("status")) == "approved"]
    seen: set[str] = set()
    lines: list[str] = []
    for e in approved:
        avoid = norm(e["term"])
        if avoid in seen:
            continue
        seen.add(avoid)
        write = " · ".join(norm(p) for p in (e.get("plain") or ["—"]))
        meaning = norm(e.get("meaning") or avoid)
        lines.append(f"| {meaning} | {write} | {avoid} |")
    head = ("# المعجم الموحّد — اكتب العمود الثاني ولا تكتب الثالث\n"
            f"\n<!-- {head_note} -->\n")
    sec_a = ("\n## أ) ألفاظ ومعانٍ\n\n"
             "| المعنى | اكتب | لا تكتب |\n|---|---|---|\n" + "\n".join(lines) + "\n\n")
    return head + sec_a + tail.strip("\n") + "\n" + render_section_d()


def blocking_terms() -> list[dict]:
    d = json.loads(BLACKLIST.read_text(encoding="utf-8"))
    out = []
    for e in d.get("blocking", []):
        t = norm(e.get("term"))
        if t:
            out.append({"term": t, "replacement": norm(e.get("replacement") or "—")})
    return out


def render_section_d() -> str:
    rows = [f"| {e['term']} | {e['replacement']} |" for e in blocking_terms()]
    return ("\n## د) ألفاظ ممنوعة (من القائمة السوداء الحاكمة)\n\n"
            "| لا تكتب | اكتب بدلًا منها |\n|---|---|\n" + "\n".join(rows) + "\n")


def missing_in_includes() -> list[str]:
    """كل لفظ مانع في القائمة السوداء يجب أن يراه الكاتب في ملفات sections/ المضمَّنة في البرومت."""
    blob = "\n".join(f.read_text(encoding="utf-8") for f in SECTIONS.glob("*.md"))
    return [e["term"] for e in blocking_terms() if e["term"] not in blob]


def note(reg: dict) -> str:
    return (f"مولَّد محوكم — المهارتان الحاكمتان: {' · '.join(GOVERNING_SKILLS)} · "
            f"السجل الحاكم: appendices/simplified-vocabulary.json v{reg.get('version')} "
            f"({reg.get('updated')}) · التوليد والتحقق: tools/lexicon_wiring.py (بوابة G044)")


def check() -> int:
    text = LEXICON.read_text(encoding="utf-8")
    reg = load()
    errors = validate(reg)
    if errors:
        print("  ✘ السجل الحاكم غير صالح: " + " · ".join(errors))
        return 2
    _, _, tail = parse_lexicon(text)
    want = render(reg, tail, note(reg))
    if want != text:
        got = {l.strip() for l in text.splitlines()}
        exp = {l.strip() for l in want.splitlines()}
        miss = sorted(exp - got)[:5]
        extra = sorted(got - exp)[:5]
        print("  ✘ المعجم لا يطابق السجل الحاكم (المصدر الواحد):")
        if miss:
            print("     · ناقص:", " | ".join(miss))
        if extra:
            print("     · زائد:", " | ".join(extra))
        return 1
    miss = missing_in_includes()
    if miss:
        print(f"  ✘ ألفاظ مانعة في القائمة السوداء لا يراها الكاتب في ملفات sections/ ({len(miss)}): "
              + " · ".join(miss[:8]))
        return 1
    n = len([e for e in reg["entries"] if str(e.get("status")) == "approved"])
    print(f"  ✔ المعجم مطابق للسجل الحاكم بندًا بندًا ({n} بندًا معتمدًا · إصدار السجل {reg.get('version')}) "
          f"· الإسناد يسمّي المهارتين: {' · '.join(GOVERNING_SKILLS)}")
    return 0


def apply() -> int:
    text = LEXICON.read_text(encoding="utf-8")
    reg = load()
    _, rows, tail = parse_lexicon(text)
    changes = merge_curated_into_registry(reg, rows)
    errors = validate(reg)
    if errors:
        print("  ✘ لا كتابة لسجل متناقض: " + " · ".join(errors))
        return 2
    if changes:
        dump(reg)
        for c in changes[:12]:
            print("   ·", c)
        print(f"   ✔ دُمج {len(changes)} تغييرًا في السجل الحاكم · الإصدار الآن {reg.get('version')}")
    LEXICON.write_text(render(reg, tail, note(reg)), encoding="utf-8")
    print("   ✔ أُعيد توليد قسم «أ» من السجل الحاكم (الأقسام ب/ج محفوظة كما هي)")
    return check()


def main() -> int:
    ap = argparse.ArgumentParser(description="توليد المعجم المحوكم من السجل الحاكم والتحقق من التطابق")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if not LEXICON.exists() or not REGISTRY.exists():
        print("  ✘ المعجم أو السجل الحاكم غير موجود")
        return 2
    return apply() if a.apply else check()


if __name__ == "__main__":
    sys.exit(main())
