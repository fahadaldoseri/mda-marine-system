#!/usr/bin/env python3
"""عقد القنوات الثنائية: يُشغّل RED قبل التنفيذ ثم GREEN بعده."""
from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from publish_channels import (  # noqa: E402
    build_publish_record,
    choose_channel,
    manus_readiness,
    preflight_exit_code,
    publish,
    verify_live_response,
)


def ready(primary: str = "ready", fallback: str = "ready") -> dict:
    return {
        "manus": {"state": primary, "reason": "test"},
        "github-pages": {"state": fallback, "reason": "test"},
    }


def test_primary_ready_is_selected_first() -> None:
    assert choose_channel(ready()) == "manus"


def test_fallback_is_selected_when_primary_is_down() -> None:
    assert choose_channel(ready(primary="down")) == "github-pages"


def test_preflight_fails_closed_when_both_channels_are_down() -> None:
    assert preflight_exit_code(ready(primary="down", fallback="down")) == 2


def test_d010_never_records_ok_without_verified_http_200() -> None:
    failed_live = verify_live_response(404, b"", "2026-11-07")
    record = build_publish_record(
        date="2026-11-07",
        channel="manus",
        url="https://example.invalid/reports/2026-11-07.html",
        head="abc123",
        live=failed_live,
        rc=0,
    )
    assert record["status"] != "ok"
    assert record["rc"] != 0


def test_d020_fails_closed_for_404_or_empty_body() -> None:
    assert verify_live_response(404, b"", "2026-11-07")["ok"] is False
    assert verify_live_response(200, b"", "2026-11-07")["ok"] is False
    assert verify_live_response(200, b"report 2026-11-06", "2026-11-07")["ok"] is False
    assert verify_live_response(200, b"report 2026-11-07", "2026-11-07")["ok"] is True


def test_addon_failure_overrides_successful_manus_webdev_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    """تحدٍّ: نجاح سجل المشروع لا يتغلب على فشل إضافة webdev نفسها."""
    calls: list[list[str]] = []
    addon_error = (
        "Error: failed to list tools: failed to get connection: "
        "addon workspace recovery has not completed"
    )

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[int, str]:
        calls.append(args)
        if args[:2] == ["manus-mcp-cli", "tool"]:
            return 1, addon_error
        if args[0] == "manus-webdev-logs":
            return 0, "latest log entry: ready"
        raise AssertionError(args)

    monkeypatch.setattr("publish_channels.run_command", fake_run_command)
    result = manus_readiness()
    assert result["state"] == "down"
    assert "addon workspace recovery has not completed" in result["reason"]
    assert calls == [["manus-mcp-cli", "tool", "list", "--server", "webdev-mcp"]]


def test_successful_manus_push_with_live_404_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """دفع Manus الناجح جزئي فقط؛ 404 الحي يجب أن يفعّل القناة البديلة."""
    date = "2026-11-07"
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / f"publish-channel-{date}.json").write_text(
        '{"channels": {"manus": {"state": "ready"}, "github-pages": {"state": "ready"}}}\n',
        encoding="utf-8",
    )

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[int, str]:
        del kwargs
        if args[1].endswith("publish_site.sh"):
            (logs / f"publish-{date}.json").write_text(
                '{"status": "ok", "rc": 0, "head": "manus-head"}\n', encoding="utf-8"
            )
            return 0, "✔ pushed Manus HEAD:main"
        if args[1].endswith("publish_fallback.sh"):
            (logs / f"publish-{date}-fallback.json").write_text(
                '{"status": "ok", "rc": 0, "head": "fallback-head", '
                '"url": "https://raw.githack.com/fahadaldoseri/seawatch-live/main/reports/'
                f'{date}.html", "content_sha256": "fallback-fingerprint"}}\n',
                encoding="utf-8",
            )
            return 0, "✔ fallback pushed"
        raise AssertionError(args)

    def fake_verify_live_url(url: str, checked_date: str) -> dict[str, object]:
        assert checked_date == date
        if "manus.space" in url:
            return {"ok": False, "status": 404, "bytes": 0, "date_marker": False,
                    "reason": "http=404; bytes=0; date_marker=false", "url": url}
        return {"ok": True, "status": 200, "bytes": 189327, "date_marker": True,
                "reason": "ok", "url": url}

    monkeypatch.setattr("publish_channels.run_command", fake_run_command)
    monkeypatch.setattr("publish_channels.verify_live_url", fake_verify_live_url)
    monkeypatch.setenv("LIVE_BASE_URL", "https://seawatch-xp4qirmr.manus.space")

    assert publish(tmp_path, date) == 0
    record = json.loads((logs / f"publish-{date}.json").read_text(encoding="utf-8"))
    assert record["status"] == "ok"
    assert record["channel"] == "github-pages"
    assert record["head"] == "fallback-head"
    assert record["live"]["status"] == 200
    assert record["attempts"][0]["channel"] == "manus"
    assert record["attempts"][0]["status"] == "failed"
    assert record["attempts"][0]["live"]["status"] == 404
