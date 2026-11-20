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


MEASURE_TOOL = "tools/browser_measure.py"


def parse_measure(argv: list[str]) -> dict | None:
    """بند قياس بصري بصيغة الأداة المعروفة، أو None إن خرج عن الصيغة (فيُشغَّل وحده كما كان)."""
    if len(argv) < 2 or argv[0] != "python3" or not argv[1].endswith(MEASURE_TOOL):
        return None
    spec = {"script": argv[1], "checks": [], "soft": [], "en": False, "out": None, "fixed": []}
    i = 2
    while i < len(argv):
        a = argv[i]
        if a == "--en":
            spec["en"] = True; i += 1; continue
        if a in ("--check", "--soft", "--out", "--root", "--site-root") and i + 1 < len(argv):
            v = argv[i + 1]
            if a == "--check": spec["checks"].append(v)
            elif a == "--soft": spec["soft"].append(v)
            elif a == "--out": spec["out"] = v
            else: spec["fixed"] += [a, v]
            i += 2; continue
        return None  # خيار غير معروف (--url · --widths · --phrase ...) ⇒ تشغيل منفرد
    if not spec["checks"]:
        return None
    return spec


def shared_measure(root: Path, site: Path, group: list[tuple[dict, dict]], env: dict) -> dict[str, tuple[str, str]]:
    """قياس واحد بمتصفح لسطح واحد يجمع فحوص بنوده، ثم يُحكم كل بند بفحوصه هو.

    السبب المقيس (20 نوفمبر 2026): كلفة فتح المتصفح وتحميل الصفحة ثابتة (~31 ثانية) مهما قلّت الفحوص،
    وكانت البوابة تدفعها ست مرات. الحكم يبقى لكل بند: `judge` نفسها من الأداة نفسها على فحوصه المانعة.
    فشل مغلق: أي انهيار أو غياب ملف القياس ⇒ كل بنود السطح ساقطة.
    """
    first = group[0][1]
    checks = sorted({c for _, s in group for c in s["checks"]})
    import tempfile
    with tempfile.TemporaryDirectory(prefix="regression-shared-") as tdir:
        return _shared_measure(root, group, env, checks, first, Path(tdir) / "measure.json")


def _shared_measure(root: Path, group: list[tuple[dict, dict]], env: dict, checks: list[str], first: dict,
                    tmp: Path) -> dict[str, tuple[str, str]]:
    argv = ["python3", first["script"], *first["fixed"], *(["--en"] if first["en"] else [])]
    for c in checks:
        argv += ["--check", c, "--soft", c]  # كل الفحوص إعلامية هنا؛ الحكم المانع لكل بند أدناه
    argv += ["--out", str(tmp)]
    ids = [it["id"] for it, _ in group]
    try:
        r = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True, timeout=900)
        rc = r.returncode
        data = json.loads(tmp.read_text(encoding="utf-8")) if rc == 0 and tmp.is_file() else None
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return {i: ("ساقط", f"تعذّر القياس المشترك: {exc}"[:110]) for i in ids}
    if data is None:
        tail = (r.stdout or r.stderr or "").strip().splitlines()
        return {i: ("ساقط", f"القياس المشترك rc={rc}: {tail[-1][:80] if tail else ''}") for i in ids}
    import importlib.util
    script = Path(first["script"]) if Path(first["script"]).is_absolute() else root / first["script"]
    try:
        mod_spec = importlib.util.spec_from_file_location("browser_measure_shared", script)
        mod = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(mod)
        judge = mod.judge
    except (OSError, SyntaxError, ImportError, AttributeError) as exc:  # فشل مغلق: لا حكم بلا دالة الحكم
        return {i: ("ساقط", f"تعذّر تحميل دالة الحكم: {exc}"[:110]) for i in ids}
    out: dict[str, tuple[str, str]] = {}
    for it, s in group:
        hard = [c for c in s["checks"] if c not in s["soft"]]
        soft = [c for c in s["checks"] if c in s["soft"]]
        item_data = json.loads(json.dumps(data, ensure_ascii=False))
        bad = judge(item_data, hard)
        item_data["checks"] = s["checks"]
        item_data["soft_checks"] = soft
        item_data["violations"] = bad
        if s["out"]:
            p = Path(s["out"]) if Path(s["out"]).is_absolute() else root / s["out"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(item_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out[it["id"]] = (("ساقط", f"✘ القياس البصري: {len(bad)} مخالفة مانعة — {bad[0][:60]}") if bad
                         else ("ناجح", "✔ القياس البصري: صفر مخالفة في الفحوص المطلوبة"))
    return out


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

    # بنود القياس البصري تُجمع حسب السطح (عربي/إنجليزي وجذراه) فيُفتح المتصفح مرة لكل سطح
    env = dict(os.environ, B=str(root), SITE=str(site), SITE_DIR=str(site))
    groups: dict[tuple, list[tuple[dict, dict]]] = {}
    for it in items:
        if it["kind"] == "manual":
            continue
        argv = [str(a).replace("{root}", str(root)).replace("{site}", str(site)).replace("{dist}", str(site / "dist"))
                for a in it["argv"]]
        spec = parse_measure(argv)
        if spec and it.get("expect", 0) == 0:
            groups.setdefault((spec["script"], spec["en"], tuple(spec["fixed"])), []).append((it, spec))
    shared: dict[str, tuple[str, str]] = {}
    for group in groups.values():
        shared.update(shared_measure(root, site, group, env))

    rows, blockers, exceptions = [], [], []
    for it in items:
        if it["kind"] == "manual":
            state, note = ("ساقط" if args.require_manual else "يدوي"), it.get("how", "قياس بمتصفح")
        elif it["id"] in shared:
            state, note = shared[it["id"]]
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
