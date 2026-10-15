#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سياسة عرض رموز الأحداث (الخيار 2 + 5 المعتمد من المالك).

القاعدة:
- الرمز الكامل `MN-YYYY-MM-DD-NN` يظهر **مرة واحدة** في قسم «الوقائع الجديدة».
- في كل موضع آخر يُعرض **مختصرًا**: `DD-NN` إذا كانت واقعة الشهر نفسه،
  و`MM-DD-NN` إذا كانت من شهر آخر (لأن التسلسل يُصفَّر شهريًا).
- ويُدمج مع **رقم البلاغ الرسمي** عند وجوده: `#172 · 15-04`.

المبدأ: الرمز الداخلي لا يتغير أبدًا (يبقى كاملًا في ملف الواجهة والدفتر التراكمي
وخريطة الرموز)؛ هذه الوحدة تخصّ **العرض للقارئ** فقط.
"""
import re

CODE_RE = re.compile(r"MN-(\d{4})-(\d{2})-(\d{2})-(\d{2})")
OFFICIAL_RE = re.compile(r"(?:UKMTO\s*)?#\s?(\d{2,4})")
PRIMARY_SECTION = "الوقائع الجديدة"


def is_primary(title):
    """هل هذا هو القسم الذي يُعرض فيه الرمز الكامل؟ (يبدأ بـ«الوقائع»)."""
    return str(title or "").strip().startswith("الوقائع")


def short_code(code, report_date=None):
    """صيغة العرض المختصرة لرمز الحدث."""
    m = CODE_RE.fullmatch(str(code or ""))
    if not m:
        return str(code or "")
    _y, mo, d, n = m.groups()
    rd = str(report_date or "")
    if len(rd) >= 7 and rd[5:7] == mo:
        return f"{d}-{n}"
    return f"{mo}-{d}-{n}"


def official_ref(*texts):
    """يستخرج رقم البلاغ الرسمي (#172) من أي حقل نصي."""
    for t in texts:
        if not t:
            continue
        m = OFFICIAL_RE.search(str(t))
        if m:
            return f"#{m.group(1)}"
    return ""


def label(code, ref="", note="", report_date=None, official=None):
    """الصيغة المعروضة: رقم البلاغ الرسمي · الرمز المختصر."""
    short = short_code(code, report_date)
    off = official_ref(ref, note) or (official or {}).get(str(code or ""), "")
    return f"{off} · {short}" if off else short


def official_map(meta):
    """خريطة الرمز ← رقم البلاغ الرسمي، تُبنى من ملف الواجهة."""
    out = {}
    if not isinstance(meta, dict):
        return out
    for key in ("changes", "event_keys", "map", "vessel_identity"):
        v = meta.get(key)
        items = v.get("points") if isinstance(v, dict) else v
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            c = it.get("code")
            if not c or c in out:
                continue
            off = official_ref(it.get("ref"), it.get("note"), it.get("text"), it.get("title"))
            if off:
                out[c] = off
    return out


def demote(text, report_date=None, official=None):
    """يستبدل الرموز الكاملة في نص ثانوي بالصيغة المختصرة المدموجة."""
    if not text:
        return text
    return CODE_RE.sub(lambda m: label(m.group(0), "", "", report_date, official), str(text))
