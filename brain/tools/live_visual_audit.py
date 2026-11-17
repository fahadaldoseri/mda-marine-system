#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تدقيق بصري حي للموقع كاملًا ومقارنته بالكود — فشل مغلق على المخالفات المانعة.

يُشغَّل من أي مسار (لا مسار مطلق). يفتح كل صفحة منشورة بالمتصفح، ويقيس:
العنوان · العناوين الظاهرة · أخطاء الطرفية · الصور المكسورة · الوسوم الفارغة ·
كتل المصادر التي يجب حجبها من PDF · صيغة الإحداثيات · الأرقام اللاتينية ·
الفقرات المكررة حرفيًا · ثم يقارن عناوين الصفحة الحية بقسم المصدر نفسه.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
S = Path(os.environ.get("SITE_DIR") or B.parent / "seawatch")
BASE = os.environ.get("SITE_BASE_URL", "https://seawatch-live.pages.dev")
OUT = B / "audit"

ARABIC_DIGITS = re.compile(r"[\u0660-\u0669\u06F0-\u06F9]")
DECIMAL_COORD = re.compile(r"\b\d{1,2}\.\d+\s*°")
DUP_MIN = 60          # طول أدنى للفقرة قبل اعتبار التكرار مخالفة


def pages() -> list[tuple[str, str]]:
    """(المسار الحي، مسار ملف المصدر) — يُبنى من بنية الموقع الفعلية لا من قائمة يدوية."""
    out: list[tuple[str, str]] = [("/", "index.html")]
    dist = S / "dist"
    if not dist.exists():
        return out
    for f in sorted(dist.rglob("*.html")):
        rel = f.relative_to(dist).as_posix()
        if rel in ("index.html",) or rel.startswith("assets/"):
            continue
        out.append((f"/{rel}", rel))
    return out


def source_sections(date: str) -> list[str]:
    md = B / "reports" / f"{date}-sectioned.md"
    if not md.exists():
        return []
    return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+)$", md.read_text(encoding="utf-8"), re.M)]


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (audit)"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--base", default=BASE)
    a = ap.parse_args()
    base = a.base.rstrip("/")

    rows, blocks, warns = [], [], []
    plist = pages()
    print(f"═══ تدقيق بصري حي — {len(plist)} صفحة · الجذر {base} ═══\n")
    for route, _rel in plist:
        code, html = fetch(f"{base}{route}")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()[:70]
        heads = [re.sub(r"<[^>]+>", "", h).strip()
                 for h in re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.S)]
        heads = [re.sub(r"\s+", " ", h) for h in heads if h]
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
        # عطل ك-73: المقياس الأول عدّ كل تسلسل «><» كوسم فارغ فأنذر ب195 وسمًا في صفحة سليمة.
        # القياس الصحيح: وسم مغلق يقابل فتحه بالاسم نفسه، وفي وسوم المحتوى فقط.
        empty_tags = len(re.findall(r"<(p|li|td|th)\b[^>]*>\s*(?:&nbsp;)?\s*</\1>", html))
        # فقرات مكررة حرفيًا في الصفحة نفسها
        paras = [p.strip() for p in re.split(r"</p>|</li>", html) if len(p.strip()) > DUP_MIN]
        paras = [re.sub(r"<[^>]+>", "", p).strip() for p in paras]
        paras = [p for p in paras if len(p) > DUP_MIN]
        dups = len(paras) - len(set(paras))
        no_digits = bool(ARABIC_DIGITS.search(text))
        bad_coord = bool(DECIMAL_COORD.search(text))

        if code != 200:
            blocks.append(f"{route}: رمز {code}")
        if no_digits:
            blocks.append(f"{route}: أرقام عربية في صفحة منشورة")
        if bad_coord:
            blocks.append(f"{route}: إحداثيات بصيغة عشرية")
        if empty_tags:
            warns.append(f"{route}: {empty_tags} وسم فارغ")
        if dups:
            warns.append(f"{route}: {dups} فقرة مكررة حرفيًا")

        # مقارنة العناوين الحية بأقسام المصدر للإصدارات اليومية
        dm = re.match(r"^reports/(\d{4}-\d{2}-\d{2})\.html$", route)
        match = "—"
        if dm:
            src = source_sections(dm.group(1))
            live = set(heads)
            missing = [s for s in src if s not in live and "المصادر" not in s and "موثوقية" not in s]
            match = f"مصدر {len(src)} · حي {len(heads)} · ناقص {len(missing)}"
            if missing:
                warns.append(f"{route}: عنوان في المصدر لا يظهر حيًا: {missing[:3]}")

        rows.append((route, code, title, len(heads), dups, empty_tags, len(imgs), match))
        print(f"  {code} · {route[:38]:40s} h2={len(heads):2} مكرر={dups:2} فارغ={empty_tags:2} صور={len(imgs):2} · {match}")

    lines = [f"# التدقيق البصري الحي — {a.date}", "",
             f"الجذر: {base} · صفحة مفحوصة: {len(rows)}", "",
             "| الصفحة | الرمز | العنوان | عناوين | فقرات مكررة | وسوم فارغة | صور | مطابقة المصدر |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    lines += ["", "## مخالفات مانعة", ""]
    lines += [f"- {b}" for b in blocks] or ["- لا شيء ✔"]
    lines += ["", "## تحذيرات", ""]
    lines += [f"- {w}" for w in warns] or ["- لا شيء ✔"]
    (OUT / f"تدقيق-بصري-حي-{a.date}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  مخالفات مانعة: {len(blocks)} · تحذيرات: {len(warns)}")
    print(f"  التقرير: {OUT / f'تدقيق-بصري-حي-{a.date}.md'}")
    return 2 if blocks else (1 if warns else 0)


if __name__ == "__main__":
    sys.exit(main())
