#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
measure_gates.py — يقيس معايير القبول الخمسة عشر على حزمة design-v1 (بلا شبكة، بلا مكتبات خارج: playwright · Pillow · poppler-utils).

الاستخدام:
  python3 tools/measure_gates.py [--pdf preview/design-v1.pdf] [--chromium /opt/pw-browsers/chromium] [--json out.json]
يُخرج جدولًا (✔/✘) ورمز خروج 0 عند نجاح كل البوابات و1 عند أي مخالفة (فشل مغلق).

ما يُقاس وكيف (مطابق لمعايير القبول):
  1  يعمل بلا شبكة            : أي طلب غير file:/data: أثناء التحميل = مخالفة؛ وبحث عن http(s):// في الملفات
  2  RTL بلا left/right       : بحث في CSS بعد حذف التعليقات
  3  لا قيم خارج tokens.css   : ألوان وأطوال (px/pt/mm/rem) في components.css وprint.css (يُستثنى @page وشروط @media)
  4  عدد الصفحات 7–12         : pdfinfo
  5  لا كتلة مقسومة          : كتلة الخريطة (عنوانها وتعليقها على الصفحة نفسها) + فحص DOM لما يحمل break-inside
  6  لا عنوان يتيم            : آخر سطر في الصفحة ليس عنوانًا
  7  تعبئة الصفحة            : متوسط ≥ 90% وأدنى صفحة ≥ 55% (من صورة الصفحة داخل المنطقة المطبوعة)
  8  لا فراغ داخلي > 45 مم    : أكبر مسافة بيضاء بين محتويين في المنطقة المطبوعة
  9  الخريطة ≥ 70% × 32%     : أبعاد .map-block في طباعة A4 (عرض ≥ 147 مم، ارتفاع ≥ 95.04 مم)
  10 صفر مخالفة تصفير         : .body-text/.list-justified/.table-cell بـ text-align:justify إلا المستثنى (.nj · .cell-short · .num)
  11 متن ≥ 11.5pt وتفاصيل ≥ 7pt: أحجام الخطوط المحسوبة في وسائط print (ويشمل نص الخريطة بحجمه الفعلي)
  12 تباين ≥ 4.5:1             : أزواج الرموز في الليلي والنهاري والطباعة
  13 رأس الجدول يتكرر         : fixtures/long-table.html
  14 نقص البيانات             : fixtures/states.html بلا أخطاء وبلا تجاوز أفقي
  15 لا تنقّل في الطباعة      : نصوص التنقّل والأزرار والمصادر غائبة من PDF
