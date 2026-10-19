#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يقرأ تغذيات RSS/Atom من sections/10-sources.md ويجلب مستجدات آخر 24/48/72 ساعة.

إصلاح 19 أكتوبر 2026 (بند 2 و3 من التدقيق المستقل): الأداة كانت تُرجع صفرًا دائمًا
فتظهر «ناجحة» في علامة الخط مهما كان عدد التغذيات الفاشلة. الآن:
  · رمز الخروج: 0 = مكتمل · 1 = متدهور (فشل محدود) · 2 = فاشل (تجاوز حد الفشل)
  · حدّ الفشل المقبول: 20% من التغذيات
  · تُكتب حالة تفصيلية: feeds/feeds-<التاريخ>.status.json
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)
import argparse
import datetime as dt
import html
import json
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from normalize_digits import to_latin  # الأرقام عند المصدر: المولَّد يُكتب لاتينيًا
import re
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path(f'{BRAIN}/sections/10-sources.md')
OUT = Path(f'{BRAIN}/feeds')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'
HEADERS = {
    'User-Agent': UA,
    'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.1',
    'Referer': 'https://www.google.com/',
}
FAIL_RATIO_LIMIT = 0.20
MIN_CONTENT_CHARS = 400
MIN_ITEMS = 1
UNVERIFIED_TLS_SOURCE_NUMS = {28}
UNVERIFIED_TLS_CONTEXT = ssl._create_unverified_context()

# The primary URL remains the URL in sections/10-sources.md.  These routes are
# source-owned feeds/pages (or the documented text proxy for the same URL), not
# substitute news sources.  Keep the via labels stable: they are written to the
# status file for auditability.
FALLBACK_ROUTES = {
    14: [
        {'url': 'https://r.jina.ai/http://www.alarabiya.net/feed/rss2/ar.xml',
         'via': 'fallback:jina.ai/alarabiya-rss'},
        {'url': 'https://r.jina.ai/http://www.alarabiya.net/',
         'via': 'fallback:jina.ai/alarabiya-home'},
    ],
    17: [
        {'url': 'https://r.jina.ai/http://x.com/bna_en',
         'via': 'fallback:jina.ai/bna-en-x'},
        {'url': 'https://r.jina.ai/http://www.bna.bh/en/RSSFeeds.aspx?cms=iQRpheuphYtJ6pyXUGiNqqtA5DItoRVa',
         'via': 'fallback:jina.ai/bna-rss'},
    ],
    20: [
        {'url': 'https://r.jina.ai/http://www.alayam.com/',
         'via': 'fallback:jina.ai/alayam-home'},
        {'url': 'https://r.jina.ai/http://www.alayam.com/pages/rss',
         'via': 'fallback:jina.ai/alayam-rss'},
    ],
    28: [
        {'url': 'https://omannews.gov.om/rssinfo/',
         'via': 'fallback:omannews-rssinfo'},
        {'url': 'https://omannews.gov.om/',
         'via': 'fallback:omannews-home'},
        {'url': 'https://r.jina.ai/http://omannews.gov.om/',
         'via': 'fallback:jina.ai/omannews-home'},
    ],
    33: [
        {'url': 'https://r.jina.ai/http://www.maritime.dot.gov/rss.xml',
         'via': 'fallback:jina.ai/marad-rss'},
        {'url': 'https://r.jina.ai/http://www.maritime.dot.gov/msci',
         'via': 'fallback:jina.ai/msci'},
    ],
}


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


def _clean(value):
    value = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', value or '', flags=re.S)
    return html.unescape(re.sub(r'<[^>]+>', ' ', value)).strip()


