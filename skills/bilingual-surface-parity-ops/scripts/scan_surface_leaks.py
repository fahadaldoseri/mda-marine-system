#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ماسح تسرّب الأسطح ثنائية اللغة — فشل مغلق.

يقيس ثلاثة أنواع من العيوب على مخرجات البناء:
  1) نص اللغة المصدر ظاهر في سطح اللغة الهدف (مقاطع حروف عربية في صفحة إنجليزية).
  2) رمز داخلي (مثل C/3) ظاهر في سطح قارئ — يُفحَص الرموز المطلوبة صراحةً،
     وتُستثنى مناطق التدقيق (<pre> · <code>) لأنها موضع الرمز المقصود.
  3) وحدات بلا ترجمة — تُقاس **بتاريخ كل صفحة**، لأن ذاكرة المحاذاة تخص تاريخها.

الاستخدام:
  python3 scan_surface_leaks.py --root /path/to/project --date 2026-11-09 --limit 4
  python3 scan_surface_leaks.py --root /path/to/project --codes C/3 --limit 0

الخروج: 0 إذا كان كل شيء نظيفًا، 2 عند أي عيب أو تعذّر قياس (فشل مغلق).
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys

ARABIC = re.compile(r"[\u0600-\u06FF]{2,}")
AUDIT_REGIONS = re.compile(r"<pre.*?</pre>|<code.*?</code>", re.S)
SKIP_TAGS = re.compile(r"<script.*?</script>|<style.*?</style>", re.S)
DATE_STEM = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def visible_text(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", SKIP_TAGS.sub(" ", html))


def reader_text(html: str) -> str:
    """نص القارئ: بلا وسوم وبلا مناطق تدقيق (الرمز داخل مناطق التدقيق مقصود)."""
    return AUDIT_REGIONS.sub(" ", html)


def load_module(path: pathlib.Path, name: str):
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        print(f"   ✘ تعذّر تحميل {path.name}: {exc}")
        return None
    return mod


def scan_codes(files: list[pathlib.Path], codes: list[str]) -> list[tuple[str, list[str]]]:
    if not codes:
        return []
    pattern = re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(re.escape(c) for c in codes) + r")(?![A-Za-z0-9_])")
    hits = []
    for f in files:
        found = sorted(set(pattern.findall(reader_text(f.read_text(encoding="utf-8", errors="ignore")))))
        if found:
            hits.append((str(f), found))
    return hits


def scan_source_language(files: list[pathlib.Path]) -> list[tuple[str, list[str]]]:
    hits = []
    for f in files:
        text = visible_text(f.read_text(encoding="utf-8", errors="ignore"))
        found = sorted({m.group(0) for m in ARABIC.finditer(text)})
        if found:
            hits.append((str(f), found[:5]))
    return hits


def scan_missing_units(root: pathlib.Path, translator: pathlib.Path, ar_glob: str,
                       fallback_date: str | None, limit: int) -> tuple[int, dict[str, list[str]]]:
    """يقيس الوحدات الناقصة لكل صفحة بتاريخها؛ يعيد عدد الصفحات وخريطة النواقص."""
    gen_dir = root / "generator"
    if str(gen_dir) not in sys.path:
        sys.path.insert(0, str(gen_dir))
    mod = load_module(translator, "project_i18n")
    if mod is None:
        return -1, {}
    gl = mod.load_glossary()
    pages = sorted(p for p in root.glob(ar_glob) if DATE_STEM.match(p.stem))
    if fallback_date:
        pages = [p for p in pages if p.stem == fallback_date] or pages
    if limit:
        pages = pages[:limit]
    missing: dict[str, list[str]] = {}
    for page in pages:
        date = page.stem
        try:
            tm = mod.build_tm(date)
            _out, miss, _total = mod.translate_page(page.read_text(encoding="utf-8"), date, tm, gl)
        except Exception as exc:
            missing[date] = [f"تعذّر القياس: {exc}"]
            continue
        if miss:
            missing[date] = sorted(set(miss))
    return len(pages), missing


def main() -> int:
    ap = argparse.ArgumentParser(description="مسح تسرّب الأسطح ثنائية اللغة")
    ap.add_argument("--root", required=True, help="جذر المشروع")
    ap.add_argument("--date", default=None, help="تاريخ الإصدار YYYY-MM-DD (لتضييق فحص الوحدات)")
    ap.add_argument("--en-dir", default="dist/reports/en", help="مجلد سطح اللغة الهدف")
    ap.add_argument("--all-glob", default="dist/**/*.html", help="نمط كل أسطح القارئ")
    ap.add_argument("--translator", default="generator/i18n_en.py", help="وحدة المترجم")
    ap.add_argument("--ar-glob", default="dist/reports/*.html", help="صفحات اللغة المصدر")
    ap.add_argument("--codes", default="", help="رموز داخلية تُفحَص صراحةً، مفصولة بفاصلة")
    ap.add_argument("--limit", type=int, default=0,
                    help="أقصى عدد صفحات يُفحَص للمترجم (0 = كل الصفحات؛ الفحص الكامل بطيء)")
    ap.add_argument("--no-translator", action="store_true", help="تجاوز فحص الوحدات الناقصة")
    a = ap.parse_args()

    root = pathlib.Path(a.root).resolve()
    if not (root / "dist").is_dir():
        print(f"   ✘ فشل مغلق: لا مخرج بناء في {root / 'dist'}")
        return 2

    targets = sorted((root / a.en_dir).glob("*.html"))
    all_surfaces = sorted(root.glob(a.all_glob))
    codes = [c.strip() for c in a.codes.split(",") if c.strip()]

    print("   ═══ مسح تسرّب الأسطح ═══")
    print(f"   صفحات اللغة الهدف: {len(targets)} · كل الأسطح: {len(all_surfaces)}")

    leaks = scan_source_language(targets)
    code_hits = scan_codes(all_surfaces, codes)
    pages, missing = (0, {})
    if not a.no_translator:
        pages, missing = scan_missing_units(root, root / a.translator, a.ar_glob, a.date, a.limit)

    ok = True
    print(f"   ■ نص اللغة المصدر في سطح الهدف: {len(leaks)} صفحة")
    for name, sample in leaks[:6]:
        print(f"      · {name}: {sample}")
    ok &= not leaks

    print(f"   ■ رموز داخلية في سطح القارئ: {len(code_hits)} صفحة (المفحوص: {codes or 'لا شيء'})")
    for name, sample in code_hits[:6]:
        print(f"      · {name}: {sample}")
    ok &= not code_hits

    if not a.no_translator:
        if pages < 0:
            print("   ✘ فشل مغلق: تعذّر قياس الوحدات الناقصة")
            return 2
        total = sum(len(v) for v in missing.values())
        print(f"   ■ وحدات بلا ترجمة: {total} عبر {pages} صفحة")
        for date, units in list(missing.items())[:4]:
            print(f"      · {date}: {len(units)} — {units[0][:90]}")
        ok &= total == 0

    print("   ── النتيجة:", "نظيف" if ok else "عيب مؤكد")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())