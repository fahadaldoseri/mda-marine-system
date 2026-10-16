#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
جلب أصل رسمي وحفظه خامًا مع بصمة SHA-256 ووقت الالتقاط (UTC) + استخراج نصه للاقتباس.
الاستخدام:
  python3 tools/fetch_primary.py --day 2026-10-16 --id ukmto-recent --url "https://www.ukmto.org/recent-incidents"
  python3 tools/fetch_primary.py --day 2026-10-16 --batch urls.txt
سطر الملف: <المعرّف>|<الرابط>
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import urllib.request
from pathlib import Path

BASE = Path('/home/ubuntu/brain-marine-news/archive/originals')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/124 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/pdf,*/*',
      'Accept-Language': 'en-US,en;q=0.9'}


def text_of(body, ctype):
    if 'pdf' in ctype.lower():
        return ''
    try:
        s = body.decode('utf-8', 'ignore')
    except Exception:
        return ''
    s = re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', s)
    s = re.sub(r'(?s)<[^>]+>', ' ', s)
    s = re.sub(r'&nbsp;?', ' ', s)
    s = re.sub(r'&amp;', '&', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def grab(day, ident, url):
    d = BASE / day
    d.mkdir(parents=True, exist_ok=True)
    rec = {'id': ident, 'url': url, 'retrieved_utc': dt.datetime.now(dt.timezone.utc)
           .isoformat(timespec='seconds').replace('+00:00', 'Z')}
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45)
        body = r.read()
        ctype = r.headers.get('Content-Type', '')
        ext = '.pdf' if 'pdf' in ctype.lower() else '.html'
        name = f"{ident}{ext}"
        (d / name).write_bytes(body)
        txt = text_of(body, ctype)
        if txt:
            (d / f"{ident}.txt").write_text(txt, encoding='utf-8')
        rec.update({'status': 'saved', 'file': name, 'bytes': len(body),
                    'sha256': hashlib.sha256(body).hexdigest(),
                    'content_type': ctype.split(';')[0],
                    'http_status': getattr(r, 'status', 200),
                    'text_chars': len(txt)})
    except Exception as e:
        rec.update({'status': 'failed', 'error': str(e)[:160]})
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--day', required=True)
    ap.add_argument('--id')
    ap.add_argument('--url')
    ap.add_argument('--batch')
    a = ap.parse_args()
    items = []
    if a.batch:
        for line in Path(a.batch).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '|' in line:
                i, u = line.split('|', 1)
                items.append((i.strip(), u.strip()))
    if a.id and a.url:
        items.append((a.id, a.url))
    d = BASE / a.day
    d.mkdir(parents=True, exist_ok=True)
    mpath = d / 'manifest.json'
    recs = json.loads(mpath.read_text(encoding='utf-8')) if mpath.exists() else []
    known = {(r.get('id'), r.get('url')) for r in recs}
    for i, u in items:
        if (i, u) in known:
            print(f"  · موجود سابقًا: {i}")
            continue
        rec = grab(a.day, i, u)
        recs.append(rec)
        if rec['status'] == 'saved':
            print(f"  ✔ {i} · {rec['bytes']} بايت · sha256 {rec['sha256'][:16]} · نص {rec['text_chars']}")
        else:
            print(f"  ✘ {i} → {rec['error']}")
    mpath.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"  البيان: {mpath} · سجلات: {len(recs)}")


if __name__ == '__main__':
    main()