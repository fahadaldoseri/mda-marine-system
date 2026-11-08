#!/usr/bin/env python3
"""اختبارات عدّ الأرقام المرئية في صفحات التماثل الإنجليزي."""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_en_parity_visible_numbers", ROOT / "validators" / "check_en_parity.py"
)
assert SPEC and SPEC.loader
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


def _page(path: Path, visible_number: str, css_number: str, script_number: str) -> None:
    path.write_text(
        "<html lang=\"en\" dir=\"ltr\"><head>"
        f"<style>.marker{{width:{css_number}px}}</style>"
        f"<script>const internal={script_number}</script>"
        "</head><body><main><p>Visible total: "
        f"{visible_number}"
        "</p></main></body></html>",
        encoding="utf-8",
    )


def test_numbers_inside_css_and_script_are_not_visible() -> None:
    with TemporaryDirectory(prefix="en-parity-visible-positive-") as raw:
        root = Path(raw)
        arabic = root / "ar.html"
        english = root / "en.html"
        _page(arabic, "128", "122", "991")
        _page(english, "128", "777", "12345")
        expected = Counter({"128": 1})
        assert parity.page_stats(arabic)["visible_numbers"] == expected
        assert parity.page_stats(english)["visible_numbers"] == expected


def test_different_visible_number_is_detected() -> None:
    with TemporaryDirectory(prefix="en-parity-visible-negative-") as raw:
        root = Path(raw)
        arabic = root / "ar.html"
        english = root / "en.html"
        _page(arabic, "128", "122", "991")
        _page(english, "129", "122", "991")
        assert parity.page_stats(arabic)["visible_numbers"] != parity.page_stats(english)["visible_numbers"]


if __name__ == "__main__":
    test_numbers_inside_css_and_script_are_not_visible()
    test_different_visible_number_is_detected()
    print("visible-number parity regression: 2/2")
