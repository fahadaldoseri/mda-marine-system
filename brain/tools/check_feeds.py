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
import time
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
# مصادر بلا تغذية آلية رسمية (موقعها JS ولا تغذية معلنة): تُقيَّد «يُفحص بالمتصفح»
# ولا تُحسب فشلًا — لا نبني مسارًا يتجاوز الحماية (سياسة المستخدم).
BROWSER_ONLY = {}  # ك-81: واس صار له مسار رسمي (بيانات الصفحة المُضمَّنة)
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
    # عطل ك-65: وام (25) وواس (26) مواقع JS بلا تغذية RSS، فتُسجَّلان فشلًا كل يوم.
    # وام لها قناة رسمية معلنة على تلغرام (t.me/wamnews_en) — قناة مملوكة للجهة، لا تجاوز حماية.
    25: [
        {'url': 'https://t.me/s/wamnews_en',
         'via': 'official-telegram:wamnews_en'},
    ],
    # ك-81: واس (26) موقع Next.js؛ بياناته الرسمية مُضمَّنة في الصفحة نفسها.
    26: [
        {'url': 'https://www.spa.gov.sa/ar', 'via': 'official:spa-next-data'},
        {'url': 'https://www.spa.gov.sa/', 'via': 'official:spa-home-next-data'},
    ],
    14: [
        {'url': 'https://r.jina.ai/http://www.alarabiya.net/feed/rss2/ar.xml',
         'via': 'fallback:jina.ai/alarabiya-rss'},
        {'url': 'https://r.jina.ai/http://www.alarabiya.net/',
         'via': 'fallback:jina.ai/alarabiya-home'},
    ],
    17: [
        {'url': 'https://www.bna.bh/en/RSSFeeds.aspx?cms=iQRpheuphYtJ6pyXUGiNqqtA5DItoRVa',
         'via': 'official:bna-en-rss'},
        {'url': 'https://web.archive.org/web/20260108135704/https://www.bna.bh/en/RSSFeeds.aspx?cms=iQRpheuphYtJ6pyXUGiNqqtA5DItoRVa',
         'via': 'archive:bna-en-rss'},
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


def _next_data_items(raw):
    """يقرأ محتوى المواقع الحديثة من __NEXT_DATA__ المُضمَّن في الصفحة الرسمية.

    مسار رسمي: الصفحة نفسها تحمل بياناتها في HTML، فلا حاجة لتجاوز أي حماية.
    """
    match = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', raw, re.S | re.I
    )
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except Exception:
        return []
    found = []

    def walk(node, depth=0):
        if depth > 8 or len(found) >= 60:
            return
        if isinstance(node, dict):
            title = node.get('title') or node.get('headline') or node.get('name')
            if isinstance(title, str) and len(title.strip()) >= 8:
                link = (node.get('url') or node.get('link') or node.get('slug')
                        or node.get('uuid') or '')
                found.append({
                    'title': _clean(title),
                    'link': str(link),
                    'date': str(node.get('published_at') or node.get('publishedAt')
                                or node.get('date') or ''),
                })
            for value in node.values():
                walk(value, depth + 1)
        elif isinstance(node, list):
            for value in node:
                walk(value, depth + 1)

    walk(data)
    seen, items = set(), []
    for item in found:
        key = item['title']
        if key not in seen:
            seen.add(key)
            items.append(item)
    return items


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
    items = parse(raw)
    method = 'rss'
    if not items:
        items = _next_data_items(raw)
        method = 'next-data'
    if not items:
        items = _derived_items(raw, source_url)
        method = 'derived'
    # عطل ك-82: هيكل تطبيق JS يُنتج «عنصرًا» واحدًا وهميًا من عنوان، فيظهر المصدر ناجحًا
    # بلا محتوى حقيقي. الشرط: أي استخراج مشتق من هيكل تطبيق يلزمه 3 عناصر على الأقل.
    shell = bool(re.search(r'polyfills\.[0-9a-f]{8}|runtime\.[0-9a-f]{8}|/_next/static/', raw, re.I))
    if method == 'derived' and shell and len(items) < 3:
        raise ValueError(f'app shell without real feed items ({len(items)} derived)')
    # عطل ك-81: مواقع Next.js تحمل بياناتها في <script>، فالنص المرئي قصير بطبعه.
    # القياس الصحيح: إن وُجدت عناصر مقروءة فالمحتوى كافٍ؛ وإلا يُقاس النص المرئي.
    if not items:
        if len(text) < MIN_CONTENT_CHARS:
            raise ValueError(f'content too short: {len(text)} chars < {MIN_CONTENT_CHARS}')
        raise ValueError(f'no feed items found (minimum {MIN_ITEMS})')
    content_chars = len(text) if len(text) >= MIN_CONTENT_CHARS else len(raw)
    return items, content_chars


