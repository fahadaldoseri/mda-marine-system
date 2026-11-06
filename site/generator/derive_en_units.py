#!/usr/bin/env python3
"""اشتقاق الوحدات الإنجليزية من المتن الإنجليزي الحاكم وتسجيلها في المعجم.

المبدأ الجديد (2026-11-03): النسخة الإنجليزية هي **الأصل**، والمتن الإنجليزي
`sources/i18n/en/<DATE>-sectioned.en.md` هو مصدر النص الإنجليزي. فعندما تبقى
وحدة عربية في الصفحة المترجمة، لا يُترجمها النموذج ولا تُخمَّن، بل تُشتق من
مقابلها في المتن الإنجليزي بمحاذاة الجُمل، ثم تُقيَّد في المعجم الحاكم.

الاستعمال:
    python3 generator/derive_en_units.py --date 2026-11-02            # فحص
    python3 generator/derive_en_units.py --date 2026-11-02 --apply    # كتابة
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys
from difflib import SequenceMatcher
from datetime import date as _date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import i18n_en  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
AR_MD = ROOT.parent / "brain-marine-news" / "reports"
I18N = ROOT / "sources" / "i18n" / "en"
MANIFEST = ROOT.parent / "brain-marine-news" / "runbook" / "runbook.json"


def i18n_policy() -> dict[str, str]:
    """اقرأ سياسة اتجاه اللغة من المانيفست، ولا تسمح بمسار اتجاه ضمني.

    قبل ``i18n.since`` كانت العربية هي الأصل التحريري؛ ومن ذلك التاريخ أصبحت
    الإنجليزية هي الأصل. لا يغيّر هذا الحارس سياسة بناء يوم لاحق، بل يحدد فقط
    اتجاه السجل الذي يُكتب لكل اشتقاق، حتى لا تختلط الوحدات التاريخية بوحدات
    الإضافات المبنية من أحدث إصدار.
    """
    if not MANIFEST.is_file():
        raise SystemExit(f"سياسة i18n مفقودة: {MANIFEST}")
    try:
        raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
        policy = raw.get("i18n") or {}
        master = str(policy.get("master") or "")
        since = str(policy.get("since") or "")
        _date.fromisoformat(since)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"سياسة i18n غير صالحة: {MANIFEST}: {exc}") from exc
    if master != "en":
        raise SystemExit(f"اتجاه i18n غير مدعوم للاشتقاق: master={master!r}")
    return {"master": master, "since": since}


def direction_for(source_date: str) -> dict[str, str]:
    """Return the audited master/rendered direction for one source edition."""
    policy = i18n_policy()
    before_cutover = _date.fromisoformat(source_date) < _date.fromisoformat(policy["since"])
    if before_cutover:
        return {
            "master": "ar",
            "rendered": "en",
            "policy": f"pre_since_ar_master<{policy['since']}",
        }
    return {
        "master": "en",
        "rendered": "ar",
        "policy": f"since_en_master>={policy['since']}",
    }


def latest_source_date() -> str:
    report_root = ROOT / "sources" / "reports"
    ar_dates = {
        p.name.split("-sectioned")[0]
        for p in report_root.glob("*-sectioned.md")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name.split("-sectioned")[0])
    }
    dates = sorted(
        p.name.split("-sectioned")[0]
        for p in I18N.glob("*-sectioned.en.md")
        if p.name.split("-sectioned")[0] in ar_dates
    )
    if not dates:
        raise SystemExit("لا يوجد متن إنجليزي قابل للمحاذاة")
    return dates[-1]


def sentences(s: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.؟!؛])\s+|\s+·\s+", s) if p.strip()]


def sentences_loose(s: str) -> list[str]:
    """تفكيك موسّع: يعامل «؛» و«;» فاصلًا واحدًا حتى تتساوى الجملتان العربية والإنجليزية."""
    return [p.strip() for p in re.split(r"(?<=[.؟!؛;])\s+|\s+·\s+", s) if p.strip()]


def pair_sentences(a: str, e: str):
    """جمل السطرين: التفكيك القياسي أولًا، ثم الموسّع عند اختلاف العدد (بلا تغيير المسار الناجح)."""
    sa, se = sentences(a), sentences(e)
    if sa and se and len(sa) == len(se):
        return sa, se
    sa2, se2 = sentences_loose(a), sentences_loose(e)
    if sa2 and se2 and len(sa2) == len(se2):
        return sa2, se2
    return [], []


def words(s: str) -> list[str]:
    return [w for w in re.split(r"\s+", s.strip()) if w]


def build_pairs(date: str):
    ar = (AR_MD / f"{date}-sectioned.md").read_text(encoding="utf-8").splitlines()
    en = (I18N / f"{date}-sectioned.en.md").read_text(encoding="utf-8").splitlines()
    A = [x for x in ar if x.strip()]
    E = [x for x in en if x.strip()]
    if len(A) != len(E):
        raise SystemExit(f"محاذاة غير ممكنة: عربي={len(A)} إنجليزي={len(E)}")
    return list(zip(A, E))


def build_pairs_history(date: str, back: int = 14):
    """أزواج اليوم المطلوب + أزواج الأيام السابقة.

    الأسطح المنشورة (صفحة الإضافات والرئيسية والأرشيف) تعرض نصوصًا من أيام
    سابقة. فإذا بقيت وحدة منها بلا ترجمة، تُشتقّ من متن يومها نفسه بدل أن
    تفشل الحزمة أو تُترجم تخمينًا. (ك-478: تجميد الاشتقاق على يوم واحد.)
    """
    import datetime as _dt
    d0 = _dt.date.fromisoformat(date)
    pairs: list[tuple[str, str]] = []
    for k in range(back + 1):
        d = (d0 - _dt.timedelta(days=k)).isoformat()
        try:
            pairs.extend(build_pairs(d))
        except SystemExit:
            continue
        except FileNotFoundError:
            continue
    if not pairs:
        raise SystemExit("محاذاة غير ممكنة: لا يوم قابل للمحاذاة")
    return pairs


# EVENT_ID_NORMALIZATION_V1: identifiers are normalized before alignment.
# Source of truth: the governing paired body lines, whose canonical incident
# key is MN-YYYY-MM-DD-NN. Short MM-DD, DD-MM, MN-DD-NN, and bare DD-NN forms
# are aliases only when they resolve uniquely to that full key; parentheses,
# dash variants, and Arabic-Indic digits are ignored for this lookup. This is
# intentionally date-agnostic: the current report date is only a fallback when
# the governing pairs do not themselves expose a full incident key.
_ID_DASHES = "‐‑‒–—−﹘﹣－"


def _build_arabic_digits() -> dict[int, int]:
    """ابنِ خريطة الأرقام العربية والهندية-الفارسية بلا قيمة نصية طويلة."""
    return str.maketrans(
        "".join(chr(0x0660 + i) for i in range(10))
        + "".join(chr(0x06F0 + i) for i in range(10)),
        "0123456789" * 2,
    )


_ARABIC_DIGITS = _build_arabic_digits()
_ID_SEP = rf"[-{re.escape(_ID_DASHES)}]"
_IDENTIFIER_RE = re.compile(
    rf"(?<![A-Za-z0-9])(?:MN{_ID_SEP}\d{{4}}{_ID_SEP}\d{{2}}{_ID_SEP}\d{{2}}{_ID_SEP}\d{{2}}|MN{_ID_SEP}\d{{2}}{_ID_SEP}\d{{2}}|\d{{2}}{_ID_SEP}\d{{2}})(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_FULL_INCIDENT_RE = re.compile(
    rf"^MN{_ID_SEP}(\d{{4}}){_ID_SEP}(\d{{2}}){_ID_SEP}(\d{{2}}){_ID_SEP}(\d{{2}})$",
    re.IGNORECASE,
)

TOKEN_RE = re.compile(r"\d[\d.,:/–\-]*[A-Za-z]{0,3}|\b[A-Z]{2,}\b|[A-Za-z]{2,}-\d+|\d+-\d+")


def _canonical_identifier_text(text: str) -> str:
    """وحّد الأرقام في نسخة المطابقة، واترك شرطات النص خارج المعرّف كما هي."""
    return (text or "").translate(_ARABIC_DIGITS)


def _canonical_identifier_token(token: str) -> str:
    """حوّل معرّفًا ملتقطًا إلى شرطة ASCII وحروف لاتينية موحّدة."""
    return token.translate(str.maketrans({dash: "-" for dash in _ID_DASHES})).upper()


def _full_incident_ids(text: str) -> set[str]:
    """استخرج مفاتيح الوقائع الكاملة من سطر متن أو وحدة."""
    value = _canonical_identifier_text(text)
    return {
        _canonical_identifier_token(match.group(0))
        for match in _IDENTIFIER_RE.finditer(value)
        if _FULL_INCIDENT_RE.fullmatch(match.group(0))
    }


def _incident_aliases(full_id: str) -> set[str]:
    """أعد صيغ الاختصار الآمنة لمفتاح واقعة كامل واحد."""
    match = _FULL_INCIDENT_RE.fullmatch(full_id)
    if not match:
        return set()
    _, month, day, sequence = match.groups()
    # Keep both date orders and the project's day-sequence shorthand. Ambiguous
    # aliases are discarded by _incident_alias_map instead of being guessed.
    return {
        full_id.upper(),
        f"MN-{day}-{sequence}",
        f"{month}-{day}",
        f"{day}-{month}",
        f"{day}-{sequence}",
        f"{sequence}-{day}",
        f"{month}-{sequence}",
        f"{sequence}-{month}",
    }


def _incident_alias_map(pairs, source_date: str | None = None) -> dict[str, str]:
    """Map unique short identifiers to full keys found in governing pairs."""
    full_ids: set[str] = set()
    for arabic, english in pairs:
        full_ids.update(_full_incident_ids(arabic))
        full_ids.update(_full_incident_ids(english))
    aliases: dict[str, set[str]] = {}
    for full_id in full_ids:
        for alias in _incident_aliases(full_id):
            aliases.setdefault(alias.upper(), set()).add(full_id)

    # Short day-sequence aliases are meaningful for the requested edition. If
    # the history window contains the same shorthand on another day, prefer
    # the full key from this source date instead of guessing across editions.
    if source_date:
        try:
            source = _date.fromisoformat(source_date)
        except ValueError:
            source = None
        if source:
            scoped = {
                full_id
                for full_id in full_ids
                if _FULL_INCIDENT_RE.fullmatch(full_id)
                and full_id.split("-")[1:4]
                == [f"{source.year:04d}", f"{source.month:02d}", f"{source.day:02d}"]
            }
            for alias, values in list(aliases.items()):
                scoped_values = values & scoped
                if scoped_values:
                    aliases[alias] = scoped_values

    # A source date is a bounded fallback for the observed MN-DD-NN / DD-NN
    # form when a caller supplies a pair set without its full incident key.
    if source_date:
        try:
            source = _date.fromisoformat(source_date)
        except ValueError:
            source = None
        if source:
            day = f"{source.day:02d}"
            for sequence in range(1, 100):
                full_id = f"MN-{source.year:04d}-{source.month:02d}-{source.day:02d}-{sequence:02d}"
                for alias in (f"MN-{day}-{sequence:02d}", f"{day}-{sequence:02d}"):
                    aliases.setdefault(alias, set()).add(full_id)
    return {alias: next(iter(values)) for alias, values in aliases.items() if len(values) == 1}


def _normalize_incident_identifiers(
    text: str,
    aliases: dict[str, str],
    source_date: str | None = None,
) -> str:
    """استبدل الاختصار بالمعرّف الكامل في نسخة المطابقة فقط."""
    value = _canonical_identifier_text(text)

    def replace(match: re.Match[str]) -> str:
        token = _canonical_identifier_token(match.group(0)).strip("()[]{}")
        return aliases.get(token, token)

    return _IDENTIFIER_RE.sub(replace, value)


def tokens(s: str) -> set[str]:
    """الرموز القابلة للتحقق: الأرقام والمعرّفات وأسماء الجهات اللاتينية."""
    out = set()
    for t in TOKEN_RE.findall(s):
        t = t.strip().lower()
        if not t:
            continue
        digits = re.sub(r"[^\d]", "", t)
        out.add(digits if digits else t)
    return {x for x in out if x}


def verified(unit_ar: str, en: str) -> bool:
    """لا يُقبل اشتقاق يخالف أرقام الوحدة أو معرّفاتها (فشل مغلق)."""
    tu, te = tokens(unit_ar), tokens(en)
    if not tu:
        return bool(te) or bool(en.strip())
    missing = {x for x in tu if x not in te}
    # تُقبل الزيادة الطفيفة في أرقام الجملة الإنجليزية، ولا يُقبل نقص رقم عربي
    return not missing


def _table_cells(line: str) -> list[str]:
    """أعد خلايا صف Markdown بلا فواصل الجدول الخارجية."""
    raw = line.strip()
    if not raw.startswith("|"):
        return []
    parts = raw.split("|")
    if len(parts) < 3:
        return []
    return [i18n_en.norm(cell) for cell in parts[1:-1]]


def _derive_table_cell(unit: str, arabic_line: str, english_line: str) -> str | None:
    """اشتق وحدة HTML التي تمثل خلية واحدة من صف Markdown المناظر."""
    ar_cells, en_cells = _table_cells(arabic_line), _table_cells(english_line)
    nu = i18n_en.norm(unit)
    if not nu or len(ar_cells) != len(en_cells):
        return None
    for idx, ar_cell in enumerate(ar_cells):
        if nu != ar_cell:
            continue
        result = en_cells[idx].strip()
        if result and not i18n_en.ARABIC.search(result) and verified(unit, result):
            return result
    return None


def _derive_table_cell_fuzzy(unit: str, arabic_line: str, english_line: str) -> str | None:
    """اشتق خلية أُعيد ترتيبها بصريًا، مثل «شمال ... - الخليج العربي»."""
    ar_cells, en_cells = _table_cells(arabic_line), _table_cells(english_line)
    nu = i18n_en.norm(unit)
    if not nu or len(ar_cells) != len(en_cells):
        return None
    unit_geo = _geo_anchor_keys(unit)
    for ar_cell, en_cell in zip(ar_cells, en_cells):
        if not ar_cell or not en_cell:
            continue
        ratio = SequenceMatcher(None, nu, ar_cell).ratio()
        if ratio < 0.55 or not unit_geo.intersection(_geo_anchor_keys(ar_cell)):
            continue
        if not i18n_en.ARABIC.search(en_cell) and verified(unit, en_cell):
            return en_cell.strip()
    return None


def _token_key(token: str) -> str:
    """طبّع رمزًا مشتركًا للمطابقة الآمنة بين اللغتين."""
    value = token.strip().lower()
    digits = re.sub(r"[^\d]", "", value)
    return digits if digits else value


def _derive_prefix_before_shared_token(unit: str, arabic_line: str, english_line: str) -> str | None:
    """اشتق بادئة نصية مقطوعة قبل مرساة لاتينية مشتركة مثل UKMTO أو IMO."""
    nu = i18n_en.norm(unit)
    na = i18n_en.norm(arabic_line)
    ne = i18n_en.norm(english_line)
    if not nu or nu == na or not na.startswith(nu):
        return None
    rest = na[len(nu):]
    if rest and not rest[0].isspace() and rest[0] not in "،؛,.!?ـ-|":
        return None
    en_tokens = list(TOKEN_RE.finditer(ne))
    for ar_token in TOKEN_RE.finditer(rest):
        key = _token_key(ar_token.group())
        for en_token in en_tokens:
            if _token_key(en_token.group()) != key:
                continue
            result = ne[:en_token.start()].rstrip(" \t،؛,.!?|-—")
            if result and not i18n_en.ARABIC.search(result) and verified(unit, result):
                return result
    return None


_GEO_ANCHORS = {
    "مضيق هرمز": "strait of hormuz",
    "خليج عُمان": "gulf of oman",
    "خليج عمان": "gulf of oman",
    "الخليج العربي": "arabian gulf",
    "بحر العرب": "arabian sea",
    "البحر الأحمر": "red sea",
    "باب المندب": "bab al-mandab",
    "خليج عدن": "gulf of aden",
    "مدينة الشمال": "madinat ash shamal",
}


def _geo_anchor_keys(text: str) -> set[str]:
    """أعد مراسي جغرافية ثابتة؛ لا تُستخدم إلا لاختيار السطر الحاكم."""
    value = i18n_en.norm(text).lower()
    return {
        f"geo:{english}"
        for arabic, english in _GEO_ANCHORS.items()
        if arabic in value
    }


def _anchor_matches(arabic: str, english: str) -> list[tuple[str, int, int, int, int]]:
    """طابق المراسي الرقمية/اللاتينية بحسب ترتيب ظهورها في السطرين."""
    a_tokens = [(m, _token_key(m.group())) for m in TOKEN_RE.finditer(arabic)]
    e_tokens = [(m, _token_key(m.group())) for m in TOKEN_RE.finditer(english)]
    out: list[tuple[str, int, int, int, int]] = []
    used: set[int] = set()
    for a_idx, (a_match, key) in enumerate(a_tokens):
        for e_idx, (e_match, e_key) in enumerate(e_tokens):
            if e_idx in used or key != e_key:
                continue
            out.append((key, a_match.start(), a_match.end(), e_match.start(), e_match.end()))
            used.add(e_idx)
            break
    return out


def _word_start_before(text: str, position: int, count: int) -> int:
    """أعد بداية ``count`` كلمات قبل موضع المرساة الإنجليزية."""
    if count <= 0:
        return position
    prefix = text[:position]
    matches = list(re.finditer(r"[A-Za-z0-9][A-Za-z0-9'/-]*", prefix))
    if not matches:
        return position
    return matches[max(0, len(matches) - count)].start()


def _next_english_delimiter(text: str, position: int, arabic_delimiter: str) -> int | None:
    """ابحث عن أول فاصلة إنجليزية تمثل فاصلة عربية بعد المرساة."""
    delimiter = ";" if arabic_delimiter in "؛;" else arabic_delimiter
    if delimiter not in ".;!?":
        return None
    found = text.find(delimiter, position)
    return found if found >= 0 else None


def _derive_fragment_from_line(unit: str, arabic_line: str, english_line: str) -> str | None:
    """اشتق شريحة عقدة HTML من سطر حاكم عند مرساة مشتركة.

    العقدة قد تبدأ داخل الجملة بعد ``<span class="ltr">`` أو تنتهي قبل وسم
    تالٍ. لا نترجم النص؛ نحدد موضع المرساة في العربية والإنجليزية ونقتطع من
    السطر الإنجليزي نفسه. وإذا انقطعت الوحدة قبل المرساة، تُحفظ الكلمات
    الإنجليزية السابقة للمرساة بعدد كلمات البادئة العربية في العقدة.
    """
    nu = i18n_en.norm(unit)
    na = i18n_en.plain(arabic_line)
    ne = i18n_en.plain(english_line)
    if not nu or not na or not ne:
        return None

    start = na.find(nu)
    end = start + len(nu) if start >= 0 else -1
    # بعض العقد تُغلق بنقطة بعد اقتطاع الفاصلة الحاكمة؛ جرّب النص بلا
    # علامة الوقف فقط، مع بقاء الكلمات نفسها مصدر المطابقة.
    if start < 0:
        bare = nu.rstrip(".!؟؛")
        if bare:
            start = na.find(bare)
            end = start + len(bare) if start >= 0 else -1
    matches = _anchor_matches(na, ne)
    if start < 0 or end <= start:
        # لا نُسقط السطر بلا مرساة في الوحدة؛ هذا يمنع التخمين عند تشابه
        # الجمل، ويترك حالات النص المتحرك لمسار المعجم/النمط الحاكم.
        unit_keys = _geo_anchor_keys(unit)
        if not unit_keys:
            return None
        ar_geo = _geo_anchor_keys(na)
        en_geo = _geo_anchor_keys(ne)
        if not unit_keys.issubset(ar_geo) or not unit_keys.issubset(en_geo):
            return None
        if not verified(unit, ne):
            return None
        return ne

    inside = [m for m in matches if start <= m[1] < end]
    if inside:
        first = inside[0]
        last = inside[-1]
        # كلمات عربية قبل أول مرساة داخل العقدة تقابل الكلمات الإنجليزية
        # السابقة لها في السطر الحاكم (بلاغ → report، رقم → No./report).
        prefix_words = len(words(na[start:first[1]]))
        e_start = _word_start_before(ne, first[3], prefix_words)
        e_end = len(ne)
        tail = na[last[2]:end]
        terminal = tail.rstrip()[-1:] if tail.strip() else ""
        if terminal in ".!?؟؛;":
            delimiter = ";" if terminal in "؛;" else terminal
            found = ne.find(delimiter, last[4])
            if found >= 0:
                e_end = found + 1
        elif end < len(na):
            # عند وجود مرساة/فاصل تالٍ في السطر، لا نبتلع ما بعد العقدة.
            next_match = next((m for m in matches if m[1] >= end), None)
            if next_match:
                e_end = next_match[3]
        result = ne[e_start:e_end].strip(" \t،,؛;(|-—")
        if result and not i18n_en.ARABIC.search(result) and verified(unit, result):
            return result
        return None

    # الوحدة لاحقة لمرساة داخلية مثل «؛ التفاصيل غير متاحة» أو «؛ الحالة: قائم».
    before = [m for m in matches if m[1] < start]
    after = [m for m in matches if m[1] >= end]
    if not before:
        return None
    anchor = before[-1]
    prev_text = na[anchor[2]:start]
    delimiters = list(re.finditer(r"[؛;.!؟]", prev_text))
    if delimiters:
        d = _next_english_delimiter(ne, anchor[4], delimiters[-1].group())
        e_start = d + 1 if d is not None else anchor[4]
    else:
        e_start = anchor[4]
    e_end = len(ne)
    if after:
        e_end = after[0][3]
    elif nu.rstrip().endswith((".", "!", "؟")):
        terminal = "." if nu.rstrip().endswith(".") else nu.rstrip()[-1]
        d = ne.find(terminal, e_start)
        if d >= 0:
            e_end = d + 1
    result = ne[e_start:e_end].strip(" \t،,؛;(|-—")
    if result and not i18n_en.ARABIC.search(result) and verified(unit, result):
        return result
    return None


def _derive_by_anchor_line(unit: str, pairs) -> str | None:
    """اشتق وحدة لا تظهر حرفيًا بسبب إعادة تركيب بطاقة/وسم، بمرساة قوية فقط."""
    counter = re.fullmatch(r"و(\d+) بنود أخرى في قسم «التوصيات»\.", i18n_en.norm(unit))
    if counter:
        return f"and {counter.group(1)} further items in the Recommendations section."
    keys = _geo_anchor_keys(unit)
    keys.update(_token_key(m.group()) for m in TOKEN_RE.finditer(unit))
    candidates: list[tuple[int, float, str]] = []
    for a, e in pairs:
        na, ne = i18n_en.plain(a), i18n_en.plain(e)
        shared = keys & (_geo_anchor_keys(na) | _geo_anchor_keys(ne))
        shared.update(
            _token_key(m.group())
            for m in TOKEN_RE.finditer(unit)
            if _token_key(m.group()) in {_token_key(x.group()) for x in TOKEN_RE.finditer(ne)}
        )
        ar_segments = sentences_loose(na) or [na]
        en_segments = sentences_loose(ne) or [ne]
        if len(ar_segments) == len(en_segments):
            segment_pairs = list(zip(ar_segments, en_segments))
        else:
            segment_pairs = [(na, ne)]
        for ar_segment, en_segment in segment_pairs:
            ratio = SequenceMatcher(None, i18n_en.norm(unit), ar_segment).ratio()
            if not shared and ratio < 0.42:
                continue
            if not verified(unit, en_segment):
                continue
            # المرساة الرقمية/الجغرافية تتقدم على التشابه النصي، والتشابه
            # يفك التعادل بين «خليج عُمان · مضيق هرمز» والعبارة المرتبة.
            score = len(shared) * 100
            candidates.append((score, ratio, en_segment))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, best_ratio, best_text = candidates[0]
    if i18n_en.ARABIC.search(best_text):
        return None
    if best_score == 0 and best_ratio < 0.55:
        return None
    return best_text


class _ContextCollector(i18n_en.HTMLParser):
    """اجمع النص المرئي لكل كتلة حاوية لعقدة HTML مقطوعة."""

    _BLOCKS = {"h1", "h2", "h3", "h4", "li", "p", "td", "th", "summary"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.blocks: list[dict[str, list[str]]] = []
        self.contexts: dict[str, set[str]] = {}

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "code"}:
            self.skip += 1
        if not self.skip and tag in self._BLOCKS:
            self.blocks.append({"parts": [], "units": []})

    def handle_endtag(self, tag):
        if not self.skip and tag in self._BLOCKS and self.blocks:
            block = self.blocks.pop()
            context = i18n_en.norm(" ".join(block["parts"]))
            if context:
                for unit in block["units"]:
                    key = i18n_en.norm(unit)
                    if key:
                        self.contexts.setdefault(key, set()).add(context)
        if tag in {"script", "style", "code"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if self.skip or not self.blocks:
            return
        for block in self.blocks:
            block["parts"].append(data)
        if data.strip():
            self.blocks[-1]["units"].append(data)


def html_contexts(html: str) -> dict[str, list[str]]:
    """أعد سياقات العقد النصية، مع حذف التكرار وحفظ ترتيب الظهور."""
    parser = _ContextCollector()
    parser.feed(html)
    return {key: sorted(values) for key, values in parser.contexts.items()}


def _derive_context_fragment(unit: str, context: str, pairs) -> str | None:
    """اقتطع مقابل العقدة من السطر الحاكم عبر مراسي الجيران."""
    nu = i18n_en.norm(unit)
    nc = i18n_en.norm(context)
    if not nu or not nc:
        return None
    start = nc.find(nu)
    end = start + len(nu) if start >= 0 else -1
    if start < 0:
        bare = nu.rstrip(".!؟؛")
        start = nc.find(bare) if bare else -1
        end = start + len(bare) if start >= 0 else -1
    if start < 0 or end <= start:
        return None
    context_keys = _geo_anchor_keys(nc)
    context_keys.update(_token_key(m.group()) for m in TOKEN_RE.finditer(nc))
    candidates: list[tuple[int, float, str, str, str]] = []
    for a, e in pairs:
        na, ne = i18n_en.plain(a), i18n_en.plain(e)
        pair_keys = _geo_anchor_keys(na) | _geo_anchor_keys(ne)
        pair_keys.update(_token_key(m.group()) for m in TOKEN_RE.finditer(na))
        pair_keys.update(_token_key(m.group()) for m in TOKEN_RE.finditer(ne))
        shared = context_keys & pair_keys
        if len(shared) < 2:
            continue
        ratio = SequenceMatcher(None, nc, na).ratio()
        candidates.append((len(shared), ratio, na, ne, e))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    _, _, na, ne, _ = candidates[0]
    matches = _anchor_matches(na, ne)
    left = [m for m in matches if m[2] <= start]
    right = [m for m in matches if m[1] >= end]
    if not left and not right:
        return None
    e_start = left[-1][4] if left else 0
    e_end = right[0][3] if right else len(ne)
    result = ne[e_start:e_end].strip(" \t،,؛;(|-—")
    if result and not i18n_en.ARABIC.search(result) and verified(unit, result):
        return result
    return None


def derive(
    unit: str,
    pairs,
    contexts: list[str] | None = None,
    source_date: str | None = None,
) -> str | None:
    """يشتقّ النص الإنجليزي لوحدة عربية من المتن الإنجليزي بمحاذاة الجُمل."""
    aliases = _incident_alias_map(pairs, source_date)
    unit = _normalize_incident_identifiers(unit, aliases, source_date)
    pairs = [
        (
            _normalize_incident_identifiers(arabic, aliases, source_date),
            _normalize_incident_identifiers(english, aliases, source_date),
        )
        for arabic, english in pairs
    ]
    contexts = [
        _normalize_incident_identifiers(context, aliases, source_date)
        for context in (contexts or [])
    ]
    nu = i18n_en.norm(unit)
    if not nu:
        return None
    su = sentences(unit)
    if not su:
        return None
    for context in contexts or []:
        result = _derive_context_fragment(unit, context, pairs)
        if result:
            return result
    for a, e in pairs:
        na = i18n_en.norm(a)
        fragment = _derive_fragment_from_line(unit, a, e)
        if fragment:
            return fragment
        if nu not in na:
            continue
        table_cell = _derive_table_cell(unit, a, e)
        if table_cell:
            return table_cell
        table_cell = _derive_table_cell_fuzzy(unit, a, e)
        if table_cell:
            return table_cell
        if nu == na and not a.lstrip().startswith("|"):
            result = e.strip()
            if result and not i18n_en.ARABIC.search(result) and verified(unit, result):
                return result
        prefix = _derive_prefix_before_shared_token(unit, a, e)
        if prefix:
            return prefix
        sa, se = pair_sentences(a, e)
        if not sa:
            continue
        # موضع أول جملة من الوحدة داخل جمل السطر العربي
        start = None
        for j, aj in enumerate(sa):
            naj = i18n_en.norm(aj)
            if i18n_en.norm(su[0]) and i18n_en.norm(su[0]) in naj:
                start = j
                break
            if naj.endswith(nu) or nu.endswith(naj):
                start = j
                break
        if start is None:
            continue
        # تحقّق أن بقية جمل الوحدة تقابل الجمل التالية نفسها
        for k, uk in enumerate(su[1:], start=1):
            idx = start + k
            if idx >= len(sa):
                return None
            if i18n_en.norm(uk) != i18n_en.norm(sa[idx]):
                return None
        out = list(se[start:])
        # اقتطاع الجملة الأولى إذا كانت الوحدة تبدأ من نهاية الجملة العربية
        first_ar, first_unit = sa[start], su[0]
        if i18n_en.norm(first_unit) != i18n_en.norm(first_ar):
            wa, wu, we = words(first_ar), words(first_unit), words(se[start])
            drop = max(0, len(wa) - len(wu))
            if len(we) > drop:
                out[0] = " ".join(we[drop:])
        res = " ".join(out).strip()
        if res and not i18n_en.ARABIC.search(res) and verified(unit, res):
            return res
    return _derive_by_anchor_line(unit, pairs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    src = ROOT / "dist" / "reports" / f"{a.date}.html"
    pages = [ROOT / "dist" / "reports" / f"{a.date}.html", ROOT / "dist" / "additions.html"]
    pages = [p for p in pages if p.exists()]
    if not pages:
        print(f"تعذّر: لا صفحة عربية مبنية ليوم {a.date}")
        return 2
    tm, gl = i18n_en.build_tm(a.date), i18n_en.load_glossary()
    uniq: list[str] = []
    total = 0
    for pg in pages:
        _, miss, tot = i18n_en.translate_page(pg.read_text(encoding="utf-8"), a.date, tm, gl)
        total += tot
        uniq.extend(miss)
        print(f"   {pg.name}: عقود {tot} · ناقص {len(set(miss))}")
    uniq = sorted(set(uniq))
    print(f"   عقود النصوص: {total} · وحدات بلا ترجمة: {len(uniq)}")
    if not uniq:
        print("   ✔ لا وحدة ناقصة")
        return 0

    source_specs: list[dict] = []
    for pg in pages:
        if pg.name == "additions.html":
            source_date = latest_source_date()
            # الإضافات تعرض نصوصًا من أيام سابقة أيضًا؛ فالاشتقاق يشمل اليوم و14 يومًا قبله
            pairs = build_pairs_history(source_date)
            surface = "additions"
            note = "الإضافات ← أحدث إصدار منشور + 14 يومًا سابقة"
        else:
            source_date = a.date
            pairs = build_pairs_history(a.date)
            surface = "report"
            note = "التقرير ← اليوم + 14 يومًا سابقة"
        direction = direction_for(source_date)
        source_specs.append({
            "pairs": pairs,
            "contexts": html_contexts(pg.read_text(encoding="utf-8")),
            "source_date": source_date,
            "surface": surface,
            "direction": direction,
        })
        print(
            f"   محاذاة {pg.name}: {len(pairs)} سطرًا · {note} · "
            f"الأصل {direction['master']} → المشتق {direction['rendered']}"
        )
    derived: dict[str, str] = {}
    derived_meta: dict[str, dict[str, str]] = {}
    failed: list[str] = []
    for u in uniq:
        for spec in source_specs:
            en = derive(
                u,
                spec["pairs"],
                spec["contexts"].get(i18n_en.norm(u), []),
                spec["source_date"],
            )
            if en:
                derived[u] = en
                direction = spec["direction"]
                derived_meta[u] = {
                    "source_date": spec["source_date"],
                    "surface": spec["surface"],
                    "master": direction["master"],
                    "rendered": direction["rendered"],
                    "policy": direction["policy"],
                }
                break
        else:
            failed.append(u)

    for k, v in derived.items():
        print(f"   ✔ اشتُقّت: {k[:70]}  →  {v[:70]}")
    for k in failed:
        print(f"   ✘ تعذّر اشتقاقها: {k[:110]}")
    if a.json:
        pathlib.Path(a.json).write_text(
            json.dumps({"derived": derived, "derived_meta": derived_meta, "failed": failed},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")

    if a.apply and derived:
        P = I18N / "glossary.json"
        d = json.loads(P.read_text(encoding="utf-8"))
        ent = d.setdefault("entries", {})
        for k, v in derived.items():
            ent[k] = v
        direction_log = d.setdefault("_directions", {})
        direction_log.update(derived_meta)
        d["updated"] = a.date
        P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"   ✔ كُتبت {len(derived)} وحدة في المعجم")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
