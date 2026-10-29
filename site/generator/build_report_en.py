#!/usr/bin/env python3
"""بناء صفحة إنجليزية لإصدار يومي من ملف الترجمة المعتمد.

المدخل:  sources/i18n/en/<DATE>-sectioned.en.md   (ترجمة أمينة عن متن التقرير)
المخرج:  dist/reports/en/<DATE>.html + dist/reports/en/index.json
التصميم: يُعاد استعمال وسم <style> من صفحة الإصدار العربية نفسها لضمان تطابق الهيئة.
الاستعمال: python3 generator/build_report_en.py --date 2026-10-29
"""
from __future__ import annotations
import argparse, html, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import site_chrome  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "i18n" / "en"
OUT = ROOT / "dist" / "reports" / "en"


def esc(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s


def table_html(rows: list[str]) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [c for c in cells if not all(re.fullmatch(r":?-{2,}:?", x or "-") for x in c)]
    if not cells:
        return ""
    head, body = cells[0], cells[1:]
    out = ["<table><thead><tr>" + "".join(f"<th>{esc(c)}</th>" for c in head) + "</tr></thead><tbody>"]
    for r in body:
        out.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def md_to_sections(md: str) -> str:
    out: list[str] = []
    lines = md.split("\n")
    i = 0
    title_seen = False
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("# ") and not title_seen:
            out.append(f'<section class="doc"><h1>{esc(ln[2:].strip())}</h1>')
            title_seen = True
            i += 1
            continue
        if ln.startswith("## "):
            if title_seen:
                out.append("</section>")
            out.append(f'<section class="doc"><h2>{esc(ln[3:].strip())}</h2>')
            title_seen = True
            i += 1
            continue
        if ln.startswith("### "):
            out.append(f"<h3>{esc(ln[4:].strip())}</h3>")
            i += 1
            continue
        if ln.strip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(table_html(rows))
            continue
        if re.match(r"^\s*[-*]\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(esc(re.sub(r"^\s*[-*]\s+", "", lines[i]).strip()))
                i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            continue
        if not ln.strip():
            i += 1
            continue
        out.append(f"<p>{esc(ln.strip())}</p>")
        i += 1
    if title_seen:
        out.append("</section>")
    return "\n".join(out)


def ar_style(date: str) -> str:
    """استخراج الهيئة البصرية من صفحة الإصدار العربية لضمان تطابق التصميم."""
    p = ROOT / "dist" / "reports" / f"{date}.html"
    if not p.exists():
        return ""
    h = p.read_text(encoding="utf-8")
    m = re.search(r"<style>.*?</style>", h, re.S)
    return m.group(0) if m else ""


def build(date: str) -> pathlib.Path:
    src = SRC / f"{date}-sectioned.en.md"
    if not src.exists():
        raise SystemExit(f"ملف الترجمة غير موجود: {src}")
    body = md_to_sections(src.read_text(encoding="utf-8"))
    style = ar_style(date)
    title = f"Daily Maritime Security Report — {date} (English edition)"
    page = f"""<!DOCTYPE html>
<html lang="en" dir="ltr" data-lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
{style}
</head>
<body class="lang-en">
<main class="page">
<div class="wrap">
{body}
</div>
</main>
</body>
</html>
"""
    page = site_chrome.inject(page, "report", "English edition · machine-assisted translation governed against the Arabic source")
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{date}.html"
    dst.write_text(page, encoding="utf-8")
    dates = sorted({p.stem for p in OUT.glob("*.html") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)})
    (OUT / "index.json").write_text(
        json.dumps({"dates": dates, "updated": date}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"   ✔ {dst.relative_to(ROOT)} · {len(body) // 1024} ك.ب · نسخ متاحة: {len(dates)}")
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    build(a.date)
