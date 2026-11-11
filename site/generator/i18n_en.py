#!/usr/bin/env python3
"""ترجمة صفحة إصدار عربية مبنية إلى إنجليزية مع الحفاظ على الوسم والهيئة حرفيًا.

المبدأ: النسخة الإنجليزية ليست إعادة بناء، بل نفس صفحة الإصدار العربية بوسمها
وأقسامها وخريطتها وبطاقاتها وزراها، مع استبدال النصوص الظاهرة بالإنجليزية. هذا
يضمن تطابق التصميم والأزرار والخريطة بين النسختين بلا استثناء.

المكوّنات:
- ذاكرة ترجمة (TM): محاذاة متن التقرير العربي مع ترجمته المعتمدة سطرًا بسطر.
- معجم واجهة (glossary.json): نصوص لا تأتي من المتن (بطاقات الوقائع · وسوم الحالة ·
  تسميات المؤشرات · مفاتيح الخريطة · عدّادات). ويسقط عليه معجم الشريط الحاكم.
- معالجة أنماط: التواريخ والعدّادات والمقاطع المقتطعة بعلامة «…».

الاستعمال:
  python3 generator/i18n_en.py --date 2026-10-29 --report
  python3 generator/i18n_en.py --date 2026-10-29 --out /tmp/en.html
"""
from __future__ import annotations
import os
import argparse, json, pathlib, re, sys

import reader_grade_labels
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
def _root(env: str, base: pathlib.Path, *names: str) -> pathlib.Path:
    """جذر الشجرة: من متغيّر البيئة أو من مجلد شقيق معتمد (قابلية النقل)."""
    v = os.environ.get(env)
    if v:
        return pathlib.Path(v)
    for n in names:
        if (base / n).is_dir():
            return base / n
    return base / names[0]


