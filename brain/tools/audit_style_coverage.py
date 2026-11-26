#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قياس تغطية بوابة الأسلوب على كل سطح يقرأه القارئ.

القاعدة (ط15): كل نص ثابت يظهر للقارئ يدخل في مدى بوابة الأسلوب. هذه الأداة تُثبت ذلك أو تعلن الثغر:
تُحوّل كل سطح إلى نص، وتُمرّره على بوابة الأسلوب وبوابة الألفاظ المصطنعة، وتعرض جدولًا:
السطح · المصدر · فُحص؟ · النتيجة.

الأسطح: المتن · ملف الواجهة (القاموس وأهم الأخبار المتعلقة بالأمن البحري) · رسالة تلغرام · صفحة التقرير ·
صفحة المصادر · الصفحة الرئيسية · PDF (قياس محدود: استخراج العربي يعكس الحروف).

رموز الخروج: 0 كل الأسطح مغطاة · 2 سطح غير مغطى أو مانع · 70 انهيار.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import html.parser
import unicodedata as _ud

def norm_derived(t: str) -> str:
    """تطبيع النص المشتق (HTML/PDF): إزالة علامات الاتجاه والكشيدة والتشكيل وتصحيح
    مواضع الترقيم — لأن الاستخراج العربي يُدخل مسافات وحروفًا زائدة لا وجود لها في المصدر."""
    # NFKC expands U+2026 (ellipsis) to three ASCII dots, which would turn a
    # legitimate truncation marker into the adjacent-punctuation defect "..".
    ellipsis = "\ue000"
    t = (t or "").replace("…", ellipsis)
    t=_ud.normalize("NFKC", t)
    t=re.sub(r"[\u0640\u200b-\u200f\u202a-\u202e\u2066-\u2069\u064b-\u0652\u0670]", "", t)
    t=re.sub(r"\s+([،.:؛؟!])", r"\1", t)
    return re.sub(r"[ \t]{2,}", " ", t).replace(ellipsis, "…")

import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SITE = Path(os.environ.get("SITE") or os.environ.get("SITE_DIR") or (Path.home() / "seawatch"))
TODAY = date.today().isoformat()
TMP = Path(tempfile.gettempdir()) / "style-coverage"


TAG_MARK = "\u0001"
TAG_MARK_INLINE = "\u0002"
_PUNCT = ".،;؛:!؟"
# الوسوم الوسيطة لا تُنتج فاصلًا في العرض؛ حذفها يطابق innerText في المتصفح.
_INLINE_TAGS = {
    "span", "bdi", "bdo", "b", "i", "em", "strong", "a", "code", "small", "sup", "sub",
    "mark", "u", "s", "strike", "abbr", "acronym", "cite", "q", "time", "kbd", "samp",
    "var", "wbr", "font", "label", "big", "tt", "data", "dfn", "ins", "del", "nobr",
}


def _tag_to_mark(m):
    """وسم وسيط ⇒ حذف · وسم كتلي ⇒ فاصل سطر (ك-4م1)."""
    g = re.match(r"<\s*/?\s*([A-Za-z0-9]+)", m.group(0))
    return TAG_MARK_INLINE if (g and g.group(1).lower() in _INLINE_TAGS) else TAG_MARK


