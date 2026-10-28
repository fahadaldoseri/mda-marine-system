#!/usr/bin/env python3
"""تصدير أصول الإصدار اليومي: ملف PDF للطباعة + صورة الخريطة التشغيلية.

الاستخدام:
  python3 tools/export_report_assets.py --date 2026-10-18
  python3 tools/export_report_assets.py --date 2026-10-18 --only pdf
  python3 tools/export_report_assets.py --date 2026-10-18 --only map
  python3 tools/export_report_assets.py --date 2026-10-18 --no-toc

المخرجات (داخل مشروع الموقع لتُنشر مع الصفحة):
  $SITE_DIR/dist/reports/pdf/<التاريخ>.pdf
  $SITE_DIR/dist/reports/img/map-<التاريخ>.png

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
import shutil
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")

import argparse
import contextlib
import functools
import http.server
import re
import socketserver
import os, subprocess
import sys
import tempfile
import threading
from pathlib import Path

B = Path(__file__).resolve().parent.parent

DIST = Path(f"{SITE}/dist")
PORT = 8799

# أنماط PDF فقط: تُحقن أثناء التصدير ولا تمسّ صفحة الموقع
PDF_CSS = """
.additions-annex{break-before:page;page-break-before:always}
.annex-note{font-size:11.5pt;color:#555}
{HIDE_SOURCES}
main{gap:0 !important}
section.doc > h2{break-after:avoid;page-break-after:avoid}
p,li,blockquote{orphans:3;widows:3}
.map-viz svg{max-height:145mm;width:100%;height:auto}
tbody tr:nth-child(even){background:#fff !important}
tbody td{border-bottom:.4pt solid #e2e8f0}
.mp-events text{font-size:12px}
#sec-toc{margin-top:2mm}
#sec-toc ol{margin:0;padding-inline-start:6mm;column-count:2;column-gap:12mm}
#sec-toc li{font-size:10pt;line-height:1.75;break-inside:avoid}
#sec-toc .toc-n{font-family:"IBM Plex Mono",monospace;font-size:9.5pt;color:#4b5e73}
/* ضغط الورق فقط: قوائم البطاقة في عمودين وهوامش فقرات أقصر — لا يمسّ هيئة الشكل المعتمد */
.dc-list{column-count:2;column-gap:10mm}
.dc-list li{break-inside:avoid}
section.doc h3{margin:3mm 0 1.2mm !important}
section.doc h3 + p,section.doc h3 + ul,section.doc h3 + ol{margin-top:.8mm !important}
section.doc p{margin:1.5mm 0}
section.doc ul,section.doc ol{margin:1mm 0}
section.doc li{margin:.45mm 0}
section.doc ul ul{margin:.6mm 0}
.decision{break-before:page;page-break-before:page}
section.doc p,section.doc li,.sec-lede,.masthead .lede,.glossary li,.src-grid li,
.dc-list li,.chg-list li,.ev-list li,.map-caption,footer.foot{text-align:justify;text-align-last:start;hyphens:none}
section.doc h2,section.doc h3,section.doc h4,.h-rule,.chip,.kpi,.tag,.st-badge,
.map-legend li,.conf,.cls-banner,.threat,.toc li,.ev-code{text-align:start}

/* عطل 2026-10-28: الملحق تجاوز الصفحة التاسعة بفقرة واحدة (صفحة عاشرة بتعبئة 7%).
   الحكم: ضغط الملحق وحده (تباعد أسطر ومقاطع) — لا يمسّ متن التقرير ولا هيئة الغلاف. */
.additions-annex section.doc{padding:0 0 2mm}
.additions-annex section.doc p{line-height:1.36;margin:.9mm 0}
.additions-annex section.doc h3{margin:2.2mm 0 1mm !important}
.additions-annex section.doc h2{margin:2mm 0 1.4mm !important}
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
    """هوية الترويسة: رقم الإصدار والتاريخ والتصنيف، مستخرجة من الصفحة نفسها."""
    num = ""
    m = re.search(r"رقم الإصدار[^<]*<[^>]*>([^<]{3,40})", html)
    if m:
        num = re.sub(r"\s+", " ", m.group(1)).strip()
    if not num:
        m = re.search(r"(و\s*ب\s*[\d\s/]{4,16})", html)
        num = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    return " · ".join(x for x in (num, date, "تصنيف: عام") if x)


def sections_of(page, hide_id: str = "") -> list[dict]:
    return page.evaluate("""(hideId)=>{
      const out=[];
      document.querySelectorAll('section.doc').forEach(s=>{
        if(s.id===hideId || getComputedStyle(s).display==='none') return;
        const h=s.querySelector('h2'); if(!h) return;
        const t=(h.textContent||'').replace(/\\s+/g,' ').trim();
        if(t) out.push({id:s.id, title:t});
      });
      return out;}""", hide_id)


def sources_section_id(html: str, heading: str = "المصادر والمراجع") -> str:
    """معرّف قسم المصادر من الصفحة نفسها — لا رقم ثابت يتغير بترتيب الأقسام."""
    for m in re.finditer(r'<section[^>]*id="(sec-\d+)"', html):
        if heading in html[m.end(): m.end() + 700]:
            return m.group(1)
    return ""


def isolate_numbers(page) -> int:
    """فرض اتجاه LTR على النطاقات الرقمية والنسب لمنع انعكاسها في PDF (ك-242)."""
    return page.evaluate(r"""() => {
                  const RE = /(?:\d+(?:[.,]\d+)?\s*[–—‑-]\s*\d+(?:[.,]\d+)?(?:\s*[–—‑-]\s*\d+(?:[.,]\d+)?)*%?)|(?:\d+(?:[.,]\d+)?%)/g;
                  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                  const nodes = []; while (walk.nextNode()) nodes.push(walk.currentNode);
                  let n = 0;
                  const RRE = /(?:\d+(?:[.,]\d+)?\s*[–—‑-]\s*\d+(?:[.,]\d+)?)|(?:\d+(?:[.,]\d+)?%)/;
                  document.querySelectorAll('bdi, .ev-code, .num').forEach(el => {
                    if (RRE.test(el.textContent || '')) { el.setAttribute('dir', 'ltr'); n++; }
                  });
                  for (const node of nodes) {
                    const p = node.parentElement; if (!p) continue;
                    const tag = p.tagName;
                    if (tag === 'SCRIPT' || tag === 'STYLE') continue;
                    const t = node.nodeValue || ''; if (!RE.test(t)) continue;
                    RE.lastIndex = 0;
                    const frag = document.createDocumentFragment(); let last = 0, m;
                    while ((m = RE.exec(t))) {
                      if (m.index > last) frag.appendChild(document.createTextNode(t.slice(last, m.index)));
                      const sp = document.createElement('span');
                      sp.setAttribute('dir', 'ltr'); sp.className = 'num-ltr';
                      sp.textContent = m[0].replace(/\s*([–—‑-])\s*/g, '$1');
                      frag.appendChild(sp); last = m.index + m[0].length;
                    }
                    if (last < t.length) frag.appendChild(document.createTextNode(t.slice(last)));
                    node.parentNode.replaceChild(frag, node); n++;
                  }
                  return n;
                }""")


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
        # ك-228: تقرير بلا أقسام مستندية (بعد نقل 11 قسمًا إلى «إضافات») لا يحتاج فهرسًا،
        # والتخطي مصرَّح به لا صامتًا. الفشل يبقى ممنوعًا إذا كانت هناك أقسام ولم يُدرج فهرسها.
        if not sections:
            print("  ℹ لا أقسام مستندية في هذه الصفحة ⇒ يُتخطّى الفهرس بلا فشل")
            return
        raise SystemExit("فشل إدراج الفهرس في الصفحة")


def page_index(pdf: Path) -> list[list[str]]:
    """أسطر كل صفحة مُوحَّدة — تُحذف أسطر الفهرس حتى لا تُحتسب مواضع للأقسام."""
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    pages: list[list[str]] = []
    for p in txt.split("\f"):
        lines = []
        for ln in p.split("\n"):
            clean = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", ln)
            if re.search(r"ص\s?\d+\s*$", clean.strip()):
                continue
            n = re.sub(r"^\d+", "", norm(clean))
            if n:
                lines.append(n)
        pages.append(lines)
    return pages


def norm(s: str) -> str:
    """توحيد النص لمقاومة تشويه الاستخراج: يحذف الأسطر والعلامات ويُبقي الحروف والأرقام."""
    s = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", s)
    return re.sub(r"[^\u0621-\u064A0-9A-Za-z]", "", s)


def locate_titles(pages_lines: list[list[str]], sections: list[dict]) -> dict[str, str]:
    """صفحة العنوان بشرط أن يكون العنوان **سطرًا مستقلًا** لا ذكرًا داخل فقرة.

    عطل ك-241: المطابقة السابقة كانت تقبل أول صفحة يرد فيها نص العنوان داخل أي فقرة،
    فسُجّل «الوقائع الجديدة ص 3» و«الخلفية ص 6» وهما في ص 6 و ص 9 فعلًا.
    """
    out: dict[str, str] = {}
    seen: set[str] = set()
    for s in sections:
        t = re.sub(r"^\d+", "", norm(s["title"]))
        if len(t) < 4 or t in seen:
            out[s["title"]] = "—"
            continue
        seen.add(t)
        found = "—"
        for i, lines in enumerate(pages_lines, 1):
            if i == 1:            # ك-241: الغلاف/الفهرس ليس موضعًا لعنوان قسم
                continue
            hit = any(l == t or (l.startswith(t) and len(l) <= len(t) + 3) for l in lines)
            if hit:
                found = str(i)
                break
        out[s["title"]] = found
    return out


def _require_system_tools() -> int:
    """فحص متطلبات النظام قبل الطباعة — برسائل علاج صريحة (2 = فشل مانع)."""
    miss = [c for c in ("pdftoppm", "pdftotext", "pdfinfo") if not shutil.which(c)]
    if miss:
        print("✘ متطلبات نظام ناقصة: " + ", ".join(miss))
        print("  العلاج: sudo apt-get update && sudo apt-get install -y poppler-utils")
        return 2
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            b.close()
    except Exception as exc:
        print("✘ تعذّر تشغيل Chromium: " + str(exc).splitlines()[0][:150])
        print("  العلاج: sudo python3 -m playwright install-deps chromium")
        return 2
    try:
        fam = subprocess.run(["fc-list", ":lang=ar", "family"], capture_output=True, text=True).stdout
        if not fam.strip():
            print("• لا خط عربي متاح — قد يخرج النص العربي مربعات في PDF")
            print("  العلاج: sudo apt-get install -y fonts-hosny-amiri fonts-noto-core fontconfig && sudo fc-cache -f")
    except FileNotFoundError:
        pass
    return 0


def main() -> int:
    _rc = _require_system_tools()
    if _rc:
        return _rc
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="تاريخ الإصدار YYYY-MM-DD")
    ap.add_argument("--only", choices=["pdf", "map", "both"], default="both")
    ap.add_argument("--no-toc", action="store_true", help="بلا فهرس محتويات")
    ap.add_argument("--no-header", action="store_true", help="بلا ترويسة وتذييل")
    ap.add_argument("--no-additions", action="store_true",
                    help="يبني PDF التقرير وحده بلا ملحق «إضافات» (للمقارنة والقياس)")
    ap.add_argument("--extra-css", help="ملف CSS اختباري يُحقن بعد أنماط PDF (للمعاينة التجريبية فقط)")
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
    hide_id = sources_section_id(html_src)
    print(f"حجب قسم المصادر: {hide_id or 'لم يُعثر على القسم'}")

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

                # ك-242: عزل النطاقات الرقمية والنسب في الطباعة لمنع انعكاس «24–72» إلى «72–24»

                if not args.no_additions:
                    _add = DIST / "additions.html"
                    if _add.exists():
                        _src = _add.read_text(encoding="utf-8")
                        _m = re.search(r"<main[^>]*>(.*?)</main>", _src, re.S)
                        _html = _m.group(1) if _m else ""
                        # منع تصادم المعرّفات مع أقسام التقرير (المصدر واحد)
                        _html = re.sub(r'id="sec-(\d+)"', r'id="sec-add-\1"', _html)
                        _n = pg.evaluate("""(html)=>{const host=document.querySelector('.wrap');
                          if(!host) return 0;
                          document.querySelectorAll('.additions-annex').forEach(e=>e.remove());
                          const d=document.createElement('div'); d.className='additions-annex';
                          d.innerHTML='<section class="doc" id="sec-additions"><h2>إضافات</h2><div class="h-rule"></div>'
                            +'<p class="annex-note">المجموعة المنقولة من التقرير اليومي — مرجعها الدائم صفحة «إضافات» على الموقع.</p></section>'+html;
                          const foot=host.querySelector('.foot'); host.insertBefore(d, foot||null);
                          return d.querySelectorAll('section.doc').length;}""", _html)
                        print(f"ملحق إضافات: {_n} قسمًا")
                if args.extra_css:
                    _extra = Path(args.extra_css).read_text(encoding="utf-8")
                    pg.add_style_tag(content=_extra)
                    print(f"أنماط اختبارية مُحقونة: {args.extra_css}")
                pg.add_style_tag(content=PDF_CSS.replace(
                    "{HIDE_SOURCES}",
                    f"#{hide_id}{{display:none !important}}" if hide_id else ""))

                sections = sections_of(pg, hide_id)
                kwargs = dict(format="A4", print_background=True, margin=margins,
                              tagged=True, outline=True)
                if not args.no_header:
                    kwargs.update(display_header_footer=True,
                                  header_template=HEADER_TPL.format(IDENT=ident),
                                  footer_template=FOOTER_TPL)

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
                    pass1 = Path(fh.name)
                if args.no_toc:
                    print(f"عزل النطاقات: {isolate_numbers(pg)} موضعًا")
                    pg.pdf(path=str(out_pdf), **kwargs)
                    pages_map = None
                else:
                    inject_toc(pg, sections, None)
                    print(f"عزل النطاقات: {isolate_numbers(pg)} موضعًا")
                    pg.pdf(path=str(pass1), **kwargs)
                    pages_map = locate_titles(page_index(pass1), sections)
                    inject_toc(pg, sections, pages_map)
                    print(f"عزل النطاقات: {isolate_numbers(pg)} موضعًا")
                    pg.pdf(path=str(out_pdf), **kwargs)
                    pass1.unlink(missing_ok=True)
                pg.emulate_media(media="screen")
                result["pdf"] = f"{out_pdf} ({out_pdf.stat().st_size/1024:.0f} ك.ب)"
                if pages_map:
                    found = sum(1 for v in pages_map.values() if v != "—")
                    result["toc"] = f"{len(pages_map)} قسمًا · أرقام صفحات مُثبتة لـ{found}"

            if args.only in ("map", "both"):
                # ك-174: الخريطة تظهر في وضع الطباعة لا على الشاشة — نلتقطها في وضعها الصحيح
                pg.emulate_media(media="print")
                pg.wait_for_timeout(300)
                el = pg.query_selector(".map-wrap") or pg.query_selector(".map-svg")
                if el:
                    try:
                        pg.evaluate("(e)=>{e.style.display='block';e.style.visibility='visible';e.style.overflow='visible';e.scrollIntoView({block:'center'});}", el)
                        pg.wait_for_timeout(600)
                        box = el.bounding_box()
                        if not box or box.get("width", 0) < 50 or box.get("height", 0) < 50:
                            raise RuntimeError("صندوق الخريطة غير صالح")
                        pg.screenshot(path=str(out_png), clip=box)
                        result["map"] = f"{out_png} ({out_png.stat().st_size/1024:.0f} ك.ب)"
                    except Exception as exc:
                        result["map"] = f"تعذّر تصوير الخريطة: {type(exc).__name__}: {exc}"
                else:
                    result["map"] = "لم يُعثر على عنصر الخريطة في الصفحة"
        finally:
            browser.close()

    for k, v in result.items():
        print(f"[{k}] {v}")
    # بوابة إلزامية: لا يُقبل PDF مخالف للشكل المعتمد (v3) الذي اعتمده صاحب القرار
    if out_pdf.exists():
        if os.environ.get("SKIP_FORMAT_GATE") == "1":
            print("!! بوابة الشكل مُتجاوزة (SKIP_FORMAT_GATE=1) — للمعايرة فقط")
        else:
            gate = subprocess.run([sys.executable, str(B / "validators" / "check_pdf_format.py"),
                                   "--pdf", str(out_pdf), "--date", args.date],
                                  capture_output=True, text=True)
            print(gate.stdout.strip())
            if gate.returncode != 0:
                print("!! الشكل مخالف للمعتمد — لا يُسلَّم هذا الملف حتى يُصلح أو يُعتمد تغييرًا جديدًا")
                # بند 5 (19 أكتوبر 2026): مخالفة الشكل مانع برمز 2 في السلّم الموحّد
                # (0 نجاح · 1 تحذير · 2 مانع) — كانت تُصنَّف «تحذيرًا» فيُمرّ التسليم.
                return max(2, gate.returncode)
        # جودة الطباعة (ك-104 · ك-105): عرض/ارتفاع كتلة الخريطة وتصفير المتن.
        # تُقاس على ملف PDF المولَّد نفسه وبوسائط print التي بُني بها، وتمنع الإفراج.
        if os.environ.get("SKIP_PRINT_QUALITY") == "1":
            print("!! بوابة جودة الطباعة مُتجاوزة (SKIP_PRINT_QUALITY=1) — للمعايرة فقط")
        else:
            page_html = DIST / "reports" / f"{args.date}.html"
            pq = subprocess.run([sys.executable, str(B / "validators" / "check_print_quality.py"),
                                 "--pdf", str(out_pdf), "--page", str(page_html),
                                 "--date", args.date],
                                capture_output=True, text=True)
            print(pq.stdout.strip())
            if pq.returncode != 0:
                print("!! جودة الطباعة مخالفة — لا يُسلَّم هذا الملف ولا يُنشر ولا يُرسل")
                return max(2, pq.returncode)

    return 0


if __name__ == "__main__":
    sys.exit(main())


def _isolate_period(html):
    """ك-256: عزل نطاق الفترة الزمنية كوحدة LTR واحدة قبل الطباعة."""
    import re as _re
    pat = _re.compile(r"(\d{6}Z)\s*[\u2013\u2014-]\s*(\d{6}Z)")
    return pat.sub(lambda m: '<bdi class="bidi" dir="ltr">%s\u2013%s</bdi>' % (m.group(1), m.group(2)), html)
