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
  runbook.py gate-json --date D [--through STEP] [--root .]   يكتب logs/gate-D/gate.json من سجل المحرّك
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


def site_dir(root):
    """مجلد الموقع: SITE_DIR ← seawatch الشقيق ← site الشقيق (نفس منطق بقية الأدوات)."""
    if os.environ.get("SITE_DIR"):
        return os.environ["SITE_DIR"]
    parent = os.path.dirname(os.path.abspath(root))
    for name in ("seawatch", "site"):
        if os.path.isdir(os.path.join(parent, name)):
            return os.path.join(parent, name)
    return os.path.join(parent, "seawatch")


def sub(s, date, root=None):
    """يستبدل {date} و{site} و{brain}. بلا root لا يحلّ {site} و{brain}."""
    if not isinstance(s, str):
        return s
    s = s.replace("{date}", date or "{date}")
    if root is not None:
        s = s.replace("{site}", site_dir(root)).replace("{brain}", os.path.abspath(root))
    return s


def step_env(root, date):
    """متغيرات البيئة التي يراها كل أمر خطوة: D و DATE و B و BRAIN_DIR و SITE و SITE_DIR."""
    e = dict(os.environ)
    sd = site_dir(root)
    e.update({"D": date or "", "DATE": date or "", "B": os.path.abspath(root), "BRAIN_DIR": os.path.abspath(root),
              "SITE": sd, "SITE_DIR": sd})
    return e


def resolve(root, p, date):
    """مسار من المانيفست → مسار فعلي (نسبي إلى root أو مطلق بعد حل {site})."""
    p = sub(p, date, root)
    return p if os.path.isabs(p) else os.path.join(root, p)


INCLUDE_RE = re.compile(r"\{\{include\s+([^}]+?)\s*\}\}")


def render_prompt(root, rel, date, depth=0):
    """يقرأ برومت خطوة الوكيل ويضمّن الملفات المشار إليها بـ {{include مسار}} (حتى عمقين)."""
    txt = open(resolve(root, rel, date), encoding="utf-8").read()
    txt = sub(txt, date, None)

    def rep(m):
        target = m.group(1).strip()
        if depth >= 2:
            return m.group(0)
        return render_prompt(root, target, date, depth + 1).rstrip("\n")
    txt = INCLUDE_RE.sub(rep, txt)
    if "{{sections}}" in txt:
        txt = txt.replace("{{sections}}", render_sections(root, date))
    return txt


def render_sections(root, date):
    """أقسام التقرير من السجل بترتيبها، ومعها مقتطف برومت كل قسم (فتُضاف الأقسام الجديدة تلقائيًا)."""
    m = load(root)
    parts = []
    for sec in sorted(m.get("sections", []), key=lambda x: x["order"]):
        head = sec.get("heading") or sec["title"]
        snippet = ""
        sp = sec.get("prompt_snippet")
        if sp and os.path.exists(resolve(root, sp, date)):
            lines = open(resolve(root, sp, date), encoding="utf-8").read().splitlines()
            snippet = "\n".join(l for l in lines if not l.startswith("# ")).strip()
        if not sec.get("heading"):
            parts.append(f"### {sec['order']}. {sec['title']}\n(تُركَّب آليًا من ملف الواجهة — لا تكتبها في النص)")
            continue
        parts.append(f"### {sec['order']}. {head}\n{snippet}")
    return "\n\n".join(parts)


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
            p = resolve(root, a["path"], date)
            if not os.path.exists(p):
                problems.append(f"ملف غائب: {sub(a['path'], date, root)}")
                continue
            if t == "min_bytes" and os.path.getsize(p) < a["n"]:
                problems.append(f"حجم أصغر من {a['n']}: {sub(a['path'], date, root)}")
            if t == "contains" and a["text"] not in open(p, encoding="utf-8", errors="replace").read():
                problems.append(f"النص المطلوب غير موجود في {sub(a['path'], date, root)}")
        elif t == "cmd":
            cmd = [sub(c, date, root) for c in a["command"]]
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=step_env(root, date))
            if r.returncode not in a.get("ok_rc", [0]):
                problems.append(f"فحص فشل (رمز {r.returncode}): {' '.join(cmd)}")
        else:
            problems.append(f"نوع شرط غير معروف: {t}")
    return problems


