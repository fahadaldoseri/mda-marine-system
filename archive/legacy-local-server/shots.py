#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""لقطات شاشة للتحقق البصري من صفحة التقرير (سطح المكتب + نمط الطباعة)."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

src = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/brain-marine-news/web/out/التقرير-الصباحي-2026-10-12.html"
outdir = Path(sys.argv[2] if len(sys.argv) > 2 else "/home/ubuntu/brain-marine-news/web/shots")
outdir.mkdir(parents=True, exist_ok=True)
url = "file://" + str(Path(src).resolve())

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1440, "height": 980}, device_scale_factor=1)
    pg.goto(url, wait_until="load")
    pg.wait_for_timeout(1800)

    shots = [0, 900, 2100, 3400, 5200, 7600]
    for i, y in enumerate(shots):
        pg.evaluate(f"window.scrollTo(0,{y})")
        pg.wait_for_timeout(900)
        pg.screenshot(path=str(outdir / f"desktop-{i}.png"))

    pg.evaluate("window.scrollTo(0,0)")
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(outdir / "full.png"), full_page=True)

    # نمط الطباعة (A4)
    pg.emulate_media(media="print")
    pg.wait_for_timeout(600)
    pg.pdf(path=str(outdir / "print-a4.pdf"), format="A4", print_background=True)
    b.close()

print("shots in", outdir)