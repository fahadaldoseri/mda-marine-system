#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات السجل الحاكم للمفردات وعدم التراجع وتغطية الأسطح.

الغرض: أن يبقى الحكم اللغوي في سجل واحد، وأن يُثبت آليًا أن كل بند معتمد يمنع فعلًا،
وأن كل سطح يقرأه القارئ داخل مدى البوابة.

الاختبارات
  1) السجل صالح ومُولَّده مطابق (build_vocab_gate --check).
  2) كل بند معتمد يمنع فعلًا في ملف اختبار (لا تراجع ولا حكم وهمي).
  3) لا بند مانع بلا سبب مكتوب ومصدر موثَّق.
  4) المُولَّد يُعاد بناؤه من السجل: التعديل اليدوي عليه يُكتشف.
  5) تغطية الأسطح: أداة القياس تُرجع 0 على أسطح اليوم (تُتخطّى موثَّقة إن لم يوجد بناء موقع).

الرمز: 0 نجاح · 1 فشل.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

B = pathlib.Path(__file__).resolve().parent.parent
SITE = pathlib.Path(os.environ.get("SITE") or os.environ.get("SITE_DIR") or (pathlib.Path.home() / "seawatch"))
REG = B / "appendices" / "simplified-vocabulary.json"
GEN = B / "appendices" / "forbidden-coinages.json"
sys.path.insert(0, str(B / "tools"))
sys.path.insert(0, str(B / "validators"))
import make_tg_digest
import build_vocab_gate
import lexicon_wiring
import check_prose_defects
fails: list[str] = []
skips: list[str] = []


def ok(name: str) -> None:
    print(f"  ✓ {name}")


def bad(name: str, why: str) -> None:
    fails.append(name)
    print(f"  ✘ {name} — {why}")


# Markdown source is not rendered prose: links retain their visible label, and
# repeated table cells remain structured data; repeated free prose stays blocking.
link_findings = check_prose_defects.find_punctuation_defects(
    "المصدر: [UKMTO](https://example.test/report)."
)
table_rows = "\n".join(
    f"| {i} | {name} | جلب ناجح؛ غير رسمي، لا يستخدم لإثبات الوقائع. |"
    for i, name in enumerate(("Source A", "Source B", "Source C"), 1)
)
free_prose = "\n".join(["جلب ناجح؛ غير رسمي، لا يستخدم لإثبات الوقائع."] * 3)
table_templates = check_prose_defects.find_repeated_templates(table_rows)
prose_templates = check_prose_defects.find_repeated_templates(free_prose)
if not link_findings and not table_templates and prose_templates:
    ok("تفسير Markdown يحفظ نص الرابط وحدود الجدول ويبقي النثر الحر مانعًا")
else:
    bad("تفسير Markdown يحفظ نص الرابط وحدود الجدول ويبقي النثر الحر مانعًا",
        f"link={len(link_findings)} · table={len(table_templates)} · prose={len(prose_templates)}")

# Current metadata uses event_keys as strings; legacy object-shaped keys remain supported.
digest_base = {
    "title": "تقرير اختبار",
    "version": "و ب 11/11/26",
    "generated_label": "2026-11-11T04:00:00Z",
    "threat_level": "مرتفع",
    "changes": [{"code": "MN-2026-11-11-01", "text": "نص ظاهر للاختبار"}],
}
try:
    current_digest = make_tg_digest.build(
        {**digest_base, "event_keys": ["MN-2026-11-11-01"]}, "2026-11-11", "https://example.test"
    )
    legacy_digest = make_tg_digest.build(
        {**digest_base, "event_keys": [{"code": "MN-2026-11-11-01", "title": "عنوان الحدث"}]},
        "2026-11-11", "https://example.test",
    )
    if "نص ظاهر للاختبار" in current_digest and "عنوان الحدث" in legacy_digest:
        ok("بناء رسالة تلغرام يقبل event_keys النصية والقاموسية")
    else:
        bad("بناء رسالة تلغرام يقبل event_keys النصية والقاموسية", "نص digest غير متوقع")
