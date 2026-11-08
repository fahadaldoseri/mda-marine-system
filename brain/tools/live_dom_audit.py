#!/usr/bin/env python3
"""تدقيق بصري حي بقياس DOM حقيقي (بديل مسار regex في live_visual_audit.py).

لماذا: مسار regex السابق كان يقرأ HTML بلا DOM/CSS/JS، فيعدّ التكرار داخل عناصر
مخفية (`.map-viz{display:none}`) تكرارًا حقيقيًا، ولا يقيس التخطيط ولا أهداف اللمس
ولا الصور المكسورة. هذا القياس يعمل داخل المتصفح (Playwright/Chromium) على المقاسين
الجوال وسطح المكتب، ويستثني غير المرئي، ويخرج JSON + رمز خروج مانع عند أي مخالفة.

الاستعمال:
  python3 tools/live_dom_audit.py --url <رابط أو file://…> [--url …] \
      [--min-touch 44] [--json out.json] [--shots dir]

الرمز: 0 = لا مخالفات · 1 = تحذيرات · 2 = مخالفة مانعة (أو تعذّر التحميل).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import Error as PWError
except ImportError as exc:  # فشل مغلق: غياب Playwright يمنع التدقيق (لا يبتلع أخطاء أخرى)
    print(f"✘ تعذّر استيراد Playwright: {exc}", file=sys.stderr)
    sys.exit(2)

MOBILE = (390, 844)
DESKTOP = (1440, 900)

JS = r"""
(opts) => {
  const minTouch = opts.minTouch;
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return false;
    if (r.width < 1 || r.height < 1) return false;
    return true;
  };
  const out = {dup: [], touch: [], broken: [], empty: [], hiddenInteractive: [],
               clipped: [], lang: document.documentElement.lang || '',
               toolbar: {}, counts: {}};

  // 1) تكرار نصّي بين العناصر المرئية فقط (عتبة 60 محرفًا)
  const seen = new Map();
  document.querySelectorAll('p, li, td, th, div, span, figcaption, h2, h3').forEach(el => {
    if (!visible(el)) return;
    if (el.closest('[aria-hidden="true"]')) return;   // فهرس بصري زخرفي: لا يُعدّ تكرار محتوى
    if (el.children.length > 0) return;              // الأوراق فقط
    // ك-524: حقول البطاقة القيمية (الوسم، درجة الموثوقية، الرمز) بيانات لا محتوى؛
    // تكرار القيمة نفسها بين بطاقات مختلفة سليم، فلا يُحتسب تكرارًا نصيًّا مرئيًّا.
    if (el.hasAttribute('data-reliability') || el.hasAttribute('data-classification')) return;
    if (el.classList.contains('ev-badge') || el.classList.contains('ev-reliability')
        || el.classList.contains('ev-code') || el.classList.contains('ev-idx')) return;
    const t = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (t.length < 60) return;
    if (seen.has(t)) out.dup.push({text: t.slice(0, 90), first: seen.get(t), again: el.tagName.toLowerCase()});
    else seen.set(t, el.tagName.toLowerCase());
  });

  // 2) أهداف اللمس المرئية
  document.querySelectorAll('a[href], button, [role="button"], summary, input, select').forEach(el => {
    if (!visible(el)) return;
    const r = el.getBoundingClientRect();
    if (r.height < minTouch || r.width < minTouch)
      out.touch.push({tag: el.tagName.toLowerCase(), cls: (el.className || '').toString().slice(0, 50),
                      txt: (el.textContent || '').trim().slice(0, 34),
                      w: +r.width.toFixed(1), h: +r.height.toFixed(1)});
  });

  // 3) صور مكسورة أو بلا نص بديل
  document.querySelectorAll('img').forEach(el => {
    const ok = el.complete && el.naturalWidth > 0;
    if (!ok) out.broken.push({src: (el.getAttribute('src') || '').slice(0, 80), alt: el.getAttribute('alt') || ''});
    else if (visible(el) && !(el.getAttribute('alt') || '').trim())
      out.broken.push({src: (el.getAttribute('src') || '').slice(0, 80), alt: 'MISSING'});
  });

  // 4) وسوم مرئية فارغة (خارج p/li/td/th)
  document.querySelectorAll('button, div, section, span, h2, h3, nav, aside').forEach(el => {
    if (!visible(el)) return;
    if (el.children.length > 0) return;
    const t = (el.textContent || '').replace(/\s+/g, '');
    if (el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('role')) return;
    if (/\b(h-rule|rule|sep|divider|spacer|bar|icon)\b/.test((el.className||'').toString())) return;
    if (t === '' && !el.querySelector('img, svg, iframe, video')) {
      const r = el.getBoundingClientRect();
      out.empty.push({tag: el.tagName.toLowerCase(), cls: (el.className || '').toString().slice(0, 50),
                      w: +r.width.toFixed(1), h: +r.height.toFixed(1)});
    }
  });

  // 5) عناصر تفاعلية موجودة لكن مخفية دائمًا (شيفرة ميتة)
  document.querySelectorAll('button, a[href]').forEach(el => {
    if (visible(el)) return;
    const id = el.id || '';
    if (id && /btn-|sn-/.test(id)) out.hiddenInteractive.push({id: id, tag: el.tagName.toLowerCase()});
  });

  // 6) قص أفقي حقيقي داخل حاويات التمرير
  document.querySelectorAll('nav, .sc-jump, .sn-links, .sx-grid, .tbl-wrap').forEach(el => {
    if (!visible(el)) return;
    if (el.clientWidth >= 12 && el.scrollWidth > el.clientWidth + 8) {
      // حاوية التمرير المقصودة مع مؤشر معلن ليست عيبًا مقيسًا
      if ((el.className || '').toString().includes('sc-jump') && document.querySelector('.sc-jump-hint')) return;
      // حاوية بتمرير أفقي مقصود: المحتوى قابل للوصول، فلا يُعدّ قصًّا مانعًا
      var ox = getComputedStyle(el).overflowX;
      if (ox === 'auto' || ox === 'scroll') return;
      out.clipped.push({cls: (el.className || el.tagName).toString().slice(0, 40),
                        ratio: +(el.scrollWidth / Math.max(1, el.clientWidth)).toFixed(2),
                        overflowX: getComputedStyle(el).overflowX});
    }
  });

  // 7) أزرار الشريط
  ['sn-theme', 'sn-print', 'sn-lang', 'sn-menu', 'sn-scale-up', 'sn-scale-down'].forEach(id => {
    const el = document.getElementById(id);
    out.toolbar[id] = el ? (visible(el) ? 'visible' : 'hidden') : 'absent';
  });
  out.counts = {dup: out.dup.length, touch: out.touch.length, broken: out.broken.length,
                empty: out.empty.length, hiddenInteractive: out.hiddenInteractive.length,
                clipped: out.clipped.length};
  return out;
}
"""


def audit(url: str, shots: Path | None, min_touch: int) -> dict:
    result: dict = {"url": url, "viewports": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, (w, h) in (("mobile", MOBILE), ("desktop", DESKTOP)):
            ctx = browser.new_context(viewport={"width": w, "height": h})
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="load", timeout=60000)
                page.wait_for_timeout(500)
                # فتح القائمة الجوالية لقياس ما داخلها
                try:
                    menu = page.query_selector(".sn-menu") or page.query_selector("#sn-menu")
                    if menu:
                        menu.click()
                        page.wait_for_timeout(300)
                except PWError:   # فشل تفاعل القائمة لا يُسقط القياس
                    pass
                data = page.evaluate(JS, {"minTouch": min_touch})
                data["http_status"] = 200
            except PWError as exc:   # فشل التصفح يُسجَّل خطأً في النتيجة لا يُبتلع
                data = {"error": str(exc)[:160], "http_status": 0,
                        "counts": {"dup": 0, "touch": 0, "broken": 0, "empty": 0,
                                   "hiddenInteractive": 0, "clipped": 0}}
            if shots:
                shots.mkdir(parents=True, exist_ok=True)
                slug = url.rstrip("/").split("/")[-1].replace(".html", "") or "root"
                try:
                    page.screenshot(path=str(shots / f"{slug}-{name}.png"), full_page=False)
                except PWError:   # تعذّر اللقطة لا يُسقط التدقيق
                    pass
            result["viewports"][name] = data
            ctx.close()
        browser.close()
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", required=True, help="رابط أو مسار file:// (يتكرر)")
    ap.add_argument("--min-touch", type=int, default=44)
    ap.add_argument("--expect", action="append", default=[],
                    help="URL=SHA256: لا يُدقَّق إلا ما يطابق بناءنا")
    ap.add_argument("--json", default="")
    ap.add_argument("--shots", default="")
    a = ap.parse_args()

    shots = Path(a.shots) if a.shots else None
    expects = {}
    for item in a.expect:
        if "=" in item:
            u, s = item.rsplit("=", 1)
            expects[u.strip()] = s.strip()
    identity_fail, urls = [], []
    for u in a.url:
        want = expects.get(u)
        if not want:
            urls.append(u)
            continue
        try:
            req = urllib.request.Request(u, headers={
                "User-Agent": "Mozilla/5.0 (compatible; mda-marine-system-live-audit/1.0)"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read()
            got = hashlib.sha256(body).hexdigest()
        except Exception as exc:
            identity_fail.append(f"{u}: تعذّر جلب الصفحة للتحقق من الهوية ({str(exc)[:70]})")
            continue
        if got == want:
            urls.append(u)
        else:
            identity_fail.append(
                f"{u}: القناة لا تخدم بناءنا (بصمة {got[:12]} ≠ {want[:12]}) — لا يُدقَّق محتوى جهة أخرى")
    reports = [audit(u, shots, a.min_touch) for u in urls]
    blocking, warnings = [], []
    for rep in reports:
        for vp, d in rep["viewports"].items():
            if d.get("http_status") != 200:
                blocking.append(f"{rep['url']} [{vp}]: تعذّر التحميل ({d.get('error','')[:80]})")
                continue
            c = d["counts"]
            if c["dup"]:
                warnings.append(f"{rep['url']} [{vp}]: {c['dup']} تكرار نصّي مرئي")
            if c["broken"]:
                blocking.append(f"{rep['url']} [{vp}]: {c['broken']} صورة مكسورة أو بلا نص بديل")
            if c["empty"]:
                warnings.append(f"{rep['url']} [{vp}]: {c['empty']} وسم مرئي فارغ")
            if c["hiddenInteractive"]:
                warnings.append(f"{rep['url']} [{vp}]: {c['hiddenInteractive']} عنصر تفاعلي مخفي دائمًا")
            if vp == "mobile" and c["touch"]:
                blocking.append(f"{rep['url']} [{vp}]: {c['touch']} هدف لمس أصغر من {a.min_touch}px")
            if vp == "mobile" and c["clipped"]:
                warnings.append(f"{rep['url']} [{vp}]: قص أفقي في {c['clipped']} حاوية")

    if a.json:
        Path(a.json).write_text(json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8")

    print("── تدقيق بصري حي بقياس DOM ──")
    for rep in reports:
        for vp, d in rep["viewports"].items():
            c = d.get("counts", {})
            print(f"   {rep['url']} [{vp}] · حالة {d.get('http_status')} · "
                  f"تكرار {c.get('dup',0)} · لمس {c.get('touch',0)} · صور {c.get('broken',0)} · "
                  f"فارغ {c.get('empty',0)} · ميت {c.get('hiddenInteractive',0)} · قص {c.get('clipped',0)} · "
                  f"أزرار {json.dumps(d.get('toolbar', {}), ensure_ascii=False)[:90]}")
    blocking = identity_fail + blocking
    for b in blocking:
        print(f"   ✘ {b}")
    for w in warnings:
        print(f"   ! {w}")
    if blocking:
        print("   النتيجة: منع")
        return 2
    if warnings:
        print("   النتيجة: تحذيرات (لا منع)")
        return 1
    print("   النتيجة: نظيف")
    return 0


if __name__ == "__main__":
    sys.exit(main())
