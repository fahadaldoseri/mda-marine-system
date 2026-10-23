#!/usr/bin/env python3
"""محرّك كتيب الإجراءات التشغيلية (مرجع تنفيذ، مكتبة معيارية فقط).

الفكرة: لا يعتمد التشغيل على ذاكرة الوكيل. المانيفست `runbook/runbook.json` هو المصدر الوحيد للخطوات والارتباطات.
المحرّك ينفّذ خطوة خطوة بالترتيب، ولا يسمح بخطوة قبل اكتمال ما قبلها بدليل (ملفات ونتائج فحص)،
ويسجّل كل خطوة في سجل `logs/runbook/<التاريخ>.jsonl`. ويولّد الكتيب المقروء `docs/runbook.md` من المانيفست نفسه.

الأوامر:
  runbook.py verify [--root .]                    فحص المانيفست والارتباطات (يخرج 2 عند أي خلل)
  runbook.py run --date D [--root .]              ينفّذ الخطوات بالترتيب؛ يتوقف عند خطوة وكيل (رمز 10) أو فشل (رمز 2)
  runbook.py complete STEP --date D [--root .]    يعلن الوكيل إتمام خطوته؛ يُقبل فقط إن تحققت شروطها بالدليل
  runbook.py status --date D [--root .]           حالة كل خطوة
  runbook.py handbook [--root .]                  يولّد docs/runbook.md
  runbook.py section-add --id ID --title T --after ID2 [--root .]      يسجّل قسمًا جديدًا في السجل
  runbook.py section-remove --id ID [--root .]
  runbook.py step-add --id ID --title T --kind script|llm|agent --after ID2 [--root .]   يسجّل خطوة جديدة
  runbook.py step-remove --id ID [--root .]
  runbook.py gates --date D [--root .]            ينفّذ خطوات مرحلة البوابات وحدها (بديل final_gate.sh)
رموز الخروج: 0 تم · 2 فشل/مخالفة · 10 بانتظار الوكيل
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time

MANIFEST = "runbook/runbook.json"
HANDBOOK = "docs/runbook.md"
TRACKED_EXT = {".py", ".sh", ".md", ".json", ".js", ".mjs", ".ts", ".yaml", ".yml"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "logs", ".venv"}


# ───────────────────────── أدوات عامة ─────────────────────────
def load(root):
    with open(os.path.join(root, MANIFEST), encoding="utf-8") as f:
        return json.load(f)


def save(root, m):
    with open(os.path.join(root, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
        f.write("\n")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def sub(s, date):
    return s.replace("{date}", date) if isinstance(s, str) else s


def ledger_path(root, m, date):
    d = os.path.join(root, m.get("ledger_dir", "logs/runbook"))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{date}.jsonl")


def read_ledger(root, m, date):
    p = ledger_path(root, m, date)
    last = {}
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.strip():
                e = json.loads(line)
                last[e["step"]] = e
    return last


def append(root, m, date, entry):
    entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(ledger_path(root, m, date), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ───────────────────────── التحقق من الشروط (بالدليل) ─────────────────────────
def check_asserts(root, step, date):
    problems = []
    for a in step.get("assert", []):
        t = a.get("type")
        if t in ("file_exists", "min_bytes", "contains"):
            p = os.path.join(root, sub(a["path"], date))
            if not os.path.exists(p):
                problems.append(f"ملف غائب: {sub(a['path'], date)}")
                continue
            if t == "min_bytes" and os.path.getsize(p) < a["n"]:
                problems.append(f"حجم أصغر من {a['n']}: {sub(a['path'], date)}")
            if t == "contains" and a["text"] not in open(p, encoding="utf-8", errors="replace").read():
                problems.append(f"النص المطلوب غير موجود في {sub(a['path'], date)}")
        elif t == "cmd":
            cmd = [sub(c, date) for c in a["command"]]
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            if r.returncode not in a.get("ok_rc", [0]):
                problems.append(f"فحص فشل (رمز {r.returncode}): {' '.join(cmd)}")
        else:
            problems.append(f"نوع شرط غير معروف: {t}")
    return problems


def outputs_hash(root, step, date):
    out = {}
    for w in step.get("writes", []):
        p = os.path.join(root, sub(w, date))
        if os.path.isfile(p):
            out[sub(w, date)] = sha(p)
    return out


def prior_ok(m, ledger, idx):
    for s in m["steps"][:idx]:
        if s.get("optional"):
            continue
        e = ledger.get(s["id"])
        if not e or e["status"] not in ("done", "done_warn"):
            return s["id"]
    return None


# ───────────────────────── run / complete ─────────────────────────
def run(root, date, only_phase=None):
    m = load(root)
    ledger = read_ledger(root, m, date)
    for i, s in enumerate(m["steps"]):
        if only_phase and s.get("phase") != only_phase:
            continue
        e = ledger.get(s["id"])
        if e and e["status"] in ("done", "done_warn"):
            continue
        blocker = prior_ok(m, ledger, i)
        if blocker:
            print(f"✘ لا يجوز تنفيذ {s['id']} قبل اكتمال {blocker}")
            return 2
        print(f"▶ {s['id']} — {s['title']}  [{s['kind']}]")
        if s["kind"] == "agent":
            prompt = open(os.path.join(root, s["prompt"]), encoding="utf-8").read().replace("{date}", date)
            append(root, m, date, {"step": s["id"], "status": "waiting_agent"})
            print("─" * 60)
            print(prompt)
            print("─" * 60)
            print(f"عند الانتهاء: python3 tools/runbook.py complete {s['id']} --date {date}")
            return 10
        # script / llm: ينفّذ الأمر
        cmd = [sub(c, date) for c in s["command"]]
        attempts = 1 + (int(s["on_fail"].split(":")[1]) if str(s.get("on_fail", "")).startswith("retry:") else 0)
        for n in range(1, attempts + 1):
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            logdir = os.path.join(root, "logs/runbook", date)
            os.makedirs(logdir, exist_ok=True)
            logf = os.path.join(logdir, f"{s['id']}.log")
            open(logf, "w", encoding="utf-8").write((r.stdout or "") + (r.stderr or ""))
            ok_rc, warn_rc = s.get("ok_rc", [0]), s.get("warn_rc", [])
            probs = check_asserts(root, s, date) if (r.returncode in ok_rc or r.returncode in warn_rc) else [f"رمز الخروج {r.returncode}"]
            if not probs:
                st = "done" if r.returncode in ok_rc else "done_warn"
                append(root, m, date, {"step": s["id"], "status": st, "rc": r.returncode, "outputs": outputs_hash(root, s, date),
                                       "log": os.path.relpath(logf, root), "attempt": n})
                print(f"  ✔ {st} (رمز {r.returncode})")
                break
            print(f"  ✘ محاولة {n}: {'; '.join(probs)}")
        else:
            append(root, m, date, {"step": s["id"], "status": "failed", "rc": r.returncode, "problems": probs, "log": os.path.relpath(logf, root)})
            if s.get("on_fail") == "continue":
                print("  ⚠ فشل مع المتابعة (مسموح في المانيفست)")
                continue
            print(f"✘ توقف عند {s['id']}: {'; '.join(probs)}")
            return 2
        ledger = read_ledger(root, m, date)
    print("✔ اكتملت كل الخطوات")
    return 0


def complete(root, step_id, date):
    m = load(root)
    ledger = read_ledger(root, m, date)
    idx = next((i for i, s in enumerate(m["steps"]) if s["id"] == step_id), None)
    if idx is None:
        print(f"✘ خطوة غير معروفة: {step_id}")
        return 2
    s = m["steps"][idx]
    if s["kind"] != "agent":
        print("✘ هذه الخطوة ينفذها المحرّك لا الوكيل")
        return 2
    blocker = prior_ok(m, ledger, idx)
    if blocker:
        print(f"✘ لا يُقبل إتمام {step_id} قبل اكتمال {blocker}")
        return 2
    if not ledger.get(step_id) or ledger[step_id]["status"] != "waiting_agent":
        print(f"✘ الخطوة {step_id} لم تُسلَّم إلى الوكيل بعد (شغّل run أولًا)")
        return 2
    probs = check_asserts(root, s, date)
    if probs:
        append(root, m, date, {"step": step_id, "status": "waiting_agent", "problems": probs})
        print("✘ لم تتحقق شروط الإتمام:\n  - " + "\n  - ".join(probs))
        return 2
    append(root, m, date, {"step": step_id, "status": "done", "outputs": outputs_hash(root, s, date)})
    print(f"✔ قُبل إتمام {step_id}")
    return 0


def status(root, date):
    m = load(root)
    ledger = read_ledger(root, m, date)
    for s in m["steps"]:
        e = ledger.get(s["id"])
        print(f"{s['id']}  {e['status'] if e else 'لم تبدأ':<14} {s['title']}")
    return 0


def gates_status(root, date):
    """حالة خطوات البوابات وحدها — تستعملها سكربتات النشر لترفض العمل بلا سجل مكتمل."""
    m = load(root)
    ledger = read_ledger(root, m, date)
    pend = []
    for s in m["steps"]:
        if s.get("phase") != "gates":
            continue
        e = ledger.get(s["id"])
        if not e or e["status"] not in ("done", "done_warn"):
            pend.append(s["id"])
    if pend:
        print(f"✘ بوابات غير مكتملة في سجل {date}: {'، '.join(pend)}")
        return 2
    print(f"✔ كل بوابات {date} مكتملة في سجل المحرّك")
    return 0


# ───────────────────────── verify ─────────────────────────
def static_paths(s):
    for key in ("reads", "writes"):
        for p in s.get(key, []):
            yield key, p
    if s.get("prompt"):
        yield "prompt", s["prompt"]
    links = s.get("links", {})
    for k in ("files", "folders", "gates", "tests"):
        for p in links.get(k, []):
            yield "links." + k, p
    if s["kind"] != "agent" and s.get("command"):
        for c in s["command"][1:]:
            if re.search(r"\.(py|sh|mjs|js)$", c) and "{" not in c:
                yield "command", c


def verify(root):
    errs, warns = [], []
    m = load(root)
    ids = [s["id"] for s in m["steps"]]
    if len(ids) != len(set(ids)):
        errs.append("معرّفات خطوات مكررة")
    referenced = set()
    for s in m["steps"]:
        for fld in ("id", "title", "kind"):
            if not s.get(fld):
                errs.append(f"{s.get('id', '?')}: حقل ناقص {fld}")
        if s.get("kind") not in ("script", "llm", "agent"):
            errs.append(f"{s['id']}: نوع غير صالح")
        if s.get("kind") == "agent" and not s.get("prompt"):
            errs.append(f"{s['id']}: خطوة وكيل بلا برومت مكتوب (تعتمد على الذاكرة)")
        if s.get("kind") in ("script", "llm") and not s.get("command"):
            errs.append(f"{s['id']}: بلا أمر")
        if not s.get("assert") and not s.get("optional"):
            errs.append(f"{s['id']}: بلا شرط نجاح بالدليل (assert)")
        if not s.get("links", {}).get("rules") and not s.get("optional"):
            warns.append(f"{s['id']}: غير مربوطة بقاعدة (links.rules)")
        for kind, p in static_paths(s):
            referenced.add(p)
            if "{" in p or "*" in p:
                continue
            if not os.path.exists(os.path.join(root, p)):
                errs.append(f"{s['id']}: {kind} يحيل إلى مسار غير موجود: {p}")
    # الأقسام
    for sec in m.get("sections", []):
        for key in ("block", "validator", "prompt_snippet"):
            p = sec.get(key)
            if not p:
                errs.append(f"قسم {sec['id']}: رابط ناقص {key}")
                continue
            referenced.add(p)
            if not os.path.exists(os.path.join(root, p)):
                errs.append(f"قسم {sec['id']}: {key} يحيل إلى غير موجود: {p}")
        for p in sec.get("tests", []) + sec.get("files", []):
            referenced.add(p)
            if not os.path.exists(os.path.join(root, p)):
                errs.append(f"قسم {sec['id']}: مسار غير موجود: {p}")
        if not sec.get("tests"):
            errs.append(f"قسم {sec['id']}: بلا اختبار")
    # تغطية: كل ملف متتبَّع إما مذكور أو مستثنى
    exempt = [e for e in m.get("exempt", [])]
    def is_exempt(rel):
        return any(fnmatch.fnmatch(rel, g) for g in exempt)
    refs_norm = {r.lstrip("./") for r in referenced}
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
            if os.path.splitext(f)[1] not in TRACKED_EXT or is_exempt(rel) or rel == MANIFEST or rel == HANDBOOK:
                continue
            # يُعدّ متصلًا إذا ذُكر مباشرة أو داخل مجلد مذكور
            if rel in refs_norm or any(rel.startswith(r.rstrip("/") + "/") for r in refs_norm):
                continue
            errs.append(f"ملف غير مربوط بأي خطوة أو قسم: {rel}")
    # الكتيب المولَّد مطابق للمانيفست
    hb = os.path.join(root, HANDBOOK)
    if not os.path.exists(hb):
        errs.append("الكتيب docs/runbook.md غير مولَّد")
    elif render_handbook(m) != open(hb, encoding="utf-8").read():
        errs.append("الكتيب docs/runbook.md لا يطابق المانيفست (عُدّل يدويًا أو لم يُولَّد بعد التغيير)")
    for w in warns:
        print("⚠", w)
    for e in errs:
        print("✘", e)
    if errs:
        print(f"\nنتيجة التحقق: {len(errs)} خلل")
        return 2
    print("✔ المانيفست متسق: كل خطوة مربوطة بملفاتها وقواعدها وكل ملف مربوط بخطوة أو قسم")
    return 0


# ───────────────────────── الكتيب ─────────────────────────
def render_handbook(m):
    h = hashlib.sha256(json.dumps(m, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    L = ["# كتيب الإجراءات التشغيلية", "",
         f"<!-- مولَّد آليًا من runbook/runbook.json (بصمة {h}). لا تعدّله يدويًا: عدّل المانيفست ثم شغّل handbook. -->", "",
         "لا يعتمد التشغيل على ذاكرة الوكيل: المحرّك ينفّذ الخطوات بالترتيب، ولا تبدأ خطوة قبل اكتمال ما قبلها بدليل.", "",
         "## الخطوات", "",
         "| # | الخطوة | المنفّذ | يقرأ | يكتب | شرط الإتمام | القواعد | الملفات والمجلدات المرتبطة | عند الفشل |",
         "|---|---|---|---|---|---|---|---|---|"]
    for s in m["steps"]:
        links = s.get("links", {})
        conds = "؛ ".join(f"{a['type']}:{a.get('path', ' '.join(a.get('command', [])))}" for a in s.get("assert", []))
        rel = "، ".join(links.get("files", []) + links.get("folders", []) + links.get("gates", []))
        L.append(f"| {s['id']} | {s['title']}{' (اختيارية)' if s.get('optional') else ''} | {s['kind']} | "
                 f"{'، '.join(s.get('reads', []))} | {'، '.join(s.get('writes', []))} | {conds} | "
                 f"{'، '.join(links.get('rules', []))} | {rel} | {s.get('on_fail', 'stop')} |")
    L += ["", "## أقسام التقرير وارتباطاتها", "",
          "| الترتيب | القسم | كتلة التوليد | المدقق | مقتطف البرومت | الاختبارات | ملفات أخرى |", "|---|---|---|---|---|---|---|"]
    for sec in sorted(m.get("sections", []), key=lambda x: x["order"]):
        L.append(f"| {sec['order']} | {sec['title']} ({sec['id']}) | {sec.get('block', '')} | {sec.get('validator', '')} | "
                 f"{sec.get('prompt_snippet', '')} | {'، '.join(sec.get('tests', []))} | {'، '.join(sec.get('files', []))} |")
    return "\n".join(L) + "\n"


def handbook(root):
    m = load(root)
    p = os.path.join(root, HANDBOOK)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(render_handbook(m))
    print(f"✔ وُلّد {HANDBOOK}")
    return 0


# ───────────────────────── الأقسام ─────────────────────────
def section_add(root, sid, title, after):
    m = load(root)
    if any(s["id"] == sid for s in m.get("sections", [])):
        print("✘ القسم موجود")
        return 2
    secs = sorted(m.get("sections", []), key=lambda x: x["order"])
    pos = next((s["order"] for s in secs if s["id"] == after), None)
    if pos is None and after != "START":
        print(f"✘ القسم المرجعي غير موجود: {after}")
        return 2
    new_order = (pos or 0) + 1
    for s in secs:
        if s["order"] >= new_order:
            s["order"] += 1
    m.setdefault("sections", []).append({"id": sid, "title": title, "order": new_order, "block": "", "validator": "",
                                          "prompt_snippet": "", "tests": [], "files": []})
    save(root, m)
    handbook(root)
    print(f"✔ سُجّل القسم {sid} بالترتيب {new_order}. أكمل روابطه (block/validator/prompt_snippet/tests) ثم شغّل verify؛ سيفشل حتى تكتمل.")
    return 0


def section_remove(root, sid):
    m = load(root)
    n = len(m.get("sections", []))
    m["sections"] = [s for s in m.get("sections", []) if s["id"] != sid]
    if len(m["sections"]) == n:
        print("✘ القسم غير موجود")
        return 2
    for i, s in enumerate(sorted(m["sections"], key=lambda x: x["order"]), 1):
        s["order"] = i
    save(root, m)
    handbook(root)
    print(f"✔ حُذف {sid}. ملفاته التي لم يعد يربطها شيء ستظهر في verify ملفاتٍ غير مربوطة؛ احذفها أو اربطها.")
    return 0


# ───────────────────────── الخطوات (إضافة/حذف) ─────────────────────────
def step_add(root, sid, title, kind, after):
    """يضيف خطوة إلى المانيفست ثم يعيد توليد الكتيب؛ وتبقى verify فاشلة حتى تكتمل روابطها وشروطها."""
    m = load(root)
    if any(s["id"] == sid for s in m.get("steps", [])):
        print("✘ الخطوة موجودة")
        return 2
    steps = m.get("steps", [])
    pos = next((i for i, s in enumerate(steps) if s["id"] == after), None)
    if pos is None and after != "START":
        print(f"✘ الخطوة المرجعية غير موجودة: {after}")
        return 2
    new = {"id": sid, "title": title, "kind": kind, "assert": [], "links": {"rules": [], "files": [], "folders": [], "gates": [], "tests": []},
           "on_fail": "stop"}
    steps.insert((pos + 1) if pos is not None else 0, new)
    m["steps"] = steps
    save(root, m)
    handbook(root)
    print(f"✔ سُجّلت الخطوة {sid} بعد {after}. أكمل command/prompt وassert وlinks ثم شغّل verify؛ سيفشل حتى تكتمل.")
    return 0


def step_remove(root, sid):
    m = load(root)
    n = len(m.get("steps", []))
    m["steps"] = [s for s in m.get("steps", []) if s["id"] != sid]
    if len(m["steps"]) == n:
        print("✘ الخطوة غير موجودة")
        return 2
    save(root, m)
    handbook(root)
    print(f"✔ حُذفت {sid}. ملفاتها التي لم يعد يربطها شيء ستظهر في verify؛ احذفها أو اربطها.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd")
    ap.add_argument("step", nargs="?")
    ap.add_argument("--date")
    ap.add_argument("--root", default=".")
    ap.add_argument("--id")
    ap.add_argument("--title")
    ap.add_argument("--kind")
    ap.add_argument("--after", default="START")
    a = ap.parse_args()
    c = a.cmd
    if c == "verify":
        return verify(a.root)
    if c == "run":
        return run(a.root, a.date)
    if c == "gates":
        return run(a.root, a.date, only_phase="gates")
    if c == "gates-status":
        return gates_status(a.root, a.date)
    if c == "complete":
        return complete(a.root, a.step, a.date)
    if c == "status":
        return status(a.root, a.date)
    if c == "handbook":
        return handbook(a.root)
    if c == "section-add":
        return section_add(a.root, a.id, a.title, a.after)
    if c == "section-remove":
        return section_remove(a.root, a.id)
    if c == "step-add":
        return step_add(a.root, a.id, a.title, a.kind, a.after)
    if c == "step-remove":
        return step_remove(a.root, a.id)
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())