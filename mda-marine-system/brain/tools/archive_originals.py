#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يحفظ نسخة الأصل الرسمي: HTML/PDF + بصمة sha256 + بيان manifest.json.

إصلاح 19 أكتوبر 2026 (بند 3 و4 من التدقيق المستقل): الأداة كانت تطبع الفشل ولا تُرجع
رمز خروج، وكان الأصل «المحفوظ» قد يكون صفحة تُبنى بجافاسكربت بلا بلاغات. الآن:
  · فحص محتوى: نص HTML الفعلي يُقاس بعد إزالة الوسوم والسكربتات؛ الصفحة الهيكلية الفارغة
    تُوسَم empty_shell ولا تُحتسب أصلًا صالحًا.
  · رمز الخروج: 0 = كل الأصول صالحة · 1 = متدهور (بعضها فشل أو هيكلي فارغ) · 2 = لا أصل صالح.
  · تُكتب حالة تفصيلية: archive/originals/<اليوم>/status.json
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

B = Path(f'{BRAIN}')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'}
BROWSER_ONLY_URLS = {
    'https://www.ukmto.org/recent-incidents',
    'https://www.ukmto.org/advisories',
}
BROWSER_ONLY_REASON = 'محمي بتحقق بشري — لا يُجلب آليًا (سياسة: لا تجاوز للحماية) · يُفحص بالمتصفح'
MIN_TEXT_CHARS = 400


def _html_text_chars(body: bytes) -> int:
    txt = body.decode('utf-8', 'ignore')
    txt = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', txt)
    txt = re.sub(r'(?s)<[^>]+>', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return len(txt)


def grab(url: str, day: str) -> dict:
    d = B / 'archive' / 'originals' / day
    d.mkdir(parents=True, exist_ok=True)
    rec = {'url': url, 'utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds') + 'Z'}
    # عطل ك-63: مصادر محمية بتحقق بشري (UKMTO) تفشل آليًا فيُسجَّل فشل يومي بلا معنى.
    # السياسة: لا نبني مسارًا يتجاوز الحماية. يُقيَّد السبب ويُصنَّف «يُفحص بالمتصفح».
    if url in BROWSER_ONLY_URLS:
        rec.update({'status': 'browser_only', 'error': BROWSER_ONLY_REASON})
        return rec
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40)
        body = r.read()
        ct = r.headers.get('Content-Type', '')
        is_pdf = 'pdf' in ct.lower() or body[:4] == b'%PDF'
        ext = '.pdf' if is_pdf else '.html'
        name = hashlib.sha256(url.encode()).hexdigest()[:12] + ext
        (d / name).write_bytes(body)
        text_chars = None if is_pdf else _html_text_chars(body)
        rec.update({'file': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                    'content_type': ct, 'text_chars': text_chars})
        if not is_pdf and text_chars < MIN_TEXT_CHARS:
            rec.update({'status': 'empty_shell',
                        'error': f'صفحة هيكلية بلا محتوى نصي ({text_chars} حرفًا < {MIN_TEXT_CHARS}) — لا قيمة إثباتية'})
        elif is_pdf and len(body) < 5000:
            rec.update({'status': 'empty_shell', 'error': f'ملف PDF صغير بشكل غير معقول ({len(body)} بايت)'})
        else:
            rec.update({'status': 'saved'})
    except Exception as e:
        rec.update({'status': 'failed', 'error': str(e)[:110]})
    return rec


def main() -> int:
    if len(sys.argv) < 3:
        print("الاستخدام: archive_originals.py <YYYY-MM-DD> <ملف الروابط>")
        return 2
    day, urls_file = sys.argv[1], sys.argv[2]
    urls = [u.strip() for u in Path(urls_file).read_text(encoding='utf-8').splitlines() if u.strip().startswith('http')]
    d = B / 'archive' / 'originals' / day
    d.mkdir(parents=True, exist_ok=True)
    if not urls:
        print("  · لا روابط في قائمة الأصول — لا حفظ مطلوب")
        (d / 'status.json').write_text(json.dumps(
            {'date': day, 'status': 'ok', 'checked': 0, 'healthy': 0, 'empty_shell': 0, 'failed': 0,
             'note': 'لا أصل مطلوب في فترة اليوم'},
            ensure_ascii=False, indent=1), encoding='utf-8')
        return 0

    with ThreadPoolExecutor(max_workers=6) as ex:
        recs = list(ex.map(lambda u: grab(u, day), urls))
    (d / 'manifest.json').write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding='utf-8')

    healthy = sum(1 for r in recs if r['status'] == 'saved')
    browser = sum(1 for r in recs if r['status'] == 'browser_only')
    shells = sum(1 for r in recs if r['status'] == 'empty_shell')
    failed = sum(1 for r in recs if r['status'] == 'failed')
    # عطل ك-71: المتعذّر بحماية بشرية كان يجعل اليوم «متعذّرًا» بلا حاجة.
    # الحالة متعذّرة فقط عند فشل حقيقي أو هيكل فارغ.
    healthy_total = healthy + browser
    # «مُثبَت» = أصل محفوظ أو متعذّر بسبب موثّق (حماية بشرية) — لا فشل ولا هيكل فارغ
    status = 'ok' if (healthy_total == len(recs) and failed == 0 and shells == 0) \
        else ('failed' if healthy == 0 and browser == 0 else 'degraded')
    print(f"  أصول مثبتة: {healthy_total}/{len(recs)} (محفوظ {healthy} · حماية بشرية {browser})"
          f" · هيكلية فارغة: {shells} · فشل: {failed} · البيان: {d/'manifest.json'}")
    for r in recs:
        if r['status'] == 'browser_only':
            print(f"   ◐ [يُفحص بالمتصفح] {r['url'][:58]}")
        elif r['status'] != 'saved':
            print(f"   ✘ [{r['status']}] {r['url'][:64]} → {r.get('error','')[:60]}")
    (d / 'status.json').write_text(json.dumps({
        'date': day, 'status': status, 'checked': len(recs), 'healthy': healthy,
        'empty_shell': shells, 'failed': failed, 'browser_only': browser,
        'min_text_chars': MIN_TEXT_CHARS,
        'urls_not_proven': [r['url'] for r in recs if r['status'] != 'saved'],
        'written_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }, ensure_ascii=False, indent=1), encoding='utf-8')
    return {'ok': 0, 'degraded': 1, 'failed': 2}[status]


if __name__ == '__main__':
    raise SystemExit(main())