#!/usr/bin/env python3
"""قياس تدفّق الطباعة: أي كتلة تبدأ كل صفحة، وكم فراغًا خلّفت الكتلة قبلها.

الغرض: تشخيص الفراغ الداخلي المانع في PDF قبل أي تعديل CSS — يحدّد الكتلة القافزة
(الذرّية التي لا تنقسم) بدل التخمين، ويسمح باختبار قاعدة CSS مقترحة عبر --extra-css
دون لمس مسار التصدير الرسمي.

الاستخدام:
  python3 measure_print_flow.py <file.html|url> [--extra-css fix.css] [--dump 10]
                               [--page-mm 276] [--selectors "section.doc, .additions-annex"]
                               [--json out.json]

الملاحظة: الفراغ هنا تقديري (محاكاة تدفّق)؛ الفراغ الحاكم هو ما يقيسه
`measure_pdf_pages.py` على ملف PDF نفسه. استخدم الاثنين: هذا للسبب، وذاك للحكم.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

MM_PER_PX = 25.4 / 96.0  # CSS px → مم

COLLECT_JS = r"""
(selectors) => {
  const out = [];
  const host = document.querySelector('.print-doc, #report, main, body');
  document.querySelectorAll(selectors).forEach(sec => {
    const sn = sec.getAttribute('data-sec') || (sec.className || '').split(' ')[0] || sec.tagName.toLowerCase();
    Array.from(sec.children).forEach(ch => {
      if (ch.hasAttribute('data-eid')) return;
      const r = ch.getBoundingClientRect();
      if (r.height < 1) return;
      out.push({
        sec: sn,
        tag: ch.tagName.toLowerCase() + (ch.className ? '.' + String(ch.className).split(' ')[0] : ''),
        top: r.top + window.scrollY,
        h: r.height,
        text: (ch.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60)
      });
    });
  });
  out.sort((a, b) => a.top - b.top || a.h - b.h);
  return out;
}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="قياس تدفّق الطباعة وتحديد الكتلة القافزة")
    ap.add_argument("target", help="مسار ملف HTML أو رابط")
    ap.add_argument("--extra-css", help="ملف CSS يُحقن في وضع الطباعة قبل القياس (اختبار بلا تعديل المسار الرسمي)")
    ap.add_argument("--page-mm", type=float, default=276.0, help="ارتفاع منطقة المحتوى في الصفحة (افتراضيًا 276 مم = A4 بهامش 10.5 مم)")
    ap.add_argument("--selectors", default="section.doc, .additions-annex, section.print-map",
                    help="محدِّدات الحاويات التي تُقاس كتل أبنائها المباشرين")
    ap.add_argument("--dump", type=int, default=0, help="طبع أطول N كتلة بترتيب الارتفاع")
    ap.add_argument("--json", help="كتابة النتائج الخام إلى ملف JSON")
    args = ap.parse_args()

    target = args.target
    if pathlib.Path(target).exists():
        target = "file://" + str(pathlib.Path(target).resolve())

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("✘ يلزم playwright: pip3 install playwright && python3 -m playwright install chromium", file=sys.stderr)
        return 70

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        page = b.new_page(viewport={"width": 900, "height": 1200})
        page.emulate_media(media="print")
        page.goto(target, wait_until="load", timeout=90000)
        page.wait_for_timeout(700)
        if args.extra_css:
            page.add_style_tag(content=pathlib.Path(args.extra_css).read_text(encoding="utf-8"))
            page.wait_for_timeout(700)
        raw = page.evaluate(COLLECT_JS, args.selectors)
        b.close()

    blocks = [{"sec": r["sec"], "tag": r["tag"], "top": r["top"] * MM_PER_PX,
               "h": r["h"] * MM_PER_PX, "text": r["text"]} for r in raw]
    if not blocks:
        print("✘ لا كتل مقيسة — راجع --selectors", file=sys.stderr)
        return 2

    page_mm = args.page_mm
    last_top = blocks[-1]["top"] + blocks[-1]["h"]
    pages = int(last_top // page_mm) + 1
    print(f"   الكتل: {len(blocks)} · الطول الكلي: {last_top:.1f} مم · صفحات تقديرية: {pages}")
    print("   ── حدود الصفحات: الكتلة التي تبدأ كل صفحة والفراغ قبلها ──")
    for k in range(1, pages + 1):
        start, end = k * page_mm, (k + 1) * page_mm
        on_page = [bl for bl in blocks if bl["top"] < end and bl["top"] + bl["h"] > start]
        if not on_page:
            print(f"   ص{k}: (لا محتوى)")
            continue
        first = on_page[0]
        last = on_page[-1]
        void = max(0.0, end - (last["top"] + last["h"])) if last["top"] + last["h"] <= end else 0.0
        flag = "  ← فراغ مانع" if void >= 45 else ""
        print(f"   ص{k}: تبدأ بـ[{first['sec']} › {first['tag']}] h={first['h']:.1f}مم · "
              f"آخر كتلة h={last['h']:.1f}مم · فراغ تقديري {void:.1f}مم{flag}")
    big = [bl for bl in blocks if bl["h"] >= page_mm * 0.6]
    if big:
        print("   ── كتل كبيرة (ذرّية محتملة: لا تنقسم فتقفز لصفحة جديدة) ──")
        for bl in sorted(big, key=lambda x: -x["h"]):
            print(f"   {bl['h']:.1f}مم [{bl['sec']} › {bl['tag']}] · {bl['text']}")
    if args.dump:
        print(f"   ── أطول {args.dump} كتلة ──")
        for bl in sorted(blocks, key=lambda x: -x["h"])[:args.dump]:
            print(f"   {bl['h']:6.1f}مم top={bl['top']:8.1f} [{bl['sec']} › {bl['tag']}] {bl['text']}")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"target": args.target, "page_mm": page_mm, "blocks": blocks}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"   ↳ JSON: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
