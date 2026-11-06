#!/usr/bin/env python3
"""قياس تدفّق الطباعة للتقرير اليومي — يعيد بناء صفحة الطباعة كما يفعل المُصدّر.

لماذا: المُصدّر يحقن ملحق «إضافات» و`PDF_CSS` داخل Chromium وقت التصدير، فلا يكفي قياس
`dist/reports/<date>.html` وحده — القياس الخاطئ يعطي كتلًا وصفحات أقل من الحقيقة.
هذا السكربت يعيد البناء نفسه: يخدم `dist`، يحمّل صفحة التقرير، يحقن الملحق ثم `PDF_CSS`
ثم يقيس التدفّق ويسمّي الكتلة التي تبدأ كل صفحة والفراغ الذي خلّفته.

الاستخدام:
  python3 measure_report_print_flow.py --date 2026-10-29 \\
      [--brain /home/ubuntu/brain-marine-news] [--site /home/ubuntu/seawatch] \\
      [--extra-css /tmp/fix.css] [--dump 8] [--port 8911]

ترتيب الحقن مهم: --extra-css قبل PDF_CSS إن أردت اختبار قاعدة تُلغي غيرها بنفس الأهمية.
الفراغ هنا تقديري؛ الفراغ الحاكم من `measure_pdf_pages.py` على PDF نفسه.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

JS_COLLECT = r"""
() => {
  const out = [];
  const host = document.querySelector('.wrap') || document.body;
  host.querySelectorAll('section.doc, .additions-annex, section.print-map').forEach(sec => {
    const sid = sec.id || sec.className;
    [...sec.children].forEach(e => {
      const r = e.getBoundingClientRect();
      if (r.height < 2) return;
      const cs = getComputedStyle(e);
      out.push({sec: sid, tag: e.tagName.toLowerCase(),
                cls: (e.className || '').toString().slice(0, 34),
                top: Math.round(r.top + window.scrollY), h: Math.round(r.height),
                brk: cs.breakInside,
                txt: (e.innerText || '').replace(/\s+/g, ' ').slice(0, 46)});
    });
  });
  return out.sort((a, b) => a.top - b.top);
}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="قياس تدفّق طباعة التقرير اليومي")
    ap.add_argument("--date", required=True)
    ap.add_argument("--brain", default="/home/ubuntu/brain-marine-news")
    ap.add_argument("--site", default="/home/ubuntu/seawatch")
    ap.add_argument("--extra-css", default=None)
    ap.add_argument("--dump", type=int, default=0)
    ap.add_argument("--port", type=int, default=8911)
    args = ap.parse_args()

    B, DIST = Path(args.brain), Path(args.site) / "dist"
    exporter = B / "tools" / "export_report_assets.py"
    if not exporter.exists():
        print(f"✘ لا مُصدِّر في {exporter}", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("era_flow", exporter)
    era = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(era)
    pdf_css = era.PDF_CSS.replace("{HIDE_SOURCES}", "")

    from playwright.sync_api import sync_playwright

    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(args.port), "--bind", "127.0.0.1", "-d", str(DIST)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch(args=["--no-sandbox"])
            ctx = br.new_context(viewport={"width": 1280, "height": 1800}, locale="ar")
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{args.port}/reports/{args.date}.html", wait_until="load")
            pg.wait_for_timeout(900)
            pg.emulate_media(media="print")
            add = DIST / "additions.html"
            if add.exists():
                html = add.read_text(encoding="utf-8")
                m = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
                body = re.sub(r'id="sec-(\d+)"', r'id="sec-add-\1"', m.group(1) if m else "")
                pg.evaluate(
                    """(html)=>{const host=document.querySelector('.wrap'); if(!host) return 0;
                    document.querySelectorAll('.additions-annex').forEach(e=>e.remove());
                    const d=document.createElement('div'); d.className='additions-annex';
                    d.innerHTML='<section class="doc" id="sec-additions"><h2>إضافات</h2>'
                      +'<div class="h-rule"></div><p class="annex-note">ملحق</p></section>'+html;
                    const foot=host.querySelector('.foot'); host.insertBefore(d, foot||null);
                    return 1;}""",
                    body,
                )
            if args.extra_css:
                pg.add_style_tag(content=Path(args.extra_css).read_text(encoding="utf-8"))
            pg.add_style_tag(content=pdf_css)
            pg.wait_for_timeout(400)
            blocks = pg.evaluate(JS_COLLECT)
            br.close()
    finally:
        srv.terminate()

    mm = 3.7795275591
    H = 297 - 9 - 12  # متن A4 بهوامش المُصدّر: 9مم أعلى · 12مم أسفل
    page, ends = 1, []
    for blk in blocks:
        top, h = blk["top"] / mm, blk["h"] / mm
        page_top = (page - 1) * H
        if top + h > page_top + H and h <= H:
            ends.append((page + 1, blk, (page_top + H) - top))
            page += 1
    last = (blocks[-1]["top"] + blocks[-1]["h"]) / mm if blocks else 0
    print(f"   كتل: {len(blocks)} · صفحات محاكاة: {page} · آخر موضع: {last:.1f} مم · ارتفاع المتن {H:.0f} مم")
    print("   تنبيه: أرقام الفراغ تقديرية للمقارنة النسبية ولا تُحتجّ بها؛ الفراغ الحاكم من measure_pdf_pages.py على PDF.")
    for p, blk, leftover in ends:
        gate = "  ← مرشّح لفراغ ≥45مم (تحقّق من PDF)" if leftover >= 45 else ""
        print(f"   → ص{p} يبدأ بـ[{blk['sec']} › {blk['tag']}] h={blk['h'] / mm:.1f}مم · "
              f"محاكاة {leftover:.1f}مم · brk={blk['brk']}{gate}")
    big = [b for b in blocks if b["h"] / mm >= H * 0.6]
    for b in sorted(big, key=lambda x: -x["h"]):
        print(f"   ⚠ كتلة ذرّية محتملة: {b['h'] / mm:.1f}مم [{b['sec']} › {b['tag']}] {b['txt']}")
    if args.dump:
        print(f"   ── آخر {args.dump} كتلة ──")
        for blk in blocks[-args.dump:]:
            print(f"      [{blk['sec']} › {blk['tag']}] top={blk['top'] / mm:.1f} h={blk['h'] / mm:.1f} · {blk['txt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
