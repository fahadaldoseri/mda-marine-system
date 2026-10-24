#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوابة جودة الطباعة — ملزمة (فشل مغلق) · ك-104 · ك-105 · إصلاح ك-122
تقيس على مُخرج الطباعة نفسه (ملف PDF) لا على الشاشة:

  1) كتلة خريطة الوقائع في PDF: العرض والارتفاع بالمليمتر ونسبتهما من الورقة.
     القياس **هندسي**: أكبر كتلة تعبئة مصمتة (لون غالب ≥ 50% من مساحتها) لا يعتمد
     على لون بحر واحد، فيعمل مع أي لوحة (فاتحة أو داكنة) — إصلاح ك-122.
     الحدود في templates/approved-pdf/print-profile.json ← gates.min_map_width_frac
     و gates.min_map_height_frac (الافتراضي 0.70 و 0.32).

  2) تصفير المتن في PDF نفسه: تُجمع كلمات كل سطر من إحداثياتها، ويُحدَّد عمود
     المتن من أكثر حافة يمين تكرارًا، ثم تُقاس الحافة اليسرى للأسطر الممتلئة
     (عرضها ≥ 85% من عرض العمود). في الفقرة المصفّرة تبلغ كل الأسطر الممتلئة
     الطرف الأيسر نفسه؛ وفي المحاذاة لليمين تتقاصر. القياس بالإحداثيات فقط،
     فلا يتأثر بعكس الحروف العربية في الاستخراج.

  3) مؤشر استشاري (لا يمنع): نسبة الأسطر الممتلئة المتقصّرة.

  4) عند تمرير صفحة HTML للتقرير (--page) يُضاف فحص محاذاة حي في وسائط print
     كتأكيد ثانٍ (لا يعوّض القياس على PDF).

فشل مغلق: أي تعذّر في القياس = مخالفة مانعة.
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
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "templates" / "approved-pdf" / "print-profile.json"

DPI = 150
CELL = 8                      # خلية القياس بالبكسل ≈ 1.35 مم
MIN_MAP_HEIGHT_MM = 25
MIN_DOMINANT_SHARE = 0.50     # الكتلة المصمتة: لون واحد يغطي نصف مساحتها
MIN_MAP_WIDTH_FRAC_OF_TEXT = 0.45
RAG_MM = 3.0
JUSTIFY_TOL_MM = 2.5
JUSTIFY_MIN_FULL_LINES = 6
JUSTIFY_MIN_CLUSTER = 0.25
COLUMN_MIN_WIDTH_MM = 55

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


def _render_pages(pdf: Path, dpi: int = DPI) -> list[Path]:
    out = Path(tempfile.mkdtemp(prefix="pq-"))
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(out / "p")],
                   check=True, capture_output=True)
    return sorted(out.glob("p-*.png"))


# ───────────────────────── قياس كتلة الخريطة (هندسي) ─────────────────────────
def _components(mask, min_cells: int):
    h = len(mask)
    w = len(mask[0]) if h else 0
    seen = [[False] * w for _ in range(h)]
    out = []
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or seen[y][x]:
                continue
            q = deque([(y, x)])
            seen[y][x] = True
            cells = []
            while q:
                cy, cx = q.popleft()
                cells.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True
                            q.append((ny, nx))
            if len(cells) >= min_cells:
                ys = [c[0] for c in cells]
                xs = [c[1] for c in cells]
                out.append({"y0": min(ys), "y1": max(ys), "x0": min(xs), "x1": max(xs),
                            "cells": len(cells)})
    return out


