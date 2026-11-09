#!/usr/bin/env python3
"""بوابة مطابقة شكل PDF المعتمد (v3 — 18 أكتوبر 2026).

الغرض: منع تسليم أي نسخة PDF بمظهر مختلف عن الشكل الذي اعتمده صاحب القرار.

الاستخدام:
  python3 validators/check_pdf_format.py --pdf <ملف> --date 2026-10-18 [--allow-css-change]

المخرجات: تقرير فحص، ورمز الخروج 0 عند المطابقة و4 عند المخالفة.
"""
from __future__ import annotations
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]

def _tree(_env, _base, *_names):
    """جذر الشجرة: متغيّر البيئة، ثم seawatch الشقيق، ثم المجلد المتداخل."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    # عند وجود مرآة قديمة داخل mda-marine-system/site، لا تسبق جذر الموقع
    # المعلن /home/ubuntu/seawatch؛ وإلا تُقرأ بصمة مولّد مختلفة عن PDF المراد
    # فحصه. يفحص الشقيق الأعلى أولًا، ثم الجذر المحلي، ثم النسخة المتداخلة.
    _parents = (_base.parent.parent, _base.parent)
    for _parent in _parents:
        for _n in _names:
            _c = _parent / _n
            if _c.is_dir():
                return _c
    return _base.parent / _names[0]
SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

B = Path(__file__).resolve().parent.parent
PROFILE = B / "templates" / "approved-pdf" / "print-profile.json"
FROZEN_CSS = B / "templates" / "approved-pdf" / "print-css-frozen.css"
BUILD_REPORT = Path(f"{SITE}/generator/build_report.py")
MAX_GAP_MM = 60          # أقصى فراغ أسفل ورقة مقبول (غير الغلاف والصفحة الأخيرة)
MIN_LEGEND_ITEMS = 3     # شكل المفتاح المعتمد: ثلاث ذرات دلالية، لا كثافة رموز النص


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class _MapLegendParser(HTMLParser):
    """يستخرج عناصر li من كتلة map-key/mp-key دون عدّ رموز المتن."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int | None]] = []
        self.key_stack: list[int] = []
        self.li_stack: list[tuple[int, int, int]] = []
        self.blocks: list[dict] = []

    def handle_starttag(self, tag: str, attrs):
        attrs_map = dict(attrs)
        classes = set((attrs_map.get("class") or "").split())
        block_index = None
        if classes & {"map-key", "mp-key"}:
            block_index = len(self.blocks)
            self.blocks.append({"classes": classes, "items": []})
            self.key_stack.append(block_index)
        depth = len(self.stack) + 1
        self.stack.append((tag, block_index))
        if tag == "li" and self.key_stack:
            block = self.blocks[self.key_stack[-1]]
            block["items"].append([])
            self.li_stack.append((depth, self.key_stack[-1], len(block["items"]) - 1))

    def handle_data(self, data: str):
        if self.li_stack:
            _, block_index, item_index = self.li_stack[-1]
            self.blocks[block_index]["items"][item_index].append(data)

    def handle_endtag(self, tag: str):
        depth = len(self.stack)
        if tag == "li":
            while self.li_stack and self.li_stack[-1][0] >= depth:
                self.li_stack.pop()
        if self.stack:
            open_tag, block_index = self.stack.pop()
            if block_index is not None and block_index in self.key_stack:
                self.key_stack.remove(block_index)

    def handle_startendtag(self, tag: str, attrs):
        # العناصر الفارغة (مثل br) لا تغيّر نطاق الكتلة أو li المفتوح.
        return


def extract_map_legend_items(html: str) -> list[str]:
    """يعيد النص الدلالي لعناصر مفتاح الخريطة من كتلة HTML الفعلية."""
    parser = _MapLegendParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        return []
    # mp-key هو مفتاح خريطة الوقائع؛ map-key بديل قديم مقبول عند غيابه.
    blocks = sorted(parser.blocks, key=lambda b: "mp-key" not in b["classes"])
    for block in blocks:
        items = [re.sub(r"\s+", " ", "".join(parts)).strip()
                 for parts in block["items"]]
        items = [item for item in items if item]
        if items:
            return items
    return []


def legend_failure(items: list[str]) -> str | None:
    """فشل مغلق إذا غاب المفتاح أو نزل عن شكل المرجع المعتمد."""
    if len(items) >= MIN_LEGEND_ITEMS:
        return None
    return f"مفتاح الخريطة غائب أو ناقص (العناصر الدلالية: {len(items)})"


def extract_pdf_legend_items(text: str) -> list[str]:
    """مسار احتياطي: يعدّ سطر/كتلة المفتاح التي تحمل الذرات الثلاث معًا فقط."""
    labels = (
        ("واقعة مؤكدة", ("واقعةمؤكدة",)),
        ("موقع تقريبي", ("موقعتقريبي", "موقعتقرييب")),
        ("بلاغ غير مؤهل", ("بلاغغيرمؤهل", "بالغغيرمؤهل", "بالغغريمؤهل")),
    )
    lines = [re.sub(r"[^\u0600-\u06ffA-Za-z0-9]", "", line)
             for line in (text or "").splitlines()]
    for index in range(len(lines)):
        window = "".join(lines[index:index + 3])
        if all(any(variant in window for variant in variants) for _, variants in labels):
            return [label for label, _ in labels]
    return []


