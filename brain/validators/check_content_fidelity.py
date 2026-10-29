#!/usr/bin/env python3
"""حاجز أمانة المحتوى — يمنع تكرار ك-303 وك-306.

الفحص الأول (أعمدة الجداول): أي قسم في المتن يحمل جدولًا بـ3 أعمدة أو أكثر ولا يطابق بصمة
جدول المصادر أو جدول الوقائع، يجب أن يُعرض في الصفحة المبنية ببطاقات بيانات (`.dg`) أو جدولًا،
ولا يجوز أن يتحوّل إلى بطاقات مصدر (`.src`) فتُسقط أعمدته.

الفحص الثاني (أعداد المصادر): سطر «إجمالي الوقائع المرمزة» في المتن يجب أن يطابق دفتر الوقائع
(عدد الوقائع · مجموع الإسنادات · عدد كل مصدر) — لا يُكتب عدد يدويًا.

الاستخدام: python3 validators/check_content_fidelity.py [--date YYYY-MM-DD] [--brain PATH] [--site PATH]
الخروج: 0 مطابق · 1 مخالف · 70 انهيار (فشل مغلق).
"""
import argparse, json, pathlib, re, sys

import os


def _root(env: str, base: pathlib.Path, *names: str) -> pathlib.Path:
    """جذر الشجرة: من متغيّر البيئة أو من مجلد شقيق معتمد (قابلية النقل)."""
    v = os.environ.get(env)
    if v:
        return pathlib.Path(v)
    for n in names:
        if (base / n).is_dir():
            return base / n
    return base / names[0]


_HOME = pathlib.Path(__file__).resolve().parents[1].parent
BRAIN = _root("BRAIN_DIR", _HOME, "brain-marine-news", "brain")
SITE = _root("SITE_DIR", _HOME, "seawatch", "site")


def fail(msg):
    print(f"  ✗ {msg}")
    return False


def is_source_status(header: str) -> bool:
    h = header
    return ("#" in h or "الرقم" in h) and "المصدر" in h and ("الحالة المقيسة" in h or "الفحص" in h) \
        and ("الإجراء" in h or "الرابط" in h or "المسار" in h)


def is_events(header: str) -> bool:
    return ("ما حدث" in header) or ("الرمز" in header and "حالة التأكيد" in header)


def md_tables(md_text):
    """عائد: [(عنوان القسم، رأس الجدول، عدد صفوفه)]."""
    out, sec = [], "—"
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("## "):
            sec = l[3:].strip()
        if l.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            header = l
            n = 0
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                n += 1
                j += 1
            out.append((sec, header, n))
            i = j
            continue
        i += 1
    return out


def check_tables(brain, site, date):
    md = brain / "reports" / f"{date}-sectioned.md"
    pages = [site / "dist" / "reports" / f"{date}.html", site / "dist" / "additions.html"]
    if not md.exists():
        return fail(f"متن التقرير غير موجود: {md}")
    tables = md_tables(md.read_text(encoding='utf-8'))
    risk = [(s, h, n) for s, h, n in tables
            if len([c for c in h.split('|') if c.strip()]) >= 3
            and not is_source_status(h) and not is_events(h)]
    if not risk:
        return True
    ok = True
    for page in pages:
        if not page.exists():
            continue
        html = page.read_text(encoding='utf-8')
        # خريطة: نص عنوان القسم ← جسم القسم (بعد تجريد الوسوم من العنوان)
        secmap = {}
        for m in re.finditer(r'(?s)<section[^>]*>(.*?)</section>', html):
            body = m.group(1)
            hm = re.search(r'(?s)<h2[^>]*>(.*?)</h2>', body)
            if not hm:
                continue
            title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', hm.group(1))).strip()
            secmap[title] = body
        for sec, header, n in risk:
            body = secmap.get(sec.strip())
            if body is None:
                continue
            src = len(re.findall(r'class="src[ "]', body))
            dg = len(re.findall(r'class="dg"', body))
            tbl = len(re.findall(r'<table', body))
            if src:
                ok = fail(f"{page.name} · قسم «{sec}»: جدول محتوى بـ{len([c for c in header.split('|') if c.strip()])} "
                          f"أعمدة ({n} صفًا) يحمل {src} بطاقة مصدر تُسقط الأعمدة (dg={dg} · جداول={tbl})")
            elif not (dg or tbl):
                ok = fail(f"{page.name} · قسم «{sec}»: جدول بـ{n} صفًا غير معروض لا ببطاقات بيانات ولا بجدول")
            else:
                print(f"  ✓ {page.name} · «{sec}»: dg={dg} · جداول={tbl} · src={src}")
    return ok


def check_source_counts(brain, site, date):
    md = brain / "reports" / f"{date}-sectioned.md"
    ledger = brain / "cumulative-2026" / "daily" / f"{date}.json"
    if not ledger.exists():
        print("  ↷ دفتر الوقائع غير متاح — تُجاوَز مطابقة الأعداد")
        return True
    rows = json.loads(ledger.read_text(encoding='utf-8'))
    counts = {}
    for r in rows:
        for p in re.split(r'[·,]', str(r.get('source', ''))):
            p = p.strip()
            if p:
                counts[p] = counts.get(p, 0) + 1
    total_attr = sum(counts.values())
    txt = md.read_text(encoding='utf-8')
    line = next((l for l in txt.splitlines() if l.startswith('إجمالي الوقائع المرمزة:')), None)
    if line is None:
        return fail("سطر «إجمالي الوقائع المرمزة» غير موجود في المتن")
    ok = True
    for num in (len(rows), total_attr):
        if str(num) not in line:
            ok = fail(f"السطر لا يذكر العدد المحتسب من الدفتر: {num}")
    for name, c in counts.items():
        key = name.split('(')[0].strip()
        short = key.split()[0]
        if key not in line and short not in line:
            ok = fail(f"لا ذكر لـ«{key}» في السطر")
    # مجموع الإسنادات المكتوبة: أرقام صريحة + صيغ المثنى والمفرد العربية
    clause = line.split('المنسوبة إليها')[-1]
    written = 0
    for m in re.finditer(r'(\d+)\s*(?:واقع|وقائع|واقعة)', clause):
        written += int(m.group(1))
    written += len(re.findall(r'واقعتان|واقعتين', clause)) * 2
    written += len(re.findall(r'واقعة واحدة', clause))
    if written != total_attr:
        ok = fail(f"مجموع الإسنادات المكتوبة في المتن {written} والدفتر {total_attr}")
    if ok:
        print(f"  ✓ أعداد المصادر مطابقة للدفتر: {len(rows)} واقعة · {total_attr} إسنادًا · {len(counts)} مصدرًا")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default='2026-10-29')
    ap.add_argument('--brain', default=str(BRAIN))
    ap.add_argument('--site', default=str(SITE))
    a = ap.parse_args()
    brain, site = pathlib.Path(a.brain), pathlib.Path(a.site)
    print(f"حاجز أمانة المحتوى · {a.date}")
    try:
        ok1 = check_tables(brain, site, a.date)
        ok2 = check_source_counts(brain, site, a.date)
    except Exception as e:  # فشل مغلق
        print(f"  ✗ انهيار المدقق: {type(e).__name__}: {e}")
        sys.exit(70)
    print("  النتيجة:", "مطابق ✓" if (ok1 and ok2) else "مخالف ✗")
    sys.exit(0 if (ok1 and ok2) else 1)


if __name__ == '__main__':
    main()
