#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس عقد النشر — فشل مغلق.

القاعدة: النشر لا يُنفَّذ إلا من خطوة معلنة في المانيفست الحاكم. الحارس يمنع
عودة أدوات نشر معزولة (سكربت دفع/نشر مكتوب خارج المانيفست) لأنها السبب الجذري
لتكرار عطل «ما بعد النشر».

المنهج:
  1) يُقرأ المانيفست `runbook/runbook.json` وتُجمع كل مسارات الأدوات المذكورة في
     أوامر خطواته (أي ملف يُستدعى من خطوة معلنة = مسار نشر مشروع).
  2) تُمسح ملفات الأدوات في الموقع والدماغ بحثًا عن أوامر نشر فعلية.
  3) كل ملف فيه أمر نشر يجب أن يكون: مذكورًا في المانيفست، أو في قائمة السماح
     الصريحة أدناه (أدوات القناة المعتمدة)، أو ملف اختبار/حارس (لا ينشر).

رموز الخروج: 0 سليم · 2 مخالفة مانعة · 3 خطأ بيئة.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from pathlib import Path

_BRAIN = pathlib.Path(__file__).resolve().parents[1]
DEF_BRAIN = os.environ.get("BRAIN_DIR") or str(_BRAIN)
DEF_SITE = (os.environ.get("SITE_DIR") or os.environ.get("SITE")
            or str(_BRAIN.parent / "seawatch"))

# أنماط أوامر النشر الفعلية (لا ذِكرًا في نص أو تعليق)
PUBLISH_PATTERNS = (
    r"git\s+push\b",
    r"wrangler\s+pages\s+deploy\b",
    r"gh\s+workflow\s+run\b",
    r"api\.cloudflare\.com",
    r"manus\s+deploy\b",
    r"publish_channels\.py",
)

# أدوات قناة النشر المعتمدة (معلنة في المانيفست، ويُسمح بذكرها هنا احتياطًا)
ALLOWED = {
    "brain/tools/publish_channels.py",
    "brain/tools/check_live.sh",
    "brain/tools/github_backup.py",
    "brain/tools/telegram_send.py",
    "brain/tools/rotate_webhook_secret.py",
    "brain/tools/build_and_push.sh",
}

SKIP_NAME = re.compile(r"(^test_|_test\.|/tests?/|check_|validate_)")


def manifest_refs(brain: Path) -> set:
    p = brain / "runbook" / "runbook.json"
    if not p.is_file():
        return set()
    raw = p.read_text(encoding="utf-8")
    refs = set()
    for m in re.finditer(r"([A-Za-z0-9_./-]+\.(?:py|sh))", raw):
        refs.add(m.group(1))
        refs.add(Path(m.group(1)).name)
    return refs


def scan(path: Path, root: Path) -> list:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        for pat in PUBLISH_PATTERNS:
            if re.search(pat, line):
                out.append((i, pat, stripped[:110]))
                break
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس عقد النشر")
    ap.add_argument("--brain", default=DEF_BRAIN)
    ap.add_argument("--site", default=DEF_SITE)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    brain = Path(a.brain).expanduser().resolve()
    site = Path(a.site).expanduser().resolve()
    if not (brain / "runbook" / "runbook.json").is_file():
        print(f"✘ خطأ بيئة: المانيفست غير موجود في {brain}", file=sys.stderr)
        return 3

    refs = manifest_refs(brain)
    roots = [(brain, "brain"), (site, "site")]
    violations = []
    scanned = 0
    for root, label in roots:
        for sub in ("tools", "generator"):
            d = root / sub
            if not d.is_dir():
                continue
            for f in sorted(d.rglob("*")):
                if not f.is_file() or f.suffix not in (".py", ".sh"):
                    continue
                rel = f"{label}/{f.relative_to(root)}"
                if SKIP_NAME.search(rel) or rel in ALLOWED or f.name in refs:
                    continue
                scanned += 1
                for line_no, pat, text in scan(f, root):
                    violations.append(f"{rel}:{line_no} [{pat}] {text}")

    if violations:
        print(f"✘ أدوات نشر خارج المانيفست: {len(violations)}", file=sys.stderr)
        for v in violations[:25]:
            print("  " + v, file=sys.stderr)
        return 2
    if not a.quiet:
        print(f"✔ عقد النشر سليم · ملفات مفحوصة: {scanned} · مراجع المانيفست: {len(refs)}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
