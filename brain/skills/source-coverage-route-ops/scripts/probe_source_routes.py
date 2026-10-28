#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص حي لمسارات المصادر الـ22 المحجوبة عن الآلية + المصدر المحجوب.

لكل مصدر: محاولة مباشرة (UA متصفح)، ثم وسيط نصّي (r.jina.ai)، ثم اكتشاف تغذية
معلنة في HTML (rel=alternate / atom / rss)، ثم كشف هيكل تطبيق JS.
المخرج: JSON بالمحاولات + جدول مختصر في الطرفية. لا يُخمَّن شيء.
"""
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
HDR = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ar,en;q=0.8',
}
CTX = ssl.create_default_context()
CTX_UNVERIFIED = ssl._create_unverified_context()

sys.path.insert(0, '/home/ubuntu/brain-marine-news/tools')
from source_channels import BROWSER_ROUTES  # noqa: E402

EXTRA = {17: 'https://x.com/bna_en'}


def fetch(url, timeout=25, unverified=False, max_bytes=400000):
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=CTX_UNVERIFIED if unverified else CTX) as r:
            body = r.read(max_bytes)
            return {'ok': True, 'status': r.status,
                    'ctype': r.headers.get('Content-Type', ''),
                    'bytes': len(body), 'body': body}
    except urllib.error.HTTPError as e:
        try:
            body = e.read(4000)
        except Exception:
            body = b''
        return {'ok': False, 'status': e.code, 'ctype': e.headers.get('Content-Type', ''),
                'bytes': len(body), 'body': body, 'error': f'HTTP {e.code}'}
    except Exception as e:
        return {'ok': False, 'status': None, 'ctype': '', 'bytes': 0,
                'body': b'', 'error': f'{type(e).__name__}: {e}'[:160]}


def feed_links(raw):
    text = raw.decode('utf-8', 'ignore')
    out = []
    for m in re.finditer(r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', text, re.I):
        tag = m.group(0)
        href = re.search(r'href=["\']([^"\']+)', tag)
        if href:
            out.append(href.group(1))
    for m in re.finditer(r'href=["\']([^"\']*(?:rss|feed|atom)[^"\']*)["\']', text, re.I):
        cand = m.group(1)
        if cand not in out and not cand.lower().endswith(('.css', '.js', '.png', '.jpg')):
            out.append(cand)
    return out[:6]


def probe(num, name, url):
    rec = {'num': num, 'name': name, 'url': url, 'direct': {}, 'jina': {}, 'feeds': [], 'shell': False}
    d = fetch(url, unverified=True)
    rec['direct'] = {k: v for k, v in d.items() if k != 'body'}
    if d.get('body'):
        raw = d['body']
        rec['feeds'] = feed_links(raw)
        rec['shell'] = bool(re.search(r'polyfills\.[0-9a-f]{8}|runtime\.[0-9a-f]{8}|/_next/static/|__NEXT_DATA__', raw.decode('utf-8', 'ignore'), re.I))
        rec['title'] = (re.search(r'<title[^>]*>(.*?)</title>', raw.decode('utf-8', 'ignore'), re.S | re.I) or [None, ''])[1][:90]
    j = fetch('https://r.jina.ai/' + url, timeout=40)
    rec['jina'] = {k: v for k, v in j.items() if k != 'body'}
    if j.get('body'):
        txt = j['body'].decode('utf-8', 'ignore')
        rec['jina_chars'] = len(txt)
        rec['jina_head'] = re.sub(r'\s+', ' ', txt[:220])
    return rec


def main():
    rows = [{'num': n, 'name': f'#{n}', 'url': v['url']} for n, v in sorted(BROWSER_ROUTES.items())]
    rows += [{'num': 17, 'name': 'bna_en', 'url': EXTRA[17]}]
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda r: probe(r['num'], r['name'], r['url']), rows))
    out = Path('/home/ubuntu/sources-audit/probe-routes.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{'#':>3} {'المسار':<58} {'مباشر':>8} {'حجم':>8} {'jina':>6} {'تغذية':>6} {'JS':>3}")
    for r in res:
        d, j = r['direct'], r['jina']
        print(f"{r['num']:>3} {r['url'][:58]:<58} {str(d.get('status') or d.get('error'))[:8]:>8} "
              f"{d.get('bytes', 0):>8} {str(j.get('status') or 'fail')[:6]:>6} "
              f"{len(r['feeds']):>6} {'نعم' if r['shell'] else 'لا':>3}")
    print('  ✔ حُفظ:', out)


if __name__ == '__main__':
    main()