_HOME = pathlib.Path(__file__).resolve().parents[2]
def _canonical_brain() -> pathlib.Path:
    """جذر الدماغ القانوني: قياس واحد عبر brain_root، ولا يُقبل الأرشيف (ك-571)."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from brain_root import brain_root as _br  # noqa: E402
    return _br()


BRAIN = _canonical_brain()
AR_MD = BRAIN / "reports"
I18N = ROOT / "sources" / "i18n" / "en"
SKIP_TAGS = {"script", "style", "code"}
TR_ATTRS = ("title", "aria-label", "alt", "placeholder", "data-label", "data-goto", "data-alt")
ARABIC = re.compile(r"[\u0600-\u06FF]")
# معرف تحذير UKMTO/NAVAREA بصيغة رقم-سنة؛ لا يجوز إدخاله من مفتاح جزئي.
ADVISORY_ID = re.compile(r"(?<![\d-])\d{3}-\d{2}(?![\d-])")
MONTHS_NUM = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "مايو": 5, "يونيو": 6,
    "يوليو": 7, "أغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}
MONTHS = {
    "يناير": "January", "فبراير": "February", "مارس": "March", "أبريل": "April",
    "مايو": "May", "يونيو": "June", "يوليو": "July", "أغسطس": "August",
    "سبتمبر": "September", "أكتوبر": "October", "نوفمبر": "November", "ديسمبر": "December",
}
COUNT_WORD = {"بندًا": "items", "بنود": "items", "بند": "item", "واقعة": "incidents", "وقائع": "incidents",
              "مصدرًا": "sources", "مصادر": "sources", "سفينة": "vessel", "سفن": "vessels",
              "يومًا": "days", "أيام": "days", "رمزًا": "codes", "رموز": "codes", "حدثًا": "events",
              "أحداث": "events", "تحذيرات": "rows", "خريطة": "map", "خرائط": "maps"}
COUNTER = re.compile(r"^(\d+)\s+(" + "|".join(COUNT_WORD) + r")\b\s*(·?)$")


def norm(s: str) -> str:
    s = (s or "").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


def _partial_key_safe(text: str, key: str) -> bool:
    """لا تسمح بمفتاح جزئي أن يضيف معرف تحذير غير موجود في العقدة."""
    text_ids = set(ADVISORY_ID.findall(text))
    key_ids = set(ADVISORY_ID.findall(key))
    if key_ids and not key_ids.issubset(text_ids):
        return False
    # ك-597: مفتاح قصير (حتى ثلاثة أحرف) لا يصلح للمطابقة الجزئية؛ فقد اختطف المدخل
    # «ع» = «AR» كل وحدة تبدأ بحرف العين (عناوين، عدد، عن…) فصارت ترجمتها «AR»
    # وظهرت نصوص عربية في الصفحة الإنجليزية. المطابقة التامة تبقى مسموحة للمفاتيح
    # القصيرة (زر اللغة «ع» مثلًا).
    if len(key.strip()) < 4:
        return False
    # ك-610: كلمة قاموس مفردة لا يجوز أن تبتلع بقية عقدة النص بالمطابقة الجزئية
    # («مادة خام» ← «material»). تُقبل المفردة بالمطابقة التامة أعلاه فقط؛ أما
    # المطابقة الجزئية فتحتاج عبارة متعددة الكلمات ذات معنى مستقل.
    return bool(re.search(r"\s", norm(key)))


def _crosses_ltr_boundary(text: str, key: str, ltr_tokens: list[str] | tuple[str, ...]) -> bool:
    """يرفض مفتاحًا جزئيًا يحمل اسمًا من وسم ltr خارج عقدة النص الحالية."""
    source = norm(text)
    candidate = norm(key)
    for raw_token in ltr_tokens:
        token = norm(raw_token)
        if not token:
            continue
        token_re = re.compile(
            rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", re.IGNORECASE
        )
        if token_re.search(candidate) and not token_re.search(source):
            return True
    return False


def plain(md_line: str) -> str:
    s = md_line.strip()
    s = re.sub(r"^#{1,6}\s+", "", s)
    s = re.sub(r"^>\s*", "", s)
    s = re.sub(r"^[-*]\s+", "", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    if s.startswith("|"):
        s = " · ".join(c.strip() for c in s.strip("|").split("|"))
    return norm(s)


def _line_kind(md_line: str) -> str:
    """Return the structural kind required for one aligned Markdown line."""
    s = md_line.strip()
    if s.startswith("|"):
        return f"table/{len(s.strip("|").split("|"))}"
    heading = re.match(r"^(#{1,6})\s+", s)
    if heading:
        return f"h{len(heading.group(1))}"
    if re.match(r"^[-*+]\s+", s):
        return "list"
    if s.startswith(">"):
        return "quote"
    return "text"


# NORMALIZE_HEAD_V1: ترويسة المستند المترجَم — doctype ثم سمات html صحيحة.
# كان بناء النسخة الإنجليزية يُسقط <!DOCTYPE html> فتقع الصفحة في وضع Quirks (BackCompat).
def normalize_document_head(page: str) -> str:
    m = re.search(r"<html([^>]*)>", page)
    if m:
        a = m.group(1)
        for k, v in (("lang", "en"), ("dir", "ltr")):
            a = re.sub(rf'{k}="[^"]*"', f'{k}="{v}"', a) if f"{k}=" in a else a + f' {k}="{v}"'
        if "data-lang=" not in a:
            a += ' data-lang="en"'
        page = page[: m.start()] + "<html" + a + ">" + page[m.end():]
    return re.sub(r"^(?:\ufeff)?\s*(?:<!doctype[^>]*>)?\s*", "<!DOCTYPE html>\n", page, count=1, flags=re.I)


def build_tm(
date: str) -> dict[str, str]:
    ar = (AR_MD / f"{date}-sectioned.md").read_text(encoding="utf-8")
    en = (I18N / f"{date}-sectioned.en.md").read_text(encoding="utf-8")
    A_raw = [x for x in ar.splitlines() if x.strip()]
    E_raw = [x for x in en.splitlines() if x.strip()]
    A = [plain(x) for x in A_raw]
    E = [plain(x) for x in E_raw]
    if len(A) != len(E):
        raise SystemExit(f"محاذاة غير ممكنة: عربي={len(A)} إنجليزي={len(E)}")
    kind_mismatches = [
        (idx, _line_kind(a), _line_kind(e))
        for idx, (a, e) in enumerate(zip(A_raw, E_raw))
        if _line_kind(a) != _line_kind(e)
    ]
    if kind_mismatches:
        details = "; ".join(
            f"idx {idx}: عربي={ar_kind} إنجليزي={en_kind}"
            for idx, ar_kind, en_kind in kind_mismatches[:12]
        )
        more = f"؛ و{len(kind_mismatches) - 12} اختلافًا آخر" if len(kind_mismatches) > 12 else ""
        raise SystemExit(f"أنواع الأسطر غير متطابقة: {details}{more}")
    tm = {a: e for a, e in zip(A, E) if a and a != e and ARABIC.search(a)}
    ar_rows = [x.strip() for x in ar.splitlines() if x.strip().startswith("|")]
    en_rows = [x.strip() for x in en.splitlines() if x.strip().startswith("|")]
    for al, el in zip(ar_rows, en_rows):
        for a, e in zip((norm(c) for c in al.strip("|").split("|")), (norm(c) for c in el.strip("|").split("|"))):
            if a and e and ARABIC.search(a):
                tm.setdefault(a, e)
    return tm


def chrome_glossary() -> dict[str, str]:
    import site_chrome  # استيراد مؤجّل

    src = pathlib.Path(site_chrome.__file__).read_text(encoding="utf-8")
    i = src.find("var I18N={ar:")
    if i < 0:
        return {}
    blk = src[i : src.find("})();", i)]
    def obj(tag: str) -> dict:
        # ك-597: الملف يكتب قسم الإنجليزية بلا علامات تنصيص (en:{) لا ("en":{)،
        # فكان المحلّل لا يجد القسم ويعيد معجمًا فارغًا، فتُهمَل كل أزواج الواجهة
        # الحاكمة بصمت. يُقبل الشكلان، ويُصرَّح بالفشل عند غياب القسمين.
        marker = blk.find(f'"{tag}"')
        if marker < 0:
            marker = blk.find(f"{tag}:")
        if marker < 0:
            raise ValueError(f"معجم الواجهة: قسم «{tag}» غير موجود في كتلة I18N")
        j = blk.find("{", marker)
        if j < 0:
            return {}
        k = blk.find("}", j)
        try:
            return json.loads(blk[j : k + 1])
        except Exception:
            return {}
    ar_obj, en_obj = obj("ar"), obj("en")
    # ك-597: الاتجاه الصحيح عربي ← إنجليزي؛ كان يعيد معرّف الوسم ← القيمة العربية،
    # وهو اتجاه غير صالح للترجمة فتُهمَل أزواج الواجهة الحاكمة حتى بعد قراءتها.
    return {norm(ar_obj[k]): en_obj[k] for k in ar_obj
            if isinstance(ar_obj[k], str) and ar_obj[k].strip()
            and isinstance(en_obj.get(k), str) and en_obj[k].strip()}


def confidence_grade_map() -> dict[str, dict[str, str]]:
    """الخريطة الحاكمة المشتركة لرمز الدرجة ووصفَي القارئ العربي والإنجليزي."""
    path = BRAIN / "appendices" / "confidence-grade-map.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    grades = data.get("grades")
    if not isinstance(grades, dict) or not grades:
        raise RuntimeError(f"خريطة الدرجات مفقودة أو فارغة: {path}")
    return grades


class _GlossaryEntries(dict[str, str]):
    def __init__(self, entries: dict[str, str], exact_match_only_entries=()):
        super().__init__(entries)
        self.exact_match_only_entries = frozenset(norm(k) for k in exact_match_only_entries)


def load_glossary() -> _GlossaryEntries:
    p = I18N / "glossary.json"
    data = {}
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
    raw_entries = data.get("entries") or {}
    if not isinstance(raw_entries, dict):
        raise ValueError("glossary entries must be an object")
    raw_exact_only = data.get("exact_match_only_entries", [])
    if not isinstance(raw_exact_only, list) or any(
        not isinstance(key, str) or not norm(key) for key in raw_exact_only
    ):
        raise ValueError("exact_match_only_entries must be a list of non-empty glossary keys")
    normalized_entries = {norm(k): v for k, v in raw_entries.items()}
    exact_only = {norm(key) for key in raw_exact_only}
    missing_exact = sorted(exact_only - set(normalized_entries))
    if missing_exact:
        raise ValueError(
            "exact_match_only_entries references missing glossary entries: "
            + ", ".join(missing_exact)
        )
    gl = _GlossaryEntries(normalized_entries, exact_only)
    gl.update(chrome_glossary())
    for entry in confidence_grade_map().values():
        gl[norm(entry["arabic"])] = entry["english"]
    # عناوين ووسوم hero_kpis تُرجَم من سجل البطاقات الحاكم، لا من جدول النص الرسمي.
    registry_path = BRAIN / "appendices" / "card_registry.json"
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        contract = registry.get("hero_kpis") or {}
        for card in contract.get("cards") or []:
            title, title_en = norm(card.get("title", "")), norm(card.get("title_en", ""))
            if title and title_en:
                gl[title] = title_en
            tag, tag_en = norm(card.get("tag", "")), norm(card.get("tag_en", ""))
            if tag and tag_en:
                gl[tag] = tag_en
            detail = card.get("detail") or {}
            ar, en = norm(detail.get("ar", "")), norm(detail.get("en", ""))
            if ar and en:
                gl[ar] = en
        for ar, en in zip(contract.get("risk_patterns") or [], contract.get("risk_patterns_en") or []):
            if ar and en:
                gl[norm(ar)] = en
        official = registry.get("official_cards") or {}
        component = official.get("page_component") or {}
        ar_label, en_label = norm(component.get("aria_label", "")), norm(component.get("aria_label_en", ""))
        if ar_label and en_label:
            gl[ar_label] = en_label
        for card in official.get("cards") or []:
            for ar_key, en_key in (("title", "title_en"), ("basis", "basis_en"),
                                   ("source_label", "source_label_en"), ("constraint", "constraint_en"),
                                   ("period", "period_en"), ("average", "average_en"),
                                   ("high", "high_en"), ("low", "low_en")):
                ar, en = norm(card.get(ar_key, "")), norm(card.get(en_key, ""))
                if ar and en:
                    gl[ar] = en
            for ar_badge, en_badge in zip(card.get("badges") or [], card.get("badges_en") or []):
                if ar_badge and en_badge:
                    gl[norm(ar_badge)] = en_badge
            for layer in (card.get("layers") or {}).values():
                for ar_key, en_key in (("label", "label_en"), ("value", "value_en"), ("source", "source_en")):
                    ar, en = norm(layer.get(ar_key, "")), norm(layer.get(en_key, ""))
                    if ar and en:
                        gl[ar] = en
    return gl


def _en_number_list(raw: str) -> str:
    """يحوّل قائمة أرقام عربية الفاصلة إلى قائمة إنجليزية: «39، 52» ← «39, 52»."""
    parts = [part.strip() for part in re.split(r"[،,]", raw) if part.strip()]
    return ", ".join(parts)


WARNING_COUNT_WORD = {
    "واحد": "one", "واحدة": "one", "اثنان": "two", "اثنتان": "two",
    "ثلاثة": "three", "ثلاث": "three", "أربعة": "four", "أربع": "four",
    "خمسة": "five", "خمس": "five", "ستة": "six", "ست": "six",
    "سبعة": "seven", "سبع": "seven", "ثمانية": "eight", "ثمان": "eight",
    "تسعة": "nine", "تسع": "nine", "عشرة": "ten", "عشر": "ten",
}


def _warning_count(raw: str) -> str | None:
    if raw.isdigit():
        return raw
    return WARNING_COUNT_WORD.get(raw)


_OVERALL_LEVEL_EN = {
    "مرتفع جدًا": "Very High",
    "مرتفع": "High",
    "متوسط": "Moderate",
    "منخفض": "Low",
}
_OVERALL_SECTORS_EN = {
    "مضيق هرمز، خليج عُمان، الخليج العربي":
        "the Strait of Hormuz, the Gulf of Oman and the Arabian Gulf",
    "مضيق هرمز، خليج عُمان، والخليج العربي":
        "the Strait of Hormuz, the Gulf of Oman and the Arabian Gulf",
    "مضيق هرمز وخليج عُمان والخليج العربي":
        "the Strait of Hormuz, the Gulf of Oman and the Arabian Gulf",
}


def _overall_sectors(raw: str) -> str | None:
    """Translate only the approved three-sector list; reject unknown free text."""
    return _OVERALL_SECTORS_EN.get(norm(raw))


def _en_date_phrase(raw: str) -> str | None:
    """ترجمة تاريخ عربي محدود إلى صيغة إنجليزية، دون تخمين نص حر."""
    value = norm(raw)
    if not re.fullmatch(r"\d{1,2}\s+(?:" + "|".join(MONTHS) + r")(?:\s+\d{4})?", value):
        return None
    for arabic, english in MONTHS.items():
        value = re.sub(rf"(?<!\S){re.escape(arabic)}(?!\S)", english, value)
    return value


def _en_month_year(raw: str) -> str | None:
    """ترجمة «شهر سنة» عربية («سبتمبر 2026») بلا تخمين نص حر (ك-595)."""
    value = norm(raw)
    if not re.fullmatch(r"(?:" + "|".join(MONTHS) + r")\s+\d{4}", value):
        return None
    for arabic, english in MONTHS.items():
        value = re.sub(rf"(?<!\S){re.escape(arabic)}(?!\S)", english, value)
    return value


_PLACE_EN = {"لما": "Lima"}


# ── ك-597: خرائط مغلقة ووحدات بطاقات تُبنى من المفردات الحاكمة ────────────────
_DIRECTION_EN = {
    "شمال غرب": "northwest",
    "شمال شرق": "northeast",
    "جنوب غرب": "southwest",
    "جنوب شرق": "southeast",
    "شمال": "north",
    "جنوب": "south",
    "شرق": "east",
    "غرب": "west",
    "وسط": "central",
}
_DIRECTION_ALT = "|".join(re.escape(k) for k in sorted(_DIRECTION_EN, key=len, reverse=True))
_DISTANCE_AR = r"(?:أميال بحرية|ميل بحري|ميلًا بحريًا|ميل بحريًا)"
_TERM_CACHE: dict[str, str] = {}
_ARABIC_LETTER = re.compile(r"[\u0600-\u06FF]")


def _gl_term(term: str) -> str | None:
    """قيمة المفردة من المعجم الحاكم (تُقرأ مرة واحدة لكل عملية)."""
    if not _TERM_CACHE:
        _TERM_CACHE.update({k: v for k, v in load_glossary().items() if isinstance(v, str)})
    value = _TERM_CACHE.get(norm(term))
    return value if value and value.strip() else None


def _cap_first(value: str) -> str:
    return value[:1].upper() + value[1:] if value else value


def _clean_en(value: str | None) -> str | None:
    """لا يُقبل مخرج ما زال يحمل حرفًا عربيًا (فشل مغلق بدل خلط اللغتين)."""
    if not value or _ARABIC_LETTER.search(value):
        return None
    return value.strip()


def _area_composite(raw: str, tr_area, tr) -> str | None:
    """ترجمة منطقة قد تكون مركّبة بفاصل «·»؛ تُرفض إن بقي أي جزء عربيًا."""
    # ك-597: الفاصل قد يكون «·» وقد يكون شرطة محاطة بفراغين («إيران - مضيق هرمز»).
    parts = [p.strip() for p in re.split(r"\s*·\s*|\s+-\s+|\s+–\s+", raw) if p.strip()]
    if not parts:
        return None
    out = []
    for part in parts:
        value = _clean_en(_gl_term(part) or tr_area(part) or tr(part))
        if not value:
            return None
        out.append(value)
    return " · ".join(out)


def _card_fragments_en(n: str, tr, tr_area) -> str | None:
    """وحدات بطاقة القرار وسجل الأحداث في الصفحة العربية.

    تُبنى من المفردات الحاكمة (المعجم والأماكن) فلا تحتاج تثبيتًا يدويًا لكل يوم،
    وتُرفض أي وحدة لا يكتمل معناها الإنجليزي بدل إظهار نص عربي في الصفحة الإنجليزية.
    """
    # ك-597: جملة عوامل التغيير ترد مقتطعة وبأطراف مختلفة؛ يُترجم طرفها من المعجم
    # الحاكم بدل تثبيت نص لكل صيغة، وتفشل مغلقًا إن لم تكن المفردة معروفة.
    m = re.fullmatch(r"عوامل التغيير:\s*(?P<dir>يرفعه|يخفضه)\s+(?P<rest>.+?)\.?", n)
    if m:
        rest = _clean_en(_gl_term(m.group("rest").strip()) or tr(m.group("rest").strip()))
        if rest:
            verb = "it is raised by" if m.group("dir") == "يرفعه" else "it is lowered by"
            return f"Change factors: {verb} {rest}"
        return None
    # ك-597: الصيغة ترد بفواصل ومحارف اتجاه مخفية تختلف بين الصفحات؛ يُلتقط
    # التاريخ نفسه من النص ويُحفظ كما هو بدل تثبيت شكل واحد.
    m = re.fullmatch(r"مستمر\s*؛?\s*آخرها\s*(?P<rest>.+)", n)
    if m:
        dm = re.search(r"\d{4}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{1,2}", m.group("rest"))
        if dm:
            return f"continuing; the latest on {dm.group(0).replace(' ', '')}."
        return None
    m = re.fullmatch(
        r"الوقائع\s+(?P<ids>(?:\d{2}-\d{2})(?:\s*·\s*\d{2}-\d{2})*)\s+—\s+المنطقة\s+(?P<area>.+?)،\s+"
        r"الصفة\s+(?P<kind>[^،]+)،\s+الإثبات\s+(?P<conf>[^،]+)،\s+الموقع\s+(?P<loc>.+?)\.", n)
    if m:
        ids = ", ".join(x.strip() for x in m.group("ids").split("·") if x.strip())
        area = _clean_en(_area_composite(m.group("area"), tr_area, tr))
        kind = _clean_en(_gl_term(m.group("kind")) or tr(m.group("kind")))
        conf = _clean_en(_gl_term(m.group("conf")) or tr(m.group("conf")))
        loc = _clean_en(_gl_term(m.group("loc")) or tr(m.group("loc")))
        if area and kind and conf and loc:
            return (f"Incidents {ids} — area {area}, type {kind}, confirmation {conf}, "
                    f"location {loc}.")
        return None
    # ك-597: عائلتا الإضافات المؤرّختان تتغيّران كل إصدار، فيُشتق اسم الشهر
    # بدل تثبيت نص لكل تاريخ (وإلا تكرّر المنع في الإصدار التالي).
    m = re.fullmatch(r"(?P<dot>·)?\s*إضافات إصدار\s+(?P<d>\d{1,2}\s+\S+\s+\d{4})", n)
    if m:
        _p = m.group("d").split()
        _mon = MONTHS.get(_p[1]) or MONTHS_NUM.get(_p[1])
        if _mon and not str(_mon).isdigit():
            _pref = "· Appendix of the" if m.group("dot") else "Appendix of the"
            return f"{_pref} {_p[0]} {_mon} {_p[2]} edition"
        return None
    m = re.fullmatch(r"إضافات\s*—\s*(?P<d>\d{2}/\d{2}/\d{4})", n)
    if m:
        return f"Appendices — {m.group('d')}"
    m = re.fullmatch(r"عدد البنود: (?P<n>\d+) · وتفصيلها في قسم «(?P<sec>[^»]+)»\.", n)
    if m:
        sec = _clean_en(_gl_term(m.group("sec")) or tr(m.group("sec")))
        if sec:
            return f"Number of items: {m.group('n')} · detailed in the “{sec}” section."
        return None
    m = re.fullmatch(r"عناوين مهنية عن تعطيل أو إصابة سفينة بضائع وحريق ناقلة وإجلاء (?P<n>\d+) شخصًا", n)
    if m:
        return ("professional headlines about the disabling or damaging of a cargo ship, a tanker fire, "
                f"and the evacuation of {m.group('n')} people")
    m = re.fullmatch(
        r"(?P<lead>عنوانًا عن|عن) نشاط مشبوه على بعد (?P<n>\d+) " + _DISTANCE_AR +
        r" (?P<dir>" + _DIRECTION_ALT + r") (?P<place>.+?)"
        r"(?P<tail>؛ التفاصيل التشغيلية غير ظاهرة\.)?", n)
    if m:
        place = _clean_en(_gl_term(m.group("place").strip())
                           or tr_area(m.group("place").strip()) or tr(m.group("place").strip()))
        if not place:
            return None
        head = "a headline about" if m.group("lead").startswith("عنوانًا") else "about"
        activity = (_gl_term("نشاط مشبوه") or "suspicious activity").lower()
        out = (f"{head} {activity} {m.group('n')} nautical miles "
               f"{_DIRECTION_EN[m.group('dir')]} of {place}")
        if m.group("tail"):
            out += "; operational details are not visible."
        return out
    m = re.fullmatch(
        r"عن واقعة (?:هجوم )?متأخر(?:ة الإبلاغ|ة التوقيت)(?: وُصفت بأنها هجوم)? على بعد "
        r"(?P<n>\d+) " + _DISTANCE_AR + r" (?P<dir>" + _DIRECTION_ALT + r") (?P<place>.+)", n)
    if m:
        place = _clean_en(_gl_term(m.group("place").strip())
                           or tr_area(m.group("place").strip()) or tr(m.group("place").strip()))
        if not place:
            return None
        return (f"about a late-reported attack incident {m.group('n')} nautical miles "
                f"{_DIRECTION_EN[m.group('dir')]} of {place}")
    return None


def localize_patterns(s: str) -> str | None:
    n = norm(s)
    # ك-595: عبارات تاريخية عامة في ترويسات تقارير تاريخية — تُبنى بنمط لا بمعجم.
    # «آخر تحديث سبتمبر 2026» و«الفترة: سبتمبر 2026 · المتوسط:» كانت تُسقط البناء
    # في الصفحات القديمة؛ والقاعدة تقبل تاريخًا معروف الشهر فقط ولا تخمّن نصًا حرًا.
    m = re.fullmatch(r"آخر تحديث\s+(?P<d>.+)", n)
    if m:
        d = _en_date_phrase(m.group("d")) or _en_month_year(m.group("d"))
        if d:
            return f"Last updated {d}"
    m = re.fullmatch(r"الفترة:\s*(?P<d>[^·]+?)\s*·\s*المتوسط:\s*(?P<v>.*)", n)
    if m:
        d = _en_date_phrase(m.group("d")) or _en_month_year(m.group("d"))
        if d:
            tail = m.group("v").strip()
            return f"Period: {d} · Average:" + (f" {tail}" if tail else "")
    # عنوان الإصدار اليومي بالتاريخ: يُبنى بنمط ثابت بدل طلب ترجمة سطر كامل (ك-595)
    m = re.fullmatch(r"(?:التقرير اليومي(?: للأمن البحري| لأمن الملاحة)?"
                     r"(?: والأوضاع الراهنة في المنطقة)?|التقرير الصباحي اليومي)"
                     r"\s*[—–-]\s*(\d{1,2})\s+([\u0600-\u06FF]+)\s+(\d{4})", n)
    if m:
        num = MONTHS_NUM.get(m.group(2))
        if num:
            return (f"Daily Maritime Security Report — "
                    f"{m.group(3)}-{num:02d}-{int(m.group(1)):02d} (English edition)")
    m = re.fullmatch(r"(?:التقرير اليومي(?: للأمن البحري| لأمن الملاحة)?"
                     r"(?: والأوضاع الراهنة في المنطقة)?|التقرير الصباحي اليومي)"
                     r"\s*[—–-]\s*(\d{4})-(\d{2})-(\d{2})", n)
    if m:
        return f"Daily Maritime Security Report — {m.group(1)}-{m.group(2)}-{m.group(3)} (English edition)"
    # ك-597: الترويسة اليومية تُكتب أيضًا بصيغة يوم/شهر/سنة (09/11/2026)؛ القاعدة
    # تُبنى على التاريخ نفسه لا على نص ثابت لتاريخ واحد.
    m = re.fullmatch(r"(?:التقرير اليومي(?: للأمن البحري| لأمن الملاحة)?"
                     r"(?: والأوضاع الراهنة في المنطقة)?|التقرير الصباحي اليومي)"
                     r"\s*[\u2014\u2013-]\s*(\d{1,2})/(\d{1,2})/(\d{4})", n)
    if m:
        return (f"Daily Maritime Security Report — {m.group(3)}-{int(m.group(2)):02d}-"
                f"{int(m.group(1)):02d} (English edition)")
    m = re.fullmatch(r"\(?official_ref=(\S+)\s+\(سجل الدفتر المجمّد\s+([^)]+)\)\)?", n)
    if m:
        return f"(official_ref={m.group(1)} (frozen ledger record {m.group(2)}))"
    m = re.fullmatch(r"\(?تصحيح معرّف معلّق\s+\(([^)]+)\)\s*←\s*([^:]+):\s*الواقعة نفسها بالسفينة\s*\)?", n)
    if m:
        return f"(Corrected dangling identifier ({m.group(1)}) ← {m.group(2)}: same vessel incident)"
    m = re.fullmatch(r"\((\d+)\s*واقعة\)([؛\.]?)", n)
    if m:
        tail = ";" if m.group(2) == "؛" else m.group(2)
        return f"({m.group(1)} events){tail}"
    # تفاصيل بطاقة الوقائع المؤهلة
    m = re.fullmatch(r"(\d+)\s*مؤكدة\s*\+\s*(\d+)\s*مرجّحة\s*\+\s*(\d+)\s*غير مؤكدة مؤهلة", n)
    if m:
        return (f"{m.group(1)} confirmed + {m.group(2)} probable + "
                f"{m.group(3)} qualifying unconfirmed")
    # تفاصيل بطاقة الروايات غير المؤكدة
    m = re.fullmatch(r"(\d+)\s*(?:روايات|رواية)\s*·\s*منها\s*(\d+)\s*مؤهلة\s*·\s*تُذكر ولا تُحتسب", n)
    if m:
        return (f"{m.group(1)} narratives · {m.group(2)} of them qualifying · "
                "reported but not counted")

    _G = None
    try:
        _G = load_glossary()
    except Exception:
        _G = {}

    _AREA_EN = {
        "غير محددة": "not specified",
        "مقابل السواحل الإماراتية": "off the UAE coast",
        "مضيق هرمز": "Strait of Hormuz", "خليج عُمان": "Gulf of Oman",
        "الخليج العربي": "Arabian Gulf", "باب المندب": "Bab-el-Mandeb",
        "البحر الأحمر": "Red Sea", "خليج عدن": "Gulf of Aden",
        "القرن الأفريقي": "Horn of Africa", "بحر العرب": "Arabian Sea",
        "المحيط الهندي": "Indian Ocean", "البحر الأسود": "Black Sea",
        "غير مكانية": "Non-spatial", "المنطقة كاملة": "Entire area",
        "سياق إقليمي": "Regional context",
    }
    try:  # نسخة مشتقة من السجل الحاكم، داخل مستودع الموقع (مسار نسبي)
        _vp = pathlib.Path(__file__).resolve().parent.parent / "sources/i18n/en/area-vocabulary.json"
        _v = json.loads(_vp.read_text(encoding="utf-8"))
        _AREA_EN.update(_v.get("areas") or {})
        _AREA_EN.update(_v.get("scalars") or {})
    except Exception:
        pass

    _ZONE_EN = {}
    try:  # الاسم المركب للقطاع يُقرأ من السجل الحاكم، لا من قائمة ثابتة
        _rp = BRAIN / "appendices" / "zone-registry.json"
        _r = json.loads(_rp.read_text(encoding="utf-8"))
        _ZONE_EN.update({
            norm(z.get("ar", "")): z.get("en", "")
            for z in (_r.get("zones") or [])
            if norm(z.get("ar", "")) and norm(z.get("en", ""))
        })
    except Exception:
        pass

    def _tr_area(v: str) -> str:
        """يترجم اسم منطقة، أو «موقع - منطقة»، أو سردًا مفصولًا بـ«·»."""
        t = (v or "").strip()
        if norm(t) in _ZONE_EN:
            return _ZONE_EN[norm(t)]
        if t in _AREA_EN:
            return _AREA_EN[t]
        if " · " in t:
            return " · ".join(_tr_area(x) for x in t.split(" · "))
        if " - " in t:
            left, _, right = t.rpartition(" - ")
            if right.strip() in _AREA_EN:
                return f"{_tr(left.strip())} - {_AREA_EN[right.strip()]}"
        return t

    def _area_full(v: str) -> str:
        """ترجمة وسم منطقة كامل، بما فيه «مكان، عمان - منطقة» (ك-497)."""
        t = (v or "").strip()
        m = re.fullmatch(r"(?P<place>[^،]+)،\s*عمان\s*-\s*(?P<area>.+)", t)
        if m:
            place = _PLACE_EN.get(m.group("place").strip())
            area = _clean_en(_area_composite(m.group("area"), _tr_area, _tr)) or ""
            if place and not ARABIC.search(area):
                return f"{place}, Oman - {area}"
        return _tr_area(t)

    def _tr(v: str) -> str:
        hit = (_G or {}).get(norm(v))
        if hit:
            return hit
        area = _tr_area(v)
        return area if area != v else v

    # عدّاد الوقائع غير المؤكدة (سطر مختصر)
    m = re.fullmatch(r"(\d+)\s*وقائع غير مؤكدة\s*·\s*تُذكر ولا تُحتسب", n)
    if m:
        return f"{m.group(1)} unconfirmed incidents · reported but not counted"
    # رقم الإصدار بالتاريخ
    m = re.fullmatch(r"[·•]?\s*إصدار\s+(\d{1,2})\s+([^\s]+)\s+(\d{4})", n)
    if m:
        month = MONTHS.get(m.group(2))
        if not month:
            return None
        return f"· Edition {m.group(1)} {month} {m.group(3)}"
    # وسم «إعلان · unconfirmed» في بطاقات الوقائع
    if n == "إعلان · unconfirmed":
        return "Declaration · unconfirmed"
    # إحالة الرمز بين اليوم والسجل
    m = re.fullmatch(r"بالرمز\s+(\d{2}-\d{2})\s*\((\d{2}-\d{2})\)\.", n)
    if m:
        return f"under reference {m.group(1)} ({m.group(2)})."
    # عدد البنود الأخرى في قسم «ما تغيّر»
    m = re.fullmatch(r"و(\d+)\s+بنود أخرى في قسم «ما تغيّر»\.", n)
    if m:
        return f"and {m.group(1)} further items in the «What changed» section."

    # حافظ على مرساة رابط التوصيات عند ترجمة الملاحظة ذات البنية المعروفة.
    m = re.fullmatch(
        r'و(\d+)\s+بنود أخرى في\s*<a class="dc-jump" href="#sec-decision">قسم «التوصيات»</a>\.',
        n,
    )
    if m:
        return (f'and {m.group(1)} further items in '
                f'<a class="dc-jump" href="#sec-decision">the Recommendations section</a>.')
    m = re.fullmatch(r"و(\d+)\s+بنود أخرى في قسم «التوصيات»\.", n)
    if m:
        return f"and {m.group(1)} further items in the Recommendations section."

    # ترويسة بطاقة القطاعات: المستوى والاسم المركب يأتيان من السجل الحاكم.
    m = re.fullmatch(
        r"المستوى العام\s+(?P<level>حرج|مرتفع جدًا|مرتفع|متوسط|منخفض)\.\s+"
        r"ويظل\s+(?P<zone>.+?)\s+أعلى القطاعات عند مستوى\s+(?P=level)\.",
        n,
    )
    if m:
        level = _OVERALL_LEVEL_EN.get(m.group("level"))
        zone = _tr_area(m.group("zone"))
        if level and zone != m.group("zone") and not ARABIC.search(zone):
            return f"Overall level: {level}. The {zone} remains the highest sector at {level} level."

    # عائلة المستوى العام: بنية كاملة ومقفلة على مستوى/قطاعات/عدد/مرجع معروف؛
    # اختلافات الصياغة المقبولة محصورة في «يستند/يُسند»، «وهو/هذا»، و«لا ترفع/لا تُرفع».
    m = re.fullmatch(
        r"المستوى العام:\s*(?P<level>مرتفع جدًا|مرتفع|متوسط|منخفض)\s+—\s+"
        r"(?P<label>القطاع الأعلى|القطاعات الأعلى):\s*(?P<sectors>.+?)\.\s+"
        r"(?P<basis>يستند|يُسند)\s+هذا التقدير إلى صدور\s+"
        r"(?P<count>واحد|واحدة|اثنان|اثنتان|ثلاثة|ثلاث|أربعة|أربع|خمسة|خمس|ستة|ست|"
        r"سبعة|سبع|ثمانية|ثمان|تسعة|تسع|عشرة|عشر|\d+)\s+تحذيرات رسمية خلال الفترة،\s+"
        r"(?P<between>منها|بينها)\s+بلاغ(?: عن)? هجوم داخل مضيق هرمز وتحديث لتحذير سابق[؛،]\s+"
        r"(?P<high>وهو|هذا)\s+أعلى تكرار رسمي خلال الفترة القريبة\.\s+"
        r"(?P<negative>لا تُرفع|لا ترفع)\s+"
        r"(?:(?:درجة التهديد\s+استناد(?:ًا|ا) إلى روايات غير مؤكدة)|"
        r"(?:الروايات غير المؤكدة\s+مستوى التهديد))\s+"
        r"قبل تأكيد رسمي أو تأكيد من مصدرين مستقلين\s+"
        r"\((?P<refs>\d{2}-\d{2}\s+إلى\s+\d{2}-\d{2}؛\s+B/2)\)\.",
        n,
    )
    if m:
        level = _OVERALL_LEVEL_EN[m.group("level")]
        sectors = _overall_sectors(m.group("sectors"))
        count = _warning_count(m.group("count"))
        if sectors is None or count is None:
            return None
        label = "highest sector" if m.group("label") == "القطاع الأعلى" else "highest sectors"
        refs = m.group("refs").replace(" إلى ", " to ").replace("؛", ";")
        return (
            f"Overall level: {level} — {label}: {sectors}. This assessment is based on the issuance of "
            f"{count} official warnings during the period, including a report of an attack inside the Strait of "
            f"Hormuz and an update to an earlier warning; this is the highest official frequency in the recent period. "
            f"The threat level is not raised on the basis of unconfirmed accounts before official confirmation or "
            f"confirmation from two independent sources ({refs})."
        )

    # عائلات متكررة في سطح الإضافات: لا تُقبل إلا مع بنية كاملة ومعرّف تحذير
    # صريح، وتاريخ يوم/شهر اختياري معروف؛ أي نص خارج هذا القيد يبقى مانعًا.
    m = re.fullmatch(r"،\s*من دون تفاصيل عن السفينة أو عن الضرر", n)
    if m:
        return ", without details about the vessel or the damage"
    # ك-480: «و» الابتدائية اختيارية — سطح الإضافات قد يكتب «، التحذير 191-26 بتاريخ».
    m = re.fullmatch(r"،\s*(?P<w>و)?التحذير\s+(?P<id>\d{3}-\d{2})\s+بتاريخ(?:\s+(?P<date>.+))?", n)
    if m:
        date = _en_date_phrase(m.group("date")) if m.group("date") else ""
        if m.group("date") and date is None:
            return None
        lead = ", and" if m.group("w") else ","
        return f"{lead} warning No. {m.group('id')} dated" + (f" {date}" if date else "")
    # عائلة ناقلتي النفط (سطح الإضافات): ترتيب الجهتين متغيّر، والمقذوف/اللغام متغيّر،
    # والمرجع مقفول ببنية معروفة؛ أي نص خارج هذا القيد يبقى مانعًا.
    m = re.fullmatch(
        r"نقلت\s+(?:وسائل متابعة ومصادر إيرانية|مصادر إيرانية ووسائل متابعة)\s+"
        r"أن ناقلتي نفط انفجرتا بعد اصطدامهما المزعوم ب(?:ألغام|مقذوفات)\s+بحرية\s+"
        r"في مضيق هرمز،\s+وأن إحداهما اندلع فيها حريق،\s+"
        r"من دون تأكيد رسمي مستقل\s+\((?P<refs>[^)]+)\)\.",
        n,
    )
    if m:
        refs = re.sub(r"\s+و", " and ", m.group("refs")).replace("؛", ";")
        return (
            "Monitoring outlets and Iranian sources reported that two oil tankers exploded after their "
            "alleged collision with maritime projectiles in the Strait of Hormuz, and that a fire broke out "
            f"on one of them, without independent official confirmation ({refs})."
        )
    m = re.fullmatch(
        r"(واحد|واحدة|اثنان|اثنتان|ثلاثة|ثلاث|أربعة|أربع|خمسة|خمس|ستة|ست|"
        r"سبعة|سبع|ثمانية|ثمان|تسعة|تسع|عشرة|عشر|\d+)\s+تحذيرات خلال الفترة:\s+"
        r"تحديث التحذير\s+(\d{3}-\d{2})،\s+ثم التحذير\s+(\d{3}-\d{2})\s+في(?:\s+(.+))?",
        n,
    )
    if m:
        count = _warning_count(m.group(1))
        date = _en_date_phrase(m.group(4)) if m.group(4) else ""
        if count is None or (m.group(4) and date is None):
            return None
        sentence_count = count[:1].upper() + count[1:]
        return (f"{sentence_count} warnings during the period: an update to warning No. {m.group(2)}, "
                f"followed by warning No. {m.group(3)} on" + (f" {date}" if date else ""))
    m = re.fullmatch(
        r"صدر\s+(واحد|واحدة|اثنان|اثنتان|ثلاثة|ثلاث|أربعة|أربع|خمسة|خمس|ستة|ست|"
        r"سبعة|سبع|ثمانية|ثمان|تسعة|تسع|عشرة|عشر|\d+)\s+تحذيرات خلال الفترة:\s+"
        r"التحذير\s+(\d{3}-\d{2})\s+\(التحديث الأول\)\s+بتاريخ(?:\s+(.+))?",
        n,
    )
    if m:
        count = _warning_count(m.group(1))
        date = _en_date_phrase(m.group(3)) if m.group(3) else ""
        if count is None or (m.group(3) and date is None):
            return None
        sentence_count = count[:1].upper() + count[1:]
        return (f"{sentence_count} warnings were issued during the period: warning No. {m.group(2)} "
                f"(the first update), dated" + (f" {date}" if date else ""))

    m = re.fullmatch(r"القطاع\s+(\S+)\s+(.+?)\s+—\s+مستواه\s+(.+?)\.", n)
    if m:
        return f"Sector {m.group(1)} {_tr(m.group(2))} — level {_tr(m.group(3))}."
    m = re.fullmatch(r"(Z\d)\s*·\s*(.+)", n)
    if m and "القطاع" not in n:
        return f"{m.group(1)} · {_tr_area(m.group(2))}"
    m = re.fullmatch(r"الخط الزمني المرصود:\s*(.+?)\.", n)
    if m:
        inner = _tr(m.group(1))
        inner = re.sub(r"\((\d+)\s*واقعة\)", r"(\1 events)", inner)
        inner = inner.replace("واقعة", "event").replace("؛", ";")
        return f"Observed timeline: {inner}."
    m = re.fullmatch(r"المؤكد:\s*(\d+)\s*·\s*المرجّح:\s*(\d+)\s*·\s*غير المؤكد:\s*(\d+)", n)
    if m:
        return f"Confirmed: {m.group(1)} · probable: {m.group(2)} · unconfirmed: {m.group(3)}"
    m = re.fullmatch(r"فُح(?:ِ)?صت\s+(\d+)\s+تغذية\s+من\s+(\d+)\s+تغذية\.", n)
    if m:
        return f"Checked {m.group(1)} of {m.group(2)} feeds."
    m = re.fullmatch(r"بلغ مجموع العناصر المقروءة\s+(\d+)\s+عنصر(?:ًا|اً)\.", n)
    if m:
        return f"Total items read: {m.group(1)}."
    m = re.fullmatch(r"تعذّرت\s+(\d+)\s+تغذية\s+من\s+أصل\s+(\d+)\.", n)
    if m:
        return f"{m.group(1)} of {m.group(2)} feeds failed."
    m = re.fullmatch(r"سُج(?:ِّ)?لت مرجعية يدوية للمصدرين\s+([\d،\s]+?)\s+—\s+العدد\s+(\d+)\.", n)
    if m:
        return (f"Manual reference recorded for sources {_en_number_list(m.group(1))}"
                f" — count {m.group(2)}.")
    m = re.fullmatch(r"وُس(?:ِّ)?مت مصادر (?:متقادمة|قديمة) وفق حد\s+(\d+)\s+يومًا:\s+([\d،\s]+?)\s+—\s+العدد\s+(\d+)؛\s+"
                     r"(?:و)?لم يُعتمد عليها وحدها لإثبات واقعة جديدة\.", n)
    if m:
        return (f"Sources marked stale at the {m.group(1)}-day threshold: "
                f"{_en_number_list(m.group(2))} — count {m.group(3)}; "
                "not relied on alone to establish a new incident.")
    m = re.fullmatch(r"سُج(?:ِّ)?ل تعذ(?:ّر|ر) مساري المصدرين\s+([\d،\s]+?)\s+في محاولات فرعية،\s+"
                     r"مع بقاء حالة التغذية الكلية ناجحة عبر المسارات المعتمدة البديلة\.", n)
    if m:
        return (f"Sub-attempt failures recorded for sources {_en_number_list(m.group(1))}, "
                "while overall feed status stayed successful through the approved alternative paths.")
    m = re.fullmatch(r"نجحت التغذية على مستوى المصدر ككل\.", n)
    if m:
        return "The feed status succeeded at the source level as a whole."
    m = re.fullmatch(r"لا تغذية فارغة، ولا يُستَتَر أي قيد عن القارئ\.", n)
    if m:
        return "No feed is empty, and no constraint is concealed from the reader."
    m = re.fullmatch(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})\s+·\s+(\d{2}:\d{2})\s+حسب التوقيت العالمي", n)
    if m:
        return f"{m.group(1)} {MONTHS[m.group(2)]} {m.group(3)} · {m.group(4)} UTC"
    m = re.fullmatch(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})", n)
    if m:
        return f"{m.group(1)} {MONTHS[m.group(2)]} {m.group(3)}"
    m = re.fullmatch(r"(" + "|".join(MONTHS) + r")\s+(\d{4})", n)
    if m:
        return f"{MONTHS[m.group(1)]} {m.group(2)}"
    m = re.fullmatch(r"لا\s+(بنود|تحذيرات)\s*(·?)", n)
    if m:
        return f"0 {'items' if m.group(1) == 'بنود' else 'rows'}" + (f" {m.group(2)}" if m.group(2) else "")
    m = re.fullmatch(r"(بند|تحذير)\s+واحد\s*(·?)", n)
    if m:
        return f"1 {'item' if m.group(1) == 'بند' else 'row'}" + (f" {m.group(2)}" if m.group(2) else "")
    m = re.fullmatch(r"(بندان|تحذيران)\s*(·?)", n)
    if m:
        return f"2 {'items' if m.group(1) == 'بندان' else 'rows'}" + (f" {m.group(2)}" if m.group(2) else "")
    # ── نصوص الخريطة المتحركة (المرحلة الاحترافية): تُبنى من الأرقام لا تُثبَّت في المعجم.
    m = re.fullmatch(r"(\d+) كيلومتر · (\d+) ميل بحري", n)
    if m:
        return f"{m.group(1)} km · {m.group(2)} nm"
    m = re.fullmatch(r"مواقع (\d+) واقعة داخل نطاق التقرير؛ (منها \d+ بموقع تقريبي داخل المنطقة "
                     r"نفسها لأن المصدر لم يذكر إحداثيات\.|وجميعها بإحداثيات مذكورة في المصادر\.)", n)
    if m:
        # ك-597: الرقمان (عدد المواقع وعدد المواقع التقريبية) يظهران في الصفحة
        # الإنجليزية؛ سقوط الرقم الثاني كان يمنع الترجمة بحارس حفظ الأرقام (ك-592).
        m2 = re.fullmatch(r"منها (\d+) بموقع تقريبي داخل المنطقة نفسها لأن المصدر لم يذكر إحداثيات\.",
                          m.group(2))
        if m2:
            tail = (f"{m2.group(1)} of them placed approximately within the same area because the source "
                    "gave no coordinates.")
        else:
            tail = "all of them with coordinates stated in the sources."
        return f"Positions of {m.group(1)} incidents within the report scope; {tail}"
    _zl = _zone_level_en(n)
    if _zl is not None:
        return _zl
    # وسم المسار المتأثر على الخريطة يحمل الرقم: القاعدة تحفظ الرقم وتترجم الوحدة،
    # كي لا تفقد الصفحة الإنجليزية قيمةً مرئية موجودة في العربية (ك-570).
    m = re.fullmatch(r"المسار المتأثر ≈ (\d+) كم", n)
    if m:
        return f"Affected route ≈ {m.group(1)} km"
    m = re.fullmatch(r"وأثر وقائع اليوم على المسار ≈ (\d+) كم\.", n)
    if m:
        return f"Today's incidents affect the route by ≈ {m.group(1)} km."
    m = re.fullmatch(r"خريطة وقائع التقرير: (\d+) واقعة مرسومة على الخليج العربي ومضيق هرمز وخليج عمان "
                     r"\(إحداثيات مذكورة (\d+) · مواقع تقريبية (\d+)\)\. الحالات: (.+?)\."
                     r" الموقع التقريبي يعني أن المصدر لم يذكر إحداثيات فوُضعت العلامة داخل المنطقة نفسها لا في موقع محدد\.", n)
    if m:
        st = m.group(4)
        for ar, en in (("غير مؤهل — لا يُحتسب", "not qualifying"),
                       ("غير مؤكد مؤهل", "unconfirmed qualifying"),
                       ("حالة غير محددة", "status not stated"),
                       ("مؤكد", "confirmed"), ("مرجّح", "probable")):
            st = st.replace(ar, en)
        return (f"Incident map: {m.group(1)} incidents drawn over the Arabian Gulf, the Strait of Hormuz "
                f"and the Gulf of Oman (stated coordinates {m.group(2)} · approximate locations {m.group(3)}). "
                f"Statuses: {st}. An approximate location means the source gave no coordinates, so the marker "
                "was placed within the same area rather than at a specific point.")
    m = re.fullmatch(r"العلامات المعروضة علامات وقائع اليوم على الخريطة؛ والموقع التقريبي يعني أن المصدر لم يذكر "
                     r"إحداثيات فوُضعت العلامة داخل المنطقة نفسها لا في موقع آخر. وتوزيع الحالة: مؤكد (\d+) · "
                     r"مرجّح (\d+) · غير مؤكد مؤهل (\d+) · غير مؤهل (\d+) · حالة غير محددة (\d+)\."
                     r"( ووقائع خارج نطاق الخريطة تُذكر في جدول التوزيع الجغرافي: .+)?", n)
    if m:
        base = (f"Markers show today's incident locations; an approximate location means the source gave no "
                f"coordinates, so it was placed within the same area rather than elsewhere. Status mix: "
                f"confirmed {m.group(1)} · probable {m.group(2)} · unconfirmed qualifying {m.group(3)} · "
                f"not qualifying {m.group(4)} · status not stated {m.group(5)}.")
        if m.group(6):
            base += (" Incidents outside the map extent are listed in the geographic distribution table.")
        return base

    # ك-497: عائلة وصف الواقعة على الخريطة (البديل النصي) — بنية مقفلة بمعرّف واقعة
    _KIND = {"بلاغ رسمي": "official report", "نقل إعلامي": "media relay",
             "تقدير تحليلي": "analytical estimate", "رواية غير مؤكدة": "unconfirmed account",
             "بلاغ غير مؤكد": "unconfirmed report"}
    _CONF = {"مؤكد": "confirmed", "غير مؤكد": "unconfirmed", "مرجح": "probable"}
    _LOC = {"تقريبي": "approximate", "دقيق": "exact"}
    m = re.fullmatch(
        r"الواقعة\s+(?P<code>\d{2}-\d{2})\s+—\s+المنطقة\s+(?P<area>.+?)،\s+"
        r"الصفة\s+(?P<kind>[^،]+)،\s+الإثبات\s+(?P<conf>[^،]+)،\s+الموقع\s+(?P<loc>.+)\.",
        n)
    if m:
        area = _clean_en(_area_composite(m.group("area"), _tr_area, _tr)) or ""
        kind = _KIND.get(m.group("kind").strip()) or _gl_term(m.group("kind"))
        conf = _CONF.get(m.group("conf").strip()) or _gl_term(m.group("conf"))
        loc = _LOC.get(m.group("loc").strip()) or _gl_term(m.group("loc"))
        if kind and conf and loc and not re.search(ARABIC, area):
            return (f"Incident {m.group('code')} — area {area}, type {kind}, "
                    f"confirmation {conf}, location {loc}.")

    # ك-497: بلاغ التحذير في جدول المصادر — نص مقتطع بعلامة قطع
    m = re.fullmatch(
        r"(?:·\s*)+التحذير\s+(?P<id>\d{3}-\d{2}):\s*هجوم على ناقلة على بعد\s+"
        r"(?P<d>\d+)\s+ميلا? بحريا? شرق\s+(?P<place>.+)…", n)
    if m:
        return (f"· Warning {m.group('id')}: an attack on a tanker {m.group('d')} "
                f"nautical miles east of {m.group('place')}…")

    # ك-497: عائلات بطاقة سجل الحوادث المؤكدة من IMO
    m = re.fullmatch(r"—\s*(?P<n>\d+)\s+حادثة مؤكدة على سفن تجارية", n)
    if m:
        return f"— {m.group('n')} confirmed incidents on commercial vessels"
    m = re.fullmatch(r"(?P<place>[^،]+)،\s*عمان\s*-\s*(?P<area>.+)", n)
    if m:
        area = _clean_en(_area_composite(m.group("area"), _tr_area, _tr)) or ""
        if not re.search(ARABIC, area):
            return f"{m.group('place')}, Oman - {area}"
    m = re.fullmatch(r"بصيغة مختصرة لا يذكر اسم السفينة ولا الضرر", n)
    if m:
        return "in a brief form that names neither the vessel nor the damage"
    m = COUNTER.match(n)
    if m:
        return f"{m.group(1)} {COUNT_WORD[m.group(2)]}" + (f" {m.group(3)}" if m.group(3) else "")
    # ك-597: وحدات البطاقات وسجل الأحداث — تُبنى من المفردات الحاكمة لا من نص ثابت،
    # فتبقى صالحة لكل تاريخ ولكل واقعة جديدة (مواقع وأعداد متغيّرة).
    frag = _card_fragments_en(n, _tr, _tr_area)
    if frag is not None:
        return frag
    return None


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.skip = 0
        self.units: list[str] = []
        self.unit_contexts: list[str | None] = []
        self.unit_ltr_tokens: list[list[str]] = []
        self.unit_inside_ltr: list[bool] = []
        self._open_tags: list[tuple[str, tuple[int | None, list[str]] | None]] = []
        self._pending_ltr_tokens: list[str] = []
        self.parts: list[str] = []
        self.attrs_seen: list[str] = []
        self.in_tz_count = False

    def _last_nonempty_unit_index(self) -> int | None:
        for index in range(len(self.units) - 1, -1, -1):
            if self.units[index].strip() and not self.unit_inside_ltr[index]:
                return index
        return None

    def _finish_ltr_frame(self, frame: tuple[int | None, list[str]]) -> None:
        before_index, chunks = frame
        token = norm("".join(chunks))
        if not token:
            return
        if before_index is not None and token not in self.unit_ltr_tokens[before_index]:
            self.unit_ltr_tokens[before_index].append(token)
        if token not in self._pending_ltr_tokens:
            self._pending_ltr_tokens.append(token)

    def _attr(self, attrs) -> str:
        if not attrs:
            return ""
        out = []
        for k, v in attrs:
            if v is None:
                out.append(f" {k}")
            elif k in TR_ATTRS and ARABIC.search(v):
                self.attrs_seen.append(v)
                out.append(f' {k}="__ATTR{len(self.attrs_seen) - 1}__"')
            else:
                out.append(f' {k}="{v}"')
        return "".join(out)

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
        if tag == "p" and "tz-count" in dict(attrs).get("class", "").split():
            self.in_tz_count = True
        frame = None
        if tag == "span" and "ltr" in dict(attrs).get("class", "").split():
            frame = (self._last_nonempty_unit_index(), [])
        self._open_tags.append((tag, frame))
        self.parts.append(f"<{tag}{self._attr(attrs)}>")

    def handle_startendtag(self, tag, attrs):
        self.parts.append(f"<{tag}{self._attr(attrs)}/>")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1
        if tag == "p" and self.in_tz_count:
            self.in_tz_count = False
        matching = next((i for i in range(len(self._open_tags) - 1, -1, -1)
                         if self._open_tags[i][0] == tag), None)
        if matching is not None:
            for _, frame in reversed(self._open_tags[matching:]):
                if frame is not None:
                    self._finish_ltr_frame(frame)
            del self._open_tags[matching:]
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self.skip:
            self.parts.append(data)
            return
        active_ltr = [frame for _, frame in self._open_tags if frame is not None]
        for frame in active_ltr:
            frame[1].append(data)
        self.parts.append("\u0000")
        self.units.append(data)
        self.unit_contexts.append("tz-count" if self.in_tz_count else None)
        self.unit_inside_ltr.append(bool(active_ltr))
        adjacent_tokens = []
        if not active_ltr and data.strip() and self._pending_ltr_tokens:
            adjacent_tokens = self._pending_ltr_tokens
            self._pending_ltr_tokens = []
        self.unit_ltr_tokens.append(adjacent_tokens)

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")


def _counter_registry_path() -> pathlib.Path:
    candidates = []
    if os.environ.get("BRAIN_DIR"):
        candidates.append(pathlib.Path(os.environ["BRAIN_DIR"]) / "appendices" / "card_registry.json")
    candidates.append(BRAIN / "appendices" / "card_registry.json")
    candidates.append(ROOT.parent / "brain" / "appendices" / "card_registry.json")
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError("سجل البطاقات مفقود: لا يمكن توليد عدادات بطاقة القطاعات")


def _sector_counter_labels() -> dict[str, str]:
    registry = json.loads(_counter_registry_path().read_text(encoding="utf-8"))
    card = next((c for c in registry.get("cards", [])
                 if c.get("id") == "sector-threat-level"
                 and (c.get("status") or {}).get("state") == "enabled"), None)
    counters = (card or {}).get("counters") or []
    labels = {c.get("display_label", ""): c.get("display_label_en", "") for c in counters}
    if not labels or any(not arabic or not english for arabic, english in labels.items()):
        raise RuntimeError("عقد تسميات بطاقة القطاعات غير صالح: يلزم كل مفتاح عربي وإنجليزي")
    return labels


def _translate_counter_fragment(text: str, labels: dict[str, str]) -> str:
    translated = text.replace("العدّاد:", "Counter:")
    for arabic, english in sorted(labels.items(), key=lambda item: len(item[0]), reverse=True):
        translated = translated.replace(arabic, english)
    return translated


_ZONES_RAW = {
    'مضيق هرمز وخليج عُمان والخليج العربي': 'the Strait of Hormuz, the Gulf of Oman and the Arabian Gulf',
    'باب المندب والبحر الأحمر': 'Bab al-Mandab and the Red Sea',
    'بحر العرب': 'the Arabian Sea',
    'القرن الأفريقي': 'the Horn of Africa',
    'المحيط الهندي': 'the Indian Ocean',
    'الخليج العربي': 'the Arabian Gulf',
    'خليج عُمان': 'the Gulf of Oman',
    'خليج عدن': 'the Gulf of Aden',
}
_LEVELS_RAW = {'حرج': 'Critical', 'مرتفع جدًا': 'Very high', 'مرتفع': 'High',
               'متوسط': 'Moderate', 'منخفض': 'Low'}
_TAILS_RAW = {
    '': '',
    ' لم تُسجَّل واقعة بحرية جديدة في المصادر المستخدمة.': ' No new maritime incident was recorded in the sources used.',
    ' لا تتضمن المصادر المستخدمة بندًا بحريًا جديدًا.': ' The sources used contain no new maritime item.',
    ' لم تُظهر المصادر المستخدمة بندًا بحريًا جديدًا.': ' The sources used show no new maritime item.',
    ' لا واقعة مؤهّلة داخل الفترة.': ' No qualifying incident within the period.',
}
ZONES_EN = {norm(k): v for k, v in _ZONES_RAW.items()}
LEVELS_EN = {norm(k): v for k, v in _LEVELS_RAW.items()}
TAILS_EN = {norm(k): v for k, v in _TAILS_RAW.items()}
_ZONE_LEVEL_RE = re.compile(
    r"المستوى في (" + "|".join(map(re.escape, ZONES_EN)) + r"): ("
    + "|".join(map(re.escape, LEVELS_EN)) + r")(?:\s*\(Z[1-5]\))?\.(.*)")


def _zone_level_en(n: str):
    """نمط أسطر مستوى القطاع: «المستوى في <منطقة>: <مستوى>. <ذيل>» (ك-497).

    يُترجم بالمعنى لا كلمة بكلمة؛ وذيل غير معروف يعيد None فيبقى الوحدة غير مترجمة
    فيرفض البناء فشلًا مغلقًا بدل إخراج عربية داخل الصفحة الإنجليزية.
    """
    m = _ZONE_LEVEL_RE.fullmatch(n)
    if not m:
        return None
    tail_en = TAILS_EN.get(norm(m.group(3)))
    if tail_en is None:
        return None
    return f"Level in {ZONES_EN[m.group(1)]}: {LEVELS_EN[m.group(2)]}.{tail_en}"


def make_translator(tm: dict[str, str], gl: dict[str, str]):
    exact_only = {norm(k) for k in getattr(gl, "exact_match_only_entries", ())}
    keys = sorted((set(tm) | set(gl)) - exact_only, key=len, reverse=True)

    def _val(k: str) -> str:
        """قيمة الترجمة لمفتاح، والمعجم المعتمد يسبق ذاكرة الترجمة الناقصة.

        العلّة (ك-447): ذاكرة الترجمة تُبنى بمحاذاة أسطر المتن، فإذا انحرفت أسطر
        الجدول أنتجت قيمةً إنجليزية تحمل كلمة عربية متبقية (مثل «في»)، وكانت
        تُقدَّم على المعجم المعتمد فيبقى نص عربي مرئي في النسخة الإنجليزية.
        القاعدة الآن: أي قيمة في ذاكرة الترجمة تحتوي حرفًا عربيًا لا تُقدَّم على
        قيمة المعجم؛ فإن لم يوجد مدخل معجم تُستعمل كما هي للعلم والإصلاح.
        """
        tv = tm.get(k)
        gv = gl.get(k)
        if gv and k in exact_only:
            return gv
        # ك-597: ذاكرة المحاذاة قد تُسند للمفتاح قيمةً لسطر آخر فقدت أرقامه
        # («No qualifying incident» بدل عبارة تحمل تاريخًا)، فيرفضها حارس الأرقام
        # ويُعلن نقص كاذب. القاعدة: إذا خالفت أرقامُ القيمة أرقامَ المفتاح وكان
        # في المعجم الحاكم قيمة مطابقة فالمعجم يُقدَّم؛ فلا تُستعمل قيمة ناقصة.
        _kd, _td = sorted(re.findall(r"\d+", k)), sorted(re.findall(r"\d+", tv or ""))
        if gv and (not tv or ARABIC.search(tv) or _kd != _td):
            return gv
        if tv and not ARABIC.search(tv):
            return tv
        return gv or tv or ""

    def lookup(t: str, ltr_tokens: list[str] | tuple[str, ...] = ()) -> str | None:
        # ك-597: العقدة النصية قد تحمل فراغًا أو محرف اتجاه مخفيًا حول النص، فيفشل
        # البحث المطابق بينما المفتاح المطبَّع موجود. يُجرّب المفتاح المطبَّع قبل
        # الأنماط، فلا يُعلن نقص كاذب في وحدة لها ترجمة حاكمة.
        # ك-597: المطابقة التامة (الخام ثم المطبَّع) تسبق أي مطابقة جزئية، فلا
        # تُقطع وحدة لها مدخل حاكم إلى عبارة أخرى.
        tk = norm(t)
        for cand in (t, tk):
            if cand and (cand in tm or cand in gl):
                return _val(cand)
        pat = localize_patterns(tk or t)
        if pat:
            return pat
        # ك-595: وحدة مركّبة بشرطة («نسب التهديد — خلال 24 ساعة السابقة») لا تطابق
        # مفتاحًا واحدًا، وكانت المطابقة الجزئية تقتطعها إلى «نسب التهديد» فتُسقط
        # الشقّ الثاني صامتةً ثم يفشل البناء بفقد الرقم. القاعدة: تُترجم كل قطعة
        # ترجمة تامة (معجم · ذاكرة · نمط) ثم تُولَّف بالشرطة نفسها. أي قطعة بلا
        # ترجمة تامة تُعيد الوحدة إلى المسار السابق، فلا يُختلق معنى ولا يُقتطع.
        parts = re.split(r"\s*[—–]\s*", t)
        if len(parts) > 1 and all(p.strip() for p in parts):
            outs: list[str] = []
            for part in parts:
                pk = norm(part)
                if pk in tm or pk in gl:
                    outs.append(_val(pk))
                else:
                    outs.append(localize_patterns(pk) or "")
            if all(o and not ARABIC.search(o) for o in outs):
                return " — ".join(o.strip() for o in outs)
        # معرفات التحذير حساسة للهوية: لا تُقبل المطابقة الجزئية إلا إذا كانت
        # كل معرفات المفتاح موجودة حرفيًا في العقدة نفسها؛ فلا يتسرّب 186-26
        # إلى عقدة ev-01 التي لا تحمل إلا موقعها.
        starts = [k for k in keys if k.startswith(t) and _partial_key_safe(t, k)
                  and not _crosses_ltr_boundary(t, k, ltr_tokens)
                  and not norm(t).endswith(("·", "…"))]
        if starts:
            k = min(starts, key=len)
            return _val(k)
        within = [k for k in keys if t.startswith(k) and _partial_key_safe(t, k)
                  and not _crosses_ltr_boundary(t, k, ltr_tokens)
                  and not ADVISORY_ID.search(t)]
        if within:
            k = max(within, key=len)
            return _val(k)
        return None

    def translate(
        u: str,
        prefix: str | None = None,
        ltr_tokens: list[str] | tuple[str, ...] = (),
    ) -> str:
        n = norm(u)
        if not n or not ARABIC.search(n):
            return u
        # ك-592: عقدة نصية تبدأ بعد وسم لاتيني داخل العنصر نفسه
        # (<span class="ltr">IMO</span> — سجل الحوادث المؤكدة؛ أحدث تاريخ ... 29 سبتمبر.)
        # كانت تُطابق مفتاحًا أقصر فيُقتطع المعنى بصمت. القاعدة: تُضمّ البادئة
        # اللاتينية إلى المفتاح، ويُقبل الرد فقط إذا كان مطابقة كاملة في المعجم
        # أو ذاكرة الترجمة، ويُعاد ما بعد البادئة كي لا تتكرر مرتين في الصفحة.
        if prefix:
            joined = prefix + u
            jn = norm(joined)
            if jn in tm or jn in gl:
                hit = _val(jn)
                hp = norm(prefix)
                if hit and norm(hit).startswith(hp):
                    rest = hit[len(prefix):]
                    lead = u[: len(u) - len(u.lstrip())]
                    if rest and not rest[:1].isspace():
                        rest = " " + rest.lstrip()
                    return lead + rest
        # ك-602: وحدة تحمل اسمًا لاتينيًا داخلها (وسم سطري) ولها مقابل معجمي أو
        # من ذاكرة الترجمة مطابق تمامًا ويحمل الاسم نفسه. كان منطق الوسوم يمنع
        # قبولها فيبقى نص عربي ويُرفض البناء مغلقًا على نص له مقابل معلَن.
        # يُقبل هنا المطابق تمامًا فقط، وبشرط ورود الاسم اللاتيني داخل المقابل،
        # فإن غاب أو لم يحمل الاسم فلا شيء يتغير (الفشل المغلق قائم).
        if ltr_tokens:
            _hit = tm.get(n) or gl.get(n)
            _tokens = [norm(t).casefold() for t in ltr_tokens if t and t.strip()]
            if (_hit and _tokens and not ARABIC.search(_hit)
                    and all(t in norm(_hit).casefold() for t in _tokens)):
                _lead = u[: len(u) - len(u.lstrip())]
                _trail = u[len(u.rstrip()):]
                return _lead + _hit + _trail
        # قوائم الأسماء اللاتينية المتصلة بحرف العطف العربي «و» (مثل: Mehr وISNA)
        # ليست نصًّا عربيًا يحتاج معجمًا، بل يجب أن تُوصل بـ«and»؛ فيبقى الاسم
        # اللاتيني كما هو ولا يبقى حرف عربي مرئي في الصفحة الإنجليزية (ك-447).
        if set(ARABIC.findall(n)) == {"و"}:
            fixed = re.sub(r"(?<=[A-Za-z0-9]) و(?=[A-Za-z0-9])", " and ", u)
            fixed = re.sub(r"^\s*و(?=[A-Za-z0-9])", "and ", fixed)
            dual = re.sub(r"(?<=[A-Za-z0-9]) و(?=[A-Za-z0-9])", " and ", fixed)
            if not ARABIC.search(dual):
                return dual
        # تسميات المؤشر القصيرة لا تُترجم بحرية؛ يُقبل هذا الشكل الكامل فقط
        # إذا وُجدت له قيمة معجمية حاكمة مثل «الأدنى» ← Low.
        label = re.fullmatch(r"·\s*(الأدنى|الأعلى)\s*:", n)
        if label:
            value = lookup(label.group(1))
            if value and not ARABIC.search(value):
                lead = u[: len(u) - len(u.lstrip())]
                trail = u[len(u.rstrip()):]
                return lead + f"· {value}:" + trail
        direct = lookup(n, ltr_tokens)
        if direct is not None:
            # ك-488: كان الاستبدال يجري بالنص المطبَّع داخل النص الأصلي، فإذا حمل
            # النص العربي تشكيلًا (شدّة أو تطويل) لا يجد `replace` مطابقة، فيبقى
            # النص عربيًا ثم يُجزّأ في الحلقة الاحتياطية إلى مقاطع مشوَّهة
            # («Aو» و«Additions Newة»). الحل: إن طابق تطبيع الوحدة مفتاحًا كاملًا،
            # تُعاد الترجمة كاملة مع الحفاظ على المسافات الطرفية.
            if n == norm(u):
                lead = u[: len(u) - len(u.lstrip())]
                trail = u[len(u.rstrip()):]
                return lead + direct + trail
            return u.replace(n, direct)
        res, ok = u, True
        for part in re.split(r"(?<=[…·])\s*", u):
            p = norm(part)
            if not p or not ARABIC.search(p):
                continue
            hit = lookup(p, ltr_tokens)
            if hit is None:
                ok = False
                break
            res = res.replace(part, part.replace(p, hit))
        if ok:
            return res
        for k in keys:
            if (k in res and _partial_key_safe(norm(res), k)
                    and not _crosses_ltr_boundary(u, k, ltr_tokens)):
                res = res.replace(k, tm.get(k) or gl.get(k) or '')
        if not ARABIC.search(res):
            return res
        # ك-337: احتياط على مستوى الجملة — النص قد يُقطَّع إلى عقد نصية حول وسوم داخلية،
        # فتُترجم كل جملة على حدة بالمطابقة المباشرة ثم بالأطول الموجود، بلا تخمين.
        parts = re.split(r"(?<=[.؟!؛])\s+|\s+·\s+", res)
        if len(parts) > 1:
            outs, allok = [], True
            for p in parts:
                pn = norm(p)
                if not pn or not ARABIC.search(pn):
                    outs.append(p); continue
                hit = lookup(pn, ltr_tokens)
                if hit is None:
                    cand = [k for k in keys if k and k in pn
                            and _partial_key_safe(pn, k)
                            and not _crosses_ltr_boundary(pn, k, ltr_tokens)]
                    if cand:
                        hit = tm.get(max(cand, key=len)) or gl.get(max(cand, key=len))
                    else:
                        allok = False; outs.append(p); continue
                outs.append(p.replace(pn, hit))
            joined = " ".join(outs)
            if allok or not ARABIC.search(joined):
                return joined
            res = joined
        return res

    return translate



# ك-320: تصحيح تسميات الشريط الثابتة في النسخة الإنجليزية.
# سبب الإصلاح: المترجم النصي يترجم الحروف المفردة ترجمة خاطئة (ع ← Aden، أ ← issued)
# وبعض سمات أدوات التحكم تبقى عربية. تُثبَّت هنا صراحةً بعد الترجمة.
_CHROME_FIX = {
    'aria-label="تنقل Location"': 'aria-label="Site navigation"',
    'aria-label="تنقل الموقع"': 'aria-label="Site navigation"',
    'aria-label="اللغة / Language"': 'aria-label="Language"',
    'aria-label="حجم الخط"': 'aria-label="Text size"',
    'title="العربية"': 'title="Arabic"',
    'title="حجم عادي"': 'title="Normal size"',
    'title="حجم أكبر"': 'title="Larger size"',
    'title="أكبر حجم"': 'title="Largest size"',
    '>Aden</button>': '>AR</button>',
    '>issued</button>': '>A</button>',
    '>أ+</button>': '>A+</button>',
    '>أ++</button>': '>A++</button>',
    'title="A+"': 'title="Larger size"',
    'title="A++"': 'title="Largest size"',
    'خريطة ': 'Map of ',
}


def _fix_chrome(out: str) -> str:
    for a, b in _CHROME_FIX.items():
        out = out.replace(a, b)
    # ك-320 (تكملة): أي وسم إمكانية وصول يبقى عربيًا في النسخة الإنجليزية يُستبدل بنص إنجليزي صريح،
    # فلا تُقرأ واجهة إنجليزية عربيةَ على قارئ الشاشة.
    def _lbl(m):
        v = m.group(1)
        # تُترجم أسماء الوصول الوصفية عبر المعجم نفسه؛ ولا يبقى نص عام مبتسر.
        try:
            tr = translate(v)
        except Exception:
            tr = ""
        if not tr or tr == v or re.search(r"[\u0600-\u06FF]", tr or ""):
            try:
                tr = localize_patterns(v) or tr
            except Exception:
                pass
        if tr and tr != v and not re.search(r"[\u0600-\u06FF]", tr):
            return 'aria-label="%s"' % tr.replace('"', "&quot;")
        en = "Map of the region with incident locations" if "خريطة" in v else "Section"
        return 'aria-label="%s"' % en
    out = re.sub(r'aria-label="([^"]*[\u0600-\u06FF][^"]*)"', _lbl, out)
    return out


def _collapse_inline_source_duplicates(out: str) -> str:
    """Keep a source node's translated text once when its organization is a ltr child.

    HTMLParser exposes text on either side of ``<span class="ltr">UKMTO</span>``
    as separate units. A glossary hit for the first unit can already contain the
    organization and the trailing unit can then repeat its suffix. Collapse only
    an exact suffix repetition; never use a broad substring replacement.
    """
    pattern = re.compile(
        r'(?P<before>[^<>]*\b(?P<org>UKMTO|JMIC|IMO|VLIZ|Marine Regions|Natural Earth)\b[^<>]*)'
        r'(?P<span><span\b[^>]*\bclass="ltr"[^>]*>\s*(?P=org)\s*</span>)'
        r'(?P<after>[^<>]*)',
        re.IGNORECASE,
    )

    def replace(match: re.Match[str]) -> str:
        before = match.group("before")
        after = match.group("after")
        org = match.group("org")
        before_without_org = re.sub(rf"\b{re.escape(org)}\b", "", before, flags=re.IGNORECASE)
        left = norm(before_without_org).rstrip(".!؟؛")
        right = norm(after).lstrip(".!؟؛").rstrip(".!؟؛")
        if right and left.endswith(right):
            # Keep the source organization's bidi-safe span, not a second plain-text copy.
            clean_before = re.sub(r"[ \t]{2,}", " ", before_without_org)
            return clean_before + match.group("span")
        return match.group(0)

    # هذه العملية انقاصية: كل استبدال صالح يحذف نسخة نصية من المصدر، لذلك
    # لا يجوز أن يتجاوز عدد الدورات طول HTML الابتدائي، ولا يجوز تمرير نتيجة
    # تغيّرت من دون أن تنقص. الفشل هنا مانع حتى لا يعاد بناء تقرير غير موثوق.
    max_iterations = max(1, len(out) + 1)
    for iteration in range(1, max_iterations + 1):
        next_out = pattern.sub(replace, out)
        if next_out == out:
            return out
        if len(next_out) >= len(out):
            raise RuntimeError(
                "حارس ترجمة مانع: ضغط تكرارات المصادر لم يكن انقاصيًا "
                f"في الدورة {iteration} (الطول {len(out)} ثم {len(next_out)})."
            )
        out = next_out
    raise RuntimeError(
        "حارس ترجمة مانع: ضغط تكرارات المصادر لم يصل إلى الثبات "
        f"ضمن السقف الانقاصي {max_iterations} دورة."
    )


def card_row_labels() -> dict[str, str]:
    """عناوين صفوف البطاقات بالإنجليزية من عقدها الحاكم، لا من ترجمة حرّة للعنوان العربي."""
    path = pathlib.Path("sources") / "card_registry.json"
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, str] = {}
    for card in registry.get("cards", []) or []:
        cid = str(card.get("id"))
        for counter in card.get("counters", []) or []:
            key = str(counter.get("key"))
            label_en = counter.get("row_label_en")
            if cid and key and label_en:
                out[f"{cid}:{key}"] = label_en
    return out


def _governed_event_card_labels(gl: dict[str, str]) -> dict[str, str]:
    """اقرأ أوسمة صفوف بطاقة الأحداث من العقد ثم حلّها في المعجم.

    قد يطابق مترجم النص مفتاحًا أطول يبدأ بكلمة «المصدر» ويضع عنوان جدول
    («Source and limits») داخل وسم البطاقة. هذه الأوسمة بنيوية، لذلك تُثبت
    بعد الترجمة من العقد نفسه، مع اشتقاق «Source» من مدخل المعجم ذي البادئة
    عندما لا يوجد مدخل مباشر.
    """
    contract_path = BRAIN / "appendices" / "event-card-contract.md"
    try:
        contract = contract_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    section = re.search(
        r"^##\s+الصفوف التسعة\s*$.*?(?=^###\s+الصف الملغى\s*$)",
        contract,
        re.M | re.S,
    )
    if not section:
        return {}
    ar_labels = {
        int(match.group(1)): match.group(2).strip()
        for match in re.finditer(
            r"^\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", section.group(0), re.M
        )
    }
    labels: dict[str, str] = {}
    for number in (4, 5, 6, 7, 8):
        arabic = ar_labels.get(number, "")
        if not arabic:
            continue
        english = gl.get(arabic, "")
        if not english:
            prefixed = [
                value for key, value in gl.items()
                if isinstance(key, str) and key.startswith(f"{arabic}:")
                and isinstance(value, str) and value.strip()
            ]
            if len(prefixed) == 1:
                english = prefixed[0].split(":", 1)[0].strip()
        if english and not ARABIC.search(english):
            labels[str(number)] = english.strip()
    return labels


_EVENT_CARD_LABEL_RE = re.compile(
    r'(?P<prefix><div\b(?=[^>]*\bclass="ev-field\b)'
    r'(?=[^>]*\bdata-row="(?P<row>\d+)")[^>]*>.*?'
    r'<span\b(?=[^>]*\bclass="ev-k\b)[^>]*>)'
    r'(?P<label>[^<]*)(?P<suffix></span>)',
    re.S,
)


def _apply_governed_event_card_labels(out: str, gl: dict[str, str]) -> str:
    """ثبّت الأوسمة البنيوية بعد الترجمة، ولا تغيّر قيم الصفوف أو متنها."""
    labels = _governed_event_card_labels(gl)
    if not labels:
        return out

    def replace(match: re.Match[str]) -> str:
        label = labels.get(match.group("row"))
        if not label:
            return match.group(0)
        return match.group("prefix") + label + match.group("suffix")

    return _EVENT_CARD_LABEL_RE.sub(replace, out)


def _apply_card_row_labels(out: str) -> str:
    """يثبّت نصّ كل صف بطاقة مُوسَّم على نص العقد الإنجليزي."""
    labels = card_row_labels()
    if not labels:
        return out

    def repl(match: "re.Match[str]") -> str:
        key = match.group("key")
        label = labels.get(key)
        if not label:
            return match.group(0)
        return (f'<div class="sc-l" data-card-label="{key}">{label}</div>')

    return re.sub(r'<div class="sc-l" data-card-label="(?P<key>[^"]+)">[^<]*</div>', repl, out)


_HTML_PART_TAG = re.compile(r"^<(/?)([A-Za-z][A-Za-z0-9:-]*)(.*?)>$", re.S)
_LTR_GROUP_BLOCKS = frozenset({
    "address", "article", "aside", "blockquote", "body", "caption", "dd", "details",
    "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1",
    "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "menu", "nav",
    "ol", "p", "pre", "section", "summary", "table", "tbody", "td", "tfoot", "th",
    "thead", "tr", "ul",
})
_INLINE_VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input",
                              "link", "meta", "param", "source", "track", "wbr"})


def _html_unit_contexts(c: _Collector) -> tuple[list[dict[str, object]], list[int]]:
    """Return each text unit's ancestor tags and KPI id from the collected HTML."""
    contexts: list[dict[str, object]] = []
    positions: list[int] = []
    stack: list[tuple[str, str]] = []
    for part_index, part in enumerate(c.parts):
        if part == "\u0000":
            kpi_id = None
            classes: list[str] = []
            for _, attrs in reversed(stack):
                match = re.search(r'\bdata-kpi-id="([^"]+)"', attrs)
                if match:
                    kpi_id = match.group(1)
                match = re.search(r'\bclass="([^"]*)"', attrs)
                if match:
                    classes.extend(match.group(1).split())
            contexts.append({
                "tags": tuple(tag for tag, _ in stack),
                "classes": tuple(classes),
                "kpi_id": kpi_id,
            })
            positions.append(part_index)
            continue
        match = _HTML_PART_TAG.fullmatch(part)
        if not match:
            continue
        closing, tag, attrs = match.groups()
        tag = tag.lower()
        if closing:
            for index in range(len(stack) - 1, -1, -1):
                if stack[index][0] == tag:
                    del stack[index:]
                    break
        elif not part.rstrip().endswith("/>"):
            stack.append((tag, attrs))
    return contexts, positions


