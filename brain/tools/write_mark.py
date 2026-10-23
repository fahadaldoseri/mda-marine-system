#!/usr/bin/env python3
"""كتابة العلامة اليومية بعد البوابة بمخطط ثابت (ع-1 · قرار 2026-10-23).

العلامة كانت تُكتب داخل الخط اليومي قبل وجود نص التقرير، فلا تعرف نتيجته ولا أرقامه،
ويتغيّر شكلها من يوم لآخر. هنا تُحدَّث بعد البوابة بمخطط واحد: الحقول المعتمدة في
templates/mark-schema.json، وأرقام المصادر الثلاثة من بيانات التشغيل، ونتيجة البوابة.

الاستخدام:
  python3 tools/write_mark.py --date 2026-10-23 --stage final
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((B / "templates" / "mark-schema.json").read_text(encoding="utf-8"))
SCHEMA_VERSION = int(SCHEMA["version"])


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--stage", default="final", choices=["pipeline", "final"])
    a = ap.parse_args()

    p = B / "logs" / f"pipeline-{a.date}.json"
    mark = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    # 1) أرقام المصادر الثلاثة من بيانات التشغيل (لا أرقام مكتوبة يدويًا)
    sys.path.insert(0, str(B / "tools"))
    from source_counts import counts
    c = counts(a.date)
    mark["sources"] = {"approved": c["approved"], "checked": c["checked"], "ok": c["ok"],
                       "failed": c["failed"], "failed_names": c["failed_names"],
                       "status_file": f"feeds/feeds-{a.date}.status.json"}

    # 2) وجود نص التقرير وواجهته وقت كتابة العلامة (تصحيح حقل كان دائمًا false)
    md = B / "reports" / f"{a.date}-sectioned.md"
    mp = B / "web" / "meta" / f"{a.date}.json"
    mark["report_present_at_pipeline_end"] = bool(md.exists() and md.stat().st_size > 1000
                                                  and mp.exists() and mp.stat().st_size > 200)

    # 3) نتيجة البوابة من ملفها الرسمي
    gp = B / "logs" / f"gate-{a.date}" / "gate.json"
    if gp.exists():
        g = json.loads(gp.read_text(encoding="utf-8"))
        mark["final_gate"] = {"status": g.get("status"), "exit_code": int(g.get("exit_code") or 0),
                              "dir": g.get("dir") or f"logs/gate-{a.date}",
                              "blocked_steps": g.get("blocked_steps") or [],
                              "note": "نتيجة بوابة التسليم النهائية — كُتبت العلامة بعدها."}
        mark["gate_finished_utc"] = g.get("finished_utc") or now()
    else:
        mark.setdefault("final_gate", {"status": "warn", "exit_code": 1,
                                       "dir": f"logs/gate-{a.date}",
                                       "note": "لا ملف بوابة بعد — علامة مرحلة الخط اليومي."})
        mark.setdefault("gate_finished_utc", "")

    # 4) حقول اللغة (أمر 23 أكتوبر 2026): تُقرأ من ملفات القياس لا من الذاكرة
    def _read(name: str):
        fp = B / "logs" / f"{name}-{a.date}.json"
        if not fp.exists():
            return None
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
            return d[0] if isinstance(d, list) and d else (d if isinstance(d, dict) else None)
        except (OSError, json.JSONDecodeError):
            return None

    _ep, _sm, _or = _read("edit-pass"), _read("style-metrics"), _read("orthography")
    mark["language"] = {
        "edit_pass": ({"model": _ep.get("model"), "sections": _ep.get("sections"),
                       "edited": _ep.get("edited"), "rejected": _ep.get("rejected"),
                       "changes": _ep.get("changes"), "by_category": _ep.get("by_category"),
                       "applied": _ep.get("applied")} if _ep else None),
        "waw_pct": (_sm.get("waw_pct") if _sm else None),
        "waw_runs3": (_sm.get("waw_runs3") if _sm else None),
        "long_sentences": (_sm.get("long") if _sm else None),
        "banned_terms": (sum(int(v) for v in (_sm.get("banned") or {}).values())
                         if _sm and isinstance(_sm.get("banned"), dict) else None),
        "orthography_errors": (_or.get("total") if _or else None),
    }

    # 5) المخطط الثابت
    mark["schema_version"] = SCHEMA_VERSION
    mark["date"] = a.date
    mark.setdefault("pipeline_version", 4)
    mark.setdefault("overall", "ok")
    mark.setdefault("feeds", {})
    mark["finished_utc"] = mark.get("finished_utc") or now()
    mark["written_stage"] = a.stage

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(mark, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"  ✔ العلامة ({a.stage}): {p} · المخطط v{SCHEMA_VERSION} · "
          f"نص التقرير موجود: {mark['report_present_at_pipeline_end']} · "
          f"المصادر: {c['approved']}/{c['checked']}/{c['ok']} · البوابة: {mark['final_gate'].get('status')}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validators"))
    from _guard import run
    run(main)
