import asyncio, json, pathlib
from playwright.async_api import async_playwright
import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument("--url", required=True)
_ap.add_argument("--out", default="/tmp/map-shots")
_A = _ap.parse_args()
URL = _A.url
OUT = pathlib.Path(_A.out); OUT.mkdir(parents=True, exist_ok=True)

async def run():
    res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            pg = await b.new_page(viewport={"width": w, "height": h})
            await pg.goto(URL, wait_until="load", timeout=90000)
            await pg.wait_for_timeout(900)
            m = await pg.evaluate("""() => {
              const out = {};
              const svg = document.querySelector('.hmap-svg');
              out.badge = !!document.querySelector('.mp-badge-t');
              out.decide = !!document.querySelector('.hmap-decide');
              out.cluster = document.querySelectorAll('.mp-cluster').length;
              const wrap = document.querySelector('.hmap-wrap');
              out.wrapOverflowX = wrap ? getComputedStyle(wrap).overflowX : null;
              out.wrapClientW = wrap ? wrap.clientWidth : 0;
              out.svgW = svg ? svg.getBoundingClientRect().width : 0;
              out.pageOverflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
              const sizes = [];
              document.querySelectorAll('.hmap-svg text').forEach(t => {
                const r = t.getBoundingClientRect();
                const fs = parseFloat(getComputedStyle(t).fontSize) * (r.width / (t.getComputedTextLength ? t.getComputedTextLength() || r.width : r.width));
                const vis = r.width > 0 && r.height > 0;
                if (vis) sizes.push({txt: (t.textContent||'').trim().slice(0,14), fs: Math.round(parseFloat(getComputedStyle(t).fontSize)*10)/10});
              });
              out.textCount = sizes.length;
              out.minFs = sizes.length ? Math.min(...sizes.map(s => s.fs)) : null;
              const small = sizes.filter(s => s.fs < 12);
              out.smallTexts = small.slice(0, 6);
              // مسافات مراكز العلامات على الشاشة
              const pts = [...document.querySelectorAll('.hmap-svg .mp-event')].map(g => {
                const r = g.getBoundingClientRect();
                return {x: r.x + r.width/2, y: r.y + r.height/2};
              });
              let mind = Infinity;
              for (let i=0;i<pts.length;i++) for (let j=i+1;j<pts.length;j++) {
                const d = Math.hypot(pts[i].x-pts[j].x, pts[i].y-pts[j].y);
                if (d < mind) mind = d;
              }
              out.markerCount = pts.length;
              out.minMarkerDist = isFinite(mind) ? Math.round(mind*10)/10 : null;
              const tb = document.querySelector('.topbar');
              out.topbarH = tb ? Math.round(tb.getBoundingClientRect().height) : 0;
              return out;
            }""")
            await pg.evaluate("window.scrollTo(0, 900)")
            await pg.wait_for_timeout(400)
            m["topbarH_scrolled"] = await pg.evaluate("Math.round(document.querySelector('.topbar').getBoundingClientRect().height)")
            el = await pg.query_selector(".hero-map")
            if el:
                await el.scroll_into_view_if_needed()
                await pg.wait_for_timeout(600)
                await el.screenshot(path=str(OUT / f"map-{name}.png"))
            res[name] = m
            await pg.close()
        await b.close()
    print(json.dumps(res, ensure_ascii=False, indent=1))
asyncio.run(run())
