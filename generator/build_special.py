#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد قسم «التقارير الخاصة» — صفحة فهرس + صفحة لكل تقرير.

المصدر الوحيد للحقيقة:
  sources/special/<slug>.md    → متن التقرير (Markdown بأقسام ##)
  sources/special/<slug>.json  → بيانات الواجهة (عنوان، ملخص، تاريخ، تصنيف، وسوم)

المخرجات:
  dist/reports/special.html            فهرس التقارير الخاصة
  dist/reports/special-<slug>.html     صفحة كل تقرير

يُدمج تلقائيًا في بناء الموقع (build_site.py) ويُحدَّث مع كل إصدار.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
sys.path.insert(0, str(HERE))

import build_report as BR  # noqa: E402
import site_chrome as CH  # noqa: E402

SPECIAL_DIR = SITE / "sources" / "special"

AR_MONTHS = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}

INDEX_CSS = """
.sp-head{padding:30px 0 4px}
.sp-head h1{font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;font-size:clamp(24px,3vw,34px);margin:0 0 8px}
.sp-head p{color:var(--muted);margin:0;max-width:74ch;font-size:14.5px}
.sp-grid{display:grid;gap:14px;margin:26px 0 40px}
.sp-card{
  display:block;border:1px solid var(--line);border-radius:12px;background:var(--panel);
  padding:18px 20px;text-decoration:none;color:inherit;transition:border-color .18s ease,transform .18s ease
}
.sp-card:hover{border-color:var(--line-2);transform:translateY(-1px);text-decoration:none}
.sp-top{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
.sp-tag{font-size:11.5px;border-radius:999px;padding:3px 10px;border:1px solid var(--line-2);background:var(--panel2);color:var(--ink2)}
.sp-tag.sp-hot{color:#ffd7d3;background:rgba(255,93,82,.16);border-color:rgba(255,93,82,.42)}
.sp-tag.sp-code{font-family:"IBM Plex Mono",monospace;direction:ltr;unicode-bidi:isolate}
.sp-card h2{font-family:"Noto Kufi Arabic",sans-serif;font-size:19px;font-weight:600;margin:0 0 6px;line-height:1.55}
.sp-card p{margin:6px 0 0;color:var(--ink2);font-size:14.5px;line-height:1.85}
.sp-meta{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px;color:var(--faint);font-size:12.5px}
.sp-open{color:var(--accent);font-size:13px}
.sp-empty{border:1px dashed var(--line-2);border-radius:12px;padding:26px;color:var(--muted);text-align:center}
@media print{.sp-card{break-inside:avoid;page-break-inside:avoid}}
"""


def esc(t) -> str:
    return BR.esc(t)


