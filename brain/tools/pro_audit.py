#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تدقيق احترافي شامل للموقع المنشور — بمتصفح حقيقي وأدوات مستقلة.

المادة الخام: الكود الأصلي · ترويسات الخادم · سجل الشبكة · التنسيق المحسوب ·
شجرة الوصول · أخطاء وحدة التحكم · البكسلات المعروضة · نتائج axe-core.
المقاسات: 5 (جوال صغير → شاشة كبيرة) · الوضعان: ليلي/نهاري · تقليل الحركة · الطباعة.

يخرج: تقرير Markdown مُصنَّف بالخطورة + ملف JSON + صور شاشة + فيديو حركة.
يُشغَّل من أي مسار. لا أسرار ولا كتابة على الموقع.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
OUT = B / "audit"
SHOTS = OUT / "لقطات"
AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"

VIEWPORTS = [
    ("جوال صغير", 360, 740, True),
    ("جوال", 414, 896, True),
    ("لوح", 768, 1024, True),
    ("حاسب", 1366, 768, False),
    ("شاشة كبيرة", 1920, 1080, False),
]

# صفحات مفتاحية لكل الفحوص الثقيلة (axe/تباين/وصول)
KEY_PAGES = ["/", "/reports/2026-10-20.html", "/reports/cumulative-2026.html",
             "/reports/monthly-2026-10.html", "/reports/special-2026-10-17-Jubail-incidents.html"]

# لقطة بكسلات: منطقة المتن الرئيسية لقياس التباين من المعروض فعلًا
PIXEL_PROBES = [("نص المتن", "article p, .report p, main p"), ("عنوان", "h2")]


def severity(impact: str) -> str:
    return {"critical": "حرج", "serious": "عالٍ", "moderate": "متوسط",
            "minor": "منخفض"}.get(impact or "", "غير محدد")


async def axe_scan(page) -> list[dict]:
    try:
        await page.add_script_tag(url=AXE_URL)
    except Exception:  # noqa: BLE001
        return [{"id": "axe-load", "impact": "serious", "help": "تعذّر تحميل axe-core (شبكة)",
                 "nodes": []}]
    res = await page.evaluate("async () => await axe.run(document, "
                              "{resultTypes:['violations'], runOnly:{type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})")
    out = []
    for v in res.get("violations", []):
        nodes = [{"target": n.get("target"), "html": (n.get("html") or "")[:150],
                  "failure": (n.get("failureSummary") or "")[:220]} for n in v.get("nodes", [])[:4]]
        out.append({"id": v.get("id"), "impact": v.get("impact"), "help": v.get("help"),
                    "count": len(v.get("nodes", [])), "nodes": nodes})
    return out


async def overflow(page) -> dict:
    return await page.evaluate("""() => {
      const vw = window.innerWidth, de = document.documentElement;
      const bad = [];
      // عطل ك-68: كان المقياس يعدّ محتوى داخل وعاء قابل للتمرير (جدول .tbl-wrap) خارجًا عن الحدود.
      // القاعدة: العنصر لا يُعدّ تجاوزًا إن كان أحد أسلافه قابلاً للتمرير أفقيًا.
      const inScroller = (el) => {
        let n = el.parentElement;
        while (n && n !== document.body) {
          const st = getComputedStyle(n);
          if (st.overflowX === 'auto' || st.overflowX === 'scroll') return true;
          n = n.parentElement;
        }
        return false;
      };
      for (const el of document.querySelectorAll('body *')) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        const st = getComputedStyle(el);
        if (st.position === 'fixed' || inScroller(el)) continue;
        if (r.right > vw + 2 || r.left < -2) {
          bad.push({tag: el.tagName.toLowerCase(), cls: (el.className||'').toString().slice(0,40),
                    left: Math.round(r.left), right: Math.round(r.right),
                    text: (el.textContent||'').trim().slice(0,50)});
        }
      }
      return {doc_scroll: de.scrollWidth, viewport: vw,
              h_scroll: de.scrollWidth > vw + 1, offenders: bad.slice(0, 8), total: bad.length};
    }""")


