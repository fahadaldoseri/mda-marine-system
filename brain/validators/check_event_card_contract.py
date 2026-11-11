#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة عقد بطاقة «سجل الأحداث» (فشل مغلق).

تقيس الصفحة المبنية مقابل `appendices/event-card-contract.md`:

- تسعة صفوف ثابتة بالترتيب نفسه في كل بطاقة؛ صف ترجمة المعنى ملغى.
- تسميات الحقول مشتقة من العقد، ومقابلات النسخة الإنجليزية من المعجم الحاكم.
- الصفوف 1 و2 و3 و9 بنيوية: رقم الصف، الحالة المعتمدة، ومضمون غير فارغ.
- لا وسوم ولا روابط مختصرة ظاهرة في نصّ البطاقة.
- الطيّ إلزامي للنص الأصلي.
- تماثل بنيوي بين النسخة العربية والإنجليزية: العدد والرموز والصفوف.

الاستعمال:
  python3 validators/check_event_card_contract.py --date 2026-11-01 --site "$SITE"
  python3 validators/check_event_card_contract.py --date 2026-11-01 --page /path/page.html --json

رموز الخروج: 0 مطابق · 2 منع · 70 انهيار المدقق.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "appendices" / "event-card-contract.md"
DEFAULT_GLOSSARY_PATH = ROOT.parent / "seawatch" / "sources" / "i18n" / "en" / "glossary.json"
CARD_ROWS = 9
LABELLED_ROWS = (4, 5, 6, 7, 8)
AR_LABELLED_ROWS = LABELLED_ROWS
STRUCTURAL_ROWS = (1, 2, 3, 9)
CLASSIFICATION_VALUES = ("بلاغ رسمي", "تقرير مهني", "نقل إعلامي", "نقل سياسي",
                         "رواية غير مؤكدة من طرف واحد", "نفي رسمي", "غير مصنّف", "قيد التثبّت")
RELIABILITY_VALUES = ("عالية", "متوسطة", "منخفضة", "غير مقيّمة")
ROW_STATES = ("shown", "hidden-rule-arabic-source", "hidden-rule-no-excerpt",
              "hidden-rule-no-official-link",
              # ملاحظة المالك 2026-11-02: التوقيت والموقع يُكتبان إن وُجدا،
              # وإن غاب الموقع يُخفى الصف بهذه الحالة المعلنة (مولّد التقرير، صف 5).
              "hidden-rule-no-location")
SHORTLINK_RE = re.compile(r"https?://(?:t\.co|bit\.ly|lnkd\.in|tinyurl\.com|goo\.gl|ow\.ly|"
                          r"buff\.ly|is\.gd|cutt\.ly|rb\.gy)/")
HASHTAG_RE = re.compile(r"(?<!\w)#[A-Za-z0-9_\u0600-\u06ff]{2,}")
TRANSLATION_FALLBACK_RE = re.compile(
    r"(?:الترجمة|ترجمة)\s+(?:غير\s+)?(?:ال)?(?:مدرجة|متاحة|متوفرة|موجودة|مذكورة)\s+في\s+"
    r"(?:الدفتر|السجل)|(?:translation|meaning translation)\s+(?:(?:is|was)\s+)?(?:not\s+)?"
    r"(?:listed|available|present|included)\s+in\s+(?:the\s+)?(?:ledger|log)",
    re.IGNORECASE,
)
MEANING_TRANSLATION_LABELS = {"ترجمة المعنى", "Meaning translation"}
CARD_RE = re.compile(r'<article\b[^>]*\bclass="ev[^"]*"[^>]*>.*?</article>', re.S)
CODE_RE = re.compile(r'data-event-code="([^"]*)"')
ROWS_ATTR_RE = re.compile(r'data-event-rows="(\d+)"')
ROW_OPEN_RE = re.compile(
    r'<(?P<tag>[A-Za-z][\w:-]*)\b'
    r'(?=[^>]*\bdata-row\s*=\s*"(?P<number>\d+)")[^>]*>',
    re.S,
)
ROW_STATE_RE = re.compile(r'\bdata-row-state\s*=\s*"([a-z\-]+)"')
EV_LABEL_RE = re.compile(r'<span\s+class="ev-k">([^<]*)</span>')
BRANCH_TITLE_RE = re.compile(r'<span\s+class="ev-branch-title">([^<]*)</span>')
BADGE_RE = re.compile(r'data-classification="([^"]*)"')
RELIABILITY_RE = re.compile(r'data-reliability="([^"]*)"')
CONTRACT_ROW_RE = re.compile(r'^\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|', re.M)