def ar_date(iso: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    if not m:
        return iso or "—"
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{d} {AR_MONTHS.get(mo, mo)} {y}"


def discover() -> list:
    """يقرأ ملفات التقارير الخاصة، ويُرجع قائمة مرتّبة بالأحدث."""
    items = []
    if not SPECIAL_DIR.exists():
        return items
    for meta_path in sorted(SPECIAL_DIR.glob("*.json")):
        slug = meta_path.stem
        md_path = SPECIAL_DIR / f"{slug}.md"
        if not md_path.exists():
            print(f"  · تُجوهل {slug}: لا ملف نصي مطابق")
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  ✘ ملف واجهة غير صالح ({slug}): {e}")
            continue
        if not isinstance(meta, dict):
            print(f"  ✘ ملف واجهة ليس كائن JSON ({slug})")
            continue
        meta.setdefault("title", slug)
        meta.setdefault("date", "")
        items.append({"slug": slug, "md": md_path, "meta": meta})
    items.sort(key=lambda x: (x["meta"].get("date") or "", x["slug"]), reverse=True)
    return items


def build_one(item: dict, dist: Path) -> Path:
    out = dist / "reports" / f"special-{item['slug']}.html"
    path, _ = BR.build(item["md"], out, item["meta"])
    html = path.read_text(encoding="utf-8")
    html = CH.inject(html, "special", "تقرير خاص — مستقل عن الإصدار اليومي")
    path.write_text(html, encoding="utf-8")
    return path


def build_index(items: list, dist: Path) -> Path:
    cards = []
    for it in items:
        m = it["meta"]
        cls = str(m.get("classification") or "عام")
        tag_cls = "sp-tag sp-hot" if cls in ("مقيّد", "حساس") else "sp-tag"
        kpis = m.get("hero_kpis") or []
        kpi_txt = " · ".join(f'{esc(k.get("label",""))}: {esc(str(k.get("value","")))}' for k in kpis[:3])
        cards.append(f"""<a class="sp-card" href="/reports/special-{esc(it['slug'])}.html">
      <div class="sp-top">
        <span class="{tag_cls}">{esc(cls)}</span>
        <span class="sp-tag sp-code">{esc(m.get('code') or '')}</span>
        <span class="sp-tag">{esc(ar_date(m.get('date')))}</span>
      </div>
      <h2>{esc(m.get('title') or it['slug'])}</h2>
      <p>{esc(m.get('summary') or m.get('lede') or '')}</p>
      {f'<div class="sp-meta"><span>{kpi_txt}</span></div>' if kpi_txt else ''}
      <div class="sp-meta">
        <span>{' · '.join(esc(t) for t in (m.get('tags') or []))}</span>
      </div>
      <div class="sp-meta"><span class="sp-open">افتح التقرير كاملًا ←</span></div>
    </a>""")
    body = "\n".join(cards) if cards else (
        '<div class="sp-empty">لا توجد تقارير خاصة منشورة بعد. تُضاف آليًا عند إنشاء تقرير موضوعي مستقل.</div>'
    )
    html = f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="التقارير الخاصة — مركز الوعي بالمجال البحري: تقارير موضوعية مستقلة عن الإصدار اليومي، مبنية على مصادر رسمية موثقة.">
<meta name="theme-color" content="#040810">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<title>التقارير الخاصة — {esc(CH.BRAND)}</title>
<link rel="stylesheet" href="{BR.FONT_LINK}">
<style>{BR.DESIGN_TOKENS}{BR.STYLE}{BR.DAYLIGHT}{INDEX_CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="sp-head">
    <h1>التقارير الخاصة</h1>
    <p>تقارير موضوعية مستقلة عن الإصدار اليومي: حادث بعينه أو مسار تهديد محدد، بمصادر رسمية موثقة وتوقيت مزدوج (UTC وتوقيت البحرين).
    تُبنى هذه الصفحة آليًا من ملفات التقارير الخاصة، وتُحدَّث مع كل إصدار.</p>
  </header>
  <div class="sp-grid">
{body}
  </div>
</div>
<script>{BR.SCRIPT}</script>
</body></html>"""
    out = dist / "reports" / "special.html"
    out.write_text(CH.inject(html, "special"), encoding="utf-8")
    return out


def update_routes(dist: Path, items: list) -> int:
    """يضيف مسارات التقارير الخاصة إلى بيان المسارات (manus-routes.json)."""
    rf = dist / "manus-routes.json"
    data = {"routes": []}
    if rf.exists():
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"routes": []}
    routes = data.get("routes") or []
    have = {r.get("path") for r in routes if isinstance(r, dict)}
    wanted = [{"path": "/reports/special.html", "title": "التقارير الخاصة"}]
    for it in items:
        wanted.append({"path": f"/reports/special-{it['slug']}.html",
                       "title": str(it["meta"].get("title") or it["slug"])[:120]})
    added = 0
    for w in wanted:
        if w["path"] not in have:
            routes.append(w)
            added += 1
    data["routes"] = routes
    rf.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return added


def update_sitemap(dist: Path, items: list, site: str = "https://seawatch-xp4qirmr.manus.space") -> int:
    """يضيف روابط التقارير الخاصة إلى خريطة الموقع إن لم تكن موجودة."""
    sf = dist / "sitemap.xml"
    if not sf.exists():
        return 0
    xml = sf.read_text(encoding="utf-8")
    urls = [f"{site}/reports/special.html"] + [f"{site}/reports/special-{it['slug']}.html" for it in items]
    added = 0
    body = []
    for u in urls:
        if u in xml:
            continue
        body.append(f"<url><loc>{u}</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>")
        added += 1
    if body:
        xml = xml.replace("</urlset>", "\n".join(body) + "\n</urlset>")
        sf.write_text(xml, encoding="utf-8")
    return added


def build_all(dist: Path, quiet: bool = False) -> tuple:
    """يبني الفهرس وصفحات التقارير الخاصة، ويحدّث المسارات وخريطة الموقع."""
    items = discover()
    pages = [build_index(items, dist)]
    for it in items:
        pages.append(build_one(it, dist))
    n_routes = update_routes(dist, items)
    n_sitemap = update_sitemap(dist, items)
    if not quiet:
        print(f"التقارير الخاصة: {len(items)} تقرير · صفحات: {len(pages)} · مسارات مضافة: {n_routes} · خريطة: +{n_sitemap}")
    return len(pages), len(items)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default=str(SITE / "dist"))
    a = ap.parse_args()
    n_pages, n_items = build_all(Path(a.dist))
    print(f"OK · صفحات: {n_pages} · تقارير: {n_items}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
