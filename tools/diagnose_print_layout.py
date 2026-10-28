#!/usr/bin/env python3
"""تشخيص أخطاء الطباعة بمسارين مستقلين:
  أ) قياس حي في المتصفح (DOM في وضع الطباعة): كتل غير مرئية تشغل فراغًا، ونصوص مقصوصة.
  ب) قياس بصري حقيقي للورق: شرائط بيضاء داخل منطقة المحتوى في ملف PDF.

الاستخدام:
  python3 tools/diagnose_print_layout.py --date 2026-10-18 [--pdf <pdf>]
"""
from __future__ import annotations
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
import re
import subprocess
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
DIST = Path(f"{SITE}/dist/reports")
MM_PER_PX = 25.4 / 96  # قياس CSS في وضع الطباعة


def dom_scan(html: Path) -> tuple[list, list, list]:
    """قياس حي: كتل غير مرئية بحجم كبير · نصوص مقصوصة · عناصر بارتفاع ثابت."""
    from playwright.sync_api import sync_playwright

    invisible, clipped, tall = [], [], []
    with sync_playwright() as pw:
        br = pw.chromium.launch(args=["--no-sandbox"])
        pg = br.new_page(viewport={"width": 794, "height": 1123})
        pg.emulate_media(media="print")
        pg.goto(html.as_uri(), wait_until="load")
        pg.wait_for_timeout(800)
        data = pg.evaluate("""() => {
          const out = {inv: [], clip: [], tall: []};
          for (const el of document.querySelectorAll('body *')) {
            const cs = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            const hmm = r.height * 25.4 / 96, wmm = r.width * 25.4 / 96;
            if (r.height < 1 || r.width < 1) continue;
            const invisible = cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05;
            if (invisible && hmm >= 8) {
              out.inv.push({cls: el.className.toString().slice(0,60), id: el.id,
                            vis: cs.visibility, op: cs.opacity, h: +hmm.toFixed(1)});
            }
            if (el.scrollHeight > el.clientHeight + 4 && cs.overflow !== 'visible' && hmm >= 4) {
              out.clip.push({cls: el.className.toString().slice(0,60), id: el.id,
                             over: el.scrollHeight - el.clientHeight, h: +hmm.toFixed(1),
                             txt: (el.textContent||'').trim().slice(0,50)});
            }
            if (hmm >= 60) out.tall.push({cls: el.className.toString().slice(0,50), id: el.id,
                                          h: +hmm.toFixed(1), w: +wmm.toFixed(1),
                                          vis: cs.visibility, txt:(el.textContent||'').trim().slice(0,40)});
          }
          return out;
        }""")
        br.close()
    invisible = sorted(data["inv"], key=lambda x: -x["h"])[:15]
    clipped = sorted(data["clip"], key=lambda x: -x["over"])[:15]
    tall = sorted(data["tall"], key=lambda x: -x["h"])[:20]
    return invisible, clipped, tall


def visual_scan(pdf: Path, margin_top_mm: float = 9, margin_bottom_mm: float = 11,
                min_gap_mm: float = 9) -> list[tuple[int, float, float]]:
    """قياس بصري: شرائط بيضاء داخل منطقة المحتوى (مع استثناء الترويسة والتذييل)."""
    from PIL import Image
    out = []
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", "100", "-png", str(pdf), f"{d}/p"],
                       capture_output=True, timeout=900)
        for f in sorted(Path(d).glob("p-*.png")):
            n = int(re.search(r"p-(\d+)", f.name).group(1))
            im = Image.open(f).convert("L")
            w, h = im.size
            px = im.load()
            dpi = 100
            top = int(margin_top_mm / 25.4 * dpi)
            bot = h - int(margin_bottom_mm / 25.4 * dpi)
            # صفوف فيها محتوى فعلي
            rows = []
            for y in range(top, bot):
                dark = sum(1 for x in range(0, w, 3) if px[x, y] < 225)
                rows.append(dark > 1)
            # اكتشاف أطول شريط فارغ
            best, start, cur = 0, None, None
            for i, has in enumerate(rows):
                if not has and cur is None:
                    cur = i
                elif has and cur is not None:
                    ln = i - cur
                    if ln > best:
                        best, start = ln, cur
                    cur = None
            if cur is not None and (len(rows) - cur) > best:
                best, start = len(rows) - cur, cur
            gmm = best / dpi * 25.4
            if gmm >= min_gap_mm:
                out.append((n, round(gmm, 1), round((top + start) / dpi * 25.4, 1)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--pdf")
    a = ap.parse_args()
    html = DIST / f"{a.date}.html"
    pdf = Path(a.pdf) if a.pdf else DIST / "pdf" / f"{a.date}.pdf"

    print("=" * 66)
    print("أ) قياس حي في المتصفح (وضع الطباعة)")
    print("=" * 66)
    inv, clip, tall = dom_scan(html)
    print("\nكتل غير مرئية تشغل فراغًا (8 مم فأكثر):")
    if not inv:
        print("  لا شيء ✓")
    for e in inv:
        tag = e["id"] and f"#{e['id']}" or ""
        print(f"  • {e['h']:6.1f} مم · {e['vis']} · opacity={e['op']} · {tag}{e['cls']}")
    print("\nنصوص مقصوصة (overflow مخفي مع محتوى زائد):")
    if not clip:
        print("  لا شيء ✓")
    for e in clip:
        print(f"  • زائد {e['over']:4d} بكسل · ارتفاع {e['h']:5.1f} مم · {e['cls']} · «{e['txt']}»")
    print("\nأطول عشر كتل (لفهم توزيع الصفحات):")
    for e in tall[:10]:
        print(f"  • {e['h']:6.1f} مم × {e['w']:5.1f} مم · {e['vis']} · {e['cls']} · {e['txt'][:34]}")

    print()
    print("=" * 66)
    print(f"ب) قياس بصري للورق: {pdf.name}")
    print("=" * 66)
    if not pdf.exists():
        print("  الملف غير موجود")
        return 0
    gaps = visual_scan(pdf)
    if not gaps:
        print("  لا فراغات داخلية ≥ 9 مم ✓")
    for page, gmm, at in gaps:
        print(f"  ✗ صفحة {page}: فراغ {gmm} مم يبدأ عند {at} مم من أعلى الورقة")
    total = sum(g for _, g, _ in gaps)
    print(f"\n  مجموع الفراغات الداخلية: {total:.0f} مم عبر {len(gaps)} موضعًا")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())