#!/usr/bin/env python3
"""تدقيق طباعي آلي لملف PDF: المقاس، الهوامش، كثافة النص، الفراغات، أحجام الخطوط، الألوان.

الاستخدام:
  python3 tools/audit_pdf_layout.py --pdf /path/file.pdf [--dpi 100] [--out /tmp/audit]

المخرجات: تقرير نصي مطبوع + صور الصفحات في مجلد --out للمراجعة البصرية.
"""
from __future__ import annotations

import argparse
import collections
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return (p.stdout or "") + (p.stderr or "")


def word_boxes(pdf: Path) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as fh:
        tmp = fh.name
    run(["pdftotext", "-bbox", str(pdf), tmp])
    html = Path(tmp).read_text(encoding="utf-8", errors="ignore")
    Path(tmp).unlink(missing_ok=True)
    pages = []
    for pm in re.finditer(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', html, re.S):
        w, h, body = float(pm.group(1)), float(pm.group(2)), pm.group(3)
        words = []
        for wm in re.finditer(
            r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>',
            body, re.S):
            x0, y0, x1, y1 = (float(wm.group(i)) for i in range(1, 5))
            txt = re.sub(r"\s+", " ", wm.group(5)).strip()
            if txt:
                words.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "t": txt,
                              "h": y1 - y0, "w": x1 - x0})
        pages.append({"w": w, "h": h, "words": words})
    return pages


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--dpi", type=int, default=100)
    ap.add_argument("--out", default="/tmp/pdf-audit")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    info = run(["pdfinfo", str(pdf)])
    pages_n = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    size = re.search(r"Page size:\s+(.+)", info).group(1)
    print(f"الملف: {pdf.name} · الصفحات: {pages_n} · المقاس: {size}")

    # تصيير الصور للمراجعة البصرية
    run(["pdftoppm", "-r", str(args.dpi), "-png", str(pdf), str(out / "page")])
    rendered = sorted(out.glob("page-*.png"))

    from PIL import Image

    print("\n== الهوامش والفراغات وكثافة النص (بالمليمتر) ==")
    print(f"{'ص':>3} {'أعلى':>6} {'أسفل':>6} {'يمين':>6} {'يسار':>6} {'حشو%':>6} {'لون الخلفية':>14} {'كلمات':>6}")
    rows = []
    for i, img_path in enumerate(rendered, start=1):
        im = Image.open(img_path).convert("L")
        W, H = im.size
        px = im.load()
        # لون الخلفية = أكثر قيمة تكرارًا
        hist = im.histogram()
        bg = max(range(256), key=lambda v: hist[v])
        # صندوق المحتوى: أي بكسل يختلف عن الخلفية بأكثر من 18
        xs, ys = [], []
        step = 2
        for y in range(0, H, step):
            for x in range(0, W, step):
                if abs(px[x, y] - bg) > 18:
                    xs.append(x)
                    ys.append(y)
        if not xs:
            print(f"{i:>3} صفحة فارغة تمامًا")
            continue
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        mm_per_px = 210.0 / W  # عرض A4 = 210 مم
        top = y0 * mm_per_px
        bottom = (H - y1) * mm_per_px
        right = x1 * mm_per_px if False else (W - x1) * mm_per_px
        left = x0 * mm_per_px
        ink = sum(1 for y in range(0, H, step) for x in range(0, W, step) if abs(px[x, y] - bg) > 18)
        fill = 100.0 * ink / ((W // step) * (H // step))
        rows.append((i, top, bottom, left, right, fill))
        print(f"{i:>3} {top:6.1f} {bottom:6.1f} {right:6.1f} {left:6.1f} {fill:6.1f} {bg:>14} ")

    # أحجام الخطوط وعدد الكلمات من طبقة النص
    wp = word_boxes(pdf)
    print("\n== أحجام الخطوط (من صناديق الكلمات، بالنقاط) وعدد الكلمات لكل صفحة ==")
    all_h = []
    for idx, page in enumerate(wp, start=1):
        hs = sorted(w["h"] for w in page["words"])
        all_h += hs
        if not hs:
            print(f"{idx:>3} لا نص (صفحة رسومية)")
            continue
        med = hs[len(hs) // 2]
        print(f"{idx:>3} كلمات={len(hs):>4} · أصغر={hs[0]:.1f} · وسيط={med:.1f} · أكبر={hs[-1]:.1f}")
    if all_h:
        c = collections.Counter(round(h, 1) for h in all_h)
        print("\nأكثر أحجام الخطوط تكرارًا:", c.most_common(8))
        print(f"أصغر حجم خط في الملف: {min(all_h):.1f} نقطة · أكبر: {max(all_h):.1f} نقطة")

    print(f"\nالصور للمراجعة البصرية في: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())