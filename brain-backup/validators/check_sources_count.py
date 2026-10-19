#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة عدد المصادر: رقم واحد معتمد يقرأه كل شيء من ملف واحد.

بند ٨ من التدقيق المستقل (19 أكتوبر 2026): الموقع كان يكتب 37 ثابتة، والملاحق وفحص
ما قبل التشغيل تقول 40 — فرق في رقم الشيء نفسه داخل المنتج الواحد.

رموز الخروج: 0 = مطابق · 1 = مخالفة غير مانعة في ملف وصفي · 2 = مخالفة مانعة
الاستخدام: python3 validators/check_sources_count.py
"""
from __future__ import annotations
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")

import json
import re
import sys
from pathlib import Path

B = Path(f'{BRAIN}')
MANIFEST = B / 'appendices' / 'sources-manifest.json'
SITE_GEN = Path(f'{SITE}/generator')

# ملفات يجب أن تطابق الرقم المعتمد (مانع)
MANDATORY = [
    B / 'sections' / '10-sources.md',
    B / 'sections' / '30-structure.md',
    B / 'sections' / '60-validation.md',
    B / 'sections' / '90-automation.md',
    SITE_GEN / 'build_site.py',
    SITE_GEN / 'build_report.py',
]
# ملفات يُنبَّه عليها فقط (سياق تاريخي أو نقل حرفي)
ADVISORY = [
    B / 'appendices',
    B / 'docs',
    B / 'notes',
]

COUNT_RE = re.compile(r'(\d{2,3})\s*مصدر(?:ًا|اً|ا)?')


def count_mentions(path: Path, approved: int) -> list[tuple[str, int]]:
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    bad = []
    for m in COUNT_RE.finditer(text):
        n = int(m.group(1))
        if n == approved or n == 0:
            continue
        line = text[:m.start()].count('\n') + 1
        bad.append((f"{path}:{line} ← {n} مصدرًا", n))
    return bad


def main() -> int:
    if not MANIFEST.exists():
        print(f"  ✘ ملف المصدر الواحد مفقود: {MANIFEST}")
        return 2
    try:
        approved = int(json.loads(MANIFEST.read_text(encoding='utf-8'))['approved_source_count'])
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"  ✘ ملف المصدر الواحد غير صالح ({e})")
        return 2

    print(f"=== بوابة عدد المصادر — المعتمد: {approved} ===")
    blockers: list[str] = []
    warnings: list[str] = []
    for p in MANDATORY:
        if not p.exists():
            continue
        for item, _ in count_mentions(p, approved):
            blockers.append(item)
    for p in ADVISORY:
        if not p.exists():
            continue
        files = [p] if p.is_file() else sorted(p.rglob('*.md')) + sorted(p.rglob('*.json'))
        for f in files:
            for item, _ in count_mentions(f, approved):
                warnings.append(item)

    for w in warnings:
        print(f"   ◐ تنبيه (سياق وصفي): {w}")
    for b in blockers:
        print(f"   ✘ مخالفة مانعة: {b}")
    if blockers:
        print(f"  النتيجة: مانع — {len(blockers)} موضعًا يخالف الرقم المعتمد {approved}")
        return 2
    if warnings:
        print(f"  النتيجة: مطابق في الملفات الملزمة · {len(warnings)} تنبيهًا وصفيًا")
        return 1
    print("  النتيجة: مطابق — رقم واحد في كل الملفات الملزمة")
    return 0


if __name__ == '__main__':
    sys.exit(main())