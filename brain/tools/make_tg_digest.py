#!/usr/bin/env python3
"""يولّد ملخص تلغرام (HTML) من `web/meta/<التاريخ>.json` وفق قالب `appendices/telegram-delivery.md` (القسم 4).

لا يرسل شيئًا. المخرج ملف نصي يمرّ بعدها على `telegram_send.py --validate-only` ثم الإرسال بأمر صريح.
الاستعمال: python3 tools/make_tg_digest.py --date YYYY-MM-DD [--out PATH] [--base-url URL]
المسارات: BRAIN_DIR و SITE_DIR تُحترمان.
رموز الخروج: 0 تم · 2 بيانات ناقصة أو الملخص فوق السقف.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

CAP = 900
MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parent.parent)


def site_base_url():
    for cand in (os.environ.get("SITE_DIR"), B.parent / "seawatch", B.parent / "site"):
        if cand and (Path(cand) / "sources" / "site.json").is_file():
            return json.loads((Path(cand) / "sources" / "site.json").read_text(encoding="utf-8")).get("base_url", "")
    return ""


def dtg(t):
    return f"{t.day:02d}{t.hour:02d}{t.minute:02d}Z"


def short(text, n):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut.rstrip("،,:؛ ") + "…"


def build(meta, date, base, detail=True):
    cut = dt.datetime.strptime(meta["generated_label"], "%Y-%m-%dT%H:%M:%SZ")
    start = cut - dt.timedelta(hours=24)
    bh = cut + dt.timedelta(hours=3)
    codes = {e["code"]: e for e in meta.get("event_keys", [])}
    lines = ["<b>مركز الوعي بالمجال البحري</b>", "",
             f"<b>{meta['title']}</b>",
             f"تقرير رقم: «{meta['version']}»",
             f"التاريخ: {cut.day} {MONTHS[cut.month - 1]} {cut.year}",
             f"الفترة: {dtg(start)}–{dtg(cut)} {MONTHS[cut.month - 1]} {cut.year}",
             f"الوقت: {cut.hour:02d}{cut.minute:02d}Z ({bh.hour:02d}{bh.minute:02d}C بتوقيت البحرين)", "",
             f"<b>مستوى الخطر:</b> {meta['threat_level']}", "", "<b>ما تغيّر عن التقرير السابق:</b>"]
    for i, c in enumerate(meta.get("changes", [])[:3], 1):
        title = (codes.get(c["code"]) or {}).get("title") or short(c["text"], 70)
        lines += [f"{i}) {short(title, 70)} ({c['code']})" + (":" if detail else "")]
        if detail:
            lines.append(short(c["text"], 90))
    kp = " · ".join(f"{k['label']} {k['value']}" for k in meta.get("hero_kpis", [])[:3])
    if kp:
        lines += ["", "<b>المؤشرات:</b>", kp]
    act = (meta.get("decision_card", {}).get("action") or [""])[0]
    lines += ["", "<b>الإجراء المطلوب:</b>", f"نفّذوا — {short(act, 110)}", "", "<b>التقرير الكامل:</b>",
              f"{base.rstrip('/')}/reports/{date}.html"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--out")
    ap.add_argument("--base-url")
    a = ap.parse_args()
    mp = B / "web" / "meta" / f"{a.date}.json"
    if not mp.is_file():
        print(f"✘ لا بيانات إصدار: {mp}")
        return 2
    meta = json.loads(mp.read_text(encoding="utf-8"))
    need = ("title", "version", "generated_label", "threat_level", "changes")
    miss = [k for k in need if not meta.get(k)]
    base = a.base_url or site_base_url()
    if miss or not base:
        print(f"✘ حقول ناقصة: {miss or ''} {'base_url' if not base else ''}")
        return 2
    for detail in (True, False):
        text = build(meta, a.date, base, detail)
        visible = re.sub(r"<[^>]+>", "", text)
        if len(visible) <= CAP:
            break
    out = Path(a.out) if a.out else B / "logs" / f"tg-digest-{a.date}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"✔ {out} — {len(visible)} حرفًا (السقف {CAP})")
    return 0 if len(visible) <= CAP else 2


if __name__ == "__main__":
    sys.exit(main())
