#!/usr/bin/env python3
"""بوابة قابلية النقل — فشل مغلق.

تمنع عودة المسار المطلق `/home/ubuntu/brain-marine-news` أو `/home/ubuntu/seawatch`
إلى أي ملف تنفيذي (.py / .sh) في النظام أو الموقع.

القاعدة المعتمدة (19 أكتوبر 2026): كل مسار جذر يُستنتج من موقع الملف
(`Path(__file__).resolve().parents[N]`) مع تجاوز بمتغيّر البيئة BRAIN_DIR / SITE_DIR.
التفاصيل: SETUP.md · docs/الاستقلال-عن-مانوس.md

رموز الخروج: 0 نجاح · 2 مخالفة مانعة.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

BRAIN = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
SITE = Path(os.environ.get("SITE_DIR") or BRAIN.parent / "seawatch")

LITERALS = (BRAIN.as_posix(), SITE.as_posix(), "/home/ubuntu/brain-marine-news", "/home/ubuntu/seawatch")
SKIP_PARTS = {"brain-backup", "__pycache__", "_oneoff", "legacy", "dist", "shots", "node_modules", ".git", "archive"}
# ملفات مسموح لها حمل النص الحرفي: أداة الكشف نفسها
ALLOW = {"portable_paths.py", "check_portable_paths.py"}
# سطر يحمل النص الحرفي بوصفه توثيقًا لا شيفرة
ALLOW_LINE_MARKERS = ("الافتراضي عند", "المصادر:", "مثال:", "usage:", "Usage:", "مقصود")

PAT = re.compile("|".join(re.escape(x) for x in LITERALS))


def scan() -> list[str]:
    hits: list[str] = []
    for root in (BRAIN, SITE):
        for p in root.rglob("*"):
            if p.suffix not in (".py", ".sh") or not p.is_file():
                continue
            if any(part in SKIP_PARTS for part in p.relative_to(root).parts):
                continue
            if p.name in ALLOW:
                continue
            try:
                lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                if PAT.search(line) is None:
                    continue
                s = line.lstrip()
                if s.startswith("#") or any(m in line for m in ALLOW_LINE_MARKERS):
                    continue
                hits.append(f"{p.relative_to(root.parent)}:{i}")
    return hits


def main() -> int:
    hits = scan()
    print("بوابة قابلية النقل — المسار المطلق في الشيفرة")
    print(f"  الجذور المفحوصة: {BRAIN} · {SITE}")
    if not hits:
        print("  ✔ لا مسار مطلق في أي ملف تنفيذي — النظام يعمل من أي مسار.")
        return 0
    print(f"  ✘ مخالفة مانعة: {len(hits)} موضعًا يحمل مسارًا مطلقًا:")
    for h in hits[:25]:
        print("   ·", h)
    if len(hits) > 25:
        print(f"   … و{len(hits) - 25} موضعًا آخر")
    print("  العلاج: استخدم BRAIN / SITE من الترويسة، أو مرّر BRAIN_DIR / SITE_DIR.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
