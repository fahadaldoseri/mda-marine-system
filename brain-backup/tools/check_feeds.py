#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يقرأ تغذيات RSS/Atom من sections/10-sources.md ويجلب مستجدات آخر 24/48/72 ساعة."""
import json, re, sys, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path('/home/ubuntu/brain-marine-news/sections/10-sources.md')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'}

def feeds():
    out, grab = [], False
    for ln in SRC.read_text(encoding='utf-8').splitlines():
        if ln.startswith('## تغذيات RSS'):
            grab = True; continue
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
    F = feeds()
    print(f"  تغذيات مرصودة: {len(F)}")
    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(fetch, F))
    ok = [r for r in res if r['ok']]
    total = sum(len(r['items']) for r in ok)
    print(f"  نجح: {len(ok)} · فشل: {len(res)-len(ok)} · عناصر مقروءة: {total}")
    for r in res:
        if not r['ok']:
            print(f"   ✘ {r['num']} {r['name'][:34]}: {r['error']}")
    out = Path('/home/ubuntu/brain-marine-news/feeds'); out.mkdir(exist_ok=True)
    stamp = dt.datetime.utcnow().strftime('%Y-%m-%d')
    (out / f'feeds-{stamp}.json').write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding='utf-8')
    lines = [f"# مستجدات التغذيات — {stamp} UTC", "", f"تغذيات مفحوصة: {len(res)} · ناجحة: {len(ok)} · عناصر: {total}", ""]
    for r in ok:
        lines.append(f"## {r['num']}. {r['name']}")
        for it in r['items'][:5]:
            lines.append(f"- {it['date'][:25]} · {it['title'][:110]}")
        lines.append("")
    (out / f'feeds-{stamp}.md').write_text("\n".join(lines), encoding='utf-8')
    print(f"  ✔ حُفظ: feeds-{stamp}.json / .md")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
