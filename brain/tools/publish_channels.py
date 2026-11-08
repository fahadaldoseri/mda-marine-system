#!/usr/bin/env python3
"""عقد نشر Seawatch: Pages أولًا، ثم النقل العام مع تحقق حي صارم.

قناة Cloudflare Pages هي قناة العرض الأساسية. raw.githack ثم jsDelivr بدائل
عرض HTML، أما raw.githubusercontent فهو ملاذ تحقق آلي فقط لأن Content-Type
الخاص به text/plain وليس قناة عرض.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

DEFAULT_REPO = "fahadaldoseri/seawatch-live"
DEFAULT_BRANCH = "main"
PAGES_BASE_URL = "https://seawatch-live.pages.dev"
PAGES_REPO = DEFAULT_REPO
PAGES_BRANCH = DEFAULT_BRANCH
PAGES_PROPAGATION_DELAYS = (15, 20, 25, 30, 40, 50)  # مهلة انتشار بناء القناة الأساسية قبل الحكم بالفشل (ثوانٍ)
PAGES_MIN_BYTES = 100_000
GITHACK_BASE = "https://raw.githack.com"
JSDELIVR_BASE = "https://cdn.jsdelivr.net/gh"
RAW_GITHUB_BASE = "https://raw.githubusercontent.com"
LIVE_VERIFY_WINDOW_SECONDS = 90
LIVE_VERIFY_INTERVAL_SECONDS = 3


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_command(args: list[str], *, env: dict[str, str] | None = None,
                cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                           text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def artifact_sha256(path: Path) -> str | None:
    try:
        return sha256_bytes(path.read_bytes()) if path.is_file() else None
    except OSError:
        return None


def _content_type(content_type: str) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def verify_live_response(
    status: int,
    body: bytes,
    date: str,
    content_type: str = "",
    *,
    allow_text_plain: bool = False,
    min_bytes: int = 1,
    expected_sha256: str | None = None,
    requested_url: str | None = None,
    final_url: str | None = None,
    redirects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Require 200, followed redirects, HTML for display, size, marker and hash."""
    normalized = _content_type(content_type)
    is_html = "text/html" in (content_type or "").lower()
    is_text = normalized == "text/plain"
    content_type_ok = is_html or (allow_text_plain and is_text)
    presentation_eligible = is_html
    digest = sha256_bytes(body)
    sha_ok = expected_sha256 is None or digest == expected_sha256
    marker = date.encode("utf-8") in body
    size_ok = len(body) >= max(1, int(min_bytes))
    ok = status == 200 and size_ok and marker and content_type_ok and sha_ok
    reason = "ok" if ok else (
        f"http={status}; bytes={len(body)}; min_bytes={min_bytes}; "
        f"date_marker={str(marker).lower()}; content_type={normalized or 'missing'}; "
        f"content_type_ok={str(content_type_ok).lower()}; sha256={digest[:16]}; "
        f"sha256_match={str(sha_ok).lower()}"
    )
    chain = redirects or []
    return {
        "ok": ok,
        "status": int(status),
        "bytes": len(body),
        "min_bytes": max(1, int(min_bytes)),
        "size_ok": size_ok,
        "date_marker": marker,
        "content_type": content_type or "",
        "content_type_normalized": normalized,
        "content_type_ok": content_type_ok,
        "presentation_eligible": presentation_eligible,
        "sha256": digest,
        "expected_sha256": expected_sha256,
        "sha256_match": sha_ok,
        "requested_url": requested_url,
        "final_url": final_url or requested_url,
        "redirected": bool(chain),
        "redirects": chain,
        "reason": reason,
    }


