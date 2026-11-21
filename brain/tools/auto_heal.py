#!/usr/bin/env python3
"""الإصلاح الذاتي للخط اليومي: جدول قواعد ثابت (runbook/auto-heal.json) يُطبَّق عند فشل خطوة.

اعتماد فهد (21 نوفمبر 2026): العطل التقني المعروف يُصلح آليًا وتُعاد الخطوة المتأثرة وحدها،
لا الخط كله. عطل سلامة المحتوى يعزل السطح المتأثر (النسخة الإنجليزية) فيُنشر العربي السليم
مع إفصاح وتنبيه، أو يحتجز التشغيل بتعليمة مكتوبة إن كان العطل في المتن العربي نفسه.
المحتوى الخاطئ لا يُنشر أبدًا، ولا يُستدعى نموذج وقت التشغيل: القرار من الجدول وحده.

يستدعيه tools/runbook.py بعد استنفاد محاولات خطوة فاشلة:
  decide(root, date, step_id, rc, log_text) ← قرار: retry · skip · stop · none

الحالة لكل يوم في logs/auto-heal/D.json (العزل والاحتجاز) وسجل كل إصلاح في logs/auto-heal/D.jsonl،
وملخص عربي للمالك في logs/auto-heal/D.md.

الأوامر:
  auto_heal.py check [--root .]                  يتحقق من الجدول (فشل مغلق عند أي خلل)
  auto_heal.py status --date D [--root .]        حالة العزل والإصلاحات لليوم
  auto_heal.py isolated --date D --surface en    رمز 0 إن كان السطح معزولًا، و1 إن لم يكن
  auto_heal.py release --date D --surface en --reason "..."   يرفع عزلًا بقرار مكتوب
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TABLE = "runbook/auto-heal.json"
STATE_DIR = "logs/auto-heal"
KNOWN_ACTIONS = {"remove_empty_dated_page", "accept_merged_shrinks", "isolate", "hold"}
THEN = {"retry", "skip", "stop"}


# ───────────────────────── الجدول والحالة ─────────────────────────
def load_table(root: str | os.PathLike) -> dict:
    return json.loads((Path(root) / TABLE).read_text(encoding="utf-8"))


def _state_path(root, date: str) -> Path:
    return Path(root) / STATE_DIR / f"{date}.json"


def load_state(root, date: str) -> dict:
    try:
        data = json.loads(_state_path(root, date).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("date", date)
    data.setdefault("isolated", {})
    data.setdefault("holds", [])
    return data


def _save_state(root, date: str, state: dict) -> None:
    p = _state_path(root, date)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    _write_summary(root, date, state)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def journal(root, date: str) -> list[dict]:
    p = Path(root) / STATE_DIR / f"{date}.jsonl"
    out = []
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _log(root, date: str, entry: dict) -> None:
    p = Path(root) / STATE_DIR / f"{date}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": _now(), **entry}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def isolated(root, date: str, surface: str) -> bool:
    """هل السطح معزول لهذا اليوم؟ يقرؤه البناء وبوابة التماثل وحكم النشر ورسالة تلغرام."""
    return surface in load_state(root, date)["isolated"]


def en_isolated_safe(root, date: str) -> bool:
    """للمدققات بعد البناء: هل النسخة الإنجليزية معزولة؟ أي عطل في القراءة = لا عزل (فشل مغلق).

    اختبار العطل المصطنع (21 نوفمبر 2026): بعد AH-C1 لا تُبنى صفحة اليوم الإنجليزية عمدًا، فكانت
    مدققات B010 تطلبها فتوقف إعادة الخطوة. المعزول يُفحص عربيًا وحده.
    """
    try:
        return isolated(root, date, "en")
    except Exception:  # noqa: BLE001
        return False


def isolated_steps(root, date: str) -> dict[str, str]:
    """الخطوات التي تُتخطّى لأن سطحها معزول: {معرّف الخطوة: السطح}."""
    state = load_state(root, date)
    if not state["isolated"]:
        return {}
    surfaces = load_table(root).get("surfaces", {})
    return {sid: name for name in state["isolated"] for sid in surfaces.get(name, {}).get("skip_steps", [])}


def owner_note(root, date: str) -> str:
    """سطر التنبيه للمالك في رسالة اليوم (فارغ إن لا عزل)."""
    state = load_state(root, date)
    if not state["isolated"]:
        return ""
    surfaces = load_table(root).get("surfaces", {})
    return " ".join(surfaces.get(n, {}).get("note_ar") or f"عُزل سطح {n}." for n in sorted(state["isolated"]))


def _write_summary(root, date: str, state: dict) -> None:
    surfaces = load_table(root).get("surfaces", {})
    lines = [f"# الإصلاح الذاتي — {date}", ""]
    if state["isolated"]:
        lines.append("## أسطح معزولة")
        for n, rec in sorted(state["isolated"].items()):
            lines.append(f"- {surfaces.get(n, {}).get('label', n)}: القاعدة {rec.get('rule')} عند {rec.get('step')} — {rec.get('reason', '')}")
        lines.append("")
    if state["holds"]:
        lines.append("## احتجاز بانتظار تصحيح المتن")
        for h in state["holds"]:
            lines.append(f"- {h.get('step')} (القاعدة {h.get('rule')}): {h.get('instruction', '')}")
        lines.append("")
    entries = journal(root, date)
    if entries:
        lines.append("## سجل الإصلاحات")
        for e in entries:
            lines.append(f"- {e.get('ts')} · {e.get('step')} · {e.get('rule')} · {e.get('then')} · {e.get('note', '')}")
    p = Path(root) / STATE_DIR / f"{date}.md"
    p.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


# ───────────────────────── التحقق من الجدول ─────────────────────────
def check_table(table: dict, step_ids: set[str] | None = None) -> list[str]:
    errs: list[str] = []
    policy = table.get("policy", {})
    content_actions = set(policy.get("content_actions", ["isolate", "hold"]))
    surfaces = table.get("surfaces", {})
    seen = set()
    for r in table.get("rules", []):
        rid = r.get("id", "?")
        if rid in seen:
            errs.append(f"{rid}: معرّف مكرر")
        seen.add(rid)
        if r.get("class") not in ("technical", "content"):
            errs.append(f"{rid}: صنف غير معروف {r.get('class')!r}")
        if r.get("action") not in KNOWN_ACTIONS:
            errs.append(f"{rid}: إجراء غير معروف {r.get('action')!r}")
        if not str(r.get("evidence", "")).strip():
            errs.append(f"{rid}: قاعدة بلا عطل مقيس (evidence)")
        # الحاجز الحاكم: عطل المحتوى لا يُعاد بلا عزل، ولا يمرّ بإجراء تقني.
        if r.get("class") == "content" and r.get("action") not in content_actions:
            errs.append(f"{rid}: عطل محتوى بإجراء {r.get('action')!r} — المسموح عزل أو احتجاز فقط")
        if r.get("class") == "technical" and r.get("action") in content_actions:
            errs.append(f"{rid}: عطل تقني بإجراء محتوى {r.get('action')!r}")
        if r.get("action") == "isolate" and r.get("surface") not in surfaces:
            errs.append(f"{rid}: سطح عزل غير معرّف {r.get('surface')!r}")
        if r.get("action") == "hold" and not str(r.get("instruction_ar", "")).strip():
            errs.append(f"{rid}: احتجاز بلا تعليمة مكتوبة")
        if r.get("action") != "hold" and r.get("then") not in THEN:
            errs.append(f"{rid}: نتيجة غير معروفة {r.get('then')!r}")
        try:
            re.compile(r.get("match", ""))
        except re.error as exc:
            errs.append(f"{rid}: نمط غير صالح: {exc}")
        if step_ids is not None:
            for s in r.get("steps", []):
                if not any(fnmatch.fnmatchcase(x, s) for x in step_ids):
                    errs.append(f"{rid}: خطوة غير موجودة في المانيفست {s!r}")
    if step_ids is not None:
        for n, spec in surfaces.items():
            for s in spec.get("skip_steps", []):
                if s not in step_ids:
                    errs.append(f"سطح {n}: خطوة تخطٍّ غير موجودة {s!r}")
    return errs


# ───────────────────────── الإجراءات الثابتة ─────────────────────────
def _site(root) -> Path:
    env = os.environ.get("SITE_DIR") or os.environ.get("SITE")
    return Path(env) if env else Path(root).resolve().parent / "site"


def act_remove_empty_dated_page(root, date, rule, log_text) -> tuple[bool, str]:
    """يحذف صفحة الإصدار المؤرخة إن كانت 0 بايت (البناء الحقيقي يكتبها من جديد)."""
    dist = _site(root) / "dist" / "reports"
    gone = []
    for p in (dist / f"{date}.html", dist / "en" / f"{date}.html"):
        if p.is_file() and p.stat().st_size == 0:
            p.unlink()
            gone.append(p.relative_to(_site(root)).as_posix())
    return (bool(gone), "حُذفت صفحة فارغة: " + " · ".join(gone)) if gone else (False, "")


SHRINK_RE = re.compile(r"نقص في أصل معتمد: (\S+)")


def _git(root, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def _repo_rel(root, abs_path: str) -> str | None:
    """يحوّل مفتاح الأرضية (مسار /home/ubuntu المطلق) إلى مسار داخل المستودع، أو None."""
    top = _git(root, "rev-parse", "--show-toplevel").stdout.strip()
    if not top:
        return None
    p = Path(abs_path)
    for base in (Path(top), Path(top).resolve(), Path("/home/ubuntu/mda-marine-system")):
        try:
            return p.relative_to(base).as_posix()
        except ValueError:
            pass
    # المهارات تُنسخ من skills/ في المستودع إلى /home/ubuntu/skills (cloud_env_prep.sh)
    try:
        return "skills/" + p.relative_to("/home/ubuntu/skills").as_posix()
    except ValueError:
        return None


def _main_ref(root) -> str | None:
    for ref in ("origin/main", "main"):
        if _git(root, "rev-parse", "--verify", "-q", ref).returncode == 0:
            return ref
    return None


def act_accept_merged_shrinks(root, date, rule, log_text) -> tuple[bool, str]:
    """يقبل نقص أصل معتمد فقط إن كان الملف مطابقًا لنسخة main وآخر تعديل له مدموج فيها.

    الشرط يفرّق بين تغيير اعتمده المالك بدمج طلب، وتلف أحدثه التشغيل نفسه (تشغيل 21 نوفمبر:
    S030 أعاد كتابة أرقام في الشيفرة فانكمشت، والملف هنا يخالف main فلا يُقبل ويبقى المنع).
    أي ملف لا يحقق الشرط يُسقط الإجراء كله: لا قبول جزئي.
    """
    paths = sorted(set(SHRINK_RE.findall(log_text)))
    ref = _main_ref(root)
    if not paths or not ref:
        return False, ""
    top = Path(_git(root, "rev-parse", "--show-toplevel").stdout.strip())
    lines, notes = [], []
    for ap in paths:
        rel = _repo_rel(root, ap)
        if rel is None:
            return False, f"مسار خارج المستودع: {ap}"
        src = Path(ap) if Path(ap).is_file() else top / rel
        want = subprocess.run(["git", "-C", str(root), "show", f"{ref}:{rel}"], capture_output=True)
        if want.returncode != 0 or not src.is_file() or src.read_bytes() != want.stdout:
            return False, f"الملف يخالف {ref}: {rel} — نقص لم يأتِ من دمج"
        commit = _git(root, "log", "-1", "--format=%h %s", ref, "--", rel).stdout.strip()
        if not commit:
            return False, f"لا تعديل مدموج معروف: {rel}"
        sha = commit.split()[0]
        lines.append(f"{ap} | تعديل مدموج في {ref} ({sha})")
        notes.append(f"{rel}←{sha}")
    dec = Path(root) / "audit" / f"asset-floor-decisions-{date}.txt"
    dec.parent.mkdir(parents=True, exist_ok=True)
    head = f"# {date} — قبول آلي (AH-T2): نقص أصول مطابقة لنسخة {ref} بعد طلب دمج مدموج بقرار المالك. لا حذف لأصل.\n"
    old = dec.read_text(encoding="utf-8") if dec.is_file() else ""
    new = [ln for ln in lines if ln.split(" | ")[0] not in old]
    dec.write_text(old + ("" if old else head) + "".join(ln + "\n" for ln in new), encoding="utf-8")
    r = subprocess.run([sys.executable, str(Path(root) / "validators" / "check_asset_floor.py"),
                        "--decisions", str(dec), "--reason", f"AH-T2: تعديل مدموج في {ref}"],
                       cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        return False, "تعذّر تسجيل القرار: " + (r.stdout + r.stderr).strip()[-200:]
    return True, "قُبل نقص مدموج: " + " · ".join(notes)


ACTIONS = {
    "remove_empty_dated_page": act_remove_empty_dated_page,
    "accept_merged_shrinks": act_accept_merged_shrinks,
}


# ───────────────────────── القرار ─────────────────────────
def _applies(rule: dict, step_id: str, log_text: str) -> bool:
    if not any(fnmatch.fnmatchcase(step_id, s) for s in rule.get("steps", [])):
        return False
    pat = rule.get("match", "")
    return not pat or re.search(pat, log_text or "") is not None


def _used(root, date: str, rule_id: str, step_id: str) -> int:
    return sum(1 for e in journal(root, date)
               if e.get("rule") == rule_id and e.get("step") == step_id and e.get("then") != "none")


def decide(root, date: str, step_id: str, rc: int | None, log_text: str) -> dict:
    """يختار أول قاعدة تنطبق وينفّذ إجراءها الثابت. يعيد {"then": retry|skip|stop|none, ...}.

    none: لا قاعدة تنطبق (أو استُنفد رصيدها) فيبقى الفشل كما هو.
    """
    try:
        table = load_table(root)
    except (OSError, json.JSONDecodeError) as exc:
        return {"then": "none", "note": f"جدول الإصلاح غير مقروء: {exc}"}
    limit = int(table.get("policy", {}).get("max_heals_per_rule_step_day", 1))
    for rule in table.get("rules", []):
        if not _applies(rule, step_id, log_text):
            continue
        if _used(root, date, rule["id"], step_id) >= limit:
            continue
        action = rule.get("action")
        base = {"rule": rule["id"], "class": rule.get("class"), "action": action, "step": step_id, "rc": rc}
        if action == "hold":
            state = load_state(root, date)
            state["holds"].append({"rule": rule["id"], "step": step_id, "ts": _now(),
                                   "instruction": rule.get("instruction_ar", "")})
            _log(root, date, {**base, "then": "stop", "note": "احتجاز: " + rule.get("title", "")})
            _save_state(root, date, state)
            return {**base, "then": "stop", "note": rule.get("instruction_ar", "")}
        if action == "isolate":
            surface = rule["surface"]
            state = load_state(root, date)
            state["isolated"].setdefault(surface, {"rule": rule["id"], "step": step_id, "ts": _now(),
                                                   "reason": rule.get("title", "")})
            skip = set(table.get("surfaces", {}).get(surface, {}).get("skip_steps", []))
            then = "skip" if step_id in skip else rule.get("then", "retry")
            _log(root, date, {**base, "then": then, "surface": surface, "note": f"عزل {surface}"})
            _save_state(root, date, state)
            return {**base, "then": then, "surface": surface, "note": f"عُزل السطح {surface}"}
        ok, note = ACTIONS[action](root, date, rule, log_text)
        if not ok:
            # الشرط على القرص لم يتحقق: القاعدة لا تنطبق، فلا يُحتسب من الرصيد، ويُسجَّل السبب إن وُجد
            if note:
                _log(root, date, {**base, "then": "none", "note": note})
            continue
        then = rule.get("then", "retry")
        _log(root, date, {**base, "then": then, "note": note})
        _save_state(root, date, load_state(root, date))
        return {**base, "then": then, "note": note}
    return {"then": "none", "note": ""}


def resolve_holds(root, date: str, step_id: str) -> int:
    """نجاح الخطوة بعد تصحيح المتن يرفع احتجازها (يبقى في السجل). يعيد عدد ما رُفع."""
    p = _state_path(root, date)
    if not p.is_file():
        return 0
    state = load_state(root, date)
    keep = [h for h in state["holds"] if h.get("step") != step_id]
    gone = len(state["holds"]) - len(keep)
    if gone:
        state["holds"] = keep
        _log(root, date, {"step": step_id, "rule": "-", "then": "resolved", "note": "نجحت الخطوة بعد التصحيح"})
        _save_state(root, date, state)
    return gone


def release(root, date: str, surface: str, reason: str) -> int:
    if not reason.strip():
        print("✘ رفع العزل يلزمه --reason مكتوب")
        return 2
    state = load_state(root, date)
    if surface not in state["isolated"]:
        print(f"✘ السطح {surface} غير معزول في {date}")
        return 2
    rec = state["isolated"].pop(surface)
    state.setdefault("released", []).append({**rec, "surface": surface, "released": _now(), "reason_release": reason})
    _log(root, date, {"rule": rec.get("rule"), "step": rec.get("step"), "then": "release", "note": reason})
    _save_state(root, date, state)
    print(f"✔ رُفع عزل {surface} في {date}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="الإصلاح الذاتي بجدول قواعد ثابت")
    ap.add_argument("cmd", choices=("check", "status", "release", "isolated"))
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--date")
    ap.add_argument("--surface", default="")
    ap.add_argument("--reason", default="")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        manifest = json.loads((Path(a.root) / "runbook" / "runbook.json").read_text(encoding="utf-8"))
        errs = check_table(load_table(a.root), {s["id"] for s in manifest["steps"]})
        for e in errs:
            print(f"  ✘ {e}")
        n = len(load_table(a.root).get("rules", []))
        word = "قواعد" if 3 <= n <= 10 else "قاعدة"
        print(("✘" if errs else "✔") + f" جدول الإصلاح الذاتي: {n} {word} · مخالفات {len(errs)}")
        return 2 if errs else 0
    if not a.date:
        print("✘ يلزم --date")
        return 2
    if a.cmd == "release":
        return release(a.root, a.date, a.surface, a.reason)
    if a.cmd == "isolated":
        return 0 if isolated(a.root, a.date, a.surface) else 1
    print(json.dumps({"state": load_state(a.root, a.date), "journal": journal(a.root, a.date)},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