def outputs_hash(root, step, date):
    out = {}
    for w in step.get("writes", []):
        p = resolve(root, w, date)
        if os.path.isfile(p):
            out[sub(w, date, root)] = sha(p)
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
def run(root, date, only_phase=None, redo=None):
    """redo: معرّفات خطوات تُعاد للتحقق لأن مدخلاتها تغيّرت (ك-321) — لا تُقبل خطوة مكتملة قديمة."""
    redo = set(redo or ())
    m = load(root)
    ledger = read_ledger(root, m, date)
    for i, s in enumerate(m["steps"]):
        if only_phase and s.get("phase") != only_phase:
            continue
        e = ledger.get(s["id"])
        if e and e["status"] in ("done", "done_warn") and s["id"] not in redo:
            continue
        blocker = prior_ok(m, ledger, i)
        if blocker:
            print(f"✘ لا يجوز تنفيذ {s['id']} قبل اكتمال {blocker}")
            return 2
        print(f"▶ {s['id']} — {s['title']}  [{s['kind']}]")
        # وضع الاختبار المعزول (طلب فهد 2026-10-24، البند 9): خطوات النشر والإرسال
        # تُسجَّل فقط ولا تُنفَّذ — لا نشر ولا تلغرام في أي اختبار.
        dry_ids = {x.strip() for x in os.environ.get("RUNBOOK_DRY_STEPS", "").split(",") if x.strip()}
        if s["id"] in dry_ids:
            logdir = os.path.join(root, "logs/runbook", date)
            os.makedirs(logdir, exist_ok=True)
            logf = os.path.join(logdir, f"{s['id']}.log")
            open(logf, "w", encoding="utf-8").write(
                "سُجّل فقط — لم يُنفَّذ (RUNBOOK_DRY_STEPS: وضع معزول)\n"
                "الأمر المعتاد: " + " ".join(str(sub(c, date, root)) for c in s.get("command", [])) + "\n")
            append(root, m, date, {"step": s["id"], "status": "done", "dry": True,
                                   "log": os.path.relpath(logf, root)})
            print("  ⏸ سُجّل فقط (وضع معزول) — لم يُنفَّذ")
            ledger = read_ledger(root, m, date)
            continue
        if s["kind"] == "agent":
            try:
                prompt = render_prompt(root, s["prompt"], date)
            except OSError as exc:
                print(f"✘ تعذّر قراءة برومت {s['id']} أو أحد الملفات المضمّنة فيه: {exc}")
                return 2
            append(root, m, date, {"step": s["id"], "status": "waiting_agent"})
            print("─" * 60)
            print(prompt)
            print("─" * 60)
            print(f"عند الانتهاء: python3 tools/runbook.py complete {s['id']} --date {date}")
            return 10
        # script / llm: ينفّذ الأمر
        cmd = [sub(c, date, root) for c in s["command"]]
        attempts = 1 + (int(s["on_fail"].split(":")[1]) if str(s.get("on_fail", "")).startswith("retry:") else 0)
        for n in range(1, attempts + 1):
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=step_env(root, date))
            logdir = os.path.join(root, "logs/runbook", date)
            os.makedirs(logdir, exist_ok=True)
            logf = os.path.join(logdir, f"{s['id']}.log")
            # ك-162 (طلب فهد 2026-10-24): لا يُكتب سرّ في أي سجل خطوة.
            # المخرج يمرّ على مرشّح الإخفاء tools/redact.py قبل الكتابة.
            try:
                from redact import redact  # type: ignore
            except Exception:  # noqa: BLE001
                def redact(text: str) -> str:  # احتياط: لا إخفاء إن غاب المرشّح
                    return text
            open(logf, "w", encoding="utf-8").write(redact((r.stdout or "") + (r.stderr or "")))
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
        if s.get("phase") not in m.get("gate_phases", ["gates"]):
            continue
        e = ledger.get(s["id"])
        if not e or e["status"] not in ("done", "done_warn"):
            pend.append(s["id"])
    if pend:
        print(f"✘ بوابات غير مكتملة في سجل {date}: {'، '.join(pend)}")
        return 2
    print(f"✔ كل بوابات {date} مكتملة في سجل المحرّك")
    return 0


