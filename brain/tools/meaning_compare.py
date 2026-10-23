#!/usr/bin/env python3
"""مقارنة استخراجين مستقلين لواقعة واحدة: واحد من الأصل الإنجليزي وواحد من النص العربي.

الفكرة (فحص ترجمة عكسية): يستخرج النموذج من كل نص، كلٌّ على حدة ودون أن يرى الآخر، حقولًا ثابتة
(المخطط أدناه). فإذا اختلفت الحقول فقد تغيّر المعنى في الترجمة.

الاستعمال:  python3 meaning_compare.py source.json arabic.json
الخروج:     0 = متطابق · 2 = فرق جوهري (أرقام/أسماء/يقين/نوع/نسبة) · 1 = فرق ثانوي (موقع/زمن).
المخطط:
{
  "event_type": "attack|advisory|warning|military_interaction|piracy|suspicious_activity|incident_update|background|market_indicator|other",
  "certainty": "official_confirmed|official_unconfirmed|media_report|one_sided_claim|estimate|none",
  "attribution": "none|named_by_official|claimed_by_party|alleged_by_media",
  "attributed_to": "اسم الجهة المنسوب إليها الفعل أو القول بالإنجليزية (UKMTO, IRGC, IMO…) أو null",
  "numbers": ["كل الأرقام الواردة في الواقعة كنصوص: 11, 179-26, 119 …"],
  "names": ["أسماء السفن والجهات والأماكن بالأحرف اللاتينية"],
  "location": "الموقع كما ورد (نص حر)",
  "time": "الزمن كما ورد (نص حر)"
}
"""
import json
import re
import signal
import sys

signal.signal(signal.SIGPIPE, signal.SIG_DFL)
STRICT = ["event_type", "certainty", "attribution", "attributed_to"]


def norm_set(xs):
    return {re.sub(r"\s+", " ", str(x)).strip().upper() for x in (xs or []) if str(x).strip()}


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 0
    a = json.load(open(sys.argv[1], encoding="utf-8"))
    b = json.load(open(sys.argv[2], encoding="utf-8"))
    major, minor = [], []
    for k in STRICT:
        va, vb = (a.get(k) or "").__str__().upper(), (b.get(k) or "").__str__().upper()
        if va != vb:
            major.append(f"  {k}: الأصل={a.get(k)!r} · العربي={b.get(k)!r}")
    for k in ("numbers", "names"):
        sa, sb = norm_set(a.get(k)), norm_set(b.get(k))
        if sa != sb:
            major.append(f"  {k}: ناقص في العربي={sorted(sa - sb)} · زائد في العربي={sorted(sb - sa)}")
    for k in ("location", "time"):
        if (a.get(k) or "").strip().lower() != (b.get(k) or "").strip().lower():
            minor.append(f"  {k}: الأصل={a.get(k)!r} · العربي={b.get(k)!r} (راجع بالعين)")
    if major:
        print("✘ فرق جوهري في المعنى:")
        print("\n".join(major + minor))
        return 2
    if minor:
        print("⚠ فرق ثانوي (للمراجعة):")
        print("\n".join(minor))
        return 1
    print("✔ الاستخراجان متطابقان في الحقول الجوهرية")
    return 0


if __name__ == "__main__":
    sys.exit(main())
