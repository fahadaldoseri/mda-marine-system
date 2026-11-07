#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فاحص عقد واجهة التقرير: عنوان موحّد · سطر متغيّر · ألفاظ ممنوعة · طبقات بطاقات · تسرّب عربي.

يفشل مغلقًا (رمز 2) عند أي مخالفة. العقد يُقرأ من ملف JSON:
{
  "title_once": "نص العنوان الثابت",
  "sub_line": "class=\"sc-sub\"",
  "forbidden_visible": ["قطاعات", "للعلم العام", "النافذة"],
  "kpi_layers": {"metrics_file": "web/kpis-totals/{date}.json",
                 "labels": {"cumulative": "المجموع من 28 فبراير 2026", "updated": "آخر تحديث"},
                 "cards": {"<kpi-id>": "<metric-id>"}},
  "pages": {"ar": "reports/{date}.html", "en": "reports/en/{date}.html"}
}
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

VISIBLE_STRIP = re.compile(r'<(style|script)\b.*?</\1>', re.S | re.I)


def _visible(html: str) -> str:
    return VISIBLE_STRIP.sub(' ', html)


def _load(p: pathlib.Path):
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def check(contract: dict, dist_root: pathlib.Path, brain: pathlib.Path, date: str) -> list[str]:
    problems: list[str] = []
    pages = {}
    for lang, pat in (contract.get('pages') or {'ar': 'reports/{date}.html'}).items():
        p = dist_root / pat.format(date=date)
        if not p.exists():
            problems.append(f'{lang}: صفحة مفقودة: {p}')
            continue
        pages[lang] = p.read_text(encoding='utf-8')

    ar = pages.get('ar', '')
    title = contract.get('title_once')
    if title:
        n = ar.count(title)
        if n != 1:
            problems.append(f'العنوان الثابت يجب أن يظهر مرة واحدة، وظهر {n} مرة')
    sub = contract.get('sub_line')
    if sub and sub not in ar:
        problems.append('السطر المتغيّر تحت العنوان مفقود')

    for word in contract.get('forbidden_visible') or []:
        for lang, html in pages.items():
            n = _visible(html).count(word)
            if n:
                problems.append(f'{lang}: لفظ ممنوع ظاهر على الواجهة: «{word}» ×{n}')

    layers = contract.get('kpi_layers') or {}
    if layers:
        metrics = _load(brain / str(layers.get('metrics_file', '')).format(date=date))
        if not metrics:
            problems.append('ملف المقاييس الحاكم مفقود')
        else:
            by_id = {m['id']: m for m in metrics.get('metrics') or []}
            labels = layers.get('labels') or {}
            for kpi_id, metric_id in (layers.get('cards') or {}).items():
                met = by_id.get(metric_id)
                if not met:
                    problems.append(f'{kpi_id}: مقياس غير موجود: {metric_id}')
                    continue
                block = None
                i = ar.find(f'data-kpi-id="{kpi_id}"')
                if i >= 0:
                    j = ar.find('data-kpi-id="', i + 10)
                    block = ar[i:j if j > 0 else i + 4000]
                if block is None:
                    problems.append(f'{kpi_id}: البطاقة غير موجودة في الصفحة')
                    continue
                for kind, field in (('cumulative', 'cumulative'), ('updated', 'updated')):
                    label = re.escape(labels.get(kind, ''))
                    m = re.search(rf'{label}</span>\s*<b class="bidi">([^<]+)</b>', block)
                    if not m:
                        problems.append(f'{kpi_id}: طبقة {kind} مفقودة')
                    elif m.group(1).strip() != str(met.get(field, '')).strip():
                        problems.append(f'{kpi_id}: طبقة {kind} = «{m.group(1)}» والمصدر = «{met.get(field)}»')

    en = pages.get('en')
    if en and re.search(r'[\u0600-\u06FF]', _visible(en)):
        problems.append('en: نص عربي متسرب في الصفحة الإنجليزية')
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--contract', required=True)
    ap.add_argument('--dist-root', required=True)
    ap.add_argument('--brain', default='.')
    ap.add_argument('--date', required=True)
    a = ap.parse_args()
    contract = json.loads(pathlib.Path(a.contract).read_text(encoding='utf-8'))
    problems = check(contract, pathlib.Path(a.dist_root), pathlib.Path(a.brain), a.date)
    if problems:
        print('   ✘ منع: عقد واجهة التقرير')
        for p in problems[:14]:
            print(f'     - {p}')
        return 2
    print('   ✔ عقد الواجهة: عنوان واحد · سطر متغيّر · لا ألفاظ ممنوعة · طبقات مطابقة · لا تسرّب عربي')
    return 0


if __name__ == '__main__':
    sys.exit(main())
