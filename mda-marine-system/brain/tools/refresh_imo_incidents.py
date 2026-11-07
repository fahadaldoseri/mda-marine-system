#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تحديث قائمة IMO الرسمية للوقائع المؤكدة من صفحتها الرسمية (فشل مغلق).

المصدر: صفحة «Middle East - Highlighted (Confirmed) incidents» على imo.org.
المخرج: ``appendices/imo-incidents.json`` بنفس مخططه القائم، مع تحديث العدّادين
الرسميين (الحوادث المؤكدة، وفيات البحّارة) وبصمة الصفحة وطابع الجلب.

رموز الخروج: 0 نجاح · 2 منع (تعارض بين العدّاد المعلن وعدد الصفوف المستخرجة) · 70 انهيار.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html as htmlmod
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "appendices" / "imo-incidents.json"
URL = ("https://www.imo.org/en/mediacentre/hottopics/pages/"
       "middle-east-highlighted-incidents.aspx")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


def fetch(url: str) -> str:
    r = subprocess.run(["curl", "-sS", "-m", "60", "-A",
                        "Mozilla/5.0 (compatible; MDA-marine-watch/1.0)", url],
                       capture_output=True, text=True)
    if r.returncode != 0 or len(r.stdout) < 5000:
        print(f"✘ تعذّر جلب صفحة IMO (rc={r.returncode} bytes={len(r.stdout)})", file=sys.stderr)
        raise SystemExit(2)
    return r.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default="", help="ملف HTML محفوظ بدل الجلب الحيّ")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    raw = Path(args.html).read_text(encoding="utf-8", errors="ignore") if args.html else fetch(URL)
    sha = hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()
    flat = clean(raw)

    m_inc = re.search(r"Number of confirmed incidents as at (\d{1,2} \w+ \d{4})\s*:?\s*(\d{1,3})", flat)
    m_fat = re.search(r"Number of confirmed seafarer fatalities\s*:?\s*(\d{1,3})", flat)
    if not m_inc or not m_fat:
        print("✘ لم يُعثر على العدّادين الرسميين في الصفحة", file=sys.stderr)
        raise SystemExit(2)
    as_at_text, declared = m_inc.group(1), int(m_inc.group(2))
    declared_fatalities = int(m_fat.group(1))

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", raw, re.S | re.I)
    incidents, current_date = [], ""
    for r in rows:
        cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S | re.I)]
        if not cells:
            continue
        if re.fullmatch(r"Date", cells[0], re.I):
            continue
        if re.match(r"^\d{1,2}\s+\w+$", cells[0]):
            current_date = cells[0]
            cells = cells[1:]
        elif current_date and len(cells) >= 3:
            pass
        else:
            continue
        if len(cells) < 3:
            continue
        vessel_raw, location, desc = cells[0], cells[1], " ".join(cells[2:])
        if not vessel_raw or not location:
            continue
        mi = re.search(r"IMO\s*([0-9]{5,9})", vessel_raw)
        vessel = re.sub(r"\(IMO[^)]*\)", "", vessel_raw).strip(" ()\u00a0")
        day, mon = current_date.split()[0], current_date.split()[1]
        iso = f"2026-{MONTHS.get(mon, 1):02d}-{int(day):02d}"
        incidents.append({"date": current_date, "date_iso": iso, "vessel": vessel,
                          "imo_number": mi.group(1) if mi else "",
                          "location": location, "description": desc})
    seen, uniq = set(), []
    for it in incidents:
        key = (it["date_iso"], it["vessel"], it["location"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    print(f"   العدّاد المعلن: {declared} · الصفوف المستخرجة الفريدة: {len(uniq)} · "
          f"وفيات معلنة: {declared_fatalities} · بتاريخ {as_at_text}")
    if len(uniq) != declared:
        print("✘ تعارض بين العدّاد المعلن وعدد الصفوف المستخرجة — لا يُكتب ملف مضلّل",
              file=sys.stderr)
        raise SystemExit(2)

    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    new = dict(old)
    new.update({
        "schema_version": old.get("schema_version", 1),
        "description": old.get("description", ""),
        "source": {**old.get("source", {}), "organization": "International Maritime Organization (IMO)",
                   "page_title": "Middle East - Highlighted (Confirmed) incidents",
                   "url": URL, "as_at": as_at_text,
                   "html_sha256": sha},
        "totals": {"confirmed_incidents": declared,
                   "confirmed_seafarer_deaths": declared_fatalities},
        "incidents": uniq,
        "retrieved": dt.date.today().isoformat(),
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "previous": {"totals": old.get("totals"), "retrieved": old.get("retrieved"),
                     "incidents_count": len(old.get("incidents", []))},
    })
    if args.apply:
        OUT.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"   ✔ كُتب {OUT.relative_to(ROOT)} بعدد {len(uniq)} حادثة")
    else:
        print("   (تجربة جافة: لم يُكتب الملف)")
    if args.report:
        Path(args.report).write_text(json.dumps(
            {"as_at": as_at_text, "declared": declared, "rows": len(uniq),
             "fatalities": declared_fatalities, "html_sha256": sha,
             "applied": bool(args.apply)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
