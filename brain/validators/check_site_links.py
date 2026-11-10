#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس روابط الموقع وفهرس المحتويات — فشل مغلق.

يُقاس على المخرج المبني (`$SITE_DIR/dist`)، لا على المصدر، لأن العطل يظهر في
الصفحة التي يقرأها القارئ.

يفحص:
  1) لا رابط فارغ (`href="#"`) في أي صفحة.
  2) لا رابط غير مشفّر (`http://`) في أي صفحة.
  3) كل مرساة داخلية (`href="#x"`) لها عنصر `id="x"` في الصفحة نفسها.
  4) كل رابط إلى صفحة أخرى مع مرساة (`page.html#x`) يشير إلى ملف موجود فيه `id="x"`.
  5) كل قسم مرئي (`<section id="sec-*">` فيه عنوان `h2`) يظهر في فهرس المحتويات
     (`nav.toc`) في الصفحة نفسها — فلا قسم خارج الفهرس ولا فهرس لا يطابق الصفحة.

رموز الخروج: 0 سليم · 2 مخالفة مانعة · 3 خطأ بيئة (لا مخرج/جذر مفقود).
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
from pathlib import Path

_BRAIN = pathlib.Path(__file__).resolve().parents[1]
DEF_SITE = (os.environ.get("SITE_DIR") or os.environ.get("SITE")
            or str(_BRAIN.parent / "seawatch"))

TAG_RE = re.compile(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>", re.S | re.I)
A_RE = re.compile(r"<a\b[^>]*\bhref\s*=\s*\"([^\"]*)\"", re.I)
ID_RE = re.compile(r"\bid\s*=\s*\"([^\"]+)\"", re.I)
SEC_RE = re.compile(r"<section\b[^>]*\bid\s*=\s*\"(sec-[^\"]+)\"[^>]*>", re.I)
H2_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
TOC_RE = re.compile(r"<nav\b[^>]*class=\"[^\"]*\btoc\b[^\"]*\"[^>]*>(.*?)</nav>", re.S | re.I)

SKIP_PREFIX = ("mailto:", "tel:", "javascript:", "data:", "#!")


def text_only(html: str) -> str:
    return TAG_RE.sub(" ", html)


def ids_of(html: str) -> set:
    return set(ID_RE.findall(text_only(html)))


def pages(dist: Path) -> list:
    return sorted(p for p in dist.rglob("*.html") if p.is_file())


def toc_targets(html: str) -> set:
    out = set()
    for m in TOC_RE.finditer(html):
        for href in A_RE.findall(m.group(1)):
            if href.startswith("#"):
                out.add(href[1:])
    return out


def sections_needing_toc(html: str) -> list:
    """الأقسام المرئية التي تحمل عنوانًا — يجب أن تظهر في الفهرس."""
    out = []
    for m in SEC_RE.finditer(html):
        seg = html[m.end():m.end() + 4000]
        h = H2_RE.search(seg)
        if not h:
            continue
        title = re.sub(r"<[^>]+>", "", h.group(1)).strip()
        if title:
            out.append((m.group(1), title))
    return out


def check_page(path: Path, dist: Path) -> list:
    html = path.read_text(encoding="utf-8")
    clean = text_only(html)
    ids = ids_of(html)
    problems = []
    rel = path.relative_to(dist)

    for href in A_RE.findall(clean):
        h = href.strip()
        if not h or h in ("#",) or h.startswith(SKIP_PREFIX):
            if h in ("#", ""):
                problems.append(f"{rel}: رابط فارغ href=\"{h}\"")
            continue
        if h.lower().startswith("http://"):
            problems.append(f"{rel}: رابط غير مشفّر {h[:60]}")
            continue
        if h.startswith("#"):
            if h[1:] not in ids:
                problems.append(f"{rel}: مرساة مكسورة {h} (لا عنصر بهذا المعرّف)")
            continue
        if h.startswith("/") or h.startswith("./") or h.startswith("../"):
            target, _, frag = h.partition("#")
            if not frag:
                continue
            if target.startswith("/"):
                cand = dist / target.lstrip("/")
            else:
                cand = (path.parent / target).resolve()
            cands = [cand] if cand.suffix else [cand / "index.html", cand.with_suffix(".html")]
            found = next((c for c in cands if c.is_file()), None)
            if found is None:
                problems.append(f"{rel}: مرساة إلى صفحة غير موجودة {h[:70]}")
            elif frag and frag not in ids_of(found.read_text(encoding="utf-8")):
                problems.append(f"{rel}: مرساة {h[:70]} لا تقابل معرّفًا في الصفحة الهدف")

    toc = toc_targets(html)
    if toc:
        for sid, title in sections_needing_toc(html):
            if sid not in toc:
                problems.append(f"{rel}: قسم «{title}» ({sid}) خارج فهرس المحتويات")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس روابط الموقع وفهرس المحتويات")
    ap.add_argument("--site", default=DEF_SITE, help="جذر الموقع (يحتوي dist)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    dist = Path(a.site).expanduser().resolve() / "dist"
    if not dist.is_dir():
        print(f"✘ خطأ بيئة: مخرج الموقع غير موجود: {dist}", file=sys.stderr)
        return 3
    files = pages(dist)
    if not files:
        print(f"✘ خطأ بيئة: لا صفحات HTML في {dist}", file=sys.stderr)
        return 3

    problems = []
    for p in files:
        problems += check_page(p, dist)

    if problems:
        print(f"✘ مخالفات: {len(problems)}", file=sys.stderr)
        for x in problems[:40]:
            print("  " + x, file=sys.stderr)
        if len(problems) > 40:
            print(f"  … و{len(problems) - 40} أخرى", file=sys.stderr)
        return 2
    if not a.quiet:
        print(f"✔ روابط سليمة وفهرس مطابق · صفحات مفحوصة: {len(files)}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
