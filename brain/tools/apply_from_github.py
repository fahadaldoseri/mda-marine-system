#!/usr/bin/env python3
"""تطبيق الشيفرة والقواعد من نسخة المستودع (GitHub) على الخادم — GitHub مصدر الحقيقة للشيفرة (قرار المالك 2026-10-24).

يلمس فقط المسارات المصنَّفة code في appendices/code-paths.json تحت brain/ و site/ و skills/. لا يلمس البيانات أبدًا ولا يحذف شيئًا.
لكل ملف يقارن ثلاث بصمات: الخادم الآن · المطبَّق آخر مرة (logs/applied-code.json) · المستودع:
  الخادم = المستودع                      → لا شيء
  الخادم = المطبَّق سابقًا ≠ المستودع    → يُحدَّث (بعد أرشفة الأصل)
  الخادم عُدّل محليًا وبعيد عن المستودع   → تعارض: يُمنع التطبيق كله (رمز 3) ما لم يُطلب --accept-repo أو --force
بعد التطبيق يُشغَّل verify؛ إن فشل تُستعاد الأصول المؤرشفة (رمز 2).

الاستعمال:
  apply_from_github.py --repo DIR [--brain DIR] [--site DIR] [--skills DIR] [--dry-run] [--accept-repo] [--no-verify]
  --accept-repo : المستودع يفوز في كل تعارض (التطبيق الأول بعد اعتماد القرار)؛ تُؤرشف النسخ المستبدلة دائمًا.
رموز الخروج: 0 تم · 2 فشل التحقق بعد التطبيق (استُعيد) أو خطأ · 3 تعارض بلا إذن
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import code_paths  # noqa: E402


# لا تُكتب نسخ /home/ubuntu/skills داخل أرشيف التطبيق؛ تُحفظ مؤقتًا خارج الشجرة
# فقط لاسترجاع فشل التحقق في العملية نفسها.
ARCHIVE_EXCLUDE_TOPS = {"skills"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--brain", default=os.environ.get("BRAIN_DIR"))
    ap.add_argument("--site", default=os.environ.get("SITE_DIR"))
    ap.add_argument("--skills", default=os.environ.get("SKILLS_DIR"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--accept-repo", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo)
    brain = Path(a.brain) if a.brain else repo.parent / "brain-marine-news"
    site = Path(a.site) if a.site else repo.parent / "seawatch"
    skills = Path(a.skills) if a.skills else (Path("/home/ubuntu/skills") if Path("/home/ubuntu/skills").is_dir() else repo / "skills")
    roots = {"brain": brain, "site": site, "skills": skills}
    spec = code_paths.load_spec(repo)
    state_p = brain / "logs" / "applied-code.json"
    state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.is_file() else {"files": {}}
    applied = state.get("files", {})

    plan, conflicts, same = [], [], 0
    for rel in code_paths.tracked_files(repo):
        top, _, tail = rel.partition("/")
        if top not in roots or not tail or code_paths.classify(rel, spec) != "code":
            continue
        src = repo / rel
        if src.is_symlink() or not src.is_file():
            continue
        dst = roots[top] / tail
        rsha = sha(src)
        if not dst.exists():
            plan.append((rel, src, dst, rsha, "جديد"))
            continue
        ssha = sha(dst)
        if ssha == rsha:
            same += 1
            applied.setdefault(rel, rsha)
            continue
        if applied.get(rel) == ssha:
            plan.append((rel, src, dst, rsha, "تحديث"))
        else:
            conflicts.append((rel, src, dst, rsha))
    for rel, *_ in conflicts:
        print(f"⚠ تعارض (عُدّل على الخادم خارج GitHub): {rel}")
    if conflicts and not a.accept_repo:
        print(f"✘ {len(conflicts)} تعارض. لا شيء طُبّق. إن كان المستودع هو الصحيح: أعد التشغيل بـ --accept-repo (تُؤرشف نسخ الخادم أولًا).")
        return 3
    for rel, src, dst, rsha in conflicts:
        plan.append((rel, src, dst, rsha, "استبدال تعارض"))
    print(f"· مطابق: {same} · للتطبيق: {len(plan)}")
    for rel, _, _, _, why in plan:
        print(f"  {why}: {rel}")
    if a.dry_run or not plan:
        return 0

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arch = None
    rollback_root = Path(tempfile.mkdtemp(prefix="apply-rollback-"))
    done = []
    try:
        for rel, src, dst, rsha, why in plan:
            archiveable = rel.split("/", 1)[0] not in ARCHIVE_EXCLUDE_TOPS
            bak = None
            if dst.exists():
                if archiveable:
                    if arch is None:
                        arch = brain / "logs" / f"apply-{stamp}"
                    bak = arch / rel
                else:
                    bak = rollback_root / rel
                bak.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, bak)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            done.append((rel, dst, bak))
        if not a.no_verify and (brain / "tools" / "runbook.py").is_file():
            r = subprocess.run([sys.executable, str(brain / "tools" / "runbook.py"), "verify", "--root", str(brain)],
                               capture_output=True, text=True, env=dict(os.environ, BRAIN_DIR=str(brain), SITE_DIR=str(site)))
            if r.returncode != 0:
                raise RuntimeError("verify فشل بعد التطبيق:\n" + "\n".join(r.stdout.splitlines()[-8:]))
    except Exception as e:  # استعادة كاملة
        for rel, dst, bak in done:
            if bak is not None and bak.exists():
                shutil.copy2(bak, dst)
            elif dst.exists():
                dst.unlink()
        shutil.rmtree(rollback_root, ignore_errors=True)
        print(f"✘ {e}\n✘ استُعيدت الملفات كما كانت.")
        return 2
    shutil.rmtree(rollback_root, ignore_errors=True)
    for rel, src, dst, rsha, why in plan:
        applied[rel] = rsha
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    state_p.parent.mkdir(parents=True, exist_ok=True)
    state_p.write_text(json.dumps({"commit": head, "applied_utc": stamp, "files": applied}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✔ طُبّق {len(plan)} ملفًا من {head[:8]} — الأرشيف: {arch or 'لا أرشيف لمجلد skills'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
