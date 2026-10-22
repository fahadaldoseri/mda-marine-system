#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوابة جودة الطباعة — ملزمة (فشل مغلق) · ك-104 و ك-105
تقيس على مُخرج الطباعة نفسه (PDF والصفحة بوسائط print) لا على الشاشة:

  1) كتلة خريطة الوقائع في ملف PDF: العرض ≥ الحد المعتمد من عرض الورقة،
     والارتفاع ≥ الحد المعتمد من ارتفاع الورقة.
     الحدود في templates/approved-pdf/print-profile.json ← gates.min_map_width_frac
     و gates.min_map_height_frac (الافتراضي 0.70 و 0.32).

  2) تصفير المتن: تُفتح صفحة التقرير بوسائط print (نفس محرّك Chromium الذي
     يولّد PDF) وتُقرأ محاذاة كل كتلة متن تحمل نصًا مباشرًا. أي فقرة أو بند قائمة
     أو قيمة بطاقة قرار بطول 25 حرفًا وأكثر لا تكون `justify` = مخالفة مانعة.
     يُستثنى: العناوين، وخلايا الجداول، وشرائح المؤشرات، والوسوم، والمصادر،
     والفهرس، والخريطة، والتذييل.

  3) مؤشر استشاري (لا يمنع): نسبة الأسطر الممتلئة التي لا تبلغ طرف المتن في PDF.

فشل مغلق: أي تعذّر في القياس (ملف مفقود، أو محرّك الصفحة لم يعمل) = مخالفة مانعة.
الاستعمال:
  python3 validators/check_print_quality.py --pdf <file.pdf> [--page <file.html>]
رموز الخروج: 0 مطابق · 2 مخالفة مانعة.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "templates" / "approved-pdf" / "print-profile.json"

SEA = (214, 224, 234)            # لون بحر خريطة الوقائع في هيئة v3
SEA_TOL = 4
MIN_SEA_PIXELS_PER_ROW = 60
MIN_MAP_HEIGHT_MM = 30
RAG_MM = 3.0                     # فجوة تُعدّ سطرًا غير بالغ للطرف (استشاري)

ALIGN_SKIP_CLASSES = [
    "chip", "tag", "k-l", "k-n", "lbl", "brand", "legend", "map-", "bar-",
    "foot", "toc", "badge", "notice", "mono", "src", "cite-ref", "kv-k",
    "meta", "pill", "sev", "level",
]

ALIGN_JS_TMPL = """
() => {
  const bad = [];
  const SKIP_TAGS = new Set(['H1','H2','H3','H4','H5','H6','TH','TD','BUTTON','A','SUMMARY','LABEL']);
  const SKIP_CLASSES = __SKIP__;
  const sel = 'p, li, .dc-v, .kv-v, .sec-lede, .blk-lede, .note, .glossary li, figcaption';
  const direct = el => {
    let n = 0;
    for (const c of el.childNodes) if (c.nodeType === 3) n += (c.textContent || '').trim().length;
    return n;
  };
  for (const el of document.querySelectorAll(sel)) {
    if (direct(el) < 25) continue;
    if (SKIP_TAGS.has(el.tagName)) continue;
    let skip = false;
    for (const c of SKIP_CLASSES) {
      if (el.closest('[class*="' + c + '"]')) { skip = true; break; }
    }
    if (skip) continue;
    const cs = getComputedStyle(el);
    if (cs.textAlign !== 'justify') {
      bad.push({tag: el.tagName,
                cls: (el.className || '').toString().slice(0, 40),
                ta: cs.textAlign,
                sample: (el.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 50)});
    }
  }
  return bad;
}
"""


def _profile() -> dict:
    try:
        return json.loads(PROFILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _render_pages(pdf: Path, dpi: int = 150) -> list[Path]:
    out = Path(tempfile.mkdtemp(prefix="pq-"))
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(out / "p")],
                   check=True, capture_output=True)
    return sorted(out.glob("p-*.png"))


def map_block_report(pdf: Path) -> dict:
    """يقيس كتلة خريطة الوقائع في ملف PDF: العرض والارتفاع بالمليمتر ونسبتهما."""
    res = {"w_mm": -1.0, "h_mm": -1.0, "page_w": 0.0, "page_h": 0.0, "page": ""}
    try:
        from PIL import Image
    except Exception:
        return res
    for img_path in _render_pages(pdf):
        im = Image.open(img_path).convert("RGB")
        W, H = im.size
        px = im.load()
        res["page_w"] = max(res["page_w"], W / 150 * 25.4)
        res["page_h"] = max(res["page_h"], H / 150 * 25.4)
        rows = []
        for y in range(0, H, 2):
            xs = [x for x in range(0, W, 2)
                  if abs(px[x, y][0] - SEA[0]) <= SEA_TOL
                  and abs(px[x, y][1] - SEA[1]) <= SEA_TOL
                  and abs(px[x, y][2] - SEA[2]) <= SEA_TOL]
            if len(xs) >= MIN_SEA_PIXELS_PER_ROW:
                rows.append((y, min(xs), max(xs)))
        if not rows:
            continue
        w_mm = (max(r[2] for r in rows) - min(r[1] for r in rows)) / 150 * 25.4
        h_mm = (max(r[0] for r in rows) - min(r[0] for r in rows)) / 150 * 25.4
        if h_mm >= MIN_MAP_HEIGHT_MM and w_mm * h_mm > res["w_mm"] * max(res["h_mm"], 0):
            res.update(w_mm=w_mm, h_mm=h_mm, page=img_path.name)
    return res


