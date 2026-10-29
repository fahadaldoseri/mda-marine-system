#!/usr/bin/env python3
"""بناء النسخة الإنجليزية لإصدار يومي بترجمة صفحة الإصدار العربية نفسها.

المبدأ (ك-311): النسخة الإنجليزية ليست إعادة بناء من Markdown بمُحلّل خاص — لأن ذلك
يُسقط الخريطة التشغيلية وشبكة بطاقات الوقائع ووحدة أزرار الشريط وسياسة الطيّ. بل هي
صفحة الإصدار العربية المبنية بوسمها حرفيًا، مع ترجمة عقود النصوص فقط.

المدخل:  dist/reports/<DATE>.html                     (صفحة الإصدار العربية)
         sources/i18n/en/<DATE>-sectioned.en.md       (الترجمة المعتمدة للمتن)
         sources/i18n/en/glossary.json                (معجم الواجهة الإنجليزي)
المخرج:  dist/reports/en/<DATE>.html + index.json

البوابة: لا يُكتب مخرج إذا بقي أي نص عربي غير مترجم (فشل مغلق).

الاستعمال: python3 generator/build_report_en.py --date 2026-10-29
"""
from __future__ import annotations
import argparse, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import i18n_en  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "reports" / "en"


def build(date: str) -> pathlib.Path:
    ar_page = ROOT / "dist" / "reports" / f"{date}.html"
    if not ar_page.exists():
        raise SystemExit(f"صفحة الإصدار العربية غير موجودة: {ar_page}")
    tm = i18n_en.build_tm(date)
    gl = i18n_en.load_glossary()
    page, missing, total = i18n_en.translate_page(ar_page.read_text(encoding="utf-8"), date, tm, gl)
    if missing:
        raise SystemExit(
            "فشل مغلق: نصوص عربية بلا ترجمة — أضفها إلى sources/i18n/en/glossary.json\n  - "
            + "\n  - ".join(sorted(set(missing))[:15])
        )
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{date}.html"
    dst.write_text(page, encoding="utf-8")
    dates = sorted({p.stem for p in OUT.glob("*.html") if p.stem[:4].isdigit()})
    (OUT / "index.json").write_text(
        json.dumps({"dates": dates, "updated": date}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"   ✔ {dst.relative_to(ROOT)} · عقود نصوص مترجمة: {total} · نسخ متاحة: {len(dates)}")
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    build(a.date)
