#!/usr/bin/env python3
"""جرّب مسارًا رسميًا معلنًا بديلًا لكل مصدر محجوب وسجّل الدليل.

الأداة تستخدم طلب HTTP عاديًا فقط؛ لا تتجاوز CAPTCHA أو الحجب ولا تستخدم متصفحًا
مخفيًا. نتيجة HTTP 200 لا تُعد نجاحًا إذا كان الرد صفحة تحقق بلا مادة دلالية.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SOURCES = [
    {
        "source": "حساب @bna_en على X",
        "original_path": "https://x.com/bna_en",
        "alternative_path": "https://www.bna.bh/en/RSSFeeds.aspx?cms=iQRpheuphYtJ6pyXUGiNqqtA5DItoRVa",
        "official_route": "وكالة أنباء البحرين — RSS الرسمي المعلن",
    },
    {
        "source": "جريدة الأيام",
        "original_path": "https://www.alayam.com/pages/rss",
        "alternative_path": "https://www.alayam.com/",
        "official_route": "الصفحة الرئيسية الرسمية للجريدة",
    },
    {
        "source": "وكالة الأنباء القطرية (قنا)",
        "original_path": "https://qna.org.qa/en/RSS-Feeds",
        "alternative_path": "https://qna.org.qa/en/Pages/RSS-Feeds/Analysis-and-Reports",
        "official_route": "صفحة RSS الرسمية البديلة لقنا",
    },
]


class AlternativeProbeError(ValueError):
    """خطأ في عقد سجل المسارات البديلة."""


def classify_probe(http_code: int | None, body: bytes) -> dict[str, Any]:
    text = body.decode("utf-8", "ignore").lower()
    blocked_markers = ("human verification", "attention required", "captcha", "cloudflare")
    if http_code is None:
        return {"result": "فشل", "reason": "لم يُحصل على رمز HTTP", "content_chars": len(text)}
    if not 200 <= http_code < 300:
        return {"result": "فشل", "reason": f"HTTP {http_code}", "content_chars": len(text)}
    if not text.strip():
        return {"result": "فشل", "reason": "HTTP 200 بلا مادة", "content_chars": 0}
    if any(marker in text for marker in blocked_markers):
        return {"result": "فشل", "reason": f"HTTP {http_code} مع صفحة حجب/تحقق", "content_chars": len(text)}
    return {"result": "نجح", "reason": f"HTTP {http_code} مع مادة مستلمة", "content_chars": len(text)}


def probe_url(url: str, *, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "seawatch-source-alternative/1.0"})
    body = b""
    http_code: int | None = None
    error_text = ""
    started = time.monotonic()
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            http_code = int(response.getcode())
            body = response.read()
    except urllib.error.HTTPError as exc:
        http_code = int(exc.code)
        try:
            body = exc.read()
        except OSError:
            body = b""
        error_text = f"HTTPError {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        error_text = f"{type(exc).__name__}: {exc}"
    elapsed_ms = round((time.monotonic() - started) * 1000)
    classified = classify_probe(http_code, body)
    if error_text:
        classified["reason"] = f"{classified['reason']}; {error_text}" if classified["reason"] else error_text
    classified.update({
        "http_code": http_code,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "elapsed_ms": elapsed_ms,
    })
    return classified


def run_probes(probe: Callable[[str], dict[str, Any]] = probe_url) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for spec in SOURCES:
        outcome = probe(spec["alternative_path"])
        evidence = (
            f"route={spec['official_route']}; http_code={outcome.get('http_code')}; "
            f"bytes={outcome.get('bytes', 0)}; sha256={outcome.get('sha256', '')}; "
            f"reason={outcome.get('reason', '')}"
        )
        records.append({
            "source": spec["source"],
            "original_path": spec["original_path"],
            "alternative_path": spec["alternative_path"],
            "http_code": outcome.get("http_code"),
            "result": outcome.get("result"),
            "evidence": evidence,
            "official_route": spec["official_route"],
            "content_chars": outcome.get("content_chars", 0),
            "bytes": outcome.get("bytes", 0),
            "sha256": outcome.get("sha256"),
            "elapsed_ms": outcome.get("elapsed_ms"),
        })
    return records


def write_log(root: Path, date: str, records: list[dict[str, Any]]) -> Path:
    path = root / "logs" / f"source-alternatives-{date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": date,
        "method": "HTTP request only; no hidden browser and no bypass of blocking/CAPTCHA",
        "records": records,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="2026-11-04")
    parser.add_argument("--brain", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        records = run_probes()
        path = write_log(args.brain.resolve(), args.date, records)
        print(json.dumps({"log": str(path), "records": records}, ensure_ascii=False))
        return 0
    except (AlternativeProbeError, OSError) as exc:
        print(f"فشل سجل المسارات البديلة: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