except Exception as exc:
    bad("بناء رسالة تلغرام يقبل event_keys النصية والقاموسية", f"{type(exc).__name__}: {exc}")


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=B)


# G034: السجل لا يوصي باللفظ الذي يمنعه، ولو جاء بين بدائل أو بتشكيل.
base_entry = {
    "term": "لا تؤكد", "plain": ["لم تؤكد"], "status": "approved",
    "source": "اختبار بنيوي", "reason": "اختبار", "since": "2026-11-12",
}
valid = build_vocab_gate.validate({"entries": [base_entry]})
self_conflicts = [
    build_vocab_gate.validate({"entries": [{**base_entry, "plain": [replacement]}]})
    for replacement in ("لا تؤكد", "لم تؤكد، لا تؤكد", "لا تُؤكّد، لم تؤكد")
]
rejected = build_vocab_gate.validate({"entries": [{**base_entry, "plain": ["لا تؤكد"], "status": "rejected"}]})
if not valid and not rejected and all(any("تناقض ذاتي" in error for error in errors) for errors in self_conflicts):
    ok("صلاحية السجل ترفض البديل الذاتي المباشر والمفصول والمشكّل وتقبل البديل السليم والمدخل المرفوض")
else:
    bad("حارس البديل الذاتي", f"valid={valid} · conflicts={self_conflicts} · rejected={rejected}")


with tempfile.TemporaryDirectory() as temp:
    original_paths = lexicon_wiring.REGISTRY, lexicon_wiring.LEXICON
    try:
        lexicon_wiring.REGISTRY = pathlib.Path(temp) / "registry.json"
        lexicon_wiring.LEXICON = pathlib.Path(temp) / "lexicon.md"
        lexicon_wiring.REGISTRY.write_text(json.dumps({"entries": [base_entry]}, ensure_ascii=False), encoding="utf-8")
        lexicon_wiring.LEXICON.write_text(
            "# المعجم الموحّد\n## أ)\n| المعنى | اكتب | لا تكتب |\n"
            "| لا تؤكد | لا تؤكد، لم تؤكد | لا تؤكد |\n## ب)\nنص محفوظ.\n",
            encoding="utf-8",
        )
        before = tuple(path.read_bytes() for path in (lexicon_wiring.REGISTRY, lexicon_wiring.LEXICON))
        code = lexicon_wiring.apply()
        after = tuple(path.read_bytes() for path in (lexicon_wiring.REGISTRY, lexicon_wiring.LEXICON))
        if code == 2 and before == after:
            ok("مولد المعجم يرفض صفًا ذاتيًا متناقضًا قبل أي كتابة")
        else:
            bad("رفض كتابة سجل متناقض", f"code={code} · unchanged={before == after}")
    finally:
        lexicon_wiring.REGISTRY, lexicon_wiring.LEXICON = original_paths


# 1) السجل صالح والمُولَّد مطابق
r = run([str(B / "tools" / "build_vocab_gate.py"), "--check"])
if r.returncode == 0:
    ok("السجل الحاكم صالح ومُولَّده مطابق")
else:
    bad("السجل الحاكم صالح ومُولَّده مطابق", (r.stdout + r.stderr).strip().splitlines()[:2])

reg = json.loads(REG.read_text(encoding="utf-8"))
approved = [e for e in reg["entries"] if e.get("status") == "approved"]

# 2) كل بند معتمد يمنع فعلًا
blocked_ok, not_blocking = [], []
import concurrent.futures as _cf, os as _os
_probe_dir = pathlib.Path(tempfile.mkdtemp(prefix="vocab_probe_"))


def _probe_rc(i_term):
    i, term = i_term
    probe = _probe_dir / f"vocab_probe_{i}.md"
    probe.write_text(f"# عنوان\n## قسم\n- {term} اختبار الإنفاذ.\n", encoding="utf-8")
    return term, subprocess.run([sys.executable, str(B / "validators" / "check_prose_defects.py"), "--md", str(probe)],
                                capture_output=True, text=True).returncode


