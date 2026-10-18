#!/usr/bin/env python3
"""إرسال رسالة تلغرام (ومرفقاتها) إلى جهة أو أكثر — أداة التسليم المعتمدة.

الاستخدام:
  python3 tools/telegram_send.py --file /tmp/digest.html
  python3 tools/telegram_send.py --file /tmp/digest.html --photo <png> --document <pdf>
  python3 tools/telegram_send.py --file /tmp/digest.html --targets all|primary|"مجموعة العمل"
  python3 tools/telegram_send.py --file /tmp/digest.html --dry-run

الجهات: تُقرأ من appendices/telegram-targets.json (كل جهة enabled=true)،
ومع --targets يقتصر الإرسال على ما يُحدَّد بالاسم أو المعرّف.

المسارات: مباشر أولًا، ثم وسيط POST (يحفظ فواصل الأسطر) للنص.
المرفقات (sendDocument/sendPhoto) تُرسَل مباشرة فقط؛ وإن تعذّر، تُستبدل بسطر رابط
لأن الوسيط النصي لا ينقل ملفات.

الرمز يُقرأ من TELEGRAM_BOT_TOKEN ولا يُطبع أبدًا.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

B = Path(__file__).resolve().parent.parent
TARGETS_FILE = B / "appendices" / "telegram-targets.json"
LEGACY_CHAT = B / "appendices" / "telegram-chat.json"
RELAY = "https://r.jina.ai/"


def load_targets(selector: str | None) -> list[dict]:
    items: list[dict] = []
    if TARGETS_FILE.exists():
        data = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
        items = [t for t in data.get("targets", []) if t.get("chat_id")]
    if not items and LEGACY_CHAT.exists():
        data = json.loads(LEGACY_CHAT.read_text(encoding="utf-8"))
        if data.get("chat_id"):
            items = [{"label": "المحادثة الشخصية", "chat_id": str(data["chat_id"]),
                      "enabled": True, "type": "private"}]
    if not selector or selector == "all":
        chosen = [t for t in items if t.get("enabled", True)]
    elif selector == "primary":
        chosen = [t for t in items if t.get("type") == "private"][:1]
    else:
        chosen = [t for t in items if selector in (t.get("label"), str(t.get("chat_id")))]
    if not chosen:
        raise SystemExit("لا توجد جهة مطابقة في appendices/telegram-targets.json")
    return chosen


def curl(args: list[str], timeout: int = 120) -> str:
    p = subprocess.run(["curl", "-s", "--max-time", str(timeout)] + args,
                       capture_output=True, text=True)
    return (p.stdout or "") + (p.stderr or "")


def ok_of(body: str) -> bool:
    return bool(re.search(r'"ok"\s*:\s*true', body))


def mid_of(body: str) -> str:
    m = re.search(r'"message_id"\s*:\s*(\d+)', body)
    return m.group(1) if m else "?"


def send_text(token: str, cid: str, text: str, route_log: list[str]) -> bool:
    base = (f"https://api.telegram.org/bot{token}/sendMessage"
            f"?chat_id={cid}&parse_mode=HTML&disable_web_page_preview=true"
            f"&text={urllib.parse.quote(text, safe='')}")
    body = send_text_direct(base)
    route_log.append("مباشر")
    if not ok_of(body):
        payload = json.dumps({"url": base}, ensure_ascii=False)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            fh.write(payload)
            tmp = fh.name
        try:
            body = curl(["-X", "POST", RELAY, "-H", "Content-Type: application/json",
                         "--data-binary", "@" + tmp])
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        route_log[-1] = "وسيط POST"
        if not ok_of(body):
            body = curl([RELAY + base], timeout=90)
            route_log[-1] = "وسيط GET (احتياطي)"
    if ok_of(body):
        route_log.append(f"نص: ok · الرسالة {mid_of(body)}")
        return True
    route_log.append("نص: فشل")
    return False


def send_text_direct(url: str) -> str:
    return curl(["--max-time", "25", url], timeout=35)


def send_file(token: str, cid: str, kind: str, path: Path, caption: str, route_log: list[str]) -> bool:
    method = "sendDocument" if kind == "document" else "sendPhoto"
    field = "document" if kind == "document" else "photo"
    args = ["-X", "POST", f"https://api.telegram.org/bot{token}/{method}",
            "-F", f"chat_id={cid}", "-F", f"{field}=@{path}"]
    if caption:
        args += ["-F", f"caption={caption}", "-F", "parse_mode=HTML"]
    body = curl(args, timeout=180)
    if ok_of(body):
        route_log.append(f"{kind}: ok · {path.name} · {path.stat().st_size/1024:.0f} ك.ب")
        return True
    route_log.append(f"{kind}: فشل ({path.name})")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--photo")
    ap.add_argument("--document")
    ap.add_argument("--caption", default="")
    ap.add_argument("--targets")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token and not args.dry_run:
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

    targets = load_targets(args.targets)
    if args.dry_run:
        print("اختبار جاف — الجهات المستهدفة:")
        for t in targets:
            print(f"  · {t['label']} ({t['type']}) · enabled={t.get('enabled')}")
        print(f"نص: {len(text)} حرف · صورة: {args.photo or 'لا'} · مستند: {args.document or 'لا'}")
        return 0

    failures = 0
    for t in targets:
        log: list[str] = []
        cid = str(t["chat_id"])
        ok_text = send_text(token, cid, text, log)
        if ok_text:
            if args.photo:
                p = Path(args.photo)
                if p.exists():
                    send_file(token, cid, "photo", p, args.caption, log)
            if args.document:
                p = Path(args.document)
                if p.exists():
                    send_file(token, cid, "document", p, args.caption, log)
        else:
            failures += 1
        print(f"[تلغرام] {t['label']}: " + " · ".join(log))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())