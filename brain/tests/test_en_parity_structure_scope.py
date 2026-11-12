#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس نطاق قياس بنية التماثل بين المتن العربي والإنجليزي (ك-617).

العيب المقيس (2026-11-11): كان الفاحص يقارن عدد بنود القوائم `<li>` في الصفحة
المبنية كاملة، وهي تقيس اختيار وسم في الودجات (شرائح القطاعات · مفتاح الخريطة ·
بطاقة القرار) لا المحتوى. القياس: العربي 43 والإنجليزي 70 بلا أي فقد محتوى
(المتن 38=38 · الأرقام المرئية 42=42). النتيجة: منع كاذب لبوابة G001.

الإصلاح: يبقى قياس بنود القوائم في مستوى المتن (حيث يقيس المحتوى فعلًا)، وتُقاس
الصفحة بالعناوين والجداول والصفوف والرسوم والروابط والأرقام المرئية.

هذا الحارس يثبت العقد في الاتجاهين:
  · موجب: الشجرة الحيّة تمرّ (لا منع كاذب).
  · سالب أ: حذف صفّ جدول من الصفحة الإنجليزية يُمنع.
  · سالب ب: حذف بند قائمة من المتن الإنجليزي يُمنع.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

BRAIN = pathlib.Path(os.environ.get("BRAIN_DIR") or pathlib.Path(__file__).resolve().parents[1])
CHECKER = BRAIN / "validators" / "check_en_parity.py"


def site_root() -> pathlib.Path | None:
    v = os.environ.get("SITE_DIR") or os.environ.get("SITE")
    if v and (pathlib.Path(v) / "dist").is_dir():
        return pathlib.Path(v)
    for cand in (BRAIN.parent / "seawatch", pathlib.Path.home() / "seawatch"):
        if (cand / "dist").is_dir():
            return cand
    return None


def surface_date(site: pathlib.Path) -> str | None:
    pages = sorted((site / "dist" / "reports").glob("20*.html"))
    return pages[-1].stem if pages else None


def run_checker(site: pathlib.Path, date: str) -> int:
    env = dict(os.environ)
    env.update({"BRAIN_DIR": str(BRAIN), "SITE": str(site), "SITE_DIR": str(site)})
    r = subprocess.run(
        [sys.executable, str(CHECKER), "--date", date],
        env=env, capture_output=True, text=True, timeout=600,
    )
    return r.returncode


def stage(site: pathlib.Path, date: str, tmp: pathlib.Path) -> pathlib.Path:
    """انسخ ما يحتاجه الفاحص فقط: المتن الإنجليزي والصفحتين."""
    (tmp / "reports").mkdir(parents=True, exist_ok=True)
    (tmp / "reports" / "en").mkdir(parents=True, exist_ok=True)
    (tmp / "sources" / "i18n" / "en").mkdir(parents=True, exist_ok=True)
    shutil.copy2(site / "dist" / "reports" / f"{date}.html", tmp / "reports" / f"{date}.html")
    shutil.copy2(site / "dist" / "reports" / "en" / f"{date}.html", tmp / "reports" / "en" / f"{date}.html")
    shutil.copy2(site / "sources" / "i18n" / "en" / f"{date}-sectioned.en.md",
                 tmp / "sources" / "i18n" / "en" / f"{date}-sectioned.en.md")
    return tmp


def main() -> int:
    if not CHECKER.exists():
        print(f"   ✘ الفاحص غير موجود: {CHECKER}")
        return 2
    site = site_root()
    if site is None:
        print("   ⚠ لا جذر موقع فيه dist — تخطّي (يُشغَّل في البوابة بجذر معلوم)")
        return 0
    date = surface_date(site)
    if date is None:
        print("   ⚠ لا صفحة إصدار مبنية — تخطّي")
        return 0

    bad: list[str] = []

    # ── 1) موجب: الشجرة الحيّة تمرّ ─────────────────────────────────────────
    rc = run_checker(site, date)
    print(f"   {'✔' if rc == 0 else '✘'} موجب: الشجرة الحيّة ({date}) — rc={rc}")
    if rc != 0:
        bad.append("موجب: الشجرة الحيّة تُمنع (منع كاذب)")

    with tempfile.TemporaryDirectory(prefix="enparity-") as td:
        base = pathlib.Path(td)

        # ── 2) سالب أ: حذف صفّ جدول من الصفحة الإنجليزية ────────────────────
        a = stage(site, date, base / "a")
        page = a / "reports" / "en" / f"{date}.html"
        html = page.read_text(encoding="utf-8")
        m = re.search(r"<tr\b.*?</tr>", html, re.S)
        if m:
            page.write_text(html.replace(m.group(0), "", 1), encoding="utf-8")
            rc = run_checker(a, date)
            print(f"   {'✔' if rc != 0 else '✘'} سالب أ (فقد صفّ جدول): rc={rc}")
            if rc == 0:
                bad.append("سالب أ: فقد صفّ جدول لم يُمنع")
        else:
            print("   ⚠ سالب أ: لا صفّ جدول في الصفحة — تخطّي")

        # ── 3) سالب ب: حذف بند قائمة من المتن الإنجليزي ─────────────────────
        b = stage(site, date, base / "b")
        md = b / "sources" / "i18n" / "en" / f"{date}-sectioned.en.md"
        lines = md.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            if re.match(r"^\s*[-*]\s+", ln):
                lines.pop(i)
                break
        md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc = run_checker(b, date)
        print(f"   {'✔' if rc != 0 else '✘'} سالب ب (فقد بند قائمة في المتن): rc={rc}")
        if rc == 0:
            bad.append("سالب ب: فقد بند قائمة في المتن لم يُمنع")

    if bad:
        print("   ✘ النتيجة: مخالف — " + " · ".join(bad))
        return 1
    print("   ✓ النتيجة: نطاق قياس البنية سليم — موجب يمرّ وسالبان يُمنعان")
    return 0


if __name__ == "__main__":
    sys.exit(main())