class _RedirectRecorder(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.chain: list[dict[str, Any]] = []

    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int,
                         msg: str, headers: Any, newurl: str) -> urllib.request.Request | None:
        self.chain.append({"status": int(code), "from": req.full_url, "to": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def verify_live_url(
    url: str,
    date: str,
    *,
    opener: Callable[..., Any] | None = None,
    allow_text_plain: bool = False,
    min_bytes: int = 1,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """GET a live URL, follow 3xx, and never infer success from a Git push."""
    window = max(0, int(os.environ.get("SEAWATCH_LIVE_VERIFY_WINDOW_SECONDS",
                                      str(LIVE_VERIFY_WINDOW_SECONDS))))
    interval = max(0, int(os.environ.get("SEAWATCH_LIVE_VERIFY_INTERVAL_SECONDS",
                                        str(LIVE_VERIFY_INTERVAL_SECONDS))))
    started = time.monotonic()
    attempts = 0
    while True:
        attempts += 1
        redirects: list[dict[str, Any]] = []
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "User-Agent": "seawatch-publish-contract",
                "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1",
            },
        )
        try:
            if opener is None:
                recorder = _RedirectRecorder()
                response_opener = urllib.request.build_opener(recorder)
                response = response_opener.open(request, timeout=min(30, max(1, window or 1)))
                redirects = recorder.chain
            else:
                response = opener(request, timeout=min(30, max(1, window or 1)))
            with response:
                body = response.read()
                verdict = verify_live_response(
                    int(response.status), body, date,
                    response.headers.get("Content-Type", ""),
                    allow_text_plain=allow_text_plain,
                    min_bytes=min_bytes,
                    expected_sha256=expected_sha256,
                    requested_url=url,
                    final_url=response.geturl(),
                    redirects=redirects,
                )
        except urllib.error.HTTPError as exc:
            verdict = verify_live_response(
                int(exc.code), b"", date,
                exc.headers.get("Content-Type", "") if exc.headers else "",
                allow_text_plain=allow_text_plain,
                min_bytes=min_bytes,
                expected_sha256=expected_sha256,
                requested_url=url,
                final_url=exc.geturl(),
                redirects=redirects,
            )
        except Exception as exc:  # network failures are closed failures
            verdict = verify_live_response(
                0, b"", date, "", allow_text_plain=allow_text_plain,
                min_bytes=min_bytes, expected_sha256=expected_sha256,
                requested_url=url, final_url=url, redirects=redirects,
            )
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


def cloudflare_report_url(date: str, base_url: str = PAGES_BASE_URL) -> str:
    return f"{base_url.rstrip('/')}/reports/{date}"


def site_root(root: Path) -> Path:
    """Resolve the site independently of whether ``root`` is brain or its mirror."""
    env = os.environ.get("SITE_DIR")
    candidates = [
        Path(env) if env else None,
        root.parent / "seawatch",
        root.parent.parent / "seawatch",
    ]
    # يُفضَّل الجذر الذي يحوي مخرج بناء فعليًا؛ لا مسارات مطلقة مثبَّتة (شرط النقل).
    for candidate in candidates:
        if candidate and (candidate / "dist").is_dir():
            return candidate
    for candidate in candidates:
        if candidate and candidate.is_dir():
            return candidate
    return Path(env) if env else root.parent / "seawatch"


def cloudflare_pages_readiness(root: Path, date: str) -> dict[str, Any]:
    local = site_root(root) / "dist" / "reports" / f"{date}.html"
    expected = artifact_sha256(local)
    return _status(
        "ready",
        "Cloudflare Pages مرتبط بـfahadaldoseri/seawatch-live@main؛ القياس الحي داخل D020",
        enabled=True,
        primary=True,
        presentation_eligible=True,
        url=PAGES_BASE_URL,
        report_url=cloudflare_report_url(date),
        repo=PAGES_REPO,
        branch=PAGES_BRANCH,
        min_bytes=PAGES_MIN_BYTES,
        expected_sha256=expected,
        auto_deploy=True,
    )


def github_pages_readiness(repo: str = DEFAULT_REPO) -> dict[str, Any]:
    """Check the public raw.githack fallback repository, not Pages API."""
    gh_env = dict(os.environ, GH_FORCE_TTY="0", NO_COLOR="1")
    rc, output = run_command(["gh", "auth", "status", "--hostname", "github.com"], env=gh_env)
    if rc != 0:
        return _status("down", f"gh auth status rc={rc}: {output[-500:]}", auth_rc=rc,
                       presentation_eligible=True, transport="raw.githack")
    rc, repo_output = run_command(
        ["gh", "repo", "view", repo, "--json", "nameWithOwner,defaultBranchRef,url,visibility"],
        env=gh_env,
    )
    if rc != 0:
        return _status("down", f"repository unavailable rc={rc}: {repo_output[-500:]}",
                       auth_rc=0, repo_rc=rc, presentation_eligible=True, transport="raw.githack")
    try:
        repo_doc = json.loads(repo_output)
    except json.JSONDecodeError:
        return _status("down", "repository metadata returned non-JSON output", auth_rc=0,
                       repo_rc=0, presentation_eligible=True, transport="raw.githack")
    visibility = str(repo_doc.get("visibility", "")).upper()
    branch = ((repo_doc.get("defaultBranchRef") or {}).get("name") or "")
    if visibility != "PUBLIC" or branch != DEFAULT_BRANCH:
        return _status("down", f"fallback repository visibility={visibility or 'unknown'} branch={branch or 'unknown'}",
                       auth_rc=0, repo_rc=0, visibility=visibility, branch=branch,
                       presentation_eligible=True, transport="raw.githack")
    return _status(
        "ready",
        "raw.githack fallback repository is public; jsDelivr is an intermediate transport",
        auth_rc=0,
        repo_rc=0,
        visibility=visibility,
        branch=branch,
        repo=repo,
        presentation_eligible=True,
        transport="raw.githack",
    )


def preflight(root: Path, date: str, repo: str = DEFAULT_REPO) -> tuple[int, dict[str, Any]]:
    pages = cloudflare_pages_readiness(root, date)
    githack = github_pages_readiness(repo)
    raw_verify = _status(
        "verification-only",
        "raw.githubusercontent.com يعيد text/plain؛ ممنوع كقناة عرض",
        enabled=True,
        primary=False,
        presentation_eligible=False,
        transport="raw.githubusercontent.com",
        url=f"{RAW_GITHUB_BASE}/{repo}/{DEFAULT_BRANCH}",
    )
    doc = {
        "date": date,
        "at": utc_now(),
        "measurement_scope": "readiness-only; D020 owns live status, redirects, bytes and sha256",
        "release_today_checked": False,
        "release_today_note": "S085 يثبت الربط فقط؛ D020 يثبت 200 بعد التحويل وtext/html والحجم والبصمة.",
        "channel_order": ["cloudflare-pages", "raw-githack", "raw.githubusercontent-verify-only"],
        "channels": {
            "cloudflare-pages": pages,
            "raw-githack": githack,
            "raw.githubusercontent": raw_verify,
        },
    }
    doc["status"] = "ready" if choose_channel(doc["channels"]) else "down"
    doc["rc"] = 0 if doc["status"] == "ready" else 2
    out = root / "logs" / f"publish-channel-{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(doc["rc"]), doc


def choose_channel(statuses: dict[str, dict[str, Any]]) -> str | None:
    for channel in ("cloudflare-pages", "raw-githack"):
        state = statuses.get(channel, {})
        if state.get("state") == "ready" and state.get("presentation_eligible", True):
            return channel
    return None


def preflight_exit_code(statuses: dict[str, dict[str, Any]]) -> int:
    return 0 if choose_channel(statuses) else 2


def build_publish_record(*, date: str, channel: str, url: str, head: str,
                         live: dict[str, Any], rc: int,
                         fingerprint: str | None = None,
                         urls: list[str] | None = None) -> dict[str, Any]:
    verified = bool(rc == 0 and live.get("ok") is True and
                    live.get("presentation_eligible", True) is True)
    record: dict[str, Any] = {
        "date": date,
        "channel": channel,
        "url": url,
        "successful_url": url if verified else None,
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


def _write_publish(root: Path, date: str, record: dict[str, Any]) -> None:
    path = root / "logs" / f"publish-{date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _record_history(record: dict[str, Any], attempts: list[dict[str, Any]],
                    channel_states: dict[str, dict[str, Any]]) -> None:
    """Attach detached attempt snapshots; never serialize a record into itself."""
    record["channels"] = copy.deepcopy(channel_states)
    record["attempts"] = [copy.deepcopy(item) for item in attempts]


def fallback_report_urls(date: str, repo: str = DEFAULT_REPO,
                         branch: str = DEFAULT_BRANCH) -> list[str]:
    owner, name = repo.split("/", 1)
    return [
        f"{GITHACK_BASE}/{owner}/{name}/{branch}/reports/{date}.html",
        f"{JSDELIVR_BASE}/{owner}/{name}@{branch}/reports/{date}.html",
        f"{RAW_GITHUB_BASE}/{owner}/{name}/{branch}/reports/{date}.html",
    ]


def fallback_urls(date: str, repo: str = DEFAULT_REPO,
                  branch: str = DEFAULT_BRANCH) -> list[str]:
    return fallback_report_urls(date, repo, branch)


def _transport(url: str) -> str:
    if "raw.githack.com" in url:
        return "raw.githack"
    if "jsdelivr.net" in url:
        return "jsDelivr"
    if "raw.githubusercontent.com" in url:
        return "raw.githubusercontent.com"
    if "pages.dev" in url:
        return "cloudflare-pages"
    return "unknown"


def verify_candidates(urls: list[str], date: str, *,
                      expected_sha256: str | None = None,
                      min_bytes: int = 1) -> tuple[int, dict[str, Any]]:
    """Try display transports in order; raw.githubusercontent is verification-only."""
    attempts: list[dict[str, Any]] = []
    for url in urls:
        raw_only = "raw.githubusercontent.com" in url
        verdict = verify_live_url(
            url,
            date,
            allow_text_plain=raw_only,
            min_bytes=min_bytes,
            expected_sha256=expected_sha256 if not raw_only else None,
        )
        if raw_only:
            verdict["presentation_eligible"] = False
            verdict["verification_only"] = True
        attempts.append(verdict)
        if verdict.get("ok") and verdict.get("presentation_eligible", True):
            return 0, {
                "status": "ok",
                "date": date,
                "successful_url": url,
                "successful_transport": _transport(url),
                "attempts": attempts,
            }
    verification = next((item for item in attempts if item.get("ok") and item.get("verification_only")), None)
    return 2, {
        "status": "verification-only" if verification else "failed",
        "date": date,
        "successful_url": None,
        "verification_url": verification.get("url") if verification else None,
        "successful_transport": None,
        "attempts": attempts,
    }


def _local_report(root: Path, date: str) -> Path:
    return site_root(root) / "dist" / "reports" / f"{date}.html"


def _fresh_statuses(root: Path, date: str, repo: str) -> tuple[int, dict[str, dict[str, Any]]]:
    """جهوزية القنوات بقياس جديد في كل مرة — لا قرار نشر على لقطة مخزّنة (عطل ك-555)."""
    rc, doc = preflight(root, date, repo)
    return rc, doc.get("channels", {})


def publish(root: Path, date: str, repo: str = DEFAULT_REPO) -> int:
    preflight_rc, statuses = _fresh_statuses(root, date, repo)
    selected = choose_channel(statuses)
    if not selected:
        _write_publish(root, date, {"date": date, "status": "failed", "rc": 2,
                                    "channel": None, "url": None, "head": None,
                                    "why": "no presentation channel ready after fresh preflight",
                                    "preflight_rc": preflight_rc, "at": utc_now()})
        return 2

    order = ["cloudflare-pages", "raw-githack"] if selected == "cloudflare-pages" else [selected]
    attempts: list[dict[str, Any]] = []
    channel_states = {
        name: {"state": value.get("state"), "reason": value.get("reason", ""),
               "presentation_eligible": value.get("presentation_eligible", True)}
        for name, value in statuses.items()
    }
    local_sha = artifact_sha256(_local_report(root, date))
    for channel in order:
        if statuses.get(channel, {}).get("state") != "ready":
            continue
        if channel == "cloudflare-pages":
            base = str(statuses[channel].get("url") or PAGES_BASE_URL).rstrip("/")
            env = dict(os.environ, BRAIN_DIR=str(root), LIVE_BASE_URL=base)
            rc, output = run_command(["bash", str(root / "tools" / "publish_site.sh"), date], cwd=root, env=env)
            publish_doc = _read_json(root / "logs" / f"publish-{date}.json")
            head = publish_doc.get("head") or ""
            url = cloudflare_report_url(date, base)
            live = verify_live_url(url, date, min_bytes=PAGES_MIN_BYTES, expected_sha256=local_sha)
            waited = 0
            for delay in PAGES_PROPAGATION_DELAYS:
                if live.get("ok"):
                    break
                time.sleep(delay)
                waited += delay
                live = verify_live_url(url, date, min_bytes=PAGES_MIN_BYTES, expected_sha256=local_sha)
            if waited:
                live["propagation_wait_seconds"] = waited
            record = build_publish_record(date=date, channel=channel, url=url, head=head,
                                          live=live, rc=rc, fingerprint=local_sha)
            record["publish_output_tail"] = output[-1000:]
            record["channel_role"] = "primary-presentation"
            attempts.append(record)
            if record["status"] == "ok":
                channel_states[channel] = {"state": "ready", "reason": "Pages live 200/html/sha256 verified",
                                            "live": live, "presentation_eligible": True}
                _record_history(record, attempts, channel_states)
                _write_publish(root, date, record)
                return 0
            channel_states[channel] = {"state": "down", "reason": live.get("reason", "Pages verification failed"),
                                       "live": live, "presentation_eligible": True}
            _write_publish(root, date, record)
            continue

        if channel in {"raw-githack", "github-pages"}:
            rc, output = run_command(["bash", str(root / "tools" / "publish_fallback.sh"), date],
                                     cwd=root, env=dict(os.environ, BRAIN_DIR=str(root)))
            fallback = _read_json(root / "logs" / f"publish-{date}-fallback.json")
            candidates = fallback.get("urls") or fallback_report_urls(date, repo)
            vrc, verification = verify_candidates(candidates, date)
            successful_url = verification.get("successful_url") or ""
            live = next((item for item in verification.get("attempts", []) if item.get("url") == successful_url),
                        verification.get("attempts", [{}])[-1] if verification.get("attempts") else verify_live_response(0, b"", date))
            record = build_publish_record(date=date, channel="raw-githack", url=successful_url,
                                          head=fallback.get("head") or "", live=live,
                                          rc=rc if rc else vrc,
                                          fingerprint=fallback.get("content_sha256"), urls=candidates)
            record["fallback_output_tail"] = output[-1000:]
            record["verification"] = verification
            record["channel_role"] = "fallback-presentation"
            attempts.append(record)
            channel_states["raw-githack"] = {
                "state": "ready" if record["status"] == "ok" else "down",
                "reason": live.get("reason", "fallback verification failed"),
                "live": live,
                "presentation_eligible": True,
            }
            _write_publish(root, date, record)
            if record["status"] == "ok":
                _record_history(record, attempts, channel_states)
                _write_publish(root, date, record)
                return 0

    final = attempts[-1] if attempts else {"date": date, "channel": None, "url": None,
                                           "head": None, "rc": 2, "status": "failed", "at": utc_now()}
    _record_history(final, attempts, channel_states)
    _write_publish(root, date, final)
    return int(final.get("rc", 2)) or 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seawatch Pages and fallback publishing contracts")
    parser.add_argument("command", choices=("preflight", "publish", "verify"))
    parser.add_argument("--date", required=True)
    parser.add_argument("--root", default=os.environ.get("BRAIN_DIR", str(Path(__file__).resolve().parents[1])))
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--url", action="append", default=[], help="رابط حي؛ يمكن تكراره للـfailover")
    parser.add_argument("--expected-sha256", default=None)
    parser.add_argument("--min-bytes", type=int, default=1)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "preflight":
        rc, doc = preflight(root, args.date, args.repo)
        for name, state in doc["channels"].items():
            print(f"{name}: {state['state']} — {state['reason']}")
        return rc
    if args.command == "verify":
        if not args.url:
            parser.error("verify يحتاج --url واحدًا على الأقل")
        rc, doc = verify_candidates(args.url, args.date,
                                     expected_sha256=args.expected_sha256,
                                     min_bytes=args.min_bytes)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return rc
    return publish(root, args.date, args.repo)


if __name__ == "__main__":
    raise SystemExit(main())