def _visible_text(payload):
    text = payload.decode('utf-8', 'ignore') if isinstance(payload, bytes) else str(payload)
    text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def parse(xml):
    """Parse RSS/Atom entries while tolerating namespaces and link styles."""
    items = []
    for m in re.finditer(r'<(item|entry)(?:\s[^>]*)?>(.*?)</\1\s*>', xml, re.S | re.I):
        body = m.group(2)
        title = re.search(r'<title\b[^>]*>(.*?)</title\s*>', body, re.S | re.I)
        link = (re.search(r'<link\b[^>]*href=["\']([^"\']+)', body, re.S | re.I)
                or re.search(r'<link\b[^>]*>(.*?)</link\s*>', body, re.S | re.I))
        date = re.search(r'<(pubDate|updated|published|dc:date)\b[^>]*>(.*?)</\1\s*>', body, re.S | re.I)
        items.append({
            'title': _clean(title.group(1)) if title else '',
            'link': _clean(link.group(1)) if link else '',
            'date': _clean(date.group(2)) if date else '',
        })
    return [item for item in items if item['title'] or item['link']]


def _derived_items(text, source_url):
    """Turn a valid proxy-rendered page into auditable, non-empty feed items."""
    items = []
    seen = set()
    patterns = [
        r'\[([^\]\n]{8,})\]\((https?://[^)\s]+)\)',
        r'<h[1-6][^>]*>(.*?)</h[1-6]\s*>',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I | re.S):
            title = _clean(match.group(1))
            link = match.group(2) if len(match.groups()) > 1 else source_url
            key = (title, link)
            if title and key not in seen:
                seen.add(key)
                items.append({'title': title, 'link': link, 'date': ''})
            if len(items) >= 50:
                return items
    if not items:
        title_match = re.search(r'(?im)^\s*Title:\s*(.+?)\s*$', text)
        title = _clean(title_match.group(1)) if title_match else ''
        if not title:
            title = next((line.strip() for line in text.splitlines() if line.strip()), '')
        if title:
            items.append({'title': title[:300], 'link': source_url, 'date': ''})
    return items


def _blocked_reason(text):
    sample = text[:2500].lower()
    markers = {
        'attention required': 'blocked page: Attention Required',
        'human verification': 'blocked page: Human Verification',
        'target url returned error': 'proxy reported target error',
        'access denied': 'blocked page: Access Denied',
        'just a moment': 'blocked page: Just a moment',
        'error 403': 'proxy reported HTTP 403',
    }
    for marker, reason in markers.items():
        if marker in sample:
            return reason
    return ''


def _payload_items(payload, source_url):
    raw = payload.decode('utf-8', 'ignore') if isinstance(payload, bytes) else str(payload)
    text = _visible_text(raw)
    blocked = _blocked_reason(raw)
    if blocked:
        raise ValueError(blocked)
    if len(text) < MIN_CONTENT_CHARS:
        raise ValueError(f'content too short: {len(text)} chars < {MIN_CONTENT_CHARS}')
    items = parse(raw) or _derived_items(raw, source_url)
    if len(items) < MIN_ITEMS:
        raise ValueError(f'no feed items found (minimum {MIN_ITEMS})')
    return items, len(text)


def _routes_for(feed):
    routes = [{'url': feed['url'], 'via': 'primary'}]
    seen = {feed['url']}
    for route in FALLBACK_ROUTES.get(feed['num'], []):
        if route['url'] not in seen:
            routes.append(route)
            seen.add(route['url'])
    return routes


def _error_text(error):
    return str(error).strip()[:180] or repr(error)[:180]


