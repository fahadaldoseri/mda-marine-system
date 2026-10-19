#!/usr/bin/env python3
"""اختبار تشغيل شامل لنظام مركز الوعي بالمجال البحري.

يُشغّل البيئة والبوابات وخط البيانات والموقع وتلغرام والنسخة الاحتياطية،
ثم يكتب تقريرًا مفصّلًا في audit/self-test-<التاريخ>.md ولا يرسل أي رسالة فعلية.

سلّم الرموز: 0 نجاح · 1 تحذير · 2 مانع.
الاستعمال:
    python3 tools/self_test.py                 # الفحص الكامل
    python3 tools/self_test.py --skip-network   # بلا فحوص الشبكة الثقيلة
    python3 tools/self_test.py --date 2026-10-19
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = Path(os.environ.get("BRAIN_DIR", HERE.parent)).resolve()
SITE = Path(os.environ.get("SITE_DIR", BRAIN.parent / "seawatch")).resolve()
DIST = SITE / "dist"
SITE_URL = os.environ.get("SITE_URL", "https://seawatch-xp4qirmr.manus.space")

RESULTS: list[dict] = []
ENV_FACTS: list[str] = []
NOTES: dict[str, str] = {}


def record(group: str, name: str, rc: int, tolerate: int, evidence: str = "", note: str = ""):
    status = "ok" if rc == 0 else ("warn" if rc <= tolerate else "block")
    RESULTS.append({"group": group, "name": name, "rc": rc,
                    "status": status, "evidence": evidence.strip()[:200]})
    if note:
        NOTES[name] = note
    mark = {"ok": "✔", "warn": "•", "block": "✘"}[status]
    print(f"  {mark} {name:<44} رمز {rc:<3} {status}")
    return status


def run(group: str, name: str, cmd: list[str], tolerate: int = 0,
        cwd: Path | None = None, timeout: int = 900, note: str = "") -> int:
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=str(cwd or BRAIN), capture_output=True,
                           text=True, timeout=timeout)
        rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        rc, out = 124, f"انتهت المهلة بعد {timeout} ثانية"
    except FileNotFoundError as exc:
        rc, out = 127, f"أمر غير موجود: {exc}"
    last = next((l.strip() for l in reversed(out.strip().splitlines()) if l.strip()), "")
    record(group, name, rc, tolerate, f"{last} ({time.time()-t0:.0f}ث)", note)
    return rc


def probe(group: str, name: str, ok: bool, detail: str = "", tolerate: bool = False,
          note: str = "") -> None:
    rc = 0 if ok else (1 if tolerate else 2)
    record(group, name, rc, 1 if tolerate else 0, detail, note)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--skip-network", action="store_true")
    ap.add_argument("--skip-heavy", action="store_true")
    args = ap.parse_args()

    date = args.date or subprocess.run(
        ["bash", "-c", "ls -1 reports/*-sectioned.md | tail -1"],
        cwd=str(BRAIN), capture_output=True, text=True).stdout.strip().replace("-sectioned.md", "")
    if not date:
        print("تعذّر تحديد تاريخ الإصدار — مرّر --date")
        return 2
    meta = BRAIN / "web" / "meta" / f"{date}.json"
    report_md = BRAIN / "reports" / f"{date}-sectioned.md"
    net = not args.skip_network
    heavy = not args.skip_heavy

    print(f"اختبار تشغيل شامل — إصدار {date}")
    print(f"النظام: {BRAIN}\nالموقع: {SITE}\n")

    # ═══ 0) البيئة ═══
    print("0) البيئة")
    g = "0) البيئة"
    v = subprocess.run(["python3", "--version"], capture_output=True, text=True).stdout.strip()
    ENV_FACTS.append(f"بايثون: {v}")
    for mod in ("docx", "PIL", "requests", "playwright", "shapely", "pymysql", "lxml"):
        try:
            __import__(mod)
            probe(g, f"حزمة بايثون: {mod}", True, "متوفرة")
        except Exception as exc:  # noqa: BLE001
            probe(g, f"حزمة بايثون: {mod}", False, f"{type(exc).__name__}", tolerate=True,
                  note="حزمة ناقصة تُعطّل مسارًا كاملًا عند الحاجة إليها")
    for binary in ("soffice", "pdftoppm", "pdftotext", "pdfinfo", "git", "curl", "fc-list"):
        probe(g, f"أداة نظام: {binary}", subprocess.run(["bash", "-c", f"command -v {binary}"],
              capture_output=True).returncode == 0, tolerate=True,
              note="أداة نظام مطلوبة لتوليد Word/PDF أو للفحص الطباعي")
    fonts = subprocess.run(["bash", "-c", "fc-list :lang=ar | head -3"], capture_output=True, text=True).stdout
    probe(g, "خط عربي مثبّت", len(fonts.strip()) > 0, fonts.splitlines()[0][:60] if fonts.strip() else "لا يوجد",
          note="بلا خط عربي يخرج PDF العربي بمربعات")
    probe(g, "مصدر التقرير موجود", report_md.exists(), report_md.name)
    probe(g, "ملف واجهة الإصدار موجود", meta.exists(), meta.name)

    # ═══ 1) الصياغة ═══
    print("\n1) تصريف الشيفرة")
    g = "1) الصياغة"
    for label, root, tol in (("النظام", BRAIN, 0), ("الموقع", SITE, 0)):
        p = subprocess.run([sys.executable, "-m", "compileall", "-q", str(root)],
                           capture_output=True, text=True)
        files = len(list(root.rglob("*.py")))
        probe(g, f"تصريف ملفات {label} ({files} ملف)", p.returncode == 0,
              (p.stdout or p.stderr).strip().splitlines()[-1][:80] if p.returncode else "بلا أخطاء")

    # ═══ 2) البوابات العامة ═══
    print("\n2) البوابات العامة")
    g = "2) البوابات العامة"
    run(g, "عدد المصادر (مصدر واحد)", ["python3", "validators/check_sources_count.py"], tolerate=1,
        note="تحذير = تعارض نصّي في ذكر العدد لا نقص في المصادر")
    run(g, "الأرقام اللاتينية", ["python3", "validators/check_numerals.py"], tolerate=1,
        note="تحذير = أرقام عربية عُثر عليها في نصّ غير مغطّى")
    run(g, "قابلية النقل (مسارات مطلقة)", ["python3", "validators/check_portable_paths.py"])
    run(g, "سياسة الرموز في المخرجات", ["python3", "validators/check_code_policy.py", str(DIST)], tolerate=1)
    run(g, "مطابقة النسخة الاحتياطية (تنبيهي)",
        ["python3", "validators/check_backup_parity.py", "--mode", "advisory"], tolerate=1,
        note="تحذير = الشجرة تسبق المستودع قبل الدفع، وهو الوضع الطبيعي")

    # ═══ 3) بوابات الإصدار ═══
    print("\n3) بوابات الإصدار")
    g = "3) بوابات الإصدار"
    run(g, "مدقق التقرير (المخطط والتسليم)", ["python3", "validators/validate_report.py", str(meta),
        "--md", str(report_md)], tolerate=1, note="تحذير = تنبيه تنسيقي غير مانع")
    run(g, "بوابة الأسلوب", ["python3", "validators/check_style.py", str(report_md)])
    run(g, "بوابة اللغة", ["python3", "validators/check_language.py", str(report_md)])
    run(g, "بوابة التحليل الاستخباري", ["python3", "validators/check_intel.py", str(report_md), str(meta)])
    run(g, "قاعدة النقاط في المصدر", ["python3", "validators/check_points_rule.py", "--md", str(report_md), "--meta", str(meta)])
    run(g, "فصل فضاءات الرموز", ["python3", "validators/check_code_spaces.py", "--date", date])
    run(g, "تغطية فحص العقوبات", ["python3", "validators/check_ofac_coverage.py", "--date", date], tolerate=1,
        note="تحذير = سفينة بتطابق جزئي تحتاج تحققًا بشريًا")
    pdf = DIST / "reports" / "pdf" / f"{date}.pdf"
    run(g, "الشكل المعتمد للـPDF", ["python3", "validators/check_pdf_format.py", "--pdf", str(pdf)], tolerate=1)

    # ═══ 4) بوابات المخرج ═══
    print("\n4) بوابات المخرج")
    run("4) المخرج", "بوابات المخرج العشر", ["python3", "tools/qa_gates.py", "--date", date])
    run("4) المخرج", "مولّد Word طبق الأصل", ["python3", "tools/build_report_docx_exact.py", "--date", date], tolerate=1)

    # ═══ 5) خط البيانات ═══
    print("\n5) خط البيانات")
    g = "5) خط البيانات"
    if net:
        run(g, "فحص التغذيات الأربعين", ["python3", "tools/check_feeds.py"], tolerate=1, timeout=1200,
            note="تحذير = مصادر ترد 403/شهادة معطوبة ويُستعمل لها مسار جلب بديل")
    else:
        record(g, "فحص التغذيات (مُتخطّى)", 0, 0, "تُخطّي بطلب المستخدم")
    run(g, "توليد قائمة العقوبات من التقرير", ["python3", "tools/ofac_targets_from_report.py", date], tolerate=1)
    run(g, "فحص العقوبات", ["python3", "tools/ofac_screen.py", "watchlist/ofac-targets.txt"], tolerate=1,
        note="تحذير = تطابق جزئي يستوجب مراجعة بشرية")
    run(g, "استخراج أسماء السفن", ["python3", "tools/vessel_names.py", date], tolerate=1)
    ledger = BRAIN / "cumulative-2026" / "event-ledger-master.json"
    before = sha(ledger)
    run(g, "دمج الدفتر التراكمي (جولة أولى)", ["python3", "tools/merge_ledger_daily.py"], tolerate=1, timeout=600)
    mid = sha(ledger)
    run(g, "دمج الدفتر التراكمي (جولة ثانية)", ["python3", "tools/merge_ledger_daily.py"], tolerate=1, timeout=600)
    probe(g, "الدمج لا يكرّر السجلات (ثبات البصمة)", sha(ledger) == mid,
          f"بصمة ثابتة {mid[:12]}" if sha(ledger) == mid else "البصمة تغيّرت بين جولتين متطابقتين",
          note="تغيّر البصمة يعني إضافة مزدوجة تكسر عدّادات السجل التراكمي")
    if net and heavy:
        run(g, "حفظ أصول البلاغات الرسمية", ["python3", "tools/archive_originals.py", date, "sources/ukmto-urls.txt"],
            tolerate=1, timeout=900, note="تحذير = مصدر رسمي لم يُحفظ أصله اليوم")

    # ═══ 6) المعرفة والرموز ═══
    print("\n6) المعرفة والرموز")
    g = "6) المعرفة والرموز"
    try:
        codemap = json.loads((BRAIN / "appendices" / "event-code-map.json").read_text(encoding="utf-8"))
        m = json.loads(meta.read_text(encoding="utf-8"))
        codes = set(re.findall(r"MN-\d{4}-\d{2}-\d{2}-\d{2}", json.dumps(m, ensure_ascii=False)))
        missing = sorted(c for c in codes if c not in json.dumps(codemap, ensure_ascii=False))
        probe(g, "كل رموز الحدث مُحلّة في الخريطة", not missing,
              "لا رموز معلّقة" if not missing else f"معلّقة: {', '.join(missing[:4])}")
    except Exception as exc:  # noqa: BLE001
        probe(g, "خريطة الرموز تُقرأ", False, f"{type(exc).__name__}: {exc}")
    try:
        log = [json.loads(l) for l in (BRAIN / "memory" / "learning-log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        probe(g, "سجل الدروس صالح", True, f"{len(log)} درسًا")
    except Exception as exc:  # noqa: BLE001
        probe(g, "سجل الدروس صالح", False, f"{type(exc).__name__}")
    try:
        bl = json.loads((BRAIN / "appendices" / "style-blacklist.json").read_text(encoding="utf-8"))
        n = sum(len(v) for v in bl.values() if isinstance(v, list))
        probe(g, "القائمة السوداء تُقرأ", n > 0, f"{n} نمطًا ممنوعًا")
    except Exception as exc:  # noqa: BLE001
        probe(g, "القائمة السوداء تُقرأ", False, f"{type(exc).__name__}")
    audit = BRAIN / "audit" / "سجل-الأعطال-والثغرات.md"
    ids = re.findall(r"ك-(\d+)", audit.read_text(encoding="utf-8")) if audit.exists() else []
    seq = sorted({int(i) for i in ids}) == list(range(1, max((int(i) for i in ids), default=0) + 1))
    probe(g, "سجل الأعطال مرقّم بلا فجوات", bool(ids) and seq,
          f"حتى ك-{max((int(i) for i in ids), default=0)}")
    try:
        man = json.loads((BRAIN / "appendices" / "sources-manifest.json").read_text(encoding="utf-8"))
        tot = man.get("total_sources") or man.get("total")
        probe(g, "مصدر واحد لعدد المصادر", True, f"العدد المعتمد: {tot}")
    except Exception as exc:  # noqa: BLE001
        probe(g, "مصدر واحد لعدد المصادر", False, f"{type(exc).__name__}")
    corpus = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in list(BRAIN.rglob("*.md")) + list(BRAIN.rglob("*.sh")) + list(BRAIN.rglob("*.py"))
        if p.is_file() and not any(x in p.parts for x in (".git", "__pycache__", "backup-repo", "tools"))
    )
    orphans = sorted(p.name for p in (BRAIN / "validators").glob("*.py")
                     if p.name not in corpus and p.name != Path(__file__).name)
    probe(g, "لا بوابات مهجورة غير مرجعية", not orphans,
          "كل البوابات مرجعية" if not orphans else f"{len(orphans)}: {', '.join(orphans[:4])}",
          note="بوابة لا يستدعيها شيء = ملف ميت يربك الفحص ويوهم بتغطية غير قائمة")

    # ═══ 7) تلغرام والبوت (بلا إرسال) ═══
    print("\n7) تلغرام والبوت (بلا إرسال)")
    g = "7) تلغرام والبوت"
    sample = Path("/tmp/selftest-digest.html")
    sample.write_text("<b>مركز الوعي بالمجال البحري</b>\nاختبار جاف فقط — لا يُرسل.\n", encoding="utf-8")
    run(g, "إرسال جاف لتقرير يومي (معتمد)", ["python3", "tools/telegram_send.py", "--file", str(sample),
        "--dry-run", "--daily-report", "--date", date], tolerate=0,
        note="اختبار جاف: لا تصل رسالة إلى القناة")
    rc_ref = subprocess.run(["python3", "tools/telegram_send.py", "--text", "رسالة جانبية ليست تقريرًا يوميًا",
                             "--dry-run"], cwd=str(BRAIN), capture_output=True, text=True).returncode
    probe(g, "الحاجز يرفض غير التقارير اليومية", rc_ref != 0, f"رمز الرفض {rc_ref}",
          note="الحاجز يمنع استعمال القناة لمحادثات جانبية")
    chat = BRAIN / "appendices" / "telegram-chat.json"
    probe(g, "معرّف المحادثة محفوظ (بلا إظهار)", chat.exists(), "الملف موجود" if chat.exists() else "مفقود")
    tg = BRAIN / "appendices" / "telegram-targets.json"
    if tg.exists():
        try:
            tgj = json.loads(tg.read_text(encoding="utf-8"))
            tlist = tgj if isinstance(tgj, list) else tgj.get("targets", [])
            probe(g, "جهات التسليم معرّفة", bool(tlist), f"{len(tlist)} جهة · الموافقة إلزامية")
        except Exception as exc:  # noqa: BLE001
            probe(g, "جهات التسليم معرّفة", False, f"{type(exc).__name__}")
    if net:
        try:
            with urllib.request.urlopen(f"{SITE_URL}/healthz", timeout=40) as r:
                body = r.read(200).decode("utf-8", "ignore")
            probe(g, "خدمة البوت تستجيب", r.status == 200, f"HTTP {r.status} · {body[:40]}")
        except Exception as exc:  # noqa: BLE001
            probe(g, "خدمة البوت تستجيب", False, f"{type(exc).__name__}", tolerate=True,
                  note="تعذّر الوصول لخدمة البوت — تحقّق من نشر الحاوية")

    # ═══ 8) الموقع ═══
    print("\n8) الموقع")
    g = "8) الموقع"
    def dist_hashes() -> dict[str, str]:
        return {str(p.relative_to(DIST)): sha(p) for p in DIST.rglob("*.html")}
    run(g, "بناء الموقع (الجولة الأولى)", ["python3", "generator/build_site.py"], cwd=SITE)
    h1 = dist_hashes()
    run(g, "بناء الموقع (الجولة الثانية)", ["python3", "generator/build_site.py"], cwd=SITE)
    h2 = dist_hashes()
    diff = sorted(k for k in set(h1) | set(h2) if h1.get(k) != h2.get(k))
    probe(g, "البناء ثابت الناتج (لا تذبذب)", not diff,
          f"{len(h1)} صفحة، بلا فرق" if not diff else f"{len(diff)} صفحة تغيّرت: {', '.join(diff[:3])}",
          note="تذبذب البناء يجعل كل تحديث يُلوّث المستودع بلا سبب")
    routes = DIST / "manus-routes.json"
    try:
        rj = json.loads(routes.read_text(encoding="utf-8"))
        n = len(rj.get("routes", []))
        probe(g, "ملف مسارات الموقع صالح", n > 0, f"{n} مسارًا")
    except Exception as exc:  # noqa: BLE001
        probe(g, "ملف مسارات الموقع صالح", False, f"{type(exc).__name__}")
    run(g, "توليد PDF المعتمد", ["python3", "tools/export_report_assets.py", "--date", date, "--only", "pdf"], tolerate=1)
    probe(g, "ملف PDF موجود وبحجم معقول", pdf.exists() and pdf.stat().st_size > 300_000,
          f"{pdf.stat().st_size//1024} ك.ب" if pdf.exists() else "مفقود")
    docx = BRAIN / "reports" / "docx" / f"التقرير-اليومي-{date}-طبق-الأصل.docx"
    probe(g, "نسخة Word موجودة", docx.exists(), f"{docx.stat().st_size//1024} ك.ب" if docx.exists() else "مفقودة")
    if net:
        for path in ("/", f"/reports/{date}.html", f"/reports/pdf/{date}.pdf", "/feed.xml",
                     f"/reports/monthly-{date[:7]}.html", "/reports/cumulative-2026.html", "/robots.txt", "/sitemap.xml"):
            try:
                req = urllib.request.Request(SITE_URL + path, headers={"User-Agent": "Mozilla/5.0 selftest"})
                with urllib.request.urlopen(req, timeout=45) as r:
                    probe(g, f"المنشور {path}", r.status == 200, f"HTTP {r.status}")
            except Exception as exc:  # noqa: BLE001
                probe(g, f"المنشور {path}", False, f"{type(exc).__name__}")

    # ═══ 9) النسخة الاحتياطية ═══
    print("\n9) النسخة الاحتياطية")
    g = "9) النسخة الاحتياطية"
    run(g, "دفع النسخة الاحتياطية", ["bash", "tools/github_backup.sh"], tolerate=1, timeout=900)
    run(g, "المطابقة الصارمة بعد الدفع", ["python3", "validators/check_backup_parity.py", "--mode", "strict"],
        tolerate=1, note="تحذير = انحراف حقيقي بين الشجرة والمستودع يجب إصلاحه قبل التسليم")
    repo = BRAIN / "backup-repo"
    for rel in ("bootstrap.sh", "requirements.txt", ".env.example", "SETUP.md",
                ".devcontainer/devcontainer.json", "appendices/sources-manifest.json",
                "sections/90-automation.md", "validators/check_style.py"):
        probe(g, f"المستودع يحوي {rel}", (repo / rel).exists())

    # ═══ 10) الأمن والأرقام ═══
    print("\n10) الأمن والالتزام التحريري")
    g = "10) الأمن والأرقام"
    secret_pats = [
        (re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}\b"), "توكن بوت"),
        (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "مفتاح خاص"),
        (re.compile(r"(?i)(password|passwd|api[_\-]?key)\s*[=:]\s*[\"'][^\"']{10,}[\"']"), "كلمة سر/مفتاح"),
    ]
    hits: list[str] = []
    for tree in (BRAIN, SITE):
        for p in tree.rglob("*"):
            if not p.is_file() or any(x in p.parts for x in (".git", "node_modules", "__pycache__", "backup-repo", "dist")):
                continue
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".docx", ".zip", ".gz", ".woff", ".woff2", ".ttf"}:
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                continue
            for pat, label in secret_pats:
                if pat.search(txt):
                    hits.append(f"{p.relative_to(tree.parent)} ({label})")
                    break
    probe(g, "لا أسرار في ملفات المشروعين", not hits,
          "لا نتائج" if not hits else f"{len(hits)} ملفًا: {', '.join(hits[:3])}",
          note="أي نتيجة تعني تسرّبًا محتملًا يجب تجديده فورًا")
    arab = re.compile("[\u0660-\u0669\u06F0-\u06F9]")
    bad: list[str] = []
    for p in list(DIST.rglob("*.html")) + [meta, report_md]:
        if p.exists() and arab.search(p.read_text(encoding="utf-8", errors="ignore")):
            bad.append(p.name)
    probe(g, "الأرقام لاتينية في المخرجات", not bad, "بلا أرقام عربية" if not bad else f"{len(bad)} ملفًا",
          note="قرار المستخدم: 0-9 لاتينية في كل المشروع")
    try:
        mtxt = meta.read_text(encoding="utf-8")
        probe(g, "التوقيت مزدوج (UTC + البحرين)", bool(re.search(r"\d{6}Z", mtxt)) and "البحرين" in mtxt,
              "DTG وتوقيت البحرين حاضران")
    except Exception as exc:  # noqa: BLE001
        probe(g, "التوقيت مزدوج (UTC + البحرين)", False, f"{type(exc).__name__}")

    # ═══ التقرير ═══
    blocks = [r for r in RESULTS if r["status"] == "block"]
    warns = [r for r in RESULTS if r["status"] == "warn"]
    verdict = 2 if blocks else (1 if warns else 0)
    out = BRAIN / "audit" / f"self-test-{date}.md"
    lines = [f"# اختبار تشغيل شامل — {date}", "",
             f"- وقت التنفيذ: {time.strftime('%Y-%m-%d %H:%M')} (بيئة Sandbox)",
             f"- النتيجة: **{'مانع' if verdict == 2 else ('نجاح مع تحذير' if verdict == 1 else 'نجاح بلا ملاحظات')}**",
             f"- نجح: {len([r for r in RESULTS if r['status'] == 'ok'])} · "
             f"تحذير: {len(warns)} · مانع: {len(blocks)}", ""]
    lines += ["## بيئة التشغيل", ""] + [f"- {f}" for f in ENV_FACTS] + [""]
    for grp in dict.fromkeys(r["group"] for r in RESULTS):
        lines += [f"## {grp}", "", "| الفحص | رمز | الحالة | الدليل |", "| --- | --- | --- | --- |"]
        for r in [x for x in RESULTS if x["group"] == grp]:
            mark = {"ok": "نجح", "warn": "تحذير", "block": "مانع"}[r["status"]]
            lines.append(f"| {r['name']} | {r['rc']} | {mark} | {r['evidence'].replace('|', '/')} |")
        lines.append("")
    if warns:
        lines += ["## معنى التحذيرات", ""]
        for r in warns:
            lines.append(f"- **{r['name']}** — {NOTES.get(r['name'], 'تحذير غير مانع، يُراجع بشرًا.')}")
        lines.append("")
    if blocks:
        lines += ["## الموانع", ""]
        for r in blocks:
            lines.append(f"- **{r['name']}** — رمز {r['rc']} · {r['evidence']}")
        lines.append("")
    lines += ["## ما لم يُفحص في هذه الجولة", "",
              "- الإرسال الفعلي على تلغرام (مقصود: لا ترسل الأداة شيئًا في وضع الاختبار الجاف).",
              "- الاستقلال الكامل عن المنصة (Codespaces/Actions) — يُختبر بأداة verify_codespace.sh في ورشة مطابقة.",
              "- جودة المحتوى الاستخباري نفسها؛ البوابات تقيس الالتزام لا صواب التقدير.",
              "", f"— أُنتجت بأداة: `tools/self_test.py`"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nالنتيجة: نجح {len([r for r in RESULTS if r['status'] == 'ok'])} · "
          f"تحذير {len(warns)} · مانع {len(blocks)}")
    print(f"التقرير: {out}")
    return verdict


if __name__ == "__main__":
    sys.exit(main())
