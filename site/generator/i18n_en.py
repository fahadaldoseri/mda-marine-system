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
BRAIN = _root("BRAIN_DIR", _HOME, "brain-marine-news", "brain")
AR_MD = BRAIN / "reports"
I18N = ROOT / "sources" / "i18n" / "en"
SKIP_TAGS = {"script", "style", "code"}
TR_ATTRS = ("title", "aria-label", "alt", "placeholder", "data-label", "data-goto", "data-alt")
ARABIC = re.compile(r"[\u0600-\u06FF]")
# معرف تحذير UKMTO/NAVAREA بصيغة رقم-سنة؛ لا يجوز إدخاله من مفتاح جزئي.
ADVISORY_ID = re.compile(r"(?<![\d-])\d{3}-\d{2}(?![\d-])")
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
    return not key_ids or key_ids.issubset(text_ids)


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


def build_tm(date: str) -> dict[str, str]:
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
        j = blk.find("{", blk.find(f'"{tag}"'))
        if j < 0:
            return {}
        k = blk.find("}", j)
        try:
            return json.loads(blk[j : k + 1])
        except Exception:
            return {}
    ar_obj, en_obj = obj("ar"), obj("en")
    return {norm(k): v for k, v in ar_obj.items() if isinstance(v, str) and v.strip() and en_obj.get(k)}


def load_glossary() -> dict[str, str]:
    p = I18N / "glossary.json"
    gl: dict[str, str] = {}
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        gl = {norm(k): v for k, v in (d.get("entries") or {}).items()}
    gl.update(chrome_glossary())
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


_PLACE_EN = {"لما": "Lima"}


def localize_patterns(s: str) -> str | None:
    n = norm(s)
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

    def _tr_area(v: str) -> str:
        """يترجم اسم منطقة، أو «موقع - منطقة»، أو سردًا مفصولًا بـ«·»."""
        t = (v or "").strip()
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
            area = _tr_area(m.group("area"))
            if place and not ARABIC.search(area):
                return f"{place}, Oman - {area}"
        return _tr_area(t)

    def _tr(v: str) -> str:
        hit = (_G or {}).get(norm(v))
        if hit:
            return hit
        area = _tr_area(v)
        return area if area != v else v

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
    m = re.fullmatch(r"الواقعة\s+(\S+)\s+—\s+المنطقة\s+(.+?)،\s+الصفة\s+(.+?)،\s+"
                     r"الإثبات\s+(.+?)،\s+الموقع\s+(.+?)\.", n)
    if m:
        return (f"Event {m.group(1)} — area {_area_full(m.group(2))}, "
                f"class {_tr(m.group(3))}, confirmation {_tr(m.group(4))}, "
                f"location {_tr(m.group(5))}.")
    # ك-471: جملة مجمّعة لوقائع متشابهة في المنطقة والصفة والإثبات ودقة الموضع؛
    # تُحفظ كل المعرّفات ويُترجَم النص بنمط واحد بلا اعتماد على المعجم.
    m = re.fullmatch(r"الوقائع\s+((?:\S+\s*·\s*)+\S+)\s+—\s+المنطقة\s+(.+?)،\s+الصفة\s+(.+?)،\s+"
                     r"الإثبات\s+(.+?)،\s+الموقع\s+(.+?)\.", n)
    if m:
        ids = ", ".join(x.strip() for x in m.group(1).split("·") if x.strip())
        return (f"Events {ids} — area {_area_full(m.group(2))}, class {_tr(m.group(3))}, "
                f"confirmation {_tr(m.group(4))}, location {_tr(m.group(5))}.")
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
        tail = ("some of them placed approximately within the same area because the source gave no "
                "coordinates." if m.group(2).startswith("منها") else
                "all of them with coordinates stated in the sources.")
        return f"Positions of {m.group(1)} incidents within the report scope; {tail}"
    _zl = _zone_level_en(n)
    if _zl is not None:
        return _zl
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
        area = _tr_area(m.group("area"))
        kind = _KIND.get(m.group("kind").strip())
        conf = _CONF.get(m.group("conf").strip())
        loc = _LOC.get(m.group("loc").strip())
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
        area = _tr_area(m.group("area"))
        if not re.search(ARABIC, area):
            return f"{m.group('place')}, Oman - {area}"
    m = re.fullmatch(r"بصيغة مختصرة لا يذكر اسم السفينة ولا الضرر", n)
    if m:
        return "in a brief form that names neither the vessel nor the damage"
    m = COUNTER.match(n)
    if m:
        return f"{m.group(1)} {COUNT_WORD[m.group(2)]}" + (f" {m.group(3)}" if m.group(3) else "")
    return None


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.skip = 0
        self.units: list[str] = []
        self.unit_contexts: list[str | None] = []
        self.parts: list[str] = []
        self.attrs_seen: list[str] = []
        self.in_tz_count = False

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
        self.parts.append(f"<{tag}{self._attr(attrs)}>")

    def handle_startendtag(self, tag, attrs):
        self.parts.append(f"<{tag}{self._attr(attrs)}/>")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1
        if tag == "p" and self.in_tz_count:
            self.in_tz_count = False
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self.skip:
            self.parts.append(data)
            return
        self.parts.append("\u0000")
        self.units.append(data)
        self.unit_contexts.append("tz-count" if self.in_tz_count else None)

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")


