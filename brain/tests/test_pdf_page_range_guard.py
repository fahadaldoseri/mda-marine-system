#!/usr/bin/env python3
"""اختبار فشل مغلق: يرفض PDF خارج نطاق 7–12 صفحة."""
from __future__ import annotations

import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

MIN_PAGES = 7
MAX_PAGES = 12


def check_page_range(pdf: Path) -> int:
    pages = len(PdfReader(str(pdf)).pages)
    return 0 if MIN_PAGES <= pages <= MAX_PAGES else 2


def make_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    with path.open("wb") as handle:
        writer.write(handle)


def test_rejects_pages_outside_range() -> None:
    with tempfile.TemporaryDirectory(prefix="pdf-page-range-") as tmp:
        root = Path(tmp)
        for pages in (6, 13):
            bad = root / f"bad-{pages}.pdf"
            make_pdf(bad, pages)
            assert check_page_range(bad) == 2, f"قُبل PDF خارج النطاق: {pages}"


def test_accepts_range_boundaries() -> None:
    with tempfile.TemporaryDirectory(prefix="pdf-page-range-") as tmp:
        root = Path(tmp)
        for pages in (MIN_PAGES, MAX_PAGES):
            good = root / f"good-{pages}.pdf"
            make_pdf(good, pages)
            assert check_page_range(good) == 0, f"رُفض حد صحيح: {pages}"


if __name__ == "__main__":
    test_rejects_pages_outside_range()
    test_accepts_range_boundaries()
    print("pdf page-range guard: 2/2")
