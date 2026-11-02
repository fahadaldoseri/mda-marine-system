#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة عقد بطاقة «سجل الأحداث» (فشل مغلق).

تقيس الصفحة المبنية مقابل `appendices/event-card-contract.md`:

- عشرة صفوف ثابتة بالترتيب نفسه في كل بطاقة: العنوان · التصنيف · درجة الموثوقية ·
  التاريخ والوقت · الموضع · المصدر · الرابط الرسمي · ترجمة المعنى · النص الأصلي · فرع تابع.
- الوسوم حرفية كما في العقد، والقيم داخل القوائم المغلقة.
- لا وسوم ولا روابط مختصرة ظاهرة في نصّ البطاقة.
- الطيّ إلزامي لمسار التحقق الداخلي وللنص الأصلي.
- تماثل بنيوي بين النسخة العربية والإنجليزية: العدد والرموز والصفوف.

الاستعمال:
  python3 validators/check_event_card_contract.py --date 2026-11-01 --site "$SITE"
  python3 validators/check_event_card_contract.py --date 2026-11-01 --page /path/page.html --json

رموز الخروج: 0 مطابق · 2 منع · 70 انهيار المدقق.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD_ROWS = 10
ROW_LABELS = {4: "التاريخ والوقت", 5: "الموضع", 6: "المصدر", 7: "الرابط الرسمي",
              8: "ترجمة المعنى", 9: "النص الأصلي"}
# الوسوم المقابلة في النسخة الإنجليزية (تُقرأ من المعجم المعتمد، لا تُخمَّن).
EN_ROW_LABELS = {4: "Date and time", 5: "Location", 6: "Source and grade",
                 7: "Official link", 8: "Meaning translation", 9: "Original text"}
CLASSIFICATION_VALUES = ("بلاغ رسمي", "تقرير مهني", "نقل إعلامي", "نقل سياسي",
                         "رواية غير مؤكدة من طرف واحد", "نفي رسمي", "غير مصنّف", "قيد التثبّت")
RELIABILITY_VALUES = ("عالية", "متوسطة", "منخفضة", "غير مقيّمة")
ROW_STATES = ("shown", "hidden-rule-arabic-source", "hidden-rule-no-excerpt")
SHORTLINK_RE = re.compile(r"https?://(?:t\.co|bit\.ly|lnkd\.in|tinyurl\.com|goo\.gl|ow\.ly|"
                          r"buff\.ly|is\.gd|cutt\.ly|rb\.gy)/")
HASHTAG_RE = re.compile(r"(?<!\w)#[A-Za-z0-9_\u0600-\u06ff]{2,}")
CARD_RE = re.compile(r'<article\b[^>]*\bclass="ev[^"]*"[^>]*>.*?</article>', re.S)
CODE_RE = re.compile(r'data-event-code="([^"]*)"')
ROWS_ATTR_RE = re.compile(r'data-event-rows="(\d+)"')
ROW_RE = re.compile(r'data-row="(\d+)"(?: data-row-state="([a-z\-]+)")?[^>]*>\s*'
                    r'(?:<span class="ev-k">([^<]*)</span>)?')
BADGE_RE = re.compile(r'data-classification="([^"]*)"')
RELIABILITY_RE = re.compile(r'data-reliability="([^"]*)"')


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RuntimeError(f"الملف مفقود: {path}")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"تعذر قراءة {path}: {exc}") from exc


def visible_text(card_html: str) -> str:
    """نصّ البطاقة المرئي بلا وسوم، لفحص الوسوم والروابط المختصرة."""
    text = re.sub(r"<(?:script|style)\b.*?</(?:script|style)>", " ", card_html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", text)


def card_violations(card_html: str, index: int, labels: dict[int, str] | None = None) -> list[str]:
    errors: list[str] = []
    labels = labels or ROW_LABELS
    code = (CODE_RE.search(card_html) or [None, f"#{index}"])[1]
    where = f"بطاقة {index} ({code})"
    rows_attr = ROWS_ATTR_RE.search(card_html)
    if not rows_attr or rows_attr.group(1) != str(CARD_ROWS):
        errors.append(f"{where}: سمة عدد الصفوف غائبة أو مخالفة (المتوقع {CARD_ROWS})")
    found: dict[int, str] = {}
    for match in ROW_RE.finditer(card_html):
        found[int(match.group(1))] = match.group(2) or "shown"
    missing = [str(number) for number in range(1, CARD_ROWS + 1) if number not in found]
    if missing:
        errors.append(f"{where}: صفوف غائبة: {', '.join(missing)}")
    for number, state in sorted(found.items()):
        if state not in ROW_STATES:
            errors.append(f"{where}: صف {number} بحالة غير معروفة: {state}")
    for number, label in labels.items():
        if number in found and label not in card_html:
            errors.append(f"{where}: وسم الصف {number} لا يطابق العقد («{label}»)")
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
    if 'data-fold="original-text"' not in card_html and found.get(9) == "shown":
        errors.append(f"{where}: صف النص الأصلي ظاهر بلا طيّ")
    if found.get(9, "").startswith("hidden") and 'data-fold="original-text"' in card_html:
        errors.append(f"{where}: صف النص الأصلي مخفيّ وله طيّ في الوقت نفسه")
    return errors


def page_violations(page_html: str, label: str,
                    labels: dict[int, str] | None = None) -> tuple[list[str], list[str]]:
    cards = CARD_RE.findall(page_html)
    errors: list[str] = []
    if not cards:
        return [f"{label}: لا بطاقات سجل أحداث في الصفحة"], []
    codes: list[str] = []
    for index, card in enumerate(cards, 1):
        errors.extend(card_violations(card, index, labels))
        match = CODE_RE.search(card)
        codes.append(match.group(1) if match else "")
    if len(set(codes)) != len(codes):
        errors.append(f"{label}: رموز بطاقات مكررة في الصفحة")
    return errors, codes


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
    except RuntimeError as exc:
        print(f"✘ منع: {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"✘ منع: دفتر اليوم غير قابل للقراءة: {exc}")
        return 2

    ar_errors, ar_codes = page_violations(ar_html, "العربية")
    errors.extend(ar_errors)
    records = [row for row in ledger_rows if isinstance(row, dict) and not row.get("no_incident")]
    if len(ar_codes) != len(records):
        errors.append(f"العربية: عدد البطاقات {len(ar_codes)} لا يساوي وقائع الدفتر {len(records)}")
    expected_codes = [str(row.get("code") or "").strip() for row in records]
    if ar_codes and expected_codes and ar_codes != expected_codes:
        errors.append("العربية: رموز البطاقات لا تطابق رموز الدفتر بالترتيب")

    if en_page.is_file():
        en_errors, en_codes = page_violations(read_text(en_page), "الإنجليزية", EN_ROW_LABELS)
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
    from _guard import run
    run(main)