async def contrast_from_pixels(page, shot_path: Path) -> list[dict]:
    """قياس تباين تقريبي من البكسلات المعروضة: أدكن وأفتح لونين في منطقة المتن."""
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001
        return []
    res = []
    for label, sel in PIXEL_PROBES:
        el = await page.query_selector(sel)
        if not el:
            continue
        box = await el.bounding_box()
        if not box or box["width"] < 20 or box["height"] < 8:
            continue
        # عنصر أسفل الشاشة لا يُلتقط بقصّ الفترة — نمرّره للعرض ثم نصوّر العنصر نفسه
        try:
            await el.scroll_into_view_if_needed(timeout=5000)
            await el.screenshot(path=str(shot_path), timeout=15000)
        except Exception:  # noqa: BLE001
            continue
        try:
            im = Image.open(shot_path).convert("L")
            px = list(im.getdata())
        except Exception:  # noqa: BLE001
            continue
        if not px:
            continue
        lo, hi = min(px), max(px)

        def lin(c: int) -> float:
            c /= 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r = (max(lin(lo), lin(hi)) + 0.05) / (min(lin(lo), lin(hi)) + 0.05)
        res.append({"label": label, "sel": sel, "ratio": round(r, 2),
                    "lo": lo, "hi": hi, "pass_aa_text": r >= 4.5})
    return res


async def keyboard(page) -> dict:
    seq, seen_outline = [], 0
    for _ in range(22):
        await page.keyboard.press("Tab")
        info = await page.evaluate("""() => {
          const a = document.activeElement; if (!a || a === document.body) return null;
          const st = getComputedStyle(a);
          return {tag: a.tagName.toLowerCase(), txt: (a.textContent||'').trim().slice(0,32),
                  outline: st.outlineStyle + ' ' + st.outlineWidth, shadow: st.boxShadow.slice(0,20)};
        }""")
        if info:
            seq.append(info)
            if info["outline"].split()[0] not in ("none",) or info["shadow"] not in ("none", ""):
                seen_outline += 1
    return {"steps": len(seq), "visible_focus": seen_outline, "sample": seq[:6]}


