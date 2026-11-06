#!/usr/bin/env python3
"""Read-only Playwright audit for live Arabic web surfaces."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - environment error path
    PlaywrightTimeoutError = TimeoutError  # type: ignore
    sync_playwright = None  # type: ignore


AUDIT_JS = r"""
() => {
  const findings = [];
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const shortText = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 160);
  const describe = (el) => {
    const r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      className: typeof el.className === 'string' ? el.className.slice(0, 120) : '',
      text: shortText(el),
      x: Math.round(r.x), y: Math.round(r.y),
      width: Math.round(r.width * 100) / 100,
      height: Math.round(r.height * 100) / 100,
      selectorHint: el.id ? `#${el.id}` : el.tagName.toLowerCase()
    };
  };
  const touchSelector = 'a,button,input,select,textarea,[role="button"],[role="link"],[role="checkbox"],[role="radio"],[tabindex]:not([tabindex="-1"])';
  document.querySelectorAll(touchSelector).forEach((el) => {
    if (!visible(el)) return;
    const r = el.getBoundingClientRect();
    if (r.width < 44 || r.height < 44) {
      findings.push({kind: 'touch-target', detail: describe(el), measured: `${Math.round(r.width * 100) / 100}x${Math.round(r.height * 100) / 100}px`, rule: 'width/height >= 44px'});
    }
  });
  const cardSelector = 'td,th,[data-card],.card,[class*="card" i],[role="article"]';
  document.querySelectorAll(cardSelector).forEach((el) => {
    if (!visible(el)) return;
    const text = (el.innerText || el.textContent || '').trim();
    if (text.length === 0) {
      findings.push({kind: 'empty-cell-or-card', detail: describe(el), measured: 'textLength=0', rule: 'non-empty table cell/card'});
    }
  });
  document.querySelectorAll('*').forEach((el) => {
    if (el === document.documentElement || el === document.body || !visible(el)) return;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    if (el.scrollWidth > el.clientWidth + 4 && ['auto', 'scroll', 'hidden', 'clip'].includes(s.overflowX)) {
      findings.push({kind: 'contained-horizontal-overflow', detail: describe(el), measured: `scrollWidth=${el.scrollWidth}px clientWidth=${el.clientWidth}px`, rule: `overflow-x=${s.overflowX}`});
    }
    if (el.scrollHeight > el.clientHeight + 4 && s.overflow === 'hidden') {
      findings.push({kind: 'hidden-vertical-clipping', detail: describe(el), measured: `scrollHeight=${el.scrollHeight}px clientHeight=${el.clientHeight}px`, rule: 'overflow:hidden'});
    }
  });
  return {
    viewport: {width: window.innerWidth, height: window.innerHeight},
    document: {scrollWidth: document.documentElement.scrollWidth, scrollHeight: document.documentElement.scrollHeight},
    findings
  };
}
"""


def safe_name(url: str, index: int) -> str:
    parsed = urlparse(url)
    base = (parsed.netloc + parsed.path).strip("/") or "page"
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:70]
    return f"{index:02d}_{base or 'page'}.png"


def read_urls(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def format_finding(finding: dict) -> str:
    d = finding["detail"]
    identity = d.get("id") or d.get("className") or d.get("selectorHint")
    text = f" text={d.get('text')!r}" if d.get("text") else ""
    return (
        f"- [{finding['kind']}] {identity!r}{text}; "
        f"measure={finding['measured']}; rule={finding['rule']}; "
        f"box=({d.get('x')},{d.get('y')},{d.get('width')}x{d.get('height')})"
    )


def append_learning_log(log_path: Path | None, event: dict) -> None:
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        event = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit URLs read-only with Playwright and save screenshots.")
    parser.add_argument("--urls-file", required=True, type=Path, help="UTF-8 file with one URL per line")
    parser.add_argument("--out", required=True, type=Path, help="Output directory for report and screenshots")
    parser.add_argument("--timeout-ms", type=int, default=45000, help="Navigation timeout per URL")
    parser.add_argument("--log-path", type=Path, help="Optional JSONL learning/defect log path")
    args = parser.parse_args()
    if not args.urls_file.is_file():
        print(f"ERROR: ملف الروابط غير موجود: {args.urls_file}", file=sys.stderr)
        return 1
    urls = read_urls(args.urls_file)
    if not urls:
        print("ERROR: ملف الروابط فارغ.", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / "audit-report.txt"
    lines = [
        "تدقيق الأسطح الحية (قراءة فقط)",
        f"الوقت: {datetime.now(timezone.utc).isoformat()}",
        "القواعد: هدف لمس >=44px؛ خلية/بطاقة غير فارغة؛ overflow-x داخلي محصور؛ منع القص العمودي المخفي.",
        "",
    ]
    finding_count = 0
    errors = 0

    if sync_playwright is None:
        print("ERROR: مكتبة Playwright Python غير متاحة.", file=sys.stderr)
        return 1

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="ar-SA")
            page = context.new_page()
            for index, url in enumerate(urls, start=1):
                lines.append(f"URL {index}: {url}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=args.timeout_ms)
                    page.wait_for_timeout(500)
                    result = page.evaluate(AUDIT_JS)
                    screenshot = args.out / safe_name(url, index)
                    page.screenshot(path=str(screenshot), full_page=True)
                    findings = result.get("findings", [])
                    finding_count += len(findings)
                    lines.append(f"  viewport={result['viewport']['width']}x{result['viewport']['height']} document={result['document']}")
                    lines.append(f"  screenshot={screenshot}")
                    if findings:
                        lines.append(f"  findings={len(findings)}")
                        lines.extend(f"  {format_finding(item)}" for item in findings)
                        for item in findings:
                            append_learning_log(args.log_path, {
                                "tool": "audit_live_surfaces",
                                "status": "مؤكد",
                                "url": url,
                                "finding": item,
                                "screenshot": str(screenshot),
                            })
                    else:
                        lines.append("  findings=0")
                except PlaywrightTimeoutError as exc:
                    errors += 1
                    lines.append(f"  ERROR timeout: {exc}")
                    append_learning_log(args.log_path, {
                        "tool": "audit_live_surfaces",
                        "status": "لم يتحقق",
                        "url": url,
                        "reason": f"timeout: {exc}",
                    })
                except Exception as exc:  # keep auditing the remaining URLs
                    errors += 1
                    lines.append(f"  ERROR {type(exc).__name__}: {exc}")
                    append_learning_log(args.log_path, {
                        "tool": "audit_live_surfaces",
                        "status": "لم يتحقق",
                        "url": url,
                        "reason": f"{type(exc).__name__}: {exc}",
                    })
                lines.append("")
            context.close()
            browser.close()
    except Exception as exc:
        print(f"ERROR: تعذر تشغيل Playwright/Chromium: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    lines.append(f"الخلاصة: findings={finding_count}; errors={errors}; screenshots={args.out}")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"REPORT: {report_path}")
    if errors and finding_count == 0:
        return 1
    return 2 if finding_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
