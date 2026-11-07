#!/usr/bin/env python3
"""اختبار فشل مغلق: يرفض اختلاف بصمة PDF أو ظهور العربية في HTML الإنجليزي."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

ARABIC = "\u0600-\u06ff"


def check_live_parity_en(local_pdf: Path, live_pdf: Path, english_html: Path) -> int:
    local_sha = hashlib.sha256(local_pdf.read_bytes()).hexdigest()
    live_sha = hashlib.sha256(live_pdf.read_bytes()).hexdigest()
    english = english_html.read_text(encoding="utf-8")
    if local_sha != live_sha or any("\u0600" <= ch <= "\u06ff" for ch in english):
        return 2
    return 0


def test_rejects_live_pdf_hash_mismatch() -> None:
    with tempfile.TemporaryDirectory(prefix="pdf-live-guard-") as tmp:
        root = Path(tmp)
        local = root / "local.pdf"
        live = root / "live.pdf"
        english = root / "en.html"
        local.write_bytes(b"local-pdf")
        live.write_bytes(b"different-live-pdf")
        english.write_text("<html lang=\"en\">English</html>", encoding="utf-8")
        assert check_live_parity_en(local, live, english) == 2


def test_rejects_arabic_in_english_surface() -> None:
    with tempfile.TemporaryDirectory(prefix="pdf-live-guard-") as tmp:
        root = Path(tmp)
        local = root / "local.pdf"
        live = root / "live.pdf"
        english = root / "en.html"
        local.write_bytes(b"same-pdf")
        live.write_bytes(b"same-pdf")
        english.write_text("<html lang=\"en\">خطر</html>", encoding="utf-8")
        assert check_live_parity_en(local, live, english) == 2


def test_accepts_matching_english_surface() -> None:
    with tempfile.TemporaryDirectory(prefix="pdf-live-guard-") as tmp:
        root = Path(tmp)
        local = root / "local.pdf"
        live = root / "live.pdf"
        english = root / "en.html"
        local.write_bytes(b"same-pdf")
        live.write_bytes(b"same-pdf")
        english.write_text("<html lang=\"en\">English</html>", encoding="utf-8")
        assert check_live_parity_en(local, live, english) == 0


if __name__ == "__main__":
    test_rejects_live_pdf_hash_mismatch()
    test_rejects_arabic_in_english_surface()
    test_accepts_matching_english_surface()
    print("pdf live/parity English guard: 3/3")
