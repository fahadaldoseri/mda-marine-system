#!/usr/bin/env python3
"""فحص مفاتيح الواجهات البرمجية: وجودها وصلاحية مصادقتها وحالة الرصيد.

لا يطبع أي مفتاح — يطبع الطول وأول 7 أحرف فقط.
الاستخدام:
    python3 tools/check_api_keys.py            # فحص مصادقة فقط (بلا كلفة)
    python3 tools/check_api_keys.py --deep     # فحص إضافي لحالة الرصيد
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT = 25


def mask(value: str) -> str:
    return f"{value[:7]}… ({len(value)} حرفًا)"


def http(url: str, headers: dict[str, str], data: bytes | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers, data=data, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def check_anthropic(deep: bool) -> bool:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    print("── Anthropic")
    if not key:
        print("   ✘ ANTHROPIC_API_KEY غير موجود في هذه الجلسة")
        return False
    print(f"   · المفتاح: {mask(key)}")
    status, body = http(
        "https://api.anthropic.com/v1/models",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    if status != 200:
        print(f"   ✘ فشل فحص المصادقة · الحالة {status} · {body[:160]}")
        return False
    models = [m["id"] for m in json.loads(body).get("data", [])]
    print(f"   ✔ المصادقة سليمة · {len(models)} نموذجًا متاحًا · نماذج: {', '.join(models[:3]) or '—'}")
    if not deep:
        return True
    payload = json.dumps(
        {"model": "claude-haiku-5-5", "max_tokens": 8, "messages": [{"role": "user", "content": "تم"}]}
    ).encode()
    status, body = http(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        payload,
    )
    if status == 200:
        usage = json.loads(body).get("usage", {})
        print(f"   ✔ النداء الفعلي نجح · دخل {usage.get('input_tokens')} · خرج {usage.get('output_tokens')}")
        return True
    print(f"   ✘ النداء الفعلي فشل · الحالة {status}")
    if "credit balance" in body:
        print("   ⚠ السبب: رصيد الحساب منخفض — يلزم شحن رصيد أو مفتاح من حساب آخر")
    else:
        print(f"   ⚠ {body[:200]}")
    return False


def check_openai(deep: bool) -> bool:
    key = os.environ.get("OPENAI_API_KEY", "")
    print("── OpenAI")
    if not key:
        print("   ✘ OPENAI_API_KEY غير موجود")
        return False
    print(f"   · المفتاح: {mask(key)}")
    base = (os.environ.get("OPENAI_API_BASE") or "https://api.openai.com/v1").rstrip("/")
    if not base.startswith("http"):
        base = "https://api.openai.com/v1"
    status, body = http(f"{base}/models", {"Authorization": f"Bearer {key}"})
    if status != 200:
        print(f"   ✘ فشل فحص المصادقة · الحالة {status} · {body[:160]}")
        return False
    count = len(json.loads(body).get("data", []))
    print(f"   ✔ المصادقة سليمة · {count} نموذجًا متاحًا")
    return True


def main() -> int:
    deep = "--deep" in sys.argv
    print("===== فحص مفاتيح الواجهات =====")
    a = check_anthropic(deep)
    print()
    o = check_openai(deep)
    print()
    if not deep:
        print("ملاحظة: هذا فحص مصادقة بلا كلفة. لفحص الرصيد: --deep")
    return 0 if (a or o) else 1


if __name__ == "__main__":
    raise SystemExit(main())
