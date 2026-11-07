#!/usr/bin/env python3
"""Two-channel publishing contracts for S085, D010 and D020.

The existing Manus publisher remains the first channel.  This module owns only
readiness, live verification, deterministic fingerprints, and orchestration.
It never stores credentials; GitHub authentication is delegated to ``gh``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

DEFAULT_REPO = "fahadaldoseri/seawatch-live"
DEFAULT_BRANCH = "main"
GITHACK_BASE = "https://raw.githack.com"
JSDELIVR_BASE = "https://cdn.jsdelivr.net/gh"
LIVE_VERIFY_WINDOW_SECONDS = 90
LIVE_VERIFY_INTERVAL_SECONDS = 3


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_command(args: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def verify_live_response(status: int, body: bytes, date: str) -> dict[str, Any]:
    """Return a strict live-page verdict; 200 alone is never sufficient."""
    marker = date.encode("utf-8") in body
    ok = status == 200 and bool(body) and marker
    reason = "ok" if ok else f"http={status}; bytes={len(body)}; date_marker={str(marker).lower()}"
    return {"ok": ok, "status": int(status), "bytes": len(body), "date_marker": marker, "reason": reason}


def verify_live_url(url: str, date: str, *, opener: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Poll a live release for a bounded window; never infer success from a push."""
    opener = opener or urllib.request.urlopen
    window = max(0, int(os.environ.get("SEAWATCH_LIVE_VERIFY_WINDOW_SECONDS", str(LIVE_VERIFY_WINDOW_SECONDS))))
    interval = max(0, int(os.environ.get("SEAWATCH_LIVE_VERIFY_INTERVAL_SECONDS", str(LIVE_VERIFY_INTERVAL_SECONDS))))
    started = time.monotonic()
    attempts = 0
    verdict: dict[str, Any] = verify_live_response(0, b"", date)
    while True:
        attempts += 1
        request = urllib.request.Request(url, headers={"User-Agent": "seawatch-publish-contract"})
        try:
            with opener(request, timeout=min(30, max(1, window or 1))) as response:
                body = response.read()
                verdict = verify_live_response(int(response.status), body, date)
        except urllib.error.HTTPError as exc:
            verdict = verify_live_response(int(exc.code), b"", date)
        except Exception as exc:  # network failures are a closed failure, not a guessed success
            verdict = verify_live_response(0, b"", date)
            verdict["reason"] = f"request-error={exc}"
        verdict["url"] = url
        verdict["attempts"] = attempts
        verdict["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if verdict["ok"] or window == 0 or time.monotonic() - started >= window:
            return verdict
        remaining = window - (time.monotonic() - started)
        time.sleep(min(interval, max(0.0, remaining)))


def content_fingerprint(dist: Path) -> str:
    """Hash sorted relative paths, sizes and file hashes under ``dist``."""
    h = hashlib.sha256()
    if not dist.is_dir():
        return h.hexdigest()
    for path in sorted(p for p in dist.rglob("*") if p.is_file()):
        rel = path.relative_to(dist).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        h.update(f"{rel}\0{path.stat().st_size}\0{digest}\n".encode("utf-8"))
    return h.hexdigest()


def _status(state: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"state": state, "reason": reason, **extra}


def fallback_urls(date: str, repo: str = DEFAULT_REPO, branch: str = DEFAULT_BRANCH) -> list[str]:
    """Return public raw.githack/jsDelivr candidate URLs for the release."""
    owner, name = repo.split("/", 1)
    githack = f"{GITHACK_BASE}/{owner}/{name}/{branch}"
    jsdelivr = f"{JSDELIVR_BASE}/{owner}/{name}@{branch}"
    previous = date.replace("-07", "-06") if date.endswith("-07") else date
    return [
        f"{githack}/",
        f"{githack}/reports/{date}.html",
        f"{githack}/reports/{previous}.html",
        f"{jsdelivr}/",
        f"{jsdelivr}/reports/{date}.html",
        f"{jsdelivr}/reports/{previous}.html",
    ]


def manus_readiness() -> dict[str, Any]:
    """Probe the Manus add-on itself; project logs are never a readiness authority."""
    rc, output = run_command(["manus-mcp-cli", "tool", "list", "--server", "webdev-mcp"])
    if rc != 0:
        reason = output[-500:] or f"manus-mcp-cli rc={rc}"
        if "addon workspace recovery has not completed" in output.lower():
            reason = "addon workspace recovery has not completed"
        return _status("down", reason, probe="manus-mcp-cli tool list --server webdev-mcp", probe_rc=rc)
    return _status(
        "ready",
        "manus-mcp-cli tool list --server webdev-mcp succeeded",
        probe="manus-mcp-cli tool list --server webdev-mcp",
        probe_rc=0,
    )


def github_pages_readiness(repo: str = DEFAULT_REPO) -> dict[str, Any]:
    """Check the public fallback repository, not the unavailable Pages API."""
    gh_env = dict(os.environ, GH_FORCE_TTY="0", NO_COLOR="1")
    rc, output = run_command(["gh", "auth", "status", "--hostname", "github.com"], env=gh_env)
    if rc != 0:
        return _status("down", f"gh auth status rc={rc}: {output[-500:]}", auth_rc=rc)
    rc, repo_output = run_command(["gh", "repo", "view", repo, "--json", "nameWithOwner,defaultBranchRef,url,visibility"], env=gh_env)
    if rc != 0:
        return _status("down", f"repository unavailable rc={rc}: {repo_output[-500:]}", auth_rc=0, repo_rc=rc)
    try:
        repo_doc = json.loads(repo_output)
    except json.JSONDecodeError:
        return _status("down", "repository metadata returned non-JSON output", auth_rc=0, repo_rc=0)
    visibility = str(repo_doc.get("visibility", "")).upper()
    if visibility != "PUBLIC":
        return _status("down", f"fallback repository visibility={visibility or 'unknown'}, expected PUBLIC", auth_rc=0, repo_rc=0, visibility=visibility)
    branch = ((repo_doc.get("defaultBranchRef") or {}).get("name") or "")
    if not branch:
        return _status("down", "fallback repository has no committed default branch", auth_rc=0, repo_rc=0, visibility=visibility)
    if branch != DEFAULT_BRANCH:
        return _status("down", f"fallback repository default branch={branch!r}, expected {DEFAULT_BRANCH!r}", auth_rc=0, repo_rc=0, visibility=visibility, branch=branch)
    return _status(
        "ready",
        "public fallback repository is available; raw.githack/jsDelivr serve its root",
        auth_rc=0,
        repo_rc=0,
        visibility=visibility,
        branch=branch,
        repo=repo,
    )


def preflight(root: Path, date: str, repo: str = DEFAULT_REPO) -> tuple[int, dict[str, Any]]:
    manus = manus_readiness()
    pages = github_pages_readiness(repo)
    doc = {"date": date, "at": utc_now(), "channels": {"manus": manus, "github-pages": pages}}
    doc["status"] = "ready" if any(x["state"] == "ready" for x in (manus, pages)) else "down"
    doc["rc"] = 0 if doc["status"] == "ready" else 2
    out = root / "logs" / f"publish-channel-{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(doc["rc"]), doc


def choose_channel(statuses: dict[str, dict[str, Any]]) -> str | None:
    for channel in ("manus", "github-pages"):
        if statuses.get(channel, {}).get("state") == "ready":
            return channel
    return None


def preflight_exit_code(statuses: dict[str, dict[str, Any]]) -> int:
    return 0 if choose_channel(statuses) else 2


def build_publish_record(*, date: str, channel: str, url: str, head: str, live: dict[str, Any], rc: int, fingerprint: str | None = None, urls: list[str] | None = None) -> dict[str, Any]:
    verified = bool(rc == 0 and live.get("ok") is True)
    record: dict[str, Any] = {
        "date": date,
        "channel": channel,
        "url": url,
        "head": head,
        "rc": 0 if verified else (int(rc) if int(rc) != 0 else 2),
        "status": "ok" if verified else "failed",
        "live": live,
        "at": utc_now(),
    }
    if urls:
        record["urls"] = urls
    if fingerprint:
        record["content_sha256"] = fingerprint
    return record


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _base_url(report_url: str) -> str:
    marker = "/reports/"
    return report_url.split(marker, 1)[0].rstrip("/") if marker in report_url else report_url.rstrip("/")


def _write_publish(root: Path, date: str, record: dict[str, Any]) -> None:
    path = root / "logs" / f"publish-{date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish(root: Path, date: str, repo: str = DEFAULT_REPO) -> int:
    preflight_path = root / "logs" / f"publish-channel-{date}.json"
    statuses = _read_json(preflight_path).get("channels", {})
    if not statuses:
        rc, preflight_doc = preflight(root, date, repo)
        statuses = preflight_doc["channels"]
        if rc != 0:
            return rc
    selected = choose_channel(statuses)
    if not selected:
        _write_publish(root, date, {"date": date, "status": "failed", "rc": 2, "channel": None, "url": None, "head": None, "why": "both channels down", "at": utc_now()})
        return 2

    attempts: list[dict[str, Any]] = []
    channel_states: dict[str, dict[str, Any]] = {
        name: {"state": value.get("state"), "reason": value.get("reason", "")}
        for name, value in statuses.items()
    }
    for channel in (selected, "github-pages" if selected == "manus" else None):
        if channel is None:
            break
        if statuses.get(channel, {}).get("state") != "ready":
            continue
        if channel == "manus":
            rc, output = run_command(["bash", str(root / "tools" / "publish_site.sh"), date], cwd=root, env=dict(os.environ, BRAIN_DIR=str(root)))
            publish_doc = _read_json(root / "logs" / f"publish-{date}.json")
            head = publish_doc.get("head") or ""
            site = Path(os.environ.get("SITE_DIR", str(root.parent / "seawatch")))
            base = os.environ.get("LIVE_BASE_URL")
            if not base:
                try:
                    base = json.loads((site / "sources" / "site.json").read_text(encoding="utf-8")).get("base_url", "")
                except (OSError, json.JSONDecodeError):
                    base = ""
            url = f"{base.rstrip('/')}/reports/{date}.html" if base else ""
            live = verify_live_url(url, date) if url else verify_live_response(0, b"", date)
            if not url:
                live["reason"] = "Manus live base URL unavailable"
            record = build_publish_record(date=date, channel=channel, url=url, head=head, live=live, rc=rc)
            record["manus_output_tail"] = output[-1000:]
            attempts.append(record)
            if record["status"] == "ok":
                channel_states["manus"] = {"state": "ready", "reason": "live HTTP 200 verified", "live": live}
                record["channels"] = channel_states
                record["attempts"] = [{"channel": x.get("channel"), "status": x.get("status"), "live": x.get("live")} for x in attempts]
                _write_publish(root, date, record)
                return 0
            # Ensure stale Manus status=ok can never survive a failed live check.
            channel_states["manus"] = {"state": "down", "reason": live.get("reason", "live verification failed"), "live": live}
            record["channel_state"] = channel_states["manus"]
            _write_publish(root, date, record)
        else:
            rc, output = run_command(["bash", str(root / "tools" / "publish_fallback.sh"), date], cwd=root, env=dict(os.environ, BRAIN_DIR=str(root)))
            fallback = _read_json(root / "logs" / f"publish-{date}-fallback.json")
            url = fallback.get("url") or (fallback.get("urls") or [""])[0]
            head = fallback.get("head") or ""
            live = verify_live_url(url, date)
            record = build_publish_record(date=date, channel=channel, url=url, head=head, live=live, rc=rc, fingerprint=fallback.get("content_sha256"), urls=fallback.get("urls"))
            record["fallback_output_tail"] = output[-1000:]
            attempts.append(record)
            channel_states["github-pages"] = {"state": "ready" if record["status"] == "ok" else "down", "reason": live.get("reason", "live verification failed"), "live": live}
            _write_publish(root, date, record)
            if record["status"] == "ok":
                record["channels"] = channel_states
                record["attempts"] = [{"channel": x.get("channel"), "status": x.get("status"), "live": x.get("live")} for x in attempts]
                _write_publish(root, date, record)
                return 0
    final = attempts[-1] if attempts else {"date": date, "channel": None, "url": None, "head": None, "rc": 2, "status": "failed", "at": utc_now()}
    final["channels"] = channel_states
    final["attempts"] = [{"channel": x.get("channel"), "status": x.get("status"), "live": x.get("live")} for x in attempts]
    _write_publish(root, date, final)
    return int(final.get("rc", 2)) or 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seawatch two-channel publishing contracts")
    parser.add_argument("command", choices=("preflight", "publish"))
    parser.add_argument("--date", required=True)
    parser.add_argument("--root", default=os.environ.get("BRAIN_DIR", str(Path(__file__).resolve().parents[1])))
    parser.add_argument("--repo", default=DEFAULT_REPO)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "preflight":
        rc, doc = preflight(root, args.date, args.repo)
        for name, state in doc["channels"].items():
            print(f"{name}: {state['state']} — {state['reason']}")
        return rc
    return publish(root, args.date, args.repo)


if __name__ == "__main__":
    raise SystemExit(main())
