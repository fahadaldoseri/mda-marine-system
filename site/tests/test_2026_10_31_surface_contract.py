#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات عقد العرض للإصدار 2026-10-31.

هذه الاختبارات تقارن السطح المبني بالمصدر الحاكم، ولا تكتب في dist.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAIN_ROOT = Path(__import__("os").environ.get("BRAIN_DIR") or ROOT.parent / "brain-marine-news")
AR = ROOT / "dist" / "reports" / "2026-10-31.html"
EN = ROOT / "dist" / "reports" / "en" / "2026-10-31.html"
ZONES = ROOT / "sources" / "zones" / "2026-10-31.json"

sys.path.insert(0, str(BRAIN_ROOT))
from validators.check_zone_strip import validate_zone_strip  # noqa: E402


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


class _ClassText(HTMLParser):
    def __init__(self, class_name: str):
        super().__init__(convert_charrefs=True)
        self.class_name = class_name
        self.depth = 0
        self.parts: list[str] = []
        self.items: list[str] = []
        self._item_depth = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if self._item_depth is not None:
            self.depth += 1
        if self.class_name in classes and self._item_depth is None:
            self._item_depth = self.depth
            self.parts = []
        self.depth += 1

    def handle_endtag(self, tag):
        self.depth -= 1
        if self._item_depth is not None and self.depth == self._item_depth:
            self.items.append(_norm(" ".join(self.parts)))
            self.parts = []
            self._item_depth = None

    def handle_data(self, data):
        if self._item_depth is not None:
            self.parts.append(data)


def class_texts(html: str, class_name: str) -> list[str]:
    parser = _ClassText(class_name)
    parser.feed(html)
    return parser.items


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "template"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "template"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth == 0 and data.strip():
            self.parts.append(data)


def visible_text(html: str) -> str:
    parser = _VisibleText()
    parser.feed(html)
    return _norm(" ".join(parser.parts))


class _ReleaseChipText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.meta_depth: int | None = None
        self.capture_depth: int | None = None
        self.parts: list[str] = []
        self.items: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        depth = len(self.stack)
        classes = set((attrs.get("class") or "").split())
        if "masthead-meta" in classes:
            self.meta_depth = depth
        if (
            self.capture_depth is None
            and self.meta_depth is not None
            and tag == "span"
            and "chip" in classes
            and depth == self.meta_depth + 1
        ):
            self.capture_depth = depth
            self.parts = []
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()
        if self.capture_depth is not None and len(self.stack) == self.capture_depth:
            text = _norm(" ".join(self.parts))
            if text.startswith("رقم الإصدار") or text.startswith("Release number"):
                self.items.append(text)
            self.capture_depth = None
            self.parts = []
        if self.meta_depth is not None and len(self.stack) == self.meta_depth:
            self.meta_depth = None

    def handle_data(self, data):
        if self.capture_depth is not None:
            self.parts.append(data)


def release_chip_texts(html: str) -> list[str]:
    parser = _ReleaseChipText()
    parser.feed(html)
    return parser.items


def require(cond: bool, message: str):
    if not cond:
        raise AssertionError(message)


def run():
    require(AR.is_file(), f"missing {AR}")
    require(EN.is_file(), f"missing {EN}")
    zones = json.loads(ZONES.read_text(encoding="utf-8"))
    for path, lang in ((AR, "ar"), (EN, "en")):
        html = path.read_text(encoding="utf-8")
        if lang == "ar":
            require("31 أكتوبر 2026 · 04:00 حسب التوقيت العالمي" in html,
                    "Arabic human-readable update timestamp is missing")
            release_chips = release_chip_texts(html)
            require(release_chips == ["رقم الإصدار 31/10/26"],
                    f"Arabic release number chip is not normalized: {release_chips}")
            labels = class_texts(html, "sc-l")
            require("خلال 24 ساعة السابقة" in labels,
                    "approved first news-card branch label is missing")
            require("التحذيرات والنشرات الرسمية النشطة" in labels,
                    "approved second news-card branch label is missing")
            require("ما تغيّر" not in labels and "التوجيهات التشغيلية" not in labels,
                    "deprecated news-card branch label remains")
            zone_errors = validate_zone_strip(html, zones)
            require(not zone_errors, "sector strip contract failed: " + " · ".join(zone_errors))
        else:
            require("31 October 2026 · 04:00 UTC" in html,
                    "English human-readable update timestamp is missing")
            release_chips = release_chip_texts(html)
            require(release_chips == ["Release number 31/10/26"],
                    f"English release number chip is not normalized: {release_chips}")
            labels = class_texts(html, "sc-l")
            require("During the previous 24 hours" in labels,
                    "English approved first news-card branch label is missing")
            require("Active official warnings and advisories" in labels,
                    "English approved second news-card branch label is missing")
            require("What changed" not in labels and "Operational Guidance" not in labels,
                    "deprecated English news-card branch label remains")
            require(not re.search(r"[\u0600-\u06ff]", visible_text(html)),
                    "Arabic text leaked into English surface")
    print("surface contract: PASS")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as exc:
        print(f"surface contract: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
