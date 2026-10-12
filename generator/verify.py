#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص آلي قبل التسليم لصفحة التقرير الصباحي.
يتحقق من: البنية، المعرّفات، العناوين، الجداول، العزل الاتجاهي، العرض على الجوال،
ظهور المحتوى بدون JavaScript، التقاطح الأفقي، ونسخة الطباعة A4.

الاستخدام: python3 verify.py <صفحة.html> [مجلد_المخرجات]
يعيد 0 عند النجاح، و1 عند وجود إخفاق.
"""
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

src = Path(sys.argv[1]).resolve()
outdir = Path(sys.argv[2] if len(sys.argv) > 2 else "/home/ubuntu/brain-marine-news/audit/visual")
outdir.mkdir(parents=True, exist_ok=True)
raw = src.read_text(encoding="utf-8")

fails, warns, notes = [], [], []


def check(cond, msg):
    (notes if cond else fails).append(("PASS: " if cond else "FAIL: ") + msg)


# ---- فحوص ثابتة على المصدر ----
check(raw.count("<h1") == 1, f"عنصر h1 واحد ({raw.count('<h1')})")
ids = re.findall(r'\sid="([^"]+)"', raw)
dups = {i for i in ids if ids.count(i) > 1}
check(not dups, f"المعرّفات فريدة ({len(ids)} معرّفًا) — مكرر: {sorted(dups)}")
check('lang="ar"' in raw and 'dir="rtl"' in raw, "اللغة والاتجاه مضبوطان")
check("<thead" in raw and 'scope="col"' in raw, "الجداول لها رؤوس ونطاق أعمدة")
check(raw.count("<table") == raw.count("<thead"), "كل جدول له رأس")
check('<meta name="description"' in raw, "وصف الصفحة موجود")
check('noindex' in raw, "منع الفهرسة مضبوط")
check("@keyframes rise" in raw and "html.js .reveal{opacity:0" not in raw, "الحركة بالـCSS والمحتوى غير مخفي بجافاسكربت")
check('style="--w:' in raw, "أعمدة المخطط تحمل عرضها في HTML لا في JavaScript")
check('aria-hidden="true"' in raw, "الأيقونات مخفية عن قارئ الشاشة")
check("bidi" in raw, "العزل الاتجاهي للقيم اللاتينية موجود")
check("<a " in raw, "توجد روابط مصادر قابلة للنقر")
check(
    not re.search(r'content="[^"]*"\s+onmouseover', raw) and "<script src=" not in raw,
    "لا سكربتات خارجية ولا حقن في الصفات",
)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])

    # سطح المكتب
    pg = b.new_page(viewport={"width": 1440, "height": 980}, device_scale_factor=1)
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(src.as_uri(), wait_until="load")
    pg.wait_for_timeout(1500)
    check(not errs, f"لا أخطاء في وحدة التحكم ({len(errs)})")
    secs = pg.eval_on_selector_all("section.doc", "els => els.length")
    check(secs >= 13, f"عدد الأقسام المرصودة على الشاشة: {secs}")
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    pg.wait_for_timeout(1500)
    hidden = pg.eval_on_selector_all(
        "section.doc", "els => els.filter(e => getComputedStyle(e).opacity === '0').length"
    )
    check(hidden == 0, f"لا قسم مخفي بعد التمرير ({hidden})")
    for i, y in enumerate([0, 900, 2100, 3400, 5200, 7600]):
        pg.evaluate(f"window.scrollTo(0,{y})")
        pg.wait_for_timeout(800)
        pg.screenshot(path=str(outdir / f"desktop-{i}.png"))
    pg.evaluate("window.scrollTo(0,0)")
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(outdir / "full.png"), full_page=True)

    # جوال
    m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    m.goto(src.as_uri(), wait_until="load")
    m.wait_for_timeout(1200)
    metrics = m.evaluate("({s:document.documentElement.scrollWidth,c:document.documentElement.clientWidth})")
    check(metrics["s"] <= metrics["c"] + 1, f"لا تمرير أفقي على الجوال ({metrics['s']} <= {metrics['c']})")
    m.screenshot(path=str(outdir / "mobile-390.png"), full_page=False)

    # بدون JavaScript
    nj = b.new_context(java_script_enabled=False, viewport={"width": 1440, "height": 980})
    n1 = nj.new_page()
    n1.goto(src.as_uri(), wait_until="load")
    n1.wait_for_timeout(600)
    vis = n1.eval_on_selector_all(
        "section.doc", "els => els.filter(e => getComputedStyle(e).opacity !== '0').length"
    )
    check(vis >= 13, f"المحتوى كامل بدون JavaScript ({vis} قسمًا مرئيًا)")
    nj.close()

    # الطباعة
    pg.emulate_media(media="print")
    pg.wait_for_timeout(600)
    pg.pdf(path=str(outdir / "print-a4.pdf"), format="A4", print_background=False)
    b.close()

pdf = outdir / "print-a4.pdf"
if pdf.exists():
    head = pdf.read_bytes()[:200000]
    pages = len(re.findall(rb"/Type\s*/Page[^s]", head)) or "غير معروف (تقريب)"
    notes.append(f"PASS: أُنشئت نسخة الطباعة A4 ({pdf.stat().st_size} bytes، صفحات مكتشفة: {pages})")

print("\n".join(notes))
if fails:
    print("\n".join(fails))
    print(f"\nالنتيجة: فشل {len(fails)} فحصًا.")
    sys.exit(1)
print("\nالنتيجة: نجحت جميع الفحوص.")
sys.exit(0)

    # فحص الوسوم المهرَّبة: أي وسم يظهر نصًّا للقارئ = عيب مانع
    html_txt = Path(sys.argv[1]).read_text(encoding="utf-8")
    n_esc = html_txt.count("&lt;")
    if n_esc:
        print(f"فشل: {n_esc} وسمًا مهرَّبًا يظهر نصًّا للقارئ")
        sys.exit(1)
    print("فحص الوسوم المهرَّبة: لا شيء")
