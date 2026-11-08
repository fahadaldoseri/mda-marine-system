#!/usr/bin/env python3
"""قياس تطابق ما يخدمه القارئ مع ملف البناء المحلي.

الاستخدام:
  python3 live_parity.py --url URL --local /path/file.html [--min-bytes 100000]

الفكرة: لا يُعلن النشر ناجحًا بالكود 200 وحده. يلزم كود 200 + نوع محتوى HTML
(للقناة التي تعرض HTML) + حدّ حجم أدنى + بصمة تطابق الملف المحلي.

رموز الخروج: 0 مطابق · 2 مختلف (حجم/محتوى/نوع) · 3 تعذّر الوصول.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request

UA = 'Mozilla/5.0 (compatible; seawatch-parity/1.0)'


def fetch(url: str, timeout: int) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), (r.headers.get('Content-Type') or '')
    except urllib.error.HTTPError as e:                     # 404/500 تُقاس لا تُخفى
        return e.code, e.read() or b'', (e.headers.get('Content-Type') or '')


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description='قياس تطابق قناة حية مع بناء محلي')
    ap.add_argument('--url', required=True, help='رابط القناة (بلا ترويسة أو بها)')
    ap.add_argument('--local', help='مسار الملف المحلي للمقارنة')
    ap.add_argument('--min-bytes', type=int, default=0, help='حد الحجم الأدنى بالبايت')
    ap.add_argument('--expect-html', action='store_true', help='يُلزم نوع محتوى HTML')
    ap.add_argument('--timeout', type=int, default=30)
    a = ap.parse_args()

    code, body, ctype = fetch(a.url, a.timeout)
    print(f'   الرابط: {a.url}')
    print(f'   الاستجابة: {code} · {len(body)} بايت · {ctype or "بلا نوع محتوى"}')

    if code != 200:
        print('   النتيجة: تعذّر الوصول — القناة لا تخدم المورد')
        return 3

    fails = []
    if a.min_bytes and len(body) < a.min_bytes:
        fails.append(f'الحجم {len(body)} < الحد {a.min_bytes}')
    if a.expect_html and 'html' not in ctype.lower():
        fails.append(f'نوع المحتوى ليس HTML: {ctype}')

    if a.local:
        local = open(a.local, 'rb').read()
        same = local == body
        print(f'   المحلي: {len(local)} بايت · بصمة {sha(local)[:32]}')
        print(f'   الحي  : {len(body)} بايت · بصمة {sha(body)[:32]}')
        if not same:
            if len(local) != len(body):
                fails.append('الحجم مختلف عن البناء المحلي')
            else:
                fails.append('المحتوى مختلف عن البناء المحلي بالبصمة')
    else:
        print(f'   بصمة الحي: {sha(body)[:32]}')

    verdict = 'مطابق' if not fails else 'مختلف'
    print(f'   النتيجة: {verdict}' + ('' if not fails else ' — ' + ' · '.join(fails)))
    return 0 if not fails else 2


if __name__ == '__main__':
    sys.exit(main())