def fetch(f):
    attempts = []
    for route in _routes_for(f):
        try:
            headers = {**HEADERS, 'Referer': f['url']}
            request = urllib.request.Request(route['url'], headers=headers)
            use_unverified_tls = (
                f['num'] in UNVERIFIED_TLS_SOURCE_NUMS and route['via'] != 'primary'
            )
            context = UNVERIFIED_TLS_CONTEXT if use_unverified_tls else None
            tls_verification = ('disabled_source_28_only' if use_unverified_tls else 'verified')
            with urllib.request.urlopen(request, timeout=25, context=context) as response:
                payload = response.read()
            items, content_chars = _payload_items(payload, route['url'])
            attempts.append({
                'url': route['url'], 'via': route['via'], 'ok': True,
                'items_count': len(items), 'content_chars': content_chars,
                'tls_verification': tls_verification,
            })
            return {
                **f, 'ok': True, 'items': items, 'items_count': len(items),
                'content_chars': content_chars, 'via': route['via'],
                'fetched_url': route['url'], 'attempts': attempts,
                'tls_verification': tls_verification,
            }
        except Exception as error:
            message = _error_text(error)
            attempts.append({
                'url': route['url'], 'via': route['via'], 'ok': False,
                'error': message, 'tls_verification': tls_verification,
            })
    block_reason = 'all routes failed: ' + ' | '.join(
        f"{attempt['via']}: {attempt.get('error', 'invalid content')}" for attempt in attempts
    )
    return {
        **f, 'ok': False, 'error': attempts[-1].get('error', 'invalid content'),
        'items': [], 'items_count': 0, 'content_chars': 0, 'via': None,
        'fetched_url': None, 'attempts': attempts, 'block_reason': block_reason,
        'tls_verification': ('disabled_source_28_only'
                             if f['num'] in UNVERIFIED_TLS_SOURCE_NUMS else 'verified'),
    }


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
        print(f"   ✘ {r['num']} {r['name'][:34]}: {r['block_reason']}")

    if not ok:
        status = 'failed'
    elif ratio > FAIL_RATIO_LIMIT:
        status = 'failed'
    elif failed:
        status = 'degraded'
    else:
        status = 'ok'

    OUT.mkdir(exist_ok=True)
    (OUT / f'feeds-{stamp}.json').write_text(
        to_latin(json.dumps(ok, ensure_ascii=False, indent=1)), encoding='utf-8')
    lines = [f"# مستجدات التغذيات — {stamp} UTC", "",
             f"تغذيات مفحوصة: {len(res)} · ناجحة: {len(ok)} · فاشلة: {len(failed)} · عناصر: {total}", ""]
    for r in ok:
        lines.append(f"## {r['num']}. {r['name']} — via: {r['via']} · عناصر: {r['items_count']} · محتوى: {r['content_chars']} حرف")
        for it in r['items'][:5]:
            lines.append(f"- {it['date'][:25]} · {it['title'][:110]}")
        lines.append("")
    (OUT / f'feeds-{stamp}.md').write_text(to_latin("\n".join(lines)), encoding='utf-8')
    checked_feeds = [{
        'num': r['num'], 'name': r['name'], 'primary_url': r['url'],
        'ok': r['ok'], 'via': r.get('via'), 'fetched_url': r.get('fetched_url'),
        'items_count': r.get('items_count', 0), 'content_chars': r.get('content_chars', 0),
        'tls_verification': r.get('tls_verification', 'verified'),
        **({'block_reason': r['block_reason']} if not r['ok'] else {}),
    } for r in res]
    (OUT / f'feeds-{stamp}.status.json').write_text(to_latin(json.dumps({
        'date': stamp, 'status': status, 'checked': len(res), 'ok': len(ok), 'failed': len(failed),
        'fail_ratio': round(ratio, 3), 'fail_ratio_limit': FAIL_RATIO_LIMIT, 'items': total,
        'checked_feeds': checked_feeds,
        'failed_feeds': [{
            'num': r['num'], 'name': r['name'], 'primary_url': r['url'],
            'error': r['error'], 'block_reason': r['block_reason'], 'attempts': r['attempts'],
        } for r in failed],
        'written_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }, ensure_ascii=False, indent=1)), encoding='utf-8')
    print(f"  ✔ حُفظ: feeds-{stamp}.json / .md / .status.json — الحالة: {status}")
    return {'ok': 0, 'degraded': 1, 'failed': 2}[status]


if __name__ == '__main__':
    raise SystemExit(main())
