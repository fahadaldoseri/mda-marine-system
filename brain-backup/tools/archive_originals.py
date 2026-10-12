#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يحفظ نسخة الأصل الرسمي: HTML/PDF + بصمة sha256 + بيان manifest.json."""
import hashlib, json, sys, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'}

def grab(url, day):
    d = Path('/home/ubuntu/brain-marine-news/archive/originals') / day
    d.mkdir(parents=True, exist_ok=True)
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40)
        body = r.read(); ct = r.headers.get('Content-Type', '')
        ext = '.pdf' if 'pdf' in ct.lower() else '.html'
        name = hashlib.sha256(url.encode()).hexdigest()[:12] + ext
        (d / name).write_bytes(body)
        return {'url': url, 'utc': dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z', 'file': name,
                'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'content_type': ct, 'status': 'saved'}
    except Exception as e:
        return {'url': url, 'utc': dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
                'status': 'failed', 'error': str(e)[:110]}

def main():
    day = sys.argv[1]
    urls = [u.strip() for u in Path(sys.argv[2]).read_text(encoding='utf-8').splitlines() if u.strip().startswith('http')]
    with ThreadPoolExecutor(max_workers=6) as ex:
        recs = list(ex.map(lambda u: grab(u, day), urls))
    d = Path('/home/ubuntu/brain-marine-news/archive/originals') / day
    (d / 'manifest.json').write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding='utf-8')
    ok = sum(1 for r in recs if r['status'] == 'saved')
    print(f"  أصول محفوظة: {ok}/{len(urls)} · البيان: {d/'manifest.json'}")
    for r in recs:
        if r['status'] != 'saved':
            print(f"   ✘ {r['url'][:70]} → {r.get('error','')[:70]}")

if __name__ == '__main__':
    main()
