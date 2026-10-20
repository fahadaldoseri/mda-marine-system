#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة عدد المصادر: رقم واحد معتمد يقرأه كل شيء من ملف واحد.

بند 8 من التدقيق المستقل (19 أكتوبر 2026): الموقع كان يكتب 37 ثابتة، والملاحق وفحص
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

_AR_D = str.maketrans("0123456789", "0123456789")
COUNT_RE = re.compile(r"([0-90-9]{2,3})\s*مصدر(?:ًا|اً|ا)?")
# أرقام مكتوبة بالكلمات (كانت تمرّ من البوابة: «السبعة والثلاثون» بدل 40) — عطل ك-08
_W_ONES = {"السبعة": 7, "سبعة": 7, "الثمانية": 8, "ثمانية": 8, "التسعة": 9, "تسعة": 9}
_W_TENS = {"الثلاثون": 30, "ثلاثون": 30, "الأربعون": 40, "أربعون": 40, "الخمسون": 50, "خمسون": 50}
WORD_RE = re.compile(
    "(" + "|".join(_W_ONES) + r")\s+و(?:ال)?(" + "|".join(k.lstrip("ال") for k in _W_TENS) + ")")
WORD_TENS_RE = re.compile("(?:ال)?(" + "|".join(k.lstrip("ال") for k in _W_TENS) + r")\s+(?:مصدرًا|مصدرا|مصدر|المصادر)")


def count_mentions(path: Path, approved: int) -> list[tuple[str, int]]:
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    bad = []
    for m in COUNT_RE.finditer(text):
        n = int(m.group(1).translate(_AR_D))
        if n == approved or n == 0:
            continue
        line = text[:m.start()].count('\n') + 1
        bad.append((f"{path}:{line} ← {n} مصدرًا", n))
    # أرقام مكتوبة بالكلمات: «السبعة والثلاثون» = 37
    for m in WORD_RE.finditer(text):
        n = _W_ONES[m.group(1)] + _W_TENS.get("ال" + m.group(2), _W_TENS.get(m.group(2), 0))
        if n == approved or n == 0:
            continue
        line = text[:m.start()].count('\n') + 1
        bad.append((f"{path}:{line} ← «{m.group(0)}» = {n} مصدرًا", n))
    for m in WORD_TENS_RE.finditer(text):
        n = _W_TENS.get("ال" + m.group(1), _W_TENS.get(m.group(1), 0))
        if n == approved or n == 0:
            continue
        line = text[:m.start()].count('\n') + 1
        bad.append((f"{path}:{line} ← «{m.group(0)}» = {n} مصدرًا", n))
    return bad


def main() -> int:
    if not MANIFEST.exists():
        print(f"  ✘ ملف المصدر الواحد مفقود: {MANIFEST}")
        return 2
    try:
        _man = json.loads(MANIFEST.read_text(encoding='utf-8'))
        approved = int(_man['approved_source_count'])
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"  ✘ ملف المصدر الواحد غير صالح ({e})")
        return 2

    print(f"=== بوابة عدد المصادر — المعتمد: {approved} ===")
    blockers: list[str] = []
    warnings: list[str] = []

    # (أ) ملف القائمة المشار إليه في البيان يجب أن يكون موجودًا — عطل ك-08 (مرجع ميت)
    _slf = _man.get('source_list_file')
    if _slf and not (B / _slf).exists():
        blockers.append(f"ملف قائمة المصادر المشار إليه في البيان مفقود: {_slf}")
    # (ب) إن كانت القائمة ملف JSON بسجلات، فعددها يجب أن يطابق الرقم المعتمد
    _slj = _man.get('source_list_json')
    if _slj and (B / _slj).exists():
        try:
            _recs = json.loads((B / _slj).read_text(encoding='utf-8'))
            if isinstance(_recs, list) and len(_recs) != approved:
                blockers.append(f"عدد سجلات {_slj} = {len(_recs)} بينما المعتمد {approved}")
        except (json.JSONDecodeError, OSError):
            warnings.append(f"تعذّرت قراءة قائمة المصادر {_slj}")
    for p in MANDATORY:
        if not p.exists():
            continue
        for item, _ in count_mentions(p, approved):
            blockers.append(item)
    for p in ADVISORY:
        if not p.exists():
            continue
        files = [p] if p.is_file() else sorted(p.rglob('*.md')) + sorted(p.rglob('*.json'))
        # عطل ك-67: تقرير استشاري تاريخي يذكر «21 مصدرًا» بأنذر كتعارض في عدد المصادر المعتمد.
        # الوثائق الاستشارية المرتبطة ليست ملفات سياسة — تُستثنى من مسح العدد.
        _adv = ('ach-hormuz-targeting', 'ach-', 'special-', 'raw-notes')
        for f in files:
            if any(a in f.name for a in _adv):
                continue
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