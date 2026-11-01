#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة طبقات بطاقات المؤشرات: اليوم · المجموع من 28 فبراير 2026 · آخر تحديث المصدر.

تفشل مغلقًا إذا:
  - بطاقة معلنة في السجل بطبقات ولم تظهر طبقاتها في الصفحة المبنيّة (عربي/إنجليزي)،
  - أو اختلف رقم المجموع أو تاريخ آخر تحديث عن ملف المقاييس الحاكم web/kpis-totals/<date>.json،
  - أو كان دفتر الأحداث ناقص الأيام (days_covered != days_total).

المصدر الواحد: appendices/card_registry.json#hero_kpis + web/kpis-totals/<date>.json.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

LABELS = {
    'ar': {'cumulative': 'المجموع من 28 فبراير 2026', 'updated': 'آخر تحديث'},
    'en': {'cumulative': 'Total since 28 February 2026', 'updated': 'Last updated'},
}
PAGES = {'ar': ('reports', '{date}.html'), 'en': ('reports/en', '{date}.html')}


def _load(path: pathlib.Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def _metric_by_id(metrics: dict, metric_id: str) -> dict | None:
    return next((metric for metric in (metrics.get('metrics') or [])
                 if isinstance(metric, dict) and metric.get('id') == metric_id), None)


def _card_block(html: str, card_id: str) -> str | None:
    i = html.find(f'data-kpi-id="{card_id}"')
    if i < 0:
        return None
    j = html.find('data-kpi-id="', i + 10)
    return html[i:j if j > 0 else i + 4000]


def _layer_value(block: str, lang: str, kind: str) -> str | None:
    """يقرأ قيمة الطبقة من طبقة الصفحة (k-lay) أو من طبقة الشاشة (sc-klay)."""
    label = re.escape(LABELS[lang][kind])
    for cls in ('k-lay-l', 'sc-klab'):
        m = re.search(rf'class="{cls}">{label}</span>\s*<b class="bidi">([^<]+)</b>', block)
        if m:
            return m.group(1).strip()
    return None


def check(date: str, dist_root: pathlib.Path, brain: pathlib.Path) -> list[str]:
    problems: list[str] = []
    registry = _load(brain / 'appendices/card_registry.json') or {}
    contract = (registry.get('hero_kpis') or {}).get('layers_contract') or {}
    metrics = _load(brain / 'web/kpis-totals' / f'{date}.json')
    if not metrics:
        return [f'ملف المقاييس الحاكم مفقود: web/kpis-totals/{date}.json']
    rng = metrics.get('range') or {}
    if rng.get('days_covered') != rng.get('days_total'):
        problems.append(f"دفتر الأحداث ناقص: {rng.get('days_covered')} من {rng.get('days_total')} يومًا")
    by_id = {m['id']: m for m in metrics.get('metrics') or []}
    meta_path = dist_root.parent / 'sources' / 'meta' / f'{date}.json'
    meta = _load(meta_path)
    if not meta:
        problems.append(f'ملف meta الحاكم مفقود: {meta_path}')
    meta_by_id = {c.get('id'): c for c in (meta or {}).get('hero_kpis') or [] if isinstance(c, dict)}

    cards = [c for c in (registry.get('hero_kpis') or {}).get('cards') or [] if c.get('layers')]
    if not cards:
        problems.append('لا بطاقة معلنة بطبقات في سجل البطاقات')
    pages = {}
    for lang, (sub, pat) in PAGES.items():
        p = dist_root / sub / pat.format(date=date)
        pages[lang] = p.read_text(encoding='utf-8') if p.exists() else None
        if pages[lang] is None:
            problems.append(f'{lang}: صفحة الإصدار المبنيّة مفقودة: {p}')

    for card in cards:
        cid = card['id']
        source = card.get('source') or {}
        if source.get('kind') == 'kpis_totals':
            metric_id = source.get('id')
            metric = _metric_by_id(metrics, str(metric_id or ''))
            if metric is None:
                problems.append(f'{cid}: مقياس القيمة الأساسية غير موجود: {metric_id}')
            layer_ids = {spec.get('id') for spec in (card.get('layers') or {}).values()}
            if layer_ids != {metric_id} or any(spec.get('kind') != 'kpis_totals' for spec in (card.get('layers') or {}).values()):
                problems.append(f'{cid}: القيمة الأساسية والطبقتان لا تستخدم المقياس نفسه: {metric_id} مقابل {sorted(layer_ids)}')
            actual_card = meta_by_id.get(cid)
            if actual_card is None:
                problems.append(f'{cid}: البطاقة غير موجودة في meta الحاكم')
            elif metric is not None:
                expected_value = metric.get(source.get('field', 'today'))
                if str(actual_card.get('value')).strip() != str(expected_value).strip():
                    problems.append(f'{cid}: قيمة البطاقة = «{actual_card.get("value")}» والمصدر = «{expected_value}»')
                for layer_name, spec in (card.get('layers') or {}).items():
                    expected_layer = metric.get(spec.get('field', layer_name))
                    actual_layer = actual_card.get(layer_name)
                    if str(actual_layer).strip() != str(expected_layer).strip():
                        problems.append(f'{cid}: meta طبقة {layer_name} = «{actual_layer}» والمصدر = «{expected_layer}»')
        for kind, spec in (card.get('layers') or {}).items():
            mid = spec.get('id')
            met = by_id.get(mid)
            if not met:
                problems.append(f"{cid}: مقياس غير موجود في ملف المقاييس: {mid}")
                continue
            expected = met.get(spec.get('field', kind))
            if expected is None:
                problems.append(f"{cid}: قيمة {kind} غير متاحة في المصدر ({mid})")
                continue
            for lang, html in pages.items():
                if html is None:
                    continue
                block = _card_block(html, cid)
                if block is None:
                    problems.append(f'{lang}: البطاقة {cid} غير موجودة في الصفحة')
                    continue
                got = _layer_value(block, lang, kind)
                if got is None:
                    problems.append(f'{lang}: طبقة {kind} مفقودة في البطاقة {cid}')
                elif str(got).strip() != str(expected).strip():
                    problems.append(f'{lang}: {cid} طبقة {kind} = «{got}» والمصدر = «{expected}»')
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--dist-root', default=None)
    ap.add_argument('--brain', default='.')
    a = ap.parse_args()
    if not a.dist_root:
        a.dist_root = str(pathlib.Path(__file__).resolve().parents[1].parent / 'seawatch' / 'dist')
    problems = check(a.date, pathlib.Path(a.dist_root), pathlib.Path(a.brain))
    if problems:
        print('   ✘ منع: بوابة طبقات بطاقات المؤشرات')
        for p in problems[:12]:
            print(f'     - {p}')
        return 2
    registry = _load(pathlib.Path(a.brain) / 'appendices/card_registry.json') or {}
    n = len([c for c in (registry.get('hero_kpis') or {}).get('cards') or [] if c.get('layers')])
    print(f'   ✔ طبقات البطاقات: {n} بطاقة بطبقتين (المجموع · آخر تحديث) مطابقة للمصدر عربيًا وإنجليزيًا')
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
