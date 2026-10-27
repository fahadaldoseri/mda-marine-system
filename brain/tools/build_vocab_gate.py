#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بناء بوابة المفردات من السجل الحاكم — مصدر حكم واحد لا سجلين.

المبدأ
------
سجل واحد يحكم، والبوابة تُبنى منه آليًا، فلا يتناقض سجلان بعد اليوم:

    appendices/simplified-vocabulary.json   ← السجل الحاكم (حكم المالك وحده)
    appendices/forbidden-coinages.json      ← مُولَّد: لا يُحرَّر يدويًا (تقارنه بوابة المصطنعة)
    appendices/style-blacklist.json         ← قائمة المراقبة تُكمَّل منه

الأوامر
-------
  --check     (الافتراضي) يقارن المُولَّد بالسجل. رمز 2 عند أي انحراف، و0 عند المطابقة.
  --apply     يكتب المُولَّد من السجل.
  --migrate   ترحيل بنود القائمة المانعة القائمة إلى السجل الحاكم (يعمل مرة واحدة، وآمن للتكرار).
  --status    جدول حالات السجل.

رموز الخروج: 0 مطابق · 2 انحراف أو خطأ في السجل · 70 انهيار.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / "appendices" / "simplified-vocabulary.json"
COINAGES = BASE / "appendices" / "forbidden-coinages.json"
BLACKLIST = BASE / "appendices" / "style-blacklist.json"
TODAY = date.today().isoformat()

STATUSES = {
    "approved": "مانع — يوقف التسليم",
    "watch": "مراقب — يُرصد ولا يوقف",
    "rejected": "لا يُدرج — لا قاعدة ولا رصد",
    "proposed": "بانتظار قرار المالك",
}
REQUIRED = ("term", "plain", "status", "source")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: dict, indent: int) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def load_registry() -> dict:
    if not REGISTRY.exists():
        fail(f"السجل الحاكم مفقود: {REGISTRY}")
    return load_json(REGISTRY)


def validate(reg: dict) -> list[str]:
    """تحقق من صحة السجل. أي خلل ⇒ انحراف مانع (فشل مغلق)."""
    errs: list[str] = []
    entries = reg.get("entries")
    if not isinstance(entries, list) or not entries:
        return ["السجل بلا بنود (entries)"]
    seen: dict[str, str] = {}
    for i, e in enumerate(entries, 1):
        for k in REQUIRED:
            if not str(e.get(k) or "").strip():
                errs.append(f"البند {i}: الحقل «{k}» مطلوب")
        st = str(e.get("status") or "")
        if st not in STATUSES:
            errs.append(f"البند {i} ({e.get('term')}): حالة غير معروفة «{st}»")
        if st == "approved":
            if not str(e.get("reason") or "").strip():
                errs.append(f"البند {i} ({e.get('term')}): المانع يحتاج «reason» مكتوبًا")
            if not str(e.get("since") or "").strip():
                errs.append(f"البند {i} ({e.get('term')}): المانع يحتاج «since» (تاريخ السريان)")
        plain = e.get("plain")
        if not isinstance(plain, list) or not [p for p in plain if str(p).strip()]:
            errs.append(f"البند {i} ({e.get('term')}): «plain» قائمة بدائل غير فارغة")
        term = str(e.get("term") or "").strip()
        if term in seen and seen[term] != st:
            errs.append(f"اللفظ «{term}» بحالتين مختلفتين: {seen[term]} و{st}")
        seen[term] = st
    return errs


def canonical_coinages(reg: dict) -> dict:
    """المُولَّد من حالات «approved» فقط — بترتيب ثابت ليكون القياس حتميًا."""
    approved = [e for e in reg["entries"] if e.get("status") == "approved"]
    approved.sort(key=lambda e: (str(e.get("since") or ""), str(e.get("term") or "")))
    entries = []
    for e in approved:
        plain = [str(p).strip() for p in e["plain"] if str(p).strip()]
        entries.append({
            "term": str(e["term"]).strip(),
            "replacement": plain[0],
            "reason": str(e.get("reason") or "").strip(),
            "source": str(e.get("source") or "").strip(),
            "since": str(e.get("since") or "").strip(),
        })
    return {
        "version": 2,
        "status": "generated",
        "updated": str(reg.get("updated") or TODAY),
        "note": "مُولَّد آليًا من appendices/simplified-vocabulary.json — لا يُحرَّر يدويًا. "
                "الأمر: python3 tools/build_vocab_gate.py --apply",
        "entries": entries,
    }


def canonical_watch(reg: dict) -> list[dict]:
    out = []
    for e in reg["entries"]:
        if e.get("status") == "watch":
            plain = [str(p).strip() for p in e["plain"] if str(p).strip()]
            out.append({"term": str(e["term"]).strip(), "replacement": plain[0] if plain else ""})
    out.sort(key=lambda e: e["term"])
    return out


def diff_coinages(want: dict) -> list[str]:
    if not COINAGES.exists():
        return ["ملف القائمة المصطنعة مفقود"]
    have = load_json(COINAGES)
    h = {e.get("term"): (e.get("replacement"), e.get("since")) for e in have.get("entries", [])}
    w = {e["term"]: (e["replacement"], e["since"]) for e in want["entries"]}
    out = []
    for t in sorted(set(w) - set(h)):
        out.append(f"ينقص المُولَّد: {t}")
    for t in sorted(set(h) - set(w)):
        out.append(f"زائد في المُولَّد: {t}")
    for t in sorted(set(h) & set(w)):
        if h[t] != w[t]:
            out.append(f"مختلف: {t} — المُولَّد {h[t]} · السجل {w[t]}")
    return out


