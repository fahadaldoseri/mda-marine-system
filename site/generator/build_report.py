from brain_root import under_brain as _brain
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد صفحة التقرير الصباحي (نسخة الويب / HTTPS) — Marine News Brain.

الاستخدام:
  python3 build_report.py --md <تقرير.md> --out <صفحة.html> --meta <meta.json>

المبدأ: المصدر الوحيد للحقيقة هو ملف Markdown + ملف meta. لا يُعدَّل الناتج يدويًا.

الإصلاحات المدمجة بعد مراجعة التصميم والمراجعة التقنية:
- ألوان الطباعة تُعاد تعريفها كاملة (لا وراثة ألوان النمط الداكن).
- المحتوى مرئي افتراضيًا؛ الحركة تحسين اختياري عند توفر JavaScript.
- أعمدة المخطط بأعراض ثابتة واتجاه معزول (LTR isolate) بلا التفاف.
- عزل كل قيمة لاتينية/رقمية مركبة بـ bdi لمنع اضطراب الاتجاه في العربية.
- روابط المصادر صارت قابلة للنقر من تعريفات Markdown.
- منع التجاوز الأفقي على الجوال، وإصلاح تباين النمط النهاري.
- هروب صفات HTML بشكل صحيح، وفحوص مدخلات تفشل برسالة واضحة.
- تسلسل عناوين صحيح، scope للأعمدة، aria-hidden للأيقونات، وحالة تركيز ظاهرة.
- قواعد كسر صفحات صحيحة للجداول والبطاقات، وأحجام طباعة لا تقل عن 10.5pt.
"""

import argparse
import html
import json
import re
import reader_grade_labels
import threat_card as TC
import sys
from datetime import datetime, timezone
from display_format import format_release_version, format_update_label
from third_person import to_third_person

# أقسام تُكتب بأسلوب الغائب (م-31): لا صيغة مخاطبة في التوجيهات والتوصيات.
DIRECTIVE_SECTIONS = ("التوجيهات التشغيلية", "التوصيات", "التوجيهات", "الإجراءات المقترحة")

# CSS فهرس المحتويات (م-32): شريط خفيف لا يدفع بطاقة القرار خارج الشاشة الأولى.
TOC_CSS = """
.toc{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:14px 0 4px;font-size:13px}
.toc .toc-l{color:var(--muted);margin-inline-end:4px}
.toc a{display:inline-block;padding:3px 9px;border:1px solid var(--line);border-radius:999px;
  color:var(--ink2);text-decoration:none;background:var(--card)}
.toc a:hover{border-color:var(--accent);color:var(--accent)}
.dc-jump{color:inherit;text-decoration:underline;text-decoration-style:dotted;text-underline-offset:3px}
.upd{margin:10px 0}
.upd .upd-h{font-weight:700;margin:0 0 6px}
.upd-list{margin:0;padding-inline-start:18px}
.upd-list li{margin:4px 0}
"""


def _third_person_html(html: str) -> str:
    """يطبّق أسلوب الغائب على النصوص خارج الوسوم فقط (لا يمسّ السمات)."""
    parts = re.split(r"(<[^>]+>)", html)
    return "".join(p if p.startswith("<") else to_third_person(p) for p in parts)


def structure_update_paragraphs(html: str) -> str:
    """م-16: فقرة «تحديث» الكثيفة تُقسَّم بنودًا مع تمييز العنوان وفواصل نصية.

    تعمل على كل الإصدارات بلا قائمة تواريخ ثابتة: أي فقرة طويلة تبدأ بعلامة تحديث
    تُحوَّل إلى قائمة بنود. الفقرات القصيرة أو غير المصنّفة تمرّ كما هي.
    """
    pat = re.compile(r"<p([^>]*)>((?:(?!</p>).){180,4000}?)</p>", re.S)

    def repl(m):
        attrs, inner = m.group(1), m.group(2)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        head = re.match(r"^(تحديث|ما تغيّر|التقدّم|التقدم)\b[:：]?", text)
        if not head:
            return m.group(0)
        parts = [p.strip() for p in re.split(r"\s*(?:؛|\.\s|•)\s*", text) if len(p.strip()) > 25]
        if len(parts) < 2:
            return m.group(0)
        items = "".join(f"<li>{p}</li>" for p in parts)
        label = head.group(1)
        return (f'<div class="upd"{attrs}><p class="upd-h">{label}</p>'
                f'<ul class="upd-list">{items}</ul></div>')

    return pat.sub(repl, html)

from html.parser import HTMLParser

# الاسم المعتمد للتقرير اليومي
from daily_title import DAILY_TITLE, normalize_daily_title  # noqa: E402
HERO_KPI_MODERN_FROM = "2026-10-31"
from pathlib import Path


# نمط وسم نوع البند في القوائم — مصدر واحد يخدم القائمة المنظّمة والمرقّمة، فلا يتكرر النمط
MARK_RE = re.compile(r"^\[(حقيقة|واقعة|تقدير تحليلي|تقدير|إعلامي|إعلام|خلفية|مراقبة)\]\s*")

# رموز الدرجات داخل المادة المصدرية مفيدة للتدقيق، لكنها ليست لغة قارئ في صفحة «إضافات».
# تُقرأ الأوصاف من خريطة حاكمة مشتركة مع المولّد الإنجليزي وفاحص التماثل.
_GRADE_MAP_PATH = _brain("appendices", "confidence-grade-map.json")
_GRADE_MAP = json.loads(_GRADE_MAP_PATH.read_text(encoding="utf-8"))["grades"]
_INTERNAL_GRADE_LABELS = {code: entry["arabic"] for code, entry in _GRADE_MAP.items()}
_INTERNAL_GRADE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:" + "|".join(re.escape(k) for k in _INTERNAL_GRADE_LABELS) + r")(?![A-Za-z0-9_])"
)


def redact_internal_grade_codes(text: str) -> str:
    """يحوّل رموز درجات الإسناد إلى وسم القارئ العربي.

    ك-599: الوسم يأتي من الوحدة المشتركة مع المولّد الإنجليزي، فلا يتسرّب رمز
    داخلي إلى أي سطح، ولا يُحقن وسم عربي في سطح إنجليزي.
    """
    return reader_grade_labels.redact(text, "ar")


def compact_threat_section_html(section_html: str) -> str:
    """يختصر العبارات المكررة في قسم التهديد دون إسقاط الوقائع أو مستويات القطاعات."""
    replacements = (
        ("المستوى في ", ""),
        ("ما يبرره في كلمات قليلة", "السبب"),
        ("لا واقعة مؤهلة داخل الفترة", "لا واقعة مؤهلة"),
        ("استمراري؛ آخر واقعة مؤهلة في هذا القطاع بتاريخ ", "مستمر؛ آخر واقعة مؤهلة في "),
        ("لماذا لم يرتفع أكثر:", "سبب الثبات:"),
        ("ما يرفعه أو يخفضه:", "عوامل التغيير:"),
        ("لا تأكيد رسمي لتضرر ", "لا تأكيد لتضرر "),
        ("الانتقال إلى حالة حرجة يتطلب ", "الحالة الحرجة تتطلب "),
    )
    for before, after in replacements:
        section_html = section_html.replace(before, after)
    return section_html


class BuildError(Exception):
    pass


_TEMPLATE_ARTIFACT_RE = re.compile(r"[{}]|<%|%>|\$\{")

# ك-11-11ح: تاريخ الإصدار الجاري، لتعبئة العناصر النائبة في نصوص المصادر عند العرض.
_REPORT_DATE = ""


def assert_no_template_artifacts(text, label: str = "النص المرئي") -> None:
    """Fail closed when a template/dict representation reaches reader text."""
    value = str(text or "")
    match = _TEMPLATE_ARTIFACT_RE.search(value)
    if match:
        # ك-11-11ز: الرسالة تسمي القيمة المسببة ليمكن إغلاق العطل من قياس واحد.
        snippet = re.sub(r"\s+", " ", value)[:120]
        raise BuildError(
            f"تسرّب رمز قالب في {label}: {match.group(0)!r} — لا يُعرض النص الخام · القيمة: {snippet!r}"
        )


import blocks as BLK
import codes  # سياسة عرض رموز الأحداث (كامل مرة واحدة، ومختصر مدموج برقم البلاغ)
import screen_layer as SCR  # طبقة الشاشة: القرار فوق الطيّ، للشاشة فقط (لا تمسّ الطباعة)
from card_measurements import count_rendered_fragment

IMO_INCIDENTS_JSON = _brain("appendices", "imo-incidents.json")
AR_MONTHS = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}


def _imo_reference_line(meta: dict) -> str:
    """سطر مرجعي لا يُعرض بلا قراءة ناجحة من سجل IMO الحاكم."""
    try:
        raw = json.loads(IMO_INCIDENTS_JSON.read_text(encoding="utf-8"))
        totals = raw.get("totals") if isinstance(raw, dict) else None
        confirmed = totals.get("confirmed_incidents") if isinstance(totals, dict) else None
        if isinstance(confirmed, bool) or not isinstance(confirmed, int) or confirmed < 0:
            raise ValueError("totals.confirmed_incidents ليس عددًا صحيحًا غير سالبًا")
        cards = meta.get("official_cards") if isinstance(meta, dict) else None
        card = next((row for row in cards or []
                     if isinstance(row, dict) and row.get("id") == "imo-confirmed-incidents"), None)
        layers = card.get("layers") if isinstance(card, dict) else None
        updated = layers.get("updated") if isinstance(layers, dict) else None
        updated = updated.get("value") if isinstance(updated, dict) else None
        if not updated:
            # ك-11-11ج: إصدارات سابقة لا تحمل layers.updated.value — يُقرأ التاريخ الموثّق من
            # ملف المصدر الحاكم نفسه (source.as_at ثم source.list_updated)، ويبقى الفشل مغلقًا عند غيابهما.
            try:
                _app = json.loads(IMO_INCIDENTS_JSON.read_text(encoding="utf-8"))
                _src = _app.get("source") if isinstance(_app, dict) else None
                _src = _src if isinstance(_src, dict) else {}
                _as_at = str(_src.get("as_at") or "").strip()
                _m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", _as_at)
                if _m:
                    _months = ["january","february","march","april","may","june","july",
                               "august","september","october","november","december"]
                    _mon = _months.index(_m.group(2).strip().lower()) + 1
                    parsed = datetime(int(_m.group(3)), _mon, int(_m.group(1)))
                    updated = f"{int(_m.group(3)):04d}-{_mon:02d}-{int(_m.group(1)):02d}"
                else:
                    _lu = str(_src.get("list_updated") or "").strip()
                    if _lu:
                        parsed = datetime.strptime(_lu, "%Y-%m-%d")
                        updated = _lu
            except (OSError, json.JSONDecodeError, ValueError, AttributeError):
                updated = None
        if not updated:
            raise ValueError("official_cards[imo-confirmed-incidents].layers.updated.value مفقود ولا سند مؤرخ في ملف المصدر الحاكم")
        try:
            parsed = datetime.strptime(str(updated), "%d/%m/%Y")
        except ValueError:
            parsed = datetime.strptime(str(updated), "%Y-%m-%d")
    except (OSError, json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
        raise BuildError(f"مصدر IMO الحاكم غير قابل للقراءة لسطر المرجع: {IMO_INCIDENTS_JSON}: {exc}") from exc
    date_label = f"{parsed.day} {AR_MONTHS[parsed.month]} {parsed.year}"
    return (
        '<p class="hmap-imo-reference" data-source="imo-incidents.json">'
        '<span>هجمات مؤكدة على سفن <bdi class="bidi" dir="ltr">(IMO)</bdi>:</span> '
        f'<bdi class="bidi" dir="ltr">{confirmed}</bdi> · '
        f'<span>آخر تحديث</span> <bdi class="bidi" dir="ltr">{date_label}</bdi>'
        '</p>'
    )


# ----------------------------------------------------------------------------
# نظام التصميم — «غرفة عمليات بحرية»: داكن، فيروزي واحد، بلا زخرفة
# ----------------------------------------------------------------------------
DESIGN_TOKENS = """
  --bg:#050a12;
  --bg-2:#08101c;
  --panel:#0c1626;
  --panel-2:#101d31;
  --panel-3:#152441;
  --line:#1d2e4a;
  --line-2:#28405f;
  --ink:#e9f0f9;
  --ink-2:#c3d2e6;
  --muted:#8ba0bd;
  --faint:#86AEDE;
  --accent:#22c3b6;
  --accent-ink:#04120f;
  --info:#4d9dff;
  --danger:#ff5d52;
  --warn:#ffb02e;
  --ok:#33d07a;
  --shadow-2:0 10px 30px -14px rgba(0,0,0,.7);
  --radius:12px;
  --radius-sm:8px;
  --map-sea:#06111f;
  --map-land:#22375a;
  --map-coast:#5b7ba6;
  --map-border:#33507a;
  --map-grid:#16273f;
  --map-grid-lbl:#54749c;
  --map-label:#dbe6f4;
  --map-country:#7f97b8;
  --map-sea-label:#4f6f96;
  --map-strait:#ffd9d5;
"""
DESIGN_TOKENS = ":root{" + DESIGN_TOKENS + "}"

FONT_LINK = "/assets/fonts/fonts.css"

# وسوم طبقات بطاقات المؤشرات (مصدر واحد مع بوابة check_kpi_layers)
CUM_LABEL = "المجموع من 28 فبراير 2026"
UPD_LABEL = "آخر تحديث"


def _hero_cumulative_html(k: dict) -> str:
    """لا يعرض مجموعًا تراكميًا كقراءة حالية بلا مصدر رسمي وتاريخ مسجل في ملف الواجهة."""
    value = k.get("cumulative")
    # ك-11-11هـ: قيمة الطبقة قد تكون كائنًا {label, value} فيُقرأ حقل value لا الكائن كاملًا.
    _val = value.get("value") if isinstance(value, dict) else value
    if value in (None, ""):
        return ""
    source = _value_text(k.get("cumulative_official_source") or k.get("source"))
    read_at = _value_text(k.get("cumulative_read_at") or k.get("updated"))
    official = "رسمي" in source or bool(re.search(r"\b(?:UKMTO|IMO)\b", source, re.I))
    if not source or not read_at or not official:
        _src2 = source or "دفتر الوقائع التراكمي"
        _read2 = read_at or _value_text(k.get("updated"))
        return (f'<div class="k-lay"><span class="k-lay-l">{CUM_LABEL}</span> '
                f'<b class="bidi">{esc(str(_val))}</b></div>'
                f'<div class="k-lay"><span class="k-lay-l">المصدر</span> <b>{inline(_src2)}</b>'
                + (f'<span class="k-lay-l">تاريخ القراءة</span> <b class="bidi">{esc(_read2)}</b>' if _read2 else "")
                + '</div>')  # ك-11-11د
    return (
        f'<div class="k-lay"><span class="k-lay-l">{CUM_LABEL}</span> '
        f'<b class="bidi">{esc(str(_val))}</b></div>'
        '<div class="k-lay"><span class="k-lay-l">المصدر الرسمي</span> '
        f'<b>{inline(source)}</b><span class="k-lay-l">تاريخ القراءة</span> '
        f'<b class="bidi">{esc(read_at)}</b></div>'
    )


SECTION_ICONS = {
    "الخلاصة": "flag",
    "الوقائع الجديدة": "alert",
    "سجل الأحداث": "alert",
    "التحذيرات والتنبيهات النشطة": "broadcast",
    "سجل IMO": "ledger",
    "مؤشرات الموقف": "gauge",
    "التوزيع الجغرافي للوقائع": "map",
    "خريطة الوقائع": "map",
    "الحركة الملاحية والتكدس": "route",
    "مستوى التهديد": "shield",
    "الاحتمالات ونسبة الحوادث إلى جهات": "scale",
    "قراءة الموقف وتحليل المؤشرات": "intel",
    "التوجيهات التشغيلية": "gear",
    "الخلفية القائمة": "history",
    "ما لم يُحسم": "gap",
    "المصادر والمراجع": "source",
}

SECTION_HINTS = {
    "ما تغيّر منذ التقرير السابق": "ما استُجد، وما تغيّر تصنيفه، وما أُغلق.",
    "الخلاصة": "الموقف ومستوى التهديد والإجراء المقترح في ثلاثة أسطر.",
    "التوزيع الجغرافي للوقائع": "أين تركّزت الوقائع، وحصيلة IMO بحسب النطاق.",
    "مؤشرات الموقف": "الأرقام، ومقارنتها بتقرير أمس، وحدود كل رقم.",
    # قرار المالك 2026-11-04: حُذف السطر التمهيدي لقسم «مستوى التهديد» لتمام
    # تكراره مع عناصر التصميم الرباعي، ولئلا يستهلك من سقف كلمات القسم.
    "التوجيهات التشغيلية": "ما يُنفَّذ قبل العبور والرسو وأثناء الحادث.",
    "الوقائع الجديدة": "الوقائع الأمنية الجديدة خلال فترة التغطية، مفصولًا عن الخلفية.",
    "سجل الأحداث": "الوقائع الأمنية الجديدة خلال فترة التغطية، مرتّبة بالرمز والتوقيت.",
    "التحذيرات والتنبيهات النشطة": "حالة الجهات الرسمية خلال فترة التقرير.",
    "سجل IMO": "الحصيلة الرسمية التراكمية، وآخر إدخال ظاهر.",
    "قراءة الموقف وتحليل المؤشرات": "ما يدل عليه النمط والافتراضات والفرضيات وعلامات الإنذار المبكر.",
    "الاحتمالات ونسبة الحوادث إلى جهات": "من قد يكون مسؤولًا، بلا جزم وبلا نسبة بلا دليل.",
    "الحركة الملاحية والتكدس": "حركة المضيق والرسو من مصادر معلنة فقط.",
    "ما لم يُحسم": "ما لم تحدده المواد بعد، وما يلزم متابعته في التقرير التالي.",
    "الخلفية القائمة": "وقائع أقدم لا يزال أثرها مؤثرًا على التشغيل.",
    "المصادر والمراجع": "حالة المصادر المفحوصة، وروابط المراجع المستشهد بها.",
}
# أقسام تُمنح تمييزًا بصريًا محسوبًا: خلاصة القرار + الإجراء المطلوب
PRIORITY_SECTIONS = ("الخلاصة", "التوجيهات التشغيلية")

# ── إخفاء أقسام من إصدار التقرير (الويب والطباعة معًا) — قرار المالك 2026-10-21 ──
# القاعدة: الإخفاء يُنفَّذ هنا مرة واحدة فيخدم الويب وPDF وWord، ولا تُحذف البيانات
# من ملف الواجهة ولا من دفتر الأحداث (تبقى للأرشيف والفحوص).
HIDDEN_SECTIONS = set()  # تُقرأ من سياسة Brain وحدها (ك-86/ك-91) — لا قائمة مزدوجة
HIDDEN_BLOCKS = set()  # تُقرأ من السياسة
ADDITIONS_SECTIONS = []  # أقسام صفحة «إضافات» (قرار المالك 2026-10-28) بترتيبها المعتمد
ADDITIONS_FROM = ""  # تاريخ سريان النقل؛ الإصدارات الأقدم في الأرشيف لا تتأثر


def load_section_policy(meta_path=None):
    """سياسة الأقسام من مصادرها الواحدة في Brain؛ تُنسخ إلى sources/ عند المزامنة."""
    global HIDDEN_SECTIONS, HIDDEN_BLOCKS, ADDITIONS_SECTIONS, ADDITIONS_FROM
    cands = []
    if meta_path:
        mp = Path(meta_path).resolve()
        ps = list(mp.parents)
        if len(ps) > 2:
            cands.append(ps[2] / "sources" / "report-sections-policy.json")
        if len(ps) > 1:
            cands.append(ps[1] / "appendices" / "report-sections-policy.json")
    cands.append(Path(__file__).resolve().parent.parent / "sources" / "report-sections-policy.json")
    for c in cands:
        try:
            if c.is_file():
                d = json.loads(c.read_text(encoding="utf-8"))
                HIDDEN_SECTIONS = set(d.get("hidden_sections") or [])
                HIDDEN_BLOCKS = set(d.get("hidden_blocks") or [])
                ADDITIONS_SECTIONS = list(d.get("additions_sections") or [])
                ADDITIONS_FROM = str(d.get("additions_effective_from") or "")
                print(f"سياسة الأقسام: {c} · محذوف {len(HIDDEN_SECTIONS)} · كتل {len(HIDDEN_BLOCKS)}",
                      file=sys.stderr)
                return c
        except Exception:
            continue
    return None


# _POLICY_LOADED_AT_IMPORT: تحميل السياسة عند الاستيراد، فلا يبقى أي افتراضي مزدوج
try:
    load_section_policy()
except Exception as _e:  # noqa: BLE001
    print(f"تعذّر تحميل سياسة الأقسام: {_e}", file=sys.stderr)


def _hidden(title: str) -> bool:
    return any(h in title for h in HIDDEN_SECTIONS)

INCIDENT_SECTION_KEYS = ("سجل الأحداث", "الوقائع الجديدة", "الوقائع", "الوقائع الأمنية")

ICON_PATHS = {
    "flag": "M4 3h9l-1.2 3H19v8h-8.2L9.6 11H6v9H4z",
    "alert": "M12 3l9 16H3zM12 8v6M12 16.4v1.2",
    "broadcast": "M12 10.5a2 2 0 100 4 2 2 0 000-4zM7.8 7.6a6.2 6.2 0 000 8.8M16.2 7.6a6.2 6.2 0 010 8.8M5 4.8a10 10 0 000 14.4M19 4.8a10 10 0 010 14.4",
    "ledger": "M5 3h11l3 3v15H5zM8 9h8M8 13h8M8 17h5",
    "gauge": "M12 20a8 8 0 110-16 8 8 0 010 16zM12 12l4-3",
    "map": "M9 4l6 2 5-2v14l-5 2-6-2-5 2V6zM9 4v14M15 6v14",
    "route": "M6 4v9a4 4 0 004 4h5M15 17l-2-2M15 17l-2 2M18 4a2 2 0 11-.001 4.001A2 2 0 0118 4z",
    "shield": "M12 3l7 3v6c0 4.4-2.9 7.6-7 9-4.1-1.4-7-4.6-7-9V6z",
    "scale": "M12 4v16M6 8h12M6 8l-3 6h6zM18 8l-3 6h6z",
    "intel": "M12 5c5 0 9 4 9 7s-4 7-9 7-9-4-9-7 4-7 9-7zM12 9.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z",
    "gear": "M12 15.5a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM12 2l1.6 2.3 2.8-.4.5 2.7 2.6 1.2-1.1 2.6 1.1 2.6-2.6 1.2-.5 2.7-2.8-.4L12 22l-1.6-2.3-2.8.4-.5-2.7-2.6-1.2L5.6 13 4.5 10.4l2.6-1.2.5-2.7 2.8.4z",
    "history": "M12 7v5l3 2M3.5 12a8.5 8.5 0 1 0 2.6-6.1M3 4v4h4",
    "gap": "M4 12h5M15 12h5M12 4v5M12 15v5",
    "source": "M4 6h16M4 12h16M4 18h10",
}

LINK_RULE = """
/* ── تمييز الروابط داخل النص (WCAG 2.1 AA — 1.4.1) ──
   عطل ك-72: تساوي الخصوصية يُحسم بالترتيب، فالقاعدة تُركَّب آخر كل الأنماط لتفوز. */
