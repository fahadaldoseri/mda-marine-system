#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مستخرجات محتوى للمسارات الآلية — مصدر واحد لكل استخراج (عطل ك-2xx).

المشكلة التي أُغلقت هنا: عدّاد «عناصر» كان يعدّ روابط صور وقوائم تنقّل ويسمّيها
محتوى، فيظهر مصدر «ناجحًا» بعشرات العناصر ولا يحمل خبرًا واحدًا. كل مستخرج هنا
يلزمه محتوى حقيقي: نصّ منشور أو عنوان مادة، مع رابط وتاريخ حين يتوفران.

المستخرجات:
  • extract_x_profile   : صفحة حساب X العامة (JSON مُهرَّب داخل السكربت) → منشورات فعلية.
  • extract_telegram    : عرض تلغرام العام /s/<قناة> → رسائل فعلية بتواريخها.
  • extract_proxy_text  : نصّ وسيط قراءة (r.jina.ai) → عناوين/روابط حقيقية بلا ضجيج.

الاستخدام:
  from content_extractors import items_for
  items = items_for(url, raw_bytes)   -> (method, [{'title','link','date'}])
"""
from __future__ import annotations

import html as _html
import re
import json
from typing import Any

# ── مرشّح الضجيج: ما لا يُعدّ محتوى ──
JUNK_TITLE = re.compile(
    r'^(?:image|img|logo|icon|banner|avatar|صورة|شعار|أيقونة)\b|^!\[|^\s*$', re.I)
JUNK_LINK = re.compile(r'\.(?:svg|png|jpe?g|gif|webp|ico)(?:\?|$)', re.I)
NAV_TITLE = re.compile(
    r'^(?:home|about|contact|login|sign in|register|menu|search|privacy|terms|cookies|'
    r'الرئيسية|اتصل بنا|من نحن|تسجيل|بحث|الأرشيف|المزيد|اقرأ المزيد|next|previous|'
    r'read more|more|share|follow|subscribe|advertisement|إعلان|جميع الحقوق)\b', re.I)


def is_real_item(item: dict[str, Any]) -> bool:
    """هل العنصر محتوى حقيقي؟ (عنوان نصّي ذو معنى + رابط غير وسائط)."""
    title = (item.get('title') or '').strip()
    link = (item.get('link') or '').strip()
    if len(title) < 12:
        return False
    if JUNK_TITLE.search(title) or NAV_TITLE.search(title):
        return False
    if JUNK_LINK.search(link):
        return False
    letters = len(re.findall(r'[^\W\d_]', title, re.UNICODE))
    return letters >= 8


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen, out = set(), []
    for it in items:
        key = re.sub(r'\s+', ' ', (it.get('title') or ''))[:90]
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def _unescape_js(text: str) -> str:
    """يحوّل نصًّا مُهرَّبًا داخل JSON (\\" و \\n و \\uXXXX) إلى نصّ مقروء."""
    def _u(m):
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return m.group(0)
    text = re.sub(r'\\u([0-9a-fA-F]{4})', _u, text)
    return (text.replace('\\n', '\n').replace('\\r', ' ')
                .replace('\\"', '"').replace("\\'", "'").replace('\\/', '/'))


# ── X (تويتر): الحمولة الرسمية للصفحة العامة ──
X_TEXT = re.compile(r'\\?"full_text\\?":\\?"((?:[^"\\]|\\.)*?)\\?"')
X_TIME = re.compile(r'\\?"created_at_ms\\?":(\d{13})')
X_ID = re.compile(r'\\?"entry_id\\?":\\?"tweet-(\d{6,})\\?"')
X_URL = re.compile(r'\\?"expanded_url\\?":\\?"(https?://[^"\\]+)')


def extract_x_profile(raw: bytes | str, handle: str) -> list[dict[str, Any]]:
    """منشورات حساب X من صفحته العامة: نصّ المنشور + تاريخه + رابطه."""
    text = raw.decode('utf-8', 'ignore') if isinstance(raw, bytes) else str(raw)
    import datetime as _dt
    marks = [(m.start(), m.group(1)) for m in X_ID.finditer(text)]
    items: list[dict[str, Any]] = []
    for idx, (pos, tid) in enumerate(marks):
        # نافذة المنشور = ما بين معرّف المنشور السابق ومعرّفه الحالي؛ آخر نصّ وآخر طابع
        # فيها يخصّان هذا المنشور (بيانات الحساب تسبق أول منشور فلا تُخلط به).
        start = marks[idx - 1][0] if idx else 0
        window = text[start:pos]
        bodies = X_TEXT.findall(window)
        times = X_TIME.findall(window)
        if not bodies:
            continue
        body = _unescape_js(bodies[-1]).strip()
        if not body:
            continue
        date = ''
        if times:
            date = _dt.datetime.fromtimestamp(int(times[-1]) / 1000, _dt.timezone.utc)\
                .strftime('%Y-%m-%dT%H:%M:%SZ')
        body = re.sub(r'\\[a-z]', ' ', body)
        body = re.sub(r'\s+', ' ', body.replace('\\', '')).strip()
        items.append({'title': body[:300],
                      'link': f'https://x.com/{handle}/status/{tid}', 'date': date})
    return _dedupe(items)


# ── تلغرام: العرض العام ──
TG_CARD = re.compile(
    r'data-post="([^"/]+)/(\d+)"(.*?)(?=<div class="tgme_widget_message |\Z)', re.S)
TG_TEXT = re.compile(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
TG_TIME = re.compile(r'<time[^>]*datetime="([^"]+)"')


def extract_telegram(raw: bytes | str, channel: str) -> list[dict[str, Any]]:
    """رسائل قناة تلغرام من عرضها العام /s/<قناة>."""
    text = raw.decode('utf-8', 'ignore') if isinstance(raw, bytes) else str(raw)
    items: list[dict[str, Any]] = []
    for m in TG_CARD.finditer(text):
        chan, mid, block = m.group(1), m.group(2), m.group(3)
        body = TG_TEXT.search(block)
        if not body:
            continue
        plain = _html.unescape(re.sub(r'<br\s*/?>', '\n', body.group(1)))
        plain = re.sub(r'<[^>]+>', ' ', plain)
        plain = re.sub(r'\s+', ' ', plain).strip()
        if not plain:
            continue
        stamp = TG_TIME.search(block)
        items.append({'title': plain[:300],
                      'link': f'https://t.me/{chan}/{mid}',
                      'date': (stamp.group(1) if stamp else '')})
    return _dedupe(items)


# ── الوسيط النصّي: عناوين وروابط حقيقية فقط ──
MD_LINK = re.compile(r'\[([^\]\n]{12,})\]\((https?://[^)\s]+)\)')
HTML_HEAD = re.compile(r'<h[1-6][^>]*>(.*?)</h[1-6]\s*>', re.S | re.I)


def extract_proxy_text(raw: bytes | str, source_url: str) -> list[dict[str, Any]]:
    """عنوان/رابط من نصّ وسيط قراءة — بمرشّح ضجيج صارم."""
    text = raw.decode('utf-8', 'ignore') if isinstance(raw, bytes) else str(raw)
    items: list[dict[str, Any]] = []
    for pattern in (MD_LINK, HTML_HEAD):
        for m in pattern.finditer(text):
            title = _html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1))).strip()
            link = m.group(2) if m.lastindex and m.lastindex >= 2 else source_url
            items.append({'title': re.sub(r'\s+', ' ', title)[:300], 'link': link, 'date': ''})
    items = [it for it in items if is_real_item(it)]
    if not items:
        return []
    return _dedupe(items)[:60]


