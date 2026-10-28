#!/usr/bin/env python3
"""بوابة مطابقة شكل PDF المعتمد (v3 — 18 أكتوبر 2026).

الغرض: منع تسليم أي نسخة PDF بمظهر مختلف عن الشكل الذي اعتمده صاحب القرار.

الاستخدام:
  python3 validators/check_pdf_format.py --pdf <ملف> --date 2026-10-18 [--allow-css-change]

المخرجات: تقرير فحص، ورمز الخروج 0 عند المطابقة و4 عند المخالفة.
"""
from __future__ import annotations
# ── مسارات محمولة: استخدم --brain/--site أو استنتج الجذر من الملف وPDF ──
import os as _os
from pathlib import Path as _Path
SKILL_ROOT = _Path(__file__).resolve().parents[2]
B = None
SITE = None
PROFILE = None
FROZEN_CSS = None
BUILD_REPORT = None

def _infer_brain(_explicit, _pdf):
    if _explicit:
        return _Path(_explicit).expanduser().resolve()
    if _os.environ.get("BRAIN_DIR"):
        return _Path(_os.environ["BRAIN_DIR"]).expanduser().resolve()
    seeds = [_Path(_pdf).expanduser().resolve(), _Path(__file__).resolve()]
    for _seed in seeds:
        for _ancestor in (_seed, *_seed.parents):
            for _candidate in (_ancestor, _ancestor / "brain-marine-news", _ancestor.parent / "brain-marine-news"):
                if (_candidate / "templates" / "approved-pdf" / "print-profile.json").exists():
                    return _candidate
    return _Path(__file__).resolve().parents[4] / "brain-marine-news"

def _infer_site(_explicit, _pdf):
    if _explicit:
        return _Path(_explicit).expanduser().resolve()
    if _os.environ.get("SITE_DIR"):
        return _Path(_os.environ["SITE_DIR"]).expanduser().resolve()
    _pdf = _Path(_pdf).expanduser().resolve()
    for _ancestor in (_pdf, *_pdf.parents):
        if (_ancestor / "dist").is_dir():
            return _ancestor
    return _pdf.parents[3] if len(_pdf.parents) > 3 else _pdf.parent

def _configure(_brain, _site, _pdf):
    global B, SITE, PROFILE, FROZEN_CSS, BUILD_REPORT
    B = _infer_brain(_brain, _pdf)
    SITE = _infer_site(_site, _pdf)
    PROFILE = B / "templates" / "approved-pdf" / "print-profile.json"
    FROZEN_CSS = B / "templates" / "approved-pdf" / "print-css-frozen.css"
    BUILD_REPORT = SITE / "generator" / "build_report.py"

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

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


def page_metrics(pdf: Path) -> tuple[list[float], list[tuple[int, float]]]:
    """تعبئة كل صفحة (نسبة منطقة المحتوى المملوءة) وأطول فجوة داخلية بالمليمتر.

    تُقاس منطقة المحتوى بين الترويسة (9 مم) والتذييل (12 مم)، فلا يُحسب التذييل محتوى.
    """
    from PIL import Image
    fills: list[float] = []
    voids: list[tuple[int, float]] = []
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", "80", "-png", str(pdf), f"{d}/p"],
                       capture_output=True, timeout=900)
        for f in sorted(Path(d).glob("p-*.png")):
            n = int(re.search(r"p-(\d+)", f.name).group(1))
            im = Image.open(f).convert("L")
            w, h = im.size
            px = im.load()
            top, bot = int(9 / 25.4 * 80), h - int(12 / 25.4 * 80)
            rows = [any(px[x, y] < 245 for x in range(0, w, 3)) for y in range(top, bot)]
            last = max([i for i, v in enumerate(rows) if v] or [0])
            fills.append((last + 1) / len(rows) * 100)
            best = cur = 0
            for v in rows:
                if not v:
                    cur += 1
                    best = max(best, cur)
                else:
                    cur = 0
            voids.append((n, round(best / 80 * 25.4, 1)))
    return fills, voids



def orphan_titles(pages_text, headings):
    """ك-103: يكشف عنوانًا (قسم أو بطاقة) بقي وحده آخر ورقة بلا مضمون."""
    bad = []
    for i, t in enumerate(pages_text, 1):
        lines = [l.strip() for l in t.splitlines() if l.strip()]
        lines = [l for l in lines if 'صفحة' not in l and 'مركز الوعي' not in l
                 and 'التقرير اليومي' not in l and 'MDA.BH' not in l]
        if lines and lines[-1] in headings:
            bad.append((i, lines[-1]))
    return bad