.site-nav a,.sn-links a,.sn-foot a,.foot a,footer a,.glossary a,p a,li a,td a,
.src a,.src-note a,.cite-ref{text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px}
"""
STYLE = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-padding-top:74px}
body{
  margin:0;background:var(--bg);color:var(--ink);
  font-family:"IBM Plex Sans Arabic","Noto Kufi Arabic","Segoe UI","Tahoma",system-ui,sans-serif;
  font-size:16.5px;line-height:1.95;text-rendering:optimizeLegibility;
}
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(1100px 520px at 88% -12%, rgba(34,195,182,.09), transparent 60%),
    radial-gradient(900px 480px at 6% 4%, rgba(77,157,255,.06), transparent 62%);
}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
section.doc p,section.doc li,.card p,.src,.foot,.notice,blockquote{overflow-wrap:anywhere}
a:focus-visible,.btn:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:4px}
.wrap{position:relative;z-index:1;max-width:1180px;margin:0 auto;padding:0 22px 90px}

/* عزل القيم اللاتينية والرقمية المركبة داخل سياق عربي */
bdi,.bidi{direction:ltr;unicode-bidi:isolate}
.k-v,.chip b,.cite-ref,.bar-row .bv,td.num,th.num{direction:ltr;unicode-bidi:isolate;white-space:nowrap}
.ev-code,.bidi.ev-code{direction:ltr;unicode-bidi:isolate;white-space:nowrap}  /* رمز الحدث لا يُكسر بين سطرين */
a.bidi{white-space:normal}
.eng{direction:ltr;unicode-bidi:plaintext;overflow-wrap:anywhere}

/* ---------- الشريط العلوي ---------- */
.topbar{
  position:sticky;top:0;z-index:30;backdrop-filter:blur(14px);
  background:linear-gradient(180deg,rgba(6,11,20,.95),rgba(6,11,20,.82));
  border-bottom:1px solid var(--line);
}
.topbar-inner{max-width:1180px;margin:0 auto;padding:11px 22px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;transition:padding .18s ease}
.topbar.is-compact .topbar-inner{padding:4px 22px}
.site-nav.is-compact{--sn-pad:2px}
.site-nav.is-compact .site-nav-inner{padding-block:3px !important}
.site-nav.is-compact .sn-sub,.site-nav.is-compact .sn-brand-sub{display:none}
.topbar.is-compact .brand-sub,.topbar.is-compact .tb-meta{display:none}
.topbar.is-compact .brand-mark{width:24px;height:24px}
.topbar.is-compact .brand-mark svg{width:14px;height:14px}
.hmap,.hmap-panel,section[id]{scroll-margin-top:64px}
.brand{display:flex;align-items:center;gap:11px;min-width:0}
.brand-mark{
  width:34px;height:34px;border-radius:10px;flex:0 0 auto;display:grid;place-items:center;
  background:rgba(34,195,182,.10);border:1px solid var(--line-2);color:var(--accent)
}
.brand-mark svg{width:21px;height:21px;line-height:21px;height:19px}
.brand-title{font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:15px;line-height:1.4}
.brand-sub{font-size:12px;color:var(--muted);line-height:1.4}
.topbar-spacer{flex:1 1 auto}
.tb-meta{display:flex;gap:9px;align-items:center;flex-wrap:wrap}
.chip{
  font-size:12px;color:var(--ink-2);border:1px solid var(--line);
  background:var(--panel);border-radius:999px;padding:5px 11px
}
.chip b{color:var(--ink);font-weight:600}
.btn{
  font:inherit;font-size:12.5px;cursor:pointer;color:var(--ink);
  background:var(--panel-2);border:1px solid var(--line-2);border-radius:8px;
  padding:7px 13px;transition:background .18s ease,transform .18s ease
}
.btn:hover{background:var(--panel-3)}
.btn:active{transform:translateY(1px)}
.btn-primary{background:var(--accent);color:var(--accent-ink);border-color:transparent;font-weight:600}
.btn-primary:hover{background:#2ad4c6}

/* ---------- الترويسة ---------- */
.masthead{padding:34px 0 6px;display:flex;gap:22px;align-items:flex-end;flex-wrap:wrap}
.masthead h1{
  font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;
  font-size:clamp(26px,3.4vw,40px);line-height:1.3;margin:0 0 8px;
  flex:0 0 100%;width:100%;text-align:center
}
.masthead > div:not(.threat){flex:1 0 100%}
.masthead .lede{color:var(--ink-2);font-size:15px;max-width:none;margin:0}
.masthead-meta{display:flex;gap:9px;flex-wrap:wrap;margin-top:14px}
.threat{
  margin-inline-start:0;margin-inline-end:auto;text-align:center;border-radius:var(--radius);
  border:1px solid var(--line-2);background:var(--panel);padding:14px 20px;min-width:172px
}
.threat .lbl{font-size:12px;color:var(--muted)}
.threat .val{font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;font-size:23px;line-height:1.45;margin-top:2px}
.threat.risk-high .val{color:var(--danger)}
.threat.risk-med .val{color:var(--warn)}
.threat.risk-low .val{color:var(--ok)}

/* ---------- شريط المؤشرات ---------- */
.kpis{display:grid;gap:16px;margin:24px 0 8px;direction:rtl}
.kpi-row{display:grid;gap:16px;direction:rtl}
.kpi-row-1{grid-template-columns:repeat(4,minmax(0,1fr))}
.kpi-row-2{grid-template-columns:repeat(4,minmax(0,1fr))}
.kpi{
  background:var(--panel-2);border:1px solid var(--line);border-radius:var(--radius);
  padding:15px 16px;position:relative;overflow:hidden;height:148px;min-height:148px;
  display:flex;flex-direction:column;text-align:right;direction:rtl
}
.kpi em{position:absolute;inset-inline-start:0;top:0;bottom:0;width:3px;background:var(--accent)}
.kpi.acc-info em{background:var(--info)}
.kpi.acc-warn em{background:var(--warn)}
.kpi.acc-danger em{background:var(--danger)}
.kpi.acc-ok em{background:var(--ok)}
.kpi .k-l{font-size:12.5px;color:var(--muted);line-height:1.6;min-height:2.6em}
.kpi .k-tag{display:inline-block;margin-inline-start:6px;padding:1px 7px;border:1px solid var(--line-2);border-radius:999px;color:var(--ink-2);font-size:12px;line-height:1.4;white-space:nowrap}
.kpi .k-v{font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:30px;line-height:1.25;margin-top:3px;font-variant-numeric:tabular-nums;text-align:right;direction:rtl}
.kpi .k-lays{display:flex;flex-wrap:wrap;gap:4px 10px;margin:4px 0 0;font-size:12.5px;color:var(--muted)}
.k-lay{display:inline-flex;gap:4px;align-items:baseline}
.k-lay-l{color:var(--muted)}
.k-lay b{color:var(--ink);font-weight:700}
.k-n{font-size:12px;color:var(--muted);line-height:1.7;margin-top:4px}
.k-risk-patterns{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:-8px 0 0;color:var(--muted);font-size:12px}
.k-risk-tag{border:1px solid var(--line-2);border-radius:999px;padding:1px 8px;color:var(--ink-2)}

.notice{
  display:flex;gap:12px;align-items:flex-start;margin:20px 0 6px;padding:13px 16px;
  border:1px solid var(--line);border-inline-start:3px solid var(--accent);
  border-radius:var(--radius-sm);background:rgba(34,195,182,.05);
  font-size:13.5px;color:var(--ink-2)
}
.notice svg{width:18px;height:18px;color:var(--accent);flex:0 0 auto;margin-top:5px}

/* ---------- الأقسام ---------- */
main{margin-top:30px;display:grid;gap:18px;min-width:0}
section.doc{
  background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px 24px 10px;min-width:0;max-width:100%;scroll-margin-top:74px
}
section.doc.pri{box-shadow:inset 0 2px 0 0 rgba(34,195,182,.55)}
section.doc > h2{
  font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:21px;line-height:1.5;
  margin:0 0 4px;display:flex;align-items:center;gap:11px
}
section.doc > h2 .ico{width:24px;height:24px;flex:0 0 auto;display:grid;place-items:center;color:var(--accent)}
section.doc > h2 .ico svg{width:18px;height:18px}
.h-rule{height:1px;background:var(--line);margin:8px 0 12px}
section.doc h3{
  font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:16.5px;
  margin:22px 0 6px;line-height:1.6;color:var(--ink)
}
section.doc p{margin:10px 0;color:var(--ink-2)}
section.doc strong{color:var(--ink);font-weight:600}
section.doc code{font-family:"IBM Plex Mono",monospace;font-size:.92em;color:var(--ink);background:var(--panel-3);padding:1px 5px;border-radius:4px}
ul,ol{margin:10px 0;padding-inline-start:22px;color:var(--ink-2)}
li{margin:7px 0}
section.doc ul ul{margin:6px 0;padding-inline-start:18px}
section.doc ul ul li{margin:4px 0;font-size:.96em;color:var(--ink-2)}
li::marker{color:var(--accent)}
blockquote{
  margin:16px 0;padding:12px 16px;border-inline-start:3px solid var(--accent);
  background:rgba(34,195,182,.055);border-radius:0 var(--radius-sm) var(--radius-sm) 0;
  color:var(--ink-2);font-size:15px
}
hr{border:0;border-top:1px solid var(--line);margin:20px 0}

/* ---------- بطاقات الوقائع ---------- */
.cards{display:grid;gap:14px;margin:16px 0 20px}
.card{border:1px solid var(--line);border-radius:var(--radius);background:var(--panel-2);padding:16px 18px}
.card-head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:6px}
.card-head h3{font-family:"Noto Kufi Arabic",sans-serif;font-size:16px;font-weight:600;margin:0;line-height:1.6;color:var(--ink)}
.tag{font-size:12.5px;border-radius:999px;padding:3px 10px;border:1px solid var(--line-2);color:var(--ink-2);background:var(--panel-3);white-space:nowrap}
.tag.t-confirm{color:#ffd7d3;background:rgba(255,93,82,.16);border-color:rgba(255,93,82,.42)}
.tag.t-suspect{color:#ffe6bd;background:rgba(255,176,46,.15);border-color:rgba(255,176,46,.40)}
.tag.t-inter{color:#d5e6ff;background:rgba(77,157,255,.15);border-color:rgba(77,157,255,.40)}
.card p{font-size:15px;margin:8px 0}

/* ---------- الجداول ---------- */
.tbl-wrap{overflow-x:auto;margin:16px 0 22px;border:1px solid var(--line);border-radius:var(--radius-sm);max-width:100%}
table{width:100%;border-collapse:collapse;font-size:14.5px;min-width:480px}
thead th{
  background:var(--panel-3);color:var(--ink);font-weight:600;text-align:start;
  padding:11px 13px;border-bottom:1px solid var(--line-2);white-space:nowrap
}
tbody td{padding:10px 13px;border-bottom:1px solid var(--line);color:var(--ink-2);vertical-align:top}
tbody tr:last-child td{border-bottom:0}
tbody tr:nth-child(even){background:rgba(255,255,255,.015)}
tbody tr:hover{background:rgba(34,195,182,.05)}
td.num,th.num{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;text-align:end;white-space:nowrap;color:var(--ink)}
tbody tr.total td{background:rgba(34,195,182,.09);color:var(--ink);font-weight:600}

/* ---------- المخططات ---------- */
.viz{margin:18px 0 24px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel-2);padding:18px}
.viz h3{
  margin:0 0 14px;font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;
  font-size:15px;color:var(--ink-2)
}
.bar-row{display:grid;grid-template-columns:minmax(150px,1.05fr) 3fr 108px;gap:14px;align-items:center;margin:11px 0}
.bar-row .bl{font-size:13.5px;color:var(--ink-2);line-height:1.55}
.bar-track{height:9px;border-radius:999px;background:var(--panel-3);overflow:hidden}
.bar-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#1fbfb2,#5ad6c8);width:var(--w,0);animation:grow 1s cubic-bezier(.22,.8,.28,1) both}
@keyframes grow{from{width:0}}
.bar-row .bv{font-family:"IBM Plex Mono",monospace;font-size:12.5px;text-align:end;color:var(--ink);font-variant-numeric:tabular-nums}
.viz .src-note{font-size:12.5px;color:var(--muted);margin:12px 0 0}

/* ---------- خريطة الوقائع ---------- */
.map-wrap{border:1px solid var(--line-2);border-radius:var(--radius-sm);overflow:hidden;background:var(--map-sea);margin-top:6px}
.map-svg{display:block;width:100%;height:auto;max-width:100%}
.mp-sea-bg{fill:var(--map-sea)}
.mp-grid line{stroke:var(--map-grid);stroke-width:.7;vector-effect:non-scaling-stroke}
.mp-grid-lbl{font-family:"IBM Plex Mono",monospace;font-size:12px;fill:var(--map-grid-lbl);direction:ltr;unicode-bidi:isolate}
.mp-land path{fill:var(--map-land);stroke:var(--map-coast);stroke-width:1.2;vector-effect:non-scaling-stroke}
.mp-borders path{fill:none;stroke:var(--map-border);stroke-width:.9;stroke-dasharray:6 5;vector-effect:non-scaling-stroke}
.mp-places text{font-family:"IBM Plex Sans Arabic","Noto Kufi Arabic",sans-serif;dominant-baseline:middle;text-anchor:middle}
.mp-port-dot{fill:var(--map-label)}
.mp-port-lbl{fill:var(--map-label);font-size:14px;direction:rtl;unicode-bidi:isolate}
.mp-country{fill:var(--map-country);font-size:15px;letter-spacing:0;direction:rtl;unicode-bidi:isolate}
.mp-sea-lbl{fill:var(--map-sea-label);letter-spacing:0;direction:rtl;unicode-bidi:isolate}
.mp-key{grid-template-columns:repeat(2,minmax(0,1fr))}
.mp-key li{display:flex;align-items:center;gap:9px;font-size:12.5px;color:var(--faint)}
.mp-key .lg-sw{width:22px;height:14px;border-radius:3px;display:inline-block;flex:0 0 auto;border:1px solid var(--line-2)}
.sw-land{background:var(--map-land);border-color:var(--map-coast)}
.sw-sea{background:var(--map-sea)}
.sw-border{border:0;border-top:2px dashed var(--map-border);height:0}
.sw-grid{border:0;border-top:1px solid var(--map-grid-lbl);height:0}
.sw-port{background:none;border:0;position:relative}
.sw-port::after{content:"";position:absolute;inset:4px 9px;background:var(--map-label);border-radius:50%}
.sw-strait{background:none;border:0}
.sw-strait::after{content:"مضيق";color:var(--map-strait);font-weight:700;font-size:12px}
.mp-key .sw-strait{width:auto;height:auto;padding:1px 6px;border:1px solid var(--map-strait);border-radius:999px;background:none}
.mp-key .sw-strait::after{font-size:10.5px;line-height:1.35;white-space:nowrap}
.sw-none{border:1px dashed var(--faint);background:none}
.mp-key .lg-none{grid-column:1 / -1;color:var(--ink-2)}
.hmap-zstrip{margin:14px 0 0;border-top:1px solid var(--line-2);padding-top:12px}
.hmap-zstrip h4{margin:0 0 10px;font-size:13px;color:var(--ink-2)}
.hmap-zstrip ul{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.hmap-zstrip li{border:1px solid var(--line-2);border-radius:var(--radius-sm);padding:10px;background:var(--panel-2);display:grid;gap:6px}
.hmap-zstrip .zs-id{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--faint)}
.hmap-zstrip .zs-nm{font-size:12.5px;color:var(--ink-2);line-height:1.5}
.hmap-zstrip .zs-lv{font-size:12.5px;font-weight:600}
.hmap-zstrip .zs-c{font-size:12px;color:var(--faint)}
.hmap-zstrip .zs-p{white-space:nowrap}
@media (max-width:1000px){.hmap-zstrip ul{grid-template-columns:repeat(2,minmax(0,1fr))}}
.mp-sea-lg{font-size:19px}
.mp-sea-sm{font-size:15px;font-weight:600;fill:var(--map-strait);letter-spacing:0}
.mp-events .mp-halo{fill:var(--mk);opacity:.22}
.mp-events .mp-dot{fill:var(--mk);stroke:var(--bg);stroke-width:2.2;vector-effect:non-scaling-stroke}
.mp-approx .mp-dot{fill:none !important;stroke:var(--mk);stroke-width:2.4;stroke-dasharray:3.5 2.5}
.mp-events .mp-num{font-family:"IBM Plex Mono",monospace;font-size:9.5px;font-weight:600;fill:#fff;text-anchor:middle}
.map-keys{font-size:12.5px;color:var(--faint);margin:12px 0 0}
.map-legend{list-style:none;display:grid;gap:7px;margin:14px 0 0;padding:0}
.map-legend li{display:flex;gap:10px;align-items:baseline;font-size:13.5px;color:var(--ink-2);margin:0}
.lg-num{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:600;color:#fff;background:var(--mk);border-radius:999px;width:19px;height:19px;flex:0 0 auto;display:grid;place-items:center;flex:0 0 auto}
/* ---------- خريطة الشاشة العليا: للشاشة فقط، تُحجب في الطباعة وWord بصنف no-print ---------- */
.hero-map{margin:22px 0 6px}
.hmap,.hmap-panel{margin:0;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel-2);padding:18px}
.hmap h3,.hmap-panel h3{margin:0 0 14px;font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:15px;color:var(--ink-2)}
.hmap .blk-lede{display:none}
.hmap-keys{font-size:12.5px;line-height:1.65;color:var(--muted);margin:8px 0 0}
.hmap .map-key,.hmap-panel .map-key{margin-top:10px}
.hmap-wrap{position:relative;border:1px solid var(--line-2);border-radius:var(--radius-sm);overflow:hidden;background:var(--map-sea)}
/* التكبير بجانب الخريطة لا فوقها: الشريحة كانت تحجب الخليج العربي (البحرين وقطر) */
.hmap-wrap{display:grid;grid-template-columns:minmax(0,1fr);align-items:start}
/* ك-XXX: عمود التكبير لا يُحجز إلا إذا وُجدت لوحته فعلًا، وإلا بقي 29% من العرض فارغًا */
.hmap-wrap:has(> .hmap-zoom){grid-template-columns:minmax(0,2.4fr) minmax(0,1fr)}
.hmap-zoom{border-inline-start:1.5px solid var(--accent);background:var(--map-sea);min-width:0;align-self:stretch;display:flex;flex-direction:column}
.hmap-zsvg{display:block;width:100%;height:auto}
.hz-cap{font-size:13px;color:var(--ink-2);background:var(--panel);padding:4px 10px;border-top:1px solid var(--line-2);margin-top:auto}
.hmap-imo-reference{margin:7px 0 0;padding-top:6px;border-top:1px solid var(--line-2);font-size:12px;line-height:1.5;color:var(--muted)}
.hmap-imo-reference .bidi{font-family:"IBM Plex Mono",monospace;color:var(--ink-2);font-variant-numeric:tabular-nums}
@media (max-width:1000px){.hmap-wrap,.hmap-wrap:has(> .hmap-zoom){grid-template-columns:minmax(0,1fr)}.hmap-zoom{border-inline-start:0;border-top:1.5px solid var(--accent)}}
.hmap-svg{display:block;width:100%;height:auto;max-width:100%}
/* خريطة الشاشة: علامات وتسميات أكبر قليلًا للقراءة من مسافة */
.hmap-svg .mp-dot{r:9.5px}
.hmap-svg .mp-halo{r:24px}
.hmap-svg .mp-events .mp-num{font-size:24px}
.hmap-svg .mp-badge-r{fill:rgba(6,11,20,.88);stroke:var(--mk);stroke-width:1.6}
.hmap-svg .mp-badge-t{font-family:"IBM Plex Mono",monospace;direction:ltr;unicode-bidi:isolate}
.hmap-scroll-hint{display:none;font-size:12.5px;color:var(--muted);margin:6px 0 0}
.hmap-decide{list-style:none;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:0 0 12px;padding:0}
.hmap-decide li{border:1px solid var(--line-2);border-radius:var(--radius-sm);background:var(--panel);padding:8px 11px;display:grid;gap:3px}
.hmap-decide .mds-k{font-size:12px;color:var(--muted)}
.hmap-decide .mds-v{font-size:13.5px;color:var(--ink);font-weight:600;line-height:1.5}
@media (max-width:1000px){.hmap-decide{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:560px){.hmap-decide{grid-template-columns:minmax(0,1fr)}}
.hmap .mp-grid-lbl,.hmap-panel .mp-grid-lbl{font-size:18px}
.hmap .mp-port-lbl,.hmap-panel .mp-port-lbl{font-size:19px}
.hmap .mp-country,.hmap-panel .mp-country{font-size:19px}
.hmap-legend{list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 30px;margin:16px 0 0;padding:0}
.hmap-legend li{display:block;position:relative;padding-inline-start:34px;font-size:14px;line-height:1.85;color:var(--ink-2);margin:0}
.hmap-legend .lg-num{position:absolute;inset-inline-start:0;top:3px}
.hmap-legend .bidi{color:var(--muted);font-size:13px;white-space:nowrap}
@media (max-width:760px){.hmap-legend{grid-template-columns:minmax(0,1fr)}}
/* الجوال: الخريطة الرئيسية تُصغَّر كثيرًا فتكبر العلامات والتسميات لتبقى مقروءة (التفصيل في لوحة التكبير) */
@media (max-width:700px){
  /* ك-423: الجوال يعرض الخريطة بمقياس قراءة (سحب أفقي مقصود داخل الإطار) بدل تصغيرها إلى 0.30 */
  .hmap-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
  .hmap-wrap>.hmap-svg,.hmap-wrap>.hmap-zoom{min-width:640px}
  .hmap-scroll-hint{display:block}
  .hmap-svg .mp-dot{r:13px}.hmap-svg .mp-halo{r:26px}.hmap-svg .mp-events .mp-num{font-size:30px}
  .hmap-svg .mp-badge-t{font-size:28px}
  .hmap-svg .mp-port-lbl{font-size:36px}.hmap-svg .mp-country{font-size:36px}
  .hmap-svg .mp-sea-lg{font-size:40px}.hmap-svg .mp-sea-sm{font-size:34px}.hmap-svg .mp-grid-lbl{display:none}
  .hmap-svg .mp-sector-top rect{filter:drop-shadow(0 0 6px rgba(143,208,230,.35))}
  @media(max-width:900px){.hmap-svg .lbl-2{display:none}}
  @media(max-width:640px){.hmap-svg .lbl-3{display:none}}
  .sr-only{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
    clip:rect(0 0 0 0);white-space:nowrap;border:0}
  .mp-events-detail{margin-top:10px;border:1px solid var(--line,#243b57);border-radius:10px;padding:8px 10px}
  .mp-events-detail summary{cursor:pointer;font-weight:600}
  .mp-ev-table{width:100%;border-collapse:collapse;margin-top:8px;font-size:13.5px}
  .mp-ev-table th,.mp-ev-table td{border-bottom:1px solid var(--line,#243b57);padding:6px 8px;text-align:right;vertical-align:top}
  .mp-key .lg-sw.sw-zone{background:rgba(143,208,230,.25);border:1px dashed #8fd0e6}
  .mp-key .lg-sw.sw-tss{background:rgba(150,214,255,.20);border:1px dashed #9ad9ff}
  .mp-key .lg-sw.sw-route{background:#ffd479}
  .mp-key .lg-sw.sw-maritime{background:repeating-linear-gradient(90deg,#b6e7ff 0 4px,transparent 4px 8px)}
  .mp-key .lg-group{opacity:.9;font-weight:600}
}
/* ---------- الاستشهادات ---------- */
.cite-ref{
  display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:12.5px;
  color:var(--accent);background:rgba(34,195,182,.10);border:1px solid rgba(34,195,182,.34);
  border-radius:6px;padding:0 5px;margin-inline-start:3px;vertical-align:1px
}
.cite-ref:hover{background:rgba(34,195,182,.22);text-decoration:none}

/* ---------- المصادر ---------- */
.src-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin:14px 0 22px}
.src{border:1px solid var(--line);border-radius:var(--radius-sm);background:var(--panel-2);padding:11px 13px;font-size:13.5px;color:var(--ink-2)}
.src b{display:block;color:var(--ink);font-weight:600;font-size:14px;margin-bottom:3px}
.src .st{font-size:12px;color:var(--muted)}
.src.s-ok{border-inline-start:3px solid var(--ok)}
.src.s-none{border-inline-start:3px solid var(--info)}
.src.s-fail{border-inline-start:3px solid var(--danger)}
/* ---------- سجل الأحداث (قرار المالك 2026-10-29) ---------- */
.ev-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px;margin:16px 0 10px}
.ev{position:relative;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel-2);padding:14px 16px 13px;overflow:hidden}
.ev::before{content:"";position:absolute;inset-inline-start:0;top:0;bottom:0;width:3px;background:var(--info)}
.ev.b-official::before{background:var(--ok)}
.ev.b-media::before{background:#d9a441}
.ev.b-deny::before{background:var(--danger)}
.ev-top{display:flex;align-items:center;gap:8px;margin-bottom:9px;flex-wrap:wrap}
.ev-idx{font-variant-numeric:tabular-nums;font-size:12px;line-height:1;color:var(--muted);border:1px solid var(--line-2);border-radius:6px;padding:3px 6px}
.ev-code{font-size:12px;color:var(--muted);letter-spacing:.02em}
.ev-badge{margin-inline-start:auto;font-size:12.5px;line-height:1;padding:4px 10px;border-radius:999px;border:1px solid var(--line-2);color:var(--ink-2)}
.ev.b-official .ev-badge{border-color:rgba(34,195,182,.45);color:var(--ok)}
.ev.b-media .ev-badge{border-color:rgba(217,164,65,.5);color:#e0b45f}
.ev.b-deny .ev-badge{border-color:rgba(214,86,86,.45);color:#e88}
.ev-reliability{margin-inline-start:6px;font-size:12.5px;line-height:1;padding:4px 10px;border-radius:999px;white-space:normal;overflow-wrap:anywhere;max-width:100%;display:inline-block;border:1px solid var(--line-2);color:var(--ink-2);white-space:nowrap}
.ev-reliability[data-analytic-confidence="عالية"]{border-color:rgba(34,195,182,.4);color:#7fd7cf}
.ev-reliability[data-analytic-confidence="منخفضة"]{border-color:rgba(214,86,86,.35);color:#e0a0a0}
.ev-fold{margin-top:5px;font-size:12px;line-height:1.7;color:var(--muted)}
.ev-fold>summary{cursor:pointer;color:var(--info);font-size:12.5px}
.ev-fold>span{display:block;margin-top:3px;color:var(--ink-2);word-break:break-word}
.ev-fold>.ev-path{display:block;margin-top:3px;font-size:12.5px;color:var(--muted);word-break:break-all;direction:ltr;unicode-bidi:isolate}
.ev-what{margin:0;font-size:15.5px;line-height:1.8;color:var(--ink)}
.ev-meta{margin:10px 0 0;padding-top:8px;border-top:1px dashed var(--line);font-size:12.5px;line-height:1.75;color:var(--muted)}
.ev-meta .ev-k{display:block;font-size:12.5px;color:var(--muted);opacity:.85;margin-bottom:2px}
.ev-meta .ev-mv{display:block;color:var(--ink-2)}
.ev-field{margin:4px 0}
.ev-field .ev-link{color:#9fd0ff;text-decoration:underline;text-underline-offset:2px}
.ev-field .ev-link:hover,.ev-field .ev-link:focus{color:#cfe9ff}
.ev-branch{margin:12px 0 0;padding:10px 12px;border:1px solid rgba(77,157,255,.38);border-inline-start:3px solid var(--info);border-radius:8px;background:rgba(77,157,255,.06);font-size:12.5px;line-height:1.75}
section.doc .ev-branch code,.ev-branch code{font-size:1em}
.ev-branch-title{display:block;color:var(--info);font-weight:700;margin-bottom:3px}
.ev-branch-gap{margin:12px 0 0;padding:9px 12px;border:1px dashed rgba(255,176,46,.55);border-radius:8px;color:var(--warn);font-size:12.5px;line-height:1.7}
.ev-ledger-note{margin:8px 0 14px;padding:9px 12px;border-inline-start:3px solid var(--warn);background:rgba(255,176,46,.06);color:var(--muted);font-size:12.5px}
@media (max-width:820px){.ev-grid{grid-template-columns:1fr}}
.dg-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px;margin:16px 0 10px}
.dg{position:relative;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel-2);padding:14px 16px 13px;overflow:hidden}
.dg-top{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.dg-idx{font-variant-numeric:tabular-nums;font-size:12px;color:var(--muted);border:1px solid var(--line-2);border-radius:6px;padding:1px 6px}
.dg-t{font-size:14px;color:var(--ink)}
.dg-badge{margin-inline-start:auto;font-size:12.5px;line-height:1;padding:4px 10px;border-radius:999px;border:1px solid var(--line-2);color:var(--ink-2)}
.dg-body{margin:0 0 9px;font-size:13.5px;line-height:1.85;color:var(--ink-2)}
.dg-meta{display:flex;flex-direction:column;gap:5px;margin:0;padding-top:8px;border-top:1px dashed var(--line)}
.dg-f{display:grid;grid-template-columns:auto 1fr;gap:2px 8px;font-size:12.5px;line-height:1.7}
.dg-k{color:var(--muted);font-size:12.5px;opacity:.9}
.dg-v{color:var(--ink-2)}
@media (max-width:820px){.dg-grid{grid-template-columns:1fr}}

/* ---------- التذييل ---------- */
.foot{margin-top:34px;padding:20px 22px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);color:var(--muted);font-size:13.5px}
.foot b{color:var(--ink-2)}
/* قواعد العرض المعتمدة 12 أكتوبر 2026 (تعديلات المعاينة) — للتراجع: احذف السطرين التاليين */
.foot{display:none}
.method-note{display:none}

/* ---------- الحركة: دخول لطيف بالـCSS فقط، والمحتوى مرئي دائمًا ---------- */
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.masthead,.kpis{animation:rise .55s cubic-bezier(.22,.8,.28,1) both}
@media (prefers-reduced-motion: reduce){
  .masthead,.kpis,.bar-fill{animation:none}
}

@media (max-width:760px){
  body{font-size:16px}
  .wrap{padding:0 14px 70px}
  section.doc{padding:18px 15px 8px}
  .threat{margin-inline-start:0;width:100%}
  .kpi-row-1,.kpi-row-2{grid-template-columns:1fr;gap:12px}
  .bar-row{grid-template-columns:1fr auto;grid-template-areas:"l v" "t t";gap:6px 10px}
  .bar-row .bl{grid-area:l}
  .bar-row .bv{grid-area:v;text-align:start}
  .bar-track{grid-area:t;width:100%}
  table{font-size:14px}
}

/* ==================== نمط الطباعة A4 ==================== */
@page{size:A4;margin:14mm 12mm}
/* ---------- قواعد عرض معتمدة من تعديلات المعاينة (12 أكتوبر 2026) ---------- */
.notice,
.map-panel .src-note,
.map-keys,
.decision .dc-foot{display:none}

.sec-lede{font-size:13px;color:var(--muted);margin:0 0 16px;line-height:1.7;max-width:76ch}
.blk-lede{font-size:12.5px;color:var(--faint);margin:-6px 0 10px;line-height:1.6}

@media print{
  /* ك-255: بطاقة القرار على خلفية بيضاء في الطباعة */
  .card, .decision, .dc, .blk, .blk *{background-image:none !important}
  .card, .decision, .dc{background:#fff !important}
  /* ك-245: منع انقسام مفتاح الخريطة بين صفحتين في PDF */
  .map-key, .map-legend, .key-box, .mx-key,
  /* عطل 2026-10-28: كتلة الخريطة+المفتاح (~130–215مم) لا تجتمع في صفحة فتترك فراغًا مانعًا.
     الحكم: الكتلة تنقسم بين الرسم والمفتاح، وكلٌّ منهما لا ينقسم. */
  .print-map{break-inside:auto !important;page-break-inside:auto !important}
  /* الإطار نفسه ينقسم: الرسم (95مم) يبقى صحيحًا، والمفتاح يبقى كاملًا في صفحة واحدة */
  .print-map .hmap-wrap{break-inside:auto !important;page-break-inside:auto !important;overflow:visible !important}
  .print-map .hmap-svg{break-inside:avoid !important;page-break-inside:avoid !important}
  .print-map .hmap-legend{break-inside:avoid !important;page-break-inside:avoid !important}
  /* ك-245: المفتاح كامل في عمود واحد، وتلتصق كتلة الخريطة بذيل المحتوى */
  .print-map{display:block !important}
  .print-map .hmap-wrap{overflow:hidden !important}
  /* لا يُقيَّد ارتفاع الخريطة: القيد يقلّص عرضها فيسقط فحص العرض (70%) — ك-256 */
  .print-map .hmap-keys{display:block !important;margin:1.2mm 0 0;font-size:7.8pt;line-height:1.25}
  /* عطل 2026-10-28: المفتاح بعمود واحد بلغ 95مم فلم تجتمع الخريطة معه في صفحة،
     فبقي فراغ مانع (176مم). القرار: عمودان في الطباعة — المفتاح يبقى كاملًا وغير منقسم
     داخل الكتلة (break-inside:avoid) وتنخفض كتلته إلى ما يقارب النصف. */
  /* ك-298ج: المفتاح (36مم) لم يجد متسعًا في ذيل صفحة الخريطة فهبط لصفحة شبه فارغة.
     الحكم: ستة أعمدة وخط أصغر قليلًا — المفتاح يبقى كاملًا ويستقر في مكانه. */
  .print-map .hmap-legend{grid-template-columns:repeat(6,minmax(0,1fr)) !important;columns:6 !important;column-gap:2.6mm !important;gap:0 !important;margin:1mm 0 0}
  .print-map .hmap-legend li{break-inside:avoid !important;page-break-inside:avoid !important;margin:0 0 .15mm !important;font-size:6.5pt !important;line-height:1.12 !important}
  .print-map-distribution{break-inside:avoid !important;page-break-inside:avoid !important;margin-top:2mm}
  .print-map-distribution h3{font-size:10pt;margin:1.5mm 0 1mm}
  .print-map-distribution .dist-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.5mm}
  .print-map-distribution .dist-card{display:block !important;width:auto !important;margin:0 !important;padding:1.3mm 1.7mm;border:1px solid #cfd8e3;border-radius:1.2mm;background:#fff;color:#20303f;font-size:7.7pt;line-height:1.25;break-inside:avoid;page-break-inside:avoid}
  .print-map-distribution .dist-card b{display:block;color:#0a1524;font-size:8pt;margin-bottom:.5mm}
  .print-map-distribution .dist-card span{display:block}

  :root{
    --ink:#0a1524;--ink-2:#20303f;--muted:#4b5e73;--faint:#5c728c;
    --line:#8d9bad;--line-2:#5d6f84;--panel:#fff;--panel-2:#fff;--panel-3:#eef2f7;
    --accent:#0b6f66;--info:#1f5f9f;--danger:#9d2b25;--warn:#7d5200;--ok:#166b45;
    /* لوحة خريطة الطباعة المعتمدة (حزمة design-v1 — قرار المالك 2026-10-23): بحر أبيض ويابسة رمادية */
    --map-sea:#ffffff;--map-land:#dfe4ea;--map-coast:#3f4f63;--map-border:#7b8796;
    --map-grid:#d3d9e0;--map-grid-lbl:#4b5e73;--map-label:#0a1524;--map-country:#4b5e73;
    --map-sea-label:#4b5e73;--map-strait:#9d2b25;--map-marker-ring:#ffffff;--map-marker-ink:#ffffff;
  }
  body{background:#fff;color:#111;font-size:10.8pt;line-height:1.62}
  /* لا تُطبع المصادر والمراجع ولا ملحق موثوقية المصادر في نسخة PDF */
  #sec-16{display:none !important}
  p,li,blockquote,.sec-lede,.blk-lede,.note{orphans:3;widows:3}
  /* اقتصاد الورق: تُقاس الخريطة على ارتفاع صفحة واحدة مع عنوانها */
  /* الخريطة ينقسم إطارها فقط بين الرسم والمفتاح، فلا تبقى ورقة شبه فارغة */
  .map-viz{break-inside:auto;page-break-inside:auto}
  .map-viz svg{max-height:100mm;height:auto;break-inside:avoid;page-break-inside:avoid}
  .map-legend{break-inside:avoid;page-break-inside:avoid}
  /* إجبار: كتلة الخريطة تنقسم بين الرسم والمفتاح مهما وردت قاعدة أخصّ */
  #sec-03 .map-viz, .map-viz{break-inside:auto !important;page-break-inside:auto !important}
  .map-viz svg{break-inside:avoid !important;page-break-inside:avoid !important}
  .map-viz{padding:1.2mm 1.2mm}
  /* لا يُقسَّم مفتاح hmap في الطباعة؛ النسخة المطبوعة تعلن عمودًا واحدًا صراحةً */
  .map-legend{columns:2;column-gap:8mm}
  .map-legend li{break-inside:avoid;margin:0 0 1.4mm;font-size:9pt;line-height:1.45}
  .map-legend .lg-txt{font-size:9pt}
  .map-caption,.map-viz figcaption{margin-top:1.5mm;line-height:1.4}
  /* كثافة الصفحة: تقليل حشو الخلايا لتصبح الكتلة على مقاس الورقة */
  tbody td{padding:1.5mm 2.2mm !important}
  .sec-lede{margin:0 0 10px;line-height:1.55}
  section.doc{padding:0 0 3mm}
  .rmk,.glossary{break-inside:avoid;page-break-inside:avoid}
  /* انضباط بصري: خطوط فاصلة رقيقة بدل تظليل الصفوف */
  tbody tr:nth-child(even){background:#fff !important}
  tbody td{border-bottom:.4pt solid #e2e8f0}
  .kpi,.viz,.src,.card,.notice,.threat,.chip,.decision,.bar-track{border-radius:2.4mm}
  .threat{display:inline-block;min-width:52mm}
  .mp-events text{font-size:13.5px}
  /* أرقام علامات الخريطة: لا بد من تخصيص أعلى لأن قاعدة الشاشة أخصّ */
  .mp-events .mp-num{font-size:15px}
  .mp-events text{font-size:15px}
  /* لا تباعد أحرف على العربية داخل الخريطة (يفكّ الاتصال) */
  .mp-country,.mp-sea-lbl,.mp-port-lbl{letter-spacing:0}
  /* لا يُترك عنوان قسم في نهاية صفحة ومحتواه في التالية */
  .h-rule,.sec-lede{break-after:avoid;page-break-after:avoid}
  /* ضغط الغلاف: تقليل الفراغ في الصفحة الأولى */
  .masthead{padding:0 0 4mm}
  .masthead h1{margin:0 0 3mm}
  .threat{padding:4mm 6mm}
  .kpis{margin-top:3mm}
  .cls-banner{margin-top:3mm}
  body::before{display:none}
  .topbar,.no-print{display:none !important}
  .wrap{max-width:none;padding:0}
  a{color:#0a1524;text-decoration:none}
  section.doc{background:#fff;border:0;border-top:1px solid #cfd8e3;border-radius:0;padding:0 0 3mm;box-shadow:none;break-inside:auto;page-break-inside:auto}
  section.doc.pri{border-top:2px solid #0b6f66}
  section.doc > h2{font-size:13pt;color:#0a1524;break-after:avoid;page-break-after:avoid}
  section.doc > h2 .ico{display:none}
  section.doc h3{color:#0a1524;font-size:11pt;break-after:avoid;page-break-after:avoid}
  section.doc p,section.doc li,tbody td,.card p{color:#20303f}
  .masthead h1{color:#0a1524;font-size:21pt}
  .kpi,.viz,.src,.foot,.card,.notice{background:#fff;border-color:#cfd8e3;box-shadow:none}
  .kpi .k-v{color:#0a1524}
  .threat{background:#fff;border-color:#cfd8e3}
  .chip{background:#f6f8fb;border-color:#cfd8e3;color:#31465c}
  .chip b{color:#0a1524}
  .cite-ref{color:#0a1524;background:#f2f5f9;border-color:#b8c4d1}
  .tag{color:#31465c;background:#f6f8fb;border-color:#b8c4d1}
  .tag.t-confirm{color:#7a1d1a;background:#fff1f0;border-color:#c77973}
  .tag.t-suspect{color:#7c5000;background:#fff7e6;border-color:#c9a24f}
  .tag.t-inter{color:#1d4f87;background:#edf4ff;border-color:#8bb1dd}
  thead th{background:#eef2f7;color:#0a1524}
  .viz{background:#fbfcfe}
  .bar-track{background:#e6ecf3}
  .bar-fill{background:#0f8f86;animation:none}
  .masthead,.kpis{animation:none}
  .map-wrap{border-color:#c3cedb}
  .mp-events .mp-dot{stroke:#fff}
  .map-viz{break-inside:auto;page-break-inside:auto}
  .bar-row .bl,.bar-row .bv,.viz h3,.viz .src-note,.src,.src b,.src .st,.foot,.kpi .k-l,.kpi .k-n,.notice,.chip,.cite-ref,.tag{font-size:10.5pt;line-height:1.6}
  /* ك-256: البطاقات الكبيرة تنقسم بين الصفحات لتصفير الفراغ الداخلي؛ البطاقات الصغيرة تبقى موحّدة. */
  .card,.viz,.src,.table-row{break-inside:auto;page-break-inside:auto}
     /* ك-298: سجل الأحداث — عمود واحد وثبات البطاقة في الطباعة */
     /* ك-298ب: الشبكة لا تنقسم في طباعة Chromium — تُحوّل كتلًا عادية لتتدفّق البطاقات */
     /* ك-341: بطاقتان في السطر في الطباعة — تدفّق بلا تصغير خطوط ولا حذف محتوى */
     /* ك-341: بطاقتان في السطر في الطباعة — تدفّق بلا تصغير خطوط ولا حذف محتوى */
     .ev-grid{display:grid;grid-template-columns:1fr 1fr;gap:2.6mm;margin:4mm 0 0}
     .ev{display:block;margin:0;padding:3mm 3.4mm 2.8mm}
     .ev{display:block;margin:0 0 2mm;padding:2.2mm 2.6mm 2mm;break-inside:avoid;page-break-inside:avoid;opacity:1 !important;transform:none !important;animation:none !important;border-color:#c3cedb;background:#fff}
     .ev::before{width:4px;background:#0f8f86}
     .ev.b-media::before{background:#b8860b}
     .ev.b-deny::before{background:#9aa8ba}
     .ev-what{font-size:9.4pt;line-height:1.45;color:#12203a;margin:0}
     .ev-top{margin-bottom:1mm}
     .ev-meta{margin-top:1.1mm;padding-top:.9mm}
     .ev-meta{font-size:9pt;color:#4a5b73;border-top-color:#dbe3ec}
     .ev-idx,.ev-code,.ev-badge{font-size:9pt;color:#4a5b73;border-color:#c3cedb}
     .dg-grid{display:block;margin:4mm 0 0}
     .dg{display:block;margin:0 0 2mm;padding:2.4mm 2.8mm 2.2mm;break-inside:avoid;page-break-inside:avoid;border-color:#dbe3ec;background:#fff}
     .dg-top{margin-bottom:1.4mm}
     .dg-t{font-size:10pt}
     .dg-body{font-size:9.5pt;line-height:1.5;margin-bottom:1.4mm;color:#243447}
     .dg-meta{padding-top:1.2mm;border-top-color:#e4eaf1;gap:0}
     .dg-f{font-size:9pt;line-height:1.45;grid-template-columns:auto 1fr}
     .dg-k{font-size:8.6pt;color:#4a5b73}
     .dg-idx,.dg-badge{font-size:9pt;color:#4a5b73;border-color:#c3cedb}
  .kpi,.glossary,.rmk{break-inside:avoid;page-break-inside:avoid}
  .tbl-wrap{overflow:visible;break-inside:auto;page-break-inside:auto}
  table{min-width:0;font-size:10.5pt}
  thead{display:table-header-group}
  tbody tr{break-inside:avoid;page-break-inside:avoid}
  html.js .reveal{opacity:1 !important;transform:none !important;transition:none !important}

  .decision{background:#fff;border-color:#c3cedb}
  .decision .dc-title{color:#0b6f66}
  .dc-v{color:#0a1524}
  .dc-row.risk-high .dc-v{color:#9d2b25}
  .dc-row.risk-med .dc-v{color:#7d5200}
  .dc-row.risk-low .dc-v{color:#166b45}
  .dc-foot,.glossary{color:#4b5e73}
  .conf,.kstrip,.chg-tag,.st-badge,.ev-code,.cls-banner{font-size:10.5pt;background:#f6f8fb;border-color:#b8c4d1;color:#31465c}
  .conf.c-high{color:#14603f;background:#edfaf3;border-color:#7cc4a0}
  .conf.c-med{color:#7c5000;background:#fff8ea;border-color:#cfa95a}
  .conf.c-low{color:#1d4f87;background:#eff5ff;border-color:#8bb1dd}
  .kstrip.k-confirm,.st-badge.s-active{color:#7a1d1a;background:#fff1f0;border-color:#c77973}
  .kstrip.k-inter,.chg.c-new .chg-tag{color:#1d4f87;background:#edf4ff;border-color:#8bb1dd}
  .kstrip.k-suspect,.chg.c-reclassified .chg-tag,.cls-banner.c-restricted{color:#7c5000;background:#fff7e6;border-color:#c9a24f}
  .chg.c-closed .chg-tag,.st-badge.s-stable{color:#14603f;background:#edfaf3;border-color:#7cc4a0}
  .ev-code{color:#0b6f66;background:#effaf8;border-color:#7fc9c0}
  .tl-track{background:#e6ecf3}
  .tl-fill.k-confirm{background:#9d2b25}
  .tl-fill.k-inter{background:#1f5f9f}
  .tl-fill.k-suspect{background:#7d5200}
  .tl-fill.k-bg{background:#7f92a8}
  ul.d-kinds li::before{width:3px}
  .decision,.glossary{break-inside:avoid;page-break-inside:avoid}
  /* كتل التحليل الطويلة تُقسَّم بدل إفراغ ورقة كاملة */
  .tl-viz,.viz,.card{break-inside:auto !important;page-break-inside:auto !important}
  .tl-viz .tl-row,.viz svg,.card .kpi{break-inside:avoid;page-break-inside:avoid}
  .decision{animation:none}

  /* ===== سياسة التدفّق الموحّدة: تمنع الفراغات الداخلية (قرار 18 أكتوبر 2026) =====
     القاعدة: القِطَع الصغيرة محمية من الانقسام، والحاويات الكبيرة تتدفّق بحرية.
     فتُملأ كل ورقة قبل الانتقال، ولا تُدفع الكتل الكبيرة لإفراغ نصف ورقة. */
  *{break-inside:auto !important;page-break-inside:auto !important}
  tr,.kpi,.map-legend li,.glossary li,.dc-row,.ev-item,.chg-item{break-inside:avoid !important;page-break-inside:avoid !important}
  section.doc > h2,section.doc h3,section.doc h4,.h-rule,.sec-lede{break-after:avoid !important;page-break-after:avoid !important}
  thead{display:table-header-group}
  thead tr{break-after:avoid;page-break-after:avoid}
  p,li{orphans:2;widows:2}
  .map-viz svg{max-height:145mm !important;width:100%;height:auto;break-inside:avoid !important}
  .map-legend,.map-viz,.tbl-wrap,.changes,.decision,.viz,.card{break-inside:auto !important;page-break-inside:auto !important}
  /* ك-235: قاعدة مكرّرة كانت تنقض السطر 601 (auto) وتُعيد avoid، فتُنقل كتلة الخريطة كاملة فتُخلّف
     فراغًا قد يبلغ 206 مم في الصفحة السابقة. الرسم نفسه يبقى غير قابل للتجزئة (avoid على svg)،
     والحاوية والمفتاح يتدفّقان فيكتمل امتلاء الورقة. */
  .map-viz{break-inside:auto !important;page-break-inside:auto !important}
  /* Chromium لا يجزّئ حاويات grid/flex بين الصفحات، فتتدفّق هنا بترتيب inline-block
     يحفظ هيئة العمودين/البطاقات نفسها، مع السماح بالانقسام بين الصفحات */
  .wrap,.changes,.dc-grid,.kpis,.masthead,.map-legend,.src-grid,.glossary,.tl-viz,.viz,.card,.decision{display:block !important}
  /* عطل (2026-10-30): القاعدة العامة كانت تُظهر وسم <style> المحقون داخل الترويسة في الطباعة،
     فطُبع نص CSS داخل الصفحة الأولى. القياس الحي: display المحسوب لوسم style = inline-block في print.
     الإصلاح: استثناء العناصر غير المرئية + حارس صريح يمنع طباعتها. */
  .kpis > *,.masthead > *,.map-legend > li,.glossary > li,.src-grid > *{display:inline-block !important;vertical-align:top !important;width:48.5% !important;margin:0 0 2.5mm 1% !important;box-sizing:border-box !important}
  .kpis > style,.kpis > script,.kpis > template,.kpis > link,
  .masthead > style,.masthead > script,.masthead > template,.masthead > link,
  .src-grid > style,.src-grid > script,.src-grid > template,.src-grid > link,
  .map-legend > style,.map-legend > script,.glossary > style,.glossary > script{display:none !important}
  style,script,template,link,meta,title{display:none !important}
  .dc-grid > *,.dc-row{display:block !important;width:100% !important}
  /* ك-103: الوسم يُعوَّم والمحتوى كتلة قابلة للانقسام — فلا يُترك عنوان أو بطاقة يتيمة ولا فراغ أسفل الغلاف */
  .dc-row::after{content:"";display:block;clear:both}
  .dc-row > *:first-child{float:inline-start !important;display:block !important;width:26% !important}
  .dc-row > *:last-child{display:block !important;width:auto !important;margin-inline-start:27% !important}
  .changes > *{display:block !important;width:100% !important}
  .viz > *,.card > *{box-sizing:border-box}
  /* ضغط تباعد الأقسام: يوفّر نحو 40 مم فتنتقل نهاية التقرير إلى صفحتها السابقة */
  section.doc{padding:0 0 2.5mm !important}
  section.doc > h2{margin:3mm 0 1.5mm !important}
  .sec-lede{margin:0 0 2mm !important}
  .h-rule{margin:1mm 0 2mm !important}
  /* تشخيص: إلغاء كل قواعد منع الكسر لتحديد مصدر الفراغات */
  *{break-after:auto !important;break-before:auto !important}
  body,p,li,td,th{line-height:1.36 !important}
  /* overflow مخفي يمنع Chromium من تقسيم الحاوية بين الصفحات فتُدفع كاملة وتُفرّغ الورقة */
  *{overflow:visible !important}
  .map-viz svg{max-height:145mm !important;width:100%;height:auto}
  .masthead > div:not(.threat){display:block !important;width:100% !important;margin:0 !important}
  .masthead h1{width:100% !important}
  /* الغلاف ينتهي عند شريط التصنيف: أهم الأخبار المتعلقة بالأمن البحري تبدأ صفحة جديدة (يمنع العنوان اليتيم والفراغ) */
  .decision{break-inside:avoid !important;page-break-inside:avoid !important}
  .map-viz svg{max-height:145mm !important;width:100%;height:auto}
  /* القاعدة الأخص تأتي بعد سياسة التدفق العامة حتى لا تنقضها */
  .print-map{break-inside:avoid !important;page-break-inside:avoid !important}
  .print-map .hmap-wrap{break-inside:avoid !important;page-break-inside:avoid !important;overflow:hidden !important}
  .print-map .hmap-wrap{grid-template-columns:minmax(0,6fr) minmax(0,1fr) !important}
  .print-map .hmap-zoom{border-inline-start:1.5px solid var(--accent) !important;border-top:0 !important}
  /* عطل 2026-10-28: قاعدتان متعارضتان للمفتاح (عمود/عمودان) — أُلغيت الثانية.
     الحكم الواحد: عمودان في الطباعة، والكتلة لا تنقسم. */
  .print-map .hmap-legend{grid-template-columns:repeat(4,minmax(0,1fr)) !important;columns:4 !important;column-gap:3.5mm !important}
  .print-map .hmap-keys{display:block !important}
  /* محاذاة مضبوطة: تُغلق فراغات الجانبين في الفقرات والقوائم، ولا تمسّ العناوين والبطاقات */
  section.doc p,section.doc li,.sec-lede,.masthead .lede,.glossary li,.src-grid li,
  /* تصفير فقرات المتن والعناوين التمهيدية (قرار المالك 2026-10-22): يمنع الفراغ الجانبي */
  .sec-lede,section.doc p,.masthead p,.blk-lede,.note{text-align:justify !important;text-align-last:start !important;hyphens:none !important}
  /* لا يُترك عنوان بطاقة أو قسم وحده أسفل ورقة بلا مضمون (عطل ك-103) */
  section.decision > .dc-title,.card > h3,.viz > h3,section.doc > h2{break-after:avoid !important;page-break-after:avoid !important}
  .dc-grid,.dc-row,.dc-v,.dc-v ul{break-inside:auto !important;page-break-inside:auto !important}
  .dc-list li{break-inside:avoid !important;page-break-inside:avoid !important}
  /* تصفير كامل المتن بما فيه قيم أهم الأخبار المتعلقة بالأمن البحري (ك-105): البوابة تفحص الصفحة بوسائط print */
  .dc-list li,.chg-list li,.ev-list li,.map-caption,footer.foot,
  .dc-v,.dc-row,.dc-grid,.kv-v,.glossary li,.src-grid li{text-align:justify !important;
    text-align-last:start !important;hyphens:none !important;word-spacing:normal !important}
  section.doc h2,section.doc h3,section.doc h4,.h-rule,.chip,.kpi,.tag,.st-badge,
  .map-legend li,.conf,.cls-banner,.threat,.toc li,.ev-code{text-align:start !important}
  .map-panel{padding:2mm 2.5mm !important}
  .map-legend{margin-top:1.5mm !important}
  .map-legend li{margin:0 0 1mm !important;font-size:8.4pt !important;line-height:1.3 !important}
  .kpis > *{width:32% !important;padding:1.6mm 2mm !important;margin:0 0 1.5mm 1% !important}
  .kpis .k-v{font-size:14pt !important;margin:0.5mm 0 !important}
  .kpis .k-l{font-size:8.6pt !important;line-height:1.25 !important;min-height:0 !important}
  .kpis .k-m{font-size:7.6pt !important;line-height:1.25 !important}
  .kpis.hero-kpis{display:block !important;direction:rtl !important}
  .kpis.hero-kpis .k-risk-patterns{display:block !important;width:100% !important;margin:0 0 1.5mm !important}
  .kpis.hero-kpis .kpi-row{display:grid !important;gap:4mm !important;width:100% !important;margin:0 0 4mm !important;direction:rtl !important}
  .kpis.hero-kpis .kpi-row-1{grid-template-columns:repeat(4,minmax(0,1fr)) !important}
  .kpis.hero-kpis .kpi-row-2{grid-template-columns:repeat(4,minmax(0,1fr)) !important}
  .kpis.hero-kpis .kpi-row > .kpi{display:flex !important;width:auto !important;margin:0 !important;height:148px !important;min-height:148px !important;padding:1.6mm 2mm !important;break-inside:avoid !important;page-break-inside:avoid !important;text-align:right !important;direction:rtl !important}
  .kpis.hero-kpis .k-v{text-align:right !important;direction:rtl !important}
  .dc-grid{gap:1.5mm !important}
  section.doc{font-size:10.2pt !important}
  /* ك-395: استعادة ميزانية الصفحات بعد إضافة بطاقات المؤشرات؛ مسافات المتن فقط، بلا تصغير خط أو بطاقة */
  html body main section.doc{padding-bottom:1mm !important}
  html body main section.doc p{margin:1mm 0 !important}
  html body main section.doc ul,html body main section.doc ol{margin:.7mm 0 !important}
  html body main section.doc li{margin:.3mm 0 !important}
}

}

"""

