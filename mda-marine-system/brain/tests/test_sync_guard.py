#!/usr/bin/env python3
"""اختبار سلبي/إيجابي لحارس الحذف في sync_to_repo.py (ك-269).

الحارس يمنع: حذفًا خارج نطاق المصدر · حذفًا يتجاوز 20 ملفًا — إلا بعلم --allow-delete.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

NL = chr(10)
TOOL = str(Path(__file__).resolve().parents[1] / "tools" / "sync_to_repo.py")


def run(brain, repo, *extra):
    return subprocess.run([sys.executable, TOOL, "--brain", brain, "--repo", repo, *extra],
                          capture_output=True, text=True)


ok = True

with tempfile.TemporaryDirectory() as d:
    src = Path(d) / "brain"
    dst = Path(d) / "repo"
    src.mkdir()
    dst.mkdir()
    (src / "a.md").write_text("نص" + NL, encoding="utf-8")
    (dst / "skills").mkdir()
    (dst / "skills" / "x.md").write_text("مهارة" + NL, encoding="utf-8")

    r = run(str(src), str(dst))
    good = r.returncode == 2 and (dst / "skills" / "x.md").exists()
    ok &= good
    print(f"  {'✔' if good else '✘'} ملف خارج النطاق بلا علم → مُنع (rc={r.returncode}) والملف باقٍ")

    r = run(str(src), str(dst), "--allow-delete")
    good = r.returncode == 0 and not (dst / "skills" / "x.md").exists()
    ok &= good
    print(f"  {'✔' if good else '✘'} مع --allow-delete → نُفّذ (rc={r.returncode}) والملف حُذف")

with tempfile.TemporaryDirectory() as d:
    src = Path(d) / "brain"
    dst = Path(d) / "repo"
    src.mkdir()
    dst.mkdir()
    (src / "keep.md").write_text("نص" + NL, encoding="utf-8")
    for i in range(25):
        (dst / f"old{i}.md").write_text("قديم" + NL, encoding="utf-8")

    r = run(str(src), str(dst))
    good = r.returncode == 2 and (dst / "old0.md").exists()
    ok &= good
    print(f"  {'✔' if good else '✘'} حذف 25 ملفًا فوق السقف 20 → مُنع (rc={r.returncode})")

    r = run(str(src), str(dst), "--dry-run")
    good = r.returncode == 2
    ok &= good
    print(f"  {'✔' if good else '✘'} التجربة تُظهر الخطة وتمنع التنفيذ (rc={r.returncode})")

print("  الحصيلة:", "كل الاختبارات نجحت ✔" if ok else "فشل ✘")
sys.exit(0 if ok else 2)