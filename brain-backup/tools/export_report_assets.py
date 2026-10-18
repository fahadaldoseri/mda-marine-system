#!/usr/bin/env python3
"""تصدير أصول الإصدار اليومي: ملف PDF للطباعة + صورة الخريطة التشغيلية.

الاستخدام:
  python3 tools/export_report_assets.py --date 2026-10-18
  python3 tools/export_report_assets.py --date 2026-10-18 --only pdf
  python3 tools/export_report_assets.py --date 2026-10-18 --only map
  python3 tools/export_report_assets.py --date 2026-10-18 --no-toc

المخرجات (داخل مشروع الموقع لتُنشر مع الصفحة):
  /home/ubuntu/seawatch/dist/reports/pdf/<التاريخ>.pdf
  /home/ubuntu/seawatch/dist/reports/img/map-<التاريخ>.png

قواعد PDF المعتمدة (قرار 18 أكتوبر 2026):
  1. لا يُعرض قسم «المصادر والمراجع» ولا ملحق «موثوقية المصادر» (كلاهما داخل #sec-16) في نسخة PDF.
  2. تُطبع ترويسة وتذييل في كل صفحة: هوية التقرير والتصنيف ورقم الصفحة (X من Y).
  3. يُضاف فهرس محتويات بأرقام صفحات حقيقية (تمريرتان: قياس ثم توليد).
  4. علامات مرجعية (Bookmarks) لكل قسم داخل الملف، وملف موسوم (Tagged).
  5. هوامش A4: 18 مم جانبيًا · 16 أعلى · 18 أسفل.

المبدأ: تُقدَّم صفحات dist عبر خادم HTTP محلي مؤقت لأن روابط الأصول مطلقة، ثم يُستخدم
Chromium (Playwright) لطباعة A4 بالوسائط print، ولتصوير عنصر الخريطة `.map-wrap`.
لا يُعدَّل أي ملف مصدر؛ الأصول مخرجات مشتقة.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

DIST = Path("/home/ubuntu/seawatch/dist")
PORT = 8799

# أنماط PDF فقط: تُحقن أثناء التصدير ولا تمسّ صفحة الموقع
PDF_CSS = """
#sec-16{display:none !important}
section.doc > h2{break-after:avoid;page-break-after:avoid}
p,li,blockquote{orphans:3;widows:3}
.map-viz svg{max-height:118mm;height:auto}
tbody tr:nth-child(even){background:#fff !important}
tbody td{border-bottom:.4pt solid #e2e8f0}
.mp-events text{font-size:12px}
#sec-toc{margin-top:2mm}
#sec-toc ol{margin:0;padding-inline-start:6mm;column-count:2;column-gap:12mm}
#sec-toc li{font-size:10pt;line-height:1.75;break-inside:avoid}
#sec-toc .toc-n{font-family:"IBM Plex Mono",monospace;font-size:9.5pt;color:#4b5e73}
"""

HEADER_TPL = """<div style="font-family:'Noto Kufi Arabic','IBM Plex Sans Arabic',sans-serif;font-size:7.6px;
color:#4b5e73;width:100%;padding:0 18mm 2px;direction:rtl;display:flex;justify-content:space-between;
border-bottom:.4pt solid #cfd8e3;">
<span>التقرير اليومي لأمن الملاحة والأوضاع الراهنة في المنطقة</span>
<span>{IDENT}</span></div>"""

FOOTER_TPL = """<div style="font-family:'Noto Kufi Arabic','IBM Plex Sans Arabic',sans-serif;font-size:7.6px;
color:#4b5e73;width:100%;padding:2px 18mm 0;direction:rtl;display:flex;justify-content:space-between;
border-top:.4pt solid #cfd8e3;">
<span>التصنيف: عام · مركز الوعي بالمجال البحري MDA.BH</span>
<span>صفحة <span class="pageNumber"></span> من <span class="totalPages"></span></span></div>"""


@contextlib.contextmanager
def serve(directory: Path, port: int = 0):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        httpd.allow_reuse_address = True
        real_port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            yield f"http://127.0.0.1:{real_port}"
        finally:
            httpd.shutdown()


def identity_of(html: str, date: str) -> str:
    """هوية الترويسة: رقم النسخة والتاريخ والتصنيف، مستخرجة من الصفحة نفسها."""
    num = ""
    m = re.search(r"رقم النسخة[^<]*<[^>]*>([^<]{3,40})", html)
    if m:
        num = re.sub(r"\s+", " ", m.group(1)).strip()
    if not num:
        m = re.search(r"(و\s*ب\s*[\d\s/]{4,16})", html)
        num = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    return " · ".join(x for x in (num, date, "تصنيف: عام") if x)


def sections_of(page) -> list[dict]:
    return page.evaluate("""()=>{
      const out=[];
      document.querySelectorAll('section.doc').forEach(s=>{
        if(s.id==='sec-16' || getComputedStyle(s).display==='none') return;
        const h=s.querySelector('h2'); if(!h) return;
        const t=(h.textContent||'').replace(/\\s+/g,' ').trim();
        if(t) out.push({id:s.id, title:t});
      });
      return out;}""")


def inject_toc(page, sections: list[dict], pages_map: dict[str, str] | None) -> None:
    items = "".join(
        f'<li>{s["title"]} <span class="toc-n">{("ص " + pages_map.get(s["title"], "—")) if pages_map else "ص 0"}</span></li>'
        for s in sections)
    html = ('<section class="doc" id="sec-toc"><h2>المحتوى</h2><div class="h-rule"></div>'
            f'<ol>{items}</ol></section>')
    n = page.evaluate("""(html)=>{
      document.querySelectorAll('#sec-toc').forEach(e=>e.remove());
      const tmp=document.createElement('div'); tmp.innerHTML=html;
      const node=tmp.firstChild;
      const host=document.querySelector('.wrap') || document.body;
      const mast=document.querySelector('.masthead');
      if(mast) mast.after(node); else host.insertBefore(node, host.firstChild);
      window.scrollTo(0,0);
      return document.querySelectorAll('#sec-toc li').length;}""", html)
    print(f"إدراج الفهرس: {n} بندًا")
    if not n:
        raise SystemExit("فشل إدراج الفهرس في الصفحة")


def page_index(pdf: Path) -> dict[str, str]:
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    pages = []
    for p in txt.split("\f"):
        # تُحذف أسطر الفهرس (تحوي «ص N») حتى لا تُحسب أرقام الفهرس مواضع للأقسام
        kept = []
        for ln in p.split("\n"):
            clean = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", ln)
            if re.search(r"ص\s?\d+\s*$", clean.strip()):
                continue
            kept.append(clean)
        pages.append(norm("\n".join(kept)))
    return pages


def norm(s: str) -> str:
    """توحيد النص لمقاومة تشويه الاستخراج: يحذف الأسطر والعلامات ويُبقي الحروف والأرقام."""
    s = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", s)
    return re.sub(r"[^\u0621-\u064A0-9A-Za-z]", "", s)


def locate_titles(pages_norm: list[str], sections: list[dict]) -> dict[str, str]:
    """رقم أول صفحة يظهر فيها عنوان القسم، بمطابقة مُوحَّدة."""
    out: dict[str, str] = {}
    seen: set[str] = set()
    for s in sections:
        t = norm(s["title"])
        if len(t) < 4 or t in seen:
            out[s["title"]] = "—"
            continue
        seen.add(t)
        found = "—"
        for i, p in enumerate(pages_norm, 1):
            if t in p:
                found = str(i)
                break
        out[s["title"]] = found
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="تاريخ الإصدار YYYY-MM-DD")
    ap.add_argument("--only", choices=["pdf", "map", "both"], default="both")
    ap.add_argument("--no-toc", action="store_true", help="بلا فهرس محتويات")
    ap.add_argument("--no-header", action="store_true", help="بلا ترويسة وتذييل")
    args = ap.parse_args()

    page_path = DIST / "reports" / f"{args.date}.html"
    if not page_path.exists():
        print(f"فشل: صفحة الإصدار غير موجودة: {page_path}")
        return 2

    out_pdf = DIST / "reports" / "pdf" / f"{args.date}.pdf"
    out_png = DIST / "reports" / "img" / f"map-{args.date}.png"
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    html_src = page_path.read_text(encoding="utf-8")
    date_label = args.date
    m = re.search(r"(\d{1,2})\s+([^\s<]+)\s+(\d{4})م?", html_src)
    if m:
        date_label = f"{m.group(1)} {m.group(2)} {m.group(3)}"
    ident = identity_of(html_src, date_label)
    print(f"هوية الترويسة: {ident}")

    from playwright.sync_api import sync_playwright

    result: dict[str, str] = {}
    margins = {"top": "16mm", "bottom": "18mm", "left": "18mm", "right": "18mm"}
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
                pg.add_style_tag(content=PDF_CSS)

                sections = sections_of(pg)
                kwargs = dict(format="A4", print_background=True, margin=margins,
                              tagged=True, outline=True)
                if not args.no_header:
                    kwargs.update(display_header_footer=True,
                                  header_template=HEADER_TPL.format(IDENT=ident),
                                  footer_template=FOOTER_TPL)

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
                    pass1 = Path(fh.name)
                if args.no_toc:
                    pg.pdf(path=str(out_pdf), **kwargs)
                    pages_map = None
                else:
                    inject_toc(pg, sections, None)
                    pg.pdf(path=str(pass1), **kwargs)
                    pages_map = locate_titles(page_index(pass1), sections)
                    inject_toc(pg, sections, pages_map)
                    pg.pdf(path=str(out_pdf), **kwargs)
                    pass1.unlink(missing_ok=True)
                pg.emulate_media(media="screen")
                result["pdf"] = f"{out_pdf} ({out_pdf.stat().st_size/1024:.0f} ك.ب)"
                if pages_map:
                    found = sum(1 for v in pages_map.values() if v != "—")
                    result["toc"] = f"{len(pages_map)} قسمًا · أرقام صفحات مُثبتة لـ{found}"

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
