#!/usr/bin/env python3
"""تسليم سحابي محكوم لتقرير يوم واحد إلى الموقع الثابت (قرار المالك 2026-11-19: «نفّذه في طلب جديد»).

كانت خطوات النشر في السحابة يدوية في برومت المهمة (نسخ ودفع وتحقق)، فتأخرت وتفاوتت بين الأيام،
وخطوة الخادم D005 لا تعمل خارج خادم Manus. هذه الأداة تنفّذها بترتيب واحد مغلق الفشل:

  1. حكم النشر (`publish_verdict.py`): 0 سليم أو 3 منقوص مُفصح، وغيرهما يمنع قبل أي نسخ.
  2. خطة النسخ: ملفات اليوم وأسطح الموقع المشتركة والأصول المتغيرة فقط، بلا حذف أبدًا.
     الصفحات القديمة المختلفة تُذكر «انحرافًا» ولا تُنسخ (بوابات اليوم لم تفحصها).
  3. بلا --push: تقف هنا (فحص جاف يُكتب في logs/deliver-D.json).
  4. مع --push: إيداع «نشر تقرير D» ودفع إلى main في مستودع الموقع، ثم انتظار نشر
     Cloudflare لتلك البصمة نفسها، ثم تحقق حي: 200 وبصمة صفحة اليوم = بصمة المبني.

الدفع نشر فعلي: لا يُستدعى --push إلا بأمر المالك (المهمة المجدولة بأمره الدائم، أو طلبه في تلك المرة).
رموز الخروج: 0 تم (أو الخطة سليمة في الفحص الجاف) · 2 ممنوع أو فشل.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1]
ACCOUNT = "61ff6efbe480affd36a24facac92040d"
PROJECT = "mda-bh"
BASE_URL = "https://mda-bh.pages.dev"
LIVE_REPO = "https://github.com/fahadaldoseri/seawatch-live.git"
# أسطح يغيّرها كل إصدار جديد (الرئيسية والفهارس والخلاصة). غيرها من الصفحات القديمة لا يُنسخ.
SHARED = (
    "index.html", "404.html", "feed.xml", "sitemap.xml", "robots.txt", "sources.html",
    "additions.html", "manus-routes.json", "reports/index.html",
    "reports/en/index.json", "reports/en/additions.html", "reports/en/index.html",
)
SHARED_DIRS = ("assets/",)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def plan(dist: Path, live: Path, date: str) -> dict:
    """يقارن المبني بنسخة الموقع ويصنّف كل ملف مختلف: يُنسخ أو انحراف لا يُنسخ."""
    copy, drift, same = [], [], 0
    for src in sorted(p for p in dist.rglob("*") if p.is_file()):
        rel = src.relative_to(dist).as_posix()
        dst = live / rel
        if dst.is_file() and _sha(dst) == _sha(src):
            same += 1
            continue
        if date in rel or rel in SHARED or rel.startswith(SHARED_DIRS):
            copy.append(rel)
        else:
            drift.append(rel)
    return {"copy": copy, "drift": drift, "unchanged": same}


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])}…: {res.stderr.strip()[-400:]}")
    return res


def cf_api(path: str, method: str = "GET", form: dict | None = None) -> dict:
    """واجهة Cloudflare عبر curl (الوكيل يحقن المفتاح على مسارات /accounts/ فقط)."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/pages/projects/{PROJECT}/{path}"
    cmd = ["curl", "-sS", "-m", "30", "-X", method, "-H", "Authorization: Bearer dummy", url]
    for k, v in (form or {}).items():
        cmd += ["--form-string", f"{k}={v}"]
    out = run(cmd).stdout
    return json.loads(out or "{}")


def wait_deploy(sha: str, timeout: int) -> dict:
    """ينتظر نشرًا ناجحًا لبصمة الإيداع نفسها؛ إن لم يبدأ بناء تلقائي خلال 3 دقائق يطلبه يدويًا."""
    start, triggered = time.time(), False
    while time.time() - start < timeout:
        rows = cf_api("deployments?per_page=5").get("result") or []
        for d in rows:
            meta = (d.get("deployment_trigger") or {}).get("metadata") or {}
            if str(meta.get("commit_hash", "")).startswith(sha[:7]):
                stage = d.get("latest_stage") or {}
                if stage.get("name") == "deploy" and stage.get("status") == "success":
                    return {"id": d.get("id"), "status": "success"}
                if stage.get("status") == "failure":
                    return {"id": d.get("id"), "status": "failure", "stage": stage.get("name")}
                break
        else:
            if not triggered and time.time() - start > 180:
                cf_api("deployments", "POST", {"branch": "main"})
                triggered = True
        time.sleep(15)
    return {"status": "timeout"}


