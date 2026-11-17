#!/usr/bin/env python3
"""اشتقاق http_status لسجل لا واقعة من ملف حالة التغذيات (قرار المالك 2026-11-17)."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
TOOL = B / "tools" / "derive_http_status.py"


def make(tmp: Path) -> Path:
    (tmp / "cumulative-2026" / "daily").mkdir(parents=True)
    (tmp / "feeds").mkdir()
    (tmp / "feeds" / "feeds-2026-03-01.status.json").write_text(json.dumps({"checked_feeds": [
        {"num": 1, "name": "UKMTO", "primary_url": "https://a.test/1", "ok": True, "via": "primary"},
        {"num": 2, "name": "IMO", "primary_url": "https://a.test/2", "ok": False,
         "block_reason": "primary: رفض الخادم الطلب (HTTP 401)"},
        {"num": 3, "name": "KUNA", "primary_url": "https://a.test/3", "ok": False, "block_reason": "timed out"},
    ]}), encoding="utf-8")
    rows = [{"no_incident": True, "retrieved_at": "2026-03-01T04:00:00Z", "sources_checked": [
        {"source": "UKMTO", "url": "https://a.test/1", "retrieved_at": "x"},
        {"source": "IMO", "url": "https://a.test/2", "retrieved_at": "x"},
        {"source": "KUNA", "url": "https://a.test/3", "retrieved_at": "x"},
    ]}]
    (tmp / "cumulative-2026" / "daily" / "2026-03-01.json").write_text(json.dumps(rows), encoding="utf-8")
    return tmp


def run(root: Path, *args: str):
    return subprocess.run([sys.executable, str(TOOL), "--root", str(root), "--date", "2026-03-01", *args],
                          text=True, capture_output=True, check=False)


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    root = make(tmp_path)
    before = (root / "cumulative-2026/daily/2026-03-01.json").read_text()
    result = run(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "cumulative-2026/daily/2026-03-01.json").read_text() == before


def test_apply_derives_and_marks(tmp_path: Path) -> None:
    root = make(tmp_path)
    result = run(root, "--apply")
    assert result.returncode == 0, result.stdout + result.stderr
    rows = json.loads((root / "cumulative-2026/daily/2026-03-01.json").read_text())
    got = [(s["http_status"], s["http_status_derived"]) for s in rows[0]["sources_checked"]]
    assert got == [(200, True), (401, True), (0, True)]
    assert "feeds-2026-03-01.status.json" in rows[0]["sources_checked"][0]["http_status_basis"]
    assert rows[0]["sources_checked"][2]["block_reason"] == "timed out"


def test_unmatched_source_fails_closed(tmp_path: Path) -> None:
    root = make(tmp_path)
    path = root / "cumulative-2026/daily/2026-03-01.json"
    rows = json.loads(path.read_text())
    rows[0]["sources_checked"].append({"source": "X", "url": "https://other.test", "retrieved_at": "x"})
    path.write_text(json.dumps(rows))
    assert run(root, "--apply").returncode == 2
    assert "http_status" not in json.loads(path.read_text())[0]["sources_checked"][0]


def test_existing_status_untouched(tmp_path: Path) -> None:
    root = make(tmp_path)
    path = root / "cumulative-2026/daily/2026-03-01.json"
    rows = json.loads(path.read_text())
    rows[0]["sources_checked"][0]["http_status"] = 204
    path.write_text(json.dumps(rows))
    assert run(root, "--apply").returncode == 0
    first = json.loads(path.read_text())[0]["sources_checked"][0]
    assert first["http_status"] == 204 and "http_status_derived" not in first


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