SCRIPT = """
(function(){
  var tb = document.getElementById('btn-theme');
  if(tb) tb.addEventListener('click', function(){
    var on = document.body.classList.toggle('daylight');
    tb.textContent = on ? 'النمط الليلي' : 'النمط النهاري';
  });
})();
"""

# النمط النهاري: تباين مصحّح (كل نص صغير داكن على خلفية فاتحة)
DAYLIGHT = """
body.daylight{
  --bg:#eef2f7;--bg-2:#e7edf4;--panel:#ffffff;--panel-2:#ffffff;--panel-3:#eef2f7;
  --line:#d3dce7;--line-2:#b9c6d6;--ink:#0b1a2b;--ink-2:#31465c;--muted:#5a7086;--faint:#6b7f94;
  --accent:#0b6f66;--info:#1f5f9f;--danger:#a32a24;--warn:#8a5a00;--ok:#176b46;
}
body.daylight::before{display:none}
body.daylight .topbar{background:linear-gradient(180deg,rgba(255,255,255,.96),rgba(255,255,255,.85))}
body.daylight .btn-primary{background:#0b6f66;color:#ffffff}
body.daylight .cite-ref{color:#0b6f66;background:rgba(11,111,102,.07);border-color:rgba(11,111,102,.30)}
body.daylight .tag{color:#31465c;background:#f2f5f9;border-color:#c4d0dd}
body.daylight .tag.t-confirm{color:#7a1d1a;background:#fff1f0;border-color:#c77973}
body.daylight .tag.t-suspect{color:#7c5000;background:#fff7e6;border-color:#c9a24f}
body.daylight .tag.t-inter{color:#1d4f87;background:#edf4ff;border-color:#8bb1dd}
body.daylight .threat.risk-high .val{color:#a32a24}
body.daylight .map-legend li,body.daylight .lg-num{color:#31465c}
body.daylight .lg-num{color:#ffffff}
body.daylight .map-keys{color:#5a7086}
body.daylight .kpi em{opacity:.95}
"""