def alignment_report(page_path: Path) -> list[dict]:
    """يدقّق محاذاة المتن في وسائط الطباعة نفسها التي يُبنى بها ملف PDF."""
    from playwright.sync_api import sync_playwright
    js = ALIGN_JS_TMPL.replace("__SKIP__", json.dumps(ALIGN_SKIP_CLASSES, ensure_ascii=False))
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.emulate_media(media="print")
        pg.goto(page_path.resolve().as_uri(), wait_until="load")
        pg.wait_for_timeout(500)
        bad = pg.evaluate(js)
        b.close()
    return bad


def rag_indicator(pdf: Path) -> tuple[int, float]:
    """مؤشر استشاري: (عدد الأسطر الممتلئة المتقصّرة، أقصى فجوة مم)."""
    try:
        xml = subprocess.run(["pdftotext", "-bbox-layout", str(pdf), "-"],
                             capture_output=True, text=True).stdout
    except Exception:
        return 0, 0.0
    short_total, worst = 0, 0.0
    for chunk in re.split(r'<page\b', xml)[1:]:
        lines = []
        for ln in re.split(r'<line\b', chunk)[1:]:
            w = re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', ln)
            if not w:
                continue
            lines.append({"x0": min(float(x[0]) for x in w),
                          "x1": max(float(x[2]) for x in w)})
        if not lines:
            continue
        col = max(l["x1"] - l["x0"] for l in lines)
        wide = [l for l in lines if (l["x1"] - l["x0"]) >= 0.7 * col]
        if len(wide) < 6:
            continue
        edge = min(l["x0"] for l in wide)
        short = [l for l in wide if (l["x0"] - edge) > RAG_MM * 72 / 25.4]
        short_total += len(short)
        if short:
            worst = max(worst, max(l["x0"] - edge for l in short) * 25.4 / 72)
    return short_total, worst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", default="")
    ap.add_argument("--date", default="")
    a = ap.parse_args()
    pdf = Path(a.pdf)
    if not pdf.exists():
        print(f"✘ ملف PDF غير موجود: {pdf}")
        return 2

    gates = _profile().get("gates", {})
    min_frac = float(gates.get("min_map_width_frac", 0.70))
    min_h_frac = float(gates.get("min_map_height_frac", 0.32))
    page_path = Path(a.page) if a.page else None

    print(f"بوابة جودة الطباعة · {pdf.name}" + (f" · صفحة: {page_path.name}" if page_path else ""))
    problems: list[str] = []

    m = map_block_report(pdf)
    if m["w_mm"] < 0:
        problems.append("تعذّر قياس كتلة الخريطة في ملف PDF (فشل مغلق)")
    else:
        fw = m["w_mm"] / m["page_w"]
        fh = m["h_mm"] / m["page_h"]
        ok = fw >= min_frac and fh >= min_h_frac
        print(f"  {'✓' if ok else '✘'} كتلة الخريطة {m['w_mm']:.0f}×{m['h_mm']:.0f} مم من "
              f"{m['page_w']:.0f}×{m['page_h']:.0f} مم = عرض {fw*100:.0f}% (الحد {min_frac*100:.0f}%) · "
              f"ارتفاع {fh*100:.0f}% (الحد {min_h_frac*100:.0f}%)")
        if fw < min_frac:
            problems.append(f"عرض الخريطة {fw*100:.0f}% أقل من الحد {min_frac*100:.0f}%")
        if fh < min_h_frac:
            problems.append(f"ارتفاع الخريطة {fh*100:.0f}% أقل من الحد {min_h_frac*100:.0f}%")

    if page_path is None:
        problems.append("لم تُحدَّد صفحة التقرير لتدقيق المحاذاة (فشل مغلق)")
    elif not page_path.exists():
        problems.append(f"صفحة التقرير غير موجودة: {page_path.name}")
    else:
        try:
            bad = alignment_report(page_path)
        except Exception as exc:
            problems.append(f"تعذّر تدقيق المحاذاة الحي: {type(exc).__name__} (فشل مغلق)")
            bad = []
            print(f"  ✘ تعذّر تدقيق المحاذاة الحي: {type(exc).__name__}: {str(exc)[:90]}")
        if bad:
            problems.append(f"{len(bad)} كتلة متن غير مصفّرة في وسائط الطباعة")
            for b in bad[:5]:
                print(f"  ✘ غير مصفّر [{b['ta']}] <{b['tag']} .{b['cls']}> «{b['sample']}»")
        elif not any("المحاذاة" in p for p in problems):
            print("  ✓ كل كتل المتن مصفّرة في وسائط الطباعة (justify)")

    short_n, worst_mm = rag_indicator(pdf)
    print(f"  • مؤشر استشاري: {short_n} سطرًا ممتلئًا لا يبلغ الطرف (أقصى فجوة {worst_mm:.0f} مم) — لا يمنع")

    if problems:
        print("\nالمخالفات المانعة:")
        for p in problems:
            print(f"  ✘ {p}")
        print("النتيجة: مخالف لجودة الطباعة ✘")
        return 2
    print("النتيجة: مطابق لجودة الطباعة ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())