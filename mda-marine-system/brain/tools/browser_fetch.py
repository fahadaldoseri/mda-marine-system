#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مسار المتصفح الثابت — يجلب مصدرًا محجوبًا على الطلب الآلي عبر Chromium حقيقي.

السبب المقيس: USNI News تُعيد 403 على `urllib` (تحدي Cloudflare)، والمتصفح المجرَّد
يستقبل التحدي أحيانًا (403 · 28KB). الحل الحتمي المقيس: **Chromium مرئي على شاشة
افتراضية Xvfb** + ملف تعريف دائم + تسخين الجذر، ثم طلب التغذية بالكوكيز.

القياس: `مسار المتصفح: HTTP 200 · 507228B` بلا تحدي.

الواجهة:
    fetch_via_browser(url, timeout=60, warmup=True, attempts=2) -> (payload | None, note)
لا يُبتلع أي خطأ: كل فشل يُعاد كنصّ صريح مقيس في note.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
CHALLENGE_MARKS = ('just a moment', 'checking your browser', 'cf-chl', 'attention required')
DISPLAY = ':99'
# قفل: ملف التعريف الدائم لا يقبل جلستين متزامنتين، والفحص يعمل بخيوط متوازية.
_BROWSER_LOCK = threading.Lock()


def _ensure_display() -> str | None:
    """يشغّل Xvfb على :99 إن لم يكن قائمًا، ويعيد قيمة DISPLAY أو None عند التعذّر."""
    if Path(f'/tmp/.X11-unix/X{DISPLAY.lstrip(":")}').exists():
        return DISPLAY
    if not _which('Xvfb'):
        return None
    try:
        subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', '1366x900x24'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except (OSError, ValueError) as exc:  # فشل تشغيل خفي: نعود بلا شاشة
        print(f'   تنبيه: تعذّر تشغيل Xvfb — {exc}', file=sys.stderr)
        return None
    for _ in range(20):
        time.sleep(0.4)
        if Path(f'/tmp/.X11-unix/X{DISPLAY.lstrip(":")}').exists():
            return DISPLAY
    return None


def _which(name: str) -> str | None:
    for folder in os.environ.get('PATH', '').split(os.pathsep):
        candidate = Path(folder) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _challenged(status: int, text: str) -> bool:
    low = text[:4000].lower()
    return status in (403, 429, 503) or any(m in low for m in CHALLENGE_MARKS)


try:
    from playwright.sync_api import Error as _PWError
except ImportError:  # بلا playwright: المسار يُبلّغ بالتعذّر لاحقًا
    class _PWError(Exception):
        pass


def _attempt(playwright, url: str, timeout: int, warmup: bool, headful: bool):
    profile = Path(os.environ.get('BROWSER_FETCH_PROFILE',
                                  f'/home/ubuntu/.cache/browser-fetch-{"headful" if headful else "headless"}'))
    profile.mkdir(parents=True, exist_ok=True)
    env = {**os.environ}
    if headful:
        display = _ensure_display()
        if not display:
            return None, 'مسار المتصفح: لا شاشة افتراضية (Xvfb غير متاح)'
        env['DISPLAY'] = display
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile), headless=not headful,
        user_agent=UA, locale='en-US', viewport={'width': 1366, 'height': 900},
        env=env, args=['--disable-blink-features=AutomationControlled', '--no-sandbox'])
    try:
        page = context.pages[0] if context.pages else context.new_page()
        origin = f'{urlparse(url).scheme}://{urlparse(url).netloc}/'
        if warmup:
            try:
                page.goto(origin, wait_until='domcontentloaded', timeout=timeout * 1000)
                page.wait_for_timeout(6000)  # ليُحلّ التحدي ويُكتب cf_clearance
            except _PWError as exc:      # تحدي أو مهلة في التسخين: نتابع إلى الطلب الأصل
                print(f'   ملاحظة: تسخين الصفحة لم يكتمل — {type(exc).__name__}', file=sys.stderr)
        response = page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)
        status = response.status if response else 0
        page.wait_for_timeout(4000)
        text = page.content()
        try:
            body = page.locator('body').inner_text(timeout=5000)
        except _PWError:                 # لا نص مرئي في الصفحة: نكتفي بمحتوى HTML
            body = ''
        if body and ('<?xml' in body or body.lstrip().startswith('{')):
            text = body
        payload = text.encode('utf-8')
        if not _challenged(status, text) and len(payload) >= 500:
            return payload, f'HTTP {status} · {len(payload)}B'
        return None, f'HTTP {status} · {len(payload)}B — تحدي قائم'
    finally:
        context.close()


def fetch_via_browser(url: str, timeout: int = 60, warmup: bool = True, attempts: int = 2):
    started = time.time()
    try:
        from playwright.sync_api import sync_playwright
        from playwright.sync_api import Error as _PWError
    except ImportError as error:
        return None, f'مسار المتصفح غير متاح — {type(error).__name__}: {error}'

    notes = []
    try:
        with _BROWSER_LOCK, sync_playwright() as p:
            for headful in (True, False):          # المرئي أولًا: هو الذي يجتاز التحدي
                for index in range(max(1, (attempts + 1) if headful else 1)):
                    payload, note = _attempt(p, url, timeout, warmup, headful)
                    mode = 'مرئي' if headful else 'مجرَّد'
                    seconds = round(time.time() - started, 2)
                    notes.append(f'{mode}: {note}')
                    if payload is not None:
                        return payload, (f'مسار المتصفح ({mode}): {note} · '
                                         f'{seconds}s · محاولة {index + 1}')
                    if headful:
                        time.sleep(3)
    except (OSError, RuntimeError, TimeoutError, _PWError) as error:
        return None, f'مسار المتصفح فشل — {type(error).__name__}: {str(error)[:140]}'
    return None, 'مسار المتصفح: ' + ' | '.join(notes)


if __name__ == '__main__':
    import sys
    for target in sys.argv[1:]:
        data, note = fetch_via_browser(target)
        print(f'   {target}\n     {note}')
        if data:
            print(f'     أول 110 أحرف: {data[:110]!r}')