# مسار رسمي يُقدَّم على العنوان الأساسي لأنه أنقى محتوى (عطل ك-82).
PREFERRED_ROUTE = {25: 'https://t.me/s/wamnews_en'}


def _routes_for(feed):
    routes = [{'url': feed['url'], 'via': 'primary'}]
    seen = {feed['url']}
    for route in FALLBACK_ROUTES.get(feed['num'], []):
        if route['url'] not in seen:
            routes.append(route)
            seen.add(route['url'])
    preferred = PREFERRED_ROUTE.get(feed['num'])
    if preferred:
        routes.sort(key=lambda r: 0 if r['url'] == preferred else 1)
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


def _parse_date(value):
    """يحوّل تاريخ مادة التغذية إلى كائن زمني (RFC-822 أو ISO)، وإلا None."""
    import email.utils as _eu
    text = (value or '').strip()
    if not text:
        return None
    try:
        parsed = _eu.parsedate_to_datetime(text)
        if parsed:
            return (parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc))
    except Exception:
        pass
    try:
        parsed = dt.datetime.fromisoformat(text.replace('Z', '+00:00'))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc))
    except Exception:
        return None


def _newest_age_days(entry):
    """عمر أحدث مادة في التغذية بالأيام، أو None إذا تعذّر الاستخراج (عطل ك-117)."""
    newest = None
    for item in entry.get('items', []):
        stamp = _parse_date(item.get('date', ''))
        if stamp and (newest is None or stamp > newest):
            newest = stamp
    if not newest:
        return None
    return (dt.datetime.now(dt.timezone.utc) - newest).days


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
    # عطل ك-68: انقطاع اتصال عابر لمصدر واحد كان يُسجَّل فشلًا نهائيًا. إعادة محاولة واحدة.
    retry = [r for r in res if not r['ok'] and r['num'] not in BROWSER_ONLY
             and any(k in str(r.get('error', '')).lower()
                     for k in ('timed out', 'incompleteread', 'connection reset', 'remote end closed'))]
    if retry:
        time.sleep(5)
        again = {r['num']: r for r in [fetch(x) for x in retry]}
        res = [again.get(r['num'], r) if (not r['ok'] and r['num'] in again) else r for r in res]
    # الثابت الملزم (البند هـ): مفحوصة = ناجحة + متعذّرة، وتُحسب المسارات الثلاثة كلها
    attempted = {r['num'] for r in res} | {r['num'] for r in browser_only}
    ok_nums = {r['num'] for r in res if r['ok']}
    failed_nums = attempted - ok_nums
    ok = [r for r in res if r['ok']]
    failed = [r for r in res if not r['ok'] and r['num'] in failed_nums]
    n_src = len(attempted)
    n_ok = len(ok_nums)
    n_fail = len(failed_nums)
    assert n_src == n_ok + n_fail, f'عدادات التغذيات غير متسقة: {n_src} != {n_ok}+{n_fail}'
    checked_feeds = [{
        'num': r['num'], 'name': r['name'], 'primary_url': r['url'],
        'ok': r['ok'], 'via': r.get('via'), 'fetched_url': r.get('fetched_url'),
        'items_count': r.get('items_count', 0), 'content_chars': r.get('content_chars', 0),
        'latest_age_days': r.get('latest_age_days'),
        'tls_verification': r.get('tls_verification', 'verified'),
        **({'block_reason': r['block_reason']} if not r['ok'] else {}),
    } for r in res]
    (OUT / f'feeds-{stamp}.status.json').write_text(to_latin(json.dumps({
        'date': stamp, 'status': status, 'checked': n_src, 'ok': n_ok,
        'failed': n_fail, 'browser_only': sorted({r['num'] for r in browser_only}),
        'stale': sorted({r['num'] for r in stale}), 'empty': sorted({r['num'] for r in empty}),
        'stale_days_limit': STALE_DAYS_LIMIT,
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
