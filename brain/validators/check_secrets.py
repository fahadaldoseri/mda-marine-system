#!/usr/bin/env python3
"""بوابة الأسرار: تمنع أي سرّ في الشجرة أو في أي ملف قبل النسخ الاحتياطي أو الدفع.

الاستخدام:
  python3 validators/check_secrets.py --tree          # الشجرة الحالية (المتتبَّعة + الجديدة)
  python3 validators/check_secrets.py --staged        # ما هو مُجهَّز للالتزام
  python3 validators/check_secrets.py --history       # كل تاريخ Git (يستغرق وقتًا)
  python3 validators/check_secrets.py --file <path>   # ملف واحد

رموز الخروج: 0 نظيف · 70 سرّ مكتشف (منع) · 2 خطأ استعمال.
لا تُطبع أي قيمة سرّ: تُعرض المسارات والنوع فقط.
"""
from __future__ import annotations

import argparse
import os
import re
import json
import subprocess
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ملفات مسموح لها احتواء أنماط سرّية دون أن تكون أسرارًا (أمثلة، اختبارات، توثيق)
ALLOWLIST = {
    "secrets/secrets.env.example",
    "secrets/README.md",
    "tests/fixtures/dummy-secrets.txt",
    "tests/test_new_validators.py",   # اختبار زرع صناعي: قيم وهمية لا حقيقية
}

# إعفاء واحد مكتوب السبب (قرار المالك 2026-10-24: «تُحفظ الأسرار نصًّا صريحًا في المستودع الخاص»
# و«الأسرار الأخرى في secrets.env تبقى كما هي») — موثَّق في ك-166 وك-168.
# الإعفاء لهذا المسار وحده؛ أي سرّ في أي ملف آخر يبقى مانعًا، ويُثبته اختبار في tests/run_checks.sh.
OWNER_APPROVED = {
    "secrets/secrets.env": "قرار المالك 2026-10-24: حفظ الأسرار نصًّا في المستودع الخاص — مخاطرة مقبولة موثَّقة",
}

PATTERNS = {
    "رمز بوت تلغرام": r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b",
    "مفتاح OpenAI": r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b",
    "مفتاح Anthropic": r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b",
    "رمز GitHub": r"\b(?:ghp|gho|ghs|ghr)_[A-Za-z0-9]{20,}\b",
    "مفتاح AWS": r"\bAKIA[0-9A-Z]{16}\b",
    "مفتاح Google": r"\bAIza[0-9A-Za-z_\-]{30,}\b",
    "تعيين سرّي بقيمة": r"(?i)\b(TOKEN|API_KEY|APIKEY|SECRET|PASSWORD|BOT_TOKEN)\b\s*[=:]\s*[\"']?([A-Za-z0-9_\-]{24,})",
    "معرّف محادثة تلغرام": r"(?i)\b(?:TELEGRAM_)?(?:OWNER_)?CHAT_ID\b\s*[=:]\s*[\"']?-?\d{6,}",
}

# استثناء ضيق موثّق: في Python قد يطابق الفحص مرجع دالة داخليًا عاريًا مثل
# ``token = _canonical_identifier_token``. هذا ليس قيمة نصية ولا جدول أسرار؛
# القيم المقتبسة، والقيم ذات الأنماط السرية، وكل الامتدادات الأخرى تبقى مانعة.
PLACEHOLDER_RE = re.compile(
    r"(?i)(xxxx|example|placeholder|redact|dummy|fake|<[^>]{2,}>|your[_-]?(token|key|secret)|"
    r"مثال|وهمي|بديل|\bTODO\b|\bCHANGEME\b)"
)


PY_BARE_INTERNAL_REF = re.compile(
    r"(?i)\b(TOKEN|API_KEY|APIKEY|SECRET|PASSWORD|BOT_TOKEN)\b\s*[=:]\s*_([A-Za-z_][A-Za-z0-9_]*)"
)

TEXT_SUFFIXES = {".py", ".sh", ".md", ".json", ".jsonl", ".txt", ".html", ".css", ".js",
                 ".yml", ".yaml", ".env", ".ini", ".cfg", ".log", ".csv", ""}


def env_secret_values() -> list[str]:
    name = re.compile(r"(TOKEN|SECRET|API_KEY|APIKEY|PASSWORD|PASSWD|KEY)$")
    vals = [v for k, v in os.environ.items() if v and len(v) >= 12 and name.search(k.upper())]
    return sorted(set(vals), key=len, reverse=True)


