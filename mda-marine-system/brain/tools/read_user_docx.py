#!/usr/bin/env python3
"""قراءة ملف وورد للمستخدم: النص + التظليل (الأصفر) + التعديلات المتتبّعة — بلا أي كتابة عليه."""
import sys
from docx import Document
from docx.oxml.ns import qn

HL = {
    'yellow': 'أصفر', 'green': 'أخضر', 'cyan': 'سماوي', 'magenta': 'بنفسجي',
    'blue': 'أزرق', 'red': 'أحمر', 'darkYellow': 'أصفر غامق', 'brightGreen': 'أخضر فاتح',
    'turquoise': 'تركوازي', 'pink': 'زهري', 'gray25': 'رمادي', 'gray50': 'رمادي غامق',
    'lightGray': 'رمادي فاتح', 'darkBlue': 'أزرق غامق', 'darkRed': 'أحمر غامق',
    'darkGreen': 'أخضر غامق', 'violet': 'بنفسجي غامق', 'darkGray': 'رمادي',
}


def run_info(r):
    parts = []
    hc = r.font.highlight_color
    if hc is not None:
        parts.append(HL.get(str(hc), str(hc)))
    # تظليل عبر shd
    shd = r._element.find(qn('w:rPr'))
    if shd is not None:
        s = shd.find(qn('w:shd'))
        if s is not None:
            fill = (s.get(qn('w:fill')) or '').upper()
            if fill and fill not in ('AUTO', 'FFFFFF'):
                parts.append(f"shd:{fill}")
    if r.bold:
        parts.append('عريض')
    if r.underline:
        parts.append('تحته خط')
    col = r.font.color
    if col is not None and col.rgb is not None and str(col.rgb) not in ('000000',):
        parts.append(f"لون:{col.rgb}")
    return '|'.join(parts)


def walk(path):
    d = Document(path)
    out = []
    n = 0
    for p in d.paragraphs:
        txt = p.text
        marks = []
        for r in p.runs:
            inf = run_info(r)
            if inf:
                marks.append(f"[{inf}] {r.text.strip()[:400]}")
        if not txt.strip() and not marks:
            continue
        n += 1
        style = p.style.name if p.style is not None else ''
        out.append(f"--- ¶{n} ({style}) ---\n{txt}")
        if marks:
            out.append("  ★ تحديد: " + " ⏐ ".join(marks))
    # الجداول
    for ti, t in enumerate(d.tables, 1):
        out.append(f"\n=== جدول {ti} ({len(t.rows)}×{len(t.columns)}) ===")
        for ri, row in enumerate(t.rows, 1):
            cells = []
            for c in row.cells:
                hl = []
                for p in c.paragraphs:
                    for r in p.runs:
                        inf = run_info(r)
                        if inf and 'أصفر' in inf:
                            hl.append(r.text.strip()[:200])
                cells.append(c.text.strip() + (f"  ★[{'; '.join(hl)}]" if hl else ''))
            out.append(f"  ص{ri}: " + " | ".join(cells))
    return "\n".join(out)


def main():
    args = sys.argv[1:]
    if any(a in ('--help', '-h') for a in args):
        print(__doc__)
        return 0
    unknown = [a for a in args if a.startswith('-')]
    if unknown:
        print(f'وسيط غير معروف: {unknown[0]}', file=sys.stderr)
        return 2
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    print(walk(args[0]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
