#!/usr/bin/env bash
# ك-588: قراءة مبتورة/إغلاق اتصال في جلب مصدرين أوقفا بوابة اكتمال التشغيل G033.
# الإصلاح الجذري: مسار احتياطي بـ curl داخل دالة الجلب نفسها (لا قائمة مصادر متساهلة)،
# ثم إعادة القياس، ثم تسجيل العطل وتثبيت الحزمة.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) إضافة مسار curl الاحتياطي ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('tools/check_feeds.py')
t = p.read_text(encoding='utf-8')
if 'def _try_curl(' not in t:
    helper = '''

def _try_curl(url: str) -> tuple[bool, bytes, str]:
    """مسار احتياطي محكوم: curl يقرأ كامل الجسم ويتعامل مع القراءة المبتورة وإغلاق الاتصال.

    لا يتجاوز حجبًا: صفحة تحقق بشري أو رمز رفض (401/403/405/429) تُعاد كما هي ليُصنَّف العطل.
    """
    cmd = [
        'curl', '-sS', '-L', '--compressed', '--max-time', '40',
        '--write-out', '\\n%{http_code}',
        '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        url,
    ]
    try:
        done = subprocess.run(cmd, capture_output=True, timeout=60)
    except Exception as error:                       # noqa: BLE001
        return False, b'', f'curl تعذّر التنفيذ — {error}'
    body = done.stdout or b''
    if b'\\n' in body[-8:]:
        head, _, tail = body.rpartition(b'\\n')
        code_txt = tail.strip().decode('utf-8', 'replace')
        if code_txt.isdigit():
            body = head
            code = int(code_txt)
            if code in (401, 403, 405, 429):
                blocked = _blocked_reason(body.decode('utf-8', 'replace')[:4000]) or 'رفض الخادم الطلب'
                return False, b'', f'حجب مصدر — {blocked} (HTTP {code})'
            if code >= 400:
                return False, b'', f'HTTP Error {code} عبر curl'
    if done.returncode != 0 and not body:
        return False, b'', f'curl رمز {done.returncode}'
    return True, body, 'curl'
'''
    anchor = '\n\ndef _routes_for('
    t = t.replace(anchor, helper + anchor, 1)
old_except = '''            attempts.append({
                'url': route['url'], 'via': route['via'], 'ok': False,
                'error': message, 'tls_verification': tls_verification,
            })'''
new_except = '''            # مسار احتياطي: قراءة مبتورة أو إغلاق اتصال في urllib لا يعني عطلًا نهائيًا.
            if 'حجب مصدر' not in message:
                ok_curl, payload_c, note_c = _try_curl(route['url'])
                if ok_curl:
                    items, content_chars = _payload_items(payload_c, route['url'])
                    if items:
                        attempts.append({
                            'url': route['url'], 'via': f"{route['via']}+curl", 'ok': True,
                            'items_count': len(items), 'content_chars': content_chars,
                            'tls_verification': tls_verification,
                        })
                        return {
                            **f, 'ok': True, 'items': items, 'items_count': len(items),
                            'content_chars': content_chars, 'via': f"{route['via']}+curl",
                            'fetched_url': route['url'], 'attempts': attempts,
                            'tls_verification': tls_verification,
                        }
                    message = f'{message} · curl أعاد محتوى غير مقروء'
                else:
                    message = f'{message} · {note_c}'
            attempts.append({
                'url': route['url'], 'via': route['via'], 'ok': False,
                'error': message, 'tls_verification': tls_verification,
            })'''
if old_except in t:
    t = t.replace(old_except, new_except, 1)
if 'import subprocess' not in t:
    t = t.replace('import urllib.request', 'import subprocess\nimport urllib.request', 1)
p.write_text(t, encoding='utf-8')
print('   ✔ أُضيف المسار الاحتياطي وفحص الصياغة')
PY
python3 -c "import ast,pathlib;ast.parse(pathlib.Path('tools/check_feeds.py').read_text(encoding='utf-8'));print('   ✔ صياغة سليمة')"

echo "   ═══ 2) قياس المسارين الفاشلين عبر curl مباشرة ═══"
for U in "https://t.me/army21ye" "https://x.com/Yemenarmyeng"; do
  printf "   %-32s" "$U"
  code=$(curl -sS -L --compressed --max-time 40 -o /tmp/c.body -w '%{http_code}' -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36' "$U" 2>/tmp/c.err || echo ERR)
  echo "HTTP=$code · بايت=$(wc -c < /tmp/c.body 2>/dev/null || echo 0) · $(head -c 90 /tmp/c.err | tr -d '\n')"
done

echo "   ═══ 3) إعادة تشغيل فاحص التغذيات ═══"
timeout 900 python3 tools/check_feeds.py --date "$D" > /tmp/feeds2.txt 2>&1
echo "   rc=$?"
grep -E "نجح:|✘|الحالة:" /tmp/feeds2.txt | tail -8 | cut -c1-190 | sed 's/^/   /'