class RowFragment:
    __slots__ = ("number", "state", "opening_tag", "inner_html")

    def __init__(self, number: int, state: str, opening_tag: str, inner_html: str) -> None:
        self.number = number
        self.state = state
        self.opening_tag = opening_tag
        self.inner_html = inner_html


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RuntimeError(f"الملف مفقود: {path}")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"تعذر قراءة {path}: {exc}") from exc


def load_arabic_row_labels(contract_path: Path = CONTRACT_PATH) -> dict[int, str]:
    """اشتق تسميات الصفوف من جدول العقد، لا من نسخة داخل الحارس."""
    contract = read_text(contract_path)
    section_match = re.search(
        r'^##\s+الصفوف التسعة\s*$.*?(?=^###\s+الصف الملغى\s*$)',
        contract,
        re.M | re.S,
    )
    if not section_match:
        raise RuntimeError(f"جدول صفوف البطاقة مفقود في العقد: {contract_path}")
    labels = {
        int(match.group(1)): match.group(2).strip()
        for match in CONTRACT_ROW_RE.finditer(section_match.group(0))
    }
    expected = set(range(1, CARD_ROWS + 1))
    if set(labels) != expected or any(not label for label in labels.values()):
        raise RuntimeError(
            f"جدول صفوف البطاقة غير مكتمل في العقد: المتوقع 1..{CARD_ROWS}"
        )
    return labels


def _branch_label(arabic_row_label: str) -> str:
    """استخرج عنوان فرع العلاقة من تسمية الصف التاسع في العقد."""
    return arabic_row_label.split("(", 1)[0].strip()


def _arabic_expected_labels(contract_path: Path = CONTRACT_PATH) -> dict[int, str]:
    labels = load_arabic_row_labels(contract_path)
    expected = {number: labels[number] for number in LABELLED_ROWS}
    expected[9] = _branch_label(labels[9])
    return expected


def _load_entries(glossary_path: Path) -> dict[str, str]:
    try:
        data = json.loads(read_text(glossary_path))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"المعجم غير قابل للقراءة: {glossary_path}: {exc}") from exc
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        raise RuntimeError(f"مفتاح entries مفقود أو غير صالح في المعجم: {glossary_path}")
    return entries


def _glossary_translation(entries: dict[str, str], arabic_label: str) -> str:
    direct = entries.get(arabic_label)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    # بعض نسخ المعجم تحفظ تسمية المصدر داخل مثال يبدأ بالعبارة نفسها؛
    # يُشتق الجزء المقابل قبل النقطتين آليًا، ولا تُكتب تسمية إنجليزية في الحارس.
    prefixed = [
        value for key, value in entries.items()
        if isinstance(key, str) and key.startswith(f"{arabic_label}:")
        and isinstance(value, str) and value.strip()
    ]
    if len(prefixed) == 1:
        candidate = prefixed[0].split(":", 1)[0].strip()
        if candidate:
            return candidate
    raise RuntimeError(f"لا مقابل إنجليزي في المعجم للتسمية: {arabic_label}")


def load_english_row_labels(
    glossary_path: Path = DEFAULT_GLOSSARY_PATH,
    arabic_labels: dict[int, str] | None = None,
    *,
    required_rows: tuple[int, ...] | list[int] | None = None,
) -> dict[int, str]:
    """اشتق مقابلات الصفوف من entries للتسميات المطلوبة فقط، بفشل مغلق."""
    arabic_labels = arabic_labels or _arabic_expected_labels()
    required_rows = tuple(required_rows if required_rows is not None else LABELLED_ROWS)
    entries = _load_entries(glossary_path)
    translations: dict[int, str] = {}
    missing: list[str] = []
    for number in required_rows:
        arabic_label = arabic_labels[number]
        try:
            translations[number] = _glossary_translation(entries, arabic_label)
        except RuntimeError:
            missing.append(arabic_label)
    if missing:
        unique_missing = list(dict.fromkeys(missing))
        raise RuntimeError(
            "لا مقابل إنجليزي في المعجم للتسمية: " + "، ".join(unique_missing)
        )
    return translations


