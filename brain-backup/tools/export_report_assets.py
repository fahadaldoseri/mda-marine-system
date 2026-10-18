#!/usr/bin/env python3
"""تصدير أصول الإصدار اليومي: ملف PDF للطباعة + صورة الخريطة التشغيلية.

الاستخدام:
  python3 tools/export_report_assets.py --date 2026-10-18
  python3 tools/export_report_assets.py --date 2026-10-18 --only pdf
  python3 tools/export_report_assets.py --date 2026-10-18 --only map

المخرجات (داخل مشروع الموقع لتُنشر مع الصفحة):
  /home/ubuntu/seawatch/dist/reports/pdf/<التاريخ>.pdf
  /home/ubuntu/seawatch/dist/reports/img/map-<التاريخ>.png

المبدأ: تُقدَّم صفحات dist عبر خادم HTTP محلي مؤقت لأن روابط الأصول في الصفحة مطلقة،
ثم يُستخدم Chromium (Playwright) لطباعة A4 بالوسائط print، ولتصوير عنصر الخريطة `.map-wrap`.
لا يُعدَّل أي ملف مصدر؛ الأصول مخرجات مشتقة.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

DIST = Path("/home/ubuntu/seawatch/dist")
PORT = 8799


@contextlib.contextmanager
def serve(directory: Path, port: int = PORT):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        httpd.allow_reuse_address = True
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            httpd.shutdown()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="تاريخ الإصدار YYYY-MM-DD")
    ap.add_argument("--only", choices=["pdf", "map", "both"], default="both")
    args = ap.parse_args()

    page = DIST / "reports" / f"{args.date}.html"
    if not page.exists():
        print(f"فشل: صفحة الإصدار غير موجودة: {page}")
        return 2

    out_pdf = DIST / "reports" / "pdf" / f"{args.date}.pdf"
    out_png = DIST / "reports" / "img" / f"map-{args.date}.png"
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    result: dict[str, str] = {}
    with serve(DIST) as base, sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 1800},
                                      device_scale_factor=2, locale="ar")
            pg = ctx.new_page()
            pg.goto(f"{base}/reports/{args.date}.html", wait_until="load")
            pg.wait_for_timeout(1200)

            if args.only in ("pdf", "both"):
                pg.emulate_media(media="print")
                pg.pdf(path=str(out_pdf), format="A4", print_background=True,
                       margin={"top": "12mm", "bottom": "14mm", "left": "10mm", "right": "10mm"})
                pg.emulate_media(media="screen")
                result["pdf"] = f"{out_pdf} ({out_pdf.stat().st_size/1024:.0f} ك.ب)"

            if args.only in ("map", "both"):
                el = pg.query_selector(".map-wrap") or pg.query_selector(".map-svg")
                if el:
                    el.scroll_into_view_if_needed()
                    pg.wait_for_timeout(400)
                    el.screenshot(path=str(out_png))
                    result["map"] = f"{out_png} ({out_png.stat().st_size/1024:.0f} ك.ب)"
                else:
                    result["map"] = "لم يُعثر على عنصر الخريطة في الصفحة"
        finally:
            browser.close()

    for k, v in result.items():
        print(f"[{k}] {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())