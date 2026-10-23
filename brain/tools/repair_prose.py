#!/usr/bin/env python3
"""الإصلاح الآلي الواحد للصياغة — البند (ز) من مراجعة 23 أكتوبر 2026.

القاعدة بعد المراجعة: الإصلاح الآلي محصور في ثلاث حالات لا تتأثر بالنحو:
  1) الترقيم: مسافة قبل علامة ترقيم · علامة مكرّرة · علامتان متجاورتان — داخل السطر فقط.
  2) الحروف المضاعفة التي لا تصح («معلنةة» ← «معلنة»).
  3) ألفاظ ذات صيغة ثابتة لا يغيّرها الفاعل ولا العدد («عبورات» ← «عمليات عبور»).

وما يتأثر بالفاعل أو العدد أو التركيب لا يُصلَح آليًا:
  • إن وُجد في النص ⇒ يُوقف التسليم (رمز 2) وتُدرج جمله في تنبيه لإعادة كتابتها بالمعنى.
  • تنويع القالب المتكرر ميكانيكيًا أُلغي: تكرار القالب أكثر من الحد = إيقاف وتنبيه.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
RULES = B / "appendices" / "writing-rules.json"


def load_rules() -> dict:
    return json.loads(RULES.read_text(encoding="utf-8"))


def fix_punctuation(text: str) -> tuple[str, int]:
    """الترقيم داخل السطر فقط — لا يعبر نهايات الأسطر (البند ز-3)."""
    n = 0
    pats = [
        (r"[ \t]+([،؛:.!؟])", r"\1"),          # مسافة/مسافات قبل علامة ترقيم
        (r"([،؛!؟])\1+", r"\1"),               # علامة مكرّرة
        (r"([،؛])[ \t]*([.،؛])", r"\1"),       # علامتان متجاورتان
        (r"\.{2,}(?!\.)", r"."),               # نقاط متعددة
    ]
    for pat, rep in pats:
        text, k = re.subn(pat, rep, text)
        n += k
    return text, n


def fix_doubled_letters(text: str, rules: dict) -> tuple[str, int]:
    """حروف مضاعفة لا تصح في العربية: «معلنةة» ← «معلنة» · «الةة» ← «الة»."""
    allow = set(rules.get("doubled_letters_allowed") or ["ةة"])
    n = 0
    for d in rules.get("doubled_letters_forbidden") or ["ةة", "اا", "يي", "وو"]:
        if d in allow:
            continue
        text, k = re.subn(re.escape(d) + r"+", d[0], text)
        n += k
    return text, n


def fix_fixed_terms(text: str, rules: dict) -> tuple[str, int]:
    """ألفاظ ذات صيغة ثابتة فقط (auto = true). غيرها لا يُمسّ."""
    n = 0
    for item in rules.get("autoreplace", []):
        if not item.get("auto"):
            continue
        term, rep = item["term"], item["replacement"]
        text, k = re.subn(rf"(?<![\w\u0600-\u06FF]){re.escape(term)}(?![\w\u0600-\u06FF])", rep, text)
        n += k
    return text, n


def grammar_sensitive_hits(text: str, rules: dict) -> list[tuple[str, str]]:
    """جمل فيها لفظ يتأثر استبداله بالنحو ⇒ تُعاد كتابتها بالمعنى ولا تُصلَح آليًا."""
    hits: list[tuple[str, str]] = []
    for item in rules.get("manual_only", []):
        if not item.get("stop_on_hit"):
            continue
        term = item["term"]
        for line in text.splitlines():
            if re.search(rf"(?<![\w\u0600-\u06FF]){re.escape(term)}(?![\w\u0600-\u06FF])", line):
                hits.append((term, line.strip()[:180]))
    return hits


def template_overuse(text: str, rules: dict) -> list[tuple[str, int]]:
    """تكرار قالب نقطي أكثر من الحد — يُعاد كتابته طبيعيًا، ولا يُبدَّل ميكانيكيًا."""
    cap = int(rules.get("template_cap", 2))
    heads: dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(r"^(\s*[-*]\s*\*\*[^*]+\*\*\s*[—–-])\s", line)
        if m:
            h = m.group(1).strip()
            heads[h] = heads.get(h, 0) + 1
    return [(h, c) for h, c in heads.items() if c > cap]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--md", default=None, help="مسار نص بديل (للاختبار)")
    a = ap.parse_args()
    p = Path(a.md) if a.md else B / "reports" / f"{a.date}-sectioned.md"
    if not p.exists():
        print(f"  ✘ لا نص تقرير: {p}")
        return 2
    rules = load_rules()
    text = p.read_text(encoding="utf-8")
    original = text
    text, n_p = fix_punctuation(text)
    text, n_d = fix_doubled_letters(text, rules)
    text, n_t = fix_fixed_terms(text, rules)
    if not a.dry_run and text != original:
        p.write_text(text, encoding="utf-8")
    print(f"  · الترقيم: {n_p} · الحروف المضاعفة: {n_d} · ألفاظ ثابتة: {n_t}"
          + (" (تجربة بلا كتابة)" if a.dry_run else ""))

    bad = False
    hits = grammar_sensitive_hits(text, rules)
    if hits:
        bad = True
        print(f"  ✘ {len(hits)} جملة فيها لفظ يتأثر استبداله بالنحو — تُعاد كتابتها بالمعنى، ولا تُصلَح آليًا:")
        for term, line in hits[:12]:
            print(f"    - [{term}] {line}")
        al = B / "logs" / "alerts"
        al.mkdir(parents=True, exist_ok=True)
        (al / f"{a.date}-إعادة-كتابة-بال-معنى.md").write_text(
            "# جمل تحتاج إعادة كتابة بالمعنى (لا تُصلَح آليًا)\n\n"
            + "\n".join(f"- **{t}** — {l}" for t, l in hits) + "\n", encoding="utf-8")
        print(f"    · التنبيه: logs/alerts/{a.date}-إعادة-كتابة-بال-معنى.md")
    over = template_overuse(text, rules)
    if over:
        bad = True
        print("  ✘ قالب نقطي تكرّر أكثر من الحد — يُعاد كتابته طبيعيًا (لا تبديل ميكانيكي):")
        for h, c in over:
            print(f"    - {h} — {c} مرات (الحد {rules.get('template_cap', 2)})")
    if bad:
        print("  ✘ الإصلاح الآلي لا يحلّ هذه الحالات — التسليم يوقف حتى إعادة الكتابة")
        return 2
    print("  ✓ لا حالة تحتاج إعادة كتابة بالمعنى")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validators"))
    from _guard import run

    run(main)
