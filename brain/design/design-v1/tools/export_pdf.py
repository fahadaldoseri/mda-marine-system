#!/usr/bin/env python3
# تصدير PDF مرجعي: python3 tools/export_pdf.py <index.html> <out.pdf> [dark|light]  (Chromium عبر Playwright، وسائط print، A4 من @page، بلا شبكة)
import sys
from playwright.sync_api import sync_playwright
src=sys.argv[1]; out=sys.argv[2]; theme=sys.argv[3] if len(sys.argv)>3 else None
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'])
    pg=b.new_page(viewport={'width':794,'height':1123})
    bad=[]
    pg.on('request',lambda r: bad.append(r.url) if not r.url.startswith(('file:','data:')) else None)
    pg.goto('file://'+src); pg.wait_for_timeout(800); pg.evaluate("document.fonts.ready")
    if theme: pg.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
    pg.emulate_media(media='print')
    pg.pdf(path=out,prefer_css_page_size=True,print_background=True)
    print('external requests:',bad)
    b.close()