def _inline_tag_groups(c: _Collector, positions: list[int]) -> list[dict[str, object]]:
    """Locate sentence runs flanking inline elements, bounded by block-level HTML tags."""
    records: list[dict[str, object]] = []
    for open_index, part in enumerate(c.parts):
        match = _HTML_PART_TAG.fullmatch(part)
        if not match or match.group(1):
            continue
        tag = match.group(2).lower()
        # رقم ترتيب الواقعة عنصر بنيوي مستقل، فلا يدخل في الجملة الديناميكية المجاورة.
        structural_index = tag == "span" and bool(
            re.search(r'\bclass="[^\"]*\bdg-idx\b[^\"]*"', match.group(3))
        )
        if (tag in _LTR_GROUP_BLOCKS or tag in _INLINE_VOID_TAGS
                or part.rstrip().endswith("/>") or structural_index):
            continue
        depth, close_index = 1, None
        for candidate_index in range(open_index + 1, len(c.parts)):
            candidate = _HTML_PART_TAG.fullmatch(c.parts[candidate_index])
            if not candidate or candidate.group(2).lower() != tag:
                continue
            is_close, _, attrs = candidate.groups()
            if is_close:
                depth -= 1
                if depth == 0:
                    close_index = candidate_index
                    break
            elif not c.parts[candidate_index].rstrip().endswith("/>"):
                depth += 1
        if close_index is None:
            continue
        before = [(pos, unit) for unit, pos in enumerate(positions) if pos < open_index]
        after = [(pos, unit) for unit, pos in enumerate(positions) if pos > close_index]
        inside = [unit for unit, pos in enumerate(positions) if open_index < pos < close_index]
        if not inside:
            continue
        before_pos, start = before[-1] if before else (open_index, inside[0])
        after_pos, end = after[0] if after else (close_index, inside[-1])
        if start >= end:
            continue
        if any(
            tag_match and tag_match.group(2).lower() in _LTR_GROUP_BLOCKS
            for fragment in c.parts[before_pos + 1 : after_pos]
            for tag_match in [_HTML_PART_TAG.fullmatch(fragment)]
        ):
            continue
        token = norm("".join(c.units[index] for index in inside))
        if not token:
            continue
        # لا يلتقط الحامل نصًا يحتوي وسمًا متداخلًا؛ تُعالج أصغر وحدة سطرية أولًا.
        if any(_HTML_PART_TAG.fullmatch(fragment)
               for fragment in c.parts[open_index + 1 : close_index]):
            continue
        if not ARABIC.search(norm("".join(c.units[start : end + 1]))):
            continue
        records.append({
            "start": start,
            "end": end,
            "spans": [(token, part, c.parts[close_index])],
            "tag_parts": [(open_index, close_index)],
        })

    groups: list[dict[str, object]] = []
    for record in sorted(records, key=lambda item: (item["start"], item["end"])):
        if groups and record["start"] <= groups[-1]["end"]:
            groups[-1]["end"] = max(groups[-1]["end"], record["end"])
            groups[-1]["spans"].extend(record["spans"])
            groups[-1]["tag_parts"].extend(record["tag_parts"])
        else:
            groups.append(record)
    return groups


