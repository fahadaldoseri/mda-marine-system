#!/usr/bin/env python3
"""إصلاح صياغة سطور الدفتر التراكمي (ك-301).

العطل: أسطر وقائع في مصدر السجل التراكمي تحمل:
  - وسمًا فارغًا `****` مكان الوصف (لا نص بين النجمات)،
  - ترقيمًا متجاورًا `؛ .`،
  - وتسمية مصدر عامة «المصدر الأول» بلا اسم جهة، بينما الرابط يحمل اسم النطاق.
النتيجة المقروءة سابقًا: «- **14 مايو | الموقع غير مفصل** — ****؛ . **الثقة:** عالية …».

الإصلاح لا يخترع معلومة: يحذف الوسم الفارغ، ويستبدل الترقيم المتجاور بفاصل واحد،
ويشتق اسم الجهة من نطاق الرابط (Reuters · UKMTO · …) مع إبقاء الرابط كما هو.
التشغيل:
  python3 tools/repair_ledger_prose.py --apply
  python3 tools/repair_ledger_prose.py --check
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = [
    ROOT / "historical" / "cumulative-baseline-2026-02-28-to-2026-10-11.md",
    ROOT / "cumulative-2026" / "التقرير-التراكمي-الواسع-28-فبراير-الى-11-أكتوبر-2026.md",
]
BACKUP_DIR = ROOT / "audit" / "backups"

DOMAIN_NAMES = {
    "reuters.com": "Reuters",
    "ukmto.org": "UKMTO",
    "gcaptain.com": "gCaptain",
    "splash247.com": "Splash247",
    "maritime-executive.com": "The Maritime Executive",
    "apnews.com": "AP",
    "aljazeera.com": "Al Jazeera",
    "x.com": "منصة X",
    "twitter.com": "منصة X",
}

EMPTY_BOLD = re.compile(r"\*\*\s*\*\*")
BROKEN_PUNCT = re.compile(r"؛\s*\.")
EM_DASH_DOT = re.compile(r"—\s*·\s*")
SOURCE_LINK = re.compile(r"\[([^\]]*)\]\((https?://[^)]+)\)")


def domain_name(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url)
    host = m.group(1).lower() if m else ""
    for dom, name in DOMAIN_NAMES.items():
        if host.endswith(dom):
            return name
    return host or "مصدر"


def fix_line(line: str) -> str:
    out = EMPTY_BOLD.sub("", line)
    out = BROKEN_PUNCT.sub("·", out)
    out = EM_DASH_DOT.sub("— ", out)
    out = re.sub(r"—\s*؛", "—", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"—\s*\.\s*", "— ", out)

    def repl(m: re.Match[str]) -> str:
        label, url = m.group(1), m.group(2)
        if label.strip() in {"المصدر الأول", "المصدر الثاني", "المصدر الثالث", ""}:
            return f"[{domain_name(url)}]({url})"
        return m.group(0)

    out = SOURCE_LINK.sub(repl, out)
    return out.rstrip()


def process(apply: bool) -> int:
    changed_files = 0
    changed_lines = 0
    for path in TARGETS:
        if not path.is_file():
            print(f"   … تخطٍّ: {path.relative_to(ROOT)} غير موجود")
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        new_lines: list[str] = []
        local = 0
        for line in lines:
            fixed = fix_line(line)
            if fixed != line:
                local += 1
            new_lines.append(fixed)
        if local == 0:
            print(f"   ✓ نظيف: {path.relative_to(ROOT)}")
            continue
        changed_files += 1
        changed_lines += local
        if apply:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            shutil.copy2(path, BACKUP_DIR / f"{path.name}.bak-{stamp}")
            path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print(f"   أُصلح: {path.relative_to(ROOT)} · أسطر={local}")
        else:
            print(f"   ✘ يحتاج إصلاحًا: {path.relative_to(ROOT)} · أسطر={local}")
    if not apply:
        return 1 if changed_files else 0
    print(f"   المجموع: ملفات={changed_files} · أسطر={changed_lines}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="إصلاح صياغة سطور الدفتر التراكمي")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args()
    return process(args.apply)


if __name__ == "__main__":
    sys.exit(main())