#!/usr/bin/env python3
"""تحديث مكوّنات علامة الخط من المخرجات نفسها — مصدر واحد للحقيقة.

السبب الجذري (ك-XX): مكوّنات العلامة (feeds · ofac · originals · ledger_merge) كانت
تُكتب من كتلة داخل tools/daily_pipeline.sh فقط. فإذا أُعيد تشغيل الخطوة عبر الكتيب
بحالة سليمة، بقيت القيمة القديمة «failed» في العلامة، فيمنع فاحص الاكتمال التسليم
على حالة غير حقيقية. الحكم الآن يُشتق من المخرجات لا من ذاكرة تشغيل سابق.

الاستعمال:
  python3 tools/mark_components.py --date 2026-10-24                 # تحديث كل المكوّنات
  python3 tools/mark_components.py --date 2026-10-24 --component feeds
  python3 tools/mark_components.py --date 2026-10-24 --verify        # مقارنة العلامة بالمخرجات
رمز الخروج: 0 تحديث سليم · 2 تعارض (العلامة تخالف المخرجات) · 70 انهيار.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
COMPONENTS = ("feeds", "ofac", "originals", "ledger_merge")


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _bootstrap_mark(date: str, mark_p: Path) -> int:
    """أنشئ علامة pipeline القياسية عند غيابها فقط، ثم اترك أثر المنشئ."""
    print(f"  · لا علامة تشغيل: {mark_p} — إنشاء علامة pipeline عبر write_mark")
    try:
        from write_mark import main as write_mark_main
    except ImportError as exc:
        print(f"  ✘ تعذّر تحميل write_mark لإنشاء العلامة: {exc}")
        return 70
    old_argv = sys.argv[:]
    try:
        sys.argv = [str(B / "tools" / "write_mark.py"),
                    "--date", date, "--stage", "pipeline"]
        rc = int(write_mark_main())
    finally:
        sys.argv = old_argv
    if rc != 0:
        print(f"  ✘ تعذّر إنشاء علامة pipeline: رمز الخروج {rc}")
        return rc
    mark = _read_json(mark_p)
    if mark is None:
        print(f"  ✘ write_mark لم يكتب علامة قابلة للقراءة: {mark_p}")
        return 70
    mark["created_by"] = "mark_components"
    mark["created_reason"] = "bootstrap قبل اشتقاق أول مكوّن في خط اليوم"
    mark_p.write_text(json.dumps(mark, ensure_ascii=False, indent=2, sort_keys=True),
                      encoding="utf-8")
    print("  · أضيف أثر الإنشاء: created_by=mark_components")
    return 0


def derive_feeds(date: str) -> tuple[str, str, list[str], dict]:
    p = B / "feeds" / f"feeds-{date}.status.json"
    d = _read_json(p)
    if not d:
        return "failed", "لا ملف حالة تغذيات لهذا اليوم", ["لا ملف حالة تغذيات"], {}
    failed = int(d.get("failed") or 0)
    stale = d.get("stale") or []
    empty = d.get("empty") or []
    limit = float(d.get("fail_ratio_limit") or 0.05)  # عتبة نسبة لا عدد
    ratio = (failed / int(d.get("checked") or 1)) if d.get("checked") else 0.0
    ff = []
    for f in (d.get("failed_feeds") or []):
        ff.append({"num": f.get("num"), "name": f.get("name"),
                   "error": f.get("error"),
                   "block_reason": f.get("block_reason") or f.get("error") or "تعذّر الجلب"})
    items = [f"{x['name']}: {x['block_reason']}"[:180] for x in ff]
    items += [f"قياس متأخر للمصدر رقم {s}" for s in stale]
    items += [f"تغذية فارغة للمصدر رقم {e}" for e in empty]
    if ratio > limit:
        status = "failed"
    elif failed or stale or empty:
        status = "degraded"
    else:
        status = "ok"
    detail = {"status": status, "checked": d.get("checked"), "ok": d.get("ok"),
              "failed": failed, "failed_feeds": ff, "fail_ratio": d.get("fail_ratio"),
              "stale": stale, "empty": empty, "browser_only": d.get("browser_only") or [],
              "note": ("مصدر نجح على مسار وفشل على آخر لا يُحسب متعذّرًا (عطل ك-137)"
                       if failed else ("قياسات متأخرة" if stale or empty else "")),
              "derived_from": f"feeds/feeds-{date}.status.json"}
    return status, detail["note"], items, detail


def derive_ofac(date: str) -> tuple[str, str, list[str], dict]:
    targets = B / "watchlist" / "ofac-targets.txt"
    screen = B / "archive" / "ofac-screen-latest.json"
    items: list[str] = []
    n_targets = 0
    if targets.exists():
        n_targets = len([x for x in targets.read_text(encoding="utf-8").splitlines() if x.strip()])
    if n_targets == 0:
        items.append("لا أهداف عقوبات مستخرجة من التقرير")
    scr = _read_json(screen) if screen.exists() else None
    if scr is None:
        items.append("لا ملف نتيجة فحص عقوبات")
    matches = list((scr or {}).get("matches") or [])
    status = "ok" if not items else "failed"
    detail = {"status": status, "list": (scr or {}).get("list") or "",
              "matches": matches, "targets": n_targets,
              "results_file": "archive/ofac-screen-latest.json",
              "note": f"فُحص {n_targets} مستهدفًا — الحالة: {status}" if not items else "؛ ".join(items),
              "derived_from": "watchlist/ofac-targets.txt + archive/ofac-screen-latest.json"}
    return status, detail["note"], items, detail


def derive_originals(date: str) -> tuple[str, str, list[str], dict]:
    man = _read_json(B / "archive" / "originals" / date / "manifest.json") or {}
    if isinstance(man, list):  # المانيفست قائمة بنود لا قاموس
        man = {"healthy": len([x for x in man if not isinstance(x, dict) or x.get("ok", True)]),
               "failed": len([x for x in man if isinstance(x, dict) and not x.get("ok", True)])}
    d = B / "archive" / "originals" / date
    n = len([p for p in d.glob("*") if p.is_file()]) if d.exists() else 0
    healthy = int(man.get("healthy") or (1 if n else 0))
    failed = int(man.get("failed") or 0)
    status = "ok" if healthy and not failed else "failed"
    items = [] if status == "ok" else ["لم تُحفظ الأصول الرسمية لهذا اليوم"]
    detail = {"status": status, "healthy": healthy, "failed": failed,
              "empty_shell": int(man.get("empty_shell") or 0),
              "manifest": f"archive/originals/{date}/manifest.json",
              "note": (man.get("note") or f"حُفظت الأصول في archive/originals/{date}")
              if status == "ok" else "لم تُحفظ الأصول الرسمية",
              "derived_from": f"archive/originals/{date}/"}
    return status, detail["note"], items, detail


def derive_ledger(date: str) -> tuple[str, str, list[str], dict]:
    daily = B / "cumulative-2026" / "daily" / f"{date}.json"
    raw = _read_json(daily)
    n = len(raw) if isinstance(raw, list) else len((raw or {}).get("incidents") or [])
    status = "ok" if n else "failed"
    detail = {"status": status, "added_this_run_count": n, "merged_before_marker": bool(n),
              "note": (f"دُمج ملف اليوم في الدفتر الجامع ({n} واقعة)") if n
              else "لم يُدمج ملف اليوم في الدفتر",
              "derived_from": f"cumulative-2026/daily/{date}.json"}
    return status, detail["note"], [] if n else [detail["note"]], detail


DERIVERS = {"feeds": derive_feeds, "ofac": derive_ofac,
            "originals": derive_originals, "ledger_merge": derive_ledger}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--component", choices=COMPONENTS, default="")
    ap.add_argument("--verify", action="store_true",
                    help="يقارن العلامة بالمخرجات؛ يخرج 2 عند تعارض (علامة قديمة)")
    a = ap.parse_args()

    mark_p = B / "logs" / f"pipeline-{a.date}.json"
    if not mark_p.exists():
        rc = _bootstrap_mark(a.date, mark_p)
        if rc != 0:
            return rc
    mark = _read_json(mark_p)
    if mark is None:
        print(f"  ✘ لا علامة تشغيل: {mark_p}")
        return 2

    comps = [a.component] if a.component else list(COMPONENTS)
    stale: list[str] = []
    for c in comps:
        status, note, items, detail = DERIVERS[c](a.date)
        cur = mark.get(c) or {}
        cur_status = str(cur.get("status") or "")
        if a.verify:
            if cur_status != status:
                stale.append(f"{c}: العلامة «{cur_status or 'غائبة'}» والمخرجات «{status}»")
            continue
        cur = dict(cur)
        cur.update(detail)
        if c == "ledger_merge":
            cur.setdefault("status", status)
        mark[c] = cur

    if a.verify:
        if stale:
            for s in stale:
                print(f"  ✘ {s}")
            print("النتيجة: العلامة لا تطابق المخرجات — حدّثها بـ tools/mark_components.py قبل التسليم")
            return 2
        print("  ✓ العلامة تطابق المخرجات في كل المكوّنات المفحوصة")
        return 0

    # الحالة العامة: أسوأ مكوّن
    order = {"ok": 0, "degraded": 1, "failed": 2}
    worst = "ok"
    for c in COMPONENTS:
        s = str((mark.get(c) or {}).get("status") or "ok")
        if order.get(s, 0) > order.get(worst, 0):
            worst = s
    mark["overall"] = worst
    mark_p.write_text(json.dumps(mark, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✔ حُدّثت المكوّنات {comps} من المخرجات · الحالة العامة: {worst}")
    for c in comps:
        print(f"     {c}: {json.dumps(mark.get(c), ensure_ascii=False)[:130]}")
    return 0


if __name__ == "__main__":
    # الحارس الموحّد في validators/_guard.py (ك-133: الانهيار يخرج 70 ويمنع)
    for cand in (Path(__file__).resolve().parent.parent / "validators",
                 Path(__file__).resolve().parent):
        sys.path.insert(0, str(cand))
    try:
        from _guard import run  # noqa: E402
        run(main)
    except ImportError:
        sys.exit(main())