with _cf.ThreadPoolExecutor(max_workers=_os.cpu_count() or 1) as _ex:
    for term, rc in _ex.map(_probe_rc, enumerate(str(e["term"]) for e in approved)):
        (blocked_ok if rc == 2 else not_blocking).append(term)
if not approved:
    bad("إنفاذ البنود المعتمدة", "لا بنود معتمدة في السجل")
elif not not_blocking:
    ok(f"كل البنود المعتمدة تمنع فعلًا ({len(blocked_ok)} بندًا)")
else:
    bad("إنفاذ البنود المعتمدة", f"بنود لا تمنع: {'، '.join(not_blocking)}")

# 3) لا بند مانع بلا سبب ومصدر
thin = [str(e["term"]) for e in approved
        if not str(e.get("reason") or "").strip() or not str(e.get("source") or "").strip()]
if thin:
    bad("سبب ومصدر مكتوبان لكل بند مانع", f"بنود ناقصة: {'، '.join(thin)}")
else:
    ok(f"سبب ومصدر مكتوبان لكل بند مانع ({len(approved)} بندًا)")

# 4) المُولَّد يُبنى من السجل: تعديل يدوي يُكتشف
orig = GEN.read_text(encoding="utf-8")
try:
    d = json.loads(orig)
    d["entries"].append({"term": "لفظ-اختبار-يدوي-لا-أصل-له", "since": "2026-01-01", "reason": "اختبار"})
    GEN.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rc = run([str(B / "tools" / "build_vocab_gate.py"), "--check"]).returncode
    if rc == 2:
        ok("التعديل اليدوي على المُولَّد يُكتشف ويُمنع")
    else:
        bad("التعديل اليدوي على المُولَّد يُكتشف ويُمنع", f"رمز={rc}")
finally:
    GEN.write_text(orig, encoding="utf-8")

# 5) تغطية الأسطح
day = sorted(p.name.replace("-sectioned.md", "") for p in (B / "reports").glob("*-sectioned.md"))[-1]
if not (SITE / "dist" / "index.html").exists():
    skips.append("تغطية الأسطح: لا بناء موقع في SITE — تُقاس في بوابة التسليم بعد البناء")
else:
    env = dict(os.environ, SITE=str(SITE))
    def _audit(d: str, gate_id: str | None = None):
        cmd = [sys.executable, str(B / "tools" / "audit_style_coverage.py"), "--date", d]
        if gate_id:
            cmd += ["--gate-id", gate_id]
        return subprocess.run(cmd,
                              capture_output=True, text=True, env=env)

    def _counts(out: str):
        m = re.search(r"الأسطح:\s*(\d+)\s*·\s*مغطاة:\s*(\d+)\s*·\s*مؤجلة معلنة:\s*(\d+)\s*·\s*غير مغطاة:\s*(\d+)\s*·\s*مانعة:\s*(\d+)", out or "")
        return tuple(int(x) for x in m.groups()) if m else None

    page_exists = (SITE / "dist" / "reports" / f"{day}.html").exists()
    # قبل البناء: يُقاس يوم الجولة نفسه بعقد G001؛ إعلان الصفحة لا يُقرأ من هذا الاختبار.
    r = _audit(day, None if page_exists else "G001")
    c = _counts(r.stdout)
    if not page_exists and r.returncode == 0 and c and c[2] == 1 and c[3] == 0 and c[4] == 0:
        ok(f"صفحة {day} مؤجلة معلنًا من المانيفست — إنفاذها في G045 بعد B010")
    elif r.returncode == 0:
        ok(f"تغطية الأسطح كاملة ({day}) — لا سطح خارج البوابة")
    else:
        bad("تغطية الأسطح", (r.stdout or "").strip().splitlines()[-1:] or r.returncode)

print(f"── الاختبارات: {len(fails)} فشل · {len(skips)} تخطٍّ موثَّق")
for s in skips:
    print(f"  ! {s}")
sys.exit(1 if fails else 0)
