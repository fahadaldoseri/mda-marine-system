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
import site_chrome  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "reports" / "en"


def missing_translation_error(page_name: str, missing: list[str]) -> str:
    """يبني رسالة واحدة حتمية بكل الوحدات الناقصة، بلا سقف تشخيصي."""
    unique = sorted({str(item).strip() for item in missing if str(item).strip()})
    return (
        f"فشل مغلق: نصوص عربية بلا ترجمة في {page_name} — أضفها إلى "
        "sources/i18n/en/glossary.json\n  - "
        + "\n  - ".join(unique)
    )


def _translate_page(ar_page: pathlib.Path, date: str, dst: pathlib.Path, tm, gl) -> pathlib.Path:
    if not ar_page.exists():
        raise SystemExit(f"صفحة الإصدار العربية غير موجودة: {ar_page}")
    page, missing, total = i18n_en.translate_page(ar_page.read_text(encoding="utf-8"), date, tm, gl)
    if missing:
        raise SystemExit(missing_translation_error(ar_page.name, missing))
    # عناوين بطاقة الأخبار عقد واجهة، وتُطابقها بوابة العدّاد حرفيًا.
    page = page.replace("Official Warnings and Advisories", "Official warnings and advisories")
    # توحيد تسمية صف البطاقة مع السجل الحاكم (تعديلات 2026-11-01: «التحذيرات والتنبيهات النشطة»)
    page = page.replace("Official warnings and advisories", "Active warnings and advisories")
    page = page.replace("Warnings and Active Advisories", "Active warnings and advisories")
    page = page.replace("Warnings and active advisories", "Active warnings and advisories")
    page = page.replace("Early Warning Signs 24–72 Hours", "Early-warning indicators 24–72 hours")
    # الروابط داخل النسخة الإنجليزية يجب أن تبقى على السطح الإنجليزي نفسه.
    page = page.replace(f'/reports/{date}.html#', f'/reports/en/{date}.html#')
    page = page.replace('/additions.html#', '/reports/en/additions.html#')
    # م-25 (ب): في النسخة الإنجليزية يصبح «ع» رابطًا إلى النسخة العربية للتاريخ نفسه.
    import re as _re
    page = _re.sub(
        r'<div class="sn-lang".*?</div>',
        site_chrome.lang_group("en", ar_href=f"/reports/{date}.html"),
        page, count=1, flags=_re.S,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    dst.write_text(page, encoding="utf-8")
    return dst


def build(date: str) -> pathlib.Path:
    tm = i18n_en.build_tm(date)
    gl = i18n_en.load_glossary()
    ar_page = ROOT / "dist" / "reports" / f"{date}.html"
    dst = _translate_page(ar_page, date, OUT / f"{date}.html", tm, gl)
    additions = ROOT / "dist" / "additions.html"
    # الإضافات سطح واحد للإصدار الأحدث، فلا تُعاد ترجمته بذاكرة إصدار أقدم
    # أثناء حلقة بناء كل التقارير؛ هذا كان يخلط نص 31 أكتوبر بذاكرة 29 أكتوبر.
    source_dates = sorted(p.name.split("-sectioned")[0] for p in (ROOT / "sources" / "i18n" / "en").glob("*-sectioned.en.md"))
    latest = source_dates[-1] if source_dates else date
    if additions.exists() and date == latest:
        _translate_page(additions, date, OUT / "additions.html", tm, gl)
    dates = sorted({p.stem for p in OUT.glob("*.html") if p.stem[:4].isdigit()})
    (OUT / "index.json").write_text(
        json.dumps({"dates": dates, "updated": date}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"   ✔ {dst.relative_to(ROOT)} · الإضافات: {('نعم' if (OUT / 'additions.html').exists() else 'لا')} · نسخ متاحة: {len(dates)}")
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    build(a.date)