# ── التوزيع بحسب المضيف ──
def extract_md_table(raw: bytes | str, source_url: str) -> list[dict[str, Any]]:
    """صفوف جدول Markdown — لسجلات الحوادث الرسمية المنشورة جدولًا (IMO).

    عطل مُصلح: صفحة IMO تُقرأ جدولًا من 121 صفًا حادثة، لكن المستخرج العام لا يرى
    فيها روابط ولا عناوين HTML، فيُعلن المصدر متعذّرًا وهو يقرأ محتوى حقيقيًا.
    الشرط: ثلاثة صفوف حقيقية على الأقل حتى لا يُعدّ جدول تنقّل محتوى.
    """
    text = raw.decode('utf-8', 'ignore') if isinstance(raw, bytes) else str(raw)
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith('|') or set(s) <= set('|-: '):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if len(cells) < 2:
            continue
        title = re.sub(r'\s+', ' ', _html.unescape(re.sub(r'<[^>]+>', ' ', cells[0]))).strip()
        if len(title) < 12 or title.lower() in ('name', 'vessel', 'ship', 'الاسم'):
            continue
        items.append({'title': title[:300], 'link': source_url, 'date': ''})
    items = [it for it in items if is_real_item(it)]
    if len(items) < 3:
        return []
    return _dedupe(items)[:120]


