#!/usr/bin/env python3
"""حكم النشر الموحّد: يقرأ نتيجة بوابة التسليم والعلامة اليومية ويُخرج قرارًا واحدًا.

العلّة المقيسة (تشغيل 2026-11-19): يوجد سلّمان للرموز. بوابة التسليم
``tools/final_gate.sh`` تُخرج 0 نجاح · 1 نجاح مع تحذير · 2 مانع، بينما قاعدة
المالك للعلامة اليومية (CLAUDE.md، القاعدة 1) هي 0 سليم · 3 منقوص مُفصح · غير
ذلك فاشل. وأمر المهمة المجدولة كان يقول «رمز final_gate 0 أو 3»، و3 لا تصدر
عن البوابة أصلًا، فاضطر المشغّل إلى تفسير الرمز 1 بنفسه عند النشر.

هذه الأداة لا تشغّل أي بوابة ولا تخفف أي شرط. هي تقرأ ما كتبته البوابة
والعلامة فقط، وتترجمه إلى سلّم المالك:

  0  سليم        : بوابة التسليم 0، والعلامة ok، والنص لم يتغيّر بعد البوابة.
  3  منقوص مُفصح : بوابة التسليم 0 أو 1 بلا أي خطوة مانعة أو منهارة، والعلامة
                    ok أو degraded، والنص لم يتغيّر بعد البوابة.
  2  ممنوع       : أي شيء آخر (بوابة غائبة أو غير نهائية أو لتاريخ آخر، أو
                    مانع، أو انهيار، أو علامة failed، أو نص تغيّر بعد البوابة).

النشر مسموح عند 0 أو 3 فقط. الاستعمال:
  python3 tools/publish_verdict.py --date YYYY-MM-DD [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

BRAIN = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])

SOUND, DISCLOSED, BLOCKED = 0, 3, 2
LABELS = {SOUND: "سليم", DISCLOSED: "منقوص مُفصح", BLOCKED: "ممنوع"}


def _load(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def verdict(brain: Path, date: str) -> dict:
    reasons: list[str] = []
    gate_dir = brain / "logs" / f"gate-{date}"
    gate = _load(gate_dir / "gate.json")
    mark = _load(brain / "logs" / f"pipeline-{date}.json")
    stamp = _load(gate_dir / f".text-hash-{date}.json")
    report = brain / "reports" / f"{date}-sectioned.md"

    gate_rc = None
    if gate is None:
        reasons.append("نتيجة بوابة التسليم غائبة أو غير مقروءة (logs/gate-D/gate.json)")
    else:
        gate_rc = gate.get("exit_code")
        if gate.get("date") != date:
            reasons.append(f"نتيجة البوابة لتاريخ آخر: {gate.get('date')!r}")
        if gate.get("stage") != "final":
            reasons.append(f"نتيجة البوابة غير نهائية: stage={gate.get('stage')!r}")
        if gate_rc not in (0, 1):
            reasons.append(f"رمز بوابة التسليم {gate_rc!r} ليس 0 ولا 1")
        bad = [s.get("step") for s in gate.get("steps", []) if s.get("status") in ("block", "crash")]
        if bad:
            reasons.append("خطوات مانعة أو منهارة في البوابة: " + " · ".join(map(str, bad)))

    overall = None
    if mark is None:
        reasons.append("العلامة اليومية غائبة أو غير مقروءة (logs/pipeline-D.json)")
    else:
        overall = mark.get("overall")
        if mark.get("date") != date:
            reasons.append(f"العلامة لتاريخ آخر: {mark.get('date')!r}")
        if overall not in ("ok", "degraded"):
            reasons.append(f"حالة العلامة {overall!r} ليست ok ولا degraded")
        fg = mark.get("final_gate") or {}
        if gate is not None and fg.get("exit_code") != gate_rc:
            reasons.append(f"رمز البوابة في العلامة ({fg.get('exit_code')!r}) يخالف gate.json ({gate_rc!r})")

    current = _sha(report)
    if current is None:
        reasons.append(f"النص النهائي غائب: {report.relative_to(brain)}")
    elif stamp is None or stamp.get("sha256") != current:
        reasons.append("النص تغيّر بعد بوابة التسليم أو بصمته غائبة؛ أعد البوابة قبل النشر")

    # الإصلاح الذاتي (اعتماد فهد 21 نوفمبر): سطح معزول أو تشغيل محتجز لا يُحكم سليمًا أبدًا.
    heal = _load(brain / "logs" / "auto-heal" / f"{date}.json") or {}
    isolated = sorted((heal.get("isolated") or {}).keys())
    if heal.get("holds"):
        reasons.append("احتجاز ذاتي لعطل محتوى لم يُرفع: " + " · ".join(
            str(h.get("step")) for h in heal["holds"]) + f" (logs/auto-heal/{date}.md)")

    if reasons:
        code = BLOCKED
    elif gate_rc == 0 and overall == "ok" and not isolated:
        code = SOUND
    else:
        code = DISCLOSED
    return {
        "date": date,
        "verdict": code,
        "label": LABELS[code],
        "publish_allowed": code in (SOUND, DISCLOSED),
        "final_gate_exit_code": gate_rc,
        "mark_overall": overall,
        "report_sha256": current,
        "reasons": reasons,
        "isolated": isolated,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="حكم النشر الموحّد (0 سليم · 3 منقوص مُفصح · 2 ممنوع)")
    ap.add_argument("--date", required=True)
    ap.add_argument("--brain", default=str(BRAIN))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    result = verdict(Path(args.brain).resolve(), args.date)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        state = "مسموح" if result["publish_allowed"] else "ممنوع"
        print(f"حكم النشر {args.date}: {result['label']} (رمز {result['verdict']}) · النشر {state}")
        for reason in result["reasons"]:
            print(f"  ✘ {reason}")
        for surface in result["isolated"]:
            print(f"  ⚠ سطح معزول بالإصلاح الذاتي: {surface} (منقوص مُفصح)")
    return result["verdict"]


if __name__ == "__main__":
    sys.exit(main())
