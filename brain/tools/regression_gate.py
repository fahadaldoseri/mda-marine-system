#!/usr/bin/env python3
"""مدير الانحدار التراكمي — يعيد قياس بنود سجل الانحدار كلها في تشغيل واحد.

القاعدة: البند المانع إذا سقط = لا عبور. والبند غير المانع مفتوح بموعد (`open_until`)؛
فإذا مرّ الموعد صار مانعًا تلقائيًّا — فلا تُقبل الاستثناءات بلا مهلة.

الاستعمال:
  regression_gate.py --until 5          قياس كل بنود المراحل من التجهيز حتى 5
  regression_gate.py --until الكل --require-manual   إلزام البنود اليدوية أيضًا
  regression_gate.py --item ب-13        بند واحد

رمز الخروج: 0 كل البنود المانعة ناجحة · 2 بند مانع ساقط أو مهلة انتهت.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path


def resolve_site(root: Path) -> Path:
    """جذر الموقع من مصدر واحد (ك-565).

    السبب المقيس: كانت الأداة تثبّت `root.parent / "seawatch"`، فصار المسار المشتق
    `/home/ubuntu/mda-marine-system/seawatch` وهو غير موجود، فسقطت بنود الانحدار
    الثمانية («لا إصدار مبني») وهي سليمة في الحقيقة. الحلّ: استخدام محلّل الجذر
    المعلن نفسه الذي يستخدمه النشر، فلا يتكرر المسار في أداتين.
    """
    env = os.environ.get("SITE_DIR") or os.environ.get("SITE")
    candidates = [Path(env) if env else None, root.parent / "seawatch",
                  root.parent.parent / "seawatch", root.parent / "site"]
    for candidate in candidates:
        if candidate and (candidate / "dist").is_dir():
            return candidate
    for candidate in candidates:
        if candidate and candidate.is_dir():
            return candidate
    raise SystemExit("✘ تعذّر تحديد جذر الموقع (لا جذر يحوي dist) — فشل مغلق")


def load(root: Path) -> dict:
    p = root / "runbook" / "regression-items.json"
    if not p.is_file():
        raise SystemExit(f"✘ سجل الانحدار غير موجود: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def in_scope(item_phase: str, until: str, order: list[str]) -> bool:
    if until == "الكل":
        return True
    if item_phase not in order or until not in order:
        return False
    return order.index(item_phase) <= order.index(until)


def run_item(root: Path, item: dict, site: Path) -> tuple[str, str]:
    env = dict(os.environ, B=str(root), SITE=str(site))
    env["SITE_DIR"] = str(site)
    argv = [str(a).replace("{root}", str(root)).replace("{site}", str(site)).replace("{dist}", str(site / "dist"))
            for a in item["argv"]]
    try:
        r = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "ساقط", f"تعذّر التشغيل: {exc}"
    ok = (r.returncode == item.get("expect", 0))
    note = (r.stdout or r.stderr or "").strip().splitlines()
    return ("ناجح" if ok else "ساقط"), (note[-1][:110] if note else f"rc={r.returncode}")


def main() -> int:
    ap = argparse.ArgumentParser(description="مدير الانحدار التراكمي")
    ap.add_argument("--root", default=".", help="جذر النظام")
    ap.add_argument("--until", default="الكل", help="آخر مرحلة مطلوبة")
    ap.add_argument("--item", help="بند واحد بمعرّفه")
    ap.add_argument("--require-manual", action="store_true", help="عدّ البنود اليدوية ساقطة")
    ap.add_argument("--out", help="ملف النتيجة JSON")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    site = resolve_site(root)
    data = load(root)
    order = data.get("phase_order", [])
    today = date.today().isoformat()

    items = [i for i in data["items"] if in_scope(str(i["phase"]), args.until, order)]
    if args.item:
        items = [i for i in items if i["id"] == args.item]

    rows, blockers, exceptions = [], [], []
    for it in items:
        if it["kind"] == "manual":
            state, note = ("ساقط" if args.require_manual else "يدوي"), it.get("how", "قياس بمتصفح")
        else:
            state, note = run_item(root, it, site)
        open_until = it.get("open_until")
        deadline_passed = bool(open_until and open_until < today)
        blocking = bool(it.get("blocking", True)) or deadline_passed
        rows.append({"id": it["id"], "title": it["title"], "phase": it["phase"], "state": state,
                     "blocking": blocking, "open_until": open_until, "note": note})
        if state == "ساقط":
            (blockers if blocking else exceptions).append(it["id"])

    passed = sum(1 for r in rows if r["state"] == "ناجح")
    failed = sum(1 for r in rows if r["state"] == "ساقط")
    manual = sum(1 for r in rows if r["state"] == "يدوي")
    print(f"   بنود سجل الانحدار · حتى: {args.until} · العدد: {len(rows)} · الناجح: {passed} · "
          f"الساقط: {failed} · اليدوي المعلَّق: {manual}")
    for r in rows:
        mark = {"ناجح": "•", "يدوي": "◦", "ساقط": "!"}[r["state"]]
        tail = f" [غير مانع حتى {r['open_until']}]" if r["state"] == "ساقط" and not r["blocking"] else ""
        print(f"   {mark} {r['id']} (م{r['phase']}) {r['state']}{tail} — {r['note']}")

    out = Path(args.out) if args.out else root / "audit" / "regression" / f"{today}-until-{args.until}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"date": today, "until": args.until, "rows": rows,
                               "passed": passed, "failed": failed, "manual": manual,
                               "blockers": blockers, "exceptions": exceptions},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if blockers:
        print(f"✘ الانحدار: {len(blockers)} بندًا مانعًا ساقطًا — لا عبور ({' · '.join(blockers)})")
        return 2
    print(f"✔ الانحدار: صفر بند مانع ساقط" +
          (f" · {sum(1 for r in rows if r.get('open_until'))} بندًا بمهلة مفتوحة" if any(r.get("open_until") for r in rows) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
