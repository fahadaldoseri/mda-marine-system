#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ك-599: وسم رموز الدرجات على السطحين — اختبار انحدار."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import reader_grade_labels as R  # noqa: E402


def test_arabic_surface_gets_arabic_label_without_code():
    out = R.redact("(03-05 و03-08؛ C/3)", "ar")
    assert "C/3" not in out
    assert "موثوقية" in out


def test_english_surface_gets_english_label_without_code_or_arabic():
    out = R.redact("(03-05 and 03-08; C/3)", "en")
    assert "C/3" not in out
    assert "reliability" in out
    assert not any("\u0600" <= ch <= "\u06ff" for ch in out)


def test_unsupported_language_fails_closed():
    for lang in ("fr", "", "AR"):
        try:
            R.redact("C/3", lang)
        except ValueError:
            continue
        raise AssertionError(f"language {lang!r} should fail closed")


def test_exposed_codes_detects_every_governed_code():
    assert R.exposed_codes("A/1 C/3 F/6") == ["A/1", "C/3", "F/6"]
    assert R.exposed_codes("no codes here") == []
