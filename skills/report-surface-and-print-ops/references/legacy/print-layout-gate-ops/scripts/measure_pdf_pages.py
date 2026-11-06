#!/usr/bin/env python3
"""قياس تعبئة صفحات PDF والفراغات الداخلية بالمليمترات.

الاستخدام:
  python3 measure_pdf_pages.py --pdf report.pdf [--dpi 90] [--void 45] [--json]

يعتمد على pdftoppm (poppler) و PIL/numpy. يطبع كتل الحبر لكل صفحة ثم:
  - نسبة التعبئة لكل صفحة (آخر كتلة ناقص أول كتلة ÷ ارتفاع الورقة)
  - الفراغات الداخلية ≥ --void مم
  - متوسط التعبئة وصفحات التعبئة المنخفضة (< 25%)
الخروج: 0 إن لم توجد فراغات مانعة ولا صفحات قليلة التعبئة، وإلا 2.
"""
import argparse
import glob
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def measure(pdf: Path, dpi: int, void_mm: float, low_fill: float,
            footer_from: float = 270.0, ink: int = 235, min_row: float = 0.002) -> dict:
    """يقيس كتل المحتوى لكل صفحة.

    footer_from: بداية نطاق الترقيم/التذييل (مم) — يُستثنى من كشف الفراغات حتى لا
    يُحسب الفراغ بين آخر سطر محتوى والترقيم فراغًا داخليًا.
    min_row: أقل نسبة حبر في السطر ليُعدّ سطر محتوى.
    """
    import numpy as np
    from PIL import Image

    tmp = Path(tempfile.mkdtemp(prefix='pdfpages-'))
    try:
        try:
            subprocess.run(['pdftoppm', '-r', str(dpi), '-png', str(pdf), str(tmp / 'p')],
                           check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f'تعذّر تحويل الملف إلى صور — هل هو PDF صالح؟ ({e.returncode})') from e
        pages = []
        for f in sorted(glob.glob(str(tmp / 'p-*.png'))):
            a = np.array(Image.open(f).convert('L'))
            h = a.shape[0]
            mm = 297.0 / h
            rows_ink = (a < ink).sum(axis=1)
            rows = np.where(rows_ink > max(3, int(a.shape[1] * min_row)))[0]
            if rows.size == 0:
                pages.append(dict(page=int(Path(f).stem.split('-')[-1]), top=0.0, bottom=0.0,
                                  fill=0.0, voids=[]))
                continue
            segs, start, prev = [], rows[0], rows[0]
            for r in rows[1:]:
                if (r - prev) * mm > 6:
                    segs.append((start * mm, prev * mm))
                    start = r
                prev = r
            segs.append((start * mm, prev * mm))
            footer = [s for s in segs if s[0] >= footer_from]
            content = [s for s in segs if s[0] < footer_from] or segs
            top = content[0][0]
            bottom = content[-1][1]
            voids = [round(content[i + 1][0] - content[i][1]) for i in range(len(content) - 1)
                     if (content[i + 1][0] - content[i][1]) >= void_mm]
            pages.append(dict(page=int(Path(f).stem.split('-')[-1]),
                              top=round(top), bottom=round(bottom),
                              fill=round((bottom - top) / 297.0 * 100, 1),
                              page_fill=round((segs[-1][1] - segs[0][0]) / 297.0 * 100, 1),
                              footer_from=round(footer[0][0]) if footer else None,
                              segments=[[round(a1), round(b1)] for a1, b1 in content],
                              voids=voids))
        fills = [p['fill'] for p in pages]
        return dict(pdf=str(pdf), pages=len(pages),
                    avg_fill=round(sum(fills) / len(fills), 1) if fills else 0.0,
                    low_pages=[(p['page'], p['fill']) for p in pages if p['fill'] < low_fill],
                    void_pages=[(p['page'], p['voids']) for p in pages if p['voids']],
                    detail=pages)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description='قياس تعبئة صفحات PDF والفراغات')
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--dpi', type=int, default=90)
    ap.add_argument('--void', type=float, default=45.0, help='حدّ الفراغ الداخلي بالمليمتر')
    ap.add_argument('--low-fill', type=float, default=25.0)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    pdf = Path(a.pdf)
    if not pdf.exists():
        print(f'✘ الملف غير موجود: {pdf}')
        return 2
    if not shutil.which('pdftoppm'):
        print('✘ pdftoppm غير مثبت (poppler-utils)')
        return 2

    try:
        r = measure(pdf, a.dpi, a.void, a.low_fill)
    except RuntimeError as e:
        print(f'✘ {e}')
        return 2
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        print(f'قياس التعبئة · {pdf.name} · {r["pages"]} صفحة · متوسط {r["avg_fill"]}%')
        for p in r['detail']:
            print(f'  ص{p["page"]}: {p["top"]}→{p["bottom"]} مم · تعبئة {p["fill"]}%'
                  + (f' · فراغ {p["voids"]} مم' if p['voids'] else ''))
        if r['low_pages']:
            print('  ✘ صفحات قليلة التعبئة:', r['low_pages'])
        else:
            print(f'  ✓ لا صفحة تحت {a.low_fill}%')
        if r['void_pages']:
            print(f'  ✘ فراغات ≥ {a.void} مم:', r['void_pages'])
        else:
            print(f'  ✓ لا فراغ داخلي ≥ {a.void} مم')

    bad = bool(r['void_pages']) or bool(r['low_pages'])
    print('النتيجة:', 'مخالف — راجع الكتل المذكورة' if bad else 'مطابق')
    return 2 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
