#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يقرأ تغذيات RSS/Atom من sections/10-sources.md ويجلب مستجدات آخر 24/48/72 ساعة.

إصلاح 19 أكتوبر 2026 (بند ٢ و٣ من التدقيق المستقل): الأداة كانت تُرجع صفرًا دائمًا
فتظهر «ناجحة» في علامة الخط مهما كان عدد التغذيات الفاشلة. الآن:
  · رمز الخروج: 0 = مكتمل · 1 = متدهور (فشل محدود) · 2 = فاشل (تجاوز حد الفشل)
  · حدّ الفشل المقبول: 20% من التغذيات
  · تُكتب حالة تفصيلية: feeds/feeds-<التاريخ>.status.json
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path('/home/ubuntu/brain-marine-news/sections/10-sources.md')
OUT = Path('/home/ubuntu/brain-marine-news/feeds')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'}
FAIL_RATIO_LIMIT = 0.20


def feeds():
    out, grab = [], False
    for ln in SRC.read_text(encoding='utf-8').splitlines():
        if ln.startswith('## تغذيات RSS'):
            grab = True
            continue
        if grab and ln.startswith('## '):
            break
        if grab:
            m = re.match(r'^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(\S+)\s*\|$', ln.strip())
            if m:
                out.append({'num': int(m.group(1)), 'name': m.group(2), 'url': m.group(3)})
    return out


def parse(xml):
    items = []
    for m in re.finditer(r'<(item|entry)>(.*?)</\1>', xml, re.S):
        b = m.group(2)
        t = re.search(r'<title[^>]*>(.*?)</title>', b, re.S)
        l = re.search(r'<link[^>]*href="([^"]+)"', b) or re.search(r'<link[^>]*>(.*?)</link>', b, re.S)
        d = re.search(r'<(pubDate|updated|published|dc:date)[^>]*>(.*?)</\1>', b, re.S)
        items.append({'title': re.sub(r'<[^>]+>', '', t.group(1)).strip() if t else '',
                      'link': (l.group(1).strip() if l else ''),
                      'date': (d.group(2).strip() if d else '')})
    return items


def fetch(f):
    try:
        r = urllib.request.urlopen(urllib.request.Request(f['url'], headers=UA), timeout=25)
        return {**f, 'ok': True, 'items': parse(r.read().decode('utf-8', 'ignore'))}
    except Exception as e:
        return {**f, 'ok': False, 'error': str(e)[:80], 'items': []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default='', help='تاريخ ISO للتسمية (افتراضيًا تاريخ UTC اليوم)')
    a = ap.parse_args()
    stamp = a.date or dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')

    F = feeds()
    print(f"  تغذيات مرصودة: {len(F)}")
    if not F:
        print("  ✘ لا تغذيات في sections/10-sources.md — خطأ إعداد")
        return 2
    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(fetch, F))
    ok = [r for r in res if r['ok']]
    failed = [r for r in res if not r['ok']]
    total = sum(len(r['items']) for r in ok)
    ratio = len(failed) / len(res)
    print(f"  نجح: {len(ok)} · فشل: {len(failed)} · عناصر مقروءة: {total}")
    for r in failed:
        print(f"   ✘ {r['num']} {r['name'][:34]}: {r['error']}")

    if not ok:
        status = 'failed'
    elif ratio > FAIL_RATIO_LIMIT:
        status = 'failed'
    elif failed:
        status = 'degraded'
    else:
        status = 'ok'

    OUT.mkdir(exist_ok=True)
    (OUT / f'feeds-{stamp}.json').write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding='utf-8')
    lines = [f"# مستجدات التغذيات — {stamp} UTC", "",
             f"تغذيات مفحوصة: {len(res)} · ناجحة: {len(ok)} · فاشلة: {len(failed)} · عناصر: {total}", ""]
    for r in ok:
        lines.append(f"## {r['num']}. {r['name']}")
        for it in r['items'][:5]:
            lines.append(f"- {it['date'][:25]} · {it['title'][:110]}")
        lines.append("")
    (OUT / f'feeds-{stamp}.md').write_text("\n".join(lines), encoding='utf-8')
    (OUT / f'feeds-{stamp}.status.json').write_text(json.dumps({
        'date': stamp, 'status': status, 'checked': len(res), 'ok': len(ok), 'failed': len(failed),
        'fail_ratio': round(ratio, 3), 'fail_ratio_limit': FAIL_RATIO_LIMIT, 'items': total,
        'failed_feeds': [{'num': r['num'], 'name': r['name'], 'error': r['error']} for r in failed],
        'written_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"  ✔ حُفظ: feeds-{stamp}.json / .md / .status.json — الحالة: {status}")
    return {'ok': 0, 'degraded': 1, 'failed': 2}[status]


if __name__ == '__main__':
    raise SystemExit(main())