import asyncio, json, pathlib
from playwright.async_api import async_playwright
B = "https://seawatch-xp4qirmr.manus.space"
OUT = pathlib.Path("/home/ubuntu/audit-2026-10-30/shots")
async def run():
    res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for tag, url in (("ar", f"{B}/reports/2026-11-01.html"), ("en", f"{B}/reports/en/2026-11-01.html")):
            for name, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
                pg = await b.new_page(viewport={"width": w, "height": h})
                r = await pg.goto(url, wait_until="load", timeout=90000)
                await pg.wait_for_timeout(900)
                m = await pg.evaluate("""() => {
                  const q = (s) => document.querySelectorAll(s);
                  const vis = (el) => { const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && getComputedStyle(el).display !== 'none'; };
                  return { sectors: q('.mp-sectors rect').length, sectorLbl: q('.mp-sector-lbl').length,
                    tss: q('.mp-tss-main polygon').length, tssTxt: (q('.mp-tss-main text')[0]||{}).textContent||null,
                    lbl2: [...q('.lbl-2')].filter(vis).length, lbl3: [...q('.lbl-3')].filter(vis).length,
                    alt: q('.mp-alt-list li').length, evRows: q('.mp-ev-table tbody tr').length,
                    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth };
                }""")
                m["status"] = r.status if r else None
                res[f"{tag}-{name}"] = m
                if name == "desktop":
                    el = await pg.query_selector(".hero-map")
                    if el:
                        await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
                        await el.screenshot(path=str(OUT / f"live-p1p2-{tag}.png"))
                await pg.close()
        await b.close()
    print(json.dumps(res, ensure_ascii=False, indent=1))
asyncio.run(run())
