#!/usr/bin/env python3
"""معالج أوامر بوت تلغرام — مركز الوعي بالمجال البحري.

المبدأ الحاكم: لا يُقبل أي مشترك إلا بموافقة صاحب القرار.
- من يضغط Start أو يضيف البوت: يُسجَّل «قيد الانتظار» فقط، ويُبلَّغ صاحب القرار.
- صاحب القرار يوافق بأمر /approve <المعرّف> أو يرفض بـ /deny <المعرّف>.
- لا يُرسَل أي تقرير لجهة غير معتمدة.

التشغيل:
    python3 tools/telegram_bot.py --once      # دورة واحدة (مناسبة للمؤقت أو الويب هوك)
    python3 tools/telegram_bot.py             # استمرار بالاستقصاء الطويل
"""
from __future__ import annotations
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

B = Path(__file__).resolve().parents[1]
STATE = B / "state" / "telegram-offset.json"
SUBS = B / "appendices" / "telegram-subscriptions.json"
TARGETS = B / "appendices" / "telegram-targets.json"
LOG = B / "logs" / "telegram-bot.log"
SITE = "https://mda-bh.pages.dev"


def token() -> str:
    t = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if t:
        return t
    cfg = Path("/home/ubuntu/.manus/config/config.json")
    if cfg.exists():
        m = re.search(r"\d{8,10}:[A-Za-z0-9_-]{30,}", cfg.read_text(encoding="utf-8"))
        if m:
            return m.group(0)
    raise SystemExit("لا يوجد رمز بوت في البيئة")


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{stamp} {msg}\n")
    print(f"  {msg}")


def api(method: str, payload: dict | None = None, tok: str = "") -> dict:
    url = f"https://api.telegram.org/bot{tok}/{method}"
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=35))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.read().decode()[:200]}
    except Exception as e:  # شبكة
        return {"ok": False, "error": str(e)[:200]}


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def owner_id() -> str:
    for t in load_json(TARGETS, {"targets": []})["targets"]:
        if t.get("type") == "private" and t.get("enabled"):
            return str(t.get("chat_id") or "")
    return ""


def subs() -> dict:
    return load_json(SUBS, {"approved": [], "pending": [], "denied": [], "note": ""})


def is_approved(cid: str, s: dict) -> bool:
    return any(str(x.get("chat_id")) == str(cid) for x in s.get("approved", []))


def latest_report() -> dict:
    metas = sorted((B / "web" / "meta").glob("*.json"))
    if not metas:
        return {}
    return load_json(metas[-1], {})


def cmd_report(tok: str, chat: str) -> None:
    m = latest_report()
    if not m:
        api("sendMessage", {"chat_id": chat, "text": "لا يوجد إصدار منشور بعد."}, tok)
        return
    d = m.get("date", "")
    txt = (f"<b>{m.get('title', 'التقرير اليومي لأمن الملاحة والأوضاع الراهنة في المنطقة')}</b>\n"
           f"تاريخ الإصدار: {d}\n"
           f"<a href=\"{SITE}/reports/{d}.html\">التقرير الكامل</a>")
    api("sendMessage", {"chat_id": chat, "text": txt, "parse_mode": "HTML",
                        "disable_web_page_preview": False}, tok)


def cmd_pdf(tok: str, chat: str) -> None:
    pair = sorted(Path(f"{SITE}/dist/reports/pdf").glob("*.pdf"))
    if not pair:
        api("sendMessage", {"chat_id": chat, "text": "لا توجد نسخة PDF منشورة بعد."}, tok)
        return
    p = pair[-1]
    api("sendDocument", {"chat_id": chat, "document": f"{SITE}/reports/pdf/{p.name}",
                         "caption": f"نسخة PDF — {p.stem}"}, tok)


