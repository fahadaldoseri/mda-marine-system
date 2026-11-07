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
PRIMARY_SECTION = "سجل الأحداث"
LEGACY_PRIMARY_SECTIONS = ("الوقائع الجديدة",)


def is_primary(title):
    """هل هذا هو القسم الذي يُعرض فيه الرمز الكامل؟ (يبدأ بـ«الوقائع»)."""
    t = str(title or "").strip()
    return t.startswith("سجل الأحداث") or t.startswith("الوقائع")


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


# ---------------------------------------------------------------- مستوى الصفحة
_SECTION_OPEN = re.compile(r"<section\b[^>]*>")
_SECTION_CLOSE = re.compile(r"</section>")
_TAG = re.compile(r"<[^>]+>")
_H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
_EVENT_ID_ATTR = re.compile(r'data-event-id="[^"]*"')


def _demote_fragment_preserving_event_ids(text, report_date=None, official=None):
    """اختصر النص الظاهر مع إبقاء معرفات الخريطة الحاكمة كاملةً."""
    protected = []

    def mask(match):
        token = f"\x00EVENT_ID_ATTR_{len(protected)}\x00"
        protected.append(match.group(0))
        return token

    masked = _EVENT_ID_ATTR.sub(mask, str(text))
    demoted = demote(masked, report_date, official)
    return re.sub(
        r"\x00EVENT_ID_ATTR_(\d+)\x00",
        lambda match: protected[int(match.group(1))],
        demoted,
    )


def _top_sections(doc):
    """يُرجع مدى كل قسم من المستوى الأعلى (بلا تداخل)."""
    spans, stack, open_at = [], 0, None
    for m in re.finditer(r"<section\b[^>]*>|</section>", doc):
        if m.group(0).startswith("</"):
            if stack:
                stack -= 1
                if stack == 0 and open_at is not None:
                    spans.append((open_at, m.end()))
                    open_at = None
        else:
            if stack == 0:
                open_at = m.start()
            stack += 1
    if open_at is not None:
        spans.append((open_at, len(doc)))
    return spans


def demote_page(doc, report_date=None, official=None):
    """يبسّط الرموز في كل ما هو خارج قسم الوقائع (كتل، جداول، خط زمني، مقدمة)."""
    if not doc:
        return doc
    out, pos = [], 0
    for a, b in _top_sections(doc):
        out.append(_demote_fragment_preserving_event_ids(doc[pos:a], report_date, official))
        blk = doc[a:b]
        hm = _H2.search(blk)
        title = _TAG.sub("", hm.group(1)).strip() if hm else ""
        out.append(blk if is_primary(title) else _demote_fragment_preserving_event_ids(blk, report_date, official))
        pos = b
    out.append(_demote_fragment_preserving_event_ids(doc[pos:], report_date, official))
    return "".join(out)
