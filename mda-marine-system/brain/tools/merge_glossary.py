#!/usr/bin/env python3
"""يدمج بنك التعريفات المعياري في قاموس الإصدار.

القاعدة: يُدمج البند فقط إذا ورد رمزه في نص الإصدار وكان غائبًا عن قاموسه.
تعريف الإصدار يتقدّم على البنك. الهدف: ألا يمر رمز مستخدم بلا تعريف للقارئ.

الاستخدام: python3 tools/merge_glossary.py --date 2026-10-20 [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

B = Path(__file__).resolve().parent.parent
BANK = B / "appendices" / "glossary-standard.json"


def symbol_present(sym: str, text: str) -> bool:
    """يبحث عن الرمز ككلمة مستقلة، ويقبل الصيغة المركّبة مثل MN- وEST-."""
    base = sym.rstrip("-")
    if sym.endswith("-"):
        return base in text
    if sym == "A–F / 1–6":
        return bool(re.search(r"\b[A-F]/\d\b", text))
    if sym == "NAVAREA IX":
        return "NAVAREA" in text
    pat = r"(?<![A-Za-z])" + re.escape(sym) + r"(?![A-Za-z])"
    return bool(re.search(pat, text))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="يُحدّث بنود البنك في القاموس حتى لو كانت موجودة")
    a = ap.parse_args()

    meta_p = B / "web" / "meta" / f"{a.date}.json"
    md_p = B / "reports" / f"{a.date}-sectioned.md"
    if not meta_p.exists():
        print(f"✘ لا ملف واجهة: {meta_p}")
        return 2

    bank = json.loads(BANK.read_text(encoding="utf-8"))
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    text = (md_p.read_text(encoding="utf-8") if md_p.exists() else "") \
        + "\n" + json.dumps(meta, ensure_ascii=False)

    glossary = meta.setdefault("glossary", {})
    # عطل ك-45: البنك صار يحمل مصدر كل تعريف وتصنيفه. ولا يدخل تعريف بلا مصدر.
    # البنية المقبولة: {"تعريف": نص, "المصدر": نص, "التصنيف": "منشور"|"داخلي"}
    # ويُقبل النص المجرد توافقًا مع البنك القديم، لكنه يُعلَن ناقص التوثيق.
    def _defn(entry):
        return entry["تعريف"] if isinstance(entry, dict) else entry

    def _src(entry):
        return (entry.get("المصدر", ""), entry.get("التصنيف", "")) if isinstance(entry, dict) else ("", "")

    untraced = [s for s, e in bank["symbols"].items()
                if not _src(e)[0] or _src(e)[1] not in ("منشور", "داخلي")]
    added, skipped_defined, skipped_absent = [], [], []
    for sym, entry in bank["symbols"].items():
        definition = _defn(entry)
        if sym in glossary:
            if a.force and glossary[sym] != definition:
                glossary[sym] = definition
                added.append(f"{sym} (مُحدَّث)")
            else:
                skipped_defined.append(sym)
        elif symbol_present(sym, text):
            glossary[sym] = definition
            added.append(sym)
        else:
            skipped_absent.append(sym)

    if added and not a.dry_run:
        meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")

    print(f"قاموس {a.date}: {len(glossary)} بندًا · أُضيف {len(added)} · "
          f"معرَّف سابقًا {len(skipped_defined)} · غير وارد {len(skipped_absent)}")
    if untraced:
        print(f"  ✘ بنود بلا مصدر أو تصنيف صحيح: {len(untraced)} — " + " · ".join(untraced[:6]))
        return 2
    for s in added:
        print(f"  + {s}")
    if a.dry_run:
        print("  (تجربة — لم يُكتب الملف)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