def _presented_labels(page_html: str) -> dict[int, str]:
    """اقرأ التسميات المعروضة فعليًا لاختيار مقابلات المعجم اللازمة."""
    rows = _extract_rows(page_html)
    labels: dict[int, str] = {}
    for number in LABELLED_ROWS:
        row = rows.get(number)
        if row is None:
            continue
        match = EV_LABEL_RE.search(row.inner_html)
        if match:
            labels[number] = match.group(1).strip()
    branch = BRANCH_TITLE_RE.search(page_html)
    if branch:
        labels[9] = branch.group(1).strip()
    return labels


def _extract_rows(card_html: str) -> dict[int, RowFragment]:
    matches = list(ROW_OPEN_RE.finditer(card_html))
    rows: dict[int, RowFragment] = {}
    for index, match in enumerate(matches):
        number = int(match.group("number"))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(card_html)
        opening_tag = match.group(0)
        state_match = ROW_STATE_RE.search(opening_tag)
        state = state_match.group(1) if state_match else "shown"
        rows.setdefault(number, RowFragment(number, state, opening_tag, card_html[match.end():end]))
    return rows


def visible_text(card_html: str) -> str:
    """نصّ البطاقة المرئي بلا وسوم، لفحص الوسوم والروابط المختصرة."""
    text = re.sub(r"<(?:script|style)\b.*?</(?:script|style)>", " ", card_html, flags=re.S)
    # ك-471: الفحص على المحارف المرئية بعد فك ترميز الكيانات، فلا يُعدّ «&#x27;» وسمًا.
    return html.unescape(re.sub(r"<[^>]+>", " ", text))


