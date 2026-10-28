#!/usr/bin/env python3
"""فحص مفتاح Claude: الكتالوج + هوية المنظمة + توليد فعلي — دون كشف المفتاح.

يقرأ المفتاح من البيئة بالترتيب: ANTHROPIC_CLAUDE_KEY ثم ANTHROPIC_API_KEY.
الاستخدام: python3 tools/claude_check.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = (os.environ.get('ANTHROPIC_API_BASE') or 'https://api.anthropic.com').rstrip('/')
CANDIDATES = ('ANTHROPIC_CLAUDE_KEY', 'ANTHROPIC_API_KEY')


def pick_key():
    for name in CANDIDATES:
        v = os.environ.get(name)
        if v:
            return name, v
    return None, None


def mask(k):
    return f'{k[:14]}…{k[-6:]} (الطول {len(k)})'


def main():
    name, key = pick_key()
    if not key:
        print('  ✘ لا مفتاح Claude في البيئة (لا ANTHROPIC_CLAUDE_KEY ولا ANTHROPIC_API_KEY)')
        return 2
    print(f'  · المتغير المستخدم: {name}')
    print(f'  · المفتاح: {mask(key)}')

    # 1) الكتالوج + هوية المنظمة
    req = urllib.request.Request(f'{BASE}/v1/models',
                                 headers={'x-api-key': key, 'anthropic-version': '2023-06-01'})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            hdrs = {k.lower(): v for k, v in r.headers.items()}
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f'  ✘ فشل الكتالوج: {e.code} — {e.read().decode()[:200]}')
        return 1
    ids = [m['id'] for m in data.get('data', [])]
    print(f'  ✔ الكتالوج: {len(ids)} نموذجاً')
    print(f'  · معرّف المنظمة: {hdrs.get("anthropic-organization-id", "—")}')
    print('  · نماذج:', ', '.join(ids[:6]))

    # 2) توليد فعلي على نموذجين
    ok = False
    for model in ids[:2]:
        body = json.dumps({'model': model, 'max_tokens': 64,
                           'messages': [{'role': 'user', 'content': 'أجب بجملة واحدة قصيرة: هل الاتصال يعمل؟'}]}).encode()
        rq = urllib.request.Request(f'{BASE}/v1/messages', data=body,
                                    headers={'x-api-key': key, 'anthropic-version': '2023-06-01',
                                             'content-type': 'application/json'})
        try:
            with urllib.request.urlopen(rq, timeout=60) as r:
                d = json.loads(r.read())
                txt = ''.join(b.get('text', '') for b in d.get('content', []))
                print(f'  ✔ توليد ناجح عبر {model}: «{txt.strip()[:70]}»')
                ok = True
        except urllib.error.HTTPError as e:
            rid = e.headers.get('request-id') or '—'
            print(f'  ✘ توليد فاشل عبر {model}: {e.code} — {e.read().decode()[:180]} · معرّف الطلب: {rid}')
        except Exception as e:
            print(f'  ✘ توليد فاشل عبر {model}: {type(e).__name__} — {str(e)[:120]}')
    print('  ── النتيجة:', 'التوليد يعمل ✔' if ok else 'التوليد لا يعمل ✘')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())