def _counter_registry_path() -> pathlib.Path:
    candidates = []
    if os.environ.get("BRAIN_DIR"):
        candidates.append(pathlib.Path(os.environ["BRAIN_DIR"]) / "appendices" / "card_registry.json")
    candidates.extend([
        ROOT.parent / "brain" / "appendices" / "card_registry.json",
        _HOME / "brain-marine-news" / "appendices" / "card_registry.json",
    ])
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
    keys = sorted(set(tm) | set(gl), key=len, reverse=True)

    def _val(k: str) -> str:
        """قيمة الترجمة لمفتاح، والمعجم المعتمد يسبق ذاكرة الترجمة الناقصة.

        العلّة (ك-447): ذاكرة الترجمة تُبنى بمحاذاة أسطر المتن، فإذا انحرفت أسطر
        الجدول أنتجت قيمةً إنجليزية تحمل كلمة عربية متبقية (مثل «في»)، وكانت
        تُقدَّم على المعجم المعتمد فيبقى نص عربي مرئي في النسخة الإنجليزية.
        القاعدة الآن: أي قيمة في ذاكرة الترجمة تحتوي حرفًا عربيًا لا تُقدَّم على
        قيمة المعجم؛ فإن لم يوجد مدخل معجم تُستعمل كما هي للعلم والإصلاح.
        """
        tv = tm.get(k)
        if tv and not ARABIC.search(tv):
            return tv
        gv = gl.get(k)
        if gv:
            return gv
        return tv or ""

    def lookup(t: str) -> str | None:
        if t in tm or t in gl:
            return _val(t)
        pat = localize_patterns(t)
        if pat:
            return pat
        # معرفات التحذير حساسة للهوية: لا تُقبل المطابقة الجزئية إلا إذا كانت
        # كل معرفات المفتاح موجودة حرفيًا في العقدة نفسها؛ فلا يتسرّب 186-26
        # إلى عقدة ev-01 التي لا تحمل إلا موقعها.
        starts = [k for k in keys if k.startswith(t) and _partial_key_safe(t, k)
                  and not norm(t).endswith(("·", "…"))]
        if starts:
            k = min(starts, key=len)
            return _val(k)
        within = [k for k in keys if t.startswith(k) and _partial_key_safe(t, k)
                  and not ADVISORY_ID.search(t)]
        if within:
            k = max(within, key=len)
            return _val(k)
        return None

    def translate(u: str) -> str:
        n = norm(u)
        if not n or not ARABIC.search(n):
            return u
        # قوائم الأسماء اللاتينية المتصلة بحرف العطف العربي «و» (مثل: Mehr وISNA)
        # ليست نصًّا عربيًا يحتاج معجمًا، بل يجب أن تُوصل بـ«and»؛ فيبقى الاسم
        # اللاتيني كما هو ولا يبقى حرف عربي مرئي في الصفحة الإنجليزية (ك-447).
        if set(ARABIC.findall(n)) == {"و"}:
            fixed = re.sub(r"(?<=[A-Za-z0-9]) و(?=[A-Za-z0-9])", " and ", u)
            fixed = re.sub(r"^\s*و(?=[A-Za-z0-9])", "and ", fixed)
            dual = re.sub(r"(?<=[A-Za-z0-9]) و(?=[A-Za-z0-9])", " and ", fixed)
            if not ARABIC.search(dual):
                return dual
        direct = lookup(n)
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
            hit = lookup(p)
            if hit is None:
                ok = False
                break
            res = res.replace(part, part.replace(p, hit))
        if ok:
            return res
        for k in keys:
            if k in res:
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
                hit = lookup(pn)
                if hit is None:
                    cand = [k for k in keys if k and k in pn]
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

    previous = None
    while previous != out:
        previous, out = out, pattern.sub(replace, out)
    return out


def translate_page(html_text: str, date: str, tm: dict[str, str], gl: dict[str, str]):
    tr = make_translator(tm, gl)
    c = _Collector()
    c.feed(html_text)
    counter_labels = _sector_counter_labels()
    units = [(_translate_counter_fragment(t, counter_labels)
              if c.unit_contexts[i] == "tz-count" else tr(t))
             for i, t in enumerate(c.units)]
    attrs = [tr(a) for a in c.attrs_seen]
    parts, k = [], 0
    for p in c.parts:
        if p == "\u0000":
            parts.append(units[k]); k += 1
        else:
            for i, a in enumerate(attrs):
                p = p.replace(f'__ATTR{i}__', a)
            parts.append(p)
    out = "".join(parts)
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
            return True
        try:
            alt = localize_patterns(orig)
        except Exception:
            alt = None
        if not alt:
            return False
        return not ARABIC.search(norm(alt))

    remaining = [t for t, translated in zip(c.units, units) if not _unit_ok(t, translated)]
    out = _collapse_inline_source_duplicates(out)
    out = _fix_chrome(out)
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
        for s in uniq[:60]:
            print(f"      · {s[:120]}")
    else:
        print("   ✔ لا نص عربي متبقٍّ في الصفحة المترجمة")
    if a.out:
        pathlib.Path(a.out).write_text(page, encoding="utf-8")
        print(f"   ✔ كُتب {a.out}")
    return 0 if not uniq else 1


if __name__ == "__main__":
    sys.exit(main())