# ----------------------------------------------------------------------------
# أدوات
# ----------------------------------------------------------------------------
def esc(t) -> str:
    """هروب كامل يشمل علامات الاقتباس — صالح للنص وللصفات."""
    return html.escape(str(t), quote=True)


def isolate_dtg(t: str) -> str:
    """ك-171: عزل نطاقات DTG داخل bdi فلا ينعكس ترتيبها في سياق RTL."""
    import re as _re
    return _re.sub(r"(?<![\w\d])(\d{6}Z\s*[–-]\s*\d{6}Z)(?![\w])",
                   lambda m: f'<bdi class="bidi" dir="ltr">{m.group(1)}</bdi>', t)


def bdi(t: str) -> str:
    return f'<bdi class="bidi">{esc(t)}</bdi>'


def normalize_digits(s: str) -> str:
    """توحيد الأرقام العربية-الهندية والفارسية إلى أرقام لاتينية."""
    ar = "0123456789"
    fa = "۰۱۲۳۴۵۶۷۸۹"
    for i, d in enumerate(ar):
        s = s.replace(d, str(i))
    for i, d in enumerate(fa):
        s = s.replace(d, str(i))
    return s


def inline(text: str, defs: dict = None) -> str:
    """تحويل العناصر المضمّنة: عريض، مائل، كود، روابط، استشهادات."""
    if _REPORT_DATE and isinstance(text, str) and "{date}" in text:
        # ك-11-11ح: بعض حقول الواجهة تحمل العنصر النائب {date}، فيُعبّأ بتاريخ الإصدار.
        text = text.replace("{date}", _REPORT_DATE)
    if isinstance(text, dict) and "value" in text:
        # ك-11-11و: بعض حقول الواجهة كائنات معلنة {label, value}، فيُعرض حقل القيمة
        # لا الكائن الخام — ويبقى الفشل المغلق على أي شكل آخر غير معلن.
        text = text.get("value")
    assert_no_template_artifacts(text)
    t = esc(_public_text(text))
    t = isolate_dtg(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)([^*\n]+?)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(
        r"\[([^\]]+)\]\((https?://[^\)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        t,
    )
    # استشهادات [n] — تصبح رابطًا إن وُجد تعريف للمصدر
    def cite(m):
        n = m.group(1)
        url = (defs or {}).get(n)
        if url:
            return (
                f'<a class="cite-ref bidi" href="{esc(url)}" target="_blank" '
                f'rel="noopener noreferrer">[{n}]</a>'
            )
        return f'<span class="cite-ref bidi">[{n}]</span>'

    t = re.sub(r"(?<![\w\]])\[(\d{1,3})\](?!\()", cite, t)
    # عزل معرفات الحوادث المرقمة مثل #164 لمنع انقلابها داخل النص العربي
    t = re.sub(r"(?<![\w#])#(\d{1,4})(?![\w])", r'<bdi class="bidi">#\1</bdi>', t)
    # وسم درجة الثقة المعيارية [ثقة: عالية|متوسطة|منخفضة]
    t = re.sub(
        r"\[ثقة:\s*(عالية|مرتفعة|متوسطة|متوسط|منخفضة|ضعيفة)\]\s*",
        lambda m: BLK.conf_chip(m.group(1)),
        t,
    )
    # روابط عارية داخل النص
    t = re.sub(
        r"(?<![\"'>=])(https?://[^\s<]+?)(?=[\s،۔.,)]|$)",
        r'<a class="bidi" href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        t,
    )
    # إبقاء علامة الترقيم خارج آخر وسم نصي مع إزالة أي فراغ قبلها؛ فمستخرج
    # الأسطح يعامل حدود الوسوم كفواصل كتلية، وإدخال الترقيم داخل الوسم يفصل
    # الكلمة عن سياقها ويحوّل المستوى المتكرر إلى قالب زائف.
    t = re.sub(
        r"(?P<close></(?:strong|em|code|a|span|bdi)>)[ \t]*(?P<punc>[،؛:,.؟!])",
        r"\g<close>\g<punc>",
        t,
    )
    return t


_ZONE_DISPLAY_NAMES: dict[str, str] = {}


def _set_zone_display_names(meta: dict):
    """يضبط أسماء المناطق من البيانات الحاكمة قبل صياغة أي سطح ظاهر."""
    global _ZONE_DISPLAY_NAMES
    names = {}
    threat_zones = (meta or {}).get("threat_zones") or {}
    for zone in threat_zones.get("zones") or []:
        if not isinstance(zone, dict):
            continue
        zone_id = str(zone.get("id") or "").strip().upper()
        name = str(zone.get("name") or "").strip()
        if re.fullmatch(r"Z[1-5]", zone_id) and name:
            names[zone_id] = name
    top_id = str(threat_zones.get("top_zone_id") or "").strip().upper()
    top_name = str(threat_zones.get("top_zone") or "").strip()
    if re.fullmatch(r"Z[1-5]", top_id) and top_name:
        names.setdefault(top_id, top_name)
    _ZONE_DISPLAY_NAMES = names


def _public_text(value) -> str:
    """نص ظاهر للقارئ بلا رموز قطاعات أو ألفاظ محظورة في السطح العام."""
    text = _value_text(value)
    for zone_id, name in sorted(_ZONE_DISPLAY_NAMES.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(
            rf"(?<![A-Za-z0-9]){re.escape(zone_id)}\s*[—–-]\s*{re.escape(name)}",
            name,
            text,
        )
        text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(zone_id)}\b", name, text)
    text = re.sub(r"(?<![A-Za-z0-9])Z[1-5]\b\s*[—–-]?\s*", "", text)
    for source, replacement in (
        ("المواضع", "المواقع"),
        ("الموضع", "الموقع"),
        ("مواضع", "مواقع"),
        ("موضع", "موقع"),
        ("لا بلاغ", "لم يصدر بلاغ"),
        ("غير محدد المصدر", "غير معلوم المصدر"),
    ):
        text = text.replace(source, replacement)
    return re.sub(r"\s{2,}", " ", text).strip()


def icon(name: str) -> str:
    d = ICON_PATHS.get(name, ICON_PATHS["source"])
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        f'<path d="{d}"/></svg>'
    )


