#!/usr/bin/env python3
"""إصلاح بوابة الفحص الصارم في check_additions_surface.py:
1) تطبيع نصّ PDF (إزالة محارف الاتجاه والتشكيل والتطويل) ليطابق العناوين العربية المشوّهة.
2) استثناء صفحة الفهرس (صفحة تحمل ≥3 عناوين منقولة) وصفحات ملحق «إضافات».
3) الإبلاغ بأرقام الصفحات المخالفة فقط، لا بالعنوان المجرّد.
4) استخراج دالة نقية violating_pages() ليمكن اختبارها سلبيًا.
"""
from pathlib import Path
import re
import sys

F = Path('/home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py')
t = F.read_text(encoding='utf-8')

HELPERS = '''
BIDI = re.compile(r"[\\u202a-\\u202e\\u2066-\\u2069\\u200e\\u200f]")
TASHKEEL = re.compile(r"[\\u064b-\\u0652\\u0640]")


def norm(s: str) -> str:
    """تطبيع نصّ عربي/لاتيني: بلا محارف اتجاه ولا تشكيل، ومسافات موحّدة."""
    s = BIDI.sub("", s or "")
    s = TASHKEEL.sub("", s)
    return re.sub(r"\\s+", " ", s).strip()


def violating_pages(text: str, titles: list[str], min_index_hits: int = 3) -> dict:
    """يرجع {العنوان: [أرقام صفحات مخالفة]} — باستثناء صفحات الفهرس وملحق الإضافات."""
    pages = [norm(p) for p in (text or "").split("\\f")]
    if not pages:
        return {}
    normed = {t: norm(t) for t in titles if norm(t)}
    hits = {t: [i + 1 for i, p in enumerate(pages) if v in p] for t, v in normed.items()}
    index_pages = {i + 1 for i, p in enumerate(pages)
                   if sum(1 for v in normed.values() if v in p) >= min_index_hits}
    annex = None
    for i, p in enumerate(pages):
        if "إضافات" in p and (i + 1) not in index_pages:
            annex = i + 1
            break
    out = {}
    for t, ps in hits.items():
        bad = [n for n in ps if n not in index_pages and (annex is None or n < annex)]
        if bad:
            out[t] = bad
    return out

'''

if 'def violating_pages' not in t:
    anchor = 'def pdf_text(path: Path) -> str:'
    i = t.index(anchor)
    j = t.index('def ', i + 10) if 'def ' in t[i + 10:] else len(t)
    t = t[:j] + HELPERS + t[j:]
    print('  ✔ أُضيفت norm() و violating_pages()')

old_block = '''        if not text: (errors if a.strict_print else warnings).append("تعذر استخراج PDF")'''
if old_block not in t:
    print('  ✘ لم أجد كتلة فحص PDF المتوقّعة')
    sys.exit(2)

start = t.index(old_block)
end = t.index('notes.append(f"طباعة مفحوصة من {pdf.name} وفق السياسة")', start)
new_block = '''        if not text:
            (errors if a.strict_print else warnings).append("تعذر استخراج PDF")
        else:
            bad = violating_pages(text, adds)
            if bad:
                detail = " · ".join(f"«{k}» ص{','.join(map(str, v))}" for k, v in bad.items())
                (errors if a.strict_print else warnings).append(
                    f"قسم منقول ظاهر في متن التقرير المطبوع: {detail}")
            else:
                npg = len([p for p in text.split("\\f") if p.strip()])
                notes.append(f"لا قسم منقول في متن التقرير المطبوع (فُحص {npg} صفحة، باستثناء الفهرس والملحق)")
'''
t = t[:start] + new_block + t[end:]
F.write_text(t, encoding='utf-8')
print('  ✔ استُبدلت كتلة فحص PDF بالمنطق السطحي الصحيح')

TEST = '''#!/usr/bin/env python3
"""اختبار سلبي/إيجابي لدالة violating_pages — يفصل الفهرس والملحق عن متن التقرير."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_additions_surface import violating_pages  # noqa: E402

B = "\\u202b"   # محرف اتجاه يظهر في pdftotext
M = "\\u064e"   # تشكيل

INDEX = f"الفهرس {B}التوجيهات التشغيلية{B} {B}الوقائع الجديدة{B} {B}الخلفية{B} {B}التحذيرات والنشرات الرسمية{B}"
BODY = f"{B}بطاقة القرار{B} متن التقرير بلا أقسام منقولة"
ANNEX = f"{B}إضافات{B} {B}الوقائع الجديدة{B} تفصيل الوقائع {B}الخلفية{B} سياق الخلفية"

cases = [
    ("فهرس + متن نظيف + ملحق فيه العناوين → يجتاز", [INDEX, BODY, ANNEX], {}),
    ("عنوان منقول في متن التقرير → يُمنع", [INDEX, f"{B}الوقائع الجديدة{B} تفصيل داخل المتن", ANNEX],
     {"الوقائع الجديدة": [2]}),
    ("عنوان منقول في الفهرس وحده → يجتاز", [INDEX, BODY], {}),
    ("عنوان بتشكيل مختلف في المتن → يُمنع", [INDEX, f"{B}الوقا{M}ئع الجديدة{B}", ANNEX],
     {"الوقائع الجديدة": [2]}),
]

ok = True
for name, pages, expected in cases:
    got = violating_pages("\\f".join(pages), ["التوجيهات التشغيلية", "الوقائع الجديدة", "الخلفية", "التحذيرات والنشرات الرسمية"])
    good = got == expected
    ok &= good
    print(f"  {'✔' if good else '✘'} {name} → {got}")

print("  الحصيلة:", "كل الاختبارات نجحت ✔" if ok else "فشل ✘")
sys.exit(0 if ok else 2)
'''
T = Path('/home/ubuntu/skills/report-surface-policy-ops/tests')
T.mkdir(parents=True, exist_ok=True)
(T / 'test_strict_print.py').write_text(TEST, encoding='utf-8')
print('  ✔ كُتب الاختبار السلبي tests/test_strict_print.py')