#!/usr/bin/env python3
"""قياس ارتفاع كتلة (وعرض عناصرها) في وضع الطباعة مباشرةً.

الاستخدام:
  python3 measure_block.py --html page.html --selector ".print-map"
  python3 measure_block.py --html page.html --selector ".hmap-legend" --break-inside
  python3 measure_block.py --url file:///path/page.html --selector "#map" --viewport 900

المخرجات: الارتفاع والعرض بالمليمترات (A4 عرض 210 مم عند 96dpi ⇒ 1mm = 3.7795px)،
ومقارنة ارتفاع الكتلة بارتفاع مساحة الطباعة المتاحة (297 − الهوامش المقاسة من الصفحة).
مع --break-inside يطبع قيمة break-inside الفعلية للعنصر، وهي أول ما يُفحص عند
انقسام كتلة بين صفحتين.
"""
import argparse
import sys
from pathlib import Path

PX_PER_MM = 96 / 25.4


def main() -> int:
    ap = argparse.ArgumentParser(description='قياس كتلة في وضع الطباعة')
    ap.add_argument('--html', help='مسار ملف HTML محلي')
    ap.add_argument('--url', help='رابط مباشر (file:// أو http)')
    ap.add_argument('--selector', required=True)
    ap.add_argument('--viewport', type=int, default=794,
                    help='عرض نافذة القياس بالبكسل (794 = عرض A4 عند 96dpi، فيصير القياس مماثلًا للورق)')
    ap.add_argument('--break-inside', action='store_true', help='اطبع break-inside للعنصر')
    a = ap.parse_args()

    target = a.url or (Path(a.html).resolve().as_uri() if a.html else None)
    if not target:
        print('✘ حدّد --html أو --url')
        return 2
    if a.html and not Path(a.html).exists():
        print(f'✘ الملف غير موجود: {a.html}')
        return 2

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('✘ playwright غير مثبت')
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': a.viewport, 'height': 1200})
        page.goto(target, wait_until='load')
        page.emulate_media(media='print')
        page.wait_for_timeout(300)
        el = page.query_selector(a.selector)
        if el is None:
            print(f'✘ لم يُوجد العنصر: {a.selector}')
            browser.close()
            return 2
        box = el.bounding_box()
        style = el.evaluate("""e => {
            const s = getComputedStyle(e);
            return {breakInside: s.breakInside, pageBreakInside: s.pageBreakInside,
                    height: s.height, maxHeight: s.maxHeight, width: s.width};
        }""")
        # ارتفاع الصفحة المطبوعة الفعلي (بعد هوامش @page إن وُجدت)
        page_mm = page.evaluate("""() => {
            const d = document.createElement('div');
            d.style.cssText = 'position:absolute;visibility:hidden;height:297mm;width:1mm';
            document.body.appendChild(d);
            const h = d.getBoundingClientRect().height;
            d.remove();
            return h;
        }""")
        browser.close()

    mm = lambda px: round(px / PX_PER_MM, 1)
    print(f'العنصر: {a.selector}')
    print(f'  الارتفاع: {mm(box["height"])} مم · العرض: {mm(box["width"])} مم')
    print(f'  ارتفاع ورقة A4 المرجعي: {mm(page_mm)} مم')
    print(f'  عرض الورقة المرجعي 210 مم — إن تجاوز العرض القياسُ 210 فالمقاس خارج الورق'
          f' (اضبط --viewport أو افحص عرض الحاوية).')
    print(f'  الارتفاع المحسوب: {style["height"]} · أقصى ارتفاع: {style["maxHeight"]}'
          f' · العرض المحسوب: {style["width"]}')
    if a.break_inside:
        print(f'  break-inside: {style["breakInside"]} · page-break-inside: {style["pageBreakInside"]}')
    print('  ↳ إن كان الارتفاع يقارب ارتفاع الورقة أو أكبر: الكتلة لن تستقر مع ما قبلها،'
          ' فإما تُصغَّر أو تُنقل إلى موضع يمتلئ ما قبله.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