def map_block_report(pdf: Path, dpi: int = DPI) -> dict:
    """يقيس كتلة الخريطة هندسيًا بلا افتراض لون بحر.

    الخطوات: أكبر كتلة تعبئة مصمتة (بحر ملوّن أو يابسة)، ثم تمديد عرضها إلى حدّي
    الخريطة الرأسيين إن وُجدا قريبين — فيُقاس البحر الأبيض بحدود الخريطة لا بمساحة
    اليابسة وحدها. تعمل مع أي لوحة فاتحة أو داكنة (ك-122).
    """
    try:
        import numpy as np
        from PIL import Image
    except Exception:
        return {"error": "numpy/PIL غير متوفرة"}
    mm = 25.4 / dpi
    res = {"w_mm": -1.0, "h_mm": -1.0, "page_w": 0.0, "page_h": 0.0, "page": "",
           "share": 0.0, "color": None, "pages": 0, "method": "", "extended": 0}
    try:
        pages = _render_pages(pdf, dpi)
    except Exception as exc:
        return {"error": f"تعذّر تحويل PDF إلى صور: {type(exc).__name__}"}
    if not pages:
        return {"error": "لا صفحات في ملف PDF"}
    res["pages"] = len(pages)
    best = None

    def _vrun(col) -> int:
        bl = cl = 0
        for v in col:
            cl = cl + 1 if v else 0
            if cl > bl:
                bl = cl
        return bl

    for img_path in pages:
        im = Image.open(img_path).convert("RGB")
        W, H = im.size
        res["page_w"] = max(res["page_w"], W * mm)
        res["page_h"] = max(res["page_h"], H * mm)
        a = np.asarray(im).astype(int)
        h, w = H // CELL, W // CELL
        if h < 8 or w < 8:
            continue
        g = a[:h * CELL, :w * CELL].reshape(h, CELL, w, CELL, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, CELL * CELL, 3)
        mx = g.max(axis=3)
        mn = g.min(axis=3)
        mean = g.mean(axis=3)
        light = (((mx - mn) >= 5) & (mean >= 115)).mean(axis=2) > 0.55
        dark = (mean < 110).mean(axis=2) > 0.80
        mask = light | dark
        for c in _components(mask.tolist(), min_cells=60):
            y0, y1, x0, x1 = c["y0"] * CELL, (c["y1"] + 1) * CELL, c["x0"] * CELL, (c["x1"] + 1) * CELL
            bw, bh = (x1 - x0) * mm, (y1 - y0) * mm
            if bh < MIN_MAP_HEIGHT_MM or bw < res["page_w"] * MIN_MAP_WIDTH_FRAC_OF_TEXT:
                continue
            patch = a[y0:y1, x0:x1].reshape(-1, 3)
            q = (patch // 24).astype(np.int32)
            key = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
            vals, counts = np.unique(key, return_counts=True)
            k = int(vals[int(counts.argmax())])
            share = float(counts.max()) / len(key)
            if share < MIN_DOMINANT_SHARE:
                continue
            # تمديد إلى حدود الخريطة الرأسية القريبة (حتى 12 مم)
            ink = a.mean(axis=2) < 235
            need = int(0.70 * (y1 - y0))
            band = int(12 / mm)
            nx0, nx1 = x0, x1
            for dx in range(1, band + 1):
                if x0 - dx >= 0 and _vrun(ink[y0:y1, x0 - dx]) >= need:
                    nx0 = x0 - dx
                    break
            for dx in range(1, band + 1):
                if x1 + dx < W and _vrun(ink[y0:y1, x1 + dx]) >= need:
                    nx1 = x1 + dx
                    break
            ext = 1 if (nx0 != x0 or nx1 != x1) else 0
            ebw = (nx1 - nx0) * mm
            area = ebw * bh
            if best is None or area > best[0]:
                best = (area, ebw, bh, img_path.name, share,
                        (int(k // 10000) * 24, int((k // 100) % 100) * 24, int(k % 100) * 24), ext)
    if best:
        res.update(w_mm=best[1], h_mm=best[2], page=best[3], share=best[4], color=best[5],
                   extended=best[6], method="تعبئة مصمتة" + (" + حدود الخريطة" if best[6] else ""))
    return res


# ───────────────────────── قياس التصفير من PDF نفسه ─────────────────────────
def _pdf_lines(pdf: Path) -> list[list[dict]]:
    xml = subprocess.run(["pdftotext", "-bbox-layout", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    pages = []
    for chunk in re.split(r"<page\b", xml)[1:]:
        lines = []
        for ln in re.split(r"<line\b", chunk)[1:]:
            ws = re.findall(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', ln)
            if not ws:
                continue
            lines.append({"x0": min(float(x[0]) for x in ws),
                          "x1": max(float(x[2]) for x in ws),
                          "y": min(float(x[1]) for x in ws),
                          "n": len(ws),
                          "t": " ".join(x[4] for x in ws)})
        pages.append(lines)
    return pages


def justify_report(pdf: Path) -> dict:
    """يقيس تجمّع الحافة اليسرى لأسطر المتن الطويلة في PDF (دليل التصفير في RTL).

    في المتن المصفّر تبلغ الأسطر الطويلة الطرف الأيسر نفسه فتتجمّع إحداثياته؛ وفي
    المحاذاة لليمين تتبعثر. المقياس بالإحداثيات فقط فلا يتأثر بعكس الحروف العربية
    في الاستخراج، ويُهمل أثر الوسوم المضمّنة التي تقطع بعض الأسطر قبل الطرف.
    """
    pt2mm = 25.4 / 72
    try:
        pages = _pdf_lines(pdf)
    except Exception as exc:
        return {"error": f"تعذّر استخراج إحداثيات النص: {type(exc).__name__}"}
    shares, pages_used = [], 0
    for i, lines in enumerate(pages, 1):
        if not lines:
            continue
        wmax = max(l["x1"] - l["x0"] for l in lines)
        col = [l for l in lines
               if (l["x1"] - l["x0"]) >= 0.60 * wmax and (l["x1"] - l["x0"]) * pt2mm >= COLUMN_MIN_WIDTH_MM]
        if len(col) < 6:
            continue
        left_min = min(l["x0"] for l in col)
        near = sum(1 for l in col if (l["x0"] - left_min) * pt2mm <= JUSTIFY_TOL_MM)
        shares.append(near / len(col))
        pages_used += 1
    if not shares:
        return {"error": "لا أسطر متن طويلة كافية للقياس"}
    share = sum(shares) / len(shares)
    return {"share": share, "pages": pages_used,
            "worst_page": min(shares), "best_page": max(shares)}


def rag_indicator(pdf: Path) -> tuple[int, float]:
    r = justify_report(pdf)
    if "error" in r:
        return 0, 0.0
    return r["short"], r["worst_mm"]


def alignment_report(page_path: Path) -> list[dict]:
    """تدقيق محاذاة حي في وسائط print (تأكيد ثانٍ عند تمرير صفحة HTML)."""
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
    if m.get("error"):
        problems.append(f"تعذّر قياس كتلة الخريطة في PDF: {m['error']} (فشل مغلق)")
    elif m["w_mm"] < 0:
        problems.append("لم تُعثر كتلة خريطة مصمتة في PDF (فشل مغلق)")
    else:
        fw = m["w_mm"] / m["page_w"]
        fh = m["h_mm"] / m["page_h"]
        ok = fw >= min_frac and fh >= min_h_frac
        print(f"  {'✓' if ok else '✘'} كتلة الخريطة {m['w_mm']:.0f}×{m['h_mm']:.0f} مم من "
              f"{m['page_w']:.0f}×{m['page_h']:.0f} مم = عرض {fw*100:.0f}% (الحد {min_frac*100:.0f}%) · "
              f"ارتفاع {fh*100:.0f}% (الحد {min_h_frac*100:.0f}%) · {m['page']} · "
              f"الطريقة: {m.get('method','—')}")
        if fw < min_frac:
            problems.append(f"عرض الخريطة {fw*100:.0f}% أقل من الحد {min_frac*100:.0f}%")
        if fh < min_h_frac:
            problems.append(f"ارتفاع الخريطة {fh*100:.0f}% أقل من الحد {min_h_frac*100:.0f}%")

    j = justify_report(pdf)
    if j.get("error"):
        problems.append(f"تعذّر قياس تصفير المتن من PDF: {j['error']} (فشل مغلق)")
    else:
        ok = j["share"] >= JUSTIFY_MIN_CLUSTER
        print(f"  {'✓' if ok else '✘'} تصفير المتن في PDF: تجمّع الحافة اليسرى "
              f"{j['share']*100:.0f}% (الحد {JUSTIFY_MIN_CLUSTER*100:.0f}%) · {j['pages']} صفحة "
              f"· أدنى صفحة {j['worst_page']*100:.0f}%")
        if not ok:
            problems.append(f"تجمّع الحافة اليسرى {j['share']*100:.0f}% أقل من الحد "
                            f"{JUSTIFY_MIN_CLUSTER*100:.0f}% — المتن لا يبلغ الطرف (غير مصفّر)")

    if page_path is not None and page_path.exists():
        if page_path.stat().st_mtime - pdf.stat().st_mtime > 60:
            problems.append("ملف PDF أقدم من صفحة التقرير — القياس على نسخة قديمة")
        try:
            bad = alignment_report(page_path)
            if bad:
                problems.append(f"{len(bad)} كتلة متن غير مصفّرة في وسائط الطباعة")
                for b in bad[:5]:
                    print(f"  ✘ غير مصفّر [{b['ta']}] <{b['tag']} .{b['cls']}> «{b['sample']}»")
            else:
                print("  ✓ تأكيد ثانٍ: كل كتل المتن مصفّرة في وسائط الطباعة")
        except Exception as exc:
            print(f"  • تعذّر التأكيد الحي على الصفحة ({type(exc).__name__}) — لا يمنع لأن قياس PDF تم")

    if problems:
        print("\nالمخالفات المانعة:")
        for p in problems:
            print(f"  ✘ {p}")
        print("النتيجة: مخالف لجودة الطباعة ✘")
        return 2
    print("النتيجة: مطابق لجودة الطباعة ✓")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