def split_table_row(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_sep(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s\-\:\|]+\|", line.strip()))


def cell_is_numeric(c: str) -> bool:
    c = normalize_digits(c.strip())
    return bool(re.fullmatch(r"[-+–]?[\d\.,]+%?", c))


def render_table(rows, defs):
    header, body = rows[0], rows[1:]
    if not any(h.strip() for h in header):
        raise BuildError("وجدت جدولًا بلا رؤوس أعمدة.")
    out = ['<div class="tbl-wrap"><table>', '<thead><tr>']
    for h in header:
        cls = "num" if cell_is_numeric(h) and header.index(h) > 0 else ""
        out.append(f'<th scope="col"{f" class=\"{cls}\"" if cls else ""}>{inline(h, defs)}</th>')
    out.append("</tr></thead><tbody>")
    for r in body:
        if len(r) != len(header):
            r = (r + [""] * len(header))[: len(header)]
        is_total = any("المجموع" in c for c in r)
        cls = ' class="total"' if is_total else ""
        out.append(f"<tr{cls}>")
        for i, c in enumerate(r):
            txt = inline(c, defs)
            if i > 0 and cell_is_numeric(c):
                out.append(f'<td class="num">{txt}</td>')
            else:
                out.append(f"<td>{txt}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def classify(text: str):
    """وسم البطاقة من التصنيف الصريح في النص نفسه؛ لا يُضيف معلومة."""
    m = re.search(r"التصنيف\s*:?\**\s*(.{0,90})", text)
    if m:
        seg = m.group(1)
        if re.search(r"هجوم\s*(مؤكد|مثبت)", seg):
            return ("هجوم مؤكد", "t-confirm")
        if re.search(r"تفاعل عسكري|تعطيل", seg):
            return ("واقعة عسكرية", "t-inter")
        if re.search(r"لم يتم التأكيد بعد|نشاط مشبوه|غير مؤكد|غير مثبت", seg):
            return ("لم يتم التأكيد بعد", "t-suspect")
        if re.search(r"خلفية|ليست واقعة", seg):
            return ("لا جديد", "t-bg")
    if re.search(r"هجوم\s*(مؤكد|مثبت)", text):
        return ("هجوم مؤكد", "t-confirm")
    if re.search(r"تفاعل عسكري|قوات عسكرية|تعطيل", text):
        return ("واقعة عسكرية", "t-inter")
    if re.search(r"نشاط مشبوه|لم يتم التأكيد بعد|مجهول", text):
        return ("لم يتم التأكيد بعد", "t-suspect")
    return ("خلفية", "t-bg")


def render_cards(blocks, defs):
    out = ['<div class="cards">']
    for head, body in blocks:
        joined = " ".join(body)
        tag_txt, tag_cls = classify(head + " " + joined)
        out.append('<div class="card reveal"><div class="card-head">')
        out.append(f'<span class="tag {tag_cls}">{esc(tag_txt)}</span>')
        out.append(f"<h3>{inline(head, defs)}</h3></div>")
        for ln in body:
            if ln.strip():
                out.append(f"<p>{inline(ln, defs)}</p>")
        out.append("</div>")
    out.append("</div>")
    return "\n".join(out)


def render_geo_viz(rows, defs):
    data = []
    for r in rows[1:]:
        if len(r) < 3 or "المجموع" in r[0]:
            continue
        pct_raw = normalize_digits(r[2]).replace(".", ".").replace(",", ".")
        m = re.search(r"\d+(?:\.\d+)?", pct_raw)
        if not m:
            continue
        pct = float(m.group(0))
        count = normalize_digits(re.sub(r"[^\d]", "", normalize_digits(r[1]))) or "—"
        data.append((r[0], pct, count))
    if not data:
        raise BuildError("جدول التوزيع الجغرافي للوقائع موجود لكن لا توجد صفوف رقمية قابلة للقراءة.")
    mx = max(d[1] for d in data) or 1
    rows_html = []
    for label, pct, count in data:
        w = max(2.0, pct / mx * 100.0)
        rows_html.append(
            '<div class="bar-row">'
            f'<div class="bl">{inline(label, defs)}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="--w:{w:.1f}%"></div></div>'
            f'<div class="bv bidi">{esc(count)} · {pct:.1f}%</div>'
            "</div>"
        )
    return (
        '<div class="viz reveal"><h3>حصيلة IMO حسب المنطقة</h3><p class="blk-lede">نسب الحوادث المؤكدة على قطاعات النطاق.</p>'
        + "\n".join(rows_html)
        + '<p class="src-note">المصدر: جدول التوزيع الجغرافي للوقائع في هذا التقرير. النسب لا تمثل أعداد هجمات مستقلة.</p></div>'
    )


def render_source_cards(rows, defs):
    if len(rows) < 2:
        return ""
    htxt = " ".join(rows[0])
    if not re.search(r"حالة|الفحص|المصدر|مصدر", htxt) or "القطاع" in htxt:
        return ""
    cards = ['<div class="src-grid">']
    for r in rows[1:]:
        if len(r) < 2:
            continue
        joined = " ".join(r)
        if re.search(r"تعذر|فشل|حجب", joined):
            cls, status = "s-fail", "تعذر الوصول"
        elif re.search(r"مفحوص|فُحص|فحص", joined):
            cls, status = "s-ok", "فُحص"
        else:
            cls, status = "s-none", "لا واقعة جديدة"
        note = r[-1] if len(r) > 2 else ""
        cards.append(
            f'<div class="src {cls}"><b>{inline(r[0], defs)}</b>'
            f'<span class="st">{esc(status)} — {inline(note, defs)}</span></div>'
        )
    cards.append("</div>")
    return "\n".join(cards)
# ----------------------------------------------------------------------------
# ك-303: مطابقة صارمة لجدول المصادر + عارض بيانات عام يحفظ كل الأعمدة
# ----------------------------------------------------------------------------
def is_source_status_table(header) -> bool:
    """جدول المصادر الحقيقي فقط: رقم + المصدر + حالة مقيسة + إجراء/رابط.

    ك-303: المطابقة السابقة كانت واسعة («المصدر» أو «حالة») فابتلعت جداول المحتوى
    («التوزيع الجغرافي للوقائع» و«الحركة الملاحية والتكدس») وأسقطت أعمدتها.
    """
    h = " ".join(header)
    has_num = ("#" in h) or ("الرقم" in h) or ("رقم" in h)
    has_src = "المصدر" in h
    has_state = ("الحالة المقيسة" in h) or ("حالة الفحص" in h) or ("الفحص" in h)
    has_act = ("الإجراء" in h) or ("الرابط" in h) or ("المسار" in h)
    return has_num and has_src and has_state and has_act


def _badge_header_index(header):
    """فهرس عمود الحالة إن وُجد، ليُعرض شارة لا حقلًا نصيًا مكررًا."""
    for i, h in enumerate(header):
        if "حالة" in h or "التأكيد" in h:
            return i
    return None


def render_data_grid(rows, defs):
    """بطاقة لكل صف: العنوان من الخلية الأولى، ونص القراءة من الثانية، ثم بقية الأعمدة موسومة بأسماء رؤوسها.

    ك-303: الغرض ألا يسقط أي عمود، وأن يُقرأ الصف بلا ازدحام أفقي.
    """
    body = [r for r in rows[1:] if any((c or "").strip() for c in r)]
    if not body:
        return ""
    header = [re.sub(r"\s+", " ", (h or "").strip()) for h in rows[0]]
    badge_i = _badge_header_index(header)
    out = ['<div class="dg-grid">']
    for n, r in enumerate(body, 1):
        r = list(r) + [""] * (len(header) - len(r))
        title = (r[0] or "").strip()
        text = (r[1] or "").strip() if len(r) > 1 else ""
        badge = (r[badge_i] or "").strip() if badge_i is not None else ""
        # ك-303: الشارة للحالات القصيرة فقط؛ والنص الطويل يصير حقلًا موسومًا،
        # وإذا تطابق نص الشارة مع نص القراءة يُعرض مرة واحدة.
        if badge and (len(badge) > 42 or badge == text):
            badge = ""
        fields = []
        for i, cell in enumerate(r):
            if i in (0, 1) or i == badge_i:
                continue
            val = (cell or "").strip()
            if not val:
                continue
            fields.append(
                f'<div class="dg-f"><span class="dg-k">{esc(header[i] if i < len(header) else "")}</span>'
                f'<span class="dg-v">{inline(val, defs)}</span></div>'
            )
        out.append(
            '<article class="dg">'
            '<div class="dg-top">'
            f'<span class="dg-idx">{n}</span>'
            f'<b class="dg-t">{inline(title, defs)}</b>'
            + (f'<span class="dg-badge">{inline(badge, defs)}</span>' if badge else "")
            + "</div>"
            + (f'<p class="dg-body">{inline(text, defs)}</p>' if text else "")
            + (f'<div class="dg-meta">{"".join(fields)}</div>' if fields else "")
            + "</article>"
        )
    out.append("</div>")
    return "\n".join(out)


# ----------------------------------------------------------------------------
# سجل الأحداث (قرار المالك 2026-10-29: نقل القسم إلى التقرير اليومي + تصميم بطاقات)
# ----------------------------------------------------------------------------
def is_events_table(header) -> bool:
    """جدول الوقائع/سجل الأحداث: رأس فيه «ما حدث» أو («الرمز» + «حالة التأكيد»)."""
    htxt = " ".join(header)
    return ("ما حدث" in htxt) or ("الرمز" in htxt and "حالة التأكيد" in htxt)

EVENT_BADGES = (
    (("نفي", "نفت", "نفى"), "b-deny"),
    (("نقل", "إعلامي", "رواية", "غير مؤكد", "لم يتأكد"), "b-media"),
    (("رسمي", "بلاغ"), "b-official"),
)

_PUBLIC_STATUS_REPLACEMENTS = None


def _public_status_replacements():
    """يقرأ بدائل العرض من السجل الحاكم، ولا يحمّل أسباب القرار إلى الصفحة."""
    global _PUBLIC_STATUS_REPLACEMENTS
    if _PUBLIC_STATUS_REPLACEMENTS is not None:
        return _PUBLIC_STATUS_REPLACEMENTS
    candidates = [
        _brain("appendices", "forbidden-coinages.json"),
        Path(__file__).resolve().parents[1] / "appendices" / "forbidden-coinages.json",
    ]
    pairs = {}
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        for entry in data.get("entries", []) if isinstance(data, dict) else []:
            if not isinstance(entry, dict):
                continue
            term = str(entry.get("term") or "").strip()
            replacement = str(entry.get("replacement") or "").strip()
            if term and replacement:
                pairs[term] = replacement
        if pairs:
            break
    _PUBLIC_STATUS_REPLACEMENTS = tuple(sorted(pairs.items(), key=lambda pair: len(pair[0]), reverse=True))
    return _PUBLIC_STATUS_REPLACEMENTS


def _public_status_text(value: str) -> str:
    public = value
    for term, replacement in _public_status_replacements():
        public = public.replace(term, replacement)
    return public

# ── عقد بطاقة «سجل الأحداث»: appendices/event-card-contract.md ────────────────
# عشرة صفوف ثابتة بالترتيب نفسه؛ المتغيّر قيمة الصف لا وجوده ولا اسمه.
CARD_ROWS = 9
ABSENCE = {
    "classification": "قيد التثبّت",
    "reliability": "غير مقيّمة",
    "time": "التوقيت غير مسجّل في المصدر",
    "place": "المنطقة كاملة",
    "source": "غير متاح",
    "source_url": "الرابط الرسمي غير مدرج في الدفتر",
    "translation": "الترجمة غير مدرجة في الدفتر",
    "excerpt": "لا نصّ خام في الدفتر",
    "excerpt_open": "مطويّ — افتح للعرض",
}
# ترتيب المطابقة إلزامي والأخصّ أولًا: «نفي رسمي منقول» يُقرأ نفيًا لا بلاغًا رسميًّا.
CLASSIFICATION_RULES = (
    ("نفي رسمي", ("نفي",)),
    ("بلاغ رسمي", ("بلاغ", "رسمي", "سجل دولي", "مؤسسي", "تقييم رسمي")),
    ("تقرير مهني", ("مهني", "تقرير", "سجل مصدر", "تقدير", "تحليل مؤسسي")),
    ("نقل إعلامي", ("إعلامي", "إعلام", "خبر", "وسم إعلامي", "تحليل إعلامي")),
    ("نقل سياسي", ("سياسي", "دبلوماسي", "حكومي")),
    ("رواية غير مؤكدة من طرف واحد", ("رواية", "ادعاء", "منقول", "نقل طرف", "بلا تأكيد", "تجميع غير رسمي")),
)
CLASSIFICATION_VALUES = tuple(label for label, _ in CLASSIFICATION_RULES) + ("غير مصنّف",)
RELIABILITY_VALUES = ("عالية", "متوسطة", "منخفضة")
BADGE_CLASSES = {
    "بلاغ رسمي": "b-official",
    "تقرير مهني": "b-official",
    "نقل إعلامي": "b-media",
    "نقل سياسي": "b-media",
    "رواية غير مؤكدة من طرف واحد": "b-media",
    "نفي رسمي": "b-deny",
    "غير مصنّف": "b-info",
    ABSENCE["classification"]: "b-info",
}

_SHORTLINK_RE = re.compile(r"https?://(?:t\.co|bit\.ly|lnkd\.in|tinyurl\.com|goo\.gl|ow\.ly|"
                           r"buff\.ly|is\.gd|cutt\.ly|rb\.gy)/\S+")
_HASHTAG_RE = re.compile(r"(?<!\w)#[A-Za-z0-9_\u0600-\u06ff]{2,}")
_CLICKBAIT_RE = re.compile(r"click here to read the full warning\.?", re.I)
_TIME_RE = re.compile(r"^\d{4}Z$")


def event_badge(value: str):
    """شارة التصنيف من القائمة المغلقة؛ القيمة الخام تُشتق ولا تُخمَّن فئة."""
    label = event_classification(value)
    return BADGE_CLASSES.get(label, "b-info"), label


def event_classification(raw) -> str:
    text = _public_status_text(_value_text(raw))
    if not text:
        return ABSENCE["classification"]
    for label, keys in CLASSIFICATION_RULES:
        if any(key in text for key in keys):
            return label
    return "غير مصنّف"


def confidence_label(event: dict) -> str:
    value = _value_text(event.get("confidence"))
    return value if value in RELIABILITY_VALUES else ABSENCE["reliability"]


def reliability_label(event: dict, meta: dict | None = None) -> str:
    """موثوقية المصادر المصرح بها في meta، مستقلة عن الثقة التحليلية للواقعة."""
    source_names = {
        part.strip() for part in re.split(r"\s*[؛;]\s*", _join_sources(event)) if part.strip()
    }
    reliability = (meta or {}).get("source_reliability") or {}
    rows = reliability.get("rows") if isinstance(reliability, dict) else None
    grades, seen = [], set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or _value_text(row.get("name")) not in source_names:
            continue
        rel = _value_text(row.get("source_reliability") or row.get("rel")).upper()
        cred = _value_text(row.get("information_credibility") or row.get("cred"))
        if re.fullmatch(r"[A-F]", rel) and cred in set("123456"):
            grade = f"{rel}/{cred}"
            if grade not in seen:
                grades.append(grade)
                seen.add(grade)
    return " · ".join(grades) or ABSENCE["reliability"]


def _looks_arabic(text) -> bool:
    letters = [char for char in str(text or "") if char.isalpha()]
    if not letters:
        return False
    arabic = sum(1 for char in letters if "\u0600" <= char <= "\u06ff")
    return arabic / len(letters) >= 0.5


def clean_excerpt(text) -> str:
    """تنظيف العرض لا التخزين: يبقى النص الخام في الدفتر للتدقيق."""
    value = _SHORTLINK_RE.sub("", _value_text(text))
    value = _HASHTAG_RE.sub("", value)
    value = _CLICKBAIT_RE.sub("", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip(" ·|,-—")


def attribution_from_path(path) -> str:
    """إسناد غير حساس للقارئ؛ المسار الكامل يبقى مطويًّا للتدقيق."""
    text = _value_text(path).lower()
    if not text:
        return ""
    if "feeds/" in text or "feed-" in text:
        return "من تغذية المصادر"
    if "official" in text or "imo" in text:
        return "من مصدر رسمي"
    return "من سجل داخلي"


def _field_row(index: int, label: str, value: str, defs, *, state: str = "shown",
               extra: str = "", attrs: str = "", raw: bool = False) -> str:
    """صف في البطاقة. raw=True يعني أن القيمة HTML جاهز (رابط) لا نصًّا يُهرَّب."""
    hidden = "" if state == "shown" else " hidden"
    body = value if raw else inline(value, defs)
    return (f'<div class="ev-field" data-row="{index}" data-row-state="{state}"{attrs}{hidden}>'
            f'<span class="ev-k">{esc(label)}</span>'
            f'<span class="ev-mv">{body}</span>{extra}</div>')

LIVE_EVENT_LEDGER_FROM = "2026-10-31"
RELATION_KEYS = ("update_of", "parent_id", "duplicate_of")
RELATION_MARKER_KEYS = ("event_kind", "update_of", "parent_id", "duplicate_of")
RELATION_KIND_FIELDS = {"تحديث": "update_of", "تكرار": "duplicate_of", "فرع تابع": "parent_id"}
RELATION_KIND_LABELS = {"تحديث": "تحديث لبلاغ", "تكرار": "تكرار لبلاغ", "فرع تابع": "فرع من بلاغ"}


def _daily_events_path(md_path: Path, report_date: str) -> Path:
    """مسار دفتر اليوم بجوار مصادر الموقع؛ لا يعتمد على مسار ثابت في النظام."""
    return Path(md_path).resolve().parents[2] / "sources" / "daily-events" / f"{report_date}.json"


def load_daily_events(md_path: Path, report_date: str):
    """يقرأ دفتر الفترة كما نُسخ من Brain، أو يعيد None عند غيابه."""
    path = _daily_events_path(md_path, report_date)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"دفتر أحداث الفترة غير صالح: {path.name}: {exc}") from exc
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise BuildError(f"دفتر أحداث الفترة يجب أن يكون قائمة سجلات: {path.name}")
    return value


def _value_text(value) -> str:
    if isinstance(value, list):
        text = " · ".join(str(x).strip() for x in value if str(x).strip())
    else:
        text = str(value or "").strip()
    # الاقتطاع في سجلات المصادر يُعرض بمحرف واحد؛ لا تُنقل ثلاث نقاط إلى السطح.
    return re.sub(r"\.{3,}", "…", text)


def _event_code(event: dict) -> str:
    return _value_text(event.get("code") or event.get("display_code") or event.get("event_id"))


def _event_date(event: dict) -> str:
    return _value_text(event.get("date") or event.get("date_start") or event.get("date_label"))


def _event_description(event: dict) -> str:
    return _value_text(event.get("title") or event.get("description"))


def _event_location(event: dict) -> str:
    missing = {"", "غير مكانية", "خارج القطاعات", "غير محددة", "غير محدد"}
    candidates = (
        event.get("zone_name"), event.get("area"), event.get("location"),
    )
    for raw in candidates:
        value = _public_text(raw)
        if value and value not in missing:
            return value
    return ""


def _join_sources(event: dict) -> str:
    """يجمع أسماء المصادر في سطر واحد بفواصل بلا تكرار (قرار المالك 2026-11-04).

    المصادر المكررة التي حملت الواقعة نفسها تُذكر كلها في صف المصدر، ولا يُسقَط
    اسم مصدر لأن بلاغه مكرر. الترتيب: قائمة sources ثم حقل source المفرد.
    """
    vals = []
    srcs = event.get("sources")
    if isinstance(srcs, (list, tuple)):
        for item in srcs:
            # المصدر الحاكم قد يحمل الاسم والمقتطف معًا؛ لا تُحوّل القاموس
            # إلى repr قابل للظهور على السطح، فذلك يسرّب أقواس القالب والنص
            # الداخلي بدل اسم المصدر الذي يقرأه القارئ.
            if isinstance(item, dict):
                item = item.get("name") or item.get("source") or item.get("label")
            value = _value_text(item)
            if value:
                vals.append(value)
    elif isinstance(srcs, str) and srcs.strip():
        vals.append(srcs.strip())
    base = _value_text(event.get("source"))
    if base:
        vals.append(base)
    seen, out = set(), []
    for value in vals:
        for part in re.split(r"\s*[؛;]\s*", value):
            part = part.strip(" ·—-،")
            if part and part not in seen:
                seen.add(part)
                out.append(part)
    return "؛ ".join(out)


def _event_sources(event: dict) -> str:
    raw = _join_sources(event)
    if not raw:
        return ""
    assert_no_template_artifacts(raw, "مصادر الواقعة")
    # تُستخرج الجهة الحقيقية من بداية المصدر أو من مسار المصدر الأصلي عند
    # ورود وسم وصفي مثل «نقل إعلامي تركي» بدل اسم الجهة.
    for marker in (" نقلًا عن ", " نقلاً عن ", " نقل عن "):
        if marker in raw:
            prefix = raw.split(marker, 1)[0].strip(" ·—-،")
            if prefix and "إعلام" not in prefix and "وسيلة" not in prefix:
                return _public_text(prefix)
    generic = re.search(r"نقل\s*(?:إعلامي|من وسيلة إعلام|عن وسائل|عن وسيلة)", raw)
    if generic:
        provenance = _value_text(event.get("source_excerpt_from"))
        match = re.search(r"\b\d+\.\s*([^·]+?)\s*·\s*item\b", provenance, flags=re.I)
        if match:
            candidate = match.group(1).strip()
            if candidate and "/" not in candidate and "feeds" not in candidate.lower():
                return _public_text(candidate)
        for key in ("source_name", "publisher", "outlet", "source_label"):
            candidate = _value_text(event.get(key))
            if candidate and not re.search(r"نقل\s*(?:إعلامي|من وسيلة إعلام)", candidate):
                return _public_text(candidate)
    return _public_text(raw)


def _event_time(event: dict) -> tuple[str, bool]:
    for key in ("time", "event_time", "occurred_at", "published_at"):
        value = _value_text(event.get(key))
        if value:
            return value, True
    return _event_date(event), False


def _all_event_records(md_path: Path, daily_events: list[dict]) -> dict[str, dict]:
    """فهرس اليوم مع الدفتر التراكمي لمطابقة مرجع سابق فقط إذا كان موجودًا."""
    root = Path(md_path).resolve().parents[2]
    records = list(daily_events)
    cumulative = root / "sources" / "ledger.json"
    if cumulative.is_file():
        try:
            raw = json.loads(cumulative.read_text(encoding="utf-8"))
            old = raw.get("events") if isinstance(raw, dict) else raw
            if isinstance(old, list):
                records.extend(x for x in old if isinstance(x, dict))
        except (OSError, json.JSONDecodeError):
            pass
    index = {}
    for event in records:
        for key in (_event_code(event), _value_text(event.get("event_id"))):
            if key and key not in index:
                index[key] = event
    return index


def _relation_info(event: dict, known: dict[str, dict]) -> tuple[bool, str, str]:
    """يعيد (معلّم كفرع، المرجع، الحقل) دون استنتاج من تشابه النص."""
    kind = _value_text(event.get("event_kind")).lower()
    marker = bool(kind and any(token in kind for token in ("update", "extension", "follow", "duplicate", "تحديث", "امتداد", "تابع", "نسخة")))
    for key in RELATION_KEYS:
        ref = _value_text(event.get(key))
        if ref:
            return True, ref, key
    # لا تُعامل link كرابط أب إلا إذا كان يحمل معرّفًا موجودًا؛ الرابط النصي
    # العام قد يكون رابط مصدر، ولا يجوز تحويله إلى علاقة بالتخمين.
    link = _value_text(event.get("link"))
    if link and link in known:
        return True, link, "link"
    return marker, "", "event_kind" if marker else ""


def _counts_as_new_false(value) -> bool:
    """يقبل القيمة المنطقية المطلوبة، مع تحمل تمثيل JSON النصي القديم."""
    return value is False or str(value or "").strip().lower() in {"false", "0", "no"}


def _is_cumulative_update(event: dict) -> bool:
    """سجل تحديث تراكمي يبقى في الدفتر ولا يتحول إلى بطاقة واقعة."""
    return _value_text(event.get("event_kind")).strip().lower() == "تحديث بيانات"


def _relation_display(event: dict, known: dict[str, dict]) -> tuple[str, str] | None:
    """يبني سطر العلاقة من العقد الصريح فقط، دون استنتاج أو نص غياب."""
    kind = _value_text(event.get("event_kind"))
    field = RELATION_KIND_FIELDS.get(kind)
    reference = _value_text(event.get(field)) if field else ""
    basis = _value_text(event.get("link_basis"))
    if not field or not reference or not basis:
        return None
    target = known.get(reference)
    target_code = _event_code(target) if target else reference
    if not target or not target_code or target_code == _event_code(event):
        return None
    text = f"{RELATION_KIND_LABELS[kind]}: `{target_code}` ({basis})"
    if _counts_as_new_false(event.get("counts_as_new")):
        text += " لا يُحتسب واقعة جديدة"
    return field, text


def _event_fields_html(event: dict, defs) -> tuple[str, bool]:
    """الصفوف 4–8 وفق العقد؛ الصفوف 1–3 في رأس البطاقة والصف 9 هو الفرع التابع."""
    date_text = _event_date(event) or "غير متاح"
    time_text = _value_text(event.get("time"))
    has_time = bool(time_text and _TIME_RE.match(time_text))
    time_kind = _value_text(event.get("time_kind")).lower()
    if has_time:
        date_line = f"{date_text} · {time_text}"
    elif time_kind in {"نشر", "نشر فقط", "published", "publication"}:
        date_line = f"{date_text} · وقت الواقعة غير متاح"
    else:
        date_line = date_text
    rows = [_field_row(4, "التاريخ والوقت", date_line, defs)]

    place = _event_location(event)
    if place:
        rows.append(_field_row(5, "الموقع", place, defs))
    else:
        rows.append(_field_row(5, "الموقع", "", defs, state="hidden-rule-no-location"))

    source_text = _event_sources(event) or ABSENCE["source"]
    evidence_ref = _value_text(event.get("evidence_ref"))
    source_url = (evidence_ref if evidence_ref.startswith("http")
                  else _value_text(event.get("source_url")))
    if source_url.startswith("http"):
        # ملاحظة المالك 2026-11-02: اسم المصدر رابطٌ يُدخل القارئ إلى مادة المصدر نفسها.
        link = (f'<a class="ev-link" href="{esc(source_url)}" target="_blank" rel="noopener">'
                f'{esc(source_text)}</a>')
        rows.append(_field_row(6, "المصدر", link, defs, raw=True))
    else:
        rows.append(_field_row(6, "المصدر", source_text, defs))

    # ملاحظة المالك 2026-11-02: صفّ «الرابط الرسمي» لا يُعرض إلا إذا كان في الدفتر
    # رابطٌ رسميٌّ مستقل (وثيقة مرجعية)؛ فغيابه لا يُكتب على سطح القارئ أصلًا.
    official = _value_text(event.get("official_ref"))
    if official.startswith("http"):
        link = (f'<a class="ev-link" href="{esc(official)}" target="_blank" rel="noopener">'
                f'{esc(official)}</a>')
        rows.append(_field_row(7, "الرابط الرسمي", link, defs, raw=True))
    else:
        rows.append(_field_row(7, "الرابط الرسمي", "", defs,
                               state="hidden-rule-no-official-link", raw=True))

    excerpt_raw = _value_text(event.get("source_excerpt"))
    # قرار المالك 2026-11-04 (المعتمد): أُخفي صف «ترجمة المعنى» نهائيًا لأنه تكرار
    # للعنوان المرئي (الصف 1)؛ ويبقى حقل translation يُدوَّن داخليًا في الدفتر بلا عرض.

    cleaned = clean_excerpt(excerpt_raw)
    if cleaned:
        excerpt_label = ("مقتطف المصدر" if re.search(r"(?:…|\.{3,})\s*$", excerpt_raw)
                         else "النص الأصلي كما في المصدر")
        inner = ('<details class="ev-fold" data-fold="original-text">'
                 f'<summary>{excerpt_label}</summary>'
                 f'<span>{inline(cleaned, defs)}</span></details>')
        rows.append(_field_row(8, excerpt_label, ABSENCE["excerpt_open"], defs, extra=inner))
    else:
        rows.append(_field_row(8, "النص الأصلي", ABSENCE["excerpt"], defs,
                               state="hidden-rule-no-excerpt"))
    return "".join(rows), has_time


def render_ledger_events(events, defs, md_path: Path, *, meta: dict | None = None):
    """يصيّر جميع سجلات دفتر الفترة، مع فرع موثق فقط عند وجود حقل ربط."""
    renderable_events = [event for event in events if not _is_cumulative_update(event)]
    known = _all_event_records(md_path, renderable_events)
    relation_count = 0
    branch_count = 0
    unresolved = 0
    cards = []
    for idx, event in enumerate(renderable_events, 1):
        code = _event_code(event)
        cls, label = event_badge(event.get("class"))
        reliability = reliability_label(event, meta)
        confidence = confidence_label(event)
        proof_degree = _value_text(event.get("proof_degree"))
        proof_html = (f'<span class="ev-reliability" data-row="3" data-proof-degree="{esc(proof_degree)}">'
                      f'درجة الإثبات: {esc(proof_degree)}</span>' if proof_degree else "")
        fields_html, has_time = _event_fields_html(event, defs)
        relation = _relation_display(event, known)
        relation_key = relation[0] if relation else ""
        if relation:
            relation_count += 1
        branch_html = ""
        if relation:
            branch_count += 1
            relation_key, relation_text = relation
            branch_html = (
                f'<div class="ev-branch" data-row="9" data-branch-status="shown" '
                f'data-relation-ref="{esc(_value_text(event.get(relation_key)))}">'
                '<span class="ev-branch-title">العلاقة</span>'
                f'<span class="ev-mv">{inline(relation_text, defs)}</span></div>'
            )
        else:
            # يبقى الموضع البنيوي مخفيًا حتى لا تتغير أرقام الصفوف، بلا نص غياب للقارئ.
            branch_html = '<div data-row="9" data-branch-status="not-marked" hidden aria-hidden="true"></div>'
        cards.append(
            f'<article class="ev reveal {cls}" id="ev-{idx:02d}" data-event-code="{esc(code)}" '
            f'data-event-date="{esc(_event_date(event))}" data-event-has-time="{"1" if has_time else "0"}" '
            f'data-relation-key="{esc(relation_key)}" data-event-rows="{CARD_ROWS}">'
            f'<div class="ev-top"><span class="ev-idx bidi">{idx:02d}</span>'
            f'<span class="ev-code ltr">{esc(code)}</span>'
            f'<span class="ev-badge" data-row="2" data-classification="{esc(label)}">{esc(label)}</span>'
            f'<span class="ev-reliability" data-row="3" data-source-reliability="{esc(reliability)}">'
            f'موثوقية المصدر: {esc(reliability)}</span>'
            f'<span class="ev-reliability" data-row="3" data-analytic-confidence="{esc(confidence)}">'
            f'درجة الثقة التحليلية: {esc(confidence)}</span>{proof_html}</div>'
            f'<p class="ev-what" data-row="1">{inline(_event_description(event), defs)}</p>'
            f'<div class="ev-meta">{fields_html}</div>{branch_html}</article>'
        )
    return (
        f'<div class="ev-grid" data-count="{len(renderable_events)}" data-source-count="{len(renderable_events)}" '
        f'data-relation-count="{relation_count}" data-branch-count="{branch_count}" '
        f'data-unresolved-branch-count="{unresolved}">'
        + "".join(cards) + "</div>"
    )


def render_events_grid(rows, defs):
    """بطاقة لكل واقعة: شفرة وشارة حالة، ثم نص الحدث بسطر قراءة مريح، ثم المصدر والموقع والوقت."""
    body = [r for r in rows[1:] if len(r) >= 2 and r[0].strip()]
    if not body:
        return ""
    out = [f'<div class="ev-grid" data-count="{len(body)}">']
    for idx, r in enumerate(body, 1):
        code = r[0].strip()
        what = r[1].strip() if len(r) > 1 else ""
        meta = r[2].strip() if len(r) > 2 else ""
        cls, label = event_badge(r[3] if len(r) > 3 else "")
        meta_html = ""
        if meta:
            meta_html = (
                '<p class="ev-meta"><span class="ev-k">المصدر والموقع والوقت</span>'
                f'<span class="ev-mv">{inline(meta, defs)}</span></p>'
            )
        out.append(
            f'<article class="ev reveal {cls}" id="ev-{idx:02d}">'
            f'<div class="ev-top"><span class="ev-idx bidi">{idx:02d}</span>'
            f'<span class="ev-code ltr">{esc(code)}</span>'
            f'<span class="ev-badge">{esc(label)}</span></div>'
            f'<p class="ev-what">{inline(what, defs)}</p>'
            f"{meta_html}</article>"
        )
    out.append("</div>")
    return "\n".join(out)


# ----------------------------------------------------------------------------
# تحويل Markdown
# ----------------------------------------------------------------------------
def parse_ref_defs(md: str):
    """تعريفات المراجع [n]: https://..."""
    defs = {}
    for m in re.finditer(r"^\s*\[(\d{1,3})\]:\s*(\S+)", md, flags=re.M):
        defs.setdefault(m.group(1), m.group(2).strip("<>"))
    return defs


def parse_sections(md: str):
    sections, cur = [], None
    for ln in md.split("\n"):
        m = re.match(r"^##\s+(.*)$", ln)
        if m:
            cur = {"title": m.group(1).strip(), "lines": []}
            sections.append(cur)
            continue
        if ln.startswith("# ") and cur is None:
            continue
        if cur is not None:
            cur["lines"].append(ln)
    return sections


def is_incident_section(title: str) -> bool:
    return any(k in title for k in INCIDENT_SECTION_KEYS)


def render_section_body(title: str, lines, defs, doc_mode: bool = False, section_id: str = ""):
    out, cards = [], []
    incident = is_incident_section(title)

    def flush():
        if cards:
            out.append(render_cards(cards, defs))
            cards.clear()

    i, n = 0, len(lines)
    sub_idx = 0
    while i < n:
        ln = lines[i]
        s = ln.strip()

        if s.startswith("|") and i + 1 < n and is_sep(lines[i + 1]):
            flush()
            rows = [split_table_row(s)]
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_table_row(lines[i]))
                i += 1
            htxt = " ".join(rows[0])
            if doc_mode:
                # وضع الوثيقة (التقارير الخاصة): يُعرض الجدول جدولًا كاملًا بكل أعمدته
                out.append(render_table(rows, defs))
                continue
            if "القطاع" in htxt and ("عدد الوقائع" in htxt or re.search(r"النسبة", htxt)):
                out.append(render_geo_viz(rows, defs))
            if is_events_table(rows[0]):
                # ك-298: جدول الوقائع يجب أن يُصيّر بطاقاته، فكروت الحالة كانت تُسقط عمود «ما حدث»
                out.append(render_events_grid(rows, defs))
                continue
            if title in {"التحذيرات والتنبيهات النشطة", "التحذيرات والنشرات الرسمية"}:
                # عقد بطاقة التحذيرات يقيس table_body_rows؛ لا يجوز تحويل هذا
                # الجدول إلى بطاقات dg-grid لأن ذلك يفقد نوع السطح ويجعل الحارس
                # يفشل رغم تطابق عدد الصفوف.
                out.append(render_table(rows, defs))
                continue
            if is_source_status_table(rows[0]):
                # ك-303: بطاقات المصدر لجدول المصادر الحقيقي فقط (مطابقة صارمة)
                sc = render_source_cards(rows, defs)
                if sc:
                    out.append(sc)
                    continue
            if len(rows[0]) >= 3:
                # ك-303: جداول المحتوى تُعرض بطاقات موسومة تحفظ كل الأعمدة
                out.append(render_data_grid(rows, defs))
                continue
            out.append(render_table(rows, defs))
            continue

        m3 = re.match(r"^###\s+(.*)$", s)
        if m3:
            if incident:
                cards.append((m3.group(1).strip(), []))
                i += 1
                continue
            flush()
            sub_idx += 1
            sid = f' id="{section_id}-sub-{sub_idx:02d}"' if section_id else ""
            out.append(f"<h3{sid}>{inline(m3.group(1).strip(), defs)}</h3>")
            i += 1
            continue

        if re.match(r"^####\s+", s):
            flush()
            sub_idx += 1
            sid = f' id="{section_id}-sub-{sub_idx:02d}"' if section_id else ""
            out.append(f"<h3{sid}>{inline(re.sub(r'^####\s+', '', s), defs)}</h3>")
            i += 1
            continue

        if cards:
            if s.startswith("#"):
                flush()
                continue
            if s:
                cards[-1][1].append(s)
            i += 1
            continue

        if re.match(r"^\s*[-*]\s+", ln):
            flush()
            items, kinds, sub = [], False, []

            def _close_sub():
                if items and sub:
                    items[-1] = items[-1][:-5] + "<ul>" + "".join(sub) + "</ul></li>"
                    sub.clear()

            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                indent = len(lines[i]) - len(lines[i].lstrip())
                raw = re.sub(r"^\s*[-*]\s+", "", lines[i].strip())
                mk = MARK_RE.match(raw)
                cls = ""
                if mk:
                    cls = ' class="' + BLK.MARK_KIND.get(mk.group(1), "") + '"'
                    kinds = True
                    raw = raw[mk.end():]
                item = f"<li{cls}>{inline(raw, defs)}</li>"
                if indent >= 2 and items:
                    sub.append(item)
                else:
                    _close_sub()
                    items.append(item)
                i += 1
            _close_sub()
            cls_ul = ' class="d-kinds"' if kinds else ""
            out.append(f"<ul{cls_ul}>" + "".join(items) + "</ul>")
            continue

        if re.match(r"^\s*\d+[\.\)]\s+", ln):
            flush()
            items, kinds = [], False
            while i < n and re.match(r"^\s*\d+[\.\)]\s+", lines[i]):
                raw = re.sub(r"^\s*\d+[\.\)]\s+", "", lines[i].strip())
                mk = MARK_RE.match(raw)
                cls = ""
                if mk:
                    cls = ' class="' + BLK.MARK_KIND.get(mk.group(1), "") + '"'
                    kinds = True
                    raw = raw[mk.end():]
                items.append(f"<li{cls}>{inline(raw, defs)}</li>")
                i += 1
            cls_ol = ' class="d-kinds"' if kinds else ""
            out.append(f"<ol{cls_ol}>" + "".join(items) + "</ol>")
            continue

        if s.startswith(">"):
            flush()
            q = []
            while i < n and lines[i].strip().startswith(">"):
                q.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(q), defs)}</blockquote>")
            continue

        if re.match(r"^---+$", s):
            flush()
            out.append("<hr>")
            i += 1
            continue

        if s:
            flush()
            para = [s]
            i += 1
            while i < n and lines[i].strip() and not re.match(
                r"^(#|\||>|\s*[-*]\s|\s*\d+[\.\)]\s|---)", lines[i].strip()
            ):
                para.append(lines[i].strip())
                i += 1
            text = " ".join(para)
            # فقرة المنهج الداخلي تُعرض مخفية: تبقى في المصدر ولا تظهر للقارئ
            cls = ' class="method-note"' if text.lstrip("*").startswith("منهج الحالة") else ""
            out.append(f"<p{cls}>{inline(text, defs)}</p>")
            continue

        i += 1

    flush()
    return "\n".join(out)


