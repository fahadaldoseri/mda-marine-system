#!/usr/bin/env python3
"""حارس ع-370: لا يسرّب مترجم الإنجليزية معرف تحذير من عقدة مجاورة.

الحالة الموجبة تفحص بطاقة ev-01 المبنية من مصدر 2026-10-30: يجب أن تحتوي
على 187-26 ولا تحتوي على 186-26. والحالة السالبة تحقن معرفًا خاطئًا عمدًا
وتثبت أن الحارس يرفضه برمز غير صفري.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def default_site() -> Path:
    configured = os.environ.get("SITE_DIR")
    if configured:
        return Path(configured).resolve()
    for candidate in (ROOT.parent / "seawatch", ROOT.parent / "site"):
        if candidate.is_dir():
            return candidate.resolve()
    return (ROOT.parent / "seawatch").resolve()


SITE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_site()
sys.path.insert(0, str(SITE / "generator"))
import i18n_en as I18N  # noqa: E402

DATE = "2026-10-30"
EV_RE = re.compile(r'<article[^>]*\bid="ev-01"[^>]*>.*?</article>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def event_one_text(html: str) -> str:
    match = EV_RE.search(html)
    if not match:
        raise AssertionError("لم توجد بطاقة #ev-01")
    return " ".join(TAG_RE.sub(" ", match.group(0)).split())


def assert_expected(html: str) -> None:
    text = event_one_text(html)
    if "187-26" not in text:
        raise AssertionError(f"وصف ev-01 لا يحوي 187-26: {text}")
    if "186-26" in text:
        raise AssertionError(f"وصف ev-01 يحوي معرفًا خاطئًا 186-26: {text}")


def main() -> int:
    source = SITE / "dist" / "reports" / f"{DATE}.html"
    if not source.is_file():
        print(f"✘ المصدر المبني غير موجود: {source}")
        return 2
    tm, glossary = I18N.build_tm(DATE), I18N.load_glossary()
    translated, missing, total = I18N.translate_page(
        source.read_text(encoding="utf-8"), DATE, tm, glossary
    )
    if missing:
        print(f"✘ نصوص عربية متبقية في اختبار المعرف: {len(set(missing))}")
        return 2
    try:
        assert_expected(translated)
    except AssertionError as exc:
        print(f"✘ الحالة الموجبة: {exc}")
        return 1
    print(f"✔ الحالة الموجبة: ev-01 يحوي 187-26 بلا 186-26 (عقود {total})")

    match = EV_RE.search(translated)
    assert match is not None
    bad_card = match.group(0).replace("187-26", "186-26", 1)
    bad_page = translated[: match.start()] + bad_card + translated[match.end() :]
    try:
        assert_expected(bad_page)
    except AssertionError as exc:
        print(f"✔ الحالة السالبة: الحارس رفض المعرف الخاطئ مغلقًا ({exc})")
        return 0
    print("✘ الحالة السالبة: مرّ معرف خاطئ — الحارس غير مغلق")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