def handle(tok: str, upd: dict) -> None:
    msg = upd.get("message") or upd.get("channel_post") or {}
    chat = msg.get("chat", {})
    cid = str(chat.get("id", ""))
    text = (msg.get("text") or "").strip()
    if not cid or not text:
        return
    who = " ".join(x for x in [chat.get("title"), chat.get("first_name"), chat.get("last_name")] if x)
    uname = chat.get("username", "")
    own = owner_id()
    s = subs()
    low = text.lower()

    if low.startswith("/approve") or low.startswith("/deny"):
        if cid != own:
            api("sendMessage", {"chat_id": cid, "text": "هذا الأمر لصاحب القرار فقط."}, tok)
            return
        parts = text.split()
        if len(parts) < 2:
            api("sendMessage", {"chat_id": own, "text": "الصيغة: /approve <المعرّف> أو /deny <المعرّف>"}, tok)
            return
        tgt = parts[1].strip()
        pend = [p for p in s["pending"] if str(p.get("chat_id")) == tgt]
        s["pending"] = [p for p in s["pending"] if str(p.get("chat_id")) != tgt]
        if low.startswith("/approve"):
            entry = pend[0] if pend else {"chat_id": tgt, "label": "جهة من القائمة", "type": "unknown"}
            entry["approved_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
            s["approved"].append(entry)
            save_json(SUBS, s)
            api("sendMessage", {"chat_id": tgt, "text": "تم اعتماد اشتراكك. سيصلك التقرير اليومي في 06:40 بتوقيت البحرين."}, tok)
            api("sendMessage", {"chat_id": own, "text": f"تم اعتماد الجهة {tgt} ✓"}, tok)
            log(f"اعتماد جهة {tgt}")
        else:
            s["denied"].append({"chat_id": tgt, "denied_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")})
            save_json(SUBS, s)
            api("sendMessage", {"chat_id": own, "text": f"تم رفض الجهة {tgt}."}, tok)
            log(f"رفض جهة {tgt}")
        return

    if low.startswith("/list"):
        if cid != own:
            api("sendMessage", {"chat_id": cid, "text": "هذا الأمر لصاحب القرار فقط."}, tok)
            return
        ap = "، ".join(f"{x.get('label') or 'جهة'} ({x['chat_id']})" for x in s.get("approved", [])) or "لا شيء"
        pd = "، ".join(f"{x.get('label') or 'جهة'} ({x['chat_id']})" for x in s.get("pending", [])) or "لا شيء"
        api("sendMessage", {"chat_id": own, "text": f"<b>المعتمدة:</b> {ap}\n<b>قيد الانتظار:</b> {pd}",
                            "parse_mode": "HTML"}, tok)
        return

    if low.startswith("/id"):
        api("sendMessage", {"chat_id": cid, "text": f"معرّف هذه المحادثة: {cid}"}, tok)
        return

    if low.startswith("/report"):
        if is_approved(cid, s) or cid == own:
            cmd_report(tok, cid)
        else:
            api("sendMessage", {"chat_id": cid, "text": "هذه القناة للتسليم التشغيلي، واشتراكك غير معتمد بعد."}, tok)
        return

    if low.startswith("/pdf"):
        if is_approved(cid, s) or cid == own:
            cmd_pdf(tok, cid)
        else:
            api("sendMessage", {"chat_id": cid, "text": "اشتراكك غير معتمد بعد."}, tok)
        return

    if low.startswith("/help"):
        api("sendMessage", {"chat_id": cid, "text":
            "الأوامر المتاحة:\n"
            "/start — التسجيل وطلب الاشتراك\n"
            "/report — رابط آخر تقرير منشور\n"
            "/pdf — نسخة PDF لآخر إصدار\n"
            "/id — معرّف هذه المحادثة\n"
            "/help — هذه القائمة"}, tok)
        return

    if low.startswith("/start"):
        if is_approved(cid, s) or cid == own:
            api("sendMessage", {"chat_id": cid, "text":
                "التسجيل قائم. يصلك التقرير اليومي في 06:40 بتوقيت البحرين، ويمكنك استخدام /report و /pdf."}, tok)
            return
        if any(str(p.get("chat_id")) == cid for p in s.get("pending", [])):
            api("sendMessage", {"chat_id": cid, "text": "طلبك مسجّل وبانتظار موافقة المركز."}, tok)
            return
        s["pending"].append({"chat_id": cid, "label": who or "جهة", "username": uname,
                             "type": chat.get("type", "private"),
                             "requested_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")})
        save_json(SUBS, s)
        api("sendMessage", {"chat_id": cid, "text":
            "سُجِّل طلبك. لا يُفعَّل الاشتراك إلا بموافقة المركز، وستُبلَّغ عند الاعتماد."}, tok)
        if own:
            api("sendMessage", {"chat_id": own, "parse_mode": "HTML", "text":
                "<b>طلب اشتراك جديد</b>\n"
                f"الجهة: {who or 'بدون اسم'} {('@'+uname) if uname else ''}\n"
                f"النوع: {chat.get('type','private')}\n"
                f"المعرّف: <code>{cid}</code>\n"
                f"للموافقة: /approve {cid}\nلت الرفض: /deny {cid}"}, tok)
        log(f"طلب اشتراك جديد {cid} ({who})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="دورة واحدة ثم خروج")
    args = ap.parse_args()
    tok = token()
    state = load_json(STATE, {"offset": 0})
    for _ in range(1 if args.once else 10**9):
        r = api("getUpdates", {"offset": state.get("offset", 0),
                               "timeout": 0 if args.once else 30,
                               "allowed_updates": ["message", "channel_post"]}, tok)
        if not r.get("ok"):
            log(f"خطأ من تلغرام: {str(r.get('error'))[:120]}")
            time.sleep(5)
            continue
        ups = r.get("result", [])
        for u in ups:
            state["offset"] = u["update_id"] + 1
            try:
                handle(tok, u)
            except Exception as e:
                log(f"خطأ في معالجة تحديث: {str(e)[:120]}")
        save_json(STATE, state)
        if args.once:
            break
        if not ups:
            time.sleep(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())