"""
import argparse, json, os, re, subprocess, sys, tempfile
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A4_W_MM, A4_H_MM = 210.0, 297.0
MARGIN_TB_MM, MARGIN_LR_MM = 14.0, 12.0
PX_PER_MM = 96 / 25.4


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def read_css(name):
    return strip_comments((ROOT / "styles" / name).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ ثابتة
def check_static():
    res = {}
    css_all = {n: read_css(n) for n in ("tokens.css", "components.css", "print.css", "fonts.css")}
    # 2) RTL
    bad = []
    for n, c in css_all.items():
        for m in re.finditer(r"(?<![-\w])(margin-left|margin-right|padding-left|padding-right|border-left|border-right|left|right)\s*:|text-align\s*:\s*(left|right)|float\s*:\s*(left|right)", c):
            bad.append(f"{n}: {m.group(0)}")
    res[2] = (not bad, f"{len(bad)} مخالفة " + "; ".join(bad[:4]))
    # 3) لا قيم خارج الرموز
    viol = []
    for n in ("components.css", "print.css"):
        c = css_all[n]
        c = re.sub(r"@page\s*\{(?:[^{}]|\{[^{}]*\})*\}", "", c)          # استثناء @page
        c = re.sub(r"@media[^{]*\{", "{", c)                              # استثناء شرط @media
        for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", c):
            viol.append(f"{n}: {m.group(0)}")
        for m in re.finditer(r"(?<![\w.#-])-?\d*\.?\d+(px|pt|mm|rem|cm|in)\b", c):
            viol.append(f"{n}: {m.group(0)}")
    res[3] = (not viol, f"{len(viol)} قيمة حرفية خارج tokens.css " + "; ".join(viol[:5]))
    # 1) مراجع شبكة ثابتة
    net = []
    for f in [ROOT / "index.html"] + list((ROOT / "styles").glob("*.css")) + list((ROOT / "fixtures").glob("*.html")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r"https?://[^\s\"')]+", t):
            if "w3.org" not in m.group(0):
                net.append(f"{f.name}: {m.group(0)}")
    res["1s"] = (not net, f"{len(net)} رابط شبكة ثابت")
    # حدود الحجم
    html_kb = (ROOT / "index.html").stat().st_size / 1024
    css_kb = sum((ROOT / "styles" / n).stat().st_size for n in ("tokens.css", "components.css", "print.css")) / 1024
    res["size"] = (html_kb <= 1536 and css_kb <= 120, f"HTML {html_kb:.0f} ك.ب (≤1536) · CSS {css_kb:.0f} ك.ب (≤120)")
    # دلالي
    h = (ROOT / "index.html").read_text(encoding="utf-8")
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script)\b.*?</\1>", "", h, flags=re.S))
    sem = []
    if re.search(r"[٠-٩۰-۹]", text): sem.append("أرقام هندية")
    if "النافذة" in text: sem.append("كلمة «النافذة»")
    res["sem"] = (not sem, "، ".join(sem) or "لا أرقام هندية ولا «النافذة»")
    return res


# ------------------------------------------------------------------ التباين
def lum(h):
    h = h.lstrip("#")
    if len(h) == 3: h = "".join(c * 2 for c in h)
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def parse_tokens():
    t = read_css("tokens.css")
    root = re.search(r":root\s*\{(.*?)\n\}", t, re.S).group(1)
    light = re.search(r':root\[data-theme="light"\]\s*\{(.*?)\n\}', t, re.S).group(1)
    g = lambda blk: dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;", blk))
    dark = g(root); lt = {**dark, **g(light)}
    pr = {k[2:]: v for k, v in [("p-" + a, b) for a, b in []]}
    p = {k: v for k, v in g(root).items() if k.startswith("p-")}
    prn = {"bg": p["p-bg"], "panel": p["p-bg"], "panel-2": p["p-bg"], "panel-3": p["p-panel-3"], "ink": p["p-ink"], "ink-2": p["p-ink-2"],
           "muted": p["p-muted"], "accent": p["p-accent"], "info": p["p-info"], "danger": p["p-danger"], "warn": p["p-warn"], "ok": p["p-ok"],
           "danger-bg": p["p-danger-bg"], "warn-bg": p["p-warn-bg"], "info-bg": p["p-info-bg"], "ok-bg": p["p-ok-bg"], "accent-ink": p["p-bg"],
           "map-sea": p["p-map-sea"], "map-label": p["p-map-label"], "map-country": p["p-map-country"], "map-sea-label": p["p-map-sea-label"],
           "map-strait": p["p-map-strait"], "map-grid-lbl": p["p-map-grid-lbl"], "map-marker-ink": p["p-map-marker-ink"]}
    return {"ليلي": dark, "نهاري": lt, "طباعة": prn}


PAIRS = [("ink", "bg"), ("ink", "panel"), ("ink-2", "panel"), ("ink-2", "panel-3"), ("muted", "bg"), ("muted", "panel"), ("muted", "panel-2"), ("muted", "panel-3"),
         ("accent", "panel"), ("accent", "panel-3"), ("danger", "panel"), ("danger", "danger-bg"), ("warn", "panel"), ("warn", "warn-bg"), ("ok", "panel"),
         ("ok", "ok-bg"), ("info", "panel"), ("info", "info-bg"), ("accent-ink", "accent"), ("map-label", "map-sea"), ("map-country", "map-sea"),
         ("map-sea-label", "map-sea"), ("map-strait", "map-sea"), ("map-grid-lbl", "map-sea")]


def check_contrast():
    out, worst = [], 99
    for theme, tk in parse_tokens().items():
        for fg, bg in PAIRS:
            if fg in tk and bg in tk:
                r = ratio(tk[fg], tk[bg]); worst = min(worst, r)
                if r < 4.5: out.append(f"{theme}: {fg} على {bg} = {r:.2f}")
    return (not out, f"أدنى تباين {worst:.2f}:1" + (" · " + "؛ ".join(out[:5]) if out else ""))


# ------------------------------------------------------------------ PDF
def pdf_pages(pdf):
    m = re.search(r"Pages:\s+(\d+)", sh("pdfinfo", pdf))
    return int(m.group(1)) if m else 0


def page_rows(pdf, dpi=60):
    from PIL import Image
    d = tempfile.mkdtemp()
    sh("pdftoppm", "-r", str(dpi), "-gray", "-png", pdf, f"{d}/p")
    files = sorted(Path(d).glob("p-*.png"))
    pages = []
    mm = dpi / 25.4
    for f in files:
        im = Image.open(f).convert("L"); w, h = im.size
        top, bot = int(MARGIN_TB_MM * mm), int((A4_H_MM - MARGIN_TB_MM) * mm)
        lft, rgt = int(MARGIN_LR_MM * mm), int((A4_W_MM - MARGIN_LR_MM) * mm)
        px = im.load()
        rows = []
        for y in range(top, bot):
            ink = any(px[x, y] < 235 for x in range(lft, rgt, 1))
            rows.append(ink)
        pages.append((rows, mm))
    return pages


def check_fill(pdf):
    pages = page_rows(pdf)
    fills, voids, bottoms = [], [], []
    for i, (rows, mm) in enumerate(pages):
        n = len(rows)
        last = max((y for y, v in enumerate(rows) if v), default=-1)
        first = min((y for y, v in enumerate(rows) if v), default=0)
        fills.append((last + 1) / n * 100)
        bottoms.append((n - last - 1) / mm)
        gap = best = 0
        for y in range(first, last + 1):
            if rows[y]: gap = 0
            else:
                gap += 1; best = max(best, gap)
        voids.append(best / mm)
    avg, mn = sum(fills) / len(fills), min(fills)
    r7 = (avg >= 90 and mn >= 55, f"متوسط {avg:.1f}% · أدنى {mn:.1f}% · لكل صفحة: " + " ".join(f"{f:.0f}" for f in fills))
    mx = max(voids)
    r8 = (mx <= 45, f"أكبر فراغ داخلي {mx:.1f} مم (≤45) · أكبر فراغ سفلي {max(bottoms[:-1] or [0]):.1f} مم")
    return r7, r8


def norm(s):
    """يزيل المسافات وعلامات الاتجاه ليصحّ التطابق رغم تفاوت التبعيد في PDF."""
    import html as _h
    return re.sub(r"[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", _h.unescape(s))


def bbox_lines(pdf):
    """سطور كل صفحة: (صفحة، yMin، yMax، نص) بالنقاط."""
    h = sh("pdftotext", "-bbox-layout", pdf, "-")
    pages = re.split(r"<page ", h)[1:]
    out = []
    for pi, pg in enumerate(pages, 1):
        for m in re.finditer(r'<line xMin="[\d.]+" yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)">(.*?)</line>', pg, re.S):
            words = re.findall(r">([^<]+)</word>", m.group(3))
            # pdftotext -bbox يعيد الكلمات بترتيب بصري وحروفها معكوسة؛ عكس السطر كله يُرجعه منطقيًا للعربية
            out.append((pi, float(m.group(1)), float(m.group(2)), norm(" ".join(words)[::-1])))
    return out


def check_orphans(pdf, headings):
    """العنوان اليتيم: آخر سطر نصي في الصفحة (قبل التذييل) هو عنوان قسم أو عنوان فرعي. يُقرأ النص المنطقي من pdftotext صفحةً صفحة."""
    hs = {norm(h) for h in headings}
    bad = []
    for pg in range(1, pdf_pages(pdf) + 1):
        raw = sh("pdftotext", "-f", str(pg), "-l", str(pg), pdf, "-")
        lines = [norm(l) for l in raw.splitlines() if l.strip()]
        lines = [l for l in lines if not (l.startswith("صفحة") or "تصنيفالإصدار" in l or re.fullmatch(r"\d+", l))]
        if not lines:
            continue
        last = re.sub(r"^\d{1,2}", "", re.sub(r"\d{1,2}$", "", lines[-1]))
        # pdftotext يبدّل أحيانًا ترتيب حرفين متجاورين (بي ← يب)؛ فالمطابقة تقريبية (≥ 0.9)
        if any(SequenceMatcher(None, last, h).ratio() >= 0.9 for h in hs):
            bad.append(f"ص{pg}: «{last}»")
    return (not bad, "لا عنوان في آخر الصفحة" if not bad else "؛ ".join(bad))


def check_nav_absent(pdf):
    t = sh("pdftotext", pdf, "-")
    forbidden = ["الانتقال إلى المحتوى", "طباعة / PDF", "التقرير اليومي الأرشيف", "موثوقية A", "الموقع فقط"]
    found = [f for f in forbidden if f in t]
    sec17 = "حالة التشغيل" in t
    return (not found and not sec17, "غائبة: التنقّل والأزرار وقسم المصادر" if not (found or sec17) else f"موجود: {found} {sec17}")


# ------------------------------------------------------------------ DOM (طباعة)
def dom_checks(chromium):
    from playwright.sync_api import sync_playwright
    res = {}
    js = r"""
    () => {
      const mm = 96/25.4, out = {};
      const vis = e => { const r=e.getBoundingClientRect(); return r.width>0 && r.height>0 };
      // الخريطة
      const mb = document.querySelector('.map-block');
      const r = mb.getBoundingClientRect();
      out.map = {w: r.width/mm, h: r.height/mm};
      // التصفير
      const sel = '.body-text, .list-justified, .list-justified > li, td.table-cell, th.table-cell';
      const notJ = [];
      document.querySelectorAll(sel).forEach(e => {
        if (!vis(e)) return;
        const exempt = e.matches('.nj, .cell-short, .num') || e.closest('.nj');
        if (exempt) return;
        const ta = getComputedStyle(e).textAlign;
        if (ta !== 'justify') notJ.push(e.className + ':' + (e.textContent||'').trim().slice(0,24));
      });
      out.notJustified = notJ;
      // أصناف غير مسمّاة
      const un = [];
      document.querySelectorAll('main p').forEach(e => { if (vis(e) && !e.matches('.body-text, .nj, .more-note, .sec__lede, .map-caption, .prob__basis, .src__basis')) un.push('p:'+e.className); });
      document.querySelectorAll('main td, main th').forEach(e => { if (vis(e) && !e.classList.contains('table-cell')) un.push('td:'+e.className); });
      out.unclassified = un;
      // الأحجام
      const small = [], body = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) {
        const t = n.textContent.trim(); if (!t) continue;
        const e = n.parentElement; if (!e || !vis(e) || ['SCRIPT','STYLE'].includes(e.tagName)) continue;
        const cs = getComputedStyle(e); let px = parseFloat(cs.fontSize);
        const svg = e.closest('svg');
        if (svg) { const vb = svg.viewBox.baseVal; if (vb && vb.width) px = px * (svg.getBoundingClientRect().width / vb.width); }
        const pt = px * 0.75;
        if (e.closest('.body-text, .list-justified') && !e.closest('.tag, .code, .lg-meta, .sec__no, .more-note')) { if (pt < 11.5 - 0.05) body.push(pt.toFixed(1)+'pt:'+t.slice(0,16)); }
        else if (pt < 7 - 0.05) small.push(pt.toFixed(1)+'pt:'+(e.className.baseVal ?? e.className)+':'+t.slice(0,16));
      }
      out.smallBody = body; out.smallOther = small;
      // الكتل التي يجب ألا تنقسم
      out.noBreak = [...document.querySelectorAll('.kpi,.chg,.event,.stat,.decision__row,.map-block,.directives li,.prob__row,.tbl tr')].filter(e => getComputedStyle(e).breakInside !== 'avoid').map(e => e.className || e.tagName).slice(0,5);
      out.thead = getComputedStyle(document.querySelector('.tbl thead')).display;
      out.navDisplay = ['.site-nav','.skip','.btn','.src-grid'].map(s => { const e=document.querySelector(s); return e ? getComputedStyle(e).display : 'none' });
      out.headings = [...document.querySelectorAll('h2, h3')].filter(vis).map(h => h.textContent.trim());
      return out;
    }
    """
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chromium, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
        w = int((A4_W_MM - 2 * MARGIN_LR_MM) * PX_PER_MM)
        pg = b.new_page(viewport={"width": w, "height": 1000})
        bad = []
        pg.on("request", lambda r: bad.append(r.url) if not r.url.startswith(("file:", "data:")) else None)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("file://" + str(ROOT / "index.html")); pg.wait_for_timeout(600)
        pg.emulate_media(media="print"); pg.wait_for_timeout(300)
        d = pg.evaluate(js)
        res["net"] = bad; res["errs"] = errs; res["dom"] = d
        # الشاشة: تجاوز أفقي وأهداف اللمس
        scr = {}
        for width in (360, 768, 1440):
            for theme in ("dark", "light"):
                pg2 = b.new_page(viewport={"width": width, "height": 800})
                pg2.goto("file://" + str(ROOT / "index.html")); pg2.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')"); pg2.wait_for_timeout(250)
                ov = pg2.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                tg = pg2.evaluate("[...document.querySelectorAll('.btn,.nav-links a,.skip')].filter(e=>e.getBoundingClientRect().width>0).filter(e=>e.getBoundingClientRect().height<44-0.5).length")
                scr[f"{width}/{theme}"] = (ov, tg); pg2.close()
        res["screen"] = scr
        # الفيكسترات
        fx = {}
        for name in ("states.html", "long-table.html"):
            f = ROOT / "fixtures" / name
            if f.exists():
                pg3 = b.new_page(viewport={"width": 1000, "height": 800}); e3 = []
                pg3.on("pageerror", lambda e: e3.append(str(e)))
                pg3.on("request", lambda r: e3.append("net:" + r.url) if not r.url.startswith(("file:", "data:")) else None)
                pg3.goto("file://" + str(f)); pg3.wait_for_timeout(400)
                ov = pg3.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                fx[name] = (e3, ov); pg3.close()
        res["fixtures"] = fx
        b.close()
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=str(ROOT / "preview" / "design-v1.pdf"))
    ap.add_argument("--long-pdf", default=str(ROOT / "preview" / "long-table.pdf"))
    ap.add_argument("--chromium", default=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"))
    ap.add_argument("--json")
    a = ap.parse_args()
    st = check_static()
    dom = dom_checks(a.chromium)
    d = dom["dom"]
    rows = []
    add = lambda n, name, ok, det: rows.append((n, name, bool(ok), det))
    ok1 = not dom["net"] and st["1s"][0]
    add(1, "يعمل بلا شبكة", ok1, f"طلبات خارجية: {len(dom['net'])} · روابط ثابتة: {st['1s'][1]}")
    add(2, "RTL بلا left/right", *st[2])
    add(3, "كل القيم في tokens.css", *st[3])
    pages = pdf_pages(a.pdf)
    add(4, "PDF من 7 إلى 12 صفحة", 7 <= pages <= 12, f"{pages} صفحة")
    BL = bbox_lines(a.pdf)
    cap = [l for l in BL if "المصدر:" in l[3] and "تقديرية" in l[3]]
    ttl = [l for l in BL if "خريطةالوقائع" in l[3] and len(l[3]) < 24]
    same = bool(cap and ttl and cap[0][0] == ttl[-1][0])
    add(5, "لا كتلة مقسومة بين صفحتين", same and not d["noBreak"] and d["thead"] == "table-header-group",
        f"الخريطة (العنوان/التعليق) ص{ttl[-1][0] if ttl else '؟'}/ص{cap[0][0] if cap else '؟'} · كتل بلا break-inside: {d['noBreak'] or 'لا شيء'}")
    add(6, "لا عنوان يتيم", *check_orphans(a.pdf, d["headings"]))
    r7, r8 = check_fill(a.pdf)
    add(7, "تعبئة الصفحة ≥ 90% متوسطًا", *r7)
    add(8, "لا فراغ داخلي > 45 مم", *r8)
    m = d["map"]
    add(9, "الخريطة ≥ 70% عرضًا و≥ 32% ارتفاعًا", m["w"] >= 0.7 * A4_W_MM and m["h"] >= 0.32 * A4_H_MM,
        f"{m['w']:.0f} مم = {m['w']/A4_W_MM*100:.0f}% (≥147) · {m['h']:.0f} مم = {m['h']/A4_H_MM*100:.0f}% (≥95)")
    add(10, "صفر مخالفة تصفير في المتن", not d["notJustified"] and not d["unclassified"],
        f"غير مصفّر: {len(d['notJustified'])} {d['notJustified'][:3]} · أصناف غير مسمّاة: {len(d['unclassified'])} {d['unclassified'][:3]}")
    add(11, "متن ≥ 11.5pt وتفاصيل ≥ 7pt", not d["smallBody"] and not d["smallOther"], f"متن أصغر: {d['smallBody'][:3] or 0} · تفاصيل أصغر: {d['smallOther'][:3] or 0}")
    add(12, "تباين ≥ 4.5:1", *check_contrast())
    longpdf = a.long_pdf
    if Path(longpdf).exists():
        t = sh("pdftotext", "-layout", longpdf, "-")
        reps = t.count("الوصف")  # رأس عمود
        pn = pdf_pages(longpdf)
        add(13, "رأس الجدول يتكرر عند الانقسام", pn >= 2 and reps >= pn, f"{pn} صفحات · تكرر الرأس {reps} مرة")
    else:
        add(13, "رأس الجدول يتكرر عند الانقسام", False, "long-table.pdf غير موجود")
    fx = dom["fixtures"]
    fxok = fx and all(not e and ov <= 0 for e, ov in fx.values()) and all(ov <= 0 and tg == 0 for ov, tg in dom["screen"].values())
    add(14, "كل مكوّن يعالج نقص البيانات (+ الشاشة 360/768/1440 بلا تجاوز وأهداف ≥ 44)", fxok, f"fixtures: {fx} · شاشة: {dom['screen']}")
    add(15, "لا عنصر تنقّل في الطباعة", *check_nav_absent(a.pdf), ) if False else add(15, "لا عنصر تنقّل في الطباعة", check_nav_absent(a.pdf)[0] and all(x == "none" for x in d["navDisplay"]), check_nav_absent(a.pdf)[1] + f" · display: {d['navDisplay']}")
    add("+", "حجم الملفات", *st["size"])
    add("+", "قيود دلالية (أرقام لاتينية · «الفترة»)", *st["sem"])
    fonts = sh("pdffonts", a.pdf)
    t3 = len([l for l in fonts.splitlines() if "Type 3" in l])
    add("+", "خطوط PDF مضمّنة بلا Type 3 (ك-116)", t3 == 0, f"Type 3: {t3}")
    print(f"{'#':>3}  {'':2} المعيار")
    fail = 0
    for n, name, ok, det in rows:
        print(f"{str(n):>3}  {'✔' if ok else '✘'}  {name}\n          {det}")
        fail += not ok
    print(f"\nالنتيجة: {'نجحت كل البوابات' if not fail else f'{fail} مخالفة'}")
    if a.json:
        Path(a.json).write_text(json.dumps([{"n": n, "name": nm, "ok": ok, "detail": det} for n, nm, ok, det in rows], ensure_ascii=False, indent=1), encoding="utf-8")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