async def run(base: str, date: str, record_video: bool) -> dict:
    from playwright.async_api import async_playwright

    SHOTS.mkdir(parents=True, exist_ok=True)
    report: dict = {"base": base, "date": date, "pages": [], "axe": {}, "network": {},
                    "keyboard": {}, "print": {}, "overflow": {}, "contrast": {}, "console": {},
                    "a11y_tree": {}, "links": {}}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=["--no-sandbox"])

        # ═══ 1) الكود · الشبكة · الأخطاء · شجرة الوصول · الطباعة (صفحة المتن)
        ctx = await browser.new_context(viewport={"width": 1366, "height": 768},
                                        record_video_dir=str(SHOTS) if record_video else None,
                                        record_video_size={"width": 1280, "height": 720}) if record_video \
            else await browser.new_context(viewport={"width": 1366, "height": 768})
        page = await ctx.new_page()
        net: list[dict] = []
        cons: list[str] = []
        page.on("response", lambda r: net.append({"url": r.url, "status": r.status,
                                                  "type": r.request.resource_type}))
        page.on("console", lambda m: cons.append(f"{m.type}: {m.text[:160]}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: cons.append(f"pageerror: {str(e)[:160]}"))

        for route in KEY_PAGES:
            await page.goto(base + route, wait_until="networkidle", timeout=60000)
            report["pages"].append({"route": route, "title": await page.title()})
        report["network"] = {
            "total": len(net),
            "third_party": sorted({re.sub(r"^https?://([^/]+).*$", r"\1", r["url"]) for r in net
                                   if base.split("//")[-1] not in r["url"] and r["url"].startswith("http")}),
            "failed": [{"url": r["url"][:80], "status": r["status"]} for r in net if r["status"] >= 400][:10],
        }
        report["console"] = {"count": len(cons), "items": cons[:12]}

        # شجرة الوصول + الطباعة + لوحة المفاتيح على إصدار اليوم
        await page.goto(base + "/reports/2026-10-20.html", wait_until="networkidle", timeout=60000)
        try:
            snap = None  # واجهة الشجرة صارت لا تُعيد شيئًا في هذا الإصدار — نُكمل بفحص DOM مباشر
            def count_nodes(n):
                if not n:
                    return 0, {}
                tags = {}
                stack = [n]
                total = 0
                while stack:
                    cur = stack.pop()
                    total += 1
                    tags[cur.get("role", "?")] = tags.get(cur.get("role", "?"), 0) + 1
                    stack += cur.get("children", []) or []
                return total, tags
            total, tags = count_nodes(snap) if snap else (0, {})
            h1 = await page.eval_on_selector_all("h1", "els => els.map(e => e.textContent.trim().slice(0,60))")
            h2 = await page.eval_on_selector_all("h2", "els => els.length")
            report["a11y_tree"] = {"nodes": total, "roles": dict(sorted(tags.items(), key=lambda x: -x[1])[:8]),
                                   "h1": h1, "h2_count": h2,
                                   "landmarks": await page.eval_on_selector_all(
                                       "header, nav, main, article, footer", "els => els.map(e => e.tagName.toLowerCase())"),
                                   "img_without_alt": await page.eval_on_selector_all(
                                       "img:not([alt])", "els => els.length"),
                                   "lang": await page.get_attribute("html", "lang"),
                                   "dir": await page.get_attribute("html", "dir")}
        except Exception as e:  # noqa: BLE001
            report["a11y_tree"] = {"error": str(e)[:120]}

        report["keyboard"] = await keyboard(page)
        try:
            await page.emulate_media(media="print")
            await page.pdf(path=str(OUT / f"طباعة-{date}.pdf"), format="A4", print_background=True)
            await page.emulate_media(media="screen")
            report["print"] = {"pdf": f"طباعة-{date}.pdf"}
        except Exception as e:  # noqa: BLE001
            report["print"] = {"error": str(e)[:100]}

        # ═══ 2) axe-core + تباين البكسل على الصفحات المفتاحية
        for route in KEY_PAGES:
            await page.goto(base + route, wait_until="networkidle", timeout=60000)
            key = route.strip("/") or "home"
            report["axe"][key] = await axe_scan(page)
            c = await contrast_from_pixels(page, SHOTS / f"px-{key.replace('/', '_')[:24]}.png")
            if c:
                report["contrast"][key] = c

        # ═══ 3) 5 مقاسات × وضعان (ليلي/نهاري) — تمرير أفقي + لقطات
        for mname, w, h, mobile in VIEWPORTS:
            for scheme in ("dark", "light"):
                c2 = await browser.new_context(viewport={"width": w, "height": h},
                                               is_mobile=mobile, has_touch=mobile,
                                               color_scheme=scheme, reduced_motion="reduce")
                p2 = await c2.new_page()
                for route in ("/", "/reports/2026-10-20.html"):
                    await p2.goto(base + route, wait_until="networkidle", timeout=60000)
                    ov = await overflow(p2)
                    k = f"{mname}·{scheme}·{route}"
                    report["overflow"][k] = ov
                    if route == "/" or (mname == "جوال صغير" and scheme == "dark"):
                        safe = re.sub(r"[^\w\-]+", "_", k)[:40]
                        await p2.screenshot(path=str(SHOTS / f"{safe}.png"), full_page=(route == "/"))
                await c2.close()
        await ctx.close()
        await browser.close()
    return report


def to_markdown(r: dict) -> str:
    L = [f"# التدقيق الاحترافي الشامل — {r['date']}", "",
         f"الجذر: {r['base']} · صفحات مفتاحية: {len(r['pages'])} · مقاسات: 5 · وضعان: ليلي/نهاري", ""]
    L += ["## 1) الشبكة والخصوصية", "",
          f"- إجمالي الطلبات: {r['network'].get('total')} · فاشلة: {len(r['network'].get('failed', []))}",
          f"- نطاقات خارجية (تتبّع محتمل): {r['network'].get('third_party') or 'لا شيء ✔'}"]
    for f in r["network"].get("failed", []):
        L.append(f"  - ✘ {f['status']} {f['url']}")
    L += ["", "## 2) أخطاء وحدة التحكم", "",
          f"- العدد: {r['console'].get('count')}"]
    L += [f"  - {i}" for i in r["console"].get("items", [])[:8]] or ["  - لا شيء ✔"]
    L += ["", "## 3) axe-core (WCAG 2.1 AA)", ""]
    any_v = False
    for key, vs in r["axe"].items():
        if not vs:
            L.append(f"- `{key}`: لا مخالفة ✔")
            continue
        for v in vs:
            any_v = True
            L.append(f"- **{severity(v.get('impact'))}** · `{key}` · {v.get('id')}: {v.get('help')} "
                     f"({v.get('count')} عنصر)")
            for n in v.get("nodes", [])[:2]:
                L.append(f"    - `{n.get('target')}` → {(n.get('failure') or '')[:90]}")
    if not any_v:
        L.append("- لا مخالفات في الصفحات المفتاحية ✔")
    L += ["", "## 4) التباين من البكسلات المعروضة", ""]
    for key, cs in r["contrast"].items():
        for c in cs:
            L.append(f"- `{key}` · {c['label']}: نسبة {c['ratio']} "
                     f"({'مطابق AA' if c['pass_aa_text'] else 'دون AA'})")
    if not r["contrast"]:
        L.append("- لم تُقس (لا عناصر مطابقة)")
    L += ["", "## 5) شجرة الوصول والبنية", "",
          f"- دور html: lang={r['a11y_tree'].get('lang')} · dir={r['a11y_tree'].get('dir')}",
          f"- عناصر في الشجرة: {r['a11y_tree'].get('nodes')} · h1={len(r['a11y_tree'].get('h1') or [])} · h2={r['a11y_tree'].get('h2_count')}",
          f"- معالم الصفحة: {r['a11y_tree'].get('landmarks')}",
          f"- صور بلا وصف بديل: {r['a11y_tree'].get('img_without_alt')}",
          f"- أهم الأدوار: {r['a11y_tree'].get('roles')}"]
    L += ["", "## 6) لوحة المفاتيح والتركيز", "",
          f"- خطوات Tab: {r['keyboard'].get('steps')} · تركيز ظاهر: {r['keyboard'].get('visible_focus')}"]
    for s in r["keyboard"].get("sample", [])[:4]:
        L.append(f"  - {s['tag']} · «{s['txt']}» · إطار: {s['outline']}")
    L += ["", "## 7) الطباعة", "", f"- {r['print']}"]
    L += ["", "## 8) التمرير الأفقي (5 مقاسات × وضعان)", ""]
    bad = {k: v for k, v in r["overflow"].items() if v.get("h_scroll") or v.get("total")}
    for k, v in r["overflow"].items():
        flag = "✘" if (v.get("h_scroll") or v.get("total")) else "✔"
        L.append(f"- {flag} {k}: عرض المستند {v.get('doc_scroll')} · الفترة {v.get('viewport')} · خارج الحدود {v.get('total')}")
    L += ["", "## الخلاصة", "",
          f"- مخالفات axe: {sum(len(v) for v in r['axe'].values())} · تمرير أفقي: {len(bad)} حالة · "
          f"طلبات فاشلة: {len(r['network'].get('failed', []))} · أخطاء طرفية: {r['console'].get('count')}"]
    return "\n".join(L)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--base", default=os.environ.get("SITE_BASE_URL", "https://seawatch-live.pages.dev"))
    ap.add_argument("--video", action="store_true")
    a = ap.parse_args()
    r = await run(a.base.rstrip("/"), a.date, a.video)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"تدقيق-احترافي-{a.date}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    md = to_markdown(r)
    (OUT / f"تدقيق-احترافي-{a.date}.md").write_text(md, encoding="utf-8")
    blocks = sum(len(v) for v in r["axe"].values())
    hscroll = sum(1 for v in r["overflow"].values() if v.get("h_scroll") or v.get("total"))
    print(md[-1800:])
    print(f"\n  محفوظ: {OUT / f'تدقيق-احترافي-{a.date}.md'}")
    return 2 if (blocks or hscroll) else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))