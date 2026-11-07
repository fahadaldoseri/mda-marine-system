#!/usr/bin/env python3
"""Compare numeric ranges/percentages in a source text with a PDF text layer.

This tool flags only text-layer evidence. A clean or ambiguous result is not a
visual assertion; the caller must inspect rendered page images for RTL order.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore

DIGIT_TRANSLATION = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)
HYPHENS = "‐‑‒–—−﹘﹣－"


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    raw: str
    page: int | None = None


def append_learning_log(log_path: Path | None, event: dict) -> None:
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        import datetime
        event = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), **event}
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def normalize_text(text: str) -> str:
    text = (text or "").translate(DIGIT_TRANSLATION)
    for hyphen in HYPHENS:
        text = text.replace(hyphen, "-")
    return text.replace("٪", "%")


def extract_tokens(text: str, page: int | None = None) -> list[Token]:
    text = normalize_text(text)
    tokens: list[tuple[int, Token]] = []
    range_re = re.compile(r"(?<!\d)(\d{1,6})\s*-\s*(\d{1,6})(?!\d)")
    percent_re = re.compile(r"(?:(%)\s*)?(\d{1,6}(?:[.,]\d+)?)\s*(%)")
    occupied: list[tuple[int, int]] = []
    for match in range_re.finditer(text):
        raw = match.group(0)
        tokens.append((match.start(), Token("range", f"{match.group(1)}-{match.group(2)}", raw, page)))
        occupied.append((match.start(), match.end()))
    for match in percent_re.finditer(text):
        if any(start < match.end() and match.start() < end for start, end in occupied):
            continue
        number = match.group(2).replace(",", ".")
        tokens.append((match.start(), Token("percent", f"{number}%", match.group(0), page)))
    tokens.sort(key=lambda item: item[0])
    return [token for _, token in tokens]


def text_pages_with_pdftotext(pdf_path: Path) -> list[str]:
    proc = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = proc.stdout
    return text.split("\f")[:-1] if text.endswith("\f") else text.split("\f")


def extract_pdf_pages(pdf_path: Path) -> list[str]:
    try:
        pages = text_pages_with_pdftotext(pdf_path)
        if any(page.strip() for page in pages):
            return pages
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"تحذير: تعذر pdftotext: {exc}", file=sys.stderr)
    if PdfReader is not None:
        reader = PdfReader(str(pdf_path))
        pages = [(p.extract_text() or "") for p in reader.pages]
        if any(page.strip() for page in pages):
            return pages
    raise RuntimeError("تعذر قراءة طبقة النص")


def reverse_variants(token: Token) -> set[str]:
    if token.kind == "range":
        left, right = token.value.split("-", 1)
        return {f"{left[::-1]}-{right[::-1]}", f"{right}-{left}", f"{right[::-1]}-{left[::-1]}"}
    number = token.value[:-1]
    return {f"{number[::-1]}%", f"%{number}", f"%{number[::-1]}"}


def pair_tokens(expected: list[Token], observed: list[Token]) -> tuple[list[tuple[Token, Token]], list[Token], list[Token]]:
    """Pair exact values first, then deterministic reverse variants.

    Pairing is order-tolerant because RTL text extraction often emits a visual
    order that differs from source order. The original sequences remain printed
    so a reviewer can decide whether the page image is needed.
    """
    remaining = list(observed)
    pairs: list[tuple[Token, Token]] = []
    unmatched_expected: list[Token] = []
    for expected_token in expected:
        match_index = next(
            (i for i, observed_token in enumerate(remaining)
             if observed_token.kind == expected_token.kind and observed_token.value == expected_token.value),
            None,
        )
        if match_index is None:
            unmatched_expected.append(expected_token)
        else:
            pairs.append((expected_token, remaining.pop(match_index)))
    still_unmatched_expected = []
    for expected_token in unmatched_expected:
        match_index = next(
            (i for i, observed_token in enumerate(remaining)
             if observed_token.kind == expected_token.kind and observed_token.value in reverse_variants(expected_token)),
            None,
        )
        if match_index is None:
            still_unmatched_expected.append(expected_token)
        else:
            pairs.append((expected_token, remaining.pop(match_index)))
    return pairs, still_unmatched_expected, remaining


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect reversed numeric ranges/percentages in a PDF text layer.")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path, help="UTF-8 source text containing expected values")
    parser.add_argument("--log-path", type=Path, help="Optional JSONL learning/defect log path")
    args = parser.parse_args()
    if not args.pdf.is_file() or not args.source.is_file():
        print("ERROR: يجب أن يكون PDF وملف المصدر موجودين.", file=sys.stderr)
        return 1
    try:
        expected = extract_tokens(args.source.read_text(encoding="utf-8"))
        pages = extract_pdf_pages(args.pdf)
        observed: list[Token] = []
        for page_no, page_text in enumerate(pages, start=1):
            observed.extend(extract_tokens(page_text, page_no))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"المتوقع من المصدر: {len(expected)} | الموجود في طبقة PDF: {len(observed)}")
    if not expected:
        print("لا توجد نطاقات رقمية أو نسب مئوية في المصدر؛ لا يوجد فحص لهذا البند.")
        return 0
    if len(expected) != len(observed):
        print("لا يمكن الحكم من النص: عدد القيم في طبقة PDF لا يطابق المصدر.")
        print("اطلب معاينة صورة الصفحة ولا تصدر حكمًا نصيًا بالاتجاه.")
        print(f"المتوقع: {[t.value for t in expected]}")
        print(f"الموجود: {[t.value for t in observed]}")
        append_learning_log(args.log_path, {
            "tool": "verify_range_bidi",
            "status": "لم يتحقق",
            "pdf": str(args.pdf),
            "source": str(args.source),
            "reason": "عدد القيم في طبقة PDF لا يطابق المصدر",
        })
        return 3

    exact_sequence = all(e.kind == o.kind and e.value == o.value for e, o in zip(expected, observed))
    pairs, unmatched_expected, unmatched_observed = pair_tokens(expected, observed)
    if unmatched_expected or unmatched_observed:
        print("لا يمكن الحكم من النص: توجد قيم مختلفة أو غير قابلة للمحاذاة.")
        print("اطلب معاينة صورة الصفحة ولا تصدر حكمًا نصيًا بالاتجاه.")
        print(f"غير محاذى من المصدر: {[t.value for t in unmatched_expected]}")
        print(f"غير محاذى من PDF: {[t.value for t in unmatched_observed]}")
        append_learning_log(args.log_path, {
            "tool": "verify_range_bidi",
            "status": "لم يتحقق",
            "pdf": str(args.pdf),
            "source": str(args.source),
            "reason": "تعذر محاذاة القيم",
        })
        return 3

    inversions = [(e, o) for e, o in pairs if e.value != o.value]
    if inversions:
        print("انعكاس مؤكد في طبقة النص (لا يغني عن المعاينة البصرية):")
        for expected_token, observed_token in inversions:
            page = f" صفحة {observed_token.page}" if observed_token.page else ""
            print(f"- المتوقع {expected_token.value} ← الموجود {observed_token.value}{page}")
        append_learning_log(args.log_path, {
            "tool": "verify_range_bidi",
            "status": "مؤكد",
            "pdf": str(args.pdf),
            "source": str(args.source),
            "finding": "reversed-range-or-percent",
            "items": [{"expected": e.value, "observed": o.value, "page": o.page} for e, o in inversions],
        })
        return 2

    if exact_sequence:
        print("لم يظهر انعكاس في تسلسل طبقة النص.")
    else:
        print("القيم نفسها موجودة لكن مستخرج PDF أعاد ترتيبها؛ لم يظهر عكسٌ داخل قيمة نطاق/نسبة.")
    print("تنبيه: هذا ليس حكمًا بصريًا؛ راجع صورة الصفحة لتأكيد اتجاه وترتيب النطاقات والنسب.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
