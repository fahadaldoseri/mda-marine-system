#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة عدد المصادر: رقم واحد معتمد يقرأه كل شيء من ملف واحد.

بند 8 من التدقيق المستقل (19 أكتوبر 2026): الموقع كان يكتب 37 ثابتة، والملاحق وفحص
ما قبل التشغيل تقول 40 — فرق في رقم الشيء نفسه داخل المنتج الواحد.

رموز الخروج: 0 = لا مخالفة مانعة (قد تُطبع تنبيهات وصفية) · 2 = مخالفة مانعة
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
HISTORICAL_EXEMPTIONS = B / 'appendices' / 'source-count-historical-exemptions.json'
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

# ك-453: المانيفست التشغيلي والكتيب المولَّد منه كانا **خارج** نطاق هذه البوابة،
# فبقي فيهما «فحص التغذيات (40 مصدرًا)» سنوات العدد المعتمد 62. القاعدة الجديدة:
# لا رقم ثابت للمصادر في المانيفست أو الكتيب — لا «40» ولا «62» — لأن الرقم الثابت
# في ملف تشغيلي عطلُ انحراف مؤجل. المصدر الواحد هو `appendices/sources-manifest.json`.
NO_STATIC_COUNT = [
    B / 'runbook' / 'runbook.json',
    B / 'docs' / 'runbook.md',
]

_AR_D = str.maketrans("0123456789", "0123456789")
COUNT_RE = re.compile(r"([0-90-9]{2,3})\s*مصدر(?:ًا|اً|ا)?")
# أرقام مكتوبة بالكلمات (كانت تمرّ من البوابة: «السبعة والثلاثون» بدل 40) — عطل ك-08
_W_ONES = {"السبعة": 7, "سبعة": 7, "الثمانية": 8, "ثمانية": 8, "التسعة": 9, "تسعة": 9}
_W_TENS = {"الثلاثون": 30, "ثلاثون": 30, "الأربعون": 40, "أربعون": 40, "الخمسون": 50, "خمسون": 50}
WORD_RE = re.compile(
    "(" + "|".join(_W_ONES) + r")\s+و(?:ال)?(" + "|".join(k.lstrip("ال") for k in _W_TENS) + ")")
WORD_TENS_RE = re.compile("(?:ال)?(" + "|".join(k.lstrip("ال") for k in _W_TENS) + r")\s+(?:مصدرًا|مصدرا|مصدر|المصادر)")


def load_historical_exemptions() -> list[dict]:
    """يقرأ قائمة الاستثناءات المعللة؛ فسادها لا يفتح باب تجاوز صامت."""
    data = json.loads(HISTORICAL_EXEMPTIONS.read_text(encoding='utf-8'))
    entries = data.get('entries') if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise ValueError('قائمة الاستثناءات لا تحتوي entries')
    return [entry for entry in entries if isinstance(entry, dict)]


def historical_exemption(path: Path, line_no: int, number: int, line_text: str,
                         full_text: str, entries: list[dict]) -> str | None:
    """لا يتجاوز إلا موضعًا مطابقًا نصًا وعددًا وله علامة تاريخية داخل الملف."""
    try:
        relative = path.relative_to(B).as_posix()
    except ValueError:
        return None
    for entry in entries:
        if entry.get('path') != relative:
            continue
        if int(entry.get('line', -1)) != line_no or int(entry.get('number', -1)) != number:
            continue
        needle = str(entry.get('line_contains') or '')
        marker = str(entry.get('historical_marker') or '')
        if needle and needle not in line_text:
            continue
        if marker and marker not in full_text:
            continue
        return str(entry.get('reason') or 'استثناء تاريخي موثق')
    return None


