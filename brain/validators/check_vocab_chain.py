#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس سلسلة الاستبدال (ك-470 ← ك-487) — يمنع أن يكون بديل آليّ لفظًا ممنوعًا.

السبب المثبت 2026-11-02: المحرِّر الآلي استبدل «المصادر المستشهد بها» بـ«المصادر المذكورة» وهي ممنوعة.

السبب المثبت 2026-11-03 (توسيع ثانٍ): حصر الفحص في «التساوي التام» مع قائمة واحدة أفلت مدخلات
السجل الحاكم التي كان بديلها **يحتوي** اللفظ الممنوع نفسه («مقذوف غير محدد المصدر» بديلًا عن
«غير محدد المصدر»)، فأُعيد اللفظ الممنوع إلى متن اليوم ومنع التسليم.

طبقتان الآن:
  · منع (رمز 2): بديل يحتوي **لفظه الممنوع نفسه** — السلسلة الذاتية التي تكررت فعلًا.
    وكذلك أي بديل آلي في writing-rules.json يحتوي لفظًا ممنوعًا.
  · تنبيه (رمز 1): بديل يحتوي لفظًا ممنوعًا من **مدخل آخر** — تعارض بين بندين يحتاج قرار مالك،
    ويُعرض بلا إيقاف التسليم حتى يُحسم.

تفصيل السلسلة الذاتية:
  · مانعة: اللفظ الممنوع **داخل** البديل كجزء من تركيب أوسع («غير محدد المصدر» ← «مقذوف غير محدد المصدر»)
    فهذا يعيد اللفظ الممنوع إلى المتن بالضبط.
  · تنبيهية: البديل **يبدأ** باللفظ الممنوع ثم يضيف شرحًا بين قوسين أو بديلًا آخر مفصولًا بفاصلة
    («بلاغ تحالف اليمن (ذكر اسم طرف نزاع)» · «لا تؤكد، لم تؤكد») — صف تصريح مشروط لا استبدال.

المصادر: ألفاظ مصطنعة (appendices/forbidden-coinages.json) + السجل الحاكم للمعجم
(appendices/simplified-vocabulary.json). تُستثنى الألفاظ الأقصر من ثلاثة أحرف من فحص الاحتواء.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RULES = BASE / "appendices" / "writing-rules.json"
COINAGES = BASE / "appendices" / "forbidden-coinages.json"
LEDGER = BASE / "appendices" / "simplified-vocabulary.json"
MIN_LEN = 3


def banned_terms(coinages: Path, ledger: Path) -> set[str]:
    terms: set[str] = set()
    if coinages.exists():
        d = json.loads(coinages.read_text(encoding="utf-8"))
        for e in d.get("entries", []):
            t = str(e.get("term") or "").strip()
            if t:
                terms.add(t)
    if ledger.exists():
        d = json.loads(ledger.read_text(encoding="utf-8"))
        for e in d.get("entries", []):
            if str(e.get("status") or "approved").strip() not in {"", "approved"}:
                continue
            t = str(e.get("term") or "").strip()
            if t:
                terms.add(t)
    return {t for t in terms if len(t) >= MIN_LEN}


def applied_targets(rules: Path) -> list[tuple[str, str, str]]:
    if not rules.exists():
        return []
    r = json.loads(rules.read_text(encoding="utf-8"))
    out: list[tuple[str, str, str]] = []
    for item in r.get("autoreplace", []):
        t = str(item.get("term") or "").strip()
        rep = str(item.get("do") or item.get("replacement") or "").strip()
        if t and rep:
            out.append(("autoreplace", t, rep))
    for item in r.get("manual_only", []):
        t = str(item.get("dont") or "").strip()
        rep = str(item.get("do") or "").strip()
        if t and rep:
            out.append(("manual_only", t, rep))
    return out


def ledger_targets(ledger: Path) -> list[tuple[str, str, str]]:
    if not ledger.exists():
        return []
    d = json.loads(ledger.read_text(encoding="utf-8"))
    out: list[tuple[str, str, str]] = []
    for e in d.get("entries", []):
        t = str(e.get("term") or "").strip()
        if not t:
            continue
        for plain in e.get("plain", []) or []:
            rep = str(plain).strip()
            if rep:
                out.append(("ledger", t, rep))
    return out


def classify(targets, banned) -> tuple[list, list]:
    blocks, warns = [], []
    for src, term, rep in targets:
        for b in banned:
            if b in rep:
                # سلسلة ذاتية: اللفظ الممنوع نفسه داخل البديل.
                # مانعة إن كان العطف داخل تركيب أوسع؛ تنبيهية إن بدأ البديل باللفظ ثم أضاف شرحًا أو بديلًا آخر.
                if b != term:
                    warns.append((src, term, rep, b))
                elif rep.strip().startswith(b):
                    warns.append((src, term, rep, b))
                else:
                    blocks.append((src, term, rep, b))
                break
    return blocks, warns


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس سلسلة الاستبدال", allow_abbrev=False)
    ap.add_argument("--rules", type=Path, default=RULES)
    ap.add_argument("--coinages", type=Path, default=COINAGES)
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--strict", action="store_true",
                    help="ارفع التعارضات التنبيهية إلى رمز 1 (افتراضيًا: تُعرض وتبقى غير مانعة)")
    a = ap.parse_args()

    banned = banned_terms(a.coinages, a.ledger)
    targets = applied_targets(a.rules) + ledger_targets(a.ledger)
    blocks, warns = classify(targets, banned)

    for src, term, rep, b in blocks[:20]:
        print(f"   ✘ سلسلة استبدال ({src}): «{term}» ← «{rep}» والبديل يحتوي اللفظ الممنوع نفسه «{b}»",
              file=sys.stderr)
    for src, term, rep, b in warns[:20]:
        print(f"   تنبيه تعارض ({src}): «{term}» ← «{rep}» يحتوي لفظًا ممنوعًا في بند آخر «{b}»",
              file=sys.stderr)

    if blocks:
        print(f"   النتيجة: مانع — {len(blocks)} سلسلة ذاتية من {len(targets)} بديلًا "
              f"(مع {len(warns)} تعارضًا تنبيهيًّا)", file=sys.stderr)
        return 2

    print(f"   ✔ لا سلسلة ذاتية: {len(targets)} بديلًا آليًا · {len(banned)} لفظًا ممنوعًا · "
          f"تعارضات تنبيهية: {len(warns)}")
    return 1 if (warns and a.strict) else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run

    run(main)