def watch_gaps(reg: dict) -> list[str]:
    want = canonical_watch(reg)
    if not want:
        return []
    bl = load_json(BLACKLIST)
    have = {str(e.get("term") or "").strip() for e in bl.get("watch", [])}
    return [f"حالة «مراقب» بلا قائمة رصد: {e['term']}" for e in want if e["term"] not in have]


def apply_watch(reg: dict) -> int:
    """يُكمل قائمة المراقبة في القائمة السوداء بحالات «watch» الناقصة."""
    want = canonical_watch(reg)
    bl = load_json(BLACKLIST)
    have = {str(e.get("term") or "").strip() for e in bl.get("watch", [])}
    added = [e for e in want if e["term"] not in have]
    if not added:
        return 0
    bl.setdefault("watch", []).extend(added)
    bl["updated"] = TODAY
    dump_json(BLACKLIST, bl, indent=1)
    return len(added)


def migrate() -> int:
    """ترحيل بنود القائمة المانعة القائمة إلى السجل الحاكم بلا فقدان سبب ولا تاريخ."""
    reg = load_registry()
    reg.setdefault("entries", [])
    have = {str(e.get("term") or "").strip() for e in reg["entries"]}
    moved = 0
    for e in load_json(COINAGES).get("entries", []):
        term = str(e.get("term") or "").strip()
        if not term or term in have:
            continue
        reg["entries"].append({
            "term": term,
            "plain": [str(e.get("replacement") or "").strip()],
            "status": "approved",
            "since": str(e.get("since") or TODAY).strip(),
            "reason": str(e.get("reason") or "").strip(),
            "source": str(e.get("source") or "").strip(),
            "decision": {"by": "صاحب القرار", "date": str(e.get("since") or TODAY),
                         "note": "مُرحَّل من القائمة المصطنعة عند توحيد السجلين (2026-10-27)"},
        })
        have.add(term)
        moved += 1
    reg["version"] = 2
    reg["status"] = "canonical"
    reg["updated"] = TODAY
    reg["note"] = ("السجل الحاكم لحكم المالك على الألفاظ. القائمة المانعة تُبنى منه آليًا "
                   "بـ tools/build_vocab_gate.py، فلا يُحرَّر forbidden-coinages.json يدويًا.")
    reg["statuses"] = STATUSES
    reg["entries"].sort(key=lambda e: (str(e.get("status")), str(e.get("term"))))
    dump_json(REGISTRY, reg, indent=2)
    print(f"  ✔ رُحّل {moved} بندًا إلى السجل الحاكم · مجموعه الآن {len(reg['entries'])} بندًا")
    return 0


def fail(msg: str, code: int = 2) -> None:
    print(f"  ✘ {msg}", file=sys.stderr)
    sys.exit(code)


def main() -> int:
    ap = argparse.ArgumentParser(description="بناء بوابة المفردات من السجل الحاكم")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="تحقق فقط (الافتراضي)")
    g.add_argument("--apply", action="store_true", help="اكتب المُولَّد من السجل")
    g.add_argument("--migrate", action="store_true", help="ترحيل بنود القائمة القائمة إلى السجل")
    g.add_argument("--status", action="store_true", help="عرض جدول الحالات")
    a = ap.parse_args()

    if a.migrate:
        return migrate()

    reg = load_registry()
    errs = validate(reg)
    if a.status:
        counts: dict[str, int] = {}
        for e in reg["entries"]:
            counts[str(e.get("status"))] = counts.get(str(e.get("status")), 0) + 1
        print("  السجل الحاكم:", REGISTRY.name, "· الإصدار", reg.get("version"), "· آخر تحديث", reg.get("updated"))
        for k, v in STATUSES.items():
            print(f"   {k:<9} {counts.get(k, 0):>3}  — {v}")
        for e in reg["entries"]:
            if e.get("status") in ("approved", "watch"):
                print(f"     · {e['term']} → {' · '.join(e['plain'])}  [{e['status']}]")
        return 0

    if errs:
        for e in errs:
            print(f"  ✘ {e}", file=sys.stderr)
        fail("السجل الحاكم غير صالح — لا يُبنى منه شيء قبل إصلاحه")

    want = canonical_coinages(reg)

    if a.apply:
        dump_json(COINAGES, want, indent=1)
        n = apply_watch(reg)
        print(f"  ✔ كُتب المُولَّد: {len(want['entries'])} بندًا مانعًا"
              + (f" · أُضيف {n} إلى قائمة الرصد" if n else " · قائمة الرصد لا تحتاج تعديلًا"))
        return 0

    d = diff_coinages(want)
    g2 = watch_gaps(reg)
    if d or g2:
        for x in d + g2:
            print(f"  ✘ {x}", file=sys.stderr)
        fail("انحراف: المُولَّد لا يعكس السجل — نفّذ build_vocab_gate.py --apply")
    print(f"  ✔ السجل الحاكم والمُولَّد متطابقان — {len(want['entries'])} بندًا مانعًا · "
          f"{len(canonical_watch(reg))} مراقبًا")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(70)