def live_check(rel_html: str, expect_sha: str, tries: int = 8) -> dict:
    """يقرأ الصفحة من الموقع الحي بلا ذاكرة مؤقتة ويقارن بصمتها ببصمة المبني.

    وكيل مستخدم باسم الأداة: Cloudflare يرد 403 على وكيل Python-urllib الافتراضي (قيس 2026-11-20).
    """
    url = f"{BASE_URL}/{rel_html[:-5] if rel_html.endswith('.html') else rel_html}"
    last = {}
    for _ in range(tries):
        req = urllib.request.Request(f"{url}?v={int(time.time())}", headers={"Cache-Control": "no-cache", "User-Agent": "seawatch-cloud-deliver/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                last = {"url": url, "http": r.status, "sha_match": hashlib.sha256(body).hexdigest() == expect_sha}
        except Exception as exc:  # noqa: BLE001 — يُسجَّل السبب ويُعاد المحاولة
            last = {"url": url, "http": None, "error": str(exc)[:200]}
        if last.get("http") == 200 and last.get("sha_match"):
            return last
        time.sleep(15)
    return last


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", required=True)
    ap.add_argument("--brain", default=str(BRAIN))
    ap.add_argument("--site", default=os.environ.get("SITE_DIR") or str(BRAIN.parent / "site"))
    ap.add_argument("--live-dir", default="", help="نسخة محلية من مستودع الموقع (تُستنسخ إن غابت)")
    ap.add_argument("--push", action="store_true", help="نشر فعلي: إيداع ودفع وتحقق حي (بأمر المالك فقط)")
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args(argv)
    brain, dist = Path(a.brain).resolve(), Path(a.site).resolve() / "dist"
    out: dict = {"date": a.date, "push": a.push, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    log = brain / "logs" / f"deliver-{a.date}.json"

    def finish(rc: int, msg: str) -> int:
        out.update(rc=rc, message=msg, finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(("✔ " if rc == 0 else "✘ ") + msg)
        return rc

    v = subprocess.run([sys.executable, str(brain / "tools" / "publish_verdict.py"), "--date", a.date,
                        "--brain", str(brain), "--json"], capture_output=True, text=True)
    try:
        out["verdict"] = json.loads(v.stdout)
    except json.JSONDecodeError:
        return finish(2, f"حكم النشر غير مقروء (رمز {v.returncode})")
    if v.returncode not in (0, 3):
        return finish(2, "حكم النشر يمنع: " + " · ".join(out["verdict"].get("reasons") or []))
    page = dist / "reports" / f"{a.date}.html"
    if not page.is_file():
        return finish(2, f"صفحة اليوم غير مبنية: {page}")

    # خارج المستودع دائمًا: نسخة داخل brain كانت ستدخل فرع daily/D مع مخرجات اليوم.
    live = Path(a.live_dir) if a.live_dir else Path(tempfile.gettempdir()) / f"seawatch-live-{a.date}"
    try:
        if not (live / ".git").is_dir():
            if live.exists():
                shutil.rmtree(live)
            run(["git", "clone", "-q", "--depth", "5", LIVE_REPO, str(live)])
        elif a.push:
            run(["git", "pull", "-q", "--ff-only", "origin", "main"], cwd=live)
        p = plan(dist, live, a.date)
        out["plan"] = {"copy": p["copy"], "drift": p["drift"], "unchanged": p["unchanged"]}
        if f"reports/{a.date}.html" not in p["copy"] and not (live / "reports" / f"{a.date}.html").is_file():
            return finish(2, "خطة النسخ لا تحوي صفحة اليوم")
        if not a.push:
            return finish(0, f"فحص جاف: يُنسخ {len(p['copy'])} ملفًا، وانحراف غير منسوخ {len(p['drift'])}، ولا حذف")
        for rel in p["copy"]:
            (live / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dist / rel, live / rel)
        if run(["git", "status", "--porcelain"], cwd=live).stdout.strip():
            if any(line.startswith(" D") or line.startswith("D ") for line in
                   run(["git", "status", "--porcelain"], cwd=live).stdout.splitlines()):
                return finish(2, "رُفض: ظهر حذف في نسخة الموقع")
            run(["git", "add", "-A"], cwd=live)
            run(["git", "-c", "user.name=Claude", "-c", "user.email=noreply@anthropic.com",
                 "commit", "-q", "-m", f"نشر تقرير {a.date}"], cwd=live)
            run(["git", "push", "-q", "origin", "HEAD:main"], cwd=live)
        sha = run(["git", "rev-parse", "HEAD"], cwd=live).stdout.strip()
        remote = run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=live).stdout.split()[0]
        out["commit"], out["remote_main"] = sha, remote
        if remote != sha:
            return finish(2, f"فرع main البعيد ({remote[:7]}) ليس الإيداع المنشور ({sha[:7]})")
        out["deploy"] = wait_deploy(sha, a.timeout)
        if out["deploy"].get("status") != "success":
            return finish(2, f"نشر Cloudflare لم ينجح للبصمة {sha[:7]}: {out['deploy']}")
        out["live"] = live_check(f"reports/{a.date}.html", _sha(page))
        if out["live"].get("http") != 200 or not out["live"].get("sha_match"):
            return finish(2, f"الصفحة الحية لا تطابق المبني: {out['live']}")
    except (RuntimeError, OSError, json.JSONDecodeError) as exc:
        return finish(2, f"تعذّر التسليم: {exc}")
    return finish(0, f"نُشر {a.date} ({sha[:7]}) وتطابقت الصفحة الحية مع المبني: {BASE_URL}/reports/{a.date}")


if __name__ == "__main__":
    sys.exit(main())