def count_mentions(path: Path, approved: int) -> list[tuple[str, int, int, str]]:
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    bad = []

    lines = text.splitlines()

    def add_bad(display: str, number: int, start: int) -> None:
        line_no = text[:start].count('\n') + 1
        line_text = lines[line_no - 1] if 0 < line_no <= len(lines) else ''
        bad.append((display, number, line_no, line_text))

    for m in COUNT_RE.finditer(text):
        n = int(m.group(1).translate(_AR_D))
        if n == approved or n == 0:
            continue
        line = text[:m.start()].count('\n') + 1
        add_bad(f"{path}:{line} ← {n} مصدرًا", n, m.start())
    # أرقام مكتوبة بالكلمات: «السبعة والثلاثون» = 37
    for m in WORD_RE.finditer(text):
        n = _W_ONES[m.group(1)] + _W_TENS.get("ال" + m.group(2), _W_TENS.get(m.group(2), 0))
        if n == approved or n == 0:
            continue
        line = text[:m.start()].count('\n') + 1
        add_bad(f"{path}:{line} ← «{m.group(0)}» = {n} مصدرًا", n, m.start())
    for m in WORD_TENS_RE.finditer(text):
        n = _W_TENS.get("ال" + m.group(1), _W_TENS.get(m.group(1), 0))
        if n == approved or n == 0:
            continue
        line = text[:m.start()].count('\n') + 1
        add_bad(f"{path}:{line} ← «{m.group(0)}» = {n} مصدرًا", n, m.start())
    return bad


def channel_identity(_approved: int) -> list[str]:
    """كل مصدر معتمد له قناة واحدة ومجموعها = المعتمد (ك-212)."""
    bad: list[str] = []
    try:
        import sys as _sys
        _sys.path.insert(0, str(BRAIN / "tools"))
        import source_channels as _sc  # noqa: WPS433
        total, approved, gap, dup = _sc.identity()
        if gap:
            bad.append(f"مصادر معتمدة بلا قناة (تسقط من العدّاد): {gap}")
        if dup:
            bad.append(f"مصادر في أكثر من قناة: {dup}")
        if total != approved:
            bad.append(f"مجموع القنوات {total} لا يساوي المعتمد {approved}")
    except (ImportError, AttributeError, OSError, ValueError, KeyError, TypeError, RuntimeError) as e:  # مُقيّد: لا يبتلع الخطأ، يُعلن التعذّر مانعًا
        bad.append(f"تعذّر تحميل خريطة القنوات: {type(e).__name__}: {e}")
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
    blockers.extend(channel_identity(approved))  # ك-212: لا مصدر معتمد بلا قناة
    warnings: list[str] = []
    historical_skips: list[str] = []
    try:
        historical_entries = load_historical_exemptions()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
        blockers.append(f"قائمة الاستثناءات التاريخية غير صالحة: {e}")
        historical_entries = []

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
        for item, _, _, _ in count_mentions(p, approved):
            blockers.append(item)
    # ك-453: أي رقم للمصادر في المانيفست أو الكتيب مانع — ولو طابق المعتمد اليوم.
    for p in NO_STATIC_COUNT:
        if not p.exists():
            continue
        for item, number, line_no, _ in count_mentions(p, -1):
            blockers.append(
                f"رقم ثابت للمصادر في ملف تشغيلي (يُنزع الرقم، والعدد يُقرأ من "
                f"{MANIFEST.name}): {item} [سطر {line_no} · العدد المكتوب {number}]")
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
            try:
                full_text = f.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                full_text = ''
            for item, number, line_no, line_text in count_mentions(f, approved):
                reason = historical_exemption(f, line_no, number, line_text,
                                              full_text, historical_entries)
                if reason:
                    historical_skips.append(f"{item} — {reason}")
                else:
                    warnings.append(item)

    for item in historical_skips:
        print(f"   ↷ تجاهل تاريخي معلل: {item}")
    for w in warnings:
        print(f"   ◐ تنبيه (سياق وصفي): {w}")
    for b in blockers:
        print(f"   ✘ مخالفة مانعة: {b}")
    if blockers:
        print(f"  النتيجة: مانع — {len(blockers)} موضعًا يخالف الرقم المعتمد {approved}")
        return 2
    if warnings:
        print(f"  النتيجة: مطابق في الملفات الملزمة · {len(warnings)} تنبيهًا وصفيًا")
        return 0
    print("  النتيجة: مطابق — رقم واحد في كل الملفات الملزمة")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
