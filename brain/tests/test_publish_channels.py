#!/usr/bin/env python3
"""عقد قنوات النشر: Pages أساسي، raw.githack عرض بديل، وraw.githubusercontent تحقق فقط."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from publish_channels import (  # noqa: E402
    build_publish_record,
    choose_channel,
    fallback_report_urls,
    preflight_exit_code,
    publish,
    verify_candidates,
    verify_live_response,
)


def ready(pages: str = "ready", githack: str = "ready") -> dict:
    return {
        "cloudflare-pages": {
            "state": pages,
            "reason": "test Pages",
            "presentation_eligible": True,
        },
        "raw-githack": {
            "state": githack,
            "reason": "test fallback",
            "presentation_eligible": True,
        },
        "raw.githubusercontent": {
            "state": "verification-only",
            "reason": "text/plain; verification only",
            "presentation_eligible": False,
        },
    }


def test_pages_is_selected_before_raw_githack() -> None:
    assert choose_channel(ready()) == "cloudflare-pages"


def test_raw_githack_is_selected_when_pages_is_down() -> None:
    assert choose_channel(ready(pages="down")) == "raw-githack"


def test_raw_github_is_never_selected_as_presentation_channel() -> None:
    statuses = ready(pages="down", githack="down")
    assert choose_channel(statuses) is None
    assert preflight_exit_code(statuses) == 2


def test_preflight_fails_closed_when_all_presentation_channels_are_down() -> None:
    assert preflight_exit_code(ready(pages="down", githack="down")) == 2


def test_d010_never_records_ok_without_verified_http_200() -> None:
    failed_live = verify_live_response(404, b"", "2026-11-07", "text/html")
    record = build_publish_record(
        date="2026-11-07",
        channel="cloudflare-pages",
        url="https://example.invalid/reports/2026-11-07",
        head="abc123",
        live=failed_live,
        rc=0,
    )
    assert record["status"] != "ok"
    assert record["rc"] != 0


def test_d020_requires_html_content_type_and_date_marker() -> None:
    assert verify_live_response(404, b"", "2026-11-07", "text/html")["ok"] is False
    assert verify_live_response(200, b"", "2026-11-07", "text/html")["ok"] is False
    assert verify_live_response(200, b"report 2026-11-06", "2026-11-07", "text/html")["ok"] is False
    assert verify_live_response(200, b"report 2026-11-07", "2026-11-07", "text/plain")["ok"] is False
    assert verify_live_response(200, b"<html>report 2026-11-07</html>", "2026-11-07", "text/html")["ok"] is True


def test_raw_github_is_recorded_as_verification_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urls = fallback_report_urls("2026-11-07")
    assert "raw.githack.com" in urls[0]
    assert "raw.githubusercontent.com" in urls[-1]
    assert len(urls) == 3

    def fake_verify(url: str, date: str, **kwargs: object) -> dict[str, object]:
        del date, kwargs
        if "raw.githubusercontent.com" in url:
            return {
                "ok": True,
                "status": 200,
                "bytes": 100,
                "date_marker": True,
                "content_type": "text/plain",
                "presentation_eligible": False,
                "url": url,
            }
        return {
            "ok": False,
            "status": 404,
            "bytes": 0,
            "date_marker": False,
            "content_type": "text/html",
            "presentation_eligible": True,
            "url": url,
        }

    monkeypatch.setattr("publish_channels.verify_live_url", fake_verify)
    rc, result = verify_candidates(urls, "2026-11-07")
    assert rc == 2
    assert result["status"] == "verification-only"
    assert result["successful_url"] is None
    assert result["verification_url"].endswith("2026-11-07.html")


def test_successful_pages_push_is_recorded_with_hash_and_redirect_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    date = "2026-11-07"
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / f"publish-channel-{date}.json").write_text(
        json.dumps({"channels": ready()}, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[int, str]:
        del kwargs
        if args[1].endswith("publish_site.sh"):
            (logs / f"publish-{date}.json").write_text(
                json.dumps({"status": "ok", "rc": 0, "head": "pages-head"}), encoding="utf-8"
            )
            return 0, "pushed Pages"
        raise AssertionError(args)

    def fake_verify_live_url(url: str, checked_date: str, **kwargs: object) -> dict[str, object]:
        assert checked_date == date
        assert "pages.dev" in url
        assert kwargs["min_bytes"] == 100_000
        return {
            "ok": True,
            "status": 200,
            "bytes": 189327,
            "date_marker": True,
            "content_type": "text/html; charset=utf-8",
            "presentation_eligible": True,
            "redirected": True,
            "redirects": [{"status": 308, "from": url, "to": f"{url}.html"}],
            "sha256": "835ad2e9723546d295389edefbce3f750a4ff228bb53a4b0c12e79953db02f02",
            "url": url,
        }

    monkeypatch.setattr("publish_channels.run_command", fake_run_command)
    monkeypatch.setattr("publish_channels.verify_live_url", fake_verify_live_url)
    assert publish(tmp_path, date) == 0
    record = json.loads((logs / f"publish-{date}.json").read_text(encoding="utf-8"))
    assert record["status"] == "ok"
    assert record["channel"] == "cloudflare-pages"
    assert record["head"] == "pages-head"
    assert record["live"]["status"] == 200
    assert record["live"]["redirects"][0]["status"] == 308
    assert record["attempts"][0]["channel"] == "cloudflare-pages"


def test_failed_pages_push_falls_back_to_raw_githack(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    date = "2026-11-07"
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / f"publish-channel-{date}.json").write_text(
        json.dumps({"channels": ready()}, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[int, str]:
        del kwargs
        if args[1].endswith("publish_site.sh"):
            (logs / f"publish-{date}.json").write_text(
                json.dumps({"status": "failed", "rc": 2, "head": "pages-head"}), encoding="utf-8"
            )
            return 2, "Pages unavailable"
        if args[1].endswith("publish_fallback.sh"):
            (logs / f"publish-{date}-fallback.json").write_text(
                json.dumps({
                    "status": "ok", "rc": 0, "head": "fallback-head",
                    "urls": fallback_report_urls(date),
                    "content_sha256": "fallback-fingerprint",
                }), encoding="utf-8"
            )
            return 0, "fallback pushed"
        raise AssertionError(args)

    def fake_verify_live_url(url: str, checked_date: str, **kwargs: object) -> dict[str, object]:
        del kwargs
        assert checked_date == date
        if "pages.dev" in url:
            return {"ok": False, "status": 503, "bytes": 0, "date_marker": False, "url": url}
        if "raw.githack.com" in url:
            return {
                "ok": True,
                "status": 200,
                "bytes": 189327,
                "date_marker": True,
                "content_type": "text/html; charset=utf-8",
                "presentation_eligible": True,
                "url": url,
            }
        return {"ok": False, "status": 404, "bytes": 0, "date_marker": False, "url": url}

    monkeypatch.setattr("publish_channels.run_command", fake_run_command)
    monkeypatch.setattr("publish_channels.verify_live_url", fake_verify_live_url)
    assert publish(tmp_path, date) == 0
    record = json.loads((logs / f"publish-{date}.json").read_text(encoding="utf-8"))
    assert record["status"] == "ok"
    assert record["channel"] == "raw-githack"
    assert record["head"] == "fallback-head"
    assert record["attempts"][0]["channel"] == "cloudflare-pages"
    assert record["attempts"][0]["status"] == "failed"
    assert record["attempts"][1]["channel"] == "raw-githack"


if __name__ == "__main__":
    pytest.main([__file__])