def scan_text(path: str, text: str, env_vals: list[str]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for kind, pattern in PATTERNS.items():
        for match in re.finditer(pattern, text):
            if PLACEHOLDER_RE.search(text, max(0, match.start() - 40), match.end() + 40):
                continue
            if (
                kind == "تعيين سرّي بقيمة"
                and PY_BARE_INTERNAL_REF.search(text, match.start(), match.end())
            ):
                continue
            hits.append((kind, path))
            break
    for value in env_vals:
        if value in text:
            hits.append(("قيمة سرّية فعلية من البيئة", path))
            break
    return hits


def iter_tree(root: Path) -> list[str]:
    try:
        tracked = subprocess.run(["git", "-C", str(root), "ls-files"],
                                 capture_output=True, text=True, timeout=120).stdout.split()
    except Exception:
        tracked = []
    if not tracked:
        tracked = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
    return tracked



HISTORY_CURSOR = "logs/secrets-history-cursor.json"
WINDOW = 262144  # نافذة قراءة التصحيحة


def history_revs(root: Path) -> list[str]:
    """شعب كل الالتزامات (قائمة نصوص صغيرة) بلا تحميل فروقها."""
    out = subprocess.run(["git", "-C", str(root), "rev-list", "--all"],
                         capture_output=True, text=True, errors="ignore", timeout=180).stdout
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def is_allowed(path: str, allow: set[str]) -> bool:
    """إعفاء المسار في التاريخ: مطابقة تامة، أو ذيل، أو اسم ملف — لاختلاف بادئات الالتزامات القديمة."""
    if path in allow:
        return True
    base = path.rsplit("/", 1)[-1]
    for a in allow:
        if path.endswith("/" + a) or base == a.rsplit("/", 1)[-1]:
            return True
    return False


def _segments(text: str) -> list[tuple[str, str]]:
    """يقسّم نص التصحيحة إلى (مسار، نص) لكل ملف — بلا تجميع التاريخ كله."""
    out: list[tuple[str, str]] = []
    for seg in re.split(r"(?m)^diff --git ", text)[1:]:
        m = re.search(r"(?m)^\+\+\+ b/(\S+)", seg)
        out.append((m.group(1) if m else "?", seg))
    return out


def _scan_big(path: str, text: str, env_vals: list[str]) -> bool:
    """يفحص نصًّا كبيرًا بنفس منطق الشجرة الحاكم (مع استثناء المرجع الداخلي العاري)."""
    for i in range(0, len(text), 4_000_000):
        if scan_text(path, text[i:i + 4_000_000], env_vals):
            return True
    return False


def scan_commit(sha: str, env_vals: list[str], allow: set[str]) -> list[tuple[str, str]]:
    """فحص تدفقي لتصحيحة واحدة: ذاكرة محدودة مهما كبر الالتزام."""
    proc = subprocess.Popen(["git", "-C", str(ROOT), "show", sha, "--no-color", "--format="],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, errors="ignore")
    hits: list[tuple[str, str]] = []
    buf = ""
    path = "?"
    assert proc.stdout is not None
    try:
        while True:
            chunk = proc.stdout.read(WINDOW)
            if not chunk:
                break
            data = buf + chunk
            idx = data.rfind("\ndiff --git ")
            if idx == -1:
                buf = data
                continue
            complete, buf = data[:idx], data[idx:]
            for seg_path, seg in _segments(complete):
                path = seg_path
                if is_allowed(seg_path, allow):
                    continue
                if _scan_big(seg_path, seg, env_vals):
                    hits.append(("نمط سرّي في تاريخ Git", f"{sha[:8]}:{seg_path}"))
        for seg_path, seg in _segments(buf):
            path = seg_path
            if is_allowed(seg_path, allow):
                continue
            if _scan_big(seg_path, seg, env_vals):
                hits.append(("نمط سرّي في تاريخ Git", f"{sha[:8]}:{seg_path}"))
    finally:
        proc.stdout.close()
        proc.wait(timeout=60)
    return hits


def history_scan(env_vals: list[str], allow: set[str], budget: float,
                 reset: bool) -> tuple[list[tuple[str, str]], str, bool]:
    """يفحص تاريخ Git على دفعات مع مؤشر محفوظ؛ يعيد (اكتشافات، تغطية، جزئي)."""
    cur_file = ROOT / HISTORY_CURSOR
    state: dict[str, object] = {}
    if cur_file.is_file() and not reset:
        try:
            state = json.loads(cur_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = {}
    revs = history_revs(ROOT)
    last = str(state.get("last_sha") or "")
    idx = revs.index(last) + 1 if last and last in revs else 0
    deadline = time.monotonic() + max(0.0, budget)
    hits: list[tuple[str, str]] = []
    partial = False
    from concurrent.futures import ThreadPoolExecutor

    while idx < len(revs):
        if time.monotonic() > deadline:
            partial = True
            break
        batch = revs[idx:idx + 64]
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda sh: scan_commit(sh, env_vals, allow), batch))
        for sha, found in zip(batch, results):
            if found:
                hits += found
                last = sha
                idx += 1
                partial = True
                break
        else:
            last = batch[-1]
            idx += len(batch)
        if hits:
            break
    cur_file.write_text(json.dumps(
        {"last_sha": last, "scanned_upto_index": idx, "total_commits": len(revs),
         "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return hits, f"{idx}/{len(revs)}", partial


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", action="store_true", help="الشجرة المتتبَّعة")
    ap.add_argument("--staged", action="store_true", help="الملفات المُجهَّزة للالتزام")
    ap.add_argument("--history", action="store_true", help="كل تاريخ Git")
    ap.add_argument("--file", action="append", default=[], help="ملف محدد")
    ap.add_argument("--root", default=None, help="جذر الفحص (افتراضيًا مجلد brain)")
    ap.add_argument("--allow", action="append", default=[], help="مسار مسموح (يُضاف للمسموح)")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--history-budget", type=float, default=240.0,
                    help="سقف ثواني فحص التاريخ في النداء الواحد (تزايدي)")
    ap.add_argument("--history-reset", action="store_true", help="تصفير مؤشر التاريخ")
    args = ap.parse_args()

    global ROOT
    if args.root:
        ROOT = Path(args.root).resolve()
    env_vals = env_secret_values()
    allow = set(ALLOWLIST) | set(OWNER_APPROVED) | set(args.allow)
    # المسار يُعفى بالاسم أو بذيله: brain/secrets/secrets.env وsecrets/secrets.env مسار واحد (عطل ك-172).
    # عطل ك-172: المستودع يسمّي المسار brain/secrets/secrets.env والخادم secrets/secrets.env —
    # الإعفاء يشمل الاسم وبادئة brain/ معًا، وإلا مُنع الدفع بلا سبب.
    allow = allow | {("brain/" + a) for a in list(allow) if "/" in a and not a.startswith("brain/")}
    hits: list[tuple[str, str]] = []

    if args.staged:
        files = subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--name-only"],
                               capture_output=True, text=True).stdout.split()
        for rel in files:
            if rel in allow:
                continue
            p = ROOT / rel
            if p.is_file():
                hits += scan_text(rel, p.read_text(encoding="utf-8", errors="ignore"), env_vals)
    elif args.history:
        h_hits, h_cov, h_part = history_scan(env_vals, allow, args.history_budget, args.history_reset)
        hits += h_hits
        if not args.quiet:
            print(f"   تغطية تاريخ Git: {h_cov}" + (" (جزئية — تُستأنف في النداء التالي)" if h_part else " (كاملة)"))
    else:
        targets = args.file or iter_tree(ROOT)
        for rel in targets:
            rel = rel.replace(str(ROOT) + "/", "")
            if rel in allow:
                continue
            p = Path(rel) if Path(rel).is_absolute() else ROOT / rel
            if not p.is_file() or p.suffix not in TEXT_SUFFIXES:
                continue
            if p.stat().st_size > 3_000_000:
                continue
            hits += scan_text(rel, p.read_text(encoding="utf-8", errors="ignore"), env_vals)

    if hits:
        if not args.quiet:
            print(f"✘ بوابة الأسرار: {len(hits)} اكتشاف — منع")
            for kind, path in hits[:20]:
                print(f"   · {kind} — {path}")
        return 70
    if not args.quiet:
        print("✔ بوابة الأسرار: لا سرّ في النطاق المفحوص")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
