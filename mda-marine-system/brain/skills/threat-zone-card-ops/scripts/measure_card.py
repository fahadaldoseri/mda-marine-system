#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure the rendered threat-zone card on a live or local report page.

The script intentionally measures the visible screen card separately from the
print card. It uses Playwright so height, overflow, and print visibility are
computed by a real browser rather than inferred from source HTML.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError as exc:  # pragma: no cover - environment contract
    print(f"FAIL: Playwright is required: {exc}")
    raise SystemExit(2)

ALLOWED_LEVELS = ("حرج", "مرتفع جدًا", "مرتفع", "متوسط", "منخفض")
DEFAULT_URL = "https://seawatch-xp4qirmr.manus.space/reports/2026-10-30.html"


class MeasurementFailure(RuntimeError):
    """A fail-closed measurement contract violation."""


def _source_url(args: argparse.Namespace) -> str:
    if args.file:
        path = pathlib.Path(args.file).expanduser().resolve()
        if not path.is_file():
            raise MeasurementFailure(f"file not found: {path}")
        return path.as_uri()
    return args.url


def _goto(page: Any, url: str, timeout_ms: int) -> None:
    # networkidle is deliberately not used: live report pages may retain
    # analytics/telemetry connections after the report DOM is complete.
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(350)


def _screen_measure(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const card = document.querySelector('section.tz.tz-screen')
            || [...document.querySelectorAll('section.tz')].find(e => {
              const r = e.getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            });
          if (!card) return {error: 'visible threat-zone card not found'};
          const rows = [...card.querySelectorAll('.tz-z')];
          const heights = rows.map(e => e.getBoundingClientRect().height);
          const levels = ['حرج', 'مرتفع جدًا', 'مرتفع', 'متوسط', 'منخفض'];
          const levelOf = (text) => levels.find(level => text.includes(level)) || null;
          const badge = card.querySelector('.tz-badge');
          const rowLevels = rows.map(e => levelOf(e.innerText || ''));
          const overall = levelOf(badge ? badge.innerText : '');
          const rank = Object.fromEntries(levels.map((level, i) => [level, levels.length - i]));
          const top = rowLevels.filter(Boolean).sort((a, b) => rank[b] - rank[a])[0] || null;
          return {
            rows: rows.length,
            heights,
            min_height_px: heights.length ? Math.min(...heights) : 0,
            overall_level: overall,
            row_levels: rowLevels,
            top_zone_level: top,
            overall_matches_top: Boolean(overall && top && overall === top),
            excess_px: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
            no_change_label: (card.innerText || '').includes('= بلا تغير'),
            window_label: (card.innerText || '').includes('خلال 24 ساعة السابقة'),
            style_leak: (document.body.innerText || '').includes('.tz{')
          };
        }"""
    )


def _print_measure(page: Any) -> dict[str, Any]:
    page.emulate_media(media="print")
    return page.evaluate(
        """() => {
          const card = document.querySelector('section.tz.tz-print')
            || [...document.querySelectorAll('section.tz')].find(e => {
              const r = e.getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            });
          const basis = card && card.querySelector('.tz-basis');
          const basisText = basis ? (basis.innerText || '') : '';
          const styleNodes = [...document.querySelectorAll('style')];
          const styleLeak = styleNodes.some(style => {
            const r = style.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          });
          return {
            print_card_found: Boolean(card),
            print_basis: Boolean(
              basis &&
              basis.open &&
              getComputedStyle(basis).display !== 'none' &&
              basis.getBoundingClientRect().height > 0 &&
              basisText.includes('أساس التقدير')
            ),
            print_style_leak: styleLeak,
          };
        }"""
    )


def _measure(url: str, timeout_ms: int, min_height: float) -> dict[str, Any]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            desktop = browser.new_page(viewport={"width": 1280, "height": 900})
            _goto(desktop, url, timeout_ms)
            screen = _screen_measure(desktop)
            if screen.get("error"):
                raise MeasurementFailure(screen["error"])
            printed = _print_measure(desktop)

            mobile = browser.new_page(viewport={"width": 390, "height": 900})
            _goto(mobile, url, timeout_ms)
            mobile_screen = _screen_measure(mobile)
        finally:
            browser.close()

    result = {
        **screen,
        "mobile_min_height_px": mobile_screen.get("min_height_px", 0),
        "print_basis": printed.get("print_basis", False),
        "print_style_leak": printed.get("print_style_leak", False),
        "min_height_threshold_px": min_height,
    }
    failures: list[str] = []
    if result["rows"] != 4:
        failures.append(f"rows={result['rows']} (expected 4)")
    if result["min_height_px"] < min_height:
        failures.append(f"min_height_px={result['min_height_px']:.2f} < {min_height:.2f}")
    if result["mobile_min_height_px"] < min_height:
        failures.append(f"mobile_min_height_px={result['mobile_min_height_px']:.2f} < {min_height:.2f}")
    if result["excess_px"] > 0:
        failures.append(f"excess_px={result['excess_px']} (expected 0)")
    if not result["print_basis"]:
        failures.append("print_basis=no")
    if result.get("print_style_leak") or result.get("style_leak"):
        failures.append("style_leak=yes")
    if result.get("no_change_label"):
        failures.append("no_change_label=yes")
    if not result.get("window_label"):
        failures.append("window_label=missing")
    if result.get("overall_level") not in ALLOWED_LEVELS:
        failures.append(f"overall_level={result.get('overall_level')!r} (outside scale)")
    if result.get("top_zone_level") not in ALLOWED_LEVELS:
        failures.append(f"top_zone_level={result.get('top_zone_level')!r} (outside scale)")
    if not result.get("overall_matches_top"):
        failures.append("overall_matches_top=no")
    result["failures"] = failures
    return result


def _print_result(url: str, result: dict[str, Any]) -> None:
    print(f"source={url}")
    print(f"rows={result.get('rows')}")
    print(f"min_height_px={result.get('min_height_px', 0):.2f}")
    print(f"mobile_min_height_px={result.get('mobile_min_height_px', 0):.2f}")
    print(f"excess_px={result.get('excess_px')}")
    print(f"print_basis={'yes' if result.get('print_basis') else 'no'}")
    print(f"print_style_leak={'yes' if result.get('print_style_leak') else 'no'}")
    print(f"overall_level={result.get('overall_level')}")
    print(f"top_zone_level={result.get('top_zone_level')}")
    print(f"overall_matches_top={'yes' if result.get('overall_matches_top') else 'no'}")
    if result.get("failures"):
        print("status=FAIL")
        for failure in result["failures"]:
            print(f"failure={failure}")
    else:
        print("status=PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="قياس حي لبطاقة مستوى التهديد بالقطاعات")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--url", default=DEFAULT_URL, help="رابط صفحة الإصدار")
    source.add_argument("--file", help="ملف HTML محلي")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--min-height", type=float, default=44.0)
    args = parser.parse_args()
    url = _source_url(args)
    try:
        result = _measure(url, args.timeout_ms, args.min_height)
        _print_result(url, result)
        return 0 if not result["failures"] else 2
    except (MeasurementFailure, PlaywrightError) as exc:
        print(f"source={url}")
        print(f"status=FAIL")
        print(f"failure={exc}")
        return 2
    except Exception as exc:  # fail closed for unexpected browser/runtime errors
        print(f"source={url}")
        print("status=FAIL")
        print(f"failure=unexpected: {exc}")
        return 70


if __name__ == "__main__":
    sys.exit(main())