def card_violations(
    card_html: str,
    index: int,
    labels: dict[int, str] | None = None,
) -> list[str]:
    errors: list[str] = []
    labels = labels or _arabic_expected_labels()
    code = (CODE_RE.search(card_html) or [None, f"#{index}"])[1]
    where = f"بطاقة {index} ({code})"
    rows_attr = ROWS_ATTR_RE.search(card_html)
    if not rows_attr or rows_attr.group(1) != str(CARD_ROWS):
        errors.append(f"{where}: سمة عدد الصفوف غائبة أو مخالفة (المتوقع {CARD_ROWS})")

    row_matches = list(ROW_OPEN_RE.finditer(card_html))
    rows = _extract_rows(card_html)
    numbers = [int(match.group("number")) for match in row_matches]
    missing = [str(number) for number in range(1, CARD_ROWS + 1) if number not in rows]
    if missing:
        errors.append(f"{where}: صفوف غائبة: {', '.join(missing)}")
    duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
    if duplicates:
        errors.append(f"{where}: صفوف مكررة: {', '.join(map(str, duplicates))}")

    for number, row in sorted(rows.items()):
        if row.state not in ROW_STATES:
            errors.append(f"{where}: صف {number} بحالة غير معروفة: {row.state}")
        if number in STRUCTURAL_ROWS:
            content = visible_text(row.inner_html).strip()
            if number == 9 and not content:
                branch_status = re.search(r'data-branch-status="([^"]+)"', row.opening_tag)
                content = branch_status.group(1).strip() if branch_status else ""
            if not content:
                errors.append(f"{where}: صف {number} بلا مضمون")

    for number in LABELLED_ROWS:
        label = labels.get(number)
        row = rows.get(number)
        if not label or row is None:
            continue
        actual = EV_LABEL_RE.search(row.inner_html)
        if actual is None:
            errors.append(f"{where}: وسم الصف {number} مفقود (المتوقع «{label}»)")
        elif actual.group(1).strip() != label:
            errors.append(f"{where}: وسم الصف {number} لا يطابق العقد («{label}»)")

    expected_branch = labels.get(9)
    branch_titles = BRANCH_TITLE_RE.findall(card_html)
    if expected_branch and branch_titles:
        if any(title.strip() != expected_branch for title in branch_titles):
            errors.append(f"{where}: وسم العلاقة لا يطابق العقد («{expected_branch}»)")

    row_labels = [label.strip() for label in EV_LABEL_RE.findall(card_html)]
    if any(label in MEANING_TRANSLATION_LABELS for label in row_labels):
        errors.append(f"{where}: صف ترجمة المعنى ظاهر في البطاقة رغم إلغائه بقرار المالك")
    row_eight = re.search(
        r'<[^>]*\bdata-row="8"[^>]*>.*?<span class="ev-k">([^<]*)</span>',
        card_html,
        re.S,
    )
    if row_eight and row_eight.group(1).strip() in MEANING_TRANSLATION_LABELS:
        errors.append(f"{where}: الصف الثامن موسوم «ترجمة المعنى» رغم إلغائه بقرار المالك")

    badge = BADGE_RE.search(card_html)
    if not badge:
        errors.append(f"{where}: شارة التصنيف غائبة")
    elif badge.group(1) not in CLASSIFICATION_VALUES:
        errors.append(f"{where}: تصنيف خارج القائمة المغلقة: {badge.group(1)}")
    reliability = RELIABILITY_RE.search(card_html)
    if not reliability:
        errors.append(f"{where}: شارة درجة الموثوقية غائبة")
    elif reliability.group(1) not in RELIABILITY_VALUES:
        errors.append(f"{where}: درجة موثوقية خارج القائمة المغلقة: {reliability.group(1)}")

    text = visible_text(card_html)
    if SHORTLINK_RE.search(text):
        errors.append(f"{where}: رابط مختصر ظاهر في نصّ البطاقة")
    if HASHTAG_RE.search(text):
        errors.append(f"{where}: وسم (#) ظاهر في نصّ البطاقة")
    # قرار العقد 2026-11-01: المسار الداخلي لا يُعرض على سطح القارئ أصلًا؛
    # فيُمنع ظهوره نصًّا، ولا يُشترط وسم طيّ لصف غير معروض.
    if "source_excerpt_from" in text or "مسار التحقق الداخلي" in text:
        errors.append(f"{where}: المسار الداخلي ظاهر على سطح القارئ")
    if 'data-fold="original-text"' not in card_html and rows.get(8, RowFragment(8, "", "", "")).state == "shown":
        errors.append(f"{where}: صف النص الأصلي ظاهر بلا طيّ")
    if rows.get(8, RowFragment(8, "", "", "")).state.startswith("hidden") and 'data-fold="original-text"' in card_html:
        errors.append(f"{where}: صف النص الأصلي مخفيّ وله طيّ في الوقت نفسه")
    # ملاحظات المالك 2026-11-02 (فشل مغلق على كل بطاقة):
    if "التوقيت غير مسجّل" in text:
        errors.append(f"{where}: عبارة غياب التوقيت ظاهرة (أُلغيت بقرار المالك)")
    if "الرابط الرسمي غير مدرج" in text or "من تغذية المصادر" in text:
        errors.append(f"{where}: عبارة غياب الرابط أو إسناد التغذية ظاهرة (أُلغيت بقرار المالك)")
    if "الموضع" in text:
        errors.append(f"{where}: وسم «الموضع» ظاهر بدل «الموقع»")
    if rows.get(7, RowFragment(7, "", "", "")).state.startswith("hidden") and "hidden-rule-no-official-link" not in card_html:
        errors.append(f"{where}: صف الرابط الرسمي مخفيّ بحالة غير معروفة")
    src_row = rows.get(6)
    if src_row and "@" in src_row.inner_html and 'class="ev-link"' not in src_row.inner_html:
        errors.append(f"{where}: مصدر باسم حساب (@) بلا رابط إلى مادة المصدر")
    if rows.get(7, RowFragment(7, "", "", "")).state == "shown" and not re.search(r'<a\b[^>]*href="https?://', card_html):
        errors.append(f"{where}: صف الرابط الرسمي ظاهر بلا رابط")
    return errors


def page_violations(
    page_html: str,
    label: str,
    labels: dict[int, str] | None = None,
) -> tuple[list[str], list[str]]:
    cards = CARD_RE.findall(page_html)
    errors: list[str] = []
    page_text = visible_text(page_html)
    if TRANSLATION_FALLBACK_RE.search(page_text):
        errors.append(f"{label}: نص ترجمة بديل ظاهر في الصفحة المبنية")
    if not cards:
        errors.append(f"{label}: لا بطاقات سجل أحداث في الصفحة")
        return errors, []
    codes: list[str] = []
    for index, card in enumerate(cards, 1):
        errors.extend(card_violations(card, index, labels))
        match = CODE_RE.search(card)
        codes.append(match.group(1) if match else "")
    if len(set(codes)) != len(codes):
        errors.append(f"{label}: رموز بطاقات مكررة في الصفحة")
    return errors, codes


