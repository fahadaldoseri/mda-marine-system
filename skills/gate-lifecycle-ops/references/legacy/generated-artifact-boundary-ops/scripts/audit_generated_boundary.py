#!/usr/bin/env python3
"""جرد وقياس حدّ الأصل المولَّد في مشروع محكوم بثلاثة أصناف (code · data · generated).

يفحص أربعة أمور على المواصفة الحاكمة نفسها:
  1) وجود قائمة تجاهُل غير فارغة للأصول المولَّدة.
  2) أن كل نمط تجاهُل يُصنَّف فعلًا «generated» على مسار عيّنة مُشتق من النمط.
  3) أن المستودع لا يتعقّب أي ملف يطابق أنماط التجاهُل.
  4) أن كل ملف شيفرة موجود على الخادم متتبَّع في المستودع (لا شيفرة غير متتبَّعة).

الاستعمال:
  audit_generated_boundary.py --brain DIR --repo DIR [--spec PATH] [--json OUT] [--quiet]

رموز الخروج: 0 سليم · 2 مخالف · 70 تعذّر القياس (فشل مغلق).
"""
import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

RUNNABLE = 70
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", "dist", ".venv", "venv"}
SPEC_RELS = ("brain/appendices/code-paths.json", "appendices/code-paths.json")
PREFIXES = ("brain", "site", "skills")


def load_classifier(brain: Path):
    """يستعمل مكتبة المشروع إن وُجدت، وإلا مطابقة محلية بنفس الدلالة."""
    mod_path = brain / "tools" / "code_paths.py"
    if mod_path.is_file():
        sys.path.insert(0, str(mod_path.parent))
        try:
            import code_paths  # type: ignore
            return code_paths.classify, code_paths.is_ignored, "tools/code_paths.py"
        except Exception:
            pass

    def _match(rel, pat):
        if pat.endswith("/**") and (rel == pat[:-3] or rel.startswith(pat[:-2])):
            return True
        return fnmatch.fnmatchcase(rel, pat)

    def classify(rel, spec):
        rel = rel[2:] if rel.startswith("./") else rel
        if any(_match(rel, p) for p in spec.get("ignore", ())):
            return "generated"
        if any(_match(rel, p) for p in spec["code"]):
            return "code"
        if any(_match(rel, p) for p in spec["data"]):
            return "data"
        return None

    def is_ignored(rel, spec):
        rel = rel[2:] if rel.startswith("./") else rel
        return any(_match(rel, p) for p in spec.get("ignore", ()))

    return classify, is_ignored, "مطابقة محلية"


def sample_for_pattern(pat: str) -> str:
    """يشتق مسار عيّنة من نمط: `**/*.pyc` ⇒ `probe/a.pyc`."""
    parts = []
    for seg in pat.split("/"):
        if seg == "**":
            parts.append("probe")
        elif seg == "*":
            parts.append("a.pyc" if pat.endswith(".pyc") else "a")
        elif "*" in seg:
            parts.append(seg.replace("*", "a"))
        else:
            parts.append(seg)
    return "/".join(p for p in parts if p)


def tracked_files(repo: Path):
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"],
                         capture_output=True, check=True, timeout=180).stdout
    return {p.decode("utf-8") for p in out.split(b"\0") if p}


def walk_code_files(brain: Path, repo_root_map):
    """ملفات الشيفرة على الخادم: تُبنى مساراتها النسبية إلى المستودع."""
    for prefix, root in repo_root_map.items():
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            yield f"{prefix}/{p.relative_to(root).as_posix()}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brain", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--site", default=None)
    ap.add_argument("--skills", default=None)
    ap.add_argument("--spec", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    brain = Path(a.brain).resolve()
    repo = Path(a.repo).resolve()
    spec_path = Path(a.spec) if a.spec else next(
        (brain / r for r in SPEC_RELS if (brain / r).is_file()), None)
    if spec_path is None or not spec_path.is_file():
        print(f"✘ تعذّر القياس (فشل مغلق {RUNNABLE}): لا مواصفة تصنيف في {brain}")
        return RUNNABLE
    if not (repo / ".git").exists():
        print(f"✘ تعذّر القياس (فشل مغلق {RUNNABLE}): {repo} ليس مستودعًا")
        return RUNNABLE

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    classify, is_ignored, engine = load_classifier(brain)
    report = {"spec": str(spec_path), "engine": engine, "problems": [], "counts": {}}
    if not a.quiet:
        print(f"   المواصفة: {spec_path}")
        print(f"   محرّك التصنيف: {engine}")

    # 1) قائمة التجاهُل
    ignore = spec.get("ignore") or []
    report["counts"]["ignore_patterns"] = len(ignore)
    if not ignore:
        report["problems"].append("قائمة التجاهُل غائبة أو فارغة في المواصفة الحاكمة")
    if not a.quiet:
        print(f"   أنماط التجاهُل: {len(ignore)}")

    # 2) كل نمط يُصنَّف generated على عيّنة
    bad_patterns = []
    for pat in ignore:
        sample = sample_for_pattern(pat)
        got = classify(sample, spec)
        if got != "generated":
            bad_patterns.append(f"{pat} ⇒ {got} على {sample}")
    report["counts"]["patterns_failing_sample"] = len(bad_patterns)
    report["problems"].extend(f"نمط تجاهُل لا يُصنَّف generated: {b}" for b in bad_patterns)
    if not a.quiet:
        print(f"   أنماط فشلت عيّنتها: {len(bad_patterns)}")

    # 3) المولَّد المتعقَّب في المستودع
    tracked = tracked_files(repo)
    tracked_generated = sorted(t for t in tracked if is_ignored(t, spec))
    report["counts"]["tracked_total"] = len(tracked)
    report["counts"]["tracked_generated"] = len(tracked_generated)
    report["problems"].extend(f"ملف مولَّد متعقَّب: {t}" for t in tracked_generated)
    if not a.quiet:
        print(f"   متعقَّب في المستودع: {len(tracked)} · منها مولَّد: {len(tracked_generated)}")

    # 4) شيفرة على الخادم غير متتبَّعة
    roots = {"brain": brain,
             "site": Path(a.site).resolve() if a.site else brain.parent / "seawatch",
             "skills": Path(a.skills).resolve() if a.skills else brain.parent / "skills"}
    untracked = []
    for rel in walk_code_files(brain, roots):
        if classify(rel, spec) == "code" and rel not in tracked:
            untracked.append(rel)
    untracked.sort()
    report["counts"]["untracked_code"] = len(untracked)
    report["problems"].extend(f"شيفرة على الخادم غير متتبَّعة: {t}" for t in untracked[:40])
    if not a.quiet:
        print(f"   شيفرة على الخادم غير متتبَّعة: {len(untracked)}")

    if a.json:
        Path(a.json).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                encoding="utf-8")

    if report["problems"]:
        print(f"✘ حدّ الأصل المولَّد مخالف: {len(report['problems'])} ملاحظة")
        for p in report["problems"][:25]:
            print(f"   · {p}")
        return 2
    print("✔ حدّ الأصل المولَّد سليم: قائمة تجاهُل فعّالة · صفر مولَّد متعقَّب · صفر شيفرة غير متتبَّعة")
    return 0


if __name__ == "__main__":
    sys.exit(main())