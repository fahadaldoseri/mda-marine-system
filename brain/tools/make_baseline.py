#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يُجدِّد بيان خط الأساس الرسمي (virgin) من الشجرة الحالية.

يُستعمل فقط عند اعتماد تغيير مقصود على الشكل الرسمي، ويُسجِّل سبب الاعتماد
في البيان حتى يبقى الأثر واضحًا لمن يراجع لاحقًا.

الاستخدام:
  python3 tools/make_baseline.py --reason "اعتماد خريطة الحزمة الفاتحة"
"""
import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
BRAIN = Path(os.environ.get("BRAIN_DIR") or _ROOT)


def _tree(env, base, *names):
    v = os.environ.get(env)
    if v:
        return Path(v)
    for n in names:
        c = base.parent / n
        if c.is_dir():
            return c
    return base.parent / names[0]


SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")

# الملفات المُلزمة: أي تغيير فيها يغيّر شكل التقرير الرسمي أو بواباته
BRAIN_FILES = [
    "tools/export_report_assets.py", "validators/check_pdf_format.py",
    "validators/check_print_quality.py", "tools/final_gate.sh",
    "tools/rebuild_report.sh", "tools/publish_changes.sh",
    "tools/check_baseline.py", "tools/make_baseline.py",
    "templates/approved-pdf/print-profile.json",
    "templates/approved-pdf/print-css-frozen.css",
    "sections/30-structure.md", "sections/60-validation.md",
    "sections/70-delivery.md", "sections/75-style.md", "sections/90-automation.md",
]
SITE_FILES = [
    "generator/build_report.py", "generator/map_gulf.py", "generator/build_site.py",
    "generator/build_sources.py", "generator/site_chrome.py",
]
# ملفات مولَّدة لا تُبصم: يتغيّر محتواها كل بناء (معرّف PDF وزمن الإنشاء)، فيُقاس
# ناتجها بالبوابات (عدد الصفحات والتعبئة والخريطة) لا ببصمة الملف — عطل ك-127.
ARTIFACT_NOTES = {
    "dist/reports/pdf/2026-10-22.pdf": "يُقاس ببوابتي الشكل وجودة الطباعة (10 صفحات · خريطة 74% · تصفير 41%) لا بالبصمة",
}
MANIFEST = BRAIN / "templates" / "approved-pdf" / "BASELINE-virgin-2026-10-23.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_head(repo: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()[:7]
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reason", required=True, help="سبب تجديد خط الأساس (قرار موثَّق)")
    args = ap.parse_args()
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    man = dict(old) if old else {}
    man.setdefault("baseline", "virgin")
    man["on"] = "2026-10-23"
    man["status"] = "النسخة الرسمية المعتمدة الوحيدة — كل العمل عليها"
    man.setdefault("print_shape", {
        "name": "v3", "pages": 10, "page_range": "7–12", "body_pt": 10.8,
        "line_height": 1.62, "table_pt": 9.5,
        "map_print": "نموذج الحزمة: بحر #ffffff · يابسة #dfe4ea · ساحل #3f4f63",
    })
    prof_p = BRAIN / "templates/approved-pdf/print-profile.json"
    if prof_p.is_file():
        prof = json.loads(prof_p.read_text(encoding="utf-8"))
        man["print_shape"]["print_css_sha16"] = prof.get("print_css_sha16")
    man["files"] = {}
    for rel in BRAIN_FILES:
        f = BRAIN / rel
        if f.is_file():
            man["files"][rel] = {"sha256": sha256(f), "bytes": f.stat().st_size}
    for rel in SITE_FILES:
        f = SITE / rel
        if f.is_file():
            man["files"][rel] = {"sha256": sha256(f), "bytes": f.stat().st_size}
    man.setdefault("blessings", [])
    man["blessings"].append({
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": args.reason,
        "files": len(man["files"]),
    })
    man["artifacts"] = ARTIFACT_NOTES
    man["commits"] = {"site_repo": git_head(SITE), "brain_backup": git_head(Path("/home/ubuntu/mda-marine-system"))}
    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  ✔ جُدِّد خط الأساس: {len(man['files'])} ملفًا · سبب الاعتماد: {args.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())