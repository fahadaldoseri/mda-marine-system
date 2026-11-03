#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص ربط حاجز (اختبار أو مدقق) بخطوة في مشغّل المشروع، وبأن المشغّل سليم.

الغرض: منع البند المحمرّ «حاجز بلا مشغّل» — ملف اختبار أو مدقق أُضيف ولم يُربط
بخطوة أو قسم أو وثيقة، فيمنع التسليم برمز 2 من المشغّل نفسه بعد أن كان يُفترض
أنه حماية.

المدخلات: --project (افتراضيًا مجلد العمل) · --file مسار الحاجز (نسبةً للمشروع أو مطلقًا)
          --manifest (افتراضيًا runbook/runbook.json أو tools/final_gate.sh)
          --runner (افتراضيًا tools/runbook.py) · --skip-runner-verify

المخرج: 0 مربوط وسليم · 2 غير مربوط أو المشغّل أعلن خللًا. المخرجات نصّية سطرًا لكل فحص.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

CANDIDATE_MANIFESTS = ("runbook/runbook.json", "tools/final_gate.sh", "FINAL_GATE.sh")


def fail(msgs: list[str], line: str) -> None:
    msgs.append(line)
    print(f"   ✘ {line}")


def ok(line: str) -> None:
    print(f"   ✔ {line}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default=".")
    ap.add_argument("--file", required=True, help="مسار الحاجز: اختبار أو مدقق")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--runner", default="tools/runbook.py")
    ap.add_argument("--skip-runner-verify", action="store_true")
    args = ap.parse_args()

    project = pathlib.Path(args.project).resolve()
    if not project.is_dir():
        print(f"   ✘ مجلد المشروع غير موجود: {project}")
        return 2

    barrier = pathlib.Path(args.file)
    if not barrier.is_absolute():
        barrier = project / barrier
    problems: list[str] = []

    if not barrier.exists():
        fail(problems, f"ملف الحاجز غير موجود: {barrier}")
        return 2
    ok(f"ملف الحاجز موجود: {barrier.relative_to(project) if barrier.is_relative_to(project) else barrier}")

    manifest = pathlib.Path(args.manifest) if args.manifest else None
    if manifest is None:
        for cand in CANDIDATE_MANIFESTS:
            if (project / cand).exists():
                manifest = project / cand
                break
    if manifest is None or not manifest.exists():
        fail(problems, "لا يوجد مانيفست معروف (runbook/runbook.json أو tools/final_gate.sh)")
    else:
        text = manifest.read_text(encoding="utf-8", errors="ignore")
        rel = str(barrier.relative_to(project)) if barrier.is_relative_to(project) else str(barrier)
        if rel in text or barrier.name in text:
            ok(f"الحاجز مذكور في {manifest.relative_to(project)}: {rel}")
        else:
            fail(problems, f"الحاجز غير مربوط بأي خطوة: {rel} غير مذكور في {manifest.relative_to(project)}")

    runner = project / args.runner
    if args.skip_runner_verify or not runner.exists():
        ok(f"لم يُشغَّل تحقق المشغّل (runner={'موجود' if runner.exists() else 'غير موجود'} · skip={args.skip_runner_verify})")
    else:
        try:
            proc = subprocess.run(
                [sys.executable, str(runner), "verify"],
                cwd=project, capture_output=True, text=True, timeout=600,
            )
        except subprocess.TimeoutExpired:
            fail(problems, "تحقق المشغّل تجاوز المهلة")
        else:
            if proc.returncode == 0:
                ok("تحقق المشغّل: خرج 0")
            else:
                last = [ln for ln in (proc.stdout + proc.stderr).splitlines() if ln.strip()]
                fail(problems, f"تحقق المشغّل: خرج {proc.returncode} — {last[-1][:150] if last else 'بلا مخرَج'}")

    if problems:
        print(f"\n   النتيجة: غير مربوط ({len(problems)}) — أضف الحاجز إلى خطوة في المانيفست ثم أعد التوليد والتحقق.")
        return 2
    print("\n   النتيجة: مربوط وسليم")
    return 0


if __name__ == "__main__":
    sys.exit(main())