def map_legend_items(pdf_text: str, date: str | None = None) -> tuple[list[str], str]:
    """يقرأ مفتاح HTML المبني، ثم يلجأ إلى كتلة PDF فقط عند غياب مصدر HTML."""
    if date:
        html_path = Path(SITE) / "dist" / "reports" / f"{date}.html"
        if html_path.is_file():
            try:
                return extract_map_legend_items(html_path.read_text(encoding="utf-8")), "HTML"
            except OSError:
                return [], "HTML (تعذّرت القراءة)"
    return extract_pdf_legend_items(pdf_text), "PDF"


def page_count_failure(pages: int, bounds: tuple[int, int]) -> str | None:
    lo, hi = bounds
    if lo <= pages <= hi:
        return None
    return f"عدد الصفحات {pages} خارج النطاق المعتمد {lo}–{hi}"


def layout_failures(fills: list[float], voids: list[tuple[int, float]], gate: dict) -> list[str]:
    """أحكام التعبئة والفجوة في دالة واحدة قابلة للاختبار الموجب والسالب."""
    failures: list[str] = []
    avg_min = gate.get("avg_fill_min")
    if avg_min is not None and fills:
        avg = sum(fills) / len(fills)
        if avg < avg_min:
            failures.append(f"متوسط تعبئة الصفحات {avg:.1f}% دون الحد {avg_min}%")
    low = [(i + 1, round(fill)) for i, fill in enumerate(fills)
           if fill < gate.get("min_page_fill", 70)]
    if low:
        failures.append(f"صفحات قليلة التعبئة: {low}")
    body = [(number, gap) for number, gap in voids if 1 < number < len(voids)]
    big = [(number, gap) for number, gap in body
           if gap >= gate.get("max_internal_void_mm", 60)]
    if big:
        failures.append("فجوات داخلية كبيرة في متن التقرير: "
                        + " · ".join(f"ص{number}={gap} مم" for number, gap in big))
    return failures


def css_fingerprint_failure(frozen: str, current: str) -> str | None:
    frozen_hash = sha(frozen)
    current_hash = sha(current)
    if frozen_hash == current_hash:
        return None
    return f"نمط الطباعة تغيّر عن المعتمد (المعتمد {frozen_hash} · الحالي {current_hash})"


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
    a = ap.parse_args()

    pdf = Path(a.pdf)
    if not pdf.exists():
        print(f"فشل: الملف غير موجود {pdf}")
        return 2
    if pdf.stat().st_size == 0:
        print(f"فشل: الملف فارغ (0 بايت) {pdf} — بند مانع غير مُتحقَّق منه (فشل مغلق)")
        return 2
    prof = {}
    if PROFILE.exists():
        import json
        prof = json.loads(PROFILE.read_text(encoding="utf-8"))

    fails: list[str] = []
    notes: list[str] = []

    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m_pages = re.search(r"Pages:\s+(\d+)", info)
    if not m_pages:
        print("فشل: تعذّر قراءة بنية PDF (لا «Pages» في مخرج pdfinfo) — بند مانع غير مُتحقَّق منه (فشل مغلق)")
        return 2
    pages = int(m_pages.group(1))
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    nrm = lambda t: re.sub(r"[^\u0621-\u064A0-9]", "", t)
    flat = nrm(text)

    # 1) عدد الصفحات في النطاق المعتمد
    lo, hi = prof.get("pages_range", [17, 22])
    page_failure = page_count_failure(pages, (lo, hi))
    if page_failure:
        fails.append(page_failure)

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
    legend_items, legend_source = map_legend_items(text, a.date)
    legend_error = legend_failure(legend_items)
    if legend_error:
        fails.append(legend_error)
    else:
        notes.append(f"مفتاح الخريطة حاضر ({len(legend_items)} عناصر دلالية من {legend_source})")

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
    layout_issues = layout_failures(fills, voids, gate)
    fails.extend(layout_issues)
    avg = sum(fills) / len(fills) if fills else 0
    if not any("متوسط تعبئة الصفحات" in issue for issue in layout_issues):
        notes.append(f"متوسط التعبئة {avg:.1f}%")
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

    if not any("فجوات داخلية كبيرة" in issue for issue in layout_issues):
        notes.append(f"لا فجوة داخلية ≥ {gate.get('max_internal_void_mm')} مم في متن التقرير")
    edge = [(n, round(fills[n - 1]), g) for n, g in voids if n == 1 or n == len(voids)]
    low_edge = [(n, f) for n, f, _ in edge if f < gate.get("edge_page_fill_min", 55)]
    if low_edge:
        if not any("صفحات قليلة التعبئة" in issue for issue in layout_issues):
            fails.append(f"الغلاف/الصفحة الأخيرة تعبئتها منخفضة: {low_edge}")
    else:
        notes.append("الغلاف والصفحة الأخيرة فوق حدّ التعبئة الأدنى")

    # 7) بصمة نمط الطباعة (قفل الشكل)
    if FROZEN_CSS.exists() and not a.allow_css_change:
        # خلل جذري كشفه القياس 2026-11-09: كانت بصمة الملف المقفل تُجزّأ هنا ثم
        # تُجزّأ مرة أخرى داخل css_fingerprint_failure، فيُقارَن «هاش الهاش» بالهاش
        # ولا يمرّ الفحص أبدًا مهما طابق النمط. الإصلاح: يُمرَّر النصّ الخام،
        # والدالة وحدها تجزّئ الطرفين، فيبقى الفحص مغلقًا وصادقًا.
        css_failure = css_fingerprint_failure(FROZEN_CSS.read_text(encoding="utf-8"),
                                              current_print_css())
        if css_failure:
            fails.append(css_failure)

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
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
