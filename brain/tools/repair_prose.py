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
DOUBLED = B / "appendices" / "doubled-letters.json"


def load_rules() -> dict:
    return json.loads(RULES.read_text(encoding="utf-8"))


def fix_punctuation(text: str) -> tuple[str, int]:
    """الترقيم داخل السطر فقط — لا يعبر نهايات الأسطر (البند ز-3).

    صفوف الجداول المُنشئة (| :--- | · | --- |) لا تُمسّ: تغييرها يُفسد الجدول (مراجعة ثالثًا-6).
    """
    n = 0
    header = re.compile(r"^\s*\|[\s:|-]*\|[\s:|-]*\|?\s*$")
    pats = [
        (r"[ \t]+([،؛:.!؟])", r"\1"),          # مسافة/مسافات قبل علامة ترقيم
        (r"([،؛!؟])\1+", r"\1"),               # علامة مكرّرة
        (r"([،؛])[ \t]*([.،؛])", r"\1"),       # علامتان متجاورتان
        (r"\.{2,}(?!\.)", r"."),               # نقاط متعددة
    ]
    out = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\n")
        if header.match(body):
            out.append(line)
            continue
        for pat, rep in pats:
            body, k = re.subn(pat, rep, body)
            n += k
        out.append(body + ("\n" if line.endswith("\n") else ""))
    return "".join(out), n


def fix_doubled_letters(text: str, rules: dict) -> tuple[str, int]:
    """الحروف المضاعفة: «ةة» فقط، وأي حرف عربي تكرّر ثلاثًا فأكثر (اللاتيني لا يُمسّ: www في الروابط).

    «دد» و«يي» و«وو» و«اا» لا تُمسّ: تكرارات صحيحة في كلمات شائعة
    («عدد» · «تقييم» · «تهدد» · «الالتزامات») — مراجعة 23 أكتوبر 2026 ثالثًا-1.
    والقائمة المشتركة واحدة يقرأها المصلح والكاشف من appendices/doubled-letters.json.
    """
    sh = json.loads(DOUBLED.read_text(encoding="utf-8"))
    wl = set(sh["whitelist"])
    fixed = sh.get("forbidden_fixed") or ["ةة"]
    minrep = int(sh.get("forbidden_repeat_min") or 3)
    n = 0
    out = []
    for word in re.split(r"(\s+)", text):
        if not word.strip() or word in wl:
            out.append(word)
            continue
        new = word
        for f in fixed:
            new, k = re.subn(re.escape(f) + r"+", f[0], new)
            n += k
        new, k2 = re.subn(r"([\u0600-\u06FF])\1{" + str(minrep - 1) + r",}", r"\1", new)
        n += k2
        out.append(new)
    return "".join(out), n


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