# ----------------------------------------------------------------------------
# التحقق من meta
# ----------------------------------------------------------------------------
def _modern_hero_kpis(report_date: str | None) -> bool:
    return bool(report_date and report_date >= HERO_KPI_MODERN_FROM)


def validate_meta(meta: dict, *, report_date: str | None = None):
    if not isinstance(meta, dict):
        raise BuildError("ملف الواجهة (meta) يجب أن يكون كائن JSON.")
    kpis = meta.get("hero_kpis", [])
    if not isinstance(kpis, list):
        raise BuildError("الحقل hero_kpis يجب أن يكون قائمة في ملف الواجهة.")
    modern = _modern_hero_kpis(report_date)
    required_label = "title" if modern else "label"
    for k in kpis:
        if not isinstance(k, dict):
            raise BuildError(f"كل عنصر في hero_kpis يجب أن يكون كائنًا يحتوي {required_label} و value.")
        if required_label not in k or "value" not in k:
            raise BuildError(f"عنصر في hero_kpis ينقصه {required_label} أو value.")
    if "threat_level" in meta and not isinstance(meta["threat_level"], str):
        raise BuildError("الحقل threat_level يجب أن يكون نصًا.")
    return meta


def derive_intel_source_grade(meta: dict) -> str:
    """يبني سند التحليل من سجل موثوقية المصادر المولَّد، لا من نص يدوي في meta."""
    reliability = meta.get("source_reliability") or {}
    rows = reliability.get("rows") if isinstance(reliability, dict) else None
    if not isinstance(rows, list):
        return ""
    grades = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        rel = str(row.get("rel") or "").strip().upper()
        cred = str(row.get("cred") or "").strip()
        if not name or not re.fullmatch(r"[A-F]", rel) or cred not in set("123456"):
            continue
        item = f"{name} {rel}/{cred}"
        if item not in seen:
            grades.append(item)
            seen.add(item)
    return " · ".join(grades)


def render_intel_review_notes(meta: dict, inline) -> str:
    """يضيف سطري المراجعة اللذين يجب أن يظهرا أسفل كتلة التحليل."""
    if not isinstance(meta.get("intel_analysis"), dict):
        return ""
    return (
        # «التحقق من المصادر» لفظ مصطنع ممنوع (forbidden-coinages · 2026-10-29) وكان يمنع صفحة
        # الإضافات؛ يُعاد الوسم المعتمد قبل جولة 11-12.
        '<p class="rmk"><strong>التحقق المستقل من المصادر:</strong> '
        + inline("الفصل بين الوقائع والتقديرات وربط التقديرات بسند المصدر.")
        + "</p>"
    )


def threat_class(threat: str) -> str:
    """تصنيف المستوى إلى صنف لوني — يفشل مغلقًا على أي لفظ خارج السلّم المعتمد.

    السلّم الحاكم: appendices/threat-scale.json (خمسة مستويات بمطابقة JMIC).
    لكل مستوى صنف لوني مستقل: «حرج» لا يتشارك لون «مرتفع».
    """
    _map = {
        "حرج": "risk-critical",
        "مرتفع جدًا": "risk-severe",
        "مرتفع": "risk-high",
        "متوسط": "risk-med",
        "منخفض": "risk-low",
    }
    key = (threat or "").strip()
    if key not in _map:
        raise ValueError(f"مستوى تهديد خارج السلّم المعتمد: «{threat}» — يُمنع البناء")
    return _map[key]


# ----------------------------------------------------------------------------
# البناء
# ----------------------------------------------------------------------------
def hero_map(map_html: str, *, print_mode: bool = False, extra_html: str = "", top_html: str = "") -> str:
    """نسخة خريطة الوقائع للشاشة فقط، تظهر أعلى الصفحة (قرار فهد 22 أكتوبر 2026).

    الصنف no-print يحجبها في PDF، وWord يحذفه (STRIP_SELECTORS). أصنافها مغايرة لأصناف
    الخريطة الأصلية (hmap بدل map-viz/map-wrap/map-legend) حتى لا تلتقطها أدوات الطباعة
    والتصدير التي تختار بتلك الأصناف أول عنصر في الصفحة. تُخفى عن قارئ الشاشة
    (aria-hidden) لأن الخريطة الأصلية في قسمها هي المرجع.
    """
    h = map_html
    for old, new in (("viz map-viz reveal", "hmap"), ("map-panel", "hmap-panel"), ("map-wrap", "hmap-wrap"),
                     ("map-svg", "hmap-svg"), ("map-legend", "hmap-legend"), ("map-keys", "hmap-keys")):
        h = h.replace(old, new)
    if extra_html:
        head, tail = h.rsplit("</div>", 1)
        h = head + extra_html + "</div>" + tail
    if print_mode:
        return f'<section class="print-map" aria-label="خريطة الوقائع ومفتاحها">{h}</section>'
    _hint = '<p class="hmap-scroll-hint">يمكن استعراض كامل الخريطة بالتمرير الأفقي.</p>'
    return (f'<section class="print-map hero-map no-print" aria-label="خريطة سياق القطاعات للشاشة">'
            f'{top_html}{h}{_hint}</section>')