def _tag_mark_to_text(s: str) -> str:
    """يترجم أثر الوسوم إلى نصٍّ كما يُقرأ في المتصفح.

    ك-4م2 (2026-11-02): قياس حيّ أثبت أن تحويل كل وسم إلى فاصل يُنتج نصوصًا لا يراها
    القارئ: (1) فراغًا قبل علامة الترقيم إذا كان الوسم بين الرمز والعلامة
    («B/2) .» في الاستخراج · 0 في المتصفح)؛ (2) حرفًا عربيًا مضاعفًا إذا التصق نصُّ
    عنصرين متجاورين («جدًا» + «التقرير» ⇒ «االتقرير» · 0 في المتصفح).

    القواعد: الوسم الوسيط بين حرفين ⇒ مسافة · الوسم الوسيط قبل ترقيم ⇒ حذف مع فراغه ·
    ما سوى ذلك من الوسوم الوسيطة ⇒ حذف بلا فاصل (كما في العرض) · الوسم الكتلي ⇒ فاصل سطر.
    """
    # صنف الحرف: ء-ي وٱ-ۓ حروف عربية فقط — تُستثنى علامات الترقيم
    # العربية (، U+060C · ؛ U+061B · ؟ U+061F) ولو وقعت داخل المدى ؀-ۿ،
    # وإلا حُسبت حرفًا فأُدرج فراغ قبلها (عطل قياس رُصد 2026-11-02 وأُصلح).
    s = re.sub(r"(?<=[\w\u0621-\u064A\u0671-\u06D3])" + TAG_MARK_INLINE
               + r"+(?=[\w\u0621-\u064A\u0671-\u06D3])", " ", s)
    s = re.sub(r"[ \t\u00a0]*(?:" + TAG_MARK + "|" + TAG_MARK_INLINE + r")+[ \t\u00a0]*(?=[" + re.escape(_PUNCT) + r"])",
               "", s)
    s = s.replace(TAG_MARK_INLINE, "")
    return s.replace(TAG_MARK, "\n")


