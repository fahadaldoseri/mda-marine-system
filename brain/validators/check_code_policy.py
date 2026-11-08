#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص سياسة عرض رموز الأحداث (2+5) على صفحات الموقع المبنية.

القاعدة الملزمة:
- الرمز الكامل `MN-YYYY-MM-DD-NN` يظهر **فقط** داخل قسم الوقائع (عنوانه «سجل الأحداث» أو يبدأ بـ«الوقائع»).
- أي ظهور كامل خارج ذلك القسم = مخالفة مانعة.
- الرمز المختصر (`DD-NN` أو `MM-DD-NN`) هو الصيغة المعروضة في بقية المواضع،
  ويُدمج مع رقم البلاغ الرسمي (`#172 · 15-04`) عند وجوده.

الاستخدام: python3 validators/check_code_policy.py [مجلد الموقع أو ملف]
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")
import re
import sys
from pathlib import Path

CODE_RE = re.compile(r"MN-\d{4}-\d{2}-\d{2}-\d{2}")
SECTION_RE = re.compile(r"<section\b[^>]*>(.*?)</section>", re.S)
H2_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
TAGS_RE = re.compile(r"<[^>]+>")


def section_title(html):
    m = H2_RE.search(html)
    return TAGS_RE.sub("", m.group(1)).strip() if m else ""


def check_file(path: Path):
    html = path.read_text(encoding="utf-8", errors="ignore")
    sections = SECTION_RE.findall(html)
    inside = outside = 0
    outside_samples = []
    for sec in sections:
        title = section_title(sec)
        n = len(CODE_RE.findall(sec))
        if not n:
            continue
        if title.startswith("سجل الأحداث") or title.startswith("الوقائع"):
            inside += n
        else:
            outside += n
            ctx = TAGS_RE.sub(" ", sec)
            m = CODE_RE.search(ctx)
            if m is not None:
                sample = ctx[max(0, m.start() - 50):m.end() + 30]
            else:
                # قد يكون الرمز داخل خاصية HTML؛ يظل مخالفة، لكن لا يظهر بعد نزع الوسوم.
                raw_match = CODE_RE.search(sec)
                sample = sec[max(0, raw_match.start() - 50):raw_match.end() + 30] if raw_match else "رمز كامل خارج النص المرئي"
            outside_samples.append(f"{title}: {TAGS_RE.sub(' ', sample).strip()[-90:]}")
    # ما قبل أول قسم (الترويسة والمقدمة) وبعده
    head = html.split("<main", 1)[0]
    tail = html.rsplit("</main>", 1)[-1]
    pre = len(CODE_RE.findall(head)) + len(CODE_RE.findall(tail))
    merged = re.findall(r"#\d{2,4}\s*·\s*\d{2}-\d{2}", html)
    return {"file": path.name, "inside": inside, "outside": outside, "pre": pre,
            "merged": len(merged), "samples": outside_samples}


def main():
    args = sys.argv[1:]
    if any(a in ("--help", "-h") for a in args):
        print(__doc__)
        return 0
    unknown = [a for a in args if a.startswith("-")]
    if unknown:
        print(f"وسيط غير معروف: {unknown[0]}", file=sys.stderr)
        return 2
    if len(args) > 1:
        print(__doc__, file=sys.stderr)
        return 2
    target = Path(args[0]) if args else Path(f"{SITE}/dist")
    files = sorted(target.glob("reports/*.html")) if target.is_dir() else [target]
    fails = 0
    print("  فحص سياسة عرض الرموز (2+5):")
    for f in files:
        r = check_file(f)
        bad = r["outside"] + r["pre"]
        mark = "✔" if bad == 0 else "✘"
        if bad:
            fails += 1
        print(f"   {mark} {r['file']}: كامل داخل الوقائع {r['inside']} · خارجها {r['outside']} · "
              f"في الترويسة/المقدمة {r['pre']} · مدموج برقم بلاغ {r['merged']}")
        for s in r["samples"][:3]:
            print(f"      - {s}")
    print(f"  النتيجة: {'اجتاز الفحص' if fails == 0 else f'{fails} صفحة مخالفة'}")
    return 1 if fails else 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
