#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B009 regression guard: no Python/template repr leaks and no uncovered Arabic."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import build_report  # noqa: E402
import i18n_en  # noqa: E402


def test_source_names_are_rendered_as_reader_text() -> None:
    event = {
        "sources": [
            {"name": "straits.live", "excerpt": "Iran Says Two Tankers Hit Mines"},
            {"name": "gCaptain", "excerpt": "Seafarer killed"},
        ],
        "source": "straits.live؛ gCaptain",
    }
    rendered = build_report._event_sources(event)
    assert rendered == "straits.live؛ gCaptain", rendered
    assert "{'name'" not in rendered
    assert "}" not in rendered


def test_template_artifact_guard_fails_closed() -> None:
    try:
        build_report.assert_no_template_artifacts("}؛", "source")
    except build_report.BuildError as exc:
        assert "قالب" in str(exc)
    else:
        raise AssertionError("template artifact was accepted")


def test_uncovered_arabic_text_remains_a_blocker() -> None:
    html = "<html><body><p>نص عربي غير مغطّى</p></body></html>"
    _, missing, _ = i18n_en.translate_page(html, "2026-11-07", {}, {})
    assert missing == ["نص عربي غير مغطّى"], missing


def test_today_event_sources_are_clean() -> None:
    path = ROOT / "sources" / "daily-events" / "2026-11-07.json"
    events = json.loads(path.read_text(encoding="utf-8"))
    for event in events:
        rendered = build_report._event_sources(event)
        build_report.assert_no_template_artifacts(rendered, "event source")
        assert "{'" not in rendered
        assert "}" not in rendered


if __name__ == "__main__":
    test_source_names_are_rendered_as_reader_text()
    test_template_artifact_guard_fails_closed()
    test_uncovered_arabic_text_remains_a_blocker()
    test_today_event_sources_are_clean()
    print("B009 template leak guard: PASS")
