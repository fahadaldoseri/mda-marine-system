#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فاحص النقل بين الإصدارات — يمنع نقل وصف حادث من فترة أخرى.

القاعدة (قرار صاحب القرار — 20 أكتوبر 2026): وصف حادث بسنة أو اسم سفينة لا يطابق
فترة التقرير يُرصد آليًا، وهو ما وقع فعلًا في BW RHINE (حادث 2019 وُصف كواقعة 2026).

الفحوص:
  ف1 تعارض السنة     — سنة في كتلة وقائعية لا تطابق سنة الفترة بلا قرينة رجوع   (مانع)
  ف2 تعارض الاسم     — اسم سفينة مرتبط في الدفتر بواقعة خارج الفترة بلا قرينة  (مانع)
  ف3 نقل حرفي        — كتلة مطابقة حرفيًا لإصدار سابق بنسبة عالية                  (تحذير)
  ف4 حقل المصدر     — كتلة وقائعية بلا إسناد أو بلا زمن                          (مانع)

الاستخدام: python3 validators/check_carryover.py --date 2026-10-20 [--window 5] [--file مسار]
الرمز: 0 نجاح · 1 تحذير · 2 مانع
"""
from __future__ import annotations

import sys
import argparse, json, re, unicodedata, difflib
from pathlib import Path

B = Path(__file__).resolve().parent.parent

# قرائن الرجوع الزمني: عبارات تُعلن صراحةً أن الواقعة خارج الفترة.
# عطل ك-46: كانت القائمة تضم السنة نفسها و«سنة» و«منذ»، فأعفت أي ذكر لها فصار
# الفاحص لا يرصد شيئًا. القرينة يجب أن تُعلن الخروج من الفترة، لا أن تذكره فقط.
BACKREF = ("حادث سابق", "واقعة سابقة", "خلفية", "خلفي", "تاريخي", "تاريخية",
           "للمقارنة", "قديم", "قديمة", "نص قديم", "مُعاد استخدامه", "إعادة تدوير",
           "في الماضي", "أُعيد التذكير", "مرجع تاريخي")
BACKREF_SPAN = 90  # مدى البحث حول السنة بالحروف
# كلمات ليست أسماء سفن
NOT_VESSEL = {
    "NAVAREA", "UKMTO", "JMIC", "IMO", "OFAC", "AIS", "DTG", "ISM", "MPA", "GFS",
    "EST", "MN", "OCT", "UTC", "CRITICAL", "SEVERE", "SUBSTANTIAL", "SIGNIFICANT",
    "MODERATE", "ACH", "ICD", "BMP", "NCAGS", "CMF", "STS", "MSI", "MMSI", "VHF",
    "GNSS", "IMF", "AFP", "BNA", "IRNA", "PGSA", "FZE", "SPAR", "RPG", "WARNING",
    "DOC", "TLS", "AIS", "NO", "WAM", "SPA", "RSS", "Z", "E", "N",
    "GNSS", "MSCIO", "JBIC", "AI", "NATO", "EU", "UN", "US", "USA", "UAE",
}
VESSEL_PAT = re.compile(r"\b([A-Z][A-Z0-9]{2,}(?:\s+[A-Z][A-Z0-9]{2,}){0,2})\b")


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[ـ\u064B-\u0652]", "", t)
    t = re.sub(r"[*_`#>\[\]()]", " ", t)
    return re.sub(r"\s+", " ", t).strip()



def _is_time(text: str, start: int, end: int) -> bool:
    """يميّز الزمن العسكري عن السنة.

    عطل ك-47: «1922 UTC» زمن الحادث لا سنة 1922، ورُصد إنذارًا كاذبًا مانعًا.
    الزمن يتبع لاحقته UTC أو Z، أو يسبقه لفظ زمني صريح.
    """
    after = text[end:end + 8].strip().upper()
    if after.startswith(("UTC", "Z", "ZULU")):
        return True
    before = text[max(0, start - 34):start]
    return bool(re.search(r"(زمن|الساعة|عند|بتوقيت|توقيت)\s*\**\s*$", before))

def blocks_of(text: str) -> list[dict]:
    """يستخرج الكتل الوقائعية: كل كتلة تبدأ برمز MN- وتضم بنودها الفرعية."""
    out, cur = [], None
    for line in text.split("\n"):
        if re.match(r"^\s*-\s*\*\*MN-", line):
            if cur:
                out.append(cur)
            cur = {"head": norm(line), "body": ""}
        elif cur is not None:
            if line.startswith("## "):
                out.append(cur); cur = None
            elif line.strip():
                cur["body"] += " " + norm(line)
    if cur:
        out.append(cur)
    if not out:
        # التقارير الخاصة لا تحمل رموز MN-. عطل ك-46: أخذ كل بند بارز في المستند
        # أنتج 39 كتلة و76 إنذارًا كاذبًا؛ فحُصر الرصد في أقسام الوقائع وحدها.
        infacts = False
        for line in text.split("\n"):
            if line.startswith("## "):
                infacts = bool(re.search(r"الوقائع|الحوادث|البلاغ|ما حدث", line))
                continue
            if not infacts:
                continue
            if re.match(r"^\s*-\s*\*\*[^*]{6,}\*\*", line) or \
               re.match(r"^\s*\d+\.\s*\*\*[^*]{6,}\*\*", line):
                out.append({"head": norm(line), "body": "", "code": "بند وقائعي",
                            "special": True})
        for b in out:
            b["text"] = b["head"]
        return out
    for b in out:
        b["code"] = (re.search(r"MN-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]+", b["head"]) or
                     re.search(r"MN-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]+", b["body"]))
        b["code"] = b["code"].group(0) if b["code"] else "?"
        b["text"] = b["head"] + " " + b["body"]
    return out


def ledger_names() -> dict[str, list[str]]:
    """خريطة: اسم السفينة → تواريخ ورودها في الدفتر التراكمي."""
    m: dict[str, list[str]] = {}
    for f in sorted((B / "cumulative-2026" / "daily").glob("*.json")):
        try:
            recs = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            raise  # فشل مغلق: خطأ يخصّ حكم البوابة ⇒ رمز 70 (البند د)
        if not isinstance(recs, list):
            continue
        for r in recs:
            if not isinstance(r, dict):
                continue
            blob = f"{r.get('title','')} {r.get('source','')} {r.get('area','')}"
            d = str(r.get("date", ""))
            for mm in VESSEL_PAT.finditer(blob):
                name = mm.group(1).strip()
                if name.split()[0] in NOT_VESSEL or len(name) < 4:
                    continue
                m.setdefault(name, [])
                if d and d not in m[name]:
                    m[name].append(d)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--window", type=int, default=5)
    ap.add_argument("--file")
    a = ap.parse_args()

    src = Path(a.file) if a.file else B / "reports" / f"{a.date}-sectioned.md"
    if not src.exists():
        print(f"✘ لا ملف: {src}"); return 2
    text = src.read_text(encoding="utf-8")
    blocks = blocks_of(text)
    if not blocks:
        print(f"فاحص النقل — {a.date}: لا كتل وقائعية (لا مانع)")
        return 0

    year = a.date[:4]
    names = ledger_names()
    # كتل الإصدارات السابقة للمطابقة الحرفية
    prev = []
    for f in sorted((B / "reports").glob("*-sectioned.md")):
        if f.name.startswith(a.date):
            continue
        for b in blocks_of(f.read_text(encoding="utf-8")):
            prev.append((f.stem, b["text"]))
    prev = prev[-max(a.window, 1) * 12:]

    f1, f2, f3, f4 = [], [], [], []
    for b in blocks:
        t = b["text"]; code = b["code"]
        hay = t
        has_back = any(k in hay for k in BACKREF)

        # ف1 تعارض السنة — القرينة تُقاس بقربها من السنة لا بوجودها في الكتلة
        def _explained(pos_from: int, pos_to: int) -> bool:
            win = hay[max(0, pos_from - BACKREF_SPAN): pos_to + BACKREF_SPAN]
            return any(k in win for k in BACKREF)

        for mm in re.finditer(r"\b((?:19|20)[0-9]{2})\b", hay):
            y = mm.group(1)
            if y == year:
                continue
            if _is_time(hay, mm.start(), mm.end()) or _explained(mm.start(), mm.end()):
                continue
            f1.append((code, f"سنة {y} لا تطابق فترة {year}"))

        # ف2 تعارض الاسم
        for mm in VESSEL_PAT.finditer(t):
            name = mm.group(1).strip()
            if name.split()[0] in NOT_VESSEL or len(name) < 4:
                continue
            dates = names.get(name) or []
            old = [d for d in dates if d[:4] != year or d < a.date]
            far = [d for d in old if (a.date[:4] != d[:4]) or
                   (int(a.date[8:10]) - int(d[8:10])) > 7 if len(d) == 10]
            if far and not has_back:
                f2.append((code, f"{name} مرتبط في الدفتر بـ {far[0]}"))

        # ف3 نقل حرفي
        for ed, pt in prev:
            r = difflib.SequenceMatcher(None, t, pt).ratio()
            if r >= 0.85 and len(t.split()) >= 12:
                f3.append((code, f"تشابه {r:.0%} مع {ed}"))
                break

        # ف4 حقل المصدر والتاريخ — على الكتل اليومية فقط (بنية الخاص مختلفة)
        if b.get("special"):
            continue
        if "الإسناد" not in b["body"] and "الإسناد" not in b["head"]:
            f4.append((code, "لا بند إسناد"))
        if not re.search(r"\d{6}Z|\d{1,2}\s+(?:أكتوبر|سبتمبر|نوفمبر|OCT|SEP|NOV)|"
                         r"كما في|\d{4}-\d{2}-\d{2}", t):
            f4.append((code, "لا زمن صريح"))

    print(f"=== فاحص النقل بين الإصدارات — {a.date} — {len(blocks)} كتلة وقائعية ===")
    sev = 0
    for tag, items, kind in (("ف1 تعارض السنة", f1, "مانع"),
                             ("ف2 تعارض الاسم", f2, "مانع"),
                             ("ف3 نقل حرفي", f3, "تحذير"),
                             ("ف4 حقل المصدر والزمن", f4, "مانع")):
        if items:
            print(f"  {tag}: {len(items)} — ✘ {kind}" if kind == "مانع"
                  else f"  {tag}: {len(items)} — · {kind}")
            for c, d in items[:6]:
                print(f"       {c}: {d}")
            if kind == "مانع":
                sev = 2
            elif sev == 0:
                sev = 1
        else:
            print(f"  {tag}: 0")
    if sev == 2:
        print("  النتيجة: مانع — وصف خارج الفترة أو بلا إسناد")
    elif sev == 1:
        print("  النتيجة: تحذير — راجع النقل الحرفي")
    else:
        print("  النتيجة: اجتاز — لا نقل خارج الفترة")
    return sev


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    raise SystemExit(main())
