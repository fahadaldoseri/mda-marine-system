#!/usr/bin/env python3
"""بوابة العبور — تحويل إجراء مكتوب إلى تنفيذ قابل للقياس.

الترتيب الإلزامي: حالة الكتيب ← بصمتان قبل ← مصفوفة الأثر ← (التعديل يقع خارج البوابة) ←
بصمتان بعد ← مدير الانحدار ← حزمة البوابات ← الدليل ← قرار العبور.
أي فشل في الخطوات المانعة يعني «لا عبور»، ويُعاد الفحص كاملًا بعد الإصلاح.

الاستعمال:
  crossing_gate.py --from ت --to 0 --dry-run          إثبات الجاهزية بلا تعديل (انتقال تجريبي)
  crossing_gate.py --from 0 --to 1 --baseline <dir>   انتقال حقيقي بمقارنة البصمات
  خيارات إضافية: --parity (التماثل والطباعة) · --live (تحقق حي)

رمز الخروج: 0 عبور مُعلن · 2 لا عبور.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

BRAIN = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
SITE = Path(os.environ.get("SITE_DIR") or BRAIN.parent / "seawatch")


def sh(argv: list[str], root: Path, timeout: int = 1200) -> tuple[int, str]:
    env = {"B": str(root), "SITE": str(root.parent / "seawatch"), "PATH": "/usr/bin:/bin:/usr/local/bin",
           "HOME": str(Path.home()), "LANG": "C.UTF-8"}
    r = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=timeout, env=env)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="بوابة العبور")
    ap.add_argument("--root", default=str(BRAIN))
    ap.add_argument("--site", default=str(SITE))
    ap.add_argument("--from", dest="frm", required=True, help="المرحلة الحالية")
    ap.add_argument("--to", dest="to", required=True, help="المرحلة التالية")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--dry-run", action="store_true", help="انتقال تجريبي: لا يفترض تغييرًا")
    ap.add_argument("--baseline", help="مجلد بصمات «قبل» للمقارنة")
    ap.add_argument("--parity", action="store_true", help="تشغيل فحوص التماثل والطباعة")
    ap.add_argument("--live", action="store_true", help="تشغيل التحقق الحي")
    args = ap.parse_args()

    root, site = Path(args.root).resolve(), Path(args.site).resolve()
    evidence = root / "audit" / "gates" / f"{args.to}-{args.date}"
    evidence.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    def record(step: str, rc: int, note: str, blocking: bool = True):
        results.append({"step": step, "rc": rc, "blocking": blocking, "note": note[-240:]})
        print(f"   {'✔' if rc == 0 else ('✘' if blocking else '⚠')} {step}: {note.splitlines()[-1][:120] if note else 'rc=' + str(rc)}")

    # 1) حالة الكتيب: لا تشغيل متوازٍ
    r = subprocess.run(["pgrep", "-af", "runbook.py run"], capture_output=True, text=True)
    busy = [ln for ln in r.stdout.splitlines() if ln.strip() and "pgrep" not in ln]
    record("1 حالة الكتيب — لا تشغيل متوازٍ", 2 if busy else 0,
           "تشغيل كتيب جارٍ: " + busy[0] if busy else "لا جولة معلّقة")

    # 2) بصمتان «قبل»
    pre = evidence / "before"
    pre.mkdir(exist_ok=True)
    rc1, o1 = sh(["python3", "tools/surface_fingerprint.py", "--root", str(root), "--site", str(site),
                  "--tag", f"before-{args.frm}-{args.to}", "--out", str(pre / "surfaces.json")], root)
    rc2, o2 = sh(["python3", "tools/number_fingerprint.py", "--root", str(root), "--site", str(site),
                  "--date", f"before-{args.frm}-{args.to}", "--out", str(pre / "numbers.json")], root)
    record("2 بصمة الأسطح قبل", rc1, o1)
    record("3 بصمة الأرقام قبل", rc2, o2)

    # 4) مصفوفة الأثر
    rc3, o3 = sh(["python3", "tools/impact_matrix.py", "--root", str(root), "--site", str(site),
                  "--from-git", "--out", str(evidence / "impact.json")], root)
    record("4 مصفوفة الأثر", rc3, o3)

    # 5) مدير الانحدار
    rc4, o4 = sh(["python3", "tools/regression_gate.py", "--root", str(root), "--until", args.frm,
                  "--out", str(evidence / "regression.json")], root)
    record("5 مدير الانحدار", rc4, o4)

    # 6) حزمة البوابات الأساسية
    rc5, o5 = sh(["python3", "tools/gate_coverage.py", "--root", str(root)], root)
    record("6 تغطية البوابات والمراجع", rc5, o5)
    for g in ("check_delivery_policy", "check_decisions_registry", "check_reference_generated"):
        rcg, og = sh(["python3", f"validators/{g}.py", "--root", str(root), "--summary"], root)
        record(f"6-{g}", rcg, og)

    # 7) بصمتان «بعد» + المقارنة
    post = evidence / "after"
    post.mkdir(exist_ok=True)
    sh(["python3", "tools/surface_fingerprint.py", "--root", str(root), "--site", str(site),
        "--tag", f"after-{args.frm}-{args.to}", "--out", str(post / "surfaces.json")], root)
    sh(["python3", "tools/number_fingerprint.py", "--root", str(root), "--site", str(site),
        "--date", f"after-{args.frm}-{args.to}", "--out", str(post / "numbers.json")], root)
    base_dir = Path(args.baseline) if args.baseline else pre
    rcs, os_ = sh(["python3", "tools/surface_fingerprint.py", "--root", str(root), "--site", str(site),
                   "--compare", str(base_dir / "surfaces.json")], root)
    rcn, on = sh(["python3", "tools/number_fingerprint.py", "--root", str(root), "--site", str(site),
                  "--compare", str(base_dir / "numbers.json")], root)
    block_surface = bool(os_ .strip()) and not args.dry_run
    record("7 فرق بصمة الأسطح", 0 if (os_.find("0 سطحًا متغيّرًا") >= 0 or args.dry_run) else 2, os_,
           blocking=block_surface)
    record("8 فرق بصمة الأرقام", 0 if (on.find("0 سطحًا تغيّرت أرقامه") >= 0 or args.dry_run) else 2, on,
           blocking=block_surface)

    # 9) التماثل والطباعة والتحقق الحي (اختياري صريح)
    if args.parity:
        rcp, op = sh(["python3", "validators/check_en_parity.py", "--root", str(root)], root)
        record("9 التماثل عربي/إنجليزي", rcp, op)
    else:
        record("9 التماثل والطباعة", 0, "لم يُطلب في هذه الدورة (يُطلب عند الانتقال الحقيقي)", blocking=False)
    if args.live:
        rcL, oL = sh(["bash", "-lc", f"for u in index additions sources feed.xml; do "
                     f"curl -s -o /dev/null -w '%{{http_code}} ' https://seawatch-xp4qirmr.manus.space/$u; done"], root)
        record("10 التحقق الحي", rcL if "200" not in oL else 0, oL)
    else:
        record("10 التحقق الحي", 0, "لم يُطلب في هذه الدورة", blocking=False)

    # 11) الدليل وقرار العبور
    blocked = [r for r in results if r["blocking"] and r["rc"] != 0]
    verdict = "لا عبور" if blocked else ("عبور مُعلن (انتقال تجريبي)" if args.dry_run else "عبور مُعلن")
    report = ["# تقرير عبور المرحلة", "",
              f"- من: المرحلة {args.frm} → إلى: المرحلة {args.to}",
              f"- التاريخ: {args.date}", f"- النمط: {'انتقال تجريبي' if args.dry_run else 'انتقال حقيقي'}",
              f"- القرار: **{verdict}**", "",
              "| الخطوة | rc | مانعة | الملاحظة |", "|---|---:|---|---|"]
    for r in results:
        report.append(f"| {r['step']} | {r['rc']} | {'نعم' if r['blocking'] else 'لا'} | {r['note'].splitlines()[-1][:120] if r['note'] else ''} |")
    (evidence / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (evidence / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"   الدليل: {evidence}")

    if blocked:
        print(f"✘ بوابة العبور: {len(blocked)} خطوة مانعة ساقطة — لا عبور")
        return 2
    print(f"✔ بوابة العبور: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