def _map_decision_strip(meta: dict) -> str:
    """شريط قرار مثبت أعلى الخريطة: أعلى قطاع · العدّاد · إجراء اليوم · آخر تحديث."""
    import html as _h
    _esc = lambda v: _h.escape(str(v), quote=True)  # noqa: E731
    try:
        tz = meta.get("threat_zones") or {}
        zs = tz.get("zones") or []
        top = max(zs, key=lambda z: z.get("rank", 0)) if zs else {}
        cnt = tz.get("counter") or {}
        dc = meta.get("decision_card") or {}
        _a = dc.get("action")
        act = str(_a[0]) if isinstance(_a, list) and _a else (str(_a) if isinstance(_a, str) else "")
        upd = meta.get("updated") or meta.get("generated_at") or ""
        cells = [
            ("أعلى قطاع", f'{top.get("name", "")} — {top.get("level_ar", "")}'.strip(" —"), False),
            ("الوقائع المؤهلة",
             f'<bdi dir="ltr">{_esc(cnt.get("qualifying", 0))} / {_esc(cnt.get("total", 0))}</bdi>', True),
            ("إجراء اليوم", act, False),
            ("آخر تحديث", str(upd), False),
        ]
        items = "".join(
            f'<li><span class="mds-k">{_esc(k)}</span><span class="mds-v">{v if raw else _esc(v)}</span></li>'
            for k, v, raw in cells if v)
        return f'<ul class="hmap-decide">{items}</ul>'
    except Exception as e:  # لا يُسقط فشل الشريط بناء التقرير
        print(f"تنبيه: تعذر توليد شريط قرار الخريطة ({e})", file=sys.stderr)
        return ""


def render_print_distribution_cards(sections, defs) -> str:
    """بطاقات توزيع صغيرة تُوضع أسفل مفتاح خريطة PDF عند نقل القسم إلى الإضافات."""
    for sec in sections:
        if "التوزيع الجغرافي" not in sec.get("title", ""):
            continue
        lines = sec.get("lines") or []
        for i, ln in enumerate(lines[:-1]):
            if not (ln.strip().startswith("|") and is_sep(lines[i + 1])):
                continue
            rows = [split_table_row(ln)]
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(split_table_row(lines[j]))
                j += 1
            cards = []
            for row in rows[1:]:
                if len(row) < 2 or not row[0].strip():
                    continue
                detail = " · ".join(x for x in row[1:4] if x.strip())
                cards.append(
                    '<div class="dist-card">'
                    f'<b>{inline(row[0], defs)}</b><span>{inline(detail, defs)}</span>'
                    '</div>'
                )
            if cards:
                return (
                    '<div class="print-map-distribution" aria-label="بطاقات التوزيع الجغرافي">'
                    '<h3>بطاقات التوزيع الجغرافي</h3>'
                    '<div class="dist-cards">' + "".join(cards) + '</div></div>'
                )
    return ""


def _section_anchor_map(sections):
    """Return the actual top-level ids emitted for a selected section list."""
    return {sec["title"]: f"sec-{idx + 1:02d}" for idx, sec in enumerate(sections)}


def _reorder_report_sections(sections):
    """قرار المالك 2026-11-04 (ملاحظة 5): تبديل موضعَي «سجل الأحداث» و«مؤشرات الموقف» فقط."""
    event_keys = ("سجل الأحداث", "الوقائع الجديدة", "الوقائع الأمنية")
    out = list(sections)
    i_ev = i_ind = None
    for i, sec in enumerate(out):
        title = sec.get("title", "")
        if i_ev is None and any(k in title for k in event_keys):
            i_ev = i
        if i_ind is None and "مؤشرات الموقف" in title:
            i_ind = i
    if i_ev is not None and i_ind is not None and i_ev != i_ind:
        out[i_ev], out[i_ind] = out[i_ind], out[i_ev]
    return out


def _subheading_anchor_map(section, section_id):
    out = {}
    n = 0
    for line in section.get("lines", []):
        m = re.match(r"^###\s+(.+?)\s*$", line.strip())
        if m:
            n += 1
            out[m.group(1).strip()] = f"{section_id}-sub-{n:02d}"
    return out


def _markdown_table_rows(lines):
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and i + 1 < len(lines) and is_sep(lines[i + 1]):
            n = 0
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                n += 1
                j += 1
            return n
    return 0


def _subheading_list_count(section, wanted):
    active = False
    n = 0
    for line in section.get("lines", []):
        s = line.strip()
        m = re.match(r"^###\s+(.+?)\s*$", s)
        if m:
            active = m.group(1).strip() == wanted
            continue
        if active and re.match(r"^##\s+|^###\s+", s):
            break
        if active and re.match(r"^\s*(?:[-*]|\d+[.)])\s+\S", line):
            n += 1
    return n


def _rendered_section_count(section, defs, measurement):
    if not section:
        return 0
    fragment = render_section_body(section["title"], section.get("lines", []), defs,
                                   False, section_id="counter-target")
    return count_rendered_fragment(fragment, measurement)


def _addition_sections_in_render_order(all_sections):
    """Use the same policy ordering as build(mode='additions')."""
    order = {key: index for index, key in enumerate(ADDITIONS_SECTIONS)}

    def key(section):
        title = section.get("title", "")
        matches = [index for name, index in order.items() if name in title]
        return min(matches, default=len(order))

    return sorted((section for section in all_sections if key(section) < len(order)), key=key)


def _official_warning_texts(section):
    texts = []
    lines = section.get("lines", []) if section else []
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and i + 1 < len(lines) and is_sep(lines[i + 1]):
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = split_table_row(lines[j])
                if len(cells) >= 2 and cells[1].strip():
                    texts.append(cells[1].strip())
                j += 1
            break
    return texts


def _card_targets(all_sections, report_sections, meta, defs, report_date):
    """Measure the exact rendered targets used by the three card rows."""
    warning_title = "التحذيرات والتنبيهات النشطة"
    # عنوان تاريخي محفوظ في إصدارات مؤرشفة ومجمّدة البصمة؛ يُقبل للتحديد فقط ولا يُكتب في أي سطح جديد.
    legacy_warning_titles = ("التحذيرات والنشرات الرسمية",)
    watch_section_title = "المراقبة المستمرة"
    watch_title = "المراقبة المستمرة"
    warning_sec = next((x for x in all_sections if x["title"] == warning_title or x["title"] in legacy_warning_titles), None)
    watch_sec = next((x for x in all_sections if x["title"] == watch_section_title), None)
    changes_html = BLK.changes_block(meta.get("changes"), lambda x: inline(x, defs))
    changed_count = len(re.findall(r'<li class="chg\b', changes_html))
    # ك-406: صفحة «إضافات» ترقّم أقسامها من الصفر وبترتيب السياسة؛ فكانت مراسي البطاقة
    # تشير إلى ترتيب المصدر أو إلى قسم فرعي لا يطابق الصفحة المرسومة. الترقيم هنا يُطابق
    # الترتيب الفعلي الذي تستخدمه build(mode='additions').
    addition_sections = _addition_sections_in_render_order(all_sections)
    # كتلة «ما تغيّر» هي sec-00 وتأتي قبل أقسام السياسة؛ جسم الإضافات يبدأ من sec-01.
    addition_ids = {sec["title"]: f"sec-{idx + 1:02d}" for idx, sec in enumerate(addition_sections)}
    changed_anchor = addition_ids.get("ما تغيّر", "sec-00")
    warning_anchor = addition_ids.get(warning_sec["title"] if warning_sec else warning_title, "sec-01")
    watch_anchor = addition_ids.get(watch_section_title, "sec-04")
    return {
        "changed_count": changed_count,
        "changed_href": f"/additions.html#{changed_anchor}",
        "changed_title": "ما تغيّر منذ التقرير السابق",
        "warning_count": _rendered_section_count(warning_sec, defs, "table_body_rows"),
        "warning_texts": _official_warning_texts(warning_sec),
        "warning_href": f"/additions.html#{warning_anchor}",
        "watch_count": _rendered_section_count(watch_sec, defs, "visible_items"),
        "watch_href": f"/additions.html#{watch_anchor}",
        "watch_title": watch_title,
    }


def _additions_return_link(report_date: str) -> str:
    """رابط عودة إلى صفحة إصدار التقرير المقابل، ولا يُنشأ لتاريخ غير صالح."""
    try:
        parsed = datetime.strptime(str(report_date), "%Y-%m-%d")
    except (TypeError, ValueError):
        return ""
    date = parsed.strftime("%Y-%m-%d")
    return (f'<a class="chip additions-return" href="/reports/{date}.html">'
            "العودة إلى إصدار التقرير</a>")


def build(md_path: Path, out_path: Path, meta: dict, doc_mode: bool = False, mode: str = "report"):
    """mode='report' يُخفي أقسام «إضافات» (السياسة الحاكمة) · mode='additions' يعرضها وحدها بترتيبها."""
    global _REPORT_DATE
    _REPORT_DATE = md_path.stem.split("-sectioned")[0]
    md = md_path.read_text(encoding="utf-8")
    defs = parse_ref_defs(md)
    sections = parse_sections(md)
    if not sections:
        raise BuildError(
            "لم يُعثر على أي قسم بعنوان من المستوى الثاني (##) في الملف المصدر. "
            "تأكد من حفظ التقرير بأقسام بصيغة Markdown صحيحة."
        )
    _mdate = re.search(r"(\d{4}-\d{2}-\d{2})", md_path.name)
    report_date = _mdate.group(1) if _mdate else ""
    validate_meta(meta, report_date=report_date)
    _set_zone_display_names(meta)
    daily_events = load_daily_events(md_path, report_date)
    if report_date >= LIVE_EVENT_LEDGER_FROM and daily_events is None:
        raise BuildError("دفتر أحداث الفترة مفقود؛ لا يُبنى سجل الأحداث الحي بلا مصدر")
    # سياسة عرض الرموز (2+5): كامل مرة واحدة في «الوقائع الجديدة»، ومختصر مدموج برقم البلاغ الرسمي في بقية المواضع
    official = codes.official_map(meta)
    BLK.set_code_context(report_date, official)
    try:
        import map_gulf as _mg
        _mg.REPORT_DATE = report_date
    except Exception:
        pass

    # ترتيب الأقسام بالأهمية: القرار والصورة ← الوقائع ← التحليل ← الدعم
    # (الترتيب مستقر، والأقسام غير المعروفة تبقى في آخرها)
    order = [
        "ما تغيّر",         "الخلاصة القيادية",         "أهم الأخبار المتعلقة بالأمن البحري",         "التوزيع الجغرافي",
        "المؤشرات الرقمية",         "تقييم التهديد",         "الأثر التشغيلي",         "الوقائع الأمنية الجديدة",
        "النشرات والتحذيرات",         "سجل IMO",         "الفرضيات المتنافسة",         "اتجاهات الحركة والتكدس",
        "المجهولات والفجوات",         "المراقبة المستمرة",         "الخلفية المستمرة",         "المصادر وحالة الفحص",

    ]

    def _order_key(sec):
        for i, k in enumerate(order):
            if k in sec["title"]:
                return i
        return len(order)

    if mode == "additions":
        # قرار المالك 2026-10-28: هذه الأقسام تُعرض في صفحة «إضافات» وحدها بترتيب السياسة
        _add = ADDITIONS_SECTIONS or []
        sections = [x for x in sections if any(k in x["title"] for k in _add)]
        _key = lambda sec: next((i for i, k in enumerate(_add) if k in sec["title"]), len(_add))
        sections = sorted(sections, key=_key)
    else:
        # ك-229: نقل الأقسام يسري من تاريخ القرار؛ الأرشيف قبله يبقى كما نُشر بلا فقد محتوى
        _hidset = set(HIDDEN_SECTIONS)
        if ADDITIONS_FROM and report_date and report_date < ADDITIONS_FROM:
            for _a in ADDITIONS_SECTIONS:
                _hidset.discard(_a)
        sections = [x for x in sections if not any(h in x["title"] for h in _hidset)]
        sections = sorted(sections, key=_order_key)
        sections = _reorder_report_sections(sections)
    source_sections = list(parse_sections(md))
    # كتل خاصة بكل قسم: خريطة عنوان القسم إلى اسم الكتلة
    blocks_map = meta.get("blocks") or {}
    block_data = {k: meta.get(k) for k in ("indicators", "hypotheses", "gaps", "event_keys", "timeline", "source_reliability", "vessel_identity", "report_classes", "intel_analysis")}
    intel_data = block_data.get("intel_analysis")
    if isinstance(intel_data, dict):
        intel_data = dict(intel_data)
        derived_grade = derive_intel_source_grade(meta)
        if derived_grade:
            intel_data["source_grade"] = derived_grade
        block_data["intel_analysis"] = intel_data
    if not isinstance(blocks_map, dict):
        blocks_map = {}

    # خريطة الوقائع/النطاق: تُبنى من إحداثيات معلَنة في ملف الواجهة فقط.
    # عند غياب الإحداثيات لا نرسم علامات تقريبية، لكن نبقي اللوحة الجغرافية
    # المصمتة مع إفصاحها الصريح حتى لا تتحول الخريطة إلى معلومة مكانية مخترعة.
    map_html = ""
    mp = meta.get("map") or {}
    if isinstance(mp, dict) and (mp.get("points") or mp.get("caption")):
        try:
            from map_gulf import build_map

            _cap = ((mp.get("caption") or "") + " " + (mp.get("points_note") or "")).strip()
            # ك-227: جدول تفاصيل الوقائع كان يُبنى من نقاط الخريطة وحدها، فتُسقط واقعة
            # مؤهلة بلا إحداثيات. تُمرَّر وقائع اليوم غير المكانية لتُضاف صفوفها.
            _pcs = {str(p.get("code") or "") for p in (mp.get("points") or [])}
            _extra_events = [e for e in (daily_events or [])
                             if str(e.get("code") or "").strip()
                             and str(e.get("code")) not in _pcs
                             and not _is_cumulative_update(e)]
            map_html = build_map(mp["points"], _cap, mp.get("inset"),
                             zones=(meta.get("threat_zones") or {}).get("zones"),
                             timeline=meta.get("timeline"),
                             extra_events=_extra_events)
        except Exception as e:
            # فشل مغلق: وجود وقائع يعني أن الخريطة عقد إخراج لا عنصر تجميلي.
            if mp.get("points"):
                raise
            print(f"تنبيه: تعذر توليد خريطة السياق ({e})", file=sys.stderr)
            map_html = ""

    hero_map_html = ""
    print_map_html = ""
    if map_html and not doc_mode:
        _imo_line = _imo_reference_line(meta)
        try:
            from map_gulf import build_map as _build_map_hero

            _cap_h = ((mp.get("caption") or "") + " " + (mp.get("points_note") or "")).strip()
            _hero_map_source = _build_map_hero(
                mp["points"], _cap_h, mp.get("inset"), zoom=True,
                zones=(meta.get("threat_zones") or {}).get("zones"),
                timeline=meta.get("timeline"), extra_events=_extra_events)
            _strip = ""
            try:
                import threat_card as _TC
                _zj = _TC.load_zones_site(report_date)
                if _zj:
                    _strip = _TC.zones_strip(_zj)
            except Exception as e:  # لا يُسقط فشل الشريط بناء التقرير
                print(f"تنبيه: تعذر توليد شريط نسب القطاعات ({e})", file=sys.stderr)
            _strip = _strip + _imo_line
            _dstrip = _map_decision_strip(meta)
            hero_map_html = "" if mode == "additions" else hero_map(
                _hero_map_source, extra_html=_strip, top_html=_dstrip)
            # تُحضر كتلة الطباعة لكل سطح؛ سياسة الإضافات تحدد موضعها فقط.
            print_map_html = hero_map(_hero_map_source, print_mode=True)
        except Exception as e:
            if mp.get("points"):
                raise
            print(f"تنبيه: تعذر توليد خريطة الشاشة العليا ({e})", file=sys.stderr)

    # شريط المؤشرات
    kpi_html = ""
    kpis = meta.get("hero_kpis", [])
    if kpis:
        modern = _modern_hero_kpis(report_date)
        if modern:
            rows = {}
            for k in kpis:
                rows.setdefault(int(k.get("row") or 1), []).append(k)
            # قرار المالك 2026-11-04: الصف الأول 4 بطاقات، والصفوف التالية 3 (أو 2 للبطاقتين الدائمتين).
            if (1 not in rows or len(rows[1]) != 4 or len(rows) < 2
                    or any(len(v) not in (2, 3, 4) for r, v in rows.items() if r != 1)):
                raise BuildError("hero_kpis: الصف الأول 4 بطاقات والصفوف التالية 3 (أو 2 للبطاقتين الدائمتين)؛ فشل مغلق")
        if modern:
            def _hero_tile(k):
                acc = k.get("accent", "ok")
                if acc not in ("ok", "info", "warn", "danger"):
                    acc = "ok"
                title = k.get("title", "")
                detail = k.get("detail", "")
                tag = k.get("tag", "")
                tag_html = f'<span class="k-tag">{inline(tag)}</span>' if tag else ""
                # طبقات البطاقة (قرار المالك 2026-10-31): القيمة اليومية · المجموع من 28 فبراير 2026 · آخر تحديث المصدر
                _lay = []
                _cumulative_html = _hero_cumulative_html(k)
                if _cumulative_html:
                    _lay.append(_cumulative_html)
                if k.get("updated"):
                    _lay.append(f'<div class="k-lay"><span class="k-lay-l">{UPD_LABEL}</span> '
                                f'<b class="bidi">{esc(str(k["updated"]))}</b></div>')
                layers_html = f'<div class="k-lays">{"".join(_lay)}</div>' if _lay else ""
                return (f'<div class="kpi hero-kpi acc-{acc} reveal" data-kpi-id="{esc(k.get("id", ""))}"><em></em>'
                        f'<div class="k-l">{inline(title)}{tag_html}</div>'
                        f'<div class="k-v bidi">{esc(k.get("value", ""))}</div>'
                        f'{layers_html}'
                        f'<div class="k-n">{inline(detail)}</div></div>')
            risk = meta.get("hero_risk_patterns") or []
            risk_html = ('<div class="k-risk-patterns" aria-label="أنماط الخطر"><span class="k-risk-label">أنماط الخطر</span>'
                         + "".join(f'<span class="k-risk-tag">{inline(x)}</span>' for x in risk) + '</div>') if risk else ""
            row1 = "".join(_hero_tile(k) for k in kpis if k.get("row") == 1)
            row2 = "".join(_hero_tile(k) for k in kpis if k.get("row") == 2)
            kpi_html = ('<div class="kpis hero-kpis">' + risk_html
                        + f'<div class="kpi-row kpi-row-1">{row1}</div>'
                        + f'<div class="kpi-row kpi-row-2">{row2}</div></div>')
        else:
            tiles = []
            for k in kpis:
                acc = k.get("accent", "ok")
                if acc not in ("ok", "info", "warn", "danger"):
                    acc = "ok"
                tiles.append(
                    f'<div class="kpi acc-{acc} reveal"><em></em>'
                    f'<div class="k-l">{inline(k.get("label", ""))}</div>'
                    f'<div class="k-v bidi">{esc(k.get("value", ""))}</div>'
                    f'<div class="k-n">{inline(k.get("note", ""))}</div></div>'
                )
            kpi_html = '<div class="kpis">' + "".join(tiles) + '</div>'

    # خريطة الملحق: تُلحق في نهاية «إضافات» فقط (صفحتها الكاملة بلا فراغ قبلها).
    appendix_map = print_map_html if mode == "additions" else ""
    # عطل 2026-10-28 (فراغ 176مم في الصفحة السابقة للخريطة): تُدرج خريطة الملحق قبل
    # «ما لم يُحسم» فتشارك صفحتها بقيّة المحتوى، ويستقرّ الذيل في الصفحة الأخيرة بلا فراغ.
    _appendix_map_marker = "\u0000"  # لا يطابق شيئًا: الخريطة تُلحق آخر الملحق
    threat = meta.get("threat_level", "")
    tcls = threat_class(threat) if threat else ""

    # قاموس الرموز والمصطلحات: يُطبع قسمًا مستقلًا بعد الخلاصة.
    # عطل ك-36: كان في تذييل الصفحة، وأنماط الطباعة تخفي التذييل، فغاب عن PDF تمامًا.
    glossary_html = ("" if _hidden("قاموس الرموز والمصطلحات")
                     else BLK.glossary(meta.get("glossary")))

    # قائمة الأقسام المخفية تُطبع للسجل مرة واحدة (تتبّع القرار لا التخمين)
    _hid = sorted(HIDDEN_SECTIONS)
    print("أقسام مُخفاة من الإصدار: " + " · ".join(_hid), file=sys.stderr)

    body = []
    for idx, sec in enumerate(sections):
        t = sec["title"]
        ic = SECTION_ICONS.get(t, "source")
        pri = " pri" if any(p in t for p in PRIORITY_SECTIONS) else ""
        body.append(f'<section class="doc{pri} reveal" id="sec-{idx + 1:02d}" aria-labelledby="h-{idx + 1:02d}">')
        if appendix_map and _appendix_map_marker in t:
            body.append(appendix_map)
            appendix_map = ""
        body.append(
            f'<h2 id="h-{idx + 1:02d}"><span class="ico">{icon(ic)}</span>{inline(t, defs)}</h2>'
            '<div class="h-rule"></div>'
            + (f'<p class="sec-lede">{esc(SECTION_HINTS[t])}</p>' if SECTION_HINTS.get(t) else "")
        )
        if "سجل الأحداث" in t and daily_events is not None and not doc_mode:
            section_html = render_ledger_events(daily_events, defs, md_path, meta=meta)
        else:
            section_html = render_section_body(t, sec["lines"], defs, doc_mode, section_id=f"sec-{idx + 1:02d}")
        if mode != "additions" and "مستوى التهديد" in t:
            section_html = compact_threat_section_html(section_html)
        if any(k in t for k in DIRECTIVE_SECTIONS):
            section_html = _third_person_html(section_html)
        if not codes.is_primary(t):
            section_html = codes.demote(section_html, report_date, official)
        if map_html and "التوزيع الجغرافي للوقائع" in t:
            # نسخة الإضافات المطبوعة تستخدم hmap بصفحة مستقلة ومفتاح كامل؛ لا تُكرر map-viz القديمة.
            if mode == "additions" and print_map_html:
                # أبقِ النص نفسه، لكن أخّر الفقرة التفسيرية الأخيرة بصريًا كي تتسع
                # كتلة الخريطة ذات المفتاح الكامل في الصفحة التالية بلا ورقة شبه فارغة.
                tail_para = ""
                m = re.search(r"(<p>.*?</p>)\s*$", section_html, flags=re.S)
                if m:
                    tail_para = m.group(1)
                    section_html = section_html[:m.start()]
                # عطل 2026-10-28: إدراج الخريطة داخل القسم يترك فراغًا كبيرًا في الصفحة
                # السابقة لها (الخريطة تحتاج صفحة كاملة). القرار: تُلحق الخريطة ومفتاحها في
                # نهاية ملحق الإضافات (صفحتها الكاملة)، ويُستكمل ما قبلها بمحتوى الأقسام.
                section_html = section_html + tail_para
            elif mode != "additions" and print_map_html:
                # التقرير اليومي يحتاج كتلة print-map فعلية أيضًا؛ لا نستخدم
                # مواقع وقائع غير مثبتة، فاللوحة قد تكون سياقية بلا علامات.
                section_html = section_html + print_map_html
            else:
                section_html = section_html + map_html
        for key, bname in blocks_map.items():
            if key in t:
                for _bn in str(bname).split('+'):
                    if mode != "additions" and _bn in HIDDEN_BLOCKS:
                        continue
                    if block_data.get(_bn):
                        section_html += BLK.render_block(_bn, block_data[_bn], inline)
                        if _bn == "intel_analysis":
                            section_html += render_intel_review_notes(meta, inline)
        # عطل ك-72: تنبيه القسم كان داخل حلقة كتل المؤشرات فيتكرر بعددها (6 مرات في إصدار 20 أكتوبر).
        # القاعدة: تنبيه القسم يُكتب مرة واحدة في مستوى القسم لا داخل حلقة عناصره.
        if "الحركة" in t:
            section_html += '<p class="src-note">قراءة اتجاه الحركة والتكدس من مسار المتابعة المعتمد؛ ويُعرض اسم المنصة ودقة بياناتها في مراجع التقرير على الموقع. يُؤخذ في الحساب مدة التحديث (20 دقيقة) واحتمال انقطاع الإرسال أو التزييف.</p>'
        if "حالة المصادر" in t:
            # قرار المالك 2026-11-04 (البند 6): سطر واحد يذكر عدد المصادر المفحوصة
            # والمحجوبة، وتفصيلها في صفحة المصادر.
            _cov = meta.get("source_coverage") or {}
            _tried = _cov.get("attempted")
            _ok = _cov.get("successful")
            _blocked = _cov.get("blocked_count")
            if isinstance(_tried, int) and isinstance(_ok, int) and isinstance(_blocked, int):
                # قرار المالك 2026-11-04 (البند 6): سطر واحد بثلاثة أعداد، وكل عدد
                # داخل وسم لاتيني حتى يبقى النص العربي وحدات معجمية ثابتة قابلة للترجمة.
                section_html += (
                    '<p class="src-note">المصادر المفحوصة '
                    f'<span class="ltr">{_tried}</span> · الناجحة '
                    f'<span class="ltr">{_ok}</span> · المحجوبة '
                    f'<span class="ltr">{_blocked}</span></p>'
                )
        if "التوزيع الجغرافي" in t:
            section_html += '<p class="src-note">تحذيرات IHO/NAVAREA تُربط بإحداثياتها عند توفرها؛ والويب لا يستبدل البث الملاحي المعتمد.</p>'
        body.append(section_html)
        body.append("</section>")
        if "الخلاصة" in t and glossary_html:
            body.append(
                '<section class="doc reveal" id="sec-glossary" aria-labelledby="h-glossary">'
                '<h2 id="h-glossary"><span class="ico">' + icon("source") + '</span>قاموس الرموز والمصطلحات</h2>'
                '<div class="h-rule"></div>'
                '<p class="sec-lede">تعريفات الرموز والمصطلحات المستخدمة في هذا التقرير.</p>'
                + glossary_html + "</section>")

    title = normalize_daily_title(meta.get("title")) or DAILY_TITLE
    sub = meta.get("subtitle") or ""
    generated = meta.get("generated_label") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    generated_display = format_update_label(generated)

    chips = []
    if meta.get("version"):
        chips.append(f'<span class="chip">رقم الإصدار <b>{esc(format_release_version(meta["version"]))}</b></span>')
    if generated:
        chips.append(f'<span class="chip">آخر تحديث <b>{esc(generated_display)}</b></span>')
    if meta.get("window"):
        win = esc(meta["window"])
        _m = re.match(r'^(\S+Z\s*[–-]\s*\S+Z)\s*(.*)$', win)
        if _m:
            win = f'<bdi class="bidi" dir="ltr">{_m.group(1)}</bdi> {_m.group(2)}'
        chips.append(f'<span class="chip">فترة التغطية <b>{win}</b></span>')
    if meta.get("sources_approved") not in (None, ""):
        chips.append(f'<span class="chip">المصادر المعتمدة <b class="bidi">{esc(meta["sources_approved"])}</b></span>')
    if meta.get("sources_checked") not in (None, ""):
        chips.append(f'<span class="chip">بالمسار الآلي <b class="bidi">{esc(meta["sources_checked"])}</b></span>')

    notice_html = ""
    if meta.get("notice"):
        notice_html = f'<div class="notice">{icon("shield")}<div>{inline(meta["notice"], defs)}</div></div>'

    threat_html = ""
    _zj = TC.load_zones_site(report_date) if report_date else None
    if _zj:
        # بطاقة القطاعات الأربعة: مصدر رسم واحد للشاشة والطباعة (قرار المالك 2026-10-30)
        threat_html = TC.zones_card(_zj, variant="print")
    elif threat:
        threat_html = (
            f'<div class="threat {tcls}"><div class="lbl">مستوى التهديد</div>'
            f'<div class="val">{esc(threat)}</div></div>'
        )

    date_label = meta.get("date_label") or ""
    cls_html = BLK.classification_banner(meta.get("classification"))
    anchors = {"مستوى التهديد": "sec-02", "ما تغيّر": "sec-00"}
    for _i, _s in enumerate(sections):
        anchors.setdefault(_s["title"], f"sec-{_i + 1:02d}")
    anchors["أهم الأخبار المتعلقة بالأمن البحري"] = "sec-decision"
    anchors["التوصيات"] = anchors.get("التوصيات") or anchors.get("التوجيهات التشغيلية", "sec-decision")
    anchors["ما يُراقب خلال 24 ساعة"] = anchors.get("علامات الإنذار المبكر", "sec-decision")
    decision_html = "" if mode == "additions" else BLK.decision_card(
        meta.get("decision_card"), inline, anchors=anchors)
    # سياسة الأقسام 2026-10-28: «ما تغيّر» منقول إلى صفحة «إضافات»
    if mode == "additions":
        changes_html = BLK.changes_block(meta.get("changes"), inline)
    else:
        _adds_live = bool(ADDITIONS_SECTIONS) and (not ADDITIONS_FROM or not report_date
                                              or report_date >= ADDITIONS_FROM)
        changes_html = ("" if (_adds_live and _hidden("ما تغيّر"))
                        else BLK.changes_block(meta.get("changes"), inline))
    card_targets = _card_targets(source_sections, sections, meta, defs, report_date)
    # خريطة مراسي الأقسام (م-32): تربط بنود البطاقة بأقسامها بلا نص مكرر.
    # قرار المالك 2026-11-04: كتلة «أهم الأخبار المتعلقة بالأمن البحري» انتقلت من
    # صفحة الإصدار إلى صفحة «إضافات»، ويبقى في الإصدار سطر إشارة واحد فقط.
    if mode == "additions":
        screen_hero_html = SCR.news_card_block(
            meta, esc=esc, inline=inline, report_date=report_date, card_targets=card_targets)
    else:
        screen_hero_html = SCR.screen_hero(
            meta, esc=esc, inline=inline, report_date=report_date, official=official,
            threat_cls=tcls, doc_mode=doc_mode, news_card=False,
            archived=meta.get("screen_archived") or False, card_targets=card_targets)
        screen_hero_html += SCR.news_pointer()
    # معرّف قسم المستجدات الرسمية (م-32): يدخل فهرس المحتويات والربط الداخلي.
    if '<section class="sc-official-cards"' in screen_hero_html:
        screen_hero_html = screen_hero_html.replace(
            '<section class="sc-official-cards"',
            '<section class="sc-official-cards" id="sec-official" aria-labelledby="h-official"', 1)
        screen_hero_html = screen_hero_html.replace(
            '<h2 class="sc-h2">المستجدات الرسمية</h2>',
            '<h2 class="sc-h2" id="h-official">المستجدات الرسمية</h2>', 1)
    if '<section class="print-map' in hero_map_html:
        hero_map_html = hero_map_html.replace(
            '<section class="print-map', '<section id="sec-map" class="print-map', 1)
    ledger_html = (
        f'<div class="glossary">السجل التراكمي: '
        f'<a class="bidi" href="{esc(meta["ledger_url"])}" target="_blank" rel="noopener noreferrer">{esc(meta["ledger_url"])}</a></div>'
        if meta.get("ledger_url") else ""
    )
    doc = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}{f' — {esc(date_label)}' if date_label else ''}</title>
