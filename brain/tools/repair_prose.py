#!/usr/bin/env python3
"""خطوة الإصلاح الآلي الواحدة للصياغة — قبل إعادة البوابة (طلب صاحب القرار، البند 8).

تعمل لغةً وترقيمًا فقط: لا تمسّ الأرقام ولا الرموز ولا الوقائع.
تصلح: الألفاظ المصطنعة المعتمدة، والقالب المتكرر أكثر من الحد، والترقيم المتجاور والمسافة قبله.
تخرج: 0 = لا مخالفة بعد الإصلاح · 2 = بقيت مخالفات ⇒ التسليم يوقف.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
RULES = B / "appendices" / "writing-rules.json"


def load_rules() -> dict:
    return json.loads(RULES.read_text(encoding="utf-8"))


def fix_punctuation(text: str) -> tuple[str, int]:
    n = 0
    pats = [(r"\s+([،؛:.!؟])", r"\1"), (r"([،؛])\1+", r"\1"), (r"([،؛])\s*([.،؛])", r"\1")]
    for pat, rep in pats:
        text, k = re.subn(pat, rep, text)
        n += k
    return text, n


def fix_terms(text: str, rules: dict) -> tuple[str, int]:
    n = 0
    for item in rules.get("autoreplace", []):
        term, rep = item["term"], item["replacement"]
        text, k = re.subn(rf"(?<![\w\u0600-\u06FF]){re.escape(term)}(?![\w\u0600-\u06FF])", rep, text)
        n += k
    return text, n


def fix_templates(text: str, rules: dict) -> tuple[str, int]:
    cap = int(rules.get("template_cap", 2))
    alts = rules.get("template_alternatives") or []
    if not alts:
        return text, 0
    lines = text.splitlines()
    # القالب = بداية سطر نقطي ثابتة («- **نفّذوا** — ») تتكرر أكثر من الحد
    heads: dict[str, list[int]] = {}
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*[-*]\s*\*\*[^*]+\*\*\s*[—–-])\s", line)
        if m:
            heads.setdefault(m.group(1).strip(), []).append(i)
    n = 0
    for head, idxs in heads.items():
        if len(idxs) <= cap:
            continue
        for j, i in enumerate(idxs[cap:]):
            alt = alts[j % len(alts)]
            rest = lines[i].split(head, 1)[1].lstrip()
            lines[i] = alt + rest
            n += 1
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--md", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    md = Path(a.md) if a.md else B / "reports" / f"{a.date}-sectioned.md"
    if not md.exists():
        print(f"  ✘ لا نص تقرير: {md}")
        return 2
    rules = load_rules()
    text = md.read_text(encoding="utf-8")
    before = text
    text, p1 = fix_punctuation(text)
    text, p2 = fix_terms(text, rules)
    text, p3 = fix_templates(text, rules)
    changed = text != before
    if changed and not a.dry_run:
        md.write_text(text, encoding="utf-8")
    print(f"  · الترقيم: {p1} · الألفاظ: {p2} · القوالب المُنوّعة: {p3}"
          + ("  (تجربة بلا كتابة)" if a.dry_run else ""))
    chk = subprocess.run([sys.executable, str(B / "validators" / "check_prose_defects.py"), "--md", str(md)],
                         capture_output=True, text=True)
    rc = chk.returncode
    tail = [l for l in chk.stdout.splitlines() if "النتيجة" in l]
    print("  " + (tail[-1] if tail else f"رمز المدقق: {rc}"))
    if rc >= 2:   # 1 = تنبيه (كلمات مشتبهة) لا يمنع · 2 = مخالفة مانعة
        print("  ✘ بقيت مخالفات صياغة مانعة بعد الإصلاح الواحد — التسليم يوقف (يُسجَّل السبب).")
        return 2
    print("  ✔ لا مخالفة صياغة بعد الإصلاح.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
