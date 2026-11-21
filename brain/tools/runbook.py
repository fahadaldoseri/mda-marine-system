#!/usr/bin/env python3
"""محرّك كتيب الإجراءات التشغيلية (مرجع تنفيذ، مكتبة معيارية فقط).

الفكرة: لا يعتمد التشغيل على ذاكرة الوكيل. المانيفست `runbook/runbook.json` هو المصدر الوحيد للخطوات والارتباطات.
المحرّك ينفّذ خطوة خطوة بالترتيب، ولا يسمح بخطوة قبل اكتمال ما قبلها بدليل (ملفات ونتائج فحص)،
ويسجّل كل خطوة في سجل `logs/runbook/<التاريخ>.jsonl`. ويولّد الكتيب المقروء `docs/runbook.md` من المانيفست نفسه.

الأوامر:
  runbook.py verify [--root .]                    فحص المانيفست والارتباطات (يخرج 2 عند أي خلل)
  runbook.py run --date D [--root .]              ينفّذ الخطوات بالترتيب؛ يتوقف عند خطوة وكيل (رمز 10) أو فشل (رمز 2)
                                                  بعد إصلاح خطأ يُستأنف بالأمر نفسه بلا --redo واسع: المحرّك يعيد آليًّا
                                                  المكتمل الذي تغيّرت مدخلاته منذ آخر توقف (--no-auto-redo يوقفها)
  runbook.py complete STEP --date D [--root .]    يعلن الوكيل إتمام خطوته؛ يُقبل فقط إن تحققت شروطها بالدليل
  runbook.py status --date D [--root .]           حالة كل خطوة
  runbook.py handbook [--root .]                  يولّد docs/runbook.md
  runbook.py timings --date D                     جدول أزمنة المراحل والخطوات (logs/runbook/D/timings.md)
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
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", "logs", ".venv"}


class ManifestNotFound(FileNotFoundError):
    """فشل مغلق عند غياب مانيفست الكتيب من كل المسارات المعلنة."""


def discover_root(start, *, explicit: bool = False):
    """اعثر على جذر يحوي المانيفست — فشل مغلق بلا تخمين.

    العقد: عند تمرير --root يُفحص الجذر المطلوب وحده. وبلا --root تُشتق المسارات من
    مجلد العمل الحالي صاعدًا في سلسلة الآباء، ويُفحص في كل درجة مساران معلَنان:
    `<درجة>/runbook/runbook.json` و`<درجة>/brain/runbook/runbook.json`.
    لا يُستخدم موضع الأداة نفسه كبديل صامت، فمجرد تشغيلها من مجلد بلا مانيفست يفشل
    مغلقًا (rc=2) مع طباعة كل المسارات المفحوصة.
    """
    checked = []
    if explicit:
        requested = os.path.abspath(os.path.expanduser(str(start)))
        candidates = [requested]
    else:
        candidates = []
        cur = os.path.abspath(os.getcwd())
        while True:
            candidates.append(cur)
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
    for candidate in candidates:
        for rel in (MANIFEST, os.path.join("brain", MANIFEST)):
            manifest = os.path.join(candidate, rel)
            checked.append(manifest)
            if os.path.isfile(manifest):
                return os.path.dirname(os.path.dirname(manifest)) if rel.startswith("brain") else candidate
    raise ManifestNotFound(
        "مانيفست الكتيب غير موجود؛ المسارات المفحوصة: " + " · ".join(checked)
    )


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
    """مجلد الموقع: override صريح، ثم الموقع المنشور، ثم أي جذر شقيق يحوي dist.

    ك-618 (2026-11-12): كان الفحص يجمع المرشّحين بمستويات الأب فيختار مرآة المستودع
    `mda-marine-system/site` (فيها `dist/reports` جزئيًا) قبل الموقع المنشور
    المحدد عبر `SITE_DIR`، فتظهر إنذارات كاذبة في فحوص الأسطح. الإصلاح: مرور أول
    على الأسماء المنشورة (`seawatch`) في كل المستويات، ثم مرور ثانٍ على بقية الأسماء
    (`site`) — فيبقى كشف الجذر الشقيق كما كان، ويتقدّم الموقع المنشور دائمًا.
    """
    if os.environ.get("SITE_DIR"):
        return os.environ["SITE_DIR"]
    parent = os.path.dirname(os.path.abspath(root))
    levels = []
    for _ in range(4):
        levels.append(parent)
        next_parent = os.path.dirname(parent)
        if next_parent == parent:
            break
        parent = next_parent
    for names in (("seawatch",), ("site",)):
        for level in levels:
            for name in names:
                candidate = os.path.join(level, name)
                if os.path.isdir(os.path.join(candidate, "dist")):
                    return candidate
    if levels:
        candidate = os.path.join(levels[0], "site")
        if os.path.isdir(candidate):
            return candidate
        return os.path.join(levels[0], "seawatch")
    return os.path.join(os.path.dirname(os.path.abspath(root)), "seawatch")


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
        if not isinstance(a, dict):
            problems.append(f"شرط غير صالح في {step.get('id', '?')}: يجب أن يكون كائنًا (ASSERT_SHAPE_V1)")
            continue
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
            # CMD_SHAPE_V1: صيغة أمر الخطوة قائمة argv نصية غير فارغة، وإلا فشل مغلق برسالة واضحة
            if not isinstance(cmd, list) or not cmd or any(not isinstance(x, str) or not x for x in cmd):
                problems.append(f"الخطوة {step.get('id', '?')}: صيغة الأمر يجب أن تكون قائمة argv نصية غير فارغة (CMD_SHAPE_V1)")
                continue
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


def entry_allows_progress(step, entry):
    """تسمح بالاستمرار بعد إنجاز عادي أو تخطٍّ مسجّل لخطوة معطلة صراحة."""
    if not entry:
        return False
    if entry.get("status") in ("done", "done_warn"):
        return True
    return bool(step.get("disabled")) and entry.get("status") == "skipped"


def prior_ok(m, ledger, idx):
    for s in m["steps"][:idx]:
        if s.get("optional"):
            continue
        e = ledger.get(s["id"])
        if not entry_allows_progress(s, e):
            return s["id"]
    return None


# ───────────────────────── الإعادة الآلية للخطوات المتأثرة ─────────────────────────

import ast  # noqa: E402

ELIGIBLE_PHASES = {"write", "gates", "build", "outputs", "finalize"}
STALE_CODE_EXT = {".py", ".sh"}
STALE_SKIP_DIRS = SKIP_DIRS
STALE_CASCADE_SKIP = ("evidence", "audit")
STALE_PATH_RE = re.compile(r"(?:[\w.\-]+/)*[\w.\-]+\.(?:py|sh|json|jsonl|md|txt|js|css|html)\b")
SNAPSHOT_NAME = "stale-snapshot.json"


def watch_roots(root: str, site: str) -> list[str]:
    roots = [os.path.realpath(root)]
    s = os.path.realpath(site)
    if os.path.isdir(s) and not s.startswith(roots[0] + os.sep):
        roots.append(s)
    return roots


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(roots: list[str], prev: dict | None = None) -> dict:
    """{مسار: [حجم, mtime_ns, sha256]}؛ البصمة تُعاد من اللقطة السابقة إن لم يتغير الحجم والوقت."""
    prev = prev or {}
    out: dict = {}
    for base in roots:
        for dp, dn, fn in os.walk(base):
            dn[:] = sorted(d for d in dn if d not in STALE_SKIP_DIRS)
            for f in fn:
                p = os.path.join(dp, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if not os.path.isfile(p):
                    continue
                old = prev.get(p)
                if old and old[0] == st.st_size and old[1] == st.st_mtime_ns:
                    out[p] = old
                    continue
                try:
                    out[p] = [st.st_size, st.st_mtime_ns, _sha(p)]
                except OSError:
                    out[p] = [st.st_size, st.st_mtime_ns, "unreadable"]
    return out


def snap_diff(a: dict, b: dict) -> set[str]:
    return {p for p in set(a) | set(b) if (a.get(p) or [None, None, None])[2] != (b.get(p) or [None, None, None])[2]}


def snapshot_path(root: str, date: str) -> str:
    return os.path.join(root, "logs", "runbook", date, SNAPSHOT_NAME)


def load_snapshot(root: str, date: str) -> dict | None:
    p = snapshot_path(root, date)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_snapshot(root: str, date: str, snap: dict) -> None:
    p = snapshot_path(root, date)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False)
    os.replace(tmp, p)


def eligible(step: dict) -> bool:
    return step.get("kind") == "script" and step.get("phase") in ELIGIBLE_PHASES and not step.get("disabled")


class Closure:
    """سلسلة ملفات كل خطوة: ما يذكره أمرها وشروطها وروابطها، ثم ما تستورده أو تذكره هذه الملفات."""

    def __init__(self, root: str, site: str):
        self.root = os.path.realpath(root)
        self.site = os.path.realpath(site)
        self.top = os.path.dirname(self.root)
        self.bases = [self.root, self.site, self.top]
        self._file_refs: dict[str, set[str]] = {}
        self._steps: dict = {}

    def _resolve(self, token: str, here: str | None = None) -> set[str]:
        parts = token.split("/")
        found: set[str] = set()
        for i in range(len(parts)):
            rel = "/".join(parts[i:])
            bases = ([here] if here else []) + self.bases
            for b in bases:
                p = os.path.realpath(os.path.join(b, rel))
                if os.path.isfile(p) and p.startswith(self.top + os.sep):
                    found.add(p)
            if found:
                return found
        return found

    def _refs_of_text(self, text: str, here: str | None, code_only: bool = True) -> set[str]:
        out: set[str] = set()
        for tok in set(STALE_PATH_RE.findall(text)):
            if code_only and os.path.splitext(tok)[1] not in STALE_CODE_EXT:
                continue
            out |= self._resolve(tok, here)
        return out

    def _read(self, path: str) -> str:
        try:
            if os.path.getsize(path) > 2_000_000:
                return ""
            return open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            return ""

    def _refs_of_file(self, path: str) -> set[str]:
        """ملفات الشيفرة التي يستوردها ملف شيفرة أو يذكر مسارها (تبعيات البيانات لا تُتتبع: تغيّرها يعيد الكل)."""
        if path in self._file_refs:
            return self._file_refs[path]
        refs: set[str] = set()
        self._file_refs[path] = refs
        text = self._read(path)
        here = os.path.dirname(path)
        refs |= self._refs_of_text(text, here)
        if path.endswith(".py"):
            try:
                tree = ast.parse(text)
            except (SyntaxError, ValueError):
                tree = None
            names: set[str] = set()
            for node in ast.walk(tree) if tree else ():
                if isinstance(node, ast.Import):
                    names |= {a.name for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.add(node.module)
            dirs = [here, os.path.join(self.root, "tools"), os.path.join(self.root, "validators"),
                    os.path.join(self.root, "tests"), os.path.join(self.site, "generator"),
                    os.path.join(self.site, "tests"), self.root, self.site]
            for n in names:
                rel = n.replace(".", "/")
                for d in dirs:
                    for cand in (os.path.join(d, rel + ".py"), os.path.join(d, rel, "__init__.py"),
                                 os.path.join(d, rel.split("/")[0] + ".py")):
                        if os.path.isfile(cand):
                            refs.add(os.path.realpath(cand))
        refs.discard(path)
        return refs

    def of_step(self, step: dict, date: str, sub) -> set[str]:
        key = (step.get("id"), date)
        if key not in self._steps:
            self._steps[key] = self._of_step(step, date, sub)
        return self._steps[key]

    def _of_step(self, step: dict, date: str, sub) -> set[str]:
        """سلسلة ملفات الشيفرة لخطوة: المذكورة في أمرها وشروطها وروابطها، والمذكورة في ملفات
        البيانات التي تذكرها الخطوة مباشرة (مثل سجل بنود الانحدار)، ثم ما تستورده أو تستدعيه."""
        text = sub(json.dumps({k: step.get(k) for k in ("command", "assert", "links", "writes", "prompt")},
                              ensure_ascii=False), date)
        seeds = self._refs_of_text(text, None)
        for data in self._refs_of_text(text, None, code_only=False) - seeds:
            seeds |= self._refs_of_text(self._read(data), os.path.dirname(data))
        seen: set[str] = set()
        todo = list(seeds)
        while todo:
            p = todo.pop()
            if p in seen:
                continue
            seen.add(p)
            todo.extend(r for r in self._refs_of_file(p) if r not in seen)
        return seen


def stale_after(changed: set[str], steps: list[dict], done: set[str], closure: Closure, date: str, sub,
                ) -> tuple[set[str], str]:
    """الخطوات المكتملة المؤهلة التي صارت قديمة بسبب الملفات المتغيرة، مع سبب مختصر."""
    cands = [s for s in steps if s["id"] in done and eligible(s)]
    if not changed or not cands:
        return set(), ""
    data = sorted(p for p in changed if os.path.splitext(p)[1] not in STALE_CODE_EXT)
    if data:
        return {s["id"] for s in cands}, f"تغيّر ملف بيانات/محتوى: {os.path.relpath(data[0], closure.top)}" + (
            f" و{len(data) - 1} غيره" if len(data) > 1 else "")
    code = sorted(changed)
    hit: set[str] = set()
    covered: set[str] = set()
    for s in steps:
        if not eligible(s):
            continue
        deps = closure.of_step(s, date, sub)
        inter = deps & set(code)
        covered |= inter
        if inter and s["id"] in done:
            hit.add(s["id"])
    unknown = [p for p in code if p not in covered]
    if unknown:
        return {s["id"] for s in cands}, (f"شيفرة لا تقع في سلسلة أي خطوة: "
                                         f"{os.path.relpath(unknown[0], closure.top)} — إعادة شاملة احتياطًا")
    return hit, "شيفرة متغيرة: " + " · ".join(os.path.relpath(p, closure.top) for p in code[:4])


class _StaleAPI:
    """واجهة واحدة لدوال الإعادة الآلية داخل المحرّك نفسه (لا ملف مستقل يغيب عند النسخ)."""
    watch_roots = staticmethod(watch_roots)
    snapshot = staticmethod(snapshot)
    diff = staticmethod(snap_diff)
    load_snapshot = staticmethod(load_snapshot)
    save_snapshot = staticmethod(save_snapshot)
    eligible = staticmethod(eligible)
    stale_after = staticmethod(stale_after)
    Closure = Closure


# ───────────────────────── run / complete ─────────────────────────
def run_auto(root, date, only_phase=None, redo=None, only_steps=None, auto_redo=True):
    """redo: معرّفات خطوات تُعاد للتحقق لأن مدخلاتها تغيّرت (ك-321) — لا تُقبل خطوة مكتملة قديمة.

    auto_redo (اعتماد فهد 20 نوفمبر 2026): المحرّك يحسب بنفسه الخطوات المكتملة التي تغيّرت مدخلاتها
    منذ آخر توقف ويعيدها وحدها، بدل إعادة السلسلة كاملة بقائمة يدوية (tools/runbook_stale.py).
    """
    if not auto_redo or not date:
        try:
            return run(root, date, only_phase, redo, only_steps)
        finally:
            report_timings(root, date)
    rs = _StaleAPI
    m = load(root)
    roots = rs.watch_roots(root, site_dir(root))
    prev = rs.load_snapshot(root, date)
    now = rs.snapshot(roots, prev)
    ledger = read_ledger(root, m, date)
    done = {k for k, e in ledger.items() if entry_allows_progress(next((s for s in m["steps"] if s["id"] == k), {}), e)}
    closure = rs.Closure(root, site_dir(root))
    subf = lambda t, d: sub(t, d, root)  # noqa: E731
    if prev is None:
        stale = {s["id"] for s in m["steps"] if s["id"] in done and rs.eligible(s)}
        why = "لا لقطة سابقة لهذا اليوم — إعادة شاملة احتياطًا" if stale else ""
    else:
        stale, why = rs.stale_after(rs.diff(prev, now), m["steps"], done, closure, date, subf)
    if stale:
        print(f"↻ إعادة آلية لـ {len(stale)} خطوة مكتملة تغيّرت مدخلاتها — {why}")
    state = {"rs": rs, "roots": roots, "snap": now, "closure": closure, "sub": subf}
    try:
        return run(root, date, only_phase, set(redo or ()) | stale, only_steps, auto=state)
    finally:
        rs.save_snapshot(root, date, rs.snapshot(roots, state["snap"]))
        report_timings(root, date)


# ───────────────────────── جدول أزمنة المراحل (المقترح 4) ─────────────────────────
import calendar  # noqa: E402

TIMINGS_NAME = "timings.md"


def _ts(e: dict) -> float | None:
    try:
        return float(calendar.timegm(time.strptime(e["ts"], "%Y-%m-%dT%H:%M:%SZ")))
    except (KeyError, TypeError, ValueError):
        return None


def timings(root, date) -> str:
    """جدول زمن كل مرحلة وكل خطوة من سجل المحرّك (logs/runbook/DATE.jsonl).

    اعتماد فهد 20 نوفمبر 2026 (المقترح 4): يُكتب تلقائيًا في نهاية كل `run` إلى
    logs/runbook/DATE/timings.md فيظهر أي تباطؤ فور حدوثه، بلا رسالة تلغرام إضافية.
    زمن خطوة السكربت = مجموع elapsed_s لكل تشغيلاتها (الإعادة تُحسب منفصلة)؛ وخطوة الوكيل =
    من تسليمها إلى إتمامها. السطور القديمة بلا elapsed_s تُعلَّم «غير مقيس» ولا تُقدَّر."""
    m = load(root)
    p = ledger_path(root, m, date)
    entries = []
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except ValueError:
                    continue
    phase_of = {s["id"]: s.get("phase", "") for s in m["steps"]}
    order = {s["id"]: i for i, s in enumerate(m["steps"])}
    per: dict = {}
    waiting: dict = {}
    for e in entries:
        sid = e.get("step")
        if sid not in phase_of:
            continue
        r = per.setdefault(sid, {"runs": 0, "first": 0.0, "redo": 0.0, "unmeasured": 0, "failed": 0, "agent": 0.0})
        st = e.get("status")
        if st == "waiting_agent":
            waiting.setdefault(sid, _ts(e))
            continue
        if st not in ("done", "done_warn", "failed"):
            continue
        if sid in waiting and "elapsed_s" not in e:
            t0, t1 = waiting.pop(sid), _ts(e)
            if t0 is not None and t1 is not None:
                r["agent"] += max(0.0, t1 - t0)
            r["runs"] += 1
            continue
        r["runs"] += 1
        r["failed"] += st == "failed"
        if "elapsed_s" not in e:
            r["unmeasured"] += 1
            continue
        if r["runs"] == 1:
            r["first"] = float(e["elapsed_s"])
        else:
            r["redo"] += float(e["elapsed_s"])
    stamps = [t for t in (_ts(e) for e in entries) if t is not None]
    wall = (max(stamps) - min(stamps)) if stamps else 0.0

    def fmt(x: float) -> str:
        return f"{x:.0f} ث" if x < 120 else f"{x / 60:.1f} د"

    phases: dict = {}
    for sid, r in per.items():
        ph = phases.setdefault(phase_of[sid], [0, 0.0, 0.0, 0.0, 0])
        ph[0] += 1
        ph[1] += r["first"]
        ph[2] += r["redo"]
        ph[3] += r["agent"]
        ph[4] += r["unmeasured"]
    ph_order = [x for x in m.get("phase_order", []) if x in phases] + sorted(set(phases) - set(m.get("phase_order", [])))
    out = [f"# أزمنة التشغيل — {date}", "",
           f"الزمن الكلي من أول خطوة إلى آخرها: {fmt(wall)} · المصدر: {os.path.relpath(p, root)}", "",
           "| المرحلة | خطوات | زمن الآلة (أول تشغيل) | زمن الإعادات | زمن الوكيل | غير مقيس |", "|---|---|---|---|---|---|"]
    tot = [0, 0.0, 0.0, 0.0, 0]
    for ph in ph_order:
        v = phases[ph]
        tot = [a + b for a, b in zip(tot, v)]
        out.append(f"| {ph} | {v[0]} | {fmt(v[1])} | {fmt(v[2])} | {fmt(v[3])} | {v[4]} |")
    out.append(f"| **المجموع** | {tot[0]} | {fmt(tot[1])} | {fmt(tot[2])} | {fmt(tot[3])} | {tot[4]} |")
    slow = sorted(per.items(), key=lambda kv: -(kv[1]["first"] + kv[1]["redo"] + kv[1]["agent"]))[:12]
    out += ["", "## أبطأ الخطوات", "", "| الخطوة | المرحلة | التشغيلات | أول تشغيل | الإعادات | الوكيل | فشل |",
            "|---|---|---|---|---|---|---|"]
    for sid, r in sorted(slow, key=lambda kv: order[kv[0]]):
        out.append(f"| {sid} | {phase_of[sid]} | {r['runs']} | {fmt(r['first'])} | {fmt(r['redo'])} | "
                   f"{fmt(r['agent'])} | {r['failed']} |")
    return "\n".join(out) + "\n"


def report_timings(root, date) -> None:
    """يكتب الجدول ويطبع سطر المجموع؛ تعذّر الكتابة لا يغيّر رمز خروج التشغيل ويُعلن."""
    if not date:
        return
    text = timings(root, date)
    path = os.path.join(root, "logs", "runbook", date, TIMINGS_NAME)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError as exc:
        print(f"⚠ تعذّرت كتابة جدول الأزمنة: {exc}")
        return
    total = next((ln for ln in text.splitlines() if ln.startswith("| **المجموع**")), "")
    print(f"⏱ جدول الأزمنة: {os.path.relpath(path, root)} {total}")


def run(root, date, only_phase=None, redo=None, only_steps=None, auto=None):
    """redo: معرّفات خطوات تُعاد للتحقق لأن مدخلاتها تغيّرت (ك-321) — لا تُقبل خطوة مكتملة قديمة.
    auto: حالة الإعادة الآلية من run_auto (None = بلا تسلسل آلي)."""
    redo = set(redo or ())
    # ك-568: تشغيل محصور بخطوات معلومة ثم توقّف — يمنع الاستدعاء الدائري عندما
    # تُجدَّد بوابةٌ داخل خطوة نشر تستدعي بدورها الخطوة نفسها.
    only_steps = set(only_steps or ())
    m = load(root)
    ledger = read_ledger(root, m, date)
    allowed_phases = None
    if only_phase:
        allowed_phases = set(m.get("gate_phases", ["gates"])) if only_phase == "gates" else {only_phase}
    for i, s in enumerate(m["steps"]):
        if allowed_phases is not None and s.get("phase") not in allowed_phases:
            continue
        if only_steps and s["id"] not in only_steps:
            continue
        e = ledger.get(s["id"])
        if e and entry_allows_progress(s, e) and s["id"] not in redo:
            continue
        blocker = prior_ok(m, ledger, i)
        if blocker:
            print(f"✘ لا يجوز تنفيذ {s['id']} قبل اكتمال {blocker}")
            return 2
        print(f"▶ {s['id']} — {s['title']}  [{s['kind']}]")
        if s.get("disabled"):
            reason = str(s.get("reason") or "خطوة معطلة صراحة").strip()
            logdir = os.path.join(root, "logs/runbook", date)
            os.makedirs(logdir, exist_ok=True)
            logf = os.path.join(logdir, f"{s['id']}.log")
            open(logf, "w", encoding="utf-8").write(
                f"تخطٍّ آمن — لم يُنفَّذ الأمر: {reason}\n"
                "الحالة: disabled/skipped · رمز الخروج التشغيلي: 0\n")
            append(root, m, date, {"step": s["id"], "status": "skipped", "disabled": True,
                                   "reason": reason, "rc": 0, "log": os.path.relpath(logf, root)})
            print(f"  ⏭ skipped/disabled (رمز 0) — {reason} — لم يُنفَّذ الأمر")
            ledger = read_ledger(root, m, date)
            continue
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
            started = time.perf_counter()
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=step_env(root, date))
            elapsed_seconds = time.perf_counter() - started
            logdir = os.path.join(root, "logs/runbook", date)
            os.makedirs(logdir, exist_ok=True)
            logf = os.path.join(logdir, f"{s['id']}.log")
            # 2026-11-19: كل محاولة كانت تكتب فوق سجل المحاولة السابقة، فضاع سبب أربع محاولات
            # فاشلة لـB010 في يوم واحد. السجل الحالي يبقى باسمه (تقرؤه الشروط)، والسابق يُحفظ
            # باسم مؤرخ قبل الكتابة، فلا يُقرأ سطر محاولة قديمة على أنه الحالي.
            if os.path.exists(logf):
                stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(os.path.getmtime(logf)))
                kept = os.path.join(logdir, f"{s['id']}.{stamp}.log")
                if not os.path.exists(kept):
                    os.replace(logf, kept)
            # ك-162 (طلب فهد 2026-10-24): لا يُكتب سرّ في أي سجل خطوة.
            # المخرج يمرّ على مرشّح الإخفاء tools/redact.py قبل الكتابة.
            try:
                from redact import redact  # type: ignore
            except Exception:  # noqa: BLE001
                def redact(text: str) -> str:  # احتياط: لا إخفاء إن غاب المرشّح
                    return text
            output = redact((r.stdout or "") + (r.stderr or ""))
            open(logf, "w", encoding="utf-8").write(output.rstrip("\n") + f"\nelapsed_seconds={elapsed_seconds:.6f}\n")
            ok_rc, warn_rc = s.get("ok_rc", [0]), s.get("warn_rc", [])
            probs = check_asserts(root, s, date) if (r.returncode in ok_rc or r.returncode in warn_rc) else [f"رمز الخروج {r.returncode}"]
            if not probs:
                st = "done" if r.returncode in ok_rc else "done_warn"
                append(root, m, date, {"step": s["id"], "status": st, "rc": r.returncode, "outputs": outputs_hash(root, s, date),
                                       "log": os.path.relpath(logf, root), "attempt": n,
                                       "elapsed_s": round(elapsed_seconds, 3)})
                print(f"  ✔ {st} (رمز {r.returncode})")
                break
            print(f"  ✘ محاولة {n}: {'; '.join(probs)}")
        else:
            append(root, m, date, {"step": s["id"], "status": "failed", "rc": r.returncode, "problems": probs, "log": os.path.relpath(logf, root),
                                   "elapsed_s": round(elapsed_seconds, 3)})
            if s.get("on_fail") == "continue":
                print("  ⚠ فشل مع المتابعة (مسموح في المانيفست)")
                continue
            print(f"✘ توقف عند {s['id']}: {'; '.join(probs)}")
            return 2
        ledger = read_ledger(root, m, date)
        if auto is not None:
            rs = auto["rs"]
            after = rs.snapshot(auto["roots"], auto["snap"])
            # سجلات الأدلة التي تكتبها البوابة عن نفسها (بصمات بوقت التشغيل) لا تُسلسل الإعادة؛
            # ما عداها من محتوى وبناء وبيانات يُسلسلها. قيس: إعادة G000C وحدها تكتب 18 ملفًا في evidence/.
            changed = {p for p in rs.diff(auto["snap"], after)
                       if not any(p.startswith(os.path.join(os.path.realpath(root), d) + os.sep)
                                  for d in STALE_CASCADE_SKIP)}
            auto["snap"] = after
            later_done = {x["id"] for x in m["steps"][i + 1:]
                          if x["id"] not in redo and entry_allows_progress(x, ledger.get(x["id"]))}
            more, why = rs.stale_after(changed, m["steps"], later_done, auto["closure"], date, auto["sub"])
            if more:
                print(f"  ↻ {s['id']} غيّرت مدخلات {len(more)} خطوة مكتملة بعدها فتُعاد — {why}")
                redo |= more
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
        if not entry_allows_progress(s, e):
            pend.append(s["id"])
    if pend:
        print(f"✘ بوابات غير مكتملة في سجل {date}: {'، '.join(pend)}")
        return 2
    print(f"✔ كل بوابات {date} مكتملة في سجل المحرّك")
    return 0


def gate_json(root, date, through=None, final=False):
    """يكتب logs/gate-<date>/gate.json من سجل المحرّك (يقرؤه write_mark وskill_lessons) — لا من الذاكرة.

    final=True (2026-11-19، بوابة واحدة): الحكم النهائي من سجل المحرّك نفسه بعد آخر بوابة،
    فلا تُعاد final_gate.sh بعد الخط (كانت تعيد البناء والاختبارات وتعدّل النص بعد البناء).
    يلزم through (آخر بوابة قبل خطوة الحكم)، ويفشل مغلقًا إن بقيت بوابة بعده لم تُحسب."""
    import datetime
    m = load(root)
    ledger = read_ledger(root, m, date)
    if final:
        if not through:
            print("✘ gate-json --final يلزمه --through (آخر بوابة قبل خطوة الحكم)")
            return 2
        ids = [s["id"] for s in m["steps"]]
        if through not in ids:
            print(f"✘ --through {through} ليست خطوة في المانيفست")
            return 2
        phases = m.get("gate_phases", ["gates"])
        after = [s["id"] for s in m["steps"][ids.index(through) + 1:]
                 if s.get("phase") in phases and not s.get("disabled")
                 and "gate-json" not in " ".join(s.get("command") or [])]
        if after:
            print(f"✘ بوابات بعد {through} لن تدخل الحكم النهائي: {'، '.join(after)}")
            return 2
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
        elif e and e["status"] == "skipped" and s.get("disabled"):
            st, rc = "skipped", 0
        else:
            st = "block"
            rc = 2
        if e and e.get("rc") is not None and st != "ok":
            rc = e["rc"]
        if st == "block":
            blocked.append(name)
        worst = max(worst, {"ok": 0, "warn": 1, "skipped": 0, "block": 2}[st])
        steps.append({"step": name, "id": s["id"], "status": st, "exit_code": rc,
                      "disabled": bool(s.get("disabled")), "reason": s.get("reason"),
                      "log": (e or {}).get("log")})
        if through and s["id"] == through:
            break
    out = {"date": date, "status": {0: "ok", 1: "warn", 2: "block"}[worst], "exit_code": worst, "steps": steps,
           "blocked_steps": blocked, "source": "runbook-ledger", "dir": f"logs/gate-{date}", "log_dir": f"logs/gate-{date}",
           "stage": "final" if final else "provisional",
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
    runtime_outputs = set(s.get("runtime_outputs", []))
    for key in ("reads", "writes"):
        for p in s.get(key, []):
            if p in runtime_outputs:
                continue
            yield key, p
    if s.get("prompt"):
        yield "prompt", s["prompt"]
    links = s.get("links", {})
    for k in ("files", "folders", "gates", "tests"):
        for p in links.get(k, []):
            if p in runtime_outputs:
                continue
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
        self.unique_names = [(n, fs[0]) for n, fs in self.by_name.items() if len(fs) == 1 and len(n) >= 6]
        # فهرس دقيق مكافئ لـ «name in text»: كل اسم ينتهي بامتداده، فيُبحث عن الامتداد ثم تُقارن الشرائح.
        self.names_by_tail, self.untailed_names = {}, []
        for n, f in self.unique_names:
            if "." in n[1:]:
                tail = "." + n.rsplit(".", 1)[1]
                self.names_by_tail.setdefault(tail, {}).setdefault(len(n), {})[n] = f
            else:
                self.untailed_names.append((n, f))

    def refs(self, text, src):
        found = set()
        for m in PATH_RE.finditer(text):
            for h in self.suffix.get(m.group(1).lstrip("./"), []):
                found.add(h)
        for tail, by_len in self.names_by_tail.items():
            pos = text.find(tail)
            while pos != -1:
                end = pos + len(tail)
                for n_len, names in by_len.items():
                    if n_len <= end:
                        hit = names.get(text[end - n_len:end])
                        if hit:
                            found.add(hit)
                pos = text.find(tail, pos + 1)
        for name, f in self.untailed_names:
            if name in text:
                found.add(f)
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

    _memo = {}

    def _refs_of(cur):
        if cur not in _memo:
            _memo[cur] = idx.refs(read_text(root, cur), cur)
        return _memo[cur]

    def bfs(start, code_only):
        seen, queue = set(start), list(start)
        while queue:
            cur = queue.pop()
            ext = os.path.splitext(cur)[1]
            if code_only and ext not in CODE_EXT and ext not in (".json", ".md"):
                continue
            if code_only and ext in (".md",) and not cur.startswith("runbook/prompts/"):
                continue  # الوثائق لا تُعدّ «استدعاءً» في المرحلة الأولى
            for h in _refs_of(cur):
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
    print_policy = m.get("print") or {}
    print_state = "مفعّلة" if print_policy.get("enabled", True) else "معطّلة"
    print_reason = f" — {print_policy.get('reason')}" if print_policy.get("reason") else ""
    L = ["# كتيب الإجراءات التشغيلية", "",
         f"<!-- مولَّد آليًا من runbook/runbook.json (بصمة {h}). لا تعدّله يدويًا: عدّل المانيفست ثم شغّل handbook. -->", "",
         "لا يعتمد التشغيل على ذاكرة الوكيل: المحرّك ينفّذ الخطوات بالترتيب، ولا تبدأ خطوة قبل اكتمال ما قبلها بدليل.", "",
         f"سياسة الطباعة: {print_state}{print_reason}.", "",
         "## الخطوات", "",
         "| # | الخطوة | المنفّذ | يقرأ | يكتب | شرط الإتمام | القواعد | الملفات والمجلدات المرتبطة | عند الفشل |",
         "|---|---|---|---|---|---|---|---|---|"]
    for s in m["steps"]:
        links = s.get("links", {})
        conds = "؛ ".join(f"{a['type']}:{a.get('path', ' '.join(a.get('command', [])))}" for a in s.get("assert", []))
        rel = "، ".join(links.get("files", []) + links.get("folders", []) + links.get("gates", []))
        state = ""
        if s.get("optional"):
            state += " (اختيارية)"
        if s.get("disabled"):
            state += f" (معطّلة: {s.get('reason', 'سبب غير مذكور')})"
        L.append(f"| {s['id']} | {s['title']}{state} | {s['kind']} | "
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
    ap.add_argument("--root", default=None)
    ap.add_argument("--id")
    ap.add_argument("--title")
    ap.add_argument("--kind")
    ap.add_argument("--after", default="START")
    ap.add_argument("--through", help="gate-json: آخر خطوة تُحسب (ما بعدها لم يحن وقته)")
    ap.add_argument("--final", action="store_true", help="gate-json: الحكم النهائي من سجل المحرّك (يلزمه --through)")
    ap.add_argument("--only", default="", help="معرّفات خطوات تُنفَّذ وحدها ثم يتوقف المحرّك (ك-568)، مفصولة بفاصلة")
    ap.add_argument("--redo", default="", help="معرّفات خطوات تُعاد للتحقق بعد تغيّر مدخلاتها، مفصولة بفاصلة (ك-321)")
    ap.add_argument("--no-auto-redo", action="store_true",
                    help="إيقاف الإعادة الآلية للخطوات المتأثرة (الافتراضي: مفعّلة، tools/runbook_stale.py)")
    a = ap.parse_args()
    c = a.cmd
    try:
        root = discover_root(a.root or __file__, explicit=a.root is not None)
    except ManifestNotFound as exc:
        print(f"✘ فشل مغلق: {exc}")
        return 2
    if c == "verify":
        return verify(root)
    if c == "run":
        only = [x for x in getattr(a, "only", "").split(",") if x.strip()]
        # --only (ك-568) تشغيل محصور بخطوات معلومة يُستدعى من داخل خطوة أخرى؛ لا إعادة آلية فيه
        return run_auto(root, a.date, redo=[x for x in a.redo.split(",") if x.strip()],
                        only_steps=only, auto_redo=not (a.no_auto_redo or only))
    if c == "gates":
        return run_auto(root, a.date, only_phase="gates", redo=[x for x in a.redo.split(",") if x.strip()],
                        auto_redo=not a.no_auto_redo)
    if c == "gate-json":
        return gate_json(root, a.date, a.through, final=a.final)
    if c == "gates-status":
        return gates_status(root, a.date)
    if c == "complete":
        return complete(root, a.step, a.date)
    if c == "status":
        return status(root, a.date)
    if c == "timings":
        if not a.date:
            print("✘ timings يحتاج --date")
            return 2
        report_timings(root, a.date)
        print(timings(root, a.date))
        return 0
    if c == "handbook":
        return handbook(root)
    if c == "section-add":
        return section_add(root, a.id, a.title, a.after)
    if c == "section-remove":
        return section_remove(root, a.id)
    if c == "step-add":
        return step_add(root, a.id, a.title, a.kind, a.after)
    if c == "step-remove":
        return step_remove(root, a.id)
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