def _master_document_heading(date: str) -> str | None:
    """Read the canonical first-level heading for a safe, source-backed fallback."""
    path = I18N / f"{date}-sectioned.en.md"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^#\s+", line):
                heading = plain(line)
                return heading if heading and not ARABIC.search(heading) else None
    except (OSError, UnicodeError):
        return None
    return None


def _master_dynamic_title_components(date: str) -> tuple[str, str, str] | None:
    """Read the incident indicator, sector label, and decision basis from the English master."""
    path = I18N / f"{date}-sectioned.en.md"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None

    indicator = sector = basis = None
    sector_labels: list[str] = []
    for line in lines:
        sector_match = re.fullmatch(r"- Level in (?P<sector>.+?): [A-Za-z ]+", line.strip())
        if sector_match:
            sector_labels.append(sector_match.group("sector"))
        if not line.strip().startswith("|"):
            continue
        cells = [norm(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[0] == "UKMTO reports of incidents in Z1 during the period":
            indicator = cells[0]
        if len(cells) == 4 and cells[0].startswith("Strait of Hormuz,"):
            candidate = cells[3]
            if candidate.startswith("UKMTO reports of incidents in Hormuz align with "):
                match = re.fullmatch(
                    r"UKMTO reports of incidents in Hormuz align with (.+)\.", candidate
                )
                sector_label = next(
                    (label for label in sector_labels
                     if norm(label.removeprefix("the ")) == cells[0]),
                    None,
                )
                if match and sector_label:
                    sector, basis = sector_label, match.group(1)
    if not indicator or not sector or not basis:
        return None
    return indicator, sector, basis


def _compose_master_dynamic_title(source: str, tags: set[str], classes: set[str], date: str) -> str | None:
    """Compose only master-backed titles using declared source components.

    H1: retain the source count, use the matching sector label from the body, and
    append the decision-basis clause from the same sector-table row. Incident card:
    take the indicator row verbatim and replace its Z1 token with that sector label.
    """
    components = _master_dynamic_title_components(date)
    if not components:
        return None
    indicator, sector, basis = components

    if "h1" in tags:
        count = re.search(r"\bعن\s+(?P<count>ثلاث|ثلاثة|\d+)\s+وقائع\b", source)
        if count and re.search(r"\bUKMTO\b", source):
            raw_count = count.group("count")
            count_en = {"ثلاث": "3", "ثلاثة": "3"}.get(raw_count, raw_count)
            return (
                f"UKMTO reports of {count_en} incidents in {sector} align with {basis}"
            )

    if "dg-t" in classes and re.search(
        r"بلاغات\s+UKMTO\s+عن\s+وقائع\b.*(?:داخل|خلال)\s+الفترة$", source
    ):
        return indicator.replace("Z1", sector, 1)
    return None


def _preserves_numeric_tokens(source: str, translated: str) -> bool:
    return _numeric_tokens(source) == _numeric_tokens(translated)


_AR_NUM_COMPOUND = {
    "اثنتا عشرة": 12, "اثنتي عشرة": 12, "اثنا عشر": 12, "اثني عشر": 12,
    "إحدى عشرة": 11, "أحد عشر": 11, "احدى عشرة": 11, "احد عشر": 11,
    "ثلاثة عشر": 13, "ثلاث عشرة": 13, "أربعة عشر": 14, "أربع عشرة": 14,
    "خمسة عشر": 15, "خمس عشرة": 15, "ستة عشر": 16, "ست عشرة": 16,
    "سبعة عشر": 17, "سبع عشرة": 17, "ثمانية عشر": 18, "ثماني عشرة": 18,
    "تسعة عشر": 19, "تسع عشرة": 19,
}
# ك-601: مركّبات العربية 21–99 تُولَّد من جدولين صغيرين فلا تُكتب يدويًا
_AR_NUM_ONES = {
    "واحد": 1, "واحدة": 1, "إحدى": 1, "احدى": 1, "أحد": 1, "احد": 1,
    "اثنان": 2, "اثنين": 2, "اثنتان": 2, "اثنتين": 2, "ثلاثة": 3, "ثلاث": 3,
    "أربعة": 4, "أربع": 4, "خمسة": 5, "خمس": 5, "ستة": 6, "ست": 6,
    "سبعة": 7, "سبع": 7, "ثمانية": 8, "ثماني": 8, "تسعة": 9, "تسع": 9,
}
_AR_NUM_TENS_WORDS = {
    "عشرون": 20, "ثلاثون": 30, "أربعون": 40, "خمسون": 50,
    "ستون": 60, "سبعون": 70, "ثمانون": 80, "تسعون": 90,
}
_AR_NUM_COMPOUND.update({
    f"{one} و{tens}": one_value + tens_value
    for one, one_value in _AR_NUM_ONES.items()
    for tens, tens_value in _AR_NUM_TENS_WORDS.items()
})
_AR_NUM_TENS = {
    "عشرون": 20, "ثلاثون": 30, "أربعون": 40, "خمسون": 50, "ستون": 60,
    "سبعون": 70, "ثمانون": 80, "تسعون": 90, "مئة": 100, "مائة": 100,
}
_EN_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
    "single": 1, "double": 2, "triple": 3, "dozen": 12,
}


def _numeric_tokens(text: str) -> list[str]:
    """يقارن الأرقام بقيمتها لا بشكلها (ك-601).

    العيب المقيس: كانت الدالة تقرأ الأرقام الرقمية وكلمات العدّ العربية فقط،
    فتُعدّ ترجمة «ثلاثة تحذيرات» إلى "Three warnings" فقدًا للرقم 3، ويُرفض
    البناء مغلقًا على نص مترجم سليم. القاعدة: تُقرأ الأعداد على الجانبين —
    رقميةً أو مكتوبةً بالعربية أو بالإنجليزية — وتُقارن بقيمتها، فلا يمرّ
    رقم مفقود، ولا يُرفض رقم محفوظ بصيغة أخرى.
    """
    tokens = re.findall(r"\d+", text)
    work = text
    for word, value in _AR_NUM_COMPOUND.items():
        while word in work:
            tokens.append(str(value))
            work = work.replace(word, " ", 1)
    for word, value in _AR_NUM_TENS.items():
        while word in work:
            tokens.append(str(value))
            work = work.replace(word, " ", 1)
    english_digits = {
        "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
        "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    }
    for arabic, english in WARNING_COUNT_WORD.items():
        digit = english_digits.get(english)
        if digit:
            while re.search(rf"(?<![\u0600-\u06FF]){re.escape(arabic)}(?![\u0600-\u06FF])", work):
                tokens.append(digit)
                work = re.sub(
                    rf"(?<![\u0600-\u06FF]){re.escape(arabic)}(?![\u0600-\u06FF])",
                    " ", work, count=1,
                )
    # كلمات الأعداد الإنجليزية: مفردة، ومركّبة بشرطة (thirty-one)، ومعها "hundred"
    # ك-601: الكلمة المركّبة قد تحمل عددًا في جزء واحد فقط ("single-source")،
    # فلا يجوز اشتراط أن تكون كل أجزائها أعدادًا وإلا سقط العدد.
    for phrase in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*", work):
        parts = [w.lower() for w in phrase.split("-")]
        values = [_EN_NUM_WORDS.get(w) for w in parts]
        if all(v is not None for v in values):
            current = 0
            for v in values:
                current = (current or 1) * 100 if v == 100 else current + v
            tokens.append(str(current))
        else:
            for v in values:
                if v is not None:
                    tokens.append(str(v))
    return sorted(tokens, key=lambda value: (int(value), len(value)))


def _plan_ltr_translations(
    c: _Collector,
    groups: list[dict[str, object]],
    contexts: list[dict[str, object]],
    tm: dict[str, str],
    gl: dict[str, str],
    tr,
    date: str,
):
    """Translate whole exact runs, then restore each inline element at its source token."""
    overrides: dict[int, str] = {}
    covered: set[int] = set()
    translated_checks: list[tuple[str, str]] = []
    unmatched: list[tuple[int, int, str]] = []
    placeholders: dict[str, str] = {}
    consumed_tag_parts: set[int] = set()
    for group in groups:
        start, end = int(group["start"]), int(group["end"])
        source_raw = "".join(c.units[start : end + 1])
        source = norm(source_raw)
        word_count = len(re.findall(r"[A-Za-z0-9\u0600-\u06ff]+", source))
        sentence_like = word_count >= 5 or bool(re.search(r"[.!؟؛]$", source))
        governed_label = source in gl
        exact_key = source in tm or governed_label
        composed_target = None
        tags = contexts[start]["tags"]
        classes = contexts[start]["classes"]
        if not exact_key:
            composed_target = _compose_master_dynamic_title(source, tags, classes, date)
            if composed_target is None:
                # Keep unmatched title content in place; the normal missing-text
                # check will fail closed rather than discarding visible content.
                continue
            exact_key = True
        # A full master sentence may cross an inline LTR tag; a short nominal
        # phrase may cross only when its complete label is in the governed glossary.
        if exact_key and not (sentence_like or governed_label):
            continue
        target = composed_target or (tr(source) if source else "")
        rendered = target
        group_placeholders: dict[str, str] = {}
        # ك-602: المقابل المعلَن تمامًا (ذاكرة ترجمة أو معجم) مرجعٌ حاكم، فلا
        # يُعاد عليه فحص تساوي الرموز الرقمية؛ لأن العربية تكتب العدد صيغةً
        # («يومين») والإنجليزية كلمةً ("two") فيُرفض مقابل معلَن ويبقى نص عربي.
        # الفحص يبقى قائمًا على كل مقابل مشتق/مركّب، فلا يمرّ رقم مفقود.
        from_governed_pair = bool(source and (source in tm or source in gl))
        if target and not ARABIC.search(target) and (
                from_governed_pair or _preserves_numeric_tokens(source, target)):
            valid = True
            token_specs: list[tuple[str, str, str, re.Pattern[str]]] = []
            tagged_counts: dict[str, int] = {}
            for token, opening_tag, closing_tag in group["spans"]:
                normalized_token = norm(token)
                token_re = re.compile(rf"(?<!\w){re.escape(normalized_token)}(?!\w)", re.IGNORECASE)
                translated_token = normalized_token
                token_match = token_re.search(rendered)
                if not token_match and ARABIC.search(normalized_token):
                    translated_token = norm(tr(normalized_token))
                    if translated_token and not ARABIC.search(translated_token):
                        token_re = re.compile(
                            rf"(?<!\w){re.escape(translated_token)}(?!\w)", re.IGNORECASE
                        )
                        token_match = token_re.search(rendered)
                if not token_match:
                    valid = False
                    break
                tagged_counts[translated_token.casefold()] = (
                    tagged_counts.get(translated_token.casefold(), 0) + 1
                )
                token_specs.append((translated_token, opening_tag, closing_tag, token_re))

            if valid:
                # إن كررت الترجمة كيانًا أكثر مما ظهر في الأصل، يُحتفظ بعدد الأصل فقط.
                for translated_token, _, _, token_re in token_specs:
                    folded_token = translated_token.casefold()
                    if folded_token not in tagged_counts:
                        continue
                    allowed = max(
                        tagged_counts[folded_token],
                        len(token_re.findall(source)),
                    )
                    matches = list(token_re.finditer(rendered))
                    for extra in reversed(matches[allowed:]):
                        rendered = rendered[:extra.start()] + rendered[extra.end():]
                    tagged_counts.pop(folded_token, None)
                rendered = re.sub(r"[ \t]{2,}", " ", rendered)

                for translated_token, opening_tag, closing_tag, token_re in token_specs:
                    token_match = token_re.search(rendered)
                    if not token_match:
                        valid = False
                        break
                    marker = f"\u0001MDA_INLINE_{len(placeholders) + len(group_placeholders)}\u0002"
                    rendered = (rendered[:token_match.start()] + marker
                                + rendered[token_match.end():])
                    escaped_token = (token_match.group(0).replace("&", "&amp;")
                                     .replace("<", "&lt;").replace(">", "&gt;"))
                    group_placeholders[marker] = opening_tag + escaped_token + closing_tag

            if valid and token_specs:
                lead = source_raw[: len(source_raw) - len(source_raw.lstrip())]
                trail = source_raw[len(source_raw.rstrip()):]
                overrides[start] = lead + rendered + trail
                placeholders.update(group_placeholders)
                for opening_index, closing_index in group.get("tag_parts", []):
                    consumed_tag_parts.update((int(opening_index), int(closing_index)))
                covered.update(range(start, end + 1))
                translated_checks.append((source, target))
                continue

        covered.update(range(start, end + 1))
        unmatched.append((start, end, source))
    return overrides, covered, translated_checks, unmatched, placeholders, consumed_tag_parts


def _remove_empty_ltr_spans(page: str) -> str:
    return re.sub(r'<span\b(?=[^>]*\bclass="[^"]*\bltr\b[^"]*")[^>]*>\s*</span>', "", page)


def _latest_official_title_en(date: str) -> str | None:
    """Read the bilingual latest-official title from the issue's governing metadata."""
    path = ROOT / "sources" / "meta" / f"{date}.json"
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    card = next(
        (item for item in meta.get("hero_kpis", [])
         if isinstance(item, dict) and item.get("id") == "latest-official"),
        None,
    )
    title = norm(card.get("title_en", "")) if card else ""
    return title if title and not ARABIC.search(title) else None


def _drop_latest_official_cards(page: str, date: str) -> tuple[str, int]:
    """Keep each latest-official KPI and fill its label from the governing data contract."""
    title = _latest_official_title_en(date)
    if not title:
        return page, 0
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    opener = re.compile(r'<div\b(?=[^>]*\bdata-kpi-id="latest-official")[^>]*>', re.I)
    div_tag = re.compile(r"</?div\b[^>]*>", re.I)
    label = re.compile(
        r'(<div\b(?=[^>]*\bclass="[^"]*\bk-l\b[^"]*")[^>]*>).*?(</div>)',
        re.I | re.S,
    )
    starts = list(opener.finditer(page))
    updated = 0
    for opening in reversed(starts):
        depth, close_end = 1, None
        for tag in div_tag.finditer(page, opening.end()):
            if tag.group(0).startswith("</"):
                depth -= 1
                if depth == 0:
                    close_end = tag.end()
                    break
            elif not tag.group(0).rstrip().endswith("/>"):
                depth += 1
        if close_end is None:
            continue
        card = page[opening.start():close_end]
        card, count = label.subn(lambda match: match.group(1) + safe_title + match.group(2), card, count=1)
        if count:
            page = page[: opening.start()] + card + page[close_end:]
            updated += 1
    return page, updated


_ELEMENT_RE = re.compile(
    r"<(p|li|td|h3|h4|blockquote)\b([^>]*)>(.*?)</\1>", re.S | re.I)
_INLINE_RE = re.compile(r"<(span|strong|b|em|bdi)\b([^>]*)>(.*?)</\1>", re.S | re.I)


def _element_governed_overrides(html_text: str, tm: dict[str, str], gl: dict[str, str]) -> str:
    """ك-603: عنصر كامل له مقابل معلَن تمامًا لكنه يتقطّع بوسم سطري داخلي.

    العيب المقيس: بند الإضافات يُبنى داخل <p> مع <strong> و<span class="ltr">، فيتقطّع
    عند المترجم إلى مقاطع لا مقابل لها، ويُرفض البناء مغلقًا على نص له مقابل معلَن.
    القاعدة: إن كان نص العنصر كاملًا — بلا وسوم — مطابقًا لمقابل معلَن في ذاكرة الترجمة
    أو المعجم، ويحفظ المقابل أرقامه ومعرّفاته، فلا يُبقى فيه نص عربي ولا يُسقط رقم،
    وتُعاد الوسوم حول الرموز اللاتينية نفسها. المطابقة التامة وحدها تُقبل، ولا تخمين.
    """

    def replace(match: re.Match[str]) -> str:
        tag, attrs, inner = match.group(1), match.group(2), match.group(3)
        if _ELEMENT_RE.search(inner):
            return match.group(0)
        plain = norm(re.sub(r"<[^>]+>", " ", inner))
        # تُترجم ملاحظة التوصيات من HTML الخام كي تبقى مرساتها ورابطها محفوظين.
        if '<a class="dc-jump" href="#sec-decision">' in inner:
            tagged = localize_patterns(norm(inner))
            if (tagged and not ARABIC.search(tagged)
                    and _preserves_numeric_tokens(plain, tagged)):
                return f"<{tag}{attrs}>{tagged}</{tag}>"
        # لا تسبق الترجمة التامة مخطط الوسوم السطرية؛ فهو يفرض حدود LTR
        # ويحدّ تكرار الكيان بعد إعادته إلى موضعه الأصلي.
        if _INLINE_RE.search(inner):
            return match.group(0)
        # حدّ الوسم قد يُدخل فراغًا قبل ترقيم عربي («JMIC ،» بدل «JMIC،»)،
        # فيُطابَق النص بصيغتين: كما هو، وبلا فراغ قبل الترقيم.
        keys = [plain, re.sub(r"\s+([،؛:.!؟])", r"\1", plain)]
        lookup = next((k for k in keys if k in tm or k in gl), None)
        if lookup is None:
            return match.group(0)
        plain = lookup
        # ذاكرة الترجمة قد تحمل صيغة لا تحفظ الأرقام بينما المعجم يحفظها،
        # فيُفحص المرشحان ويُقبل الصالح منهما، ولا يُقبل ما يُسقط رقمًا.
        source_tokens = _numeric_tokens(plain)
        target = next(
            (candidate for candidate in (tm.get(plain), gl.get(plain))
             if candidate and not ARABIC.search(candidate)
             and all(token in _numeric_tokens(candidate) for token in source_tokens)),
            None,
        )
        if not target:
            return match.group(0)
        rendered = target
        for token_match in _INLINE_RE.finditer(inner):
            start_inner, end_inner = token_match.start(3), token_match.end(3)
            opening = token_match.group(0)[: start_inner - token_match.start(0)]
            closing = token_match.group(0)[end_inner - token_match.start(0):]
            token = norm(token_match.group(3))
            if not token or ARABIC.search(token):
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(token)}(?!\w)", re.IGNORECASE)
            hit = pattern.search(rendered)
            if hit:
                escaped = (hit.group(0).replace("&", "&amp;")
                           .replace("<", "&lt;").replace(">", "&gt;"))
                rendered = rendered[: hit.start()] + opening + escaped + closing + rendered[hit.end():]
        return f"<{tag}{attrs}>{rendered}</{tag}>"

    return _ELEMENT_RE.sub(replace, html_text)


def translate_page(html_text: str, date: str, tm: dict[str, str], gl: dict[str, str]):
    html_text = _element_governed_overrides(html_text, tm, gl)
    latest_title_value = _latest_official_title_en(date)
    if latest_title_value:
        gl = dict(gl)
        gl["أحدث بلاغ رسمي"] = latest_title_value
    tr = make_translator(tm, gl)
    c = _Collector()
    c.feed(html_text)
    counter_labels = _sector_counter_labels()
    def _bold(t: str) -> str:
        """يحوّل **نص** إلى <b>نص</b> ويمنع ظهور علامات النجمة الخام للقارئ (عطل ك-492).

        السبب: قيم المعجم الإنجليزية كُتبت بعلامات تأكيد Markdown، والترجمة تُدرجها
        في HTML مباشرة فتظهر النجوم نصًّا. العربية تُخرج التسميات عريضة، فالمواءمة
        تقتضي إخراجًا عريضًا لا نجومًا.
        """
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        return t.replace("**", "")

    # ك-592: التقاط الوسم اللاتيني الذي يسبق عقدة نصية داخل العنصر نفسه،
    # فبعض الجمل تبدأ باسم جهة لاتيني ثم معناها العربي («IMO — ...»).
    pre_tokens: list[str | None] = []
    _prev_latin: str | None = None
    _gap_clean = True
    _uidx = 0
    for _p in c.parts:
        if _p == "\u0000":
            pre_tokens.append(_prev_latin if (_prev_latin and _gap_clean) else None)
            _u = c.units[_uidx]
            _uidx += 1
            _nu = norm(_u)
            _tok = _u.strip()
            _prev_latin = (_tok if (_nu and not ARABIC.search(_nu) and 0 < len(_tok) <= 24)
                           else None)
            _gap_clean = True
        elif _p.lstrip().startswith('<') or not _p.strip():
            continue
        else:
            # نص ظاهر بين وحدتين (مثل «و») يفصل بينهما، فلا تُعدّ السابقة بادئة
            _gap_clean = False
            _prev_latin = None
    unit_contexts, unit_positions = _html_unit_contexts(c)
    ltr_groups = _inline_tag_groups(c, unit_positions)
    (ltr_overrides, ltr_covered, ltr_checks, ltr_unmatched,
     ltr_placeholders, consumed_tag_parts) = _plan_ltr_translations(
        c, ltr_groups, unit_contexts, tm, gl, tr, date
    )
    units = [_bold(_translate_counter_fragment(t, counter_labels)
                   if c.unit_contexts[i] == "tz-count"
                   else tr(t, pre_tokens[i] if i < len(pre_tokens) else None,
                           c.unit_ltr_tokens[i]))
             for i, t in enumerate(c.units)]
    for index in ltr_covered:
        units[index] = ""
    for start, value in ltr_overrides.items():
        units[start] = _bold(value)
    for start, end, _ in ltr_unmatched:
        for index in range(start, end + 1):
            units[index] = c.units[index]
    attrs = [_bold(tr(a)) for a in c.attrs_seen]
    parts, k = [], 0
    for part_index, p in enumerate(c.parts):
        if part_index in consumed_tag_parts:
            continue
        if p == "\u0000":
            parts.append(units[k]); k += 1
        else:
            for i, a in enumerate(attrs):
                p = p.replace(f'__ATTR{i}__', a)
            parts.append(p)
    out = "".join(parts)
    for marker, span_html in ltr_placeholders.items():
        out = out.replace(marker, span_html)
    out = _remove_empty_ltr_spans(out)
    out, _latest_cards_labeled = _drop_latest_official_cards(out, date)
    head_end = out.find(">")
    head = out[: head_end + 1]
    head = re.sub(r'lang="[^"]*"', 'lang="en"', head) if 'lang=' in head else head[:-1] + ' lang="en">'
    head = re.sub(r'dir="[^"]*"', 'dir="ltr"', head) if 'dir=' in head else head[:-1] + ' dir="ltr">'
    head = head if 'data-lang="en"' in head else head[:-1] + ' data-lang="en">'
    out = head + out[head_end + 1 :]
    m = re.search(r"<body([^>]*)>", out)
    if m:
        a = m.group(1)
        if "class=" in a:
            a = re.sub(r'class="', 'class="lang-en ', a, count=1)
        else:
            a = a + ' class="lang-en"'
        out = out[: m.start(1)] + a + out[m.end(1):]
    out = re.sub(r"<title>.*?</title>", f"<title>Daily Maritime Security Report — {date} (English edition)</title>", out, flags=re.S)
    out = re.sub(r'<meta name="description" content="[^"]*"',
                 '<meta name="description" content="Daily Maritime Security Report — English edition, translated and governed against the Arabic source.">', out)
    def _unit_ok(orig: str, translated: str) -> bool:
        """الوحدة مترجمة إذا نجحت الترجمة أو نجح محرك الأنماط عليها.

        محرك الأنماط مسار ثانٍ محكوم (مثل نمط تفصيل الحريق)، فلا يُعدّ النص
        العربي المتحرك عطلًا إذا كان له نمط معتمد يترجمه بالأرقام.

        تشديد ك-447/ك-447: أي حرف عربي متبقٍّ في المخرج الإنجليزي عطل مانع،
        ولو كان حرفًا واحدًا؛ لأن بوابة تماثل النسختين ترفض النص العربي المرئي
        كله. كان الحدّ السابق (>2) يسمح ببقاء كلمات مثل «في» و«و» فتوقف النشر.
        """
        if not ARABIC.search(norm(translated)):
            # ك-592: الترجمة التي تُسقط رقمًا من الأصل تُعدّ فشلًا لا نجاحًا؛
            # الاقتطاع الصامت كان يمرّ لأن الفحص كان يبحث عن العربية المتبقية فقط،
            # فتفلت جملة فقدت تاريخًا («29 سبتمبر») ويُبنى مخرج ناقص بلا منع.
            _od = _numeric_tokens(orig)
            _td = _numeric_tokens(translated)
            _pool = list(_td)
            for _d in _od:
                if _d in _pool:
                    _pool.remove(_d)
                else:
                    return False
            return True
        try:
            alt = localize_patterns(orig)
        except Exception:
            alt = None
        if not alt:
            return False
        return not ARABIC.search(norm(alt))

    out = _collapse_inline_source_duplicates(out)
    out = _fix_chrome(out)
    out = _apply_governed_event_card_labels(out, gl)
    out = _apply_card_row_labels(out)
    out = normalize_document_head(out)
    # ك-599: وسم رموز الدرجات بلغة السطح، فلا يظهر رمز داخلي في النسخة الإنجليزية.
    out = reader_grade_labels.redact(out, "en")
    remaining = [
        text for index, (text, translated) in enumerate(zip(c.units, units))
        if index not in ltr_covered
        and not _unit_ok(text, translated)
    ]
    remaining.extend(
        source for _, _, source in ltr_unmatched
        if not _unit_ok(source, source)
    )
    remaining.extend(
        source for source, translated in ltr_checks
        if not _unit_ok(source, translated)
    )
    return out, [norm(x) for x in remaining], len(c.units)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--src", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    src = pathlib.Path(a.src) if a.src else ROOT / "dist" / "reports" / f"{a.date}.html"
    if not src.exists():
        print(f"تعذّر: صفحة الإصدار العربية غير موجودة: {src}")
        return 2
    tm, gl = build_tm(a.date), load_glossary()
    page, missing, total = translate_page(src.read_text(encoding="utf-8"), a.date, tm, gl)
    print(f"   ذاكرة الترجمة: {len(tm)} · المعجم: {len(gl)} · عقود النصوص: {total}")
    uniq = sorted(set(missing))
    if uniq:
        print(f"   ✘ نصوص عربية بلا ترجمة: {len(uniq)}")
        for s in uniq:
            print(f"      · {s[:120]}")
    else:
        print("   ✔ لا نص عربي متبقٍّ في الصفحة المترجمة")
    if a.out:
        # ك-جديد: تطبيع ترويسة المستند الإنجليزي — doctype ثم وسم html بصفاته
        if '<html' in page:
            _m = re.search(r'<html([^>]*)>', page)
            _a = _m.group(1)
            for _k, _v in (('lang', 'en'), ('dir', 'ltr')):
                _a = re.sub(rf'{_k}="[^"]*"', f'{_k}="{_v}"', _a) if f'{_k}=' in _a else _a + f' {_k}="{_v}"'
            if 'data-lang=' not in _a:
                _a += ' data-lang="en"'
            page = page[:_m.start()] + '<html' + _a + '>' + page[_m.end():]
        page = re.sub(r'^(?:\ufeff)?\s*(?:<!doctype[^>]*>)?\s*', '<!DOCTYPE html>\n', page, count=1, flags=re.I)
        pathlib.Path(a.out).write_text(page, encoding="utf-8")
        print(f"   ✔ كُتب {a.out}")
    return 0 if not uniq else 1


if __name__ == "__main__":
    sys.exit(main())
