import os
import asyncio, json, pathlib
from playwright.async_api import async_playwright

import os as _os, pathlib as _pl
_D = _os.environ.get("DATE") or "2026-11-01"
_ROOT = _pl.Path(_os.environ.get("SITE") or _os.environ.get("SITE_DIR") or "seawatch")
URL = (_ROOT / f"dist/reports/{_D}.html").resolve().as_uri()
URL_EN = (_ROOT / f"dist/reports/en/{_D}.html").resolve().as_uri()
OUT = pathlib.Path(_os.environ.get("SHOTS") or "/tmp/shots")


async def measure(pg):
    return await pg.evaluate("""() => {
      const out = {};
      const q = (s) => document.querySelectorAll(s);
      const vis = (el) => { const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && getComputedStyle(el).display !== 'none'; };
      out.sectorRects = q('.mp-sectors rect').length;
      out.sectorLabels = q('.mp-sector-lbl').length;
      out.sectorTop = q('.mp-sector-top').length;
      out.tssPoly = q('.mp-tss-main polygon').length;
      out.tssRoute = (q('.mp-tss-main text')[0]||{}).textContent || null;
      out.lbl2 = [...q('.lbl-2')].filter(vis).length;
      out.lbl3 = [...q('.lbl-3')].filter(vis).length;
      out.altItems = q('.mp-alt-list li').length;
      out.altLen = (document.querySelector('#map-alt')||{}).textContent?.length || 0;
      out.evRows = q('.mp-ev-table tbody tr').length;
      out.keyGroups = q('.mp-key .lg-group').length;
      out.attrRows = q('.mp-key li').length;
      out.markers = q('.mp-events > g').length;
      out.badgeIds = [...q('.mp-events .mp-badge-t')].map(e => (e.textContent||'').trim()).filter(Boolean);
      out.pageOverflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
      const wrap = document.querySelector('.map-wrap');
      out.wrapOverflowX = wrap ? getComputedStyle(wrap).overflowX : null;
      // أصغر نص مرئي داخل الخريطة
      const sizes = [];
      q('.map-svg text').forEach(t => { if (vis(t)) sizes.push(parseFloat(getComputedStyle(t).fontSize)); });
      out.minFont = sizes.length ? Math.min(...sizes) : null;
      // أقل مسافة بين علامتين مرئيتين
      const pts = [...q('.mp-events .mp-dot, .mp-events .mp-halo')].map(e => {
        const r = e.getBoundingClientRect(); return {x: r.x + r.width/2, y: r.y + r.height/2}; });
      let minD = null;
      for (let i = 0; i < pts.length; i++) for (let j = i+1; j < pts.length; j++) {
        const d = Math.hypot(pts[i].x - pts[j].x, pts[i].y - pts[j].y);
        if (minD === null || d < minD) minD = d; }
      out.minMarkerDist = minD === null ? null : Math.round(minD * 10) / 10;
      // هل يحجب الشريط العلوي أي عنصر تنفيذي؟
      const top = document.querySelector('.site-topbar, .topbar-inner, header');
      out.blockedActionable = 0;
      if (top) { const tr = top.getBoundingClientRect();
        q('a[href], button, summary').forEach(el => { const r = el.getBoundingClientRect();
          if (r.width > 0 && r.height > 0 && r.top < tr.bottom && r.bottom > tr.top &&
              r.left < tr.right && r.right > tr.left && el !== top) out.blockedActionable++; }); }
      return out;
    }""")


async def run():
    res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            pg = await b.new_page(viewport={"width": w, "height": h})
            await pg.goto(URL, wait_until="load", timeout=90000)
            await pg.wait_for_timeout(900)
            res[name] = await measure(pg)
            await pg.screenshot(path=str(OUT / f"p1p2-map-{name}.png"), full_page=False)
            await pg.close()
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        await pg.goto(URL_EN, wait_until="load", timeout=90000)
        await pg.wait_for_timeout(900)
        res["en_desktop"] = await measure(pg)
        await pg.screenshot(path=str(OUT / "p1p2-map-en-desktop.png"), full_page=False)
        await pg.close()
        await b.close()
    print(json.dumps(res, ensure_ascii=False, indent=1))


asyncio.run(run())