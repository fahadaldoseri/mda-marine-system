#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة وضوح سطح الحاسوب (فشل مغلق):
  1) لا نص مرئي أصغر من 12px على مقاس الحاسوب،
  2) لا فيض أفقي مقصوص (scrollWidth > clientWidth مع overflow مخفي) ولا خروج عن نافذة العرض،
  3) لا عنصر تفاعلي خارج نافذة العرض أفقيًا،
  4) لا عنصر نصي مقصوص رأسيًا بسبب -webkit-line-clamp.

الاستخدام:
  python3 validators/check_desktop_readability.py --site "$SITE" --date 2026-11-01 [--json out.json]
"""
from __future__ import annotations

import os
import pathlib
import argparse, asyncio, json, sys

MEASURE = r"""
() => {
  const P = [];
  const vis = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    if (el.closest('[hidden],[aria-hidden="true"],.no-print')) return false;
    return true;
  };
  const own = (el) => Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
  const path = (el) => {
    const id = el.id ? '#' + el.id : '';
    const cls = (el.className && typeof el.className === 'string') ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + cls;
  };
  const vw = window.innerWidth;
  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el)) continue;
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    const px = parseFloat(cs.fontSize);
    if (own(el) && px > 0 && px < 12) {
      P.push({kind: 'font', sel: path(el), size: px, text: (el.textContent || '').trim().slice(0, 46), x: Math.round(r.x), y: Math.round(r.y)});
    }
    if (own(el)) {
      const clipped = cs.overflowX !== 'visible' || cs.overflowY !== 'visible';
      if (clipped && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 4)) {
        P.push({kind: 'clip', sel: path(el), sw: el.scrollWidth, cw: el.clientWidth, sh: el.scrollHeight, ch: el.clientHeight,
                text: (el.textContent || '').trim().slice(0, 40)});
      }
      const clamp = cs.webkitLineClamp || cs.getPropertyValue('-webkit-line-clamp');
      if (clamp && clamp !== 'none' && el.scrollHeight > el.clientHeight + 2) {
        P.push({kind: 'clamp', sel: path(el), clamp: clamp, sh: el.scrollHeight, ch: el.clientHeight,
                text: (el.textContent || '').trim().slice(0, 40)});
      }
    }
    // داخل SVG: العناصر تُقصّ على حدود الرسم نفسه، فلا تُعدّ خروجًا عن النافذة.
    const inSvg = el.ownerSVGElement !== undefined;
    // وإن كان أحد الآباء يقصّ الفائض، فالعنصر مقصوص لا خارج النافذة.
    const clippedByAncestor = (node) => {
      for (let a = node.parentElement; a && a !== document.body; a = a.parentElement) {
        const acs = getComputedStyle(a);
        if (acs.overflowX !== 'visible' || acs.overflowY !== 'visible') return true;
      }
      return false;
    };
    const outOfWindow = (r.right > vw + 1 || r.left < -1);
    if (outOfWindow && !inSvg && !clippedByAncestor(el) && el.tagName !== 'HTML' && el.tagName !== 'BODY') {
      P.push({kind: 'offscreen', sel: path(el), x: Math.round(r.x), right: Math.round(r.right), vw: vw,
              text: (el.textContent || '').trim().slice(0, 40)});
    }
    if (['BUTTON', 'A', 'INPUT', 'SELECT', 'SUMMARY'].includes(el.tagName) && outOfWindow && !clippedByAncestor(el)) {
      P.push({kind: 'control-offscreen', sel: path(el), x: Math.round(r.x), right: Math.round(r.right)});
    }
  }
  return {docScroll: document.documentElement.scrollWidth, vw: vw, problems: P};
}
"""


async def measure_pages(site: pathlib.Path, date: str, widths: list[int], pages: list[str]) -> dict:
    from playwright.async_api import async_playwright
    out = {"pages": [], "problems": []}
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        for rel in pages:
            f = site / rel
            if not f.exists():
                out["pages"].append({"file": rel, "exists": False})
                continue
            for w in widths:
                pg = await b.new_page(viewport={"width": w, "height": 900})
                await pg.goto(f.as_uri(), wait_until="load")
                await pg.wait_for_timeout(400)
                res = await pg.evaluate(MEASURE)
                font = [p for p in res["problems"] if p["kind"] == "font"]
                clip = [p for p in res["problems"] if p["kind"] == "clip"]
                clamp = [p for p in res["problems"] if p["kind"] == "clamp"]
                off = [p for p in res["problems"] if p["kind"] in ("offscreen", "control-offscreen")]
                out["pages"].append({"file": rel, "width": w, "font_lt12": len(font), "clip": len(clip),
                                     "clamp": len(clamp), "offscreen": len(off),
                                     "docScroll": res["docScroll"], "vw": res["vw"],
                                     "samples": (font[:4] + clip[:3] + clamp[:3] + off[:4])})
                for p in font:
                    out["problems"].append(f"{rel}@{w} خط {p['size']}px في {p['sel']}: «{p['text']}»")
                for p in clip:
                    out["problems"].append(f"{rel}@{w} فيض مقصوص في {p['sel']} ({p['sw']}>{p['cw']})")
                for p in clamp:
                    out["problems"].append(f"{rel}@{w} نص مقصوص بـline-clamp في {p['sel']} ({p['sh']}>{p['ch']})")
                for p in off:
                    out["problems"].append(f"{rel}@{w} خارج النافذة: {p['sel']} x={p.get('x')}")
                if res["docScroll"] > w + 1:
                    out["problems"].append(f"{rel}@{w} تمرير أفقي غير مقصود: {res['docScroll']} > {w}")
                await pg.close()
        await b.close()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=os.environ.get("SITE") or os.environ.get("SITE_DIR") or str(pathlib.Path(__file__).resolve().parents[1].parent / "seawatch"))
    ap.add_argument("--date", required=True)
    ap.add_argument("--widths", default="1440,1920")
    ap.add_argument("--json")
    args = ap.parse_args()
    site = pathlib.Path(args.site)
    widths = [int(x) for x in args.widths.split(",") if x.strip()]
    safe = args.date.replace("/", "")
    pages = ["dist/index.html", f"dist/reports/{safe}.html", f"dist/reports/en/{safe}.html",
             "dist/additions.html", "dist/sources.html", "dist/archive.html", "dist/dashboard.html"]
    if not (site / pages[1]).exists():
        # جرّب مسار الأرشيف البديل
        alt = [f"dist/reports/{safe}.html"]
        pages = alt + pages[:1] + pages[2:]
    try:
        res = asyncio.run(measure_pages(site, safe, widths, pages))
    except (OSError, ValueError, RuntimeError, asyncio.TimeoutError) as e:
        # تضييق مقصود 2026-11-02: أخطاء التشغيل المتوقعة فقط؛ أي انهيار آخر يمرّ بحارس الانهيار الموحّد (رمز 70).
        print(f"  ✘ فشل مغلق: تعذّر تشغيل الفحص البصري ({type(e).__name__}: {e})")
        return 2
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("   ── سطح الحاسوب ──")
    for p in res["pages"]:
        if not p.get("exists", True):
            continue
        print(f"      {p['file']}@{p['width']}: خط<12={p['font_lt12']} · فيض={p['clip']} · قص={p['clamp']} · خارج={p['offscreen']}")
    if res["problems"]:
        print(f"  ✘ فشل مغلق — {len(res['problems'])} مخالفة لوضوح سطح الحاسوب:")
        for x in res["problems"][:18]:
            print("     -", x)
        if len(res["problems"]) > 18:
            print(f"     ... و{len(res['problems']) - 18} أخرى")
        return 2
    print("  ✔ سطح الحاسوب: لا نص أقل من 12px · لا فيض ولا قص ولا خروج عن النافذة")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ولا يُبتلع.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
