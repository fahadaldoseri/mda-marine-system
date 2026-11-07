#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس مواءمة المتن الإنجليزي مع المتن العربي الحاكم."""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
import i18n_en as I  # noqa: E402

DATE = os.environ.get("I18N_DATE", "2026-11-02")
BRAIN = Path(
    os.environ.get("BRAIN_DIR")
    or os.environ.get("BRAIN")
    or (ROOT.parent / "brain-marine-news")
)
AR_SOURCE = BRAIN / "reports" / f"{DATE}-sectioned.md"
EN_SOURCE = ROOT / "sources" / "i18n" / "en" / f"{DATE}-sectioned.en.md"


@contextlib.contextmanager
def _with_tm_paths(ar_dir: Path, en_dir: Path):
    old_ar, old_i18n = I.AR_MD, I.I18N
    I.AR_MD, I.I18N = ar_dir, en_dir
    try:
        yield
    finally:
        I.AR_MD, I.I18N = old_ar, old_i18n


def _run_build_tm(ar_dir: Path, en_dir: Path, date: str):
    with _with_tm_paths(ar_dir, en_dir):
        return I.build_tm(date)


def test_real_report_alignment_is_accepted() -> None:
    tm = I.build_tm(DATE)
    assert tm["درجة الثقة: متوسطة."] == "Confidence level: medium."


def test_2026_11_07_sector_level_lines_have_english_pairs() -> None:
    expected = {
        "المستوى في مضيق هرمز وخليج عُمان والخليج العربي: مرتفع":
            "Level in the Strait of Hormuz, the Gulf of Oman and the Arabian Gulf: High",
        "المستوى في باب المندب والبحر الأحمر: منخفض":
            "Level in the Bab al-Mandab and the Red Sea: Low",
        "المستوى في بحر العرب: منخفض": "Level in the Arabian Sea: Low",
        "المستوى في القرن الأفريقي: متوسط": "Level in the Horn of Africa: Moderate",
        "المستوى في المحيط الهندي: منخفض": "Level in the Indian Ocean: Low",
    }
    with _with_tm_paths(BRAIN / "reports", ROOT / "sources" / "i18n" / "en"):
        tm = I.build_tm("2026-11-07")
    for arabic, english in expected.items():
        assert tm[arabic] == english


def test_deleted_line_in_temp_copy_fails_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="i18n-align-delete-") as raw:
        root = Path(raw)
        ar_dir, en_dir = root / "ar", root / "en"
        ar_dir.mkdir()
        en_dir.mkdir()
        ar_lines = AR_SOURCE.read_text(encoding="utf-8").splitlines()
        en_lines = EN_SOURCE.read_text(encoding="utf-8").splitlines()
        en_lines.pop(3)
        (ar_dir / "x-sectioned.md").write_text("\n".join(ar_lines) + "\n", encoding="utf-8")
        (en_dir / "x-sectioned.en.md").write_text("\n".join(en_lines) + "\n", encoding="utf-8")
        try:
            _run_build_tm(ar_dir, en_dir, "x")
        except SystemExit as exc:
            ar_n = len([x for x in ar_lines if x.strip()])
            en_n = len([x for x in en_lines if x.strip()])
            assert f"عربي={ar_n} إنجليزي={en_n}" in str(exc), str(exc)
        else:
            raise AssertionError("حارس العدد لم يمنع حذف سطر في النسخة المؤقتة")


def test_equal_count_but_wrong_line_kind_fails_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="i18n-align-kind-") as raw:
        root = Path(raw)
        ar_dir, en_dir = root / "ar", root / "en"
        ar_dir.mkdir()
        en_dir.mkdir()
        (ar_dir / "x-sectioned.md").write_text(
            "# عنوان\n| أ | ب |\n|---|---|\n", encoding="utf-8"
        )
        (en_dir / "x-sectioned.en.md").write_text(
            "# Title\nPlain text\n|---|---|\n", encoding="utf-8"
        )
        try:
            _run_build_tm(ar_dir, en_dir, "x")
        except SystemExit as exc:
            assert "أنواع الأسطر غير متطابقة" in str(exc), str(exc)
        else:
            raise AssertionError("حارس النوع لم يمنع اختلاف النوع مع تساوي العدد")


if __name__ == "__main__":
    tests = [
        test_real_report_alignment_is_accepted,
        test_2026_11_07_sector_level_lines_have_english_pairs,
        test_deleted_line_in_temp_copy_fails_closed,
        test_equal_count_but_wrong_line_kind_fails_closed,
    ]
    for test in tests:
        test()
        print(f"{test.__name__}: PASS")
    print("i18n alignment guard: PASS")