def extract_wp_json(raw: bytes | str) -> list[dict[str, Any]]:
    """واجهة WordPress العامة (wp-json/wp/v2/posts) — محتوى رسمي مملوك للجهة."""
    text = raw.decode('utf-8', 'ignore') if isinstance(raw, bytes) else str(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    items = []
    for post in data:
        if not isinstance(post, dict):
            continue
        title = post.get('title')
        if isinstance(title, dict):
            title = title.get('rendered') or ''
        title = re.sub(r'\s+', ' ', _html.unescape(re.sub(r'<[^>]+>', ' ', str(title or '')))).strip()
        if not title:
            continue
        items.append({'title': title[:300], 'link': str(post.get('link') or ''),
                      'date': str(post.get('date_gmt') or post.get('date') or '')})
    items = [it for it in items if is_real_item(it)]
    return _dedupe(items)[:40]


def extract_vessel_api(raw: bytes | str, source_url: str) -> list[dict[str, Any]]:
    """سجل سفينة واحد من واجهة عامة رسمية — سجل واحد محتوى كامل لا نقص.

    عطل مُصلح: قاعدة «ثلاثة عناصر على الأقل» صحيحة لصفحات القوائم، وخطأ على واجهة
    تُعيد سجلًا واحدًا (سفينة) تحمل الاسم والرمز والموقع؛ فيُقبل السجل الواحد هنا.
    """
    text = raw.decode('utf-8', 'ignore') if isinstance(raw, bytes) else str(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    # واجهة ShipNext تغلّف السجل في {'errors':…, 'data':{…}} — يُفتح الغلاف لا يُخمَّن.
    if isinstance(data.get('data'), dict):
        data = data['data']
    name = str(data.get('name') or data.get('vesselName') or '').strip()
    if not name:
        return []
    imo = str(data.get('imo') or data.get('imoNumber') or '').strip()
    kind = str(data.get('type') or data.get('vesselType') or '').strip()
    loc = data.get('location') if isinstance(data.get('location'), dict) else {}
    stamp = str((loc or {}).get('timestamp') or data.get('updatedAt') or '')
    title = ' — '.join(x for x in (f'{name} (IMO {imo})' if imo else name, kind) if x)
    return [{'title': title[:300], 'link': source_url, 'date': stamp}]


def host_of(url: str) -> str:
    m = re.match(r'https?://([^/]+)', url or '')
    return (m.group(1) if m else '').lower()


def items_for(url: str, raw: bytes | str) -> tuple[str, list[dict[str, Any]]]:
    """(اسم الطريقة, العناصر) بحسب مضيف المسار — بلا تخمين."""
    host = host_of(url)
    if host.endswith('x.com') or host.endswith('twitter.com'):
        handle = url.rstrip('/').split('/')[-1]
        items = extract_x_profile(raw, handle)
        if items:
            return 'x-profile', items
    if host.endswith('t.me'):
        channel = url.rstrip('/').split('/')[-1]
        items = extract_telegram(raw, channel)
        if items:
            return 'telegram-preview', items
    if 'jina.ai' in host:
        items = extract_proxy_text(raw, url)
        if items:
            return 'proxy-text', items
        # صفحة رسمية تُنشر جدولًا (سجل حوادث) بلا روابط: تُقرأ صفوفها محتوى.
        items = extract_md_table(raw, url)
        if items:
            return 'official-table', items
    if 'wp-json' in url:
        items = extract_wp_json(raw)
        if items:
            return 'wp-json', items
    if host.endswith('shipnext.com') and '/api/' in url:
        items = extract_vessel_api(raw, url)
        if items:
            return 'vessel-api', items
    return '', []


if __name__ == '__main__':
    import sys
    import urllib.request
    import ssl
    for u in sys.argv[1:]:
        req = urllib.request.Request(u, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'})
        with urllib.request.urlopen(req, timeout=35,
                                    context=ssl._create_unverified_context()) as r:
            raw = r.read(1500000)
        method, items = items_for(u, raw)
        print(f"   {u} → {method or 'لا مستخرج'} · {len(items)} عنصرًا حقيقيًا")
        for it in items[:3]:
            print('      ·', it['date'][:20], '|', it['title'][:88])
