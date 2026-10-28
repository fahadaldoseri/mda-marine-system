#!/usr/bin/env python3
"""تدوير TELEGRAM_WEBHOOK_SECRET بأمان: توليد · تحديث المخزن · إعادة تسجيل الويب هوك · تحقق.
لا تُطبع أي قيمة سرية في أي مخرج — البصمات فقط.
الاستخدام: python3 tools/rotate_webhook_secret.py [--dry-run] [--skip-telegram]"""
import argparse, hashlib, json, os, re, secrets, sys, urllib.parse, urllib.request
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')
M = Path('/home/ubuntu/mda-marine-system')
ENV = B / 'secrets' / 'secrets.env'
STATE = B / 'state' / 'webhook-secret.txt'
KEY = 'TELEGRAM_WEBHOOK_SECRET'
TOKEN_KEY = 'TELEGRAM_BOT_TOKEN'


def fp(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()[:12]


def read_env(p: Path) -> dict:
    d = {}
    for line in p.read_text(encoding='utf-8').splitlines():
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line.strip())
        if m:
            d[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return d


def write_env(p: Path, d: dict):
    lines = []
    for k, v in d.items():
        lines.append(f'{k}={v}')
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    os.chmod(p, 0o600)


def api(token: str, method: str, params: dict | None = None):
    url = f'https://api.telegram.org/bot{token}/{method}'
    data = urllib.parse.urlencode(params).encode() if params else None
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        return {'ok': False, 'error': type(e).__name__, 'detail': str(e)[:120]}


def scan_old(root: Path, old: str) -> list[str]:
    hits = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in {'.git', '__pycache__', 'node_modules'}]
        for fn in fns:
            p = Path(dp) / fn
            if p.stat().st_size > 3_000_000 or p.suffix in {'.png', '.jpg', '.pdf', '.woff2', '.zip'}:
                continue
            try:
                if old in p.read_text(encoding='utf-8', errors='ignore'):
                    hits.append(str(p))
            except OSError:
                continue
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--skip-telegram', action='store_true')
    a = ap.parse_args()

    env = read_env(ENV)
    old = env.get(KEY) or (STATE.read_text(encoding='utf-8').strip() if STATE.exists() else '')
    token = env.get(TOKEN_KEY, '')
    if not old:
        raise SystemExit('✘ لا توجد قيمة قديمة للتدوير')
    print(f'  القيمة القديمة: طول={len(old)} · بصمة={fp(old)}')

    info = api(token, 'getWebhookInfo') if token else {'ok': False, 'error': 'NO_TOKEN'}
    url = (info.get('result') or {}).get('url', '') if info.get('ok') else ''
    print(f'  الويب هوك الحالي: {"مُسجَّل" if url else "غير مُسجَّل"} · استجابة_API={"ok" if info.get("ok") else info.get("error")} · '
          f'تحديثات معلّقة={(info.get("result") or {}).get("pending_update_count")}')

    new = secrets.token_urlsafe(32)
    print(f'  القيمة الجديدة: طول={len(new)} · بصمة={fp(new)}')

    if not a.skip_telegram and token and url:
        res = api(token, 'setWebhook', {'url': url, 'secret_token': new, 'drop_pending_updates': 'false'})
        print(f'  إعادة تسجيل الويب هوك بالسرّ الجديد: {"✔ نجح" if res.get("ok") else "✘ فشل — " + str(res.get("detail") or res.get("description"))}')
        if not res.get('ok'):
            raise SystemExit('✘ أُوقِف التدوير: لم تُحدَّث الجهة الخارجية، فلا تُغيَّر القيمة محليًا')
        chk = api(token, 'getWebhookInfo')
        print(f'  تحقق بعد التسجيل: {"ok" if chk.get("ok") else "فشل"} · رابط محفوظ={bool((chk.get("result") or {}).get("url"))}')
    elif a.skip_telegram:
        print('  تخطّي تلغرام بطلب صريح (يُبقى التسجيل القديم)')
    else:
        print('  لا ويب هوك مُسجَّل: التدوير محلي فقط')

    if a.dry_run:
        print('  تجربة فقط — لم يُكتب شيء')
        return 0

    env[KEY] = new
    write_env(ENV, env)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(new + '\n', encoding='utf-8')
    os.chmod(STATE, 0o600)

    hits_b = scan_old(B, old)
    hits_m = scan_old(M, old)
    print(f'  أثر القيمة القديمة: في الدماغ={len(hits_b)} · في المرآة={len(hits_m)}')
    for h in (hits_b + hits_m)[:6]:
        print(f'   باقٍ في: {h}')
    env2 = read_env(ENV)
    print(f'  المخزن الآن يحمل القيمة الجديدة؟ {fp(env2.get(KEY, "")) == fp(new)} · ملف الحالة؟ {fp(STATE.read_text(encoding="utf-8").strip()) == fp(new)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())