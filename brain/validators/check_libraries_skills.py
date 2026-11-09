#!/usr/bin/env python3
"""مدقّق سلامة المكتبات والمهارات والترابط بينها وبين الأوامر.

يقيس ستة أبعاد، وكل نتيجة دليل لا رأي:
  1. سلامة المكتبات: تُقرأ، وبنيتها متوقعة، ولا بند فارغ أو نص مؤقت.
  2. ارتباط المكتبات: من يقرأ كل مكتبة — مهارة أو قسم تعليمات أو مدقّق أو أداة.
  3. سلامة المهارات: الترويسة، وكل رابط مرجعي يُحلّ إلى ملف موجود.
  4. إنفاذ القواعد: كل قاعدة ملزمة يقابلها مدقّق ينفّذها.
  5. ترابط البوابات: لا مدقّق معطّل، ولا أداة مذكورة في الإجراء وغير موجودة.
  6. التماثل والنقل: نسخة المهارة في المستودع مطابقة، ولا مسار مطلق يكسر النقل.

الخروج: 0 سليم · 1 تحذير · 2 عائق.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
LIBS = B / "appendices" / "libraries"
def _skills_dir(brain: Path) -> Path:
    """مجلد المهارات: SKILLS_DIR ← مسار الخادم إن وُجد ← skills/ في جذر المستودع (محمول)."""
    import os
    if os.environ.get("SKILLS_DIR"):
        return Path(os.environ["SKILLS_DIR"])
    if Path("/home/ubuntu/skills").is_dir():
        return Path("/home/ubuntu/skills")
    return brain.parent / "skills"

SKILLS = _skills_dir(B)
SKILL_NAMES = ("marine-news-brain", "military-arabic-editing")
def _site_dir(brain: Path) -> Path:
    """اختيار جذر الموقع من البيئة أو من تخطيطات brain/site وbrain/../seawatch."""
    candidates = [os.environ.get("SITE_DIR"), os.environ.get("SITE"),
                  str(brain.parent / "site"), str(brain.parent / "seawatch"),
                  str(brain.parent.parent / "seawatch")]
    for value in candidates:
        if value and (Path(value) / "generator").is_dir():
            return Path(value)
    return brain.parent / "site"


SITE = _site_dir(B)
REPO_SKILLS = (Path(os.environ["BACKUP_REPO_DIR"]) / "skills" if os.environ.get("BACKUP_REPO_DIR")
               else (B.parent / "skills" if (B.parent / "skills").is_dir() and (B.parent / ".git").exists()
                     else B.parent / "mda-marine-system" / "skills"))

PLACEHOLDERS = ("TODO", "FIXME", "XXX", "۱۸", "lorem", "placeholder", "غير معروف بعد")
SECRET_PAT = re.compile(r"8949347226:|sk-[A-Za-z0-9]{20,}|bot\d{8,}:|chat_id\"\s*:\s*\"-?\d+")
ABS_PATH_PAT = re.compile(r"(?<![\w.])/(?:home|Users|workspaces)/[\w./-]+")

findings: list[tuple[str, str, str]] = []   # (درجة, البعد, الوصف)


def add(level: str, dim: str, msg: str) -> None:
    findings.append((level, dim, msg))


# ─────────────────────────── 1) سلامة المكتبات
def check_libs() -> None:
    if not LIBS.is_dir():
        add("عائق", "المكتبات", "مجلد المكتبات غير موجود")
        return
    files = sorted(p for p in LIBS.iterdir() if p.is_file())
    if not files:
        add("عائق", "المكتبات", "المجلد فارغ")
        return
    print(f"  1) المكتبات — {len(files)} ملفًا")
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception as e:                                   # noqa: BLE001
            add("عائق", "المكتبات", f"{f.name} لا يُقرأ بترميز UTF-8: {e}")
            continue
        print(f"     ✔ {f.name} · {len(text):,} حرفًا")
        if f.suffix == ".json":
            try:
                data = json.loads(text)
            except Exception as e:                               # noqa: BLE001
                add("عائق", "المكتبات", f"{f.name} JSON معطوب: {e}")
                continue
            if isinstance(data, dict) and not data:
                add("عائق", "المكتبات", f"{f.name} كائن فارغ")
            for k, v in (data.items() if isinstance(data, dict) else []):
                if v in ("", [], {}, None):
                    add("تحذير", "المكتبات", f"{f.name}: الحقل «{k}» فارغ")
        for ph in PLACEHOLDERS:
            if ph in text:
                add("تحذير", "المكتبات", f"{f.name} يحمل نصًا مؤقتًا: {ph}")
        if ABS_PATH_PAT.search(text):
            hits = set(ABS_PATH_PAT.findall(text))
            add("تحذير", "المكتبات",
                f"{f.name} يحمل مسارًا مطلقًا ({len(hits)}) يكسر النقل: {sorted(hits)[:2]}")
        if SECRET_PAT.search(text):
            add("عائق", "المكتبات", f"{f.name} يحمل ما يشبه سرًّا — يُحجب فورًا")


# ─────────────────────────── 2) ارتباط المكتبات
def check_lib_links() -> None:
    print("  2) ارتباط المكتبات بمن يقرؤها")
    consumers = [SKILLS / s for s in SKILL_NAMES]
    consumers += [B / "sections", B / "validators", B / "tools", B / "INDEX.md"]
    blob = ""
    for c in consumers:
        for p in ([c] if c.is_file() else c.rglob("*")) if c.exists() else []:
            if p.is_file() and p.suffix in (".md", ".py", ".sh", ".json"):
                try:
                    blob += p.read_text(encoding="utf-8", errors="ignore")
                except Exception:                                # noqa: BLE001
                    raise  # فشل مغلق: خطأ يخصّ حكم البوابة ⇒ رمز 70 (البند د)
    for f in sorted(p for p in LIBS.iterdir() if p.is_file()) if LIBS.is_dir() else []:
        stem = f.stem
        family = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", stem)
        family = family if len(family) >= 4 else ""
        readers = []
        for c in consumers:
            scope = [c] if c.is_file() else list(c.rglob("*")) if c.exists() else []
            for p in scope:
                if not p.is_file() or p.suffix not in (".md", ".py", ".sh", ".json"):
                    continue
                if p.parent == LIBS:
                    continue
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                    hit = stem in txt or (family and f"{family}-" in txt)
                    if hit:
                        readers.append(p.relative_to(B).as_posix())
                except Exception:                                # noqa: BLE001
                    raise  # فشل مغلق: خطأ يخصّ حكم البوابة ⇒ رمز 70 (البند د)
        readers = [r for r in readers if "libraries" not in r]
        gate_readers = [r for r in readers if r.startswith("validators/") or "final_gate" in r]
        skill_readers = [r for r in readers if "skills" in r or r.startswith("sections/")]
        if not readers:
            add("عائق", "الارتباط", f"{f.name}: لا يقرؤه أي مدقّق ولا تعليمة ولا مهارة — مكتبة يتيمة")
        elif not gate_readers and not skill_readers:
            add("تحذير", "الارتباط",
                f"{f.name}: يقرؤه أداة توليد فقط ({', '.join(readers[:2])}) ولا يصل إلى بوابة ولا تعليمة")
        else:
            print(f"     ✔ {f.name} ← {', '.join(readers[:3])}")
        if not gate_readers and readers:
            add("تحذير", "الارتباط", f"{f.name}: لا بوابة تقرؤه — لا يُنفَّذ على الإصدار")


# ─────────────────────────── 3) سلامة المهارات
def check_skills() -> None:
    print("  3) المهارات — الترويسة والروابط")
    for s in SKILL_NAMES:
        d = SKILLS / s
        f = d / "SKILL.md"
        if not f.is_file():
            add("عائق", "المهارات", f"{s}: SKILL.md مفقود")
            continue
        text = f.read_text(encoding="utf-8")
        if not text.startswith("---"):
            add("تحذير", "المهارات", f"{s}: لا ترويسة frontmatter")
        else:
            fm = text.split("---")[1]
            for need in ("name:", "description:"):
                if need not in fm:
                    add("تحذير", "المهارات", f"{s}: الترويسة بلا {need}")
        links = set(re.findall(r"references/[a-z0-9\-]+\.md", text))
        for l in sorted(links):
            ok = (d / l).is_file()
            print(f"     {'✔' if ok else '✘'} {s} → {l}")
            if not ok:
                add("عائق", "المهارات", f"{s}: رابط مرجعي معطوب — {l}")
        refs_dir = d / "references"
        if refs_dir.is_dir():
            for r in sorted(refs_dir.iterdir()):
                if r.name not in {Path(l).name for l in links}:
                    add("تحذير", "المهارات", f"{s}: مرجع غير مربوط بـ SKILL.md — {r.name}")
        if SECRET_PAT.search(text):
            add("عائق", "المهارات", f"{s}: SKILL.md يحمل ما يشبه سرًّا")
        # التماثل مع نسخة المستودع
        rp = REPO_SKILLS / s
        if rp.is_dir():
            # مقارنة الملفات فقط: المجلدات الفارغة لا يُعقّبها git فلا تُعدّ اختلافًا
            def files_of(root: Path) -> set:
                return {x.relative_to(root).as_posix() for x in root.rglob("*") if x.is_file()}
            live_f, repo_f = files_of(d), files_of(rp)
            only_live, only_repo = live_f - repo_f, repo_f - live_f
            changed = [f for f in (live_f & repo_f)
                       if (d / f).read_bytes() != (rp / f).read_bytes()]
            if only_live or changed:
                add("عائق", "التماثل",
                    f"{s}: المستودع ناقص {sorted(only_live)[:2]} · متغيّر {changed[:2]}")
            elif only_repo:
                add("تحذير", "التماثل", f"{s}: ملفات في المستودع فقط {sorted(only_repo)[:2]}")
            else:
                print(f"     ✔ {s} مطابقة لنسخة المستودع ({len(live_f)} ملفًا)")
        else:
            add("تحذير", "التماثل", f"{s}: غير موجودة في المستودع المحلي")


# ─────────────────────────── 4) إنفاذ القواعد
def check_enforcement() -> None:
    print("  4) إنفاذ القواعد الملزمة")
    gates = {p.name: p for p in (B / "validators").glob("*.py")}
    gate_txt = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in gates.values())
    RUNNERS = ("final_gate.sh", "publish_changes.sh", "verify_codespace.sh",
               "rebuild_report.sh", "export_report_assets.py", "self_test.py")
    fg_txt = ""
    for r in RUNNERS:
        f = B / "tools" / r
        if f.is_file():
            fg_txt += f.read_text(encoding="utf-8")
    # مدقّقات تُشغَّل عبر وسيط تستدعيه البوابة (language_gates.py) أو عبر خطوات المانيفست تُعدّ مُشغَّلة
    for extra in ("tools/language_gates.py", "runbook/runbook.json"):
        ep = B / extra
        if ep.is_file():
            fg_txt += "\n" + ep.read_text(encoding="utf-8")
    RULES = {
        "كل نص ثابت يدخل مدى بوابة الأسلوب": "check_style",
        "الرموز تُعرَّف في القاموس": "check_comprehension",
        "التعدادات نقاطًا": "check_points_rule",
        "الأرقام الإنجليزية": "check_numerals",
        "فضلاء الرموز MN/EST منفصلة": "check_code_spaces",
        "لا نقل خاطئ بين الإصدارات": "check_carryover",
        "مطابقة شكل PDF": "check_pdf_format",
        "تغطية فحص العقوبات": "check_ofac_coverage",
        "سلامة المهارات": "check_skills_integrity",
    }
    for rule, validator in RULES.items():
        has = validator in gate_txt or Path(validator + ".py").name in [g.name for g in gates.values()]
        run = validator in fg_txt
        if not has:
            add("عائق", "الإنفاذ", f"قاعدة «{rule}» بلا مدقّق")
        elif not run:
            add("عائق", "الإنفاذ", f"المدقّق {validator} لا تُشغّله بوابة التسليم")
        else:
            print(f"     ✔ {rule} ← {validator} (مُشغَّل في البوابة)")
    # كل مدقّق مُشغَّل
    for name in sorted(gates):
        if name in ("__init__.py",) or name.startswith("_"):
            continue
        if name[:-3] not in fg_txt:
            add("تحذير", "الإنفاذ", f"مدقّق غير مُستدعى في بوابة التسليم: {name}")


# ─────────────────────────── 5) ترابط البوابات والأدوات
def check_wiring() -> None:
    print("  5) ترابط البوابات والأدوات والإجراء")
    fg = B / "tools" / "final_gate.sh"
    fg_txt = fg.read_text(encoding="utf-8") if fg.is_file() else ""
    refs = set(re.findall(r"tools/([A-Za-z0-9_\-]+\.(?:sh|py))", fg_txt))
    for r in sorted(refs):
        ok = (B / "tools" / r).is_file()
        if not ok:
            add("عائق", "الترابط", f"بوابة التسليم تستدعي أداة غير موجودة: {r}")
    print(f"     أدوات تستدعيها البوابة: {len(refs)} · كلها موجودة"
          if all((B / 'tools' / r).is_file() for r in refs) else "     ✘ أداة مفقودة")
    auto = B / "sections" / "90-automation.md"
    if auto.is_file():
        a_txt = auto.read_text(encoding="utf-8")
        for r in sorted(set(re.findall(r"([A-Za-z0-9_\-]+\.(?:sh|py))", a_txt))):
            if not any((B / d / r).is_file() for d in ("tools", "validators", "memory")) \
               and not any((SITE / d / r).is_file()
                           for d in (".", "generator", "scripts", "tools")):
                add("تحذير", "الترابط", f"سلسلة التشغيل تذكر ملفًا غير موجود: {r}")
    lib_audit = "audit_libraries_skills" in fg_txt or "audit_corpus" in fg_txt
    print(f"     تدقيق المكتبات في البوابة: {'✔' if lib_audit else '✘'}")
    if not lib_audit:
        add("تحذير", "الترابط", "بوابة التسليم لا تدقّق المكتبات دوريًا (قاعدة معتمدة)")


# ─────────────────────────── 6) النقل والسرية
def check_portability() -> None:
    print("  6) النقل والسرية")
    # قياس واحد لقابلية النقل: يُقرأ من بوابته المستقلة (check_portable_paths)
    # بدل نسخة ثانية هنا تختلف عنها في النطاق — عطل ك-88.
    abs_hits = []
    try:
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "portable_paths_mod", B / "validators" / "check_portable_paths.py")
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)                                  # noqa: PLC0415
        abs_hits = list(_mod.scan())
    except Exception as e:                                             # noqa: BLE001
        abs_hits = [f"تعذّر تشغيل بوابة قابلية النقل ({e})"]

    if abs_hits:
        add("تحذير", "النقل", f"{len(abs_hits)} ملفًا بمسار مطلق (يكسر النقل): {abs_hits[:3]}")
    print(f"     مسارات مطلقة: {len(abs_hits)}")
    secrets = []
    for p in (B / "appendices").rglob("*"):
        if p.is_file() and p.suffix in (".json", ".md", ".txt"):
            try:
                if SECRET_PAT.search(p.read_text(encoding="utf-8", errors="ignore")):
                    secrets.append(p.name)
            except Exception:                                    # noqa: BLE001
                raise  # فشل مغلق: خطأ يخصّ حكم البوابة ⇒ رمز 70 (البند د)
    backup = (B / "tools" / "github_backup.py")
    sanitized = backup.read_text(encoding="utf-8") if backup.is_file() else ""
    for s in secrets:
        if s in sanitized:
            print(f"     ✔ {s} سرّي ومُستثنى/مُنقّى في النسخة الاحتياطية")
        else:
            add("عائق", "السرية", f"{s} يحمل ما يشبه سرًّا وغير مُنقّى في النسخة الاحتياطية")
    print(f"     ملفات بأسرار محتملة: {len(secrets)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="تدقيق سلامة المكتبات والمهارات والترابط")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    print("=== تدقيق المكتبات والمهارات والترابط ===")
    check_libs()
    check_lib_links()
    check_skills()
    check_enforcement()
    check_wiring()
    check_portability()
    print()
    blockers = [f for f in findings if f[0] == "عائق"]
    warns = [f for f in findings if f[0] == "تحذير"]
    print(f"النتيجة: {len(blockers)} عائق · {len(warns)} تحذير")
    for lvl, dim, msg in blockers + warns:
        print(f"  {'✘' if lvl == 'عائق' else '•'} [{dim}] {msg}")
    if blockers:
        return 2
    return 1 if warns else 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
