#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس الأرقام المنشورة — يمنع تباعد الرقم عن ملفه المالك (ك-554).

القاعدة: كل رقم يُنشر على أي سطح (المتن · واجهة اليوم · العدّادات · الإضافات · المهارات)
له ملف مالك واحد معلن، ويُقارن به عند كل تشغيل. أي اختلاف = فشل مغلق (rc=2).

العلة التي أنشأت هذا الحارس: ظهر في جولة 2026-11-07 أن المتن ينشر 122 حادثًا في سجل
IMO بينما السجل المالك ينشر 128 (والرقم 122 هو اللقطة السابقة في حقل `previous`)، وأن
حقل التقادم في واجهة اليوم ينشر 0 بينما ملف حالة التغذيات ينشر 6، وأن بطاقة «روايات لم
تتأكد» تنشر 1 بينما عدّاد الدفتر ينشر 0. الأسباب الثلاثة واحدة: رقم مكتوب يدويًا في
سطح منشور بلا ربط بمالكه.

الاستخدام: python3 validators/check_published_counters.py [--brain DIR] [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[1]
DEFAULT_DATE = '2026-11-07'


def load_json(p: pathlib.Path):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:  # noqa: BLE001
        return None


def text(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding='utf-8')
    except Exception:  # noqa: BLE001
        return ''


# ────────────────────────────── الفحوص ──────────────────────────────

def check_imo_historical(brain: pathlib.Path, date: str, out: list, blockers: list) -> None:
    """لا يجوز أن ينشر أي سطح الرقم التاريخي المعلن في حقل previous."""
    owner = brain / 'appendices' / 'imo-incidents.json'
    d = load_json(owner)
    if not isinstance(d, dict):
        blockers.append(f'ملف مالك IMO غير مقروء: {owner}')
        return
    current = (d.get('totals') or {}).get('confirmed_incidents')
    prev = ((d.get('previous') or {}).get('totals') or {}).get('confirmed_incidents')
    if current is None or prev is None:
        blockers.append('سجل IMO لا يعلن الرقم الحالي والرقم السابق معًا')
        return
    out.append(('سجل IMO — الرقم الحالي', current, 'appendices/imo-incidents.json', 'تماسك المالك', 'معلن'))
    out.append(('سجل IMO — الرقم السابق', prev, 'appendices/imo-incidents.json', 'حقل previous', 'معلن'))

    report = brain / 'reports' / f'{date}-sectioned.md'
    lines = text(report).splitlines()
    offenders = [f'{i + 1}: {l.strip()[:90]}' for i, l in enumerate(lines)
                 if ('IMO' in l or 'المنظمة البحرية' in l) and str(prev) in l]
    if offenders:
        blockers.append('المتن ينشر الرقم التاريخي %s في سجل IMO: %s' % (prev, ' · '.join(offenders[:3])))
    else:
        out.append(('سجل IMO — المتن', prev, 'reports/%s-sectioned.md' % date, 'لا يظهر الرقم السابق', 'مطابق'))
    if not any('IMO' in l and str(current) in l for l in lines):
        blockers.append('المتن لا ينشر الرقم الحالي %s في أي سطر يذكر IMO' % current)
    else:
        out.append(('سجل IMO — المتن', current, 'reports/%s-sectioned.md' % date, 'الرقم الحالي منشور', 'مطابق'))


def check_stale(brain: pathlib.Path, date: str, out: list, blockers: list) -> None:
    """حقل التقادم في واجهة اليوم = عدد المتقادم في ملف حالة التغذيات."""
    meta = load_json(brain / 'web' / 'meta' / f'{date}.json')
    status = load_json(brain / 'feeds' / f'feeds-{date}.status.json')
    if not isinstance(meta, dict) or not isinstance(status, dict):
        blockers.append('ملف الواجهة أو ملف حالة التغذيات غير مقروء')
        return
    declared = (meta.get('source_reliability') or {}).get('stale')
    owner = len(status.get('stale') or [])
    ok = declared == owner
    out.append(('المصادر المتقادمة', declared, 'feeds/feeds-%s.status.json (%d)' % (date, owner),
                'واجهة اليوم source_reliability.stale', 'مطابق' if ok else 'مخالف'))
    if not ok:
        blockers.append('اختلاف ربط التقادم: الواجهة %s · حالة التغذيات %d' % (declared, owner))
    limit_declared = (meta.get('source_reliability') or {}).get('stale_days_limit')
    if limit_declared is not None and limit_declared != status.get('stale_days_limit'):
        blockers.append('اختلاف حد التقادم: الواجهة %s · حالة التغذيات %s'
                        % (limit_declared, status.get('stale_days_limit')))


def check_cards_vs_metrics(brain: pathlib.Path, date: str, out: list, blockers: list) -> None:
    """كل بطاقة في واجهة اليوم تساوي عدّادها في ملف العدّادات إن حملت المعرّف نفسه."""
    meta = load_json(brain / 'web' / 'meta' / f'{date}.json')
    kpis = load_json(brain / 'web' / 'kpis-totals' / f'{date}.json')
    if not isinstance(meta, dict) or not isinstance(kpis, dict):
        blockers.append('ملف الواجهة أو ملف العدّادات غير مقروء')
        return
    metrics = {m.get('id'): m for m in kpis.get('metrics', []) if isinstance(m, dict)}
    compared = 0
    for card in meta.get('hero_kpis') or []:
        if not isinstance(card, dict):
            continue
        cid = card.get('id')
        m = metrics.get(cid)
        if not m or 'today' not in m or 'value' not in card:
            continue
        compared += 1
        pub, own = str(card.get('value')).strip(), str(m.get('today')).strip()
        ok = pub == own
        out.append((f'بطاقة {cid}', pub, 'web/kpis-totals/%s.json (%s)' % (date, own),
                    'واجهة اليوم hero_kpis', 'مطابق' if ok else 'مخالف'))
        if not ok:
            blockers.append('اختلاف ربط البطاقة %s: الواجهة %s · العدّاد %s' % (cid, pub, own))
    if compared == 0:
        blockers.append('لا بطاقة واحدة قابلة للمقارنة بعدّادها — الربط لا يعمل')


def check_sources_count(brain: pathlib.Path, date: str, out: list, blockers: list) -> None:
    """عدد المصادر المعتمد واحد: السجل المالك · واجهة اليوم · INDEX."""
    reg = load_json(brain / 'appendices' / 'source-reliability-40.json')
    n = len(reg) if isinstance(reg, list) else len((reg or {}).get('sources', []))
    if n == 0:
        blockers.append('سجل المصادر المالك فارغ أو غير مقروء')
        return
    meta = load_json(brain / 'web' / 'meta' / f'{date}.json') or {}
    approved = meta.get('sources_approved')
    ok = approved == n
    out.append(('المصادر المعتمدة', approved, 'appendices/source-reliability-40.json (%d)' % n,
                'واجهة اليوم sources_approved', 'مطابق' if ok else 'مخالف'))
    if not ok:
        blockers.append('اختلاف ربط عدد المصادر: الواجهة %s · السجل %d' % (approved, n))
    idx = text(brain / 'INDEX.md')
    legacy = re.findall(r'\*\*\d+\s*مصدرًا\*\*', idx)
    if legacy and not any(str(n) in x for x in legacy):
        blockers.append('INDEX يعلن عددًا معتمدًا مخالفًا للسجل: %s' % ' · '.join(sorted(set(legacy))))
    else:
        out.append(('عدد المصادر في INDEX', n, 'INDEX.md', 'لا إعلان مخالف', 'مطابق'))

    scan = ['INDEX.md', 'sections/10-sources.md', 'sections/90-automation.md',
            'appendices/source-reliability-40.md']
    claims = []
    for rel in scan:
        for i, line in enumerate(text(brain / rel).splitlines(), 1):
            if re.search(r'(37|40|62)[^\n]{0,25}مصدر|مصدر[^\n]{0,25}(37|40|62)', line) \
                    and '**' in line and str(n) not in line:
                claims.append(f'{rel}:{i}')
    if claims:
        blockers.append('إعلان غليظ بعدد مصادر مخالف للسجل %d في: %s' % (n, ' · '.join(claims[:4])))
    else:
        out.append(('إعلانات عدد المصادر', n, 'الملفات الحاكمة للمصادر', 'لا إعلان غليظ مخالف', 'مطابق'))


def check_zones(brain: pathlib.Path, date: str, out: list, blockers: list) -> None:
    """عدد القطاعات في واجهة اليوم = عدد القطاعات في السجل المعتمد."""
    reg = load_json(brain / 'appendices' / 'zone-registry.json') or {}
    zones = reg.get('zones') or []
    meta = load_json(brain / 'web' / 'meta' / f'{date}.json') or {}
    levels = meta.get('threat_zone_levels') or {}
    ok = len(zones) == len(levels)
    out.append(('عدد القطاعات', len(levels), 'appendices/zone-registry.json (%d)' % len(zones),
                'واجهة اليوم threat_zone_levels', 'مطابق' if ok else 'مخالف'))
    if not ok:
        blockers.append('اختلاف عدد القطاعات: الواجهة %d · السجل %d' % (len(levels), len(zones)))


def check_probability(brain: pathlib.Path, date: str, out: list, blockers: list) -> None:
    """النسب النقطية تُشتق من النطاقات وتُسوّى إلى 100، وتظهر على سطح المتن."""
    meta = load_json(brain / 'web' / 'meta' / f'{date}.json') or {}
    hyps = [h for h in (meta.get('hypotheses') or []) if isinstance(h, dict)]
    if not hyps:
        blockers.append('لا فرضيات في واجهة اليوم لفحص النسب')
        return
    shares = []
    for h in hyps:
        m = re.match(r'(\d+)', str(h.get('likelihood') or ''))
        shares.append(int(m.group(1)) if m else None)
    if any(s is None for s in shares):
        blockers.append('نسبة فرضية غير قابلة للقراءة: %s' % shares)
        return
    total = sum(shares)
    out.append(('مجموع النسب المشتقة', total, 'web/meta/%s.json' % date, 'قاعدة التسوية إلى 100',
                'مطابق' if total == 100 else 'مخالف'))
    if total != 100:
        blockers.append('مجموع النسب المشتقة %d وليس 100' % total)
    report = text(brain / 'reports' / f'{date}-sectioned.md')
    rows = {m.group(1): m.group(0) for m in re.finditer(r'^\|\s*(EST-[^\s|]+)[^\n]*$', report, re.M)}
    missing = [f'{h.get("est")}={s}%' for h, s in zip(hyps, shares)
               if f'{s}%' not in rows.get(str(h.get('est')), '')]
    if missing:
        blockers.append('المتن لا ينشر النسبة المشتقة لهذه الفرضيات: %s' % ' · '.join(missing))
    else:
        out.append(('النسب على سطح المتن', len(shares), 'reports/%s-sectioned.md' % date,
                    'كل نسبة مشتقة ظاهرة', 'مطابق'))


def check_delivery_policy(brain: pathlib.Path, date: str, out: list, blockers: list) -> None:
    """خطوات التسليم المعلنة = خطوات طور التسليم في المانيفست، لا مجموعة جزئية."""
    policy = load_json(brain / 'runbook' / 'delivery-policy.json') or {}
    manifest = load_json(brain / 'runbook' / 'runbook.json') or {}
    declared = policy.get('manifest_delivery_steps') or []
    steps = manifest.get('steps') or []
    deliver = [s.get('id') for s in steps if str(s.get('phase', '')).lower().startswith('deliver')]
    missing = [s for s in deliver if s not in declared]
    extra = [s for s in declared if s not in deliver]
    ok = not missing and not extra
    out.append(('خطوات التسليم', len(declared), 'runbook/runbook.json (%d)' % len(deliver),
                'runbook/delivery-policy.json', 'مطابق' if ok else 'مخالف'))
    if missing:
        blockers.append('السياسة لا تعلن خطوات تسليم موجودة في المانيفست: %s' % ' · '.join(missing))
    if extra:
        blockers.append('السياسة تعلن خطوات ليست في طور التسليم: %s' % ' · '.join(extra))


def check_ofac(brain: pathlib.Path, date: str, out: list, blockers: list) -> None:
    """قائمة OFAC لا تحمل إلا أسماء سفن: لا آثار صفحات ولا عناوين تحديث."""
    p = brain / 'watchlist' / 'ofac-targets.txt'
    t = text(p)
    if not t:
        blockers.append('قائمة OFAC غير مقروءة: %s' % p)
        return
    junk = [l.strip() for l in t.splitlines()
            if l.strip() and re.search(r'UPDATE-\d+|ISNA|HTTP\s*\d{3}|<html|attention required', l, re.I)]
    entries = [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith('#')]
    ok = not junk
    out.append(('قائمة OFAC', len(entries), 'watchlist/ofac-targets.txt', 'عناصر غير سفن',
                'مطابق' if ok else 'مخالف'))
    if junk:
        blockers.append('قائمة OFAC تحمل عناصر ليست أسماء سفن: %s' % ' · '.join(junk[:5]))


CHECKS = (
    check_imo_historical, check_stale, check_cards_vs_metrics, check_sources_count,
    check_zones, check_probability, check_delivery_policy, check_ofac,
)


def collect(brain: pathlib.Path, date: str):
    out: list = []
    blockers: list = []
    for fn in CHECKS:
        try:
            fn(brain, date, out, blockers)
        except Exception as exc:  # noqa: BLE001
            blockers.append('فشل تنفيذ الفحص %s: %s: %s' % (fn.__name__, type(exc).__name__, exc))
    return out, blockers


def main() -> int:
    ap = argparse.ArgumentParser(description='حارس الأرقام المنشورة (فشل مغلق)')
    ap.add_argument('--brain', default=str(ROOT))
    ap.add_argument('--date', default=DEFAULT_DATE)
    args = ap.parse_args()
    out, blockers = collect(pathlib.Path(args.brain), args.date)
    print('   حارس الأرقام المنشورة — %s' % args.date)
    for name, published, owner, surface, verdict in out:
        print('   %-26s المنشور=%-6s المالك=%-42s السطح=%-28s %s'
              % (name, published, owner, surface, verdict))
    if blockers:
        print('   ✘ موانع: %d' % len(blockers))
        for b in blockers:
            print('      - %s' % b)
        return 2
    print('   ✔ كل رقم منشور مطابق لمالكه (%d ربطًا)' % len(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())