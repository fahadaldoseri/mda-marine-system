#!/usr/bin/env python3
"""فحص توزيع الصفحات والفراغات واكتمال النص في ملف PDF مقابل مصدره.

الاستخدام:
  python3 tools/audit_pagination.py --pdf <file.pdf> [--source <file.md>] [--label اسم]

يقيس:
  · الفراغ أسفل كل صفحة (مم) والفراغات الداخلية (نطاقات فارغة)
  · العنوان المعلّق في نهاية صفحة
  · نسبة تغطية النص مقابل المصدر + العناوين المفقودة
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

PT_TO_MM = 25.4 / 72.0
HEADER_FOOTER_BAND = 45  # نقاط


def page_words(pdf: Path):
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as fh:
        tmp = fh.name
    subprocess.run(["pdftotext", "-bbox", str(pdf), tmp], capture_output=True)
    html = Path(tmp).read_text(errors="ignore")
    Path(tmp).unlink(missing_ok=True)
    out = []
    for m in re.finditer(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', html, re.S):
        w, h, body = float(m.group(1)), float(m.group(2)), m.group(3)
        words = []
        for k in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', body, re.S):
            x0, y0, x1, y1 = map(float, k.groups()[:4])
            t = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", k.group(5)).strip()
            if t:
                words.append((x0, y0, x1, y1, t))
        out.append((w, h, words))
    return out


def norm(t: str) -> str:
    return re.sub(r"[^\u0621-\u064A0-9A-Za-z%]", "", t)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--source")
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    pdf = Path(a.pdf)
    pages = page_words(pdf)
    print(f"### {a.label or pdf.name} — {len(pages)} صفحة · {pdf.stat().st_size/1024:.0f} ك.ب")

    print("\n== الفراغ أسفل كل صفحة والفراغات الداخلية ==")
    worst = []
    for i, (w, h, words) in enumerate(pages, 1):
        inner = [x for x in words if HEADER_FOOTER_BAND < x[1] < h - HEADER_FOOTER_BAND]
        if not inner:
            print(f"  ص{i:3d}: صفحة فارغة بالكامل")
            continue
        bottom = max(x[3] for x in inner)
        gap_bottom = (h - HEADER_FOOTER_BAND - bottom) * PT_TO_MM
        # فراغات داخلية: نطاقات لا نص فيها بين كتلتين
        ys = sorted({round(x[1], 1) for x in inner})
        bands = []
        prev = bottom
        for y in sorted({x[3] for x in inner}, reverse=True):
            pass
        rows = sorted(inner, key=lambda x: x[1])
        cur_end = rows[0][3]
        for r in rows[1:]:
            if r[1] - cur_end > 40:
                bands.append(((r[1] - cur_end) * PT_TO_MM, cur_end * PT_TO_MM))
            cur_end = max(cur_end, r[3])
        worst.append((i, gap_bottom, bands))
    for i, g, bands in worst:
        flag = ""
        if g > 60:
            flag = "  ← فراغ أسفل كبير"
        inner_txt = " · ".join(f"{b[0]:.0f}مم بعد {b[1]:.0f}مم" for b in bands) if bands else "—"
        print(f"  ص{i:3d}: فراغ أسفل {g:6.0f} مم | فراغات داخلية: {inner_txt}{flag}")

    # عنوان معلّق: آخر سطر في الصفحة يبدو عنوانًا قصيرًا
    print("\n== عناوين معلّقة في نهاية صفحة (آخر سطر قصير بلا نقطة) ==")
    for i, (w, h, words) in enumerate(pages[:-1], 1):
        inner = [x for x in words if HEADER_FOOTER_BAND < x[1] < h - HEADER_FOOTER_BAND]
        if not inner:
            continue
        last = max(inner, key=lambda x: x[3])
        tail = [x for x in inner if abs(x[3] - last[3]) < 3]
        line = " ".join(t for *_ , t in sorted(tail, key=lambda x: -x[0]))
        if len(line.split()) <= 6 and len(line) <= 45 and not line.endswith((".", ":", "،")):
            print(f"  ص{i}: «{line}»")

    if a.source:
        src = Path(a.source).read_text(encoding="utf-8")
        pdf_text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        sw = len(norm(src).split()) if False else len(norm(src))
        pw = len(norm(pdf_text))
        print(f"\n== اكتمال النص مقابل المصدر ==")
        print(f"  أحرف المصدر: {sw:,} · أحرف PDF: {pw:,} · النسبة: {pw/max(sw,1)*100:.1f}%")
        heads = [h.strip() for h in re.findall(r"^#{2,3}\s+(.+)$", src, re.M)]
        missing = [h for h in heads if norm(h)[:18] and norm(h)[:18] not in norm(pdf_text)]
        print(f"  عناوين المصدر: {len(heads)} · غير موجودة في PDF: {len(missing)}")
        for h in missing[:12]:
            print(f"    ✗ {h[:70]}")
        # بنود القوائم الطويلة
        bullets = [b.strip() for b in re.findall(r"^\s*[-*]\s+(.{12,})$", src, re.M)]
        mb = [b for b in bullets if norm(b)[:22] and norm(b)[:22] not in norm(pdf_text)]
        print(f"  بنود قوائم: {len(bullets)} · غير موجودة: {len(mb)}")
        for b in mb[:8]:
            print(f"    ✗ {b[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())