#!/usr/bin/env python3
"""قنوات المصادر — مصدر واحد للحقيقة لقناة كل مصدر معتمد (ك-212).

القاعدة الملزمة: كل مصدر في السجل المعتمد له قناة واحدة فقط، ومجموع القنوات = المعتمد.
أي مصدر جديد يُضاف إلى السجل بلا قناة ⇒ مانع باسمه، لا سقوط صامت من العدّاد.

القنوات:
  • rss     : مسار آلي معلن في جدول التغذيات (sections/10-sources.md).
  • browser : مرجعية تُراجع يدويًا/بمتصفح (تُعلن هنا برقمها).
  • proxy   : مسار رسمي بديل للجهة نفسها (بيانات الصفحة المُضمَّنة) — يُعلن هنا.

الاستخدام:
  from source_channels import channels, identity
  channels()   -> {"rss": {…}, "browser": {…}, "proxy": {…}}
  identity()   -> (الإجمالي, المعتمد, أرقام بلا قناة, أرقام في قناتين)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

B = Path(__file__).resolve().parent.parent

# ── القناة الآلية: تُشتق من جدول التغذيات المُعلن، لا تُكتب يدويًا ──
RSS_TABLE = B / "sections" / "10-sources.md"
RSS_SECTION_LABEL = "تغذية آلية"

# ── المرجعية اليدوية/المتصفح: أرقام اعتمدها المالك، بعلة مكتوبة لكل مجموعة ──
# JS/محتوى غير مستخرج آليًا: 1، 5، 13، 39، 40، 59
# ضجيج تنقّل/تسويق: 21، 23، 34، 44، 52
# حجب/جلسة رسمية: 15، 18، 19، 48، 56، 57، 60، 61، 62
# فشل TLS مع كونا: 27
# 29 «البحرية الملكية البريطانية»: الموقع كله يرد 403 على أي عميل آلي (بما فيه الصفحة الرئيسية)
#    ⇒ تُقيَّد مرجعية تُراجع بالمتصفح، ولا يُبنى مسار يتجاوز الحماية (سياسة المستخدم) — ك-212
MANUAL_REFERENCE: set[int] = {
    1, 5, 13, 15, 18, 19, 21, 23, 27, 29, 34, 39,
    40, 44, 48, 52, 56, 57, 59, 60, 61, 62,
}

# ── قناة المسار الرسمي البديل للجهة نفسها ──
PROXY_ROUTES: set[int] = set()

# ك-81: واس (26) صار له مسار رسمي (بيانات الصفحة المُضمَّنة) ⇒ لم يعد «يُفحص بالمتصفح»
BROWSER_ONLY: dict[int, str] = {}


def rss_numbers() -> set[int]:
    """أرقام المصادر ذات المسار الآلي — تُشتق من جدول المسارات الحقيقي في check_feeds.

    المصدر الوحيد للحقيقة هو جدول المسارات المستعمل في التشغيل اليومي، لا نسخ نصّية منه،
    فإضافة مسار جديد تدخل العدّاد تلقائيًا (توسّع بلا إعادة بناء).
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import check_feeds  # noqa: WPS433
        return {int(x["num"]) for x in check_feeds.feeds()}
    except Exception:
        return set()



def channels() -> dict[str, set[int]]:
    auto = rss_numbers() - set(MANUAL_REFERENCE)
    return {"rss": auto, "browser": set(MANUAL_REFERENCE), "proxy": set(PROXY_ROUTES)}


def approved_numbers() -> list[int]:
    recs = json.loads((B / "appendices" / "source-reliability-40.json").read_text(encoding="utf-8"))
    return [int(r[0]) for r in recs]


def identity() -> tuple[int, int, list[int], list[int]]:
    """(الإجمالي الموزّع, المعتمد, أرقام بلا قناة, أرقام في أكثر من قناة)."""
    ch = channels()
    flat: list[int] = []
    for nums in ch.values():
        flat.extend(nums)
    approved = approved_numbers()
    total = len(set(flat))
    dup = sorted({n for n in flat if flat.count(n) > 1})
    gap = sorted(set(approved) - set(flat))
    return total, len(approved), gap, dup


def line_ar() -> str:
    ch = channels()
    total, approved, gap, dup = identity()
    txt = (f"القنوات: {approved} معتمدة = {len(ch['rss'])} بالمسار الآلي + "
           f"{len(ch['browser'])} بالمرجعية اليدوية")
    if ch["proxy"]:
        txt += f" + {len(ch['proxy'])} بمسار رسمي بديل"
    if gap:
        txt += f" · بلا قناة: {gap}"
    if dup:
        txt += f" · في قناتين: {dup}"
    return txt


if __name__ == "__main__":
    print(line_ar())
