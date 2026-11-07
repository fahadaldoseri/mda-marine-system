#!/usr/bin/env python3
"""التحقق من اتجاه اللغة في خط أنابيب تقرير ثنائي اللغة.

يفحص:
  1) مفتاح السياسة في المانيفست (i18n.master / i18n.since / ملف الأصل).
  2) وجود ملف المتن الحاكم (لغة الأصل) لتاريخ معيّن.
  3) خلو صفحات لغة الأصل المبنية من أي نص مرئي للغة الأخرى.
  4) عدم وجود مفتاح ترجمة آلية مُفعَّل في المولّد.

الرمز 0 = الاتجاه محقَّق · الرمز 2 = مخالفة.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ARABIC = re.compile(r"[\u0600-\u06FF]")
TAG = re.compile(r"<[^>]+>")
SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
MT_FLAG = re.compile(
    r"(?im)^\s*(auto_translate|mt_fallback|machine_translation)\s*[:=]\s*(true|1|\"1\"|'1')"
)
DEFAULT_MASTER = "sources/i18n/en/{date}-sectioned.en.md"


def _default_brain() -> Path:
    return Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[3])


def _default_site() -> Path:
    configured = os.environ.get("SITE_DIR")
    if configured:
        return Path(configured)
    brain = _default_brain()
    for name in ("seawatch", "site"):
        candidate = brain.parent / name
        if candidate.is_dir():
            return candidate
    return brain.parent / "seawatch"


def visible_text(html: str) -> str:
    return TAG.sub(" ", SCRIPT.sub(" ", html))


def arabic_visible(html: str) -> int:
    return len(ARABIC.findall(visible_text(html)))


def check(brain: Path, site: Path, date: str, quiet: bool = False) -> list[str]:
    bad: list[str] = []
    say = (lambda *_a: None) if quiet else print

    rb_path = brain / "runbook" / "runbook.json"
    if not rb_path.exists():
        return [f"لا مانيفست: {rb_path}"]
    rb = json.loads(rb_path.read_text(encoding="utf-8"))

    policy = rb.get("i18n") or {}
    master = str(policy.get("master", "")).strip().lower()
    if not master:
        bad.append("سياسة الاتجاه غير معلنة في المانيفست (مفتاح i18n.master)")
    else:
        say(f"   ✔ لغة الأصل المعلنة: {master} · منذ {policy.get('since', 'غير مؤرّخ')}")

    pattern = str(policy.get("en_master_file") or DEFAULT_MASTER)
    master_file = site / pattern.replace("{date}", date)
    if not master_file.exists():
        bad.append(f"ملف المتن الحاكم غير موجود: {master_file}")
    else:
        say(f"   ✔ ملف المتن الحاكم: {master_file.name} · {len(master_file.read_text(encoding='utf-8'))} حرفًا")

    for rel in (f"reports/en/{date}.html", f"reports/en/additions.html"):
        page = site / "dist" / rel
        if not page.exists():
            continue
        n = arabic_visible(page.read_text(encoding="utf-8", errors="ignore"))
        if n:
            bad.append(f"نص مرئي للغة الأخرى في صفحة الأصل: dist/{rel} ({n} حرفًا)")
        else:
            say(f"   ✔ خلو صفحة الأصل: dist/{rel}")

    gen = site / "generator" / "i18n_en.py"
    if gen.exists() and MT_FLAG.search(gen.read_text(encoding="utf-8", errors="ignore")):
        bad.append("مفتاح ترجمة آلية مُفعَّل في المولّد — الترجمة بالمعنى مطلوبة لا الآلية")
    return bad


def selftest() -> int:
    fails = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        brain = root / "brain"
        site = root / "site"
        (brain / "runbook").mkdir(parents=True)
        (site / "sources/i18n/en").mkdir(parents=True)
        (site / "dist/reports/en").mkdir(parents=True)
        (site / "generator").mkdir(parents=True)

        def write(policy, page="<p>Safe navigation report</p>", mt=False):
            (brain / "runbook/runbook.json").write_text(
                json.dumps({"i18n": policy}, ensure_ascii=False), encoding="utf-8"
            )
            (site / "sources/i18n/en/2026-11-02-sectioned.en.md").write_text(
                "# Master\n\nSafe navigation report\n", encoding="utf-8"
            )
            (site / "dist/reports/en/2026-11-02.html").write_text(page, encoding="utf-8")
            (site / "generator/i18n_en.py").write_text(
                "auto_translate = True\n" if mt else "auto_translate = False\n", encoding="utf-8"
            )

        cases = [
            ("موجب", {"master": "en", "since": "2026-11-03"}, "<p>Safe navigation report</p>", False, 0),
            ("سالب: لا سياسة", {}, "<p>Safe navigation report</p>", False, 2),
            ("سالب: عربي في صفحة الأصل", {"master": "en", "since": "2026-11-03"}, "<p>تقرير سلامة</p>", False, 2),
            ("سالب: ترجمة آلية", {"master": "en", "since": "2026-11-03"}, "<p>Safe</p>", True, 2),
        ]
        for name, policy, page, mt, want in cases:
            write(policy, page, mt)
            bad = check(brain, site, "2026-11-02", quiet=True)
            got = 0 if not bad else 2
            ok = got == want
            fails += 0 if ok else 1
            print(f"   {'✔' if ok else '✘'} {name}: رمز {got} (المتوقع {want})"
                  + ("" if ok else f" — {bad}"))
    print(f"   اختبار ذاتي: {'ناجح' if not fails else f'فاشل ({fails})'}")
    return 0 if not fails else 2


def main() -> int:
    ap = argparse.ArgumentParser(description="التحقق من اتجاه اللغة في خط أنابيب ثنائي اللغة")
    ap.add_argument("--brain", default=str(_default_brain()))
    ap.add_argument("--site", default=str(_default_site()))
    ap.add_argument("--date")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if not a.date:
        print("   ✘ يلزم --date أو --selftest")
        return 2

    bad = check(Path(a.brain), Path(a.site), a.date)
    if bad:
        print("   ✘ الاتجاه غير محقَّق:")
        for b in bad:
            print("      ·", b)
        return 2
    print("   ✔ اتجاه اللغة محقَّق")
    return 0


if __name__ == "__main__":
    sys.exit(main())
