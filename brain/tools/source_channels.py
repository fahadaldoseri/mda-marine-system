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
class ChannelsUnavailable(RuntimeError):
    """تعذّر بناء خريطة القنوات — يُعلن مانعًا لا يُبتلع."""


MANUAL_REFERENCE: set[int] = {
    39, 52,
}
# ترقية 2026-10-29 (جولة المصادر): أحد عشر مصدرًا كانت «مرجعية يدوية» ثبت لها مسار آلي
# بقياس حي مُوثَّق، فسُجّلت مساراتها في FALLBACK_ROUTES في tools/check_feeds.py:
#   1 UKMTO · 5 IMO · 13 ShipNext · 21 أخبار الخليج · 23 GDN · 27 كونا · 29 البحرية الملكية
#   34 MSCIO · 40 MarineTraffic · 44 Windward (تغذية رسمية) · 48 ISW (واجهة JSON رسمية)
# ولم يبقَ في القائمة إلا ما لا مسار آلي مُثبتًا له:
#   39 IHO: كل مساراتها 200 لكن بلا محتوى دلالي (sitemap روابط بلا عناوين، وfeed صفحة stub 1323B).
#   52 SynMax: تغذيتها المعلنة رسميًا 200 و0 عنصر، وواجهتها تعيد مصفوفة فارغة.
# الشرط: كل مسار مُدرج يقرأ محتوى حقيقيًا؛ ونجاح HTTP وحده لا يُحتسب (ك-).
# ترقية 2026-10-29: عشرة مصادر كانت «مرجعية يدوية» صار لها مسار آلي مُثبت بالقياس
# الحي في جدول التغذيات (sections/10-sources.md):
#   • حسابات X (15، 17، 18، 19، 56، 57، 60، 61، 62): الصفحة العامة الرسمية تحمل
#     حمولة المنشورات، ويقرأها مستخرج x-profile في tools/content_extractors.py.
#   • قناة تلغرام (59): عرضها العام /s/<قناة> يحمل الرسائل بتواريخها (telegram-preview).
# لا يبقى في هذه القائمة إلا ما لا مسار آلي مُثبتًا له بعد؛ وإثبات الترقية في سجل الأعطال.

# مسار كل مصدر بلا تغذية آلية: browser + الرابط المرجعي المعلن في سجل الموثوقية.
# تبقى MANUAL_REFERENCE هي مجموعة القنوات التي تدخل العدّاد، وهذا السجل يضيف عنوان المسار فقط.
BROWSER_ROUTES: dict[int, dict[str, str]] = {
    1: {"path": "browser", "url": "https://www.ukmto.org/recent-incidents"},
    5: {"path": "browser", "url": "https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx"},
    13: {"path": "browser", "url": "https://shipnext.com/vessel/9315159-cameroon-prosperity"},
    15: {"path": "browser", "url": "https://x.com/UK_MTO"},
    18: {"path": "browser", "url": "https://x.com/bahdiplomatic"},
    19: {"path": "browser", "url": "https://x.com/us5thfleet"},
    21: {"path": "browser", "url": "https://akhbar-alkhaleej.com/"},
    23: {"path": "browser", "url": "https://www.gdnonline.com"},
    27: {"path": "browser", "url": "https://www.kuna.net.kw"},
    29: {"path": "browser", "url": "https://www.royalnavy.mod.uk/news"},
    34: {"path": "browser", "url": "https://www.mscio.eu"},
    39: {"path": "browser", "url": "https://iho.int/"},
    40: {"path": "browser", "url": "https://www.marinetraffic.com/"},
    44: {"path": "browser", "url": "https://www.windward.ai/"},
    48: {"path": "browser", "url": "https://www.understandingwar.org/"},
    52: {"path": "browser", "url": "https://synmax.com/"},
    56: {"path": "browser", "url": "https://x.com/YemenResistanc1"},
    57: {"path": "browser", "url": "https://x.com/spokespersonyem"},
    59: {"path": "browser", "url": "https://t.me/army21ye"},
    60: {"path": "browser", "url": "https://x.com/CJFCSpox"},
    61: {"path": "browser", "url": "https://x.com/ERYANIM"},
    62: {"path": "browser", "url": "https://x.com/Yemenarmyeng"},
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
    except (ImportError, AttributeError, KeyError, ValueError, OSError) as e:
        # ك-: لا ابتلاع صامت. تعذّر جدول المسارات يُعلن مانعًا صريحًا بدل إرجاع مجموعة فارغة
        # تُسقط كل المصادر من العدّاد بلا سبب ظاهر.
        raise ChannelsUnavailable(
            f"تعذّر تحميل جدول مسارات الفحص: {type(e).__name__}: {e}") from e



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