def heading_present(heading: str, flat: str) -> bool:
    """هل عنوان القسم موجود في نص PDF المستخرج (مُسوَّى الحروف)؟

    pdftotext يقلب لام-ألف المتصلة داخل الكلمة إلى «ال» في بعض الإصدارات (الملاحية ← المالحية،
    الخلاصة ← الخالصة). فيُجرَّب العنوان كما هو ثم بعد قلب «لا» داخل كل كلمة (لا عبر حدود الكلمات).
    المطابقة على أول 12 أو 18 حرفًا.
    """
    clean = lambda w: re.sub(r"[^\u0621-\u064A0-9]", "", w)
    words = [clean(w) for w in heading.split() if clean(w)]
    flat_tight = "".join(flat.split())
    for variant in ("".join(words), "".join(w.replace("\u0644\u0627", "\u0627\u0644") for w in words)):
        if variant[:12] in flat_tight or variant[:18] in flat_tight:
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--date")
    ap.add_argument("--allow-css-change", action="store_true")
    ap.add_argument("--brain", default="", help="جذر brain الذي يحتوي على profile وCSS المقفل")
    ap.add_argument("--site", default="", help="جذر الموقع الذي يحتوي على generator/build_report.py")
    a = ap.parse_args()

    pdf = Path(a.pdf)
    _configure(a.brain, a.site, pdf)
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

    # 1) عدد الصفحات في النطاق المعتمد
    lo, hi = prof.get("pages_range", [17, 22])
    if not (lo <= pages <= hi):
        fails.append(f"عدد الصفحات {pages} خارج النطاق المعتمد {lo}–{hi}")

    # 2) قسم المصادر والموثوقية محجوبان تمامًا (لا نص ولا إشارة حجب)
    for bad in ("المصادر والمراجع", "موثوقية المصادر", "محجوبمننسخةالطباعة"):
        if nrm(bad) in flat:
            fails.append(f"ظهر ما يجب حجبه: «{bad}»")

    # 3) أقسام المصدر كاملة
    if a.date:
        src = B / "reports" / f"{a.date}-sectioned.md"
        if src.exists():
            heads = [h.strip() for h in re.findall(r"^##\s+(.+)$",
                                                    src.read_text(encoding="utf-8"), re.M)]
            hidden = ("المصادر والمراجع", "موثوقية المصادر")
            try:
                import json as _json
                _pol = _json.loads((B / "appendices" / "report-sections-policy.json").read_text(encoding="utf-8"))
                hidden = tuple(hidden) + tuple(_pol.get("hidden_sections", []))
            except Exception:
                raise  # فشل مغلق: خطأ يخصّ حكم البوابة ⇒ رمز 70 (البند د)
            miss = [h for h in heads
                    if not any(x in h for x in hidden) and not heading_present(h, flat)]
            if miss:
                fails.append(f"أقسام ناقصة في PDF: {miss}")
            else:
                notes.append(f"أقسام المصدر: {len(heads)} — كلها حاضرة")

    # 4) مفتاح الخريطة
    codes = {c for c in re.findall(r"\b\d{2}-\d{2}\b", text)}
    if len(codes) >= MIN_LEGEND_ITEMS:
        notes.append(f"مفتاح الخريطة حاضر ({len(codes)} رمزًا)")
    else:
        fails.append(f"مفتاح الخريطة غائب أو ناقص (رموز: {len(codes)})")

    # 5) تذييل الترقيم
    # استخراج العربية من PDF يعكس ترتيب التذييل، فيُقاس بوجود كلمة «صفحة» ورقم في الصفحة نفسها
    foot = sum(1 for pg in text.split("\f")
               if "صفحة" in pg and re.search(r"\d", pg[-260:]))
    if foot < pages * 0.8:
        fails.append(f"تذييل الترقيم ناقص ({foot} من {pages} صفحة)")
    else:
        notes.append(f"تذييل الترقيم على {foot} صفحة")

    # 6) تعبئة الصفحات والفجوات الداخلية (قياس منطقة المحتوى لا التذييل)
    fills, voids = page_metrics(pdf)
    gate = prof.get("gates", {})
    avg = sum(fills) / len(fills)
    if avg < gate.get("avg_fill_min", 92):
        fails.append(f"متوسط تعبئة الصفحات {avg:.1f}% دون الحد {gate.get('avg_fill_min')}%")
    else:
        notes.append(f"متوسط التعبئة {avg:.1f}%")
    low = [(i + 1, round(f)) for i, f in enumerate(fills) if f < gate.get("min_page_fill", 70)]
    if low:
        fails.append(f"صفحات قليلة التعبئة: {low}")
    # ك-103: لا يُترك عنوان قسم أو بطاقة وحده آخر ورقة بلا مضمون
    try:
        import subprocess as _sp
        txt = _sp.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
        pgs = txt.split("\f")
        heads = set()
        for md in sorted((B / "reports").glob(f"{pdf.stem}-sectioned.md")):
            heads = {l.strip()[3:].strip() for l in md.read_text(encoding="utf-8").splitlines() if l.startswith("## ")}
        heads |= {"عام"}
        orph = orphan_titles(pgs, heads)
        if orph:
            fails.append("عنوان يتيم آخر ورقة: " + "، ".join(f"ص{n}: {t}" for n, t in orph))
        else:
            notes.append("لا عنوان قسم أو بطاقة يتيم آخر ورقة")
    except Exception as e:
        # ك-130: شرط مانع لا يُتحقَّق منه لا يُعدّ ناجحًا — فشل مغلق لا ملاحظة صامتة.
        fails.append(f"تعذّر فحص العنوان اليتيم (بند مانع غير مُتحقَّق منه): {type(e).__name__}: {e}")

    body = [(n, g) for n, g in voids if 1 < n < len(voids)]  # دون الغلاف والصفحة الأخيرة
    big = [(n, g) for n, g in body if g >= gate.get("max_internal_void_mm", 45)]
    if big:
        fails.append("فجوات داخلية كبيرة في متن التقرير: " + " · ".join(f"ص{n}={g} مم" for n, g in big))
    else:
        notes.append(f"لا فجوة داخلية ≥ {gate.get('max_internal_void_mm')} مم في متن التقرير")
    edge = [(n, round(fills[n - 1]), g) for n, g in voids if n == 1 or n == len(voids)]
    low_edge = [(n, f) for n, f, _ in edge if f < gate.get("edge_page_fill_min", 55)]
    if low_edge:
        fails.append(f"الغلاف/الصفحة الأخيرة تعبئتها منخفضة: {low_edge}")
    else:
        notes.append("الغلاف والصفحة الأخيرة فوق حدّ التعبئة الأدنى")

    # 7) بصمة نمط الطباعة (قفل الشكل)
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
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
