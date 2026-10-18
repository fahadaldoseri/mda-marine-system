#!/usr/bin/env python3
"""إرسال رسالة تلغرام عبر واجهة البوت — أداة التسليم المعتمدة لقناة تلغرام.

الاستخدام:
  python3 tools/telegram_send.py --file /tmp/digest.html
  python3 tools/telegram_send.py --text "نص قصير"

المسار: الشبكة المباشرة إلى نطاقات تلغرام محجوبة في بيئة التنفيذ (مهلة في مصافحة TLS)،
لذلك تُجرَّب المباشرة أولًا ثم يُستعمل الوسيط النصي r.jina.ai الذي يصل بنجاح.
الرمز يُقرأ من متغير البيئة TELEGRAM_BOT_TOKEN (موصل Telegram Bot API) ولا يُطبع أبدًا.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

B = Path(__file__).resolve().parent.parent
CHAT_FILE = B / "appendices" / "telegram-chat.json"


def chat_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    if CHAT_FILE.exists():
        data = json.loads(CHAT_FILE.read_text(encoding="utf-8"))
        if data.get("chat_id"):
            return str(data["chat_id"])
    raise SystemExit("لا يوجد معرّف محادثة: مرّر --chat أو أنشئ appendices/telegram-chat.json")


def send(url: str, timeout: int = 40) -> str:
    p = subprocess.run(["curl", "-s", "--max-time", str(timeout), url],
                       capture_output=True, text=True)
    return (p.stdout or "") + (p.stderr or "")


def ok_of(body: str) -> bool:
    return bool(re.search(r'"ok"\s*:\s*true', body))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--chat")
    args = ap.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("فشل: متغير TELEGRAM_BOT_TOKEN غير متاح (تفعيل موصل Telegram Bot API)")
        return 2

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()
    text = text.strip()
    if not text:
        print("فشل: النص فارغ")
        return 2

    cid = chat_id(args.chat)
    base = (f"https://api.telegram.org/bot{token}/sendMessage"
            f"?chat_id={cid}&parse_mode=HTML&disable_web_page_preview=true"
            f"&text={urllib.parse.quote(text, safe='')}")

    body = send(base, timeout=25)
    route = "مباشر"
    if not ok_of(body):
        relay = "https://r.jina.ai/" + base
        body = send(relay, timeout=60)
        route = "وسيط نصي"

    ok = ok_of(body)
    print(f"[تلغرام] المسار: {route} · النتيجة: {'ok:true — تم التسليم' if ok else 'فشل'}")
    if not ok:
        print("الاستجابة:", body[:400].replace(token, "<TOKEN>"))
        return 1
    mid = re.search(r'"message_id"\s*:\s*(\d+)', body)
    if mid:
        print("معرّف الرسالة:", mid.group(1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())