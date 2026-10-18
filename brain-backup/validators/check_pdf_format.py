#!/usr/bin/env python3
"""بوابة مطابقة شكل PDF المعتمد (v3 — 18 أكتوبر 2026).

الغرض: منع تسليم أي نسخة PDF بمظهر مختلف عن الشكل الذي اعتمده صاحب القرار.

الاستخدام:
  python3 validators/check_pdf_format.py --pdf <ملف> --date 2026-10-18 [--allow-css-change]

المخرجات: تقرير فحص، ورمز الخروج 0 عند المطابقة و4 عند المخالفة.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
PROFILE = B / "templates" / "approved-pdf" / "print-profile.json"
FROZEN_CSS = B / "templates" / "approved-pdf" / "print-css-frozen.css"
BUILD_REPORT = Path("/home/ubuntu/seawatch/generator/build_report.py")
MAX_GAP_MM = 60          # أقصى فراغ أسفل ورقة مقبول (غير الغلاف والصفحة الأخيرة)
MIN_LEGEND_ITEMS = 8     # مفتاح الخريطة لا يقل عن ثمانية عناصر


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def current_print_css() -> str:
    s = BUILD_REPORT.read_text(encoding="utf-8")
    i = s.find("@media print")
    if i < 0:
        return ""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i:j + 1]
        j += 1
    return s[i:]


def page_gaps_mm(pdf: Path) -> list[float]:
    """فراغ أسفل كل صفحة بالمليمتر (قياس حبر فعلي)."""
    from PIL import Image
    out: list[float] = []
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", "80", "-png", str(pdf), f"{d}/p"],
                       capture_output=True, timeout=600)
        for f in sorted(Path(d).glob("p-*.png")):
            im = Image.open(f).convert("L")
            w, h = im.size
            px = im.load()
            lowest = 0
            for y in range(h - 1, -1, -1):
                dark = sum(1 for x in range(0, w, 4) if px[x, y] < 225)
                if dark > 2:
                    lowest = y
                    break
            out.append(round((h - lowest) / (80 / 25.4), 1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--date")
    ap.add_argument("--allow-css-change", action="store_true")
    a = ap.parse_args()

    pdf = Path(a.pdf)
    if not pdf.exists():
        print(f"فشل: الملف غير موجود {pdf}")
        return 2
    prof = {}
    if PROFILE.exists():
        import json
        prof = json.loads(PROFILE.read_text(encoding="utf-8"))

    fails: list[str] = []
    notes: list[str] = []

    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    nrm = lambda t: re.sub(r"[^\u0621-\u064A0-9]", "", t)
    flat = nrm(text)

    # ١) عدد الصفحات في النطاق المعتمد
    lo, hi = prof.get("pages_range", [17, 22])
    if not (lo <= pages <= hi):
        fails.append(f"عدد الصفحات {pages} خارج النطاق المعتمد {lo}–{hi}")

    # ٢) قسم المصادر والموثوقية محجوبان تمامًا (لا نص ولا إشارة حجب)
    for bad in ("المصادر والمراجع", "موثوقية المصادر", "محجوبمننسخةالطباعة"):
        if nrm(bad) in flat:
            fails.append(f"ظهر ما يجب حجبه: «{bad}»")

    # ٣) أقسام المصدر كاملة
    if a.date:
        src = B / "reports" / f"{a.date}-sectioned.md"
        if src.exists():
            heads = [h.strip() for h in re.findall(r"^##\s+(.+)$",
                                                    src.read_text(encoding="utf-8"), re.M)]
            hidden = ("المصادر والمراجع", "موثوقية المصادر")
            miss = [h for h in heads
                    if not any(x in h for x in hidden) and nrm(h)[:12] not in flat]
            if miss:
                fails.append(f"أقسام ناقصة في PDF: {miss}")
            else:
                notes.append(f"أقسام المصدر: {len(heads)} — كلها حاضرة")

    # ٤) مفتاح الخريطة
    codes = {c for c in re.findall(r"\b\d{2}-\d{2}\b", text)}
    if len(codes) >= MIN_LEGEND_ITEMS:
        notes.append(f"مفتاح الخريطة حاضر ({len(codes)} رمزًا)")
    else:
        fails.append(f"مفتاح الخريطة غائب أو ناقص (رموز: {len(codes)})")

    # ٥) تذييل الترقيم
    # استخراج العربية من PDF يعكس ترتيب التذييل، فيُقاس بوجود كلمة «صفحة» ورقم في الصفحة نفسها
    foot = sum(1 for pg in text.split("\f")
               if "صفحة" in pg and re.search(r"\d", pg[-260:]))
    if foot < pages * 0.8:
        fails.append(f"تذييل الترقيم ناقص ({foot} من {pages} صفحة)")
    else:
        notes.append(f"تذييل الترقيم على {foot} صفحة")

    # ٦) الفراغات أسفل الصفحات
    gaps = page_gaps_mm(pdf)
    bad_gaps = [(i + 1, g) for i, g in enumerate(gaps)
                if g > MAX_GAP_MM and i + 1 not in (1, 2, pages)]
    if bad_gaps:
        fails.append("فراغ أسفل ورقة يتجاوز الحد: "
                     + " · ".join(f"ص{p} = {g} مم" for p, g in bad_gaps))
    else:
        notes.append(f"أقصى فراغ داخلي: {max([g for i, g in enumerate(gaps) if i + 1 not in (1, 2, pages)] + [0])} مم")

    # ٧) بصمة نمط الطباعة (قفل الشكل)
    if FROZEN_CSS.exists() and not a.allow_css_change:
        frozen = sha(FROZEN_CSS.read_text(encoding="utf-8"))
        now = sha(current_print_css())
        if frozen != now:
            fails.append(f"نمط الطباعة تغيّر عن المعتمد (المعتمد {frozen} · الحالي {now})")

    print(f"فحص شكل PDF: {pdf.name}")
    for n in notes:
        print(f"  ✓ {n}")
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        print(f"النتيجة: مخالف للشكل المعتمد ({len(fails)} مخالفة)")
        return 4
    print("النتيجة: مطابق للشكل المعتمد (v3) ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
