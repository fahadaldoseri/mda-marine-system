#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس أسلوب الغائب — فشل مغلق.

قاعدة المشروع: الكتابة بأسلوب الغائب لا بصيغة المخاطبة. يقيس هذا الحارس المخرج
المبني (`$SITE_DIR/dist`) نصًّا ظاهرًا للقارئ، خارج كتل style/script.

مصدر معجم أفعال الأمر واحد: وحدة الموقع `generator/third_person.py` — تُستورد من
مسار الموقع نفسه، فلا تُكرَّر القائمة هنا ولا تتباعد النسختان.

رموز الخروج: 0 سليم · 2 مخالفة مانعة · 3 خطأ بيئة.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path

DEF_SITE = os.environ.get("SITE_DIR") or os.environ.get("SITE") or "/home/ubuntu/seawatch"

TAG_RE = re.compile(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>", re.S | re.I)


def load_unit(site: Path):
    """يستورد وحدة أسلوب الغائب من مشروع الموقع (مصدر واحد للحقيقة)."""
    p = site / "generator" / "third_person.py"
    if not p.is_file():
        return None
    spec = importlib.util.spec_from_file_location("site_third_person", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس أسلوب الغائب في مخرج الموقع")
    ap.add_argument("--site", default=DEF_SITE)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    site = Path(a.site).expanduser().resolve()
    dist = site / "dist"
    if not dist.is_dir():
        print(f"✘ خطأ بيئة: مخرج الموقع غير موجود: {dist}", file=sys.stderr)
        return 3
    unit = load_unit(site)
    if unit is None:
        print(f"✘ خطأ بيئة: وحدة third_person.py غير موجودة في {site}/generator", file=sys.stderr)
        return 3

    pages = sorted(p for p in dist.rglob("*.html") if p.is_file())
    if not pages:
        print(f"✘ خطأ بيئة: لا صفحات HTML في {dist}", file=sys.stderr)
        return 3

    hits = []
    for p in pages:
        html = TAG_RE.sub(" ", p.read_text(encoding="utf-8"))
        for verb in unit.violations(html):
            ctx = ""
            m = re.search(r".{0,50}" + re.escape(verb) + r".{0,50}", html)
            if m:
                ctx = re.sub(r"\s+", " ", m.group(0)).strip()
            hits.append((p.relative_to(dist), verb, ctx))

    if hits:
        print(f"✘ مخالفات أسلوب الغائب: {len(hits)}", file=sys.stderr)
        for rel, verb, ctx in hits[:30]:
            print(f"  {rel}: «{verb}» … {ctx[:90]}", file=sys.stderr)
        if len(hits) > 30:
            print(f"  … و{len(hits) - 30} أخرى", file=sys.stderr)
        return 2
    if not a.quiet:
        print(f"✔ أسلوب الغائب مطبَّق · صفحات مفحوصة: {len(pages)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())