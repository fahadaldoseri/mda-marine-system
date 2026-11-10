#!/usr/bin/env python3
"""تصنيف مسار مصدر مع قياس حي آمن.

الرموز: 0 مسار صالح، 2 مسار متعذّر أو حماية، 64 خطأ استعمال.
لا ينفّذ هذا الملف متصفحًا أو CAPTCHA أو قارئًا مدفوعًا؛ إنه يصنّف فقط.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CHALLENGE_MARKERS = (
    "just a moment",
    "cf-chl",
    "captcha",
    "verify you are human",
    "human verification",
    "checking your browser",
    "challenge",
    "تحقق بشري",
    "تحدي حماية",
)
TECHNICAL_HTTP = {408, 425, 429, 500, 502, 503, 504}
USER_AGENT = "Mozilla/5.0 (compatible; source-route-triage/1.0)"


def safe_url(raw: str) -> str:
    """يُخفي query وfragment وبيانات الدخول من المخرج."""
    parsed = urllib.parse.urlsplit(raw)
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urllib.parse.urlunsplit((parsed.scheme, host, parsed.path or "/", "", ""))


def body_text(payload: bytes) -> str:
    return html.unescape(payload.decode("utf-8", "ignore"))


def item_count(text: str) -> int:
    rss = len(re.findall(r"<(?:item|entry)(?:\s|>)", text, re.I))
    if rss:
        return rss
    headings = len(re.findall(r"<h[1-6](?:\s|>)", text, re.I))
    return headings


def classify(status: int | None, text: str, error_kind: str | None) -> tuple[str, str, bool]:
    lowered = text.lower()
    challenged = any(marker.lower() in lowered for marker in CHALLENGE_MARKERS)
    if status in {403, 429} and challenged:
        return "حماية", "توقف؛ لا تجاوز تحدي الحماية أو التحقق البشري", False
    if error_kind or (status in TECHNICAL_HTTP):
        return "فشل تقني", "تجربة التغذية الرسمية ثم BROWSER_ROUTES؛ القارئ المدفوع مسموح لهذا الصنف فقط", True
    if status == 403:
        return "تعذّر عابر", "إعادة القياس لاحقًا دون تجاوز الحماية", False
    if status is not None and not 200 <= status < 300:
        return "تعذّر عابر", "إعادة القياس لاحقًا أو طلب مسار رسمي معلن", False
    if not text.strip():
        return "فشل تقني", "المسار أعاد جسمًا فارغًا؛ تجربة المسار الرسمي البديل", True
    return "ناجح", "تسجيل القياس ثم تمرير بوابة الحداثة", False


def fetch(args: argparse.Namespace) -> tuple[int | None, bytes, str | None]:
    if args.body_file:
        try:
            return args.status_code, Path(args.body_file).read_bytes(), None
        except OSError as exc:
            return None, b"", type(exc).__name__
    request = urllib.request.Request(
        args.url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/html;q=0.9"},
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            return int(response.status), response.read(args.max_bytes), None
    except urllib.error.HTTPError as exc:
        try:
            data = exc.read(args.max_bytes)
        except OSError:
            data = b""
        return int(exc.code), data, None
    except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError) as exc:
        return None, b"", type(exc).__name__


def main() -> int:
    parser = argparse.ArgumentParser(description="تصنيف آمن لمسار مصدر")
    parser.add_argument("--url", required=True)
    parser.add_argument("--label", default="مصدر")
    parser.add_argument("--route", default="primary")
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--body-file", help="ملف اختباري محلي بدل الشبكة")
    parser.add_argument("--status-code", type=int, default=200, help="رمز الجسم المحلي الاختباري")
    args = parser.parse_args()
    if not args.body_file and not args.url.startswith(("http://", "https://")):
        parser.error("--url يجب أن يبدأ بـ http:// أو https://")
    started = time.perf_counter()
    status, payload, error_kind = fetch(args)
    elapsed = round(time.perf_counter() - started, 3)
    text = body_text(payload)
    classification, next_route, allow_paid = classify(status, text, error_kind)
    result = {
        "label": args.label,
        "route": args.route,
        "url": safe_url(args.url),
        "status_code": status,
        "classification": classification,
        "next_route": next_route,
        "allow_paid_reader": allow_paid,
        "items": item_count(text),
        "chars": len(text),
        "elapsed_seconds": elapsed,
        "measured_at": args.date,
        "error_kind": error_kind,
        "challenge_detected": classification == "حماية",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if classification == "ناجح" else 2


if __name__ == "__main__":
    raise SystemExit(main())