class _HtmlText(html.parser.HTMLParser):
    """مستخرج نص من HTML بمحلّل حقيقي.

    السبب الجذري (ك-625): الاعتماد على تعبير نمطي لإزالة `<script>…</script>` ينكسر
    إذا احتوى كود الصفحة تسلسل إغلاق أو تعليقًا داخليًا، فيتسرّب كود JS إلى نص القياس
    فيُقرأ مصفوفة JS كأنها «جملة» طويلة، ويُمنع السطح خطأً. المحلّل الحقيقي يتجاهل
    سكربتات وأنماط الصفحة دائمًا، ويحفظ كل صف جدول سطرًا واحدًا بفواصل أنابيب كما
    يشترط عقد بوابة عيوب الصياغة (تكرار الخلية بنية جدول لا قالب جملة).
    """

    SKIP = {"script", "style", "noscript", "template"}
    # عناصر الواجهة المتكررة في كل صفحة (شريط التنقل، الترويسة، التذييل، رابط التخطّي)
    # ليست نصًا تحريريًا: قياسها في بوابة الأسلوب يجعل واجهة الصفحة «جملة» واحدة طويلة
    # فيمنع السطح خطأً. تغطيتها موكلة إلى حراس التنقّل والروابط المستقلة.
    CHROME_TAGS = {"nav", "footer", "header"}
    # نطاق بوابة الأسلوب هو النثر التحريري. تُستبعد عناصر الواجهة المتكررة (شريط
    # التنقّل · الترويسة · التذييل · شرائح البيانات الوصفية)، ومنطقتا الخريطة والسجل:
    # الأولى رسوم وعلامات مواقع بلا ترقيم فتُقاس «جملة» طويلة، والثانية صفوف بيانات
    # (تاريخ · تصنيف · ملخص) تتشابه بعد تطبيع الأرقام فتُقرأ «قالبًا متكررًا».
    # كلتاهما محروستان بحراس مستقلة: حراس الخريطة وحراس عدّ الدفتر والأرشيف.
    CHROME_HINT = ("skip", "topbar", "site-nav", "sn-foot", "foot", "chrome", "toolbar",
                   "chip", "sb-code", "meta-strip", "kpi", "stat", "badge",
                   "map", "legend", "mp-", "ar-row", "ar-extra", "registry", "month-rows")
    BLOCK = {"li", "p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "section",
             "article", "ul", "ol", "blockquote", "figcaption", "br"}
    CELL = {"td", "th"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.rows: list[str] = []
        self._skips: list[str] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    @classmethod
    def _is_chrome(cls, tag: str, attrs) -> bool:
        if tag in cls.CHROME_TAGS:
            return True
        hints = " ".join(v for k, v in attrs if k in ("class", "id", "role") and v).lower()
        return any(h in hints for h in cls.CHROME_HINT)

    def _sep(self) -> None:
        # فاصل مسافة فقط: النص الأصلي يحمل علامة قطعه، وإضافة علامة من الأداة تُنشئ
        # ترقيمًا متجاورًا يخالف بوابة عيوب الصياغة. الفاصل ضروري لأن لصق «…خصب.» بـ
        # «يطلب…» يمنع حارس الطول من تقسيم الجملتين فيقيسهما جملة واحدة.
        if "".join(self.parts).rstrip():
            self.parts.append("\n")

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP or self._is_chrome(tag, attrs):
            self._skips.append(tag)
            return
        if self._skips:
            return
        if tag == "tr":
            self._row = []
        elif tag in self.CELL and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in self._skips:
            self._skips.remove(tag)
            return
        if self._skips:
            return
        if tag in self.CELL and self._cell is not None:
            txt = re.sub(r"\s+", " ", "".join(self._cell)).strip()
            if txt and self._row is not None:
                self._row.append(txt)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(" | ".join(self._row))
            self._row = None
        elif tag in self.BLOCK:
            self._sep()

    def handle_data(self, data):
        if self._skips or not data.strip():
            return
        txt = re.sub(r"\s+", " ", data)
        # لصق كتلتين بلا فاصل يدمج جملتين في واحدة (عيب ك-625): «…موقع محدد.» +
        # «المسار المتأثر…» يُقاس جملة واحدة. تُضاف مسافة عند حدود كتل النص.
        # ك-628: لا تُدرج مسافة قبل علامة ترقيم، وإلا نشأ «… » .» وهو عيب «مسافة قبل
        # علامة ترقيم» الذي يمنع السطح في بوابة عيوب الصياغة.
        PUNCT = ".!؟:؛,،؛؟٭%.,»)]}"
        if self._cell is not None:
            if self._cell and not self._cell[-1].endswith(" ") and not txt.startswith(" ") \
                    and txt[:1] not in PUNCT:
                self._cell.append(" ")
            self._cell.append(txt)
        else:
            cur = "".join(self.parts)
            if cur and not cur.endswith((" ", "\n")) and not txt.startswith(" ") \
                    and txt[:1] not in PUNCT:
                self.parts.append(" ")
            self.parts.append(txt)


def strip_html(raw: str) -> str:
    """يحوّل HTML إلى نص، ويحفظ كل صف جدول في سطر واحد بفواصل أنابيب."""
    ex = _HtmlText()
    ex.feed(raw)
    ex.close()
    body = re.sub(r"[ \t]{2,}", " ", "".join(ex.parts)).strip()
    return body + "\n" + "\n".join(ex.rows)


def flatten_json(obj, out: list[str], card: bool = False) -> None:
    # قيم بطاقات المؤشرات (hero_kpis وofficial_cards) حقول مُهيكلة لا صياغة إنشائية: تُوسم بـ«[بطاقة]»
    # كما في سطح HTML (قرار 2026-11-12)، فلا يُحسب تكرار «آخر تحديث المصدر» قالب جملة مانعًا.
    if isinstance(obj, str):
        out.append(("[بطاقة] " + obj) if card else obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            flatten_json(v, out, card or k in ("hero_kpis", "official_cards"))
    elif isinstance(obj, list):
        for v in obj:
            flatten_json(v, out, card)


def _disabled_producers() -> dict:
    """يقرأ المانيفست ويُعيد خطواته المعطّلة — أساسُ استثناء السطح بقرار المالك.

    السبب: إذا عطّل المالك الخطوة المُنتِجة لسطح (مثل الطباعة)، فغياب مخرجها ليس ثغرًا في
    التغطية بل قرارٌ مُعلن. يُقرأ القرار من المانيفست نفسه لا من قائمة يدوية، ويعود السطح
    تلقائيًا إلى القياس عند إعادة تفعيل الخطوة.
    """
    out = {}
    try:
        rb = json.loads((BASE / "runbook" / "runbook.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return out

    def walk(o):
        if isinstance(o, dict):
            if o.get("id") and o.get("disabled"):
                out[str(o["id"])] = str(o.get("disabled_reason") or "خطوة معطّلة بقرار المالك")
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(rb)
    return out


def _load_manifest() -> dict:
    """يقرأ مانيفست التشغيل؛ غيابه لا يُنشئ استثناءً تلقائيًا."""
    path = BASE / "runbook" / "runbook.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def deferred_producer_ids(manifest: dict, gate_id: str) -> dict[str, dict]:
    """يعيد المنتجات المؤجلة فقط إذا أثبت المانيفست أنها بعد البوابة الحالية.

    لا يكفي وجود اسم المنتج في قائمة يدوية: يجب أن يعلن عقد البوابة المنتج والسبب
    وتاريخ السريان، ثم يثبت ترتيب `producer` بعد `gate` في قائمة الخطوات،
    وخطوة إنفاذ لاحقة حقيقية غير معطّلة تحمل عقد الفحص المعلن.
    """
    steps = manifest.get("steps") if isinstance(manifest, dict) else None
    if not isinstance(steps, list):
        return {}
    positions = {
        str(step.get("id")): index
        for index, step in enumerate(steps)
        if isinstance(step, dict) and step.get("id")
    }
    if gate_id is not None and gate_id not in positions:
        return {}
    # gate_id=None ⇒ وضع الاتحاد: تُحتسب إعلانات كل الخطوات، وكل إعلان يبقى مشروطًا
    # بترتيبه وبوجود خطوة إنفاذ لاحقة حقيقية (لا تخفيف للعقد).
    out: dict[str, dict] = {}
    step_by_id = {
        str(step.get("id")): step
        for step in steps
        if isinstance(step, dict) and step.get("id")
    }
    for step in steps:
        if not isinstance(step, dict):
            continue
        if gate_id is not None and str(step.get("id")) != gate_id:
            continue
        for declaration in step.get("deferred_surfaces") or []:
            if not isinstance(declaration, dict):
                continue
            producer = str(declaration.get("producer") or "").strip()
            if not producer or producer not in positions:
                continue
            producer_index = positions[producer]
            gate_index = positions[str(step.get("id"))]
            if producer_index <= gate_index:
                continue
            enforced_by = str(declaration.get("enforced_by") or "").strip()
            if not enforced_by or enforced_by not in positions:
                continue
            enforcement_index = positions[enforced_by]
            if enforcement_index <= producer_index:
                continue
            enforcement_step = step_by_id.get(enforced_by) or {}
            if not _is_real_surface_enforcer(enforcement_step, declaration):
                continue
            out[producer] = {
                **declaration,
                "gate": gate_id,
                "gate_index": gate_index,
                "producer_index": producer_index,
                "enforcement_index": enforcement_index,
            }
    return out


_ENFORCEMENT_MARKERS = {
    "surface-coverage": ("audit_style_coverage.py",),
    "telegram-delivery": ("check_telegram_delivery.py",),
}


def _is_real_surface_enforcer(step: dict, declaration: dict) -> bool:
    """يثبت أن خطوة الإنفاذ المعلنة تنفذ عقدًا معروفًا وليست اسمًا حرًا."""
    if not isinstance(step, dict) or step.get("disabled"):
        return False
    contract = str(declaration.get("enforcement_contract") or "surface-coverage").strip()
    markers = _ENFORCEMENT_MARKERS.get(contract)
    if not markers:
        return False
    payload = json.dumps(step, ensure_ascii=False)
    return any(marker in payload for marker in markers)


def classify_missing_surface(surface: dict, deferred: dict[str, dict], disabled: dict[str, str],
                             error: str) -> dict[str, object]:
    """يصنف سطحًا غائبًا من عقد المانيفست فقط، لا من نص الفحص."""
    producer = str(surface.get("producer") or "").strip()
    if producer and producer in disabled:
        return {
            "status": "مستثنى بقرار المالك",
            "blocked": False,
            "note": f"الخطوة {producer} معطّلة: {disabled[producer]} — {error}",
        }
    if producer and producer in deferred:
        declaration = deferred[producer]
        enforcement = str(declaration.get("enforced_by") or "—")
        return {
            "status": "مؤجل معلن",
            "blocked": False,
            "note": (f"{declaration.get('reason', 'تأجيل معلن')} — "
                      f"{producer} بعد {declaration.get('gate', '—')}، "
                      f"والإنفاذ في {enforcement} — {error}"),
        }
    return {"status": "غير مغطى", "blocked": True, "note": error}


def classify_evaluated_surface(style_rc: int, prose_rc: int) -> dict[str, object]:
    """يصنف سطحًا موجودًا؛ أي فشل أسلوبي أو نثري مانع فشلًا مغلقًا."""
    covered = style_rc == 0 and prose_rc in (0, 1)
    return {"status": "مغطى" if covered else "مانع", "blocked": not covered}


def resolve_deferred(manifest: dict, explicit_gate: str, current_gate: str | None) -> dict[str, dict]:
    """قرار التأجيل: الضيق عند تمرير هوية صريحة فقط.

    الهوية المستدلة (current_gate) لا تُسقط إعلانًا معلَنًا في خطوة أخرى؛ وكل إعلان
    يبقى مشروطًا بترتيب منتجه بعد خطوة إعلانه وبوجود خطوة إنفاذ لاحقة حقيقية.
    """
    if explicit_gate:
        return deferred_producer_ids(manifest, explicit_gate)
    return deferred_producer_ids(manifest, None)


def _current_step_id(manifest: dict) -> str | None:
    """يستدل على خطوة G045 من ذكر ملف الأداة في أمرها؛ لا يثبت هويةً صامتة."""
    steps = manifest.get("steps") if isinstance(manifest, dict) else None
    if not isinstance(steps, list):
        return None
    matches = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        if "audit_style_coverage.py" in json.dumps(step, ensure_ascii=False):
            if step.get("id"):
                matches.append(str(step["id"]))
    return matches[0] if len(matches) == 1 else None


def run_gate(cmd: list[str], text_file: Path) -> tuple[int, list[str]]:
    r = subprocess.run(cmd + [str(text_file)], capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    keys = [ln.strip() for ln in out.splitlines()
            if any(k in ln for k in ("✗", "✘", "مخالفة", "الألفاظ المصطنعة", "النتيجة:", "مقبول"))]
    return r.returncode, keys[:6]


def surfaces(day: str) -> list[dict]:
    _tg = BASE / "tools" / "make_tg_digest.py"
    if _tg.exists():      # سطح مشتقٌّ من المتن والواجهة: يُبنى من المصدر قبل الفحص، فلا يُحكم على نسخة قديمة
        subprocess.run([sys.executable, str(_tg), "--date", day], capture_output=True, text=True)

    off = _disabled_producers()
    rows = [
        {"label": "المتن (التقرير)", "kind": "text", "path": BASE / "reports" / f"{day}-sectioned.md"},
        {"label": "ملف الواجهة (القاموس وأهم الأخبار المتعلقة بالأمن البحري)", "kind": "json",
         "path": BASE / "web" / "meta" / f"{day}.json"},
    ]
    # ك-467: الطباعة معطّلة بأمر المالك ⇒ لا يُقاس ملف PDF قديم ولا يمنع التسليم.
    if not ({"B020", "B030"} & set(off)):
        rows.append({"label": "PDF (قياس محدود)", "kind": "pdf", "producer": "B020",
                     "path": SITE / "dist" / "reports" / "pdf" / f"{day}.pdf"})
    rows += [
        {"label": "رسالة تلغرام", "kind": "html", "producer": "D030",
         "path": BASE / "logs" / f"tg-digest-{day}.html"},
        {"label": "صفحة التقرير", "kind": "html", "producer": "B010",
         "path": SITE / "dist" / "reports" / f"{day}.html"},
        {"label": "صفحة المصادر", "kind": "html", "path": SITE / "dist" / "sources.html"},
        {"label": "الصفحة الرئيسية", "kind": "html", "path": SITE / "dist" / "index.html"},
        {"label": "صفحة إضافات (ك-234)", "kind": "html", "path": SITE / "dist" / "additions.html"},
    ]
    return rows


def extract(s: dict, idx: int) -> tuple[Path | None, str]:
    p = s["path"]
    if not p.exists():
        return None, "المصدر غير موجود"
    tgt = TMP / f"{idx}.txt"
    if s["kind"] == "text":
        tgt.write_text(norm_derived(p.read_text(encoding="utf-8")), encoding="utf-8")
    elif s["kind"] == "json":
        vals: list[str] = []
        flatten_json(json.loads(p.read_text(encoding="utf-8")), vals)
        tgt.write_text("\n".join(vals), encoding="utf-8")
    elif s["kind"] == "html":
        _raw = p.read_text(encoding="utf-8", errors="replace")
        # وسم حقول البطاقات قبل التجريد: قيمة البطاقة حقل مُهيكل لا قالب جملة (قرار 2026-11-12).
        _raw = re.sub(
            r'<(?:div|span|p)[^>]*class="[^"]*\bk-(?:n|v|lay-l)\b[^"]*"[^>]*>(.*?)</(?:div|span|p)>',
            lambda mm: "\n[بطاقة] " + re.sub(r"<[^>]+>", "", mm.group(1)) + "\n",
            _raw, flags=re.S)
        tgt.write_text(strip_html(_raw), encoding="utf-8")
    else:
        r = subprocess.run(["pdftotext", "-layout", str(p), str(tgt)], capture_output=True, text=True)
        if r.returncode != 0:
            return None, "تعذّر استخراج نص PDF (pdftotext)"
    if not tgt.exists() or tgt.stat().st_size < 20:
        return None, "النص المستخرج فارغ"
    return tgt, ""


def pdf_link_proof(pdf_text: str, day: str) -> tuple[bool, str]:
    """إثبات أن PDF بُني من نصِّ الإصدار نفسه — بمدخلات لاتينية لا يمسّها استخراج العربي.

    السبب: استخراج نص PDF العربي يعكس الحروف ويفصلها، فقياس الألفاظ العربية عليه غير صالح بنيويًا.
    البديل الصادق: رموز البلاغ `MN-YYYY-MM-DD-NN` والمصطلحات اللاتينية تُستخرج سليمة،
    فوجودها في PDF هو ما يثبت أنه من النص المعتمد نفسه الذي مرّ على البوابة.
    """
    md = BASE / "reports" / f"{day}-sectioned.md"
    src = md.read_text(encoding="utf-8") if md.exists() else ""
    if not src:
        return False, "نص الإصدار غير موجود — لا يمكن الإسناد"
    codes = sorted(set(re.findall(r"MN-\d{4}-\d{2}-\d{2}-\d+", src)))
    # الروابط لا تُطبع في PDF بنصها، فلا تُحسب مفقودة: تُستثنى أولًا.
    prose = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", src)
    prose = re.sub(r"https?://\S+", " ", prose)
    _raw = re.findall(r"[A-Za-z][A-Za-z0-9._/-]{3,}", prose)
    # تجريد علامات الترقيم الختامية كي لا يُحسب الرمز ناقصًا بسبب نقطة نهاية الجملة
    toks = sorted({x for x in (r.rstrip("./-") for r in _raw) if len(x) >= 4})
    miss_codes = [c for c in codes if c not in pdf_text]
    miss_toks = [t for t in toks if t not in pdf_text]
    ratio = 1 - len(miss_toks) / max(1, len(toks))
    ok = not miss_codes and ratio >= 0.90
    note = (f"إسناد PDF: رموز البلاغ {len(codes) - len(miss_codes)}/{len(codes)} · "
            f"المصطلحات اللاتينية {round(ratio * 100)}% ({len(toks) - len(miss_toks)}/{len(toks)}) "
            f"· قياس الألفاظ العربية على PDF غير صالح بنيويًا (الاستخراج يعكس الحروف)")
    return ok, note


def main() -> int:
    ap = argparse.ArgumentParser(description="قياس تغطية بوابة الأسلوب لكل سطح")
    ap.add_argument("--date", default=TODAY)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gate-id", default=None,
                    help="هوية البوابة الحالية من المانيفست؛ الافتراضي يُستدل من الأداة")
    a = ap.parse_args()
    TMP.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest()
    gate_id = a.gate_id or _current_step_id(manifest)
    # غياب هوية البوابة لا يُلغي الإعلانات المعلَنة: تُحتسب بإعلانها وشرط إنفاذها.
    explicit_gate = str(getattr(a, "gate_id", "") or "")
    deferred = resolve_deferred(manifest, explicit_gate, gate_id)
    rows, blocked, uncovered, deferred_count = [], 0, 0, 0
    off = _disabled_producers()
    for i, s in enumerate(surfaces(a.date), 1):
        tgt, err = extract(s, i)
        if tgt is None:
            missing = classify_missing_surface(s, deferred, off, err)
            if missing["status"] == "مستثنى بقرار المالك":
                rows.append({"label": s["label"], "path": str(s["path"]),
                             "status": missing["status"], "note": missing["note"],
                             "style": "—", "prose": "—", "findings": []})
                continue
            if missing["status"] == "مؤجل معلن":
                deferred_count += 1
                rows.append({"label": s["label"], "path": str(s["path"]),
                             "status": "مؤجل معلن",
                             "note": missing["note"],
                             "style": "—", "prose": "—", "findings": []})
                continue
            uncovered += 1
            rows.append({"label": s["label"], "path": str(s["path"]), "status": "غير مغطى",
                         "note": missing["note"], "style": "—", "prose": "—"})
            continue
        sc, s_out = run_gate(["python3", str(BASE / "validators" / "check_style.py")], tgt)
        if s["kind"] == "pdf":
            # نثر PDF العربي: الاستخراج يعكس الحروف ويُدخل مسافات قبل الترقيم ⇒ حكم النثر عليه غير صالح بنيويًا
            pc, p_out = 0, "نثر PDF لا يُحكم عليه بالاستخراج — يُثبت بالإسناد (رموز البلاغ والمصطلحات اللاتينية)"
        else:
            # سطح سجل المصادر سطح مُهيكل: تكرار وسم الصف بنية سجل لا قالب جملة (قرار مُعلن 2026-11-01)
            _extra = ["--structured-registry"] if s["label"] == "صفحة المصادر" else []
            pc, p_out = run_gate(["python3", str(BASE / "validators" / "check_prose_defects.py")] + (_extra or ["--md"]), tgt)
        # بوابة المصطنعة تُرجع 1 للتحذير و2 للمنع (وهو سلوك البوابة نفسها في التسليم)
        if s["kind"] == "pdf":
            linked, note = pdf_link_proof(tgt.read_text(encoding="utf-8", errors="replace"), a.date)
            if not linked:
                blocked += 1
            rows.append({
                "label": s["label"], "path": str(s["path"]),
                "status": "مغطى بالإسناد" if linked else "مانع",
                "note": note,
                "style": "— (لا يُقاس على PDF)",
                "prose": "— (لا يُقاس على PDF)",
                "findings": [],
                "text_sha256": hashlib.sha256(tgt.read_bytes()).hexdigest()[:16],
            })
            continue
        evaluation = classify_evaluated_surface(sc, pc)
        ok = evaluation["status"] == "مغطى"
        if evaluation["blocked"]:
            blocked += 1
        note = ""
        rows.append({
            "label": s["label"], "path": str(s["path"]),
            "status": "مغطى" if ok else "مانع",
            "note": note,
            "style": "مقبول" if sc == 0 else f"منع ({sc})",
            "prose": "مقبول" if pc == 0 else ("تحذير (1)" if pc == 1 else f"منع ({pc})"),
            "findings": (s_out + p_out)[:6],
            "text_sha256": hashlib.sha256(tgt.read_bytes()).hexdigest()[:16],
        })

    if a.json:
        print(json.dumps({"date": a.date, "rows": rows}, ensure_ascii=False, indent=2))
    else:
        print(f"=== تغطية بوابة الأسلوب — {a.date} ===")
        print(f"{'السطح':<42} {'النتيجة':<14} {'الأسلوب':<10} {'المصطنعة':<10}")
        for r in rows:
            print(f"{r['label'][:41]:<42} {r['status']:<14} {r['style']:<10} {r['prose']:<10}  {r['note']}")
            for f in r.get("findings", [])[:3]:
                print(f"      · {f}")
        print(f"── الأسطح: {len(rows)} · مغطاة: {len(rows) - uncovered - blocked - deferred_count} · "
              f"مؤجلة معلنة: {deferred_count} · غير مغطاة: {uncovered} · مانعة: {blocked}")
    return 2 if (uncovered or blocked) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(70)
