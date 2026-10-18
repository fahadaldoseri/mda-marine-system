#!/usr/bin/env python3
"""خدمة ويب هوك بوت تلغرام — مركز الوعي بالمجال البحري (MDA).

تُستقبل تحديثات تلغرام على POST /api/telegram/webhook، ويُتحقق من رأس سري.
المبدأ الحاكم: لا يُقبل أي مشترك إلا بموافقة صاحب القرار عبر الأمر /approve.
تُخزَّن الاشتراكات في قاعدة البيانات المُدارة (MySQL) لأن نظام ملفات الحاوية مؤقت.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pymysql

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
HOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
OWNER = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "").strip()
SITE = os.environ.get("SITE_ORIGIN", "https://seawatch-xp4qirmr.manus.space").rstrip("/")
PORT = int(os.environ.get("PORT", "3000"))

DDL = [
    """CREATE TABLE IF NOT EXISTS subscribers (
        chat_id     VARCHAR(32)  NOT NULL PRIMARY KEY,
        label       VARCHAR(190) NULL,
        username    VARCHAR(64)  NULL,
        chat_type   VARCHAR(24)  NULL,
        status      VARCHAR(16)  NOT NULL,
        requested_utc DATETIME   NULL,
        decided_utc   DATETIME   NULL,
        KEY status_idx (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bot_state (
        k VARCHAR(64) NOT NULL PRIMARY KEY,
        v VARCHAR(255) NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]


def dsn() -> dict:
    u = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    q = urllib.parse.parse_qs(u.query or "")
    return {"host": u.hostname, "port": u.port or 3306, "user": urllib.parse.unquote(u.username or ""),
            "password": urllib.parse.unquote(u.password or ""),
            "database": (u.path or "/").lstrip("/"), "ssl": q.get("ssl", ["preferred"])[0]}


def connect():
    c = dsn()
    kw: dict = dict(host=c["host"], port=c["port"], user=c["user"], password=c["password"],
                    database=c["database"], charset="utf8mb4", autocommit=True, connect_timeout=10)
    if c["ssl"] not in ("disable", "false", "0"):
        kw["ssl"] = {"ssl_context": ssl.create_default_context()} if c["ssl"] == "verify" else {"ssl": {}}
    return pymysql.connect(**kw)


def db():
    cn = connect()
    with cn.cursor() as cur:
        for stmt in DDL:
            cur.execute(stmt)
    return cn


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def tg(method: str, payload: dict) -> dict:
    if not TOKEN:
        return {"ok": False, "error": "no token"}
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}",
                                data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.read().decode()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def send(chat_id: str, text: str) -> None:
    tg("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                       "disable_web_page_preview": False})


def find(cn, chat_id: str):
    with cn.cursor() as cur:
        cur.execute("SELECT chat_id,label,username,chat_type,status FROM subscribers WHERE chat_id=%s", (chat_id,))
        return cur.fetchone()


def latest_report() -> dict:
    """آخر إصدار: ملف ثابت إن وُجد، وإلا يُستخرج من الصفحة الرئيسية."""
    try:
        with urllib.request.urlopen(f"{SITE}/last-report.json", timeout=10) as r:
            d = json.load(r)
            if d.get("date"):
                return d
    except Exception:
        pass
    try:
        with urllib.request.urlopen(f"{SITE}/", timeout=10) as r:
            html = r.read().decode("utf-8", "ignore")
        m = sorted(set(re.findall(r"/reports/(\d{4}-\d{2}-\d{2})\.html", html)))
        if m:
            return {"date": m[-1], "title": "التقرير اليومي لأمن الملاحة والأوضاع الراهنة في المنطقة"}
    except Exception:
        pass
    return {}


def handle_update(cn, upd: dict) -> None:
    msg = upd.get("message") or upd.get("channel_post") or {}
    chat = msg.get("chat") or {}
    cid = str(chat.get("id", ""))
    text = (msg.get("text") or "").strip()
    if not cid or not text:
        return
    low = text.lower()
    label = " ".join(x for x in (chat.get("title"), chat.get("first_name"), chat.get("last_name")) if x)
    uname = chat.get("username") or ""
    ctype = chat.get("type") or "private"
    row = find(cn, cid)
    status = row[4] if row else None
    is_owner = bool(OWNER) and cid == OWNER

    if low.startswith("/approve") or low.startswith("/deny"):
        if not is_owner:
            send(cid, "هذا الأمر لصاحب القرار فقط.")
            return
        parts = text.split()
        if len(parts) < 2:
            send(cid, "الصيغة: /approve &lt;المعرّف&gt; أو /deny &lt;المعرّف&gt;")
            return
        tgt = re.sub(r"\D", "", parts[1])
        st = "approved" if low.startswith("/approve") else "denied"
        with cn.cursor() as cur:
            cur.execute("UPDATE subscribers SET status=%s, decided_utc=%s WHERE chat_id=%s", (st, now(), tgt))
            if cur.rowcount == 0:
                cur.execute("INSERT INTO subscribers (chat_id,label,status,decided_utc) VALUES (%s,%s,%s,%s)",
                            (tgt, "جهة من القائمة", st, now()))
        if st == "approved":
            send(tgt, "تم اعتماد اشتراكك. يصلك التقرير اليومي في 07:00 بتوقيت البحرين.")
            send(cid, f"تم اعتماد الجهة {tgt} ✓")
        else:
            send(cid, f"تم رفض الجهة {tgt}.")
        return

    if low.startswith("/list"):
        if not is_owner:
            send(cid, "هذا الأمر لصاحب القرار فقط.")
            return
        with cn.cursor() as cur:
            cur.execute("SELECT label,chat_id,status FROM subscribers WHERE status IN ('approved','pending') ORDER BY status")
            rows = cur.fetchall()
        ap = "، ".join(f"{r[0] or 'جهة'} ({r[1]})" for r in rows if r[2] == "approved") or "لا شيء"
        pd = "، ".join(f"{r[0] or 'جهة'} ({r[1]})" for r in rows if r[2] == "pending") or "لا شيء"
        send(cid, f"<b>المعتمدة:</b> {ap}\n<b>قيد الانتظار:</b> {pd}")
        return

    if low.startswith("/id"):
        send(cid, f"معرّف هذه المحادثة: {cid}")
        return

    if low.startswith("/report") or low.startswith("/pdf"):
        if status != "approved" and not is_owner:
            send(cid, "هذه قناة تسليم تشغيلي، واشتراكك غير معتمد بعد.")
            return
        m = latest_report()
        if not m:
            send(cid, "لم يُنشَر إصدار بعد.")
            return
        d = m.get("date", "")
        if low.startswith("/pdf"):
            tg("sendDocument", {"chat_id": cid, "document": f"{SITE}/reports/pdf/{d}.pdf",
                                "caption": f"نسخة PDF — {d}"})
        else:
            send(cid, f"<b>{m.get('title','التقرير اليومي')}</b>\nتاريخ الإصدار: {d}\n"
                      f"<a href=\"{SITE}/reports/{d}.html\">التقرير الكامل</a>")
        return

    if low.startswith("/help"):
        send(cid, "الأوامر:\n/start — التسجيل وطلب الاشتراك\n/report — رابط آخر تقرير\n"
                  "/pdf — نسخة PDF لآخر إصدار\n/id — معرّف المحادثة\n/help — هذه القائمة")
        return

    if low.startswith("/start"):
        if status == "approved" or is_owner:
            send(cid, "التسجيل قائم. يصلك التقرير اليومي في 07:00 بتوقيت البحرين.")
            return
        if status == "pending":
            send(cid, "طلبك مسجّل وبانتظار موافقة المركز.")
            return
        with cn.cursor() as cur:
            cur.execute("INSERT INTO subscribers (chat_id,label,username,chat_type,status,requested_utc) "
                        "VALUES (%s,%s,%s,%s,'pending',%s) ON DUPLICATE KEY UPDATE label=VALUES(label), "
                        "username=VALUES(username), chat_type=VALUES(chat_type), status='pending', requested_utc=VALUES(requested_utc)",
                        (cid, label, uname, ctype, now()))
        send(cid, "سُجِّل طلبك. لا يُفعَّل الاشتراك إلا بموافقة المركز، وستُبلَّغ عند الاعتماد.")
        if OWNER:
            send(OWNER, "<b>طلب اشتراك جديد</b>\n"
                        f"الجهة: {label or 'بدون اسم'} {('@'+uname) if uname else ''}\n"
                        f"النوع: {ctype}\nالمعرّف: <code>{cid}</code>\n"
                        f"للموافقة: /approve {cid}\nللرفض: /deny {cid}")
        return


class Handler(BaseHTTPRequestHandler):
    server_version = "MDA-Bot/1.0"

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if path in ("/healthz", "/api/health"):
            try:
                cn = db()
                with cn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM subscribers WHERE status='approved'")
                    n = cur.fetchone()[0]
                cn.close()
                self._send(200, {"ok": True, "approved": n, "ts": now()})
            except Exception as e:
                self._send(503, {"ok": False, "error": str(e)[:200]})
            return
        self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if path != "/api/telegram/webhook":
            self._send(404, {"ok": False, "error": "not found"})
            return
        if HOOK_SECRET and self.headers.get("X-Telegram-Bot-Api-Secret-Token", "") != HOOK_SECRET:
            self._send(401, {"ok": False, "error": "unauthorized"})
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            upd = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            self._send(400, {"ok": False, "error": "bad json"})
            return
        try:
            cn = db()
            handle_update(cn, upd)
            cn.close()
            self._send(200, {"ok": True})
        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)[:200]})

    def log_message(self, format: str, *args) -> None:  # noqa: A002 — بلا ضجيج
        return


def main() -> None:
    cn = db()  # تهيئة الجداول قبل الإقلاع
    cn.close()
    print(f"[mda-bot] ready on 0.0.0.0:{PORT} · owner={'set' if OWNER else 'unset'} "
          f"· token={'set' if TOKEN else 'unset'} · site={SITE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