<meta name="description" content="{esc(meta.get("description") or "تقرير أمني بحري يومي")}">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="referrer" content="no-referrer">
<script>document.documentElement.className='js';</script>
<script>(function(){{var f=function(){{var els=[document.querySelector('.topbar'),document.querySelector('.site-nav')].filter(Boolean);if(!els.length)return;var c=window.scrollY>140;els.forEach(function(e){{e.classList.toggle('is-compact',c)}})}};var g=function(){{f();window.addEventListener('scroll',f,{{passive:true}})}};if(document.readyState==='loading'){{document.addEventListener('DOMContentLoaded',g)}}else{{g()}}}})();</script>
<link rel="stylesheet" href="{FONT_LINK}">
<style>{DESIGN_TOKENS}{STYLE}{TOC_CSS}{BLK.STYLE_BLOCKS}{DAYLIGHT}{LINK_RULE}</style>
</head>
<body>
<div class="topbar no-print">
  <div class="topbar-inner">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true">{icon("shield")}</div>
      <div class="brand-txt">
        <div class="brand-title">{esc(title)}</div>
        <div class="brand-sub">{esc(sub)}</div>
      </div>
    </div>
    <div class="topbar-spacer"></div>
    <div class="tb-meta">
      {f'<span class="chip">{esc(date_label)}</span>' if date_label else ''}
      {_additions_return_link(report_date) if mode == "additions" else ''}
    </div>
  </div>
</div>

<div class="wrap">
  <header class="masthead">
    <h1>{esc(normalize_daily_title(meta.get("headline")) or title)}</h1>
    {threat_html}
    <div>
      <p class="lede">{codes.demote(esc(_public_text(meta.get("lede") or "")), report_date, official)}</p>
      <div class="masthead-meta">{"".join(chips)}</div>
    </div>
  </header>

  {cls_html}
  {decision_html}
  @@TOC@@
  {kpi_html}
  {screen_hero_html}
  {hero_map_html}
  {notice_html}
  <main>
    {changes_html}
    {"".join(body)}
    {appendix_map}
  </main>

  <footer class="foot">
    <b>ملاحظة مهنية:</b> {inline(meta.get("footer_note") or "هذا التقرير يعتمد على المصادر المعلنة فقط. لا تُجمع البلاغات كعدد هجمات، ولا يُنسب أي فعل إلى جهة إلا وفق مصدر رسمي مباشر.", defs)}
    <br><b>وقت الإصدار:</b> <b>{esc(generated_display)}</b> — <b>المرجع الزمني:</b> UTC.
    {ledger_html}
  </footer>
</div>
<script>{SCRIPT}</script>
</body>
</html>"""
    # فهرس المحتويات (م-32): يُشتق من الوثيقة المجمّعة فعليًا بعد الرسم، فيغطي كل
    # قسم في أي نمط (تقرير · إضافات) ولا يتباعد عن الصفحة بأي قائمة ثابتة.
    _toc = []
    if decision_html:
        _toc.append(("sec-decision", "أهم الأخبار"))
    for _m in re.finditer(r'<section[^>]*\bid="(sec-[^"]+)"[^>]*>(.*?)</section>', doc, re.S):
        _h = re.search(r"<h2[^>]*>(.*?)</h2>", _m.group(2), re.S)
        if not _h:
            continue
        _tt = re.sub(r"<[^>]+>", "", _h.group(1)).strip()
        if _tt and _m.group(1) not in [x[0] for x in _toc]:
            _toc.append((_m.group(1), _tt))
    for _sid, _lab in (("sec-official", "المستجدات الرسمية"), ("sec-map", "خريطة القطاعات"),
                       ("sec-glossary", "قاموس الرموز والمصطلحات")):
        if f'id="{_sid}"' in doc and _sid not in [x[0] for x in _toc]:
            _toc.append((_sid, _lab))
    _toc_html = ""
    if len(_toc) > 2:
        _toc_html = ('<nav class="toc no-print" aria-label="فهرس المحتويات">'
                     '<span class="toc-l">المحتوى</span>'
                     + "".join(f'<a href="#{_s}">{esc(_t)}</a>' for _s, _t in _toc) + "</nav>")
    doc = doc.replace("@@TOC@@", _toc_html)

    # لا مرساة مكسورة (عقد الربط): كل رابط داخلي يجب أن يجد عنصره في هذه الصفحة.
    # وما نُقل إلى صفحة الإضافات (سياسة الأقسام 2026-10-28) يُوجَّه إليها صراحةً.
    _ids = set(re.findall(r'id="([^"]+)"', doc))

    def _href(m):
        h = m.group(1)
        if h.startswith("#") and h[1:] and h[1:] not in _ids:
            if h == "#sec-00":
                return 'href="/additions.html#sec-00"'
            return 'data-no-anchor="1"'
        return m.group(0)

    doc = re.sub(r'href="(#[^"]+)"', _href, doc)

    # سياسة عرض الرموز (2+5): تبسيط شامل لكل ما هو خارج قسم الوقائع
    doc = codes.demote_page(doc, report_date, official)
    doc = _outside_special(_public_text, doc)
    doc = _outside_special(redact_internal_grade_codes, doc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = _outside_special(isolate_ltr, doc)
    # ك-408: بعد عزل الرموز اللاتينية تبقى مسافة بين الرمز وعلامة الترقيم التالية («UKMTO ،» · «UTC .»)،
    # وهي مخالفة صياغة مانعة. التطبيع يلصق العلامة بالرمز مع عبور حدود الوسوم بلا مساس ببنية الصفحة.
    doc = _outside_special(tighten_ltr_punct, doc)
    # م-16: تقسيم فقرة «تحديث» الكثيفة إلى بنود مع تمييز العنوان (كل الإصدارات).
    doc = _outside_special(structure_update_paragraphs, doc)
    # طبقة الشاشة تُحقن بعد العزل: isolate_ltr يعمل على نص كل ما بين الوسوم فيفسد CSS وJS (مثل UTC وأسماء الخطوط)
    doc = doc.replace("</style>", SCR.SCREEN_CSS + "</style>", 1)
    # العنوان في وسم title نص صرف: isolate_ltr يلفّ الأسماء اللاتينية فيه بوسوم span فتظهر وسومًا في تبويب المتصفح
    doc = re.sub(r"<title>.*?</title>",
                 lambda m: re.sub(r'</?span[^>]*>', "", m.group(0)), doc, count=1, flags=re.S)
    doc = doc.replace("</body>", f"<script>{SCR.SCREEN_JS}</script>\n</body>", 1)
    out_path.write_text(doc, encoding="utf-8")
    return out_path, len(sections)


LTR_PATTERNS = [
    r"\b\d{6}Z\s*[–—-]\s*\d{6}Z\b",                         # نطاق الفترة كاملًا في عزل واحد
    r"\b\d{4,6}Z(?:\s+[A-Z]{3}\s*\d{2})?\b",                       # DTG: 180400Z OCT 26
    r"\b\d{1,3}[-°]\d{1,2}(?:\.\d+)?['′]?\s*[NS]\b",               # 26-16.8N
    r"\b[NS]\s?\d{1,3}[°-]\d{1,2}(?:\.\d+)?['′]?",                  # N 057°40.65′
    r"\b\d{1,3}[-°]\d{1,2}(?:\.\d+)?['′]?\s*[EW]\b",               # 056-08.6E
    r"\b[EW]\s?\d{1,3}[°-]\d{1,2}(?:\.\d+)?['′]?",                  # E 21.48°
    r"\b(?:MN|EST)-\d{4}-\d{2}-\d{2}-\d{2}\b",  # رمز واقعة أو تقدير كاملًا في كتلة LTR واحدة
    r"\bIMO\s?\d{6,7}\b", r"\bMMSI\s?\d{8,9}\b",
    r"\bUKMTO\s?\d{2,3}\s?[-–]\s?\d{2}\b", r"\bNAVAREA\s+[IVX]+\s+\d{2,3}/\d{2}\b",
    r"\b\d{2,3}/\d{2}\b", r"\b[A-Z][A-Z0-9]{2,}(?:\s+[A-Z0-9]{2,})*\b",
]
_LTR_RE = None
_PERIOD_RE = re.compile(r"^\d{6}Z\s*[–—-]\s*\d{6}Z$")



def _outside_special(transform, html):
    """يطبّق معالجة نصية على HTML **خارج** كتل style وscript فقط.

    عطل ك-413: كانت معالجة الترقيم تُزيل المسافة قبل المحدد في CSS فيتحوّل
    «.hmap-svg .mp-dot» إلى «.hmap-svg.mp-dot» (محدد مركّب لا يطابق شيئًا)،
    وكان عزل النصوص اللاتينية يحقن <span> داخل كتل CSS فيفسد الخطوط.
    """
    parts = re.split(r"(<(?:style|script)\b[^>]*>.*?</(?:style|script)>)", html, flags=re.S | re.I)
    return "".join(p if i % 2 else transform(p) for i, p in enumerate(parts))


def isolate_ltr(html: str) -> str:
    """يغلّف المعرّفات والأوقات والإحداثيات والأسماء اللاتينية بكتلة LTR معزولة.

    يمنع انقلاب ترتيب الإحداثيات والرموز عند العرض في سياق عربي RTL.
    """
    global _LTR_RE
    if _LTR_RE is None:
        _LTR_RE = re.compile("|".join(f"(?:{p})" for p in LTR_PATTERNS))
    kept = []

    def _keep_bdi(m):
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"

    # لا نعيد تغليف bdi الموجود، خصوصًا شريحة الفترة التي يجب أن تبقى عزلًا واحدًا.
    protected = re.sub(
        r'<bdi\b[^>]*\bdir=["\']ltr["\'][^>]*>.*?</bdi>|'
        r'<bdi\b[^>]*\bclass=["\'][^"\']*\bbidi\b[^"\']*["\'][^>]*>.*?</bdi>',
        _keep_bdi,
        html,
        flags=re.S,
    )
    parts = re.split(r"(<[^>]+>)", protected)

    def _wrap(m):
        raw = re.sub(r"\s*([–—-])\s*", r"\1", m.group(0))
        if _PERIOD_RE.fullmatch(raw):
            return f'<bdi class="bidi" dir="ltr">{raw}</bdi>'
        return f'<span class="ltr">{m.group(0)}</span>'

    for k, part in enumerate(parts):
        if not part or part.startswith("<"):
            continue
        parts[k] = _LTR_RE.sub(_wrap, part)
    out = "".join(parts)
    return re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--meta", required=True, help="ملف بيانات الواجهة (إلزامي)")
    a = ap.parse_args()
    md_path = Path(a.md)
    if not md_path.exists():
        print(f"خطأ: ملف التقرير غير موجود: {md_path}", file=sys.stderr)
        return 2
    meta_path = Path(a.meta)
    if not meta_path.exists():
        print(f"خطأ: ملف الواجهة غير موجود: {meta_path}", file=sys.stderr)
        return 2
    load_section_policy(meta_path)
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"خطأ: ملف الواجهة ليس JSON صالحًا ({e}).", file=sys.stderr)
        return 2
    try:
        p, count = build(md_path, Path(a.out), meta)
    except BuildError as e:
        print(f"فشل البناء: {e}", file=sys.stderr)
        return 3
    finally:
        # بند 15 (19 أكتوبر 2026): تفريغ سياق الرموز بعد كل جولة بناء،
        # فلا يتسرّب تاريخ إصدار إلى جولة تالية عند بناء عدة تقارير في العملية نفسها.
        BLK.reset_code_context()
    print(f"OK {p} ({p.stat().st_size} bytes, {count} أقسام)")
    return 0


def tighten_ltr_punct(html: str) -> str:
    """يلصق علامة الترقيم بالرمز اللاتيني/الرقمي السابق لها عبر حدود الوسوم.

    ك-408: بعد عزل الرموز اللاتينية داخل وسوم، تظهر مسافة بين الرمز وعلامة الترقيم
    («UKMTO ،» · «UTC .» · «EST-2026-10-31-01 :») وهي مخالفة صياغة مانعة في بوابة
    عيوب الصياغة. الوسوم تُستبدل بمحرف حاجز مؤقت، ثم يُزال الفراغ وحده، ثم تُستعاد
    الوسوم كما هي — فلا يتغيّر أي وسم أو نص سوى الفراغ المخالف.
    """
    parts = re.split(r"(<[^>]*>)", html)
    token = "\u0000"
    tags: list[str] = []
    buffered: list[str] = []
    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            tags.append(part)
            buffered.append(token)
        else:
            buffered.append(part)
    text = "".join(buffered)
    # الفاصل قد يكون مسافة عادية أو مسافة غير فاصلة (&nbsp;) تُستعمل للتحكم في اتجاه النص
    text = text.replace("&nbsp;", "\u00a0")
    pattern = re.compile(r"([A-Za-z0-9])(\u0000*)[ \t\u00a0]+(\u0000*)([،.:؛!؟])")
    text = pattern.sub(lambda m: m.group(1) + m.group(2) + m.group(3) + m.group(4), text)
    out: list[str] = []
    pending = iter(tags)
    for chunk in text.split(token):
        out.append(chunk)
        out.append(next(pending, ""))
    return "".join(out)


if __name__ == "__main__":
    sys.exit(main())


