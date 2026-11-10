#!/usr/bin/env python3
"""عقد مهارة فرز مسارات المصادر (قرار المالك 2026-11-10).

يُثبت بلا تجاوز حماية أو اتصال شبكي في الاختبارات:
  1) وجود 5 ملفات وتماثلها بين المجلد الحي والدماغ والمستودع.
  2) ترويسة المهارة وحدّها مع source-coverage-route-ops وقاعدة عدم تجاوز CAPTCHA.
  3) أداة التصنيف تمرّر جسمًا ناجحًا، وتمنع 403 مع تحدٍّ، وتمنع 503 كفشل تقني.
  4) بوابة الحداثة تمرّر مادة حديثة وتمنع مادة عمرها 1031 يومًا وحقلاً ناقصًا.
الرمز: 0 عقد سليم · 1 إخفاق في العقد.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
SKILL = "source-route-triage-ops"
LIVE = (Path(os.environ["SKILLS_DIR"]) if os.environ.get("SKILLS_DIR")
        else Path("/home/ubuntu/skills") if Path("/home/ubuntu/skills").is_dir()
        else B.parent / "skills") / SKILL
REPO_ROOT = Path(os.environ.get("BACKUP_REPO_DIR", B.parent))
REPO = REPO_ROOT / "skills" / SKILL
REQUIRED = [
    "SKILL.md",
    "scripts/triage_source_route.py",
    "scripts/check_freshness_gate.py",
    "references/candidate-ladder.md",
    "templates/route-measurement-row.md",
]
FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  {'✔' if condition else '✘'} {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=120)


def structure() -> None:
    for base, label in ((LIVE, "الحي"), (B / "skills" / SKILL, "الدماغ"), (REPO, "المستودع")):
        check(f"المجلد {label} موجود", base.is_dir(), str(base))
        for rel in REQUIRED:
            check(f"{label}: {rel}", (base / rel).is_file())
    for rel in REQUIRED:
        paths = [LIVE / rel, B / "skills" / SKILL / rel, REPO / rel]
        if all(p.is_file() for p in paths):
            check(f"تماثل بايت-ببايت: {rel}", paths[0].read_bytes() == paths[1].read_bytes() == paths[2].read_bytes())


def content_contract() -> None:
    path = LIVE / "SKILL.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    front = text.split("---")[1] if text.startswith("---") else ""
    check("الترويسة تحمل name وdescription", "name:" in front and "description:" in front)
    check("الاسم مطابق للمجلد", "name: source-route-triage-ops" in front)
    check("الحد الفاصل مع source-coverage-route-ops مكتوب", "source-coverage-route-ops" in text)
    check("الحد الفاصل مع مسار المتصفح مكتوب", "BROWSER_ROUTES" in text)
    check("منع CAPTCHA مكتوب", "CAPTCHA" in text and "لا تُحلّ" in text)
    check("مثال الحداثة 1031 موثق", "1031" in text and "15 و24" in text)


def route_tools() -> None:
    triage = LIVE / "scripts" / "triage_source_route.py"
    freshness = LIVE / "scripts" / "check_freshness_gate.py"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        good_body = root / "good.xml"
        good_body.write_text("<rss><item><title>مادة</title></item></rss>", encoding="utf-8")
        r = run([sys.executable, str(triage), "--url", "https://official.example/feed?session=redacted",
                 "--label", "مصدر رسمي", "--date", "2026-11-10", "--body-file", str(good_body)])
        try:
            payload = json.loads(r.stdout)
        except json.JSONDecodeError:
            payload = {}
        check("التصنيف: مسار ناجح ⇒ rc=0", r.returncode == 0, r.stdout[-200:])
        check("التصنيف: النجاح يحمل العناصر والحروف والزمن", all(k in payload for k in ("items", "chars", "elapsed_seconds", "measured_at")))
        check("التصنيف: query لا يظهر في المخرج", "session" not in r.stdout)

        challenge = root / "challenge.html"
        challenge.write_text("<html><title>Just a moment</title>Verify you are human</html>", encoding="utf-8")
        r2 = run([sys.executable, str(triage), "--url", "https://official.example/feed",
                  "--date", "2026-11-10", "--body-file", str(challenge), "--status-code", "403"])
        try:
            p2 = json.loads(r2.stdout)
        except json.JSONDecodeError:
            p2 = {}
        check("التصنيف: 403 مع تحدٍّ ⇒ rc=2", r2.returncode == 2)
        check("التصنيف: الحماية لا تسمح بالقارئ المدفوع", p2.get("classification") == "حماية" and p2.get("allow_paid_reader") is False)

        technical = root / "technical.xml"
        technical.write_text("<rss></rss>", encoding="utf-8")
        r3 = run([sys.executable, str(triage), "--url", "https://official.example/feed",
                  "--date", "2026-11-10", "--body-file", str(technical), "--status-code", "503"])
        try:
            p3 = json.loads(r3.stdout)
        except json.JSONDecodeError:
            p3 = {}
        check("التصنيف: 503 ⇒ rc=2", r3.returncode == 2)
        check("التصنيف: الفشل التقني يسمح بالمرشح المدفوع الأخير", p3.get("classification") == "فشل تقني" and p3.get("allow_paid_reader") is True)

        fresh = root / "fresh.json"
        fresh.write_text(json.dumps({"routes": [{
            "route": "official-feed", "items": 15, "chars": 4000,
            "elapsed_seconds": 1.25, "measured_at": "2026-11-10",
            "newest_published": "2026-11-10"
        }]}, ensure_ascii=False), encoding="utf-8")
        r4 = run([sys.executable, str(freshness), "--measurement", str(fresh), "--as-of", "2026-11-10"])
        check("الحداثة: مادة حديثة ⇒ rc=0", r4.returncode == 0, r4.stdout[-220:])

        stale = root / "stale.json"
        stale.write_text(json.dumps({"routes": [{
            "route": "official-feed", "items": 24, "chars": 9000,
            "elapsed_seconds": 1.25, "measured_at": "2026-11-10",
            "newest_published": "2024-01-14"
        }]}, ensure_ascii=False), encoding="utf-8")
        r5 = run([sys.executable, str(freshness), "--measurement", str(stale), "--as-of", "2026-11-10"])
        check("الحداثة: عمر 1031 يومًا ⇒ rc=2", r5.returncode == 2 and "1031" in r5.stdout, r5.stdout[-240:])

        missing = root / "missing.json"
        missing.write_text(json.dumps({"route": "official-feed", "items": 4, "chars": 100,
                                       "elapsed_seconds": 1.0, "measured_at": "2026-11-10"}), encoding="utf-8")
        r6 = run([sys.executable, str(freshness), "--measurement", str(missing), "--as-of", "2026-11-10"])
        check("الحداثة: غياب أحدث مادة ⇒ rc=2", r6.returncode == 2 and "newest_published" in r6.stdout)


def main() -> int:
    print(f"عقد مهارة {SKILL}")
    structure()
    content_contract()
    route_tools()
    print(f"----- الحصيلة: {'نجح' if not FAILURES else 'فشل'} · إخفاقات {len(FAILURES)} -----")
    for failure in FAILURES:
        print(f"  ✘ {failure}")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    raise SystemExit(main())