def gate_json(root, date, through=None):
    """يكتب logs/gate-<date>/gate.json من سجل المحرّك (يقرؤه write_mark وskill_lessons) — لا من الذاكرة."""
    import datetime
    m = load(root)
    ledger = read_ledger(root, m, date)
    steps, blocked, worst = [], [], 0
    for s in m["steps"]:
        if s.get("phase") not in m.get("gate_phases", ["gates"]):
            continue
        e = ledger.get(s["id"])
        name = s.get("gate_title") or s["title"]
        if e and e["status"] == "done":
            st, rc = "ok", 0
        elif e and e["status"] == "done_warn":
            st, rc = "warn", 1
        else:
            st = "block"
            rc = 2
        if e and e.get("rc") is not None and st != "ok":
            rc = e["rc"]
        if st == "block":
            blocked.append(name)
        worst = max(worst, {"ok": 0, "warn": 1, "block": 2}[st])
        steps.append({"step": name, "id": s["id"], "status": st, "exit_code": rc, "log": (e or {}).get("log")})
        if through and s["id"] == through:
            break
    out = {"date": date, "status": {0: "ok", 1: "warn", 2: "block"}[worst], "exit_code": worst, "steps": steps,
           "blocked_steps": blocked, "source": "runbook-ledger", "dir": f"logs/gate-{date}", "log_dir": f"logs/gate-{date}",
           "finished_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    d = os.path.join(root, "logs", f"gate-{date}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "gate.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"gate.json: {out['status']} ({len(steps)} بوابة، مانعة: {len(blocked)})")
    return 0


# ───────────────────────── verify ─────────────────────────
PATH_RE = re.compile(r"(?<![\w/.-])((?:[\w\u0600-\u06FF.-]+/)+[\w\u0600-\u06FF.-]+\.[A-Za-z0-9]{1,6})(?![\w])")
CODE_EXT = {".py", ".sh", ".mjs", ".js", ".ts", ".yaml", ".yml"}
EXEC_DIRS = ("tools/", "validators/", "generator/")
ROOT_SEEDS = ("INDEX.md", "CLAUDE.md", "SETUP.md", "README.md")


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


def tracked_files(root):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
            if os.path.splitext(f)[1] in TRACKED_EXT or rel == "evidence" or rel.startswith("evidence/"):
                out.append(rel)
    return out


class RefIndex:
    """فهرس يحوّل نصًّا إلى ملفات يحيل إليها: بالمسار، أو باسم الملف الفريد، أو باستيراد بايثون محلي."""

    def __init__(self, files):
        self.files = set(files)
        self.suffix = {}
        self.by_name = {}
        self.by_stem = {}
        for f in files:
            parts = f.split("/")
            for i in range(len(parts)):
                self.suffix.setdefault("/".join(parts[i:]), []).append(f)
            self.by_name.setdefault(parts[-1], []).append(f)
            if f.endswith(".py"):
                self.by_stem.setdefault(parts[-1][:-3], []).append(f)

    def refs(self, text, src):
        found = set()
        for m in PATH_RE.finditer(text):
            for h in self.suffix.get(m.group(1).lstrip("./"), []):
                found.add(h)
        for name, fs in self.by_name.items():
            if len(fs) == 1 and len(name) >= 6 and name in text:
                found.add(fs[0])
        if src.endswith(".py"):
            for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", text, re.M):
                fs = self.by_stem.get(m.group(1), [])
                same = [f for f in fs if os.path.dirname(f) == os.path.dirname(src)]
                for h in (same or (fs if len(fs) == 1 else [])):
                    found.add(h)
        found.discard(src)
        return found


def read_text(root, rel):
    try:
        if os.path.getsize(os.path.join(root, rel)) > 2_000_000:
            return ""
        return open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def step_seed_texts(root, m):
    """نصوص تُستخرج منها الإحالات من المانيفست نفسه: الأوامر والشروط والروابط والبرومتات المضمّنة."""
    texts = []
    for s in m["steps"]:
        texts.append(" ".join(s.get("command") or []))
        for a in s.get("assert", []):
            texts.append(" ".join(a.get("command", [])) + " " + str(a.get("path", "")))
        texts.append(" ".join(p for _, p in static_paths(s)))
        if s.get("prompt"):
            texts.append(s["prompt"])
    for sec in m.get("sections", []):
        texts.append(" ".join(str(sec.get(k, "")) for k in ("block", "validator", "prompt_snippet")) + " " +
                     " ".join(sec.get("tests", []) + sec.get("files", [])))
    return texts


def reachability(root, m, files):
    """يعيد (متصل بالكود والمانيفست، متصل عبر الوثائق أيضًا)."""
    idx = RefIndex(files)

    def to_rel(p):
        p = sub(p, "{date}", root)
        if os.path.isabs(p):
            ap = os.path.abspath(root)
            p = os.path.relpath(p, ap) if p.startswith(ap + os.sep) else p
        return p.lstrip("./")

    seeds = set()
    for txt in step_seed_texts(root, m):
        seeds |= idx.refs(txt, "")
    for s in m["steps"]:
        for _, p in static_paths(s):
            r = to_rel(p)
            if r in idx.files:
                seeds.add(r)
            elif os.path.isdir(os.path.join(root, r)):
                seeds |= {f for f in idx.files if f.startswith(r.rstrip("/") + "/")}
        if s.get("prompt") and s["prompt"] in idx.files:
            for inc in INCLUDE_RE.findall(read_text(root, s["prompt"])):
                if to_rel(inc) in idx.files:
                    seeds.add(to_rel(inc))
    for sec in m.get("sections", []):
        for k in ("block", "validator", "prompt_snippet"):
            if sec.get(k) and to_rel(sec[k]) in idx.files:
                seeds.add(to_rel(sec[k]))
        for p in sec.get("tests", []) + sec.get("files", []):
            if to_rel(p) in idx.files:
                seeds.add(to_rel(p))

    def bfs(start, code_only):
        seen, queue = set(start), list(start)
        while queue:
            cur = queue.pop()
            ext = os.path.splitext(cur)[1]
            if code_only and ext not in CODE_EXT and ext not in (".json", ".md"):
                continue
            if code_only and ext in (".md",) and not cur.startswith("runbook/prompts/"):
                continue  # الوثائق لا تُعدّ «استدعاءً» في المرحلة الأولى
            for h in idx.refs(read_text(root, cur), cur):
                if h not in seen:
                    seen.add(h)
                    queue.append(h)
        return seen

    code_seen = bfs(seeds, True)
    doc_seeds = set(seeds) | {f for f in ROOT_SEEDS if f in idx.files}
    all_seen = bfs(doc_seeds | code_seen, False)
    return code_seen, all_seen


def verify(root):
    errs, warns = [], []
    m = load(root)
    ids = [s["id"] for s in m["steps"]]
    if len(ids) != len(set(ids)):
        errs.append("معرّفات خطوات مكررة")
    # ترتيب المراحل
    order = m.get("phase_order")
    if order:
        last = -1
        for s in m["steps"]:
            ph = s.get("phase")
            if ph not in order:
                errs.append(f"{s['id']}: مرحلة غير معروفة «{ph}» (المراحل: {'، '.join(order)})")
                continue
            i = order.index(ph)
            if i < last:
                errs.append(f"ترتيب المراحل: {s['id']} (مرحلة {ph}) جاءت بعد مرحلة أحدث منها")
            last = max(last, i)
    # برومتات: التضمينات
    for s in m["steps"]:
        if s.get("kind") == "agent" and s.get("prompt") and os.path.exists(os.path.join(root, s["prompt"])):
            for inc in INCLUDE_RE.findall(read_text(root, s["prompt"])):
                if not os.path.exists(resolve(root, inc.strip(), None)):
                    errs.append(f"{s['id']}: البرومت يضمّن ملفًا غير موجود: {inc.strip()}")
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
        for a in s.get("assert", []):
            if a.get("type") == "cmd":
                tail = (a.get("command") or [""])[-1].strip()
                if tail in ("true", ":", "") or a.get("command") == ["true"]:
                    errs.append(f"{s['id']}: شرط تافه لا يثبت شيئًا ({tail or 'فارغ'})")
        if s.get("phase") == "deliver" and not s.get("optional"):
            real = [a for a in s.get("assert", []) if not (a.get("type") == "cmd" and "test -s logs/runbook/" in " ".join(a.get("command", [])))]
            if not real:
                errs.append(f"{s['id']}: خطوة تسليم تحتاج شرطًا من ناتج حقيقي (ملف أو ردّ مُسجَّل)، لا مجرد وجود السجل")
        if not s.get("links", {}).get("rules") and not s.get("optional"):
            warns.append(f"{s['id']}: غير مربوطة بقاعدة (links.rules)")
        for kind, p in static_paths(s):
            q = sub(p, "{date}", root)
            if "{" in q or "*" in q:
                continue
            if not os.path.exists(q if os.path.isabs(q) else os.path.join(root, q)):
                errs.append(f"{s['id']}: {kind} يحيل إلى مسار غير موجود: {p}")
    # الأقسام
    for sec in m.get("sections", []):
        for key in ("block", "validator", "prompt_snippet"):
            p = sec.get(key)
            if not p:
                errs.append(f"قسم {sec['id']}: رابط ناقص {key}")
                continue
            q = sub(p, "{date}", root)
            if not os.path.exists(q if os.path.isabs(q) else os.path.join(root, q)):
                errs.append(f"قسم {sec['id']}: {key} يحيل إلى غير موجود: {p}")
        for p in sec.get("tests", []) + sec.get("files", []):
            q = sub(p, "{date}", root)
            if not os.path.exists(q if os.path.isabs(q) else os.path.join(root, q)):
                errs.append(f"قسم {sec['id']}: مسار غير موجود: {p}")
        if not sec.get("tests"):
            errs.append(f"قسم {sec['id']}: بلا اختبار")
    # كل استثناء بسبب مكتوب
    exempt = list(m.get("exempt", []))
    reasons = m.get("exempt_reasons", {})
    for g in exempt:
        if not str(reasons.get(g, "")).strip():
            errs.append(f"استثناء بلا سبب مكتوب: {g}")

    def is_exempt(rel):
        return any(fnmatch.fnmatch(rel, g) for g in exempt)
    files = tracked_files(root)
    code_seen, all_seen = reachability(root, m, files)
    manual = m.get("manual_tools", {})
    for rel in sorted(files):
        if rel in (MANIFEST, HANDBOOK) or is_exempt(rel):
            continue
        if rel not in all_seen:
            errs.append(f"ملف غير متصل بأي خطوة أو قسم أو وثيقة: {rel}")
        elif rel.startswith(EXEC_DIRS) and rel.endswith(tuple(CODE_EXT)) and rel not in code_seen:
            if not str(manual.get(rel, "")).strip():
                errs.append(f"أداة تذكرها الوثائق فقط ولا يستدعيها كود ولا خطوة (تعتمد على تذكّر الوكيل): {rel}")
    for k in manual:
        if k not in files:
            errs.append(f"manual_tools يحيل إلى ملف غير موجود: {k}")
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
    print("✔ المانيفست متسق: كل خطوة مربوطة، وكل ملف متصل بخطوة أو قسم أو وثيقة، وكل أداة يستدعيها كود أو مسجَّلة يدوية بسبب")
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
    ap.add_argument("--through", help="gate-json: آخر خطوة تُحسب (ما بعدها لم يحن وقته)")
    ap.add_argument("--redo", default="", help="معرّفات خطوات تُعاد للتحقق بعد تغيّر مدخلاتها، مفصولة بفاصلة (ك-321)")
    a = ap.parse_args()
    c = a.cmd
    if c == "verify":
        return verify(a.root)
    if c == "run":
        return run(a.root, a.date, redo=[x for x in a.redo.split(",") if x.strip()])
    if c == "gates":
        return run(a.root, a.date, only_phase="gates", redo=[x for x in a.redo.split(",") if x.strip()])
    if c == "gate-json":
        return gate_json(a.root, a.date, a.through)
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
