#!/usr/bin/env python3
"""تدوير TELEGRAM_WEBHOOK_SECRET بلا كشف القيم.

ينفذ جرد المستهلكين، ونسخة احتياطية محلية بصلاحيات مقفلة، وفحصًا لسجل Git،
ثم يحدّث الويب هوك والملفات المحلية، ويوثق البصمات فقط، ويتحقق من الحالة الحية.
الاستخدام: python3 tools/rotate_webhook_secret.py --brain DIR [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

KEY = "TELEGRAM_WEBHOOK_SECRET"
TOKEN_KEY = "TELEGRAM_BOT_TOKEN"
_SECRET_FILES = {".env", ".env.local", "secrets.env", "webhook-secret.txt"}
_SKIP_DIRS = {".git", "__pycache__", "node_modules", "secret-rotation-backups"}


def _discover(explicit: str | None, env: str, names: tuple[str, ...]) -> Path:
    if explicit:
        return Path(explicit)
    value = os.environ.get(env)
    if value:
        return Path(value)
    here = Path(__file__).resolve()
    for base in (here.parent, *here.parents):
        for name in names:
            candidate = base / name
            if candidate.is_dir():
                return candidate
    return here.parents[2] / names[0]


def fp(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line.strip())
        if match:
            out[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return out


def write_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def api(token: str, method: str, params: dict | None = None) -> dict:
    if not token:
        return {"ok": False, "error": "NO_TOKEN"}
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode() if params else None
    request = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
            return payload if isinstance(payload, dict) else {"ok": False, "error": "INVALID_RESPONSE"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:120]}


def _safe(text: object, *secret_values: str) -> str:
    rendered = str(text)
    for value in secret_values:
        if value:
            rendered = rendered.replace(value, "[محجوب]")
    return rendered


def _iter_text_files(root: Path):
    if not root.is_dir():
        return
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS]
        for filename in filenames:
            path = Path(directory) / filename
            if path.stat().st_size > 3_000_000 or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".woff2", ".zip", ".webm"}:
                continue
            yield path


def consumer_inventory(root: Path) -> list[str]:
    """أعد مسارات المستهلكين فقط، لا محتوى الملفات ولا القيم."""
    needles = (KEY, "WEBHOOK_SECRET", "secret_token", "webhook-secret")
    hits: list[str] = []
    for path in _iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(needle in text for needle in needles):
            hits.append(path.relative_to(root).as_posix())
    return sorted(set(hits))


def scan_value(root: Path, value: str, exclude: set[str] | None = None) -> list[str]:
    if not value:
        return []
    excluded = exclude or set()
    hits: list[str] = []
    for path in _iter_text_files(root):
        if any(part in excluded for part in path.relative_to(root).parts):
            continue
        try:
            if value in path.read_text(encoding="utf-8", errors="ignore"):
                hits.append(path.relative_to(root).as_posix())
        except OSError:
            continue
    return sorted(set(hits))


def git_history_hits(root: Path, value: str) -> int:
    """ابحث في التاريخ بلا طباعة diff أو سطر قد يحمل السر."""
    if not value or not (root / ".git").exists():
        return 0
    try:
        commits = subprocess.run(
            ["git", "-C", str(root), "rev-list", "--all", "--max-count=500"],
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return 0
    count = 0
    for commit in commits:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "grep", "-l", "-I", "-F", value, commit, "--"],
                capture_output=True, text=True, timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            count += len([line for line in result.stdout.splitlines() if line.strip()])
    return count


def backup_files(paths: list[Path], destination: Path, stamp: str) -> int:
    target = destination / stamp
    target.mkdir(parents=True, exist_ok=True)
    os.chmod(destination, 0o700)
    os.chmod(target, 0o700)
    copied = 0
    for path in paths:
        if not path.is_file():
            continue
        safe_name = path.name.replace("/", "_")
        shutil.copy2(path, target / safe_name)
        os.chmod(target / safe_name, 0o600)
        copied += 1
    return copied


def restore_files(env_path: Path, state_path: Path, backup_dir: Path, stamp: str) -> None:
    source = backup_dir / stamp
    for path in (env_path, state_path):
        backup = source / path.name.replace("/", "_")
        if backup.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, path)
            os.chmod(path, 0o600)


def update_docs(path: Path, stamp: str, old_fp: str, new_fp: str, consumers: int, history_hits: int, live_ok: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        current = path.read_text(encoding="utf-8", errors="ignore")
    else:
        current = "# سجل تدوير الأسرار\n"
    entry = (
        f"\n- {stamp}: تدوير `{KEY}`؛ البصمة السابقة `{old_fp}` والجديدة `{new_fp}` فقط. "
        f"المستهلكون المرصودون {consumers}؛ مواضع التاريخ {history_hits}؛ التحقق الحي {'ناجح' if live_ok else 'غير مكتمل'}.\n"
        "  لا تُسجَّل قيمة السر هنا؛ النسخة الاحتياطية المقفلة هي مرجع الاستعادة.\n"
    )
    path.write_text(current.rstrip() + entry, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain")
    parser.add_argument("--repo", help="جذر مستودع Git لفحص التاريخ؛ افتراضيًا --brain")
    parser.add_argument("--env")
    parser.add_argument("--state")
    parser.add_argument("--docs")
    parser.add_argument("--backup-dir")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-telegram", action="store_true")
    parser.add_argument("--allow-local-only", action="store_true")
    args = parser.parse_args()

    brain = _discover(args.brain, "BRAIN_DIR", ("brain-marine-news", "brain"))
    repo = Path(args.repo) if args.repo else brain
    env_path = Path(args.env) if args.env else brain / "secrets" / "secrets.env"
    state_path = Path(args.state) if args.state else brain / "state" / "webhook-secret.txt"
    docs_path = Path(args.docs) if args.docs else (
        brain / "appendices" / "security-notes.md" if (brain / "appendices" / "security-notes.md").is_file()
        else brain / "docs" / "secret-rotation.md"
    )
    backup_dir = Path(args.backup_dir) if args.backup_dir else brain / "state" / "secret-rotation-backups"

    values = read_env(env_path)
    old = values.get(KEY) or (state_path.read_text(encoding="utf-8").strip() if state_path.is_file() else "")
    if not old:
        print("✘ لا توجد قيمة قديمة للتدوير")
        return 2
    token = values.get(TOKEN_KEY, "")
    consumers = consumer_inventory(brain)
    history_hits = git_history_hits(repo, old)
    print(f"  جرد المستهلكين قبل التدوير: {len(consumers)} مسارًا")
    print(f"  فحص سجل Git السابق: {history_hits} موضعًا؛ لا تُطبع القيم")

    info = {"ok": False, "error": "SKIPPED"} if args.skip_telegram else api(token, "getWebhookInfo")
    url = (info.get("result") or {}).get("url", "") if info.get("ok") else ""
    print(f"  الويب هوك الحالي: {'مُسجَّل' if url else 'غير مُسجَّل'} · استجابة_API={'ok' if info.get('ok') else info.get('error')}")

    new = secrets.token_urlsafe(32)
    print(f"  البصمة القديمة={fp(old)} · البصمة الجديدة={fp(new)} · الأطوال فقط محفوظة ({len(old)}/{len(new)})")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    planned = [env_path, state_path]
    print(f"  النسخة الاحتياطية المخططة: {backup_dir} · الملفات الموجودة={sum(p.is_file() for p in planned)}")
    print(f"  الوثيقة المخططة: {docs_path}")

    if args.dry_run:
        print("  تجربة فقط — لم تُكتب ملفات ولم تُحدَّث الجهة الخارجية")
        return 0

    if args.skip_telegram and not args.allow_local_only:
        print("✘ التدوير المحلي وحده مرفوض؛ استخدم --allow-local-only بعد توثيق سبب عدم التحقق الحي")
        return 3

    backed_up = backup_files(planned, backup_dir, stamp)
    print(f"  النسخة الاحتياطية: {backed_up} ملفًا · المجلد مقفول")
    values[KEY] = new
    write_env(env_path, values)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(new + "\n", encoding="utf-8")
    os.chmod(state_path, 0o600)

    live_ok = args.skip_telegram
    if not args.skip_telegram and token and url:
        result = api(token, "setWebhook", {"url": url, "secret_token": new, "drop_pending_updates": "false"})
        if not result.get("ok"):
            restore_files(env_path, state_path, backup_dir, stamp)
            print(f"✘ فشل تسجيل الويب هوك؛ استُعيدت الملفات المحلية: {_safe(result.get('detail') or result.get('description'), old, new, token)}")
            return 2
        check = api(token, "getWebhookInfo")
        live_ok = bool(check.get("ok") and (check.get("result") or {}).get("url") == url)
        print(f"  التحقق الحي بعد التدوير: {'✔ ناجح' if live_ok else '✘ غير مكتمل'} · الرابط محفوظ={bool((check.get('result') or {}).get('url'))}")
    elif not args.skip_telegram:
        live_ok = False
        print("✘ لا يمكن إثبات التحقق الحي: التوكن أو رابط الويب هوك غير متاح")

    remaining = scan_value(brain, old, {backup_dir.name})
    local_ok = fp(read_env(env_path).get(KEY, "")) == fp(new) and fp(state_path.read_text(encoding="utf-8").strip()) == fp(new)
    update_docs(docs_path, stamp, fp(old), fp(new), len(consumers), history_hits, live_ok)
    print(f"  بقايا القيمة القديمة في الشجرة بعد الاستثناءات: {len(remaining)} · المخزن المحلي مطابق بالبصمة؟ {local_ok}")
    if not local_ok or not (live_ok or args.allow_local_only):
        print("✘ لم يكتمل إثبات التدوير؛ راجع النسخة الاحتياطية دون عرض أي قيمة")
        return 2
    print("✔ اكتمل التدوير مع توثيق آمن والتحقق المطلوب")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
