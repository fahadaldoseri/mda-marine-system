#!/usr/bin/env python3
"""محاولة نشر قناة Manus المحكومة — تُقاس الجهوزية أولًا، ولا تُدَّعى نجاحًا بلا تحقق حي.

المنطق:
  1) قياس جهوزية إضافة المنصة عبر `manus-mcp-cli tool list --server webdev-mcp`.
     غير جاهزة  → رمز 1 (تحذير مقصود، بلا ضجيج وبلا نشر).
  2) جاهزة → استكشاف أداة النشر من السجل الحقيقي، وبناء مدخلاتها من مخططها المعلن.
     مخطط غير مفهوم أو حقل إلزامي بلا مقابل معروف → رمز 2 (فشل مغلق، لا تخمين).
  3) نشر ثم تحقق حي من رابط اليوم على نطاق Manus: 200 · text/html · حجم أدنى · التاريخ في المتن.
     النجاح يُقيَّد في state/manus-channel-<date>.json ويُبلَّغ عنه مرة واحدة بأمر المالك.

لا يُطبع أي سر، ولا يُخمَّن اسم حقل أو مسار.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

B = Path(__file__).resolve().parent.parent
PROJECT_ID = "XP4qiRMRUjBiSubQfXVdKs"
PROJECT_DIR = "/home/ubuntu/seawatch"
MANUS_BASE = "https://seawatch-xp4qirmr.manus.space"
MIN_BYTES = 100_000
NOT_READY_MARK = "workspace recovery has not completed"
LOG_DIR = B / "logs" / "manus-channel"

# خريطة أسماء الحقول الشائعة إلى القيم المعروفة — تُستخدم فقط إن أعلن المخطط وجودها.
FIELD_ALIASES = {
    "project_id": PROJECT_ID, "projectId": PROJECT_ID, "project_uid": PROJECT_ID,
    "id": PROJECT_ID, "uid": PROJECT_ID,
    "directory": PROJECT_DIR, "dir": PROJECT_DIR, "project_dir": PROJECT_DIR,
    "path": PROJECT_DIR, "root": PROJECT_DIR, "cwd": PROJECT_DIR,
    "message": "نشر تقرير أمن الملاحة", "title": "نشر تقرير أمن الملاحة",
}


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "انتهت المهلة"
    except FileNotFoundError:
        return 127, "manus-mcp-cli غير متاح"


def classify_probe(rc: int, output: str) -> tuple[str, str]:
    """تصنيف قياس الجهوزية: ready | not-ready | error."""
    if NOT_READY_MARK in output:
        return "not-ready", "إضافة المنصة لم تكتمل استعادتها"
    if rc != 0:
        return "error", f"تعذّر القياس (رمز {rc}): {output.strip()[:120]}"
    return "ready", "الإضافة جاهزة"


def pick_publish_tool(tool_list_output: str) -> str | None:
    """أداة النشر من السجل الحقيقي للأدوات — لا اسم مُخترَع."""
    names = re.findall(r'"name"\s*:\s*"([^"]+)"', tool_list_output)
    if not names:
        names = re.findall(r'^\s*[-*]?\s*([a-zA-Z0-9_.]+)\s*$', tool_list_output, re.M)
    cands = [n for n in names if re.search(r'publish', n, re.I)]
    if not cands:
        return None
    cands.sort(key=len)
    return cands[0]


def build_publish_args(schema_text: str) -> tuple[dict | None, str]:
    """يبني مدخلات النشر من مخطط الأداة المعلن؛ يفشل مغلقًا عند أي حقل إلزامي بلا مقابل."""
    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', schema_text, re.S)
        if not m:
            return None, "مخطط الأداة غير قابل للقراءة"
        try:
            schema = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None, "مخطط الأداة غير قابل للقراءة"
    for key in ("inputSchema", "input_schema", "schema", "parameters"):
        if isinstance(schema.get(key), dict):
            schema = schema[key]
            break
    props = schema.get("properties") if isinstance(schema, dict) else None
    if not isinstance(props, dict) or not props:
        return None, "مخطط الأداة لا يعلن حقولًا"
    required = schema.get("required") or []
    args: dict = {}
    for name in props:
        if name in FIELD_ALIASES:
            args[name] = FIELD_ALIASES[name]
    missing = [r for r in required if r not in args]
    if missing:
        return None, "حقل إلزامي بلا مقابل معروف: " + ", ".join(missing)
    return args, ""


def verify_live(date: str, timeout: int = 45) -> dict:
    """تحقق حي من رابط اليوم على نطاق Manus."""
    url = f"{MANUS_BASE}/reports/{date}.html"
    req = urllib.request.Request(url, headers={"User-Agent": "seawatch-channel-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
            ok = (resp.status == 200 and ctype == "text/html"
                  and len(body) >= MIN_BYTES and date.encode() in body)
            return {"url": url, "status": resp.status, "content_type": ctype,
                    "bytes": len(body), "ok": ok,
                    "reason": "" if ok else "شرط التحقق غير مستوفى"}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "status": 0, "content_type": "", "bytes": 0, "ok": False,
                "reason": f"{type(exc).__name__}: {str(exc)[:100]}"}


def marker_path(date: str) -> Path:
    return B / "state" / f"manus-channel-{date}.json"


def log_entry(entry: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **entry}
    with (LOG_DIR / f"{dt.date.today().isoformat()}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def notify_success(doc: dict) -> tuple[bool, str]:
    """إبلاغ المالك مرة واحدة عبر المسار المحكوم (استثناء بأمر صريح مكتوب)."""
    text = (f"✅ <b>نشر قناة Manus نجح</b>\n"
            f"التاريخ: {doc['date']}\n"
            f"الرابط: {doc['url']}\n"
            f"الحجم: {doc['bytes']} بايت · النوع: text/html\n"
            f"الوقت: {doc['verified_at']}")
    rc, out = run([sys.executable, str(B / "tools" / "telegram_send.py"),
                   "--text", text, "--targets", "primary", "--owner-approved",
                   "--reason", "أمر المالك 2026-11-07: إبلاغه بنجاح نشر تقرير اليوم على قناة Manus",
                   "--date", doc["date"]], timeout=180)
    return rc == 0, out.strip()[:200]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--no-notify", action="store_true")
    a = ap.parse_args(argv)

    if marker_path(a.date).is_file():
        print(f"   ✔ قناة Manus منشورة لتاريخ {a.date} سابقًا — لا إعادة")
        return 0

    rc, out = run(["manus-mcp-cli", "tool", "list", "--server", "webdev-mcp"], timeout=120)
    state, why = classify_probe(rc, out)
    print(f"   قياس الجهوزية: {state} — {why}")
    if state != "ready":
        log_entry({"date": a.date, "state": state, "why": why})
        return 1

    tool = pick_publish_tool(out)
    if not tool:
        log_entry({"date": a.date, "state": "schema", "why": "لا أداة نشر في السجل"})
        print("   ✘ لا أداة نشر معلنة في سجل الأدوات — لا تخمين")
        return 2
    rc2, schema_text = run(["manus-mcp-cli", "tool", "get", tool, "--server", "webdev-mcp"], timeout=120)
    args, why2 = build_publish_args(schema_text)
    if args is None:
        log_entry({"date": a.date, "state": "schema", "tool": tool, "why": why2})
        print(f"   ✘ {why2} (الأداة {tool})")
        return 2

    print(f"   تنفيذ النشر عبر {tool} بمدخلات معلنة: {sorted(args)}")
    rc3, out3 = run(["manus-mcp-cli", "tool", "call", tool, "--server", "webdev-mcp",
                     "--input", json.dumps(args, ensure_ascii=False)], timeout=900)
    live = verify_live(a.date)
    doc = {"date": a.date, "tool": tool, "publish_rc": rc3,
           "publish_output_tail": out3.strip()[-300:],
           "url": live["url"], "status": live["status"], "content_type": live["content_type"],
           "bytes": live["bytes"], "verified_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if live["ok"]:
        marker_path(a.date).parent.mkdir(parents=True, exist_ok=True)
        marker_path(a.date).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        doc["state"] = "published"
        log_entry(doc)
        print(f"   ✔ تحقق حي: {live['status']} · {live['content_type']} · {live['bytes']} بايت")
        if not a.no_notify:
            sent, info = notify_success(doc)
            print(f"   إبلاغ المالك: {'أُرسل' if sent else 'فشل'} — {info[:120]}")
        return 0

    doc["state"] = "attempted-not-verified"
    doc["why"] = live["reason"]
    log_entry(doc)
    print(f"   ⚠ لم يتحقق النشر حيًّا: {live['reason']}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())