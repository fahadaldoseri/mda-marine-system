#!/usr/bin/env python3
"""مقياس أمانة محتوى التقرير: هل ما في المتن يظهر كاملًا على الصفحة المبنية؟

الفحوص:
  1) أمانة الأعمدة: كل قسم في المتن يحمل جدول محتوى (3 أعمدة فأكثر) يجب أن يظهر على الصفحة
     بجدول أو ببطاقات بيانات (class="dg") — لا ببطاقات مصدر (class="src").
  2) أعداد المصادر: إن مُرِّر دفتر الوقائع، تُحتسب الأعداد منه وتُقارن بما هو مكتوب في المتن.

الاستعمال:
  python3 check_surface_fidelity.py --md REPORT.md --html PAGE.html [--ledger LEDGER.json] \
      [--sections "قسم أ" "قسم ب"] [--cards-selector dg] [--src-selector src]

الخروج: 0 مطابق · 1 خرق · 2 خطأ استعمال.
"""
import argparse, json, re, sys
from pathlib import Path

def md_sections(text):
    """يرجع {العنوان: نص القسم} لكل عناوين ## وما دونها."""
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            if cur: out[cur] = "\n".join(buf)
            cur, buf = m.group(1).strip(), []
        elif cur is not None:
            buf.append(line)
    if cur: out[cur] = "\n".join(buf)
    return out

def table_shape(block):
    """(عدد الصفوف، أقصى عدد أعمدة) لجدول Markdown."""
    rows = [l for l in block.splitlines() if l.strip().startswith("|")]
    rows = [r for r in rows if not re.fullmatch(r"\|[\s:\-|]+\|", r.strip())]
    cols = 0
    for r in rows:
        cols = max(cols, len([c for c in r.strip().strip("|").split("|")]))
    return len(rows), cols

def html_section(html, title):
    """نص القسم من الصفحة المبنية: يفضّل ظهور العنوان داخل وسم عنوان، ثم يمتد للنافذة الأوسع."""
    idx = [m.start() for m in re.finditer(r'<h[2-3][^>]*>[^<]*' + re.escape(title), html)]
    if not idx:
        idx = [m.start() for m in re.finditer(re.escape(title), html)]
    if not idx:
        return ""
    i = idx[0]
    j = html.find("</section>", i)
    win = html[i: j if j > 0 else i + 60000]
    if len(win) < 400 or ('class="dg' not in win and 'class="src' not in win):
        win = html[i: i + 60000]
    return win

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--html", required=True)
    ap.add_argument("--ledger")
    ap.add_argument("--sections", nargs="*", default=[])
    ap.add_argument("--cards-selector", default="dg")
    ap.add_argument("--src-selector", default="src")
    a = ap.parse_args()

    md = Path(a.md).read_text(encoding="utf-8")
    html = Path(a.html).read_text(encoding="utf-8")
    secs = md_sections(md)
    titles = a.sections or [t for t in secs if table_shape(secs[t])[1] >= 3]
    bad, checked = [], 0
    for t in titles:
        block = secs.get(t, "")
        rows, cols = table_shape(block)
        if cols < 3:
            print(f"  – تخطّي «{t}»: لا جدول محتوى في المتن")
            continue
        h = html_section(html, t)
        if not h:
            bad.append(f"قسم «{t}» غائب عن الصفحة المبنية"); continue
        dg = len(re.findall(r'class="%s[ "]' % re.escape(a.cards_selector), h))
        src = len(re.findall(r'class="%s[ "]' % re.escape(a.src_selector), h))
        checked += 1
        if src and not dg:
            bad.append(f"قسم «{t}»: جدول {cols} أعمدة ({rows} صفًا) يظهر {src} بطاقة مصدر تُسقط الأعمدة")
        else:
            print(f"  ✓ «{t}»: أعمدة={cols} · صفوف={rows} · بطاقات بيانات={dg} · بطاقات مصدر={src}")

    if a.ledger:
        try:
            d = json.loads(Path(a.ledger).read_text(encoding="utf-8"))
            if isinstance(d, list):
                rows = d
            else:
                rows = d.get("rows") or d.get("events") or d.get("daily") or []
            ev = len(rows)
            at = sum(len(r.get("attributions", []) or []) for r in rows) or ev
            srcs = {s for r in rows for s in (r.get("sources") or [])}
            print(f"  · الدفتر: {ev} واقعة · {at} إسنادًا · {len(srcs)} مصدرًا")
            for n in (ev, at, len(srcs)):
                if not re.search(r"(?<!\d)%d(?!\d)" % n, md):
                    bad.append(f"العدد {n} المحتسب من الدفتر غير موجود في المتن")
        except Exception as e:
            bad.append(f"تعذّر قراءة الدفتر: {e}")

    print("  النتيجة:", "مطابق ✓" if not bad else "خرق ✗")
    for b in bad: print("   ✗", b)
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
