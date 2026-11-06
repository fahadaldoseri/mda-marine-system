#!/usr/bin/env python3
"""Verify that PDF index page numbers match physical pages of section headings.

The matcher normalizes Arabic letters and removes bidi controls. It does not use
fuzzy character similarity. Because some RTL extractors reverse a whole title,
it also tries the deterministic reverse of the normalized title. Physical pages
are 1-based.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - exercised only in incomplete environments
    PdfReader = None  # type: ignore


ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
ARABIC_LETTER_RE = re.compile(r"[\u0600-\u06ff]")
PAGE_NUMBER_RE = re.compile(r"(?<!\d)(\d{1,4})(?!\d)")
BIDI_CONTROLS = re.compile(r"[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]")
INDEX_MARKERS = ("الفهرس", "المحتويات", "جدول المحتويات", "contents", "tableofcontents")


@dataclass(frozen=True)
class IndexEntry:
    title: str
    expected_page: int
    index_page: int
    raw_line: str


def append_learning_log(log_path: Path | None, event: dict) -> None:
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        import datetime
        event = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), **event}
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def normalize_arabic(text: str) -> str:
    """Normalize Arabic glyph variants without fuzzy matching."""
    text = unicodedata.normalize("NFKC", text or "")
    text = BIDI_CONTROLS.sub("", text)
    text = ARABIC_DIACRITICS.sub("", text)
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ة": "ه",
        "ى": "ي",  # alif maqsura -> yaa
        "ـ": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.lower()


def compact(text: str) -> str:
    """Return a punctuation/whitespace-free normalized comparison form."""
    normalized = normalize_arabic(text)
    return "".join(ch for ch in normalized if ch.isalnum() or "\u0600" <= ch <= "\u06ff")


def text_pages_with_pdftotext(pdf_path: Path) -> list[str]:
    proc = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = proc.stdout
    return text.split("\f")[:-1] if text.endswith("\f") else text.split("\f")


def extract_pages(pdf_path: Path) -> list[str]:
    # Layout extraction preserves the line association needed for index leaders.
    try:
        pages = text_pages_with_pdftotext(pdf_path)
        if any(page.strip() for page in pages):
            return pages
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"تحذير: تعذر pdftotext: {exc}", file=sys.stderr)

    if PdfReader is not None:
        try:
            reader = PdfReader(str(pdf_path))
            pages = [(page.extract_text() or "") for page in reader.pages]
            if any(page.strip() for page in pages):
                return pages
        except Exception as exc:
            print(f"تحذير: تعذر استخراج النص عبر pypdf: {exc}", file=sys.stderr)
    raise RuntimeError("تعذر استخراج طبقة نص PDF")


def comparison_forms(text: str) -> set[str]:
    base = compact(text)
    if not base:
        return set()
    # Reversal is a deterministic recovery for extractors that emit an RTL line
    # in visual order. It is not fuzzy similarity and is reported as textual evidence only.
    return {base, base[::-1]}


def has_index_marker(page_text: str) -> bool:
    normalized_page = compact(page_text)
    return any(
        form in normalized_page
        for marker in INDEX_MARKERS
        for form in comparison_forms(marker)
    )


def clean_title_fragment(fragment: str) -> str:
    fragment = BIDI_CONTROLS.sub("", fragment)
    fragment = re.sub(r"[.·…_\-–—|:؛،]+", " ", fragment)
    return " ".join(fragment.split()).strip()


def is_likely_index_line(line: str) -> bool:
    compact_line = compact(line)
    return (
        len(compact_line) >= 4
        and bool(ARABIC_LETTER_RE.search(line))
        and not compact_line.startswith("صفحه")
        and not compact_line.startswith("page")
    )


def parse_index_candidates(pages: list[str]) -> list[IndexEntry]:
    """Parse trailing or leading page numbers from early index/contents pages."""
    scan_count = min(len(pages), 8)
    marker_pages = [
        page_no for page_no, page_text in enumerate(pages[:scan_count], start=1) if has_index_marker(page_text)
    ]
    start_page = min(marker_pages) if marker_pages else 1
    entries: list[IndexEntry] = []
    seen: set[tuple[str, int]] = set()
    for page_no in range(start_page, scan_count + 1):
        for raw_line in pages[page_no - 1].splitlines():
            line = " ".join(raw_line.split())
            if not is_likely_index_line(line):
                continue
            numbers = list(PAGE_NUMBER_RE.finditer(line))
            if not numbers:
                continue
            number_match = numbers[-1]
            expected_page = int(number_match.group(1))
            # RTL layout may put the title after its page number. Choose the
            # longest Arabic-bearing side of the number, then clean leaders.
            sides = [line[: number_match.start()], line[number_match.end() :]]
            title_candidates = [clean_title_fragment(side) for side in sides if ARABIC_LETTER_RE.search(side)]
            if not title_candidates:
                continue
            title = max(title_candidates, key=lambda value: len(compact(value)))
            if not is_likely_index_line(title):
                continue
            normalized_title = compact(title)
            key = (normalized_title, expected_page)
            if key in seen:
                continue
            seen.add(key)
            entries.append(IndexEntry(title, expected_page, page_no, line))

    if not marker_pages:
        leader_entries = [e for e in entries if re.search(r"[.·…_\-–—]{2,}", e.raw_line)]
        if leader_entries:
            entries = leader_entries
    return entries


def find_actual_page(title: str, pages: list[str], index_page: int) -> tuple[int | None, list[int]]:
    needles = comparison_forms(title)
    matches = [
        page_no
        for page_no, page_text in enumerate(pages, start=1)
        if page_no > index_page and any(needle in compact(page_text) for needle in needles)
    ]
    return (matches[0] if matches else None), matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare PDF index page numbers with physical heading pages.")
    parser.add_argument("--pdf", required=True, type=Path, help="PDF file to verify")
    parser.add_argument("--log-path", type=Path, help="Optional JSONL learning/defect log path")
    args = parser.parse_args()
    if not args.pdf.is_file():
        print(f"ERROR: PDF غير موجود: {args.pdf}", file=sys.stderr)
        return 1
    try:
        pages = extract_pages(args.pdf)
        entries = parse_index_candidates(pages)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"PDF: {args.pdf}")
    print(f"الصفحات الفيزيائية: {len(pages)} | الإدخالات المستخرجة: {len(entries)}")
    if not entries:
        print("لا يمكن التحقق: لم يُستخرج أي سطر فهرس بعنوان عربي ورقم صفحة.")
        print("تحقق يدويًا من صفحة الفهرس ثم أعد التشغيل.")
        append_learning_log(args.log_path, {
            "tool": "verify_pdf_index",
            "status": "لم يتحقق",
            "pdf": str(args.pdf),
            "reason": "لم يُستخرج أي سطر فهرس قابل للمطابقة",
        })
        return 2

    mismatches = 0
    for entry in entries:
        actual, all_matches = find_actual_page(entry.title, pages, entry.index_page)
        status = "OK" if actual == entry.expected_page else "DIFF"
        if status == "DIFF":
            mismatches += 1
        found = ",".join(map(str, all_matches)) if all_matches else "غير موجود"
        print(
            f"[{status}] {entry.title} | الفهرس={entry.expected_page} "
            f"| الفعلي={actual if actual is not None else 'غير موجود'} | تطابقات={found}"
        )

    if mismatches:
        append_learning_log(args.log_path, {
            "tool": "verify_pdf_index",
            "status": "مؤكد",
            "pdf": str(args.pdf),
            "finding": "index-page-mismatch",
            "count": mismatches,
        })
        print(f"النتيجة: {mismatches} اختلاف(ات).")
        return 2
    print("النتيجة: جميع أرقام الفهرس المطابقة عُثر عليها في الصفحة الفيزيائية نفسها.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
