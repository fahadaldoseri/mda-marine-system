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
SEND_LOG = B / "logs" / "telegram-sends.jsonl"


def _token_from_env_file() -> str:
    """الرمز من ملف البيئة المحلي عند غيابه من بيئة التشغيل (للبيئات السحابية مثل Codespaces).
    يُقرأ سطر واحد فقط مفتاحه TELEGRAM_BOT_TOKEN؛ ولا يُطبع الرمز ولا أي قيمة سرية."""
    for cand in (Path(os.environ.get("BRAIN_DIR", B)) / ".env", B / ".env",
                 Path(os.environ.get("BRAIN_DIR", B)) / "secrets" / "secrets.env", B / "secrets" / "secrets.env"):
        try:
            if not cand.is_file():
                continue
            for line in cand.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                if key.strip() == "TELEGRAM_BOT_TOKEN":
                    return val.strip().strip("'\"")
        except OSError:
            continue
    return ""


def _log(entry: dict) -> None:
    """سجل تدقيق لكل محاولة إرسال: مسموحة أو مرفوضة."""
    import datetime as _dt
    SEND_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": _dt.datetime.now().astimezone().isoformat(timespec="seconds"), **entry}
    with SEND_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _sent_today(target_label: str, date: str) -> bool:
    """هل أُرسل تقرير هذا اليوم فعلًا؟ (منع التكرار والرسائل الجانبية)"""
    if not SEND_LOG.exists():
        return False
    for line in SEND_LOG.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("decision") == "sent" and e.get("date") == date and e.get("target") == target_label:
            return True
    return False


def guard(args, text: str, targets: list[dict]) -> tuple[bool, str]:
    """سياسة قناة تلغرام الملزمة: القناة للتقارير الصباحية الرسمية فقط.

    تُرفض الرسائل الجانبية والتحديثات والمعاينات ورسائل الاختبار والملفات المؤقتة،
    وأي مرفق لا يخصّ تقرير اليوم (PDF التقرير أو خريطته).
    """
    if args.owner_approved:
        if not (args.reason or "").strip():
            return False, "الاستثناء يتطلب --reason مكتوبًا (أمر صريح من صاحب القرار)"
        return True, f"استثناء بأمر صاحب القرار: {args.reason.strip()}"
    if not args.daily_report:
        return False, ("القناة مخصّصة للتقرير الصباحي الرسمي فقط. لا يُرسَل أي محتوى آخر "
                       "(تحديثات، معاينات، ملفات جانبية، اختبارات). "
                       "للتقرير الرسمي: --daily-report --date YYYY-MM-DD")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date or ""):
        return False, "التقرير الرسمي يتطلب --date بصيغة YYYY-MM-DD"
    if "و ب" not in text:
        return False, "نص التقرير الرسمي يجب أن يحمل رقم الإصدار «و ب»"
    if not any(k in text for k in ("الفترة", "الفترة", "توقيت البحرين")):
        return False, "نص التقرير الرسمي يجب أن يحمل الفترة الزمنية وتوقيت البحرين"
    for path, kind in ((args.document, "مستند"), (args.photo, "صورة")):
        if not path:
            continue
        p = Path(path)
        allowed = [f"{args.date}.pdf", f"map-{args.date}.png", f"التقرير-اليومي-{args.date}.pdf"]
        if p.name not in allowed:
            return False, f"{kind} غير مسموح: {p.name} (المسموح: PDF تقرير اليوم أو خريطته)"
    if getattr(args, "validate_only", False):
        return True, "تحقق مطابق للسياسة (بلا إرسال)"
    for t in targets:
        if _sent_today(t.get("label", "?"), args.date):
            return False, (f"أُرسل تقرير {args.date} إلى «{t.get('label')}» سابقًا. "
                           "لا تكرار ولا تحديثات بعد الإرسال.")
    return True, "تقرير صباحي رسمي — مطابق للسياسة"


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
    ap.add_argument("--validate-only", action="store_true",
                    help="يفحص النص وفق السياسة ويطبع الحكم بلا إرسال ولا ضبط سجل")
    ap.add_argument("--daily-report", action="store_true",
                    help="إرسال التقرير الصباحي الرسمي (الاستخدام الوحيد المسموح)")
    ap.add_argument("--date", help="تاريخ التقرير YYYY-MM-DD")
    ap.add_argument("--owner-approved", action="store_true",
                    help="استثناء بأمر صريح من صاحب القرار، ويتطلب --reason")
    ap.add_argument("--reason", default="", help="سبب الاستثناء المكتوب")
    args = ap.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or _token_from_env_file()
    if not token and not args.dry_run:
        print("فشل: متغير TELEGRAM_BOT_TOKEN غير متاح (فعّل موصل Telegram Bot API أو ضع الرمز في brain/.env)")
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
    allowed, verdict = guard(args, text, targets)
    if getattr(args, "validate_only", False):
        verdict_label = "صالح" if allowed else "مرفوض"
        print(f"[تلغرام] {verdict_label} — {verdict}")
        return 0 if allowed else 3
    if not allowed:
        _log({"decision": "refused", "date": args.date, "reason": verdict,
              "targets": [t.get("label") for t in targets],
              "document": args.document, "photo": args.photo})
        print(f"[تلغرام] مرفوض — {verdict}")
        return 3
    if args.dry_run:
        _log({"decision": "dry-run", "date": args.date, "reason": verdict,
              "targets": [t.get("label") for t in targets]})
        print("اختبار جاف — الجهات المستهدفة:")
        for t in targets:
            print(f"  · {t['label']} ({t['type']}) · enabled={t.get('enabled')}")
        print(f"السياسة: {verdict}")
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
        if ok_text:
            _log({"decision": "sent", "date": args.date, "target": t.get("label"),
                  "kind": "daily-report" if args.daily_report else "owner-approved",
                  "reason": verdict, "detail": " · ".join(log)})
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