# واجهة توافقية للاختبارات والأدوات التي تستورد الثوابت؛ القيم مشتقة عند الاستيراد.
ROW_LABELS = load_arabic_row_labels()
AR_EXPECTED_LABELS = _arabic_expected_labels()
try:
    EN_ROW_LABELS = load_english_row_labels(
        DEFAULT_GLOSSARY_PATH,
        AR_EXPECTED_LABELS,
        required_rows=LABELLED_ROWS + (9,),
    )
except RuntimeError:
    EN_ROW_LABELS = {}


def main() -> int:
    parser = argparse.ArgumentParser(description="بوابة عقد بطاقة سجل الأحداث (فشل مغلق)",
                                     allow_abbrev=False)
    parser.add_argument("--date", required=True)
    parser.add_argument("--site", default=None)
    parser.add_argument("--brain", default=str(ROOT))
    parser.add_argument("--page", default=None, help="صفحة عربية محددة للقياس")
    parser.add_argument("--en-page", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    site = Path(args.site) if args.site else ROOT.parent / "seawatch"
    ar_page = Path(args.page) if args.page else site / "dist" / "reports" / f"{args.date}.html"
    en_page = Path(args.en_page) if args.en_page else site / "dist" / "reports" / "en" / f"{args.date}.html"
    ledger = site / "sources" / "daily-events" / f"{args.date}.json"

    errors: list[str] = []
    notes: list[str] = []
    try:
        if not ledger.is_file():
            raise RuntimeError(f"دفتر اليوم مفقود: {ledger}")
        ledger_rows = json.loads(read_text(ledger))
        ar_html = read_text(ar_page)
        ar_expected = _arabic_expected_labels()
    except RuntimeError as exc:
        print(f"✘ منع: {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"✘ منع: دفتر اليوم غير قابل للقراءة: {exc}")
        return 2

    ar_errors, ar_codes = page_violations(ar_html, "العربية", ar_expected)
    errors.extend(ar_errors)
    records = [row for row in ledger_rows if isinstance(row, dict) and not row.get("no_incident")]
    no_incident_codes = [
        str(row.get("code") or "").strip()
        for row in ledger_rows
        if isinstance(row, dict) and row.get("no_incident")
    ]
    if not records and no_incident_codes:
        # يوم بلا وقائع: الدفتر يعلنها صراحةً (no_incident)، فتُقبل بطاقة «لا وقائع» وحدها
        # بشرط مطابقة رموزها لسجل الدفتر حرفيًا؛ وأي بطاقة أخرى تبقى مانعة.
        if ar_codes != no_incident_codes:
            errors.append(
                f"العربية: يوم بلا وقائع لكن بطاقات الصفحة {ar_codes} "
                f"لا تطابق سجل «لا وقائع» {no_incident_codes}"
            )
    elif len(ar_codes) != len(records):
        errors.append(f"العربية: عدد البطاقات {len(ar_codes)} لا يساوي وقائع الدفتر {len(records)}")
    expected_codes = [str(row.get("code") or "").strip() for row in records]
    if ar_codes and expected_codes and ar_codes != expected_codes:
        errors.append("العربية: رموز البطاقات لا تطابق رموز الدفتر بالترتيب")

    if en_page.is_file():
        try:
            presented_ar = _presented_labels(ar_html)
            en_labels = load_english_row_labels(
                site / "sources" / "i18n" / "en" / "glossary.json",
                presented_ar,
                required_rows=tuple(presented_ar),
            )
        except RuntimeError as exc:
            en_labels = {}
            errors.append(str(exc))
        en_errors, en_codes = page_violations(read_text(en_page), "الإنجليزية", en_labels)
        errors.extend(en_errors)
        if en_codes and ar_codes and en_codes != ar_codes:
            errors.append("تماثل: رموز النسخة الإنجليزية لا تطابق العربية بالترتيب")
    else:
        notes.append(f"نسخة إنجليزية غير مبنية لهذا اليوم: {en_page.name}")

    result = {"gate": "check_event_card_contract", "date": args.date,
              "cards": len(ar_codes), "status": "blocked" if errors else "ok",
              "violations": errors, "notes": notes}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 2 if errors else 0
    print(f"عقد بطاقة سجل الأحداث — {args.date}: {len(ar_codes)} بطاقة")
    for note in notes:
        print("•", note)
    if errors:
        for error in errors[:40]:
            print("✘", error)
        if len(errors) > 40:
            print(f"✘ … و{len(errors) - 40} مخالفة أخرى")
        print("النتيجة: منع — فشل مغلق")
        return 2
    print("النتيجة: مطابق")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
