#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة مطابقة النسخة الاحتياطية: تحرس أن المستودع المدفوع = الشجرة المحلية.

الخلل الذي تمنعه (عطل ك-06 وك-07 وك-09): استثناء صامت — يُدفع المشروع ناقصًا بلا إعلان.
الوضع: --mode strict (مانع، يُستعمل بعد خطوة النسخ) | --mode advisory (تنبيه، قبل النسخ)
رموز الخروج: 0 مطابق · 1 انحراف في الوضع التنبيهي · 2 انحراف في الوضع المانع · 3 مستودع مفقود
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

def _git_toplevel(start: Path) -> Path | None:
    """جذر مستودع النسخ بالقياس لا بالافتراض (ك-567).

    السبب المقيس: كان الافتراض ``B.parent / "mda-marine-system"`` فينتج
    ``/home/ubuntu/mda-marine-system/mda-marine-system`` وهو غير موجود، فيُتخطّى
    فحص التماثل الصارم برسالة تحذير ورمز 3. القياس من Git يوحّد D005 وD040
    ويصحّ عند نقل المشروع أو تغيير اسم المجلد.
    """
    try:
        out = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=False)
    except OSError:
        return None
    root = out.stdout.strip()
    return Path(root) if out.returncode == 0 and root else None


B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
S = Path(os.environ.get("SITE_DIR") or B.parent / "seawatch")
REPO = Path(os.environ.get("BACKUP_REPO_DIR") or "") if os.environ.get("BACKUP_REPO_DIR") else None
if REPO is None:
    REPO = _git_toplevel(B) or B.parent
SCOPE_ENV = "PARITY_SCOPE_FILE"

# مخرجات تشغيل محلية مؤقتة لا تُنقل إلى المرآة ولا تُعدّ انحرافًا حاكمًا.
# تُحصر بالبادئة كي لا يُستثنى ملف شيفرة أو بيانات بلا سبب مكتوب.
LOCAL_ONLY_PATTERNS = (
    "audit/backups/",
    "brain/logs/skills-sync-",
    "brain/logs/skills-canon-",
    "brain/logs/apply-",
    "brain/logs/",
    "logs/",
)


class ScopeError(ValueError):
    """سجل النطاق مفقود/فاسد أو مسار لا ينتمي إلى فئة معلنة."""


def load_scope() -> dict:
    path = Path(os.environ.get(SCOPE_ENV) or B / "runbook" / "parity-scope.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ScopeError(f"تعذّر قراءة {path.name}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ScopeError("parity-scope.json يجب أن يكون كائنًا بإصدار 1")
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ScopeError("parity-scope.json يجب أن يحوي categories غير فارغة")
    seen: set[str] = set()
    for item in categories:
        if not isinstance(item, dict):
            raise ScopeError("كل فئة في parity-scope.json يجب أن تكون كائنًا")
        ident = item.get("id")
        if not isinstance(ident, str) or not ident.strip() or ident in seen:
            raise ScopeError("معرّف فئة مفقود أو مكرر في parity-scope.json")
        if not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise ScopeError(f"الفئة {ident} بلا سبب مكتوب")
        if item.get("policy") not in {"strict", "informational"}:
            raise ScopeError(f"سياسة الفئة {ident} غير معروفة")
        if not isinstance(item.get("prefixes"), list) or not all(
            isinstance(v, str) and v for v in item["prefixes"]
        ):
            raise ScopeError(f"الفئة {ident} بلا prefixes صالحة")
        if not isinstance(item.get("exact", []), list) or not all(
            isinstance(v, str) and v for v in item.get("exact", [])
        ):
            raise ScopeError(f"exact في الفئة {ident} غير صالح")
        seen.add(ident)
    roots = data.get("roots")
    if not isinstance(roots, dict) or not isinstance(roots.get("brain"), dict) or not isinstance(roots.get("site"), dict):
        raise ScopeError("parity-scope.json يجب أن يعلن roots.brain وroots.site")
    repo = data.get("repo")
    if not isinstance(repo, dict):
        raise ScopeError("parity-scope.json يجب أن يعلن repo")
    for key in ("only_prefixes", "extra_allow", "sanitized", "protected", "symlink_views"):
        if not isinstance(repo.get(key), list) or not all(isinstance(v, str) and v for v in repo[key]):
            raise ScopeError(f"repo.{key} غير صالح في parity-scope.json")
    return data


def _root_policy(scope: dict, root: str) -> tuple[set[str], set[str]]:
    policy = scope["roots"][root]
    dirs = policy.get("skip_dirs", [])
    files = policy.get("skip_files", [])
    if not isinstance(dirs, list) or not all(isinstance(v, str) for v in dirs):
        raise ScopeError(f"roots.{root}.skip_dirs غير صالح")
    if not isinstance(files, list) or not all(isinstance(v, str) for v in files):
        raise ScopeError(f"roots.{root}.skip_files غير صالح")
    return set(dirs), set(files)


def classify(rel: str, scope: dict) -> dict:
    matches = []
    for item in scope["categories"]:
        if rel in item.get("exact", []) or any(rel.startswith(prefix) for prefix in item["prefixes"]):
            matches.append(item)
    if not matches:
        raise ScopeError(f"مسار غير مصنّف: {rel}")
    lengths = [max([len(p) for p in item.get("prefixes", []) if rel.startswith(p)] + [len(rel) if rel in item.get("exact", []) else 0]) for item in matches]
    max_len = max(lengths)
    best = [item for item, length in zip(matches, lengths) if length == max_len]
    if len({item["id"] for item in best}) != 1:
        raise ScopeError(f"تصنيف متعارض للمسار: {rel}")
    return best[0]


def classify_all(paths, scope: dict) -> dict[str, dict]:
    return {rel: classify(rel, scope) for rel in paths}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def manifest(root: Path, skip_dirs, skip_files, prefix: str, junk_files=()):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in skip_dirs]
        rd = Path(dp).relative_to(root)
        for fn in fns:
            p = Path(dp) / fn
            rel = (rd / fn).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            if rel in skip_files or p.suffix == ".pyc" or fn in junk_files:
                continue
            if p.is_symlink():
                tgt = p.resolve()
                for _tree, rp in ((B, "brain"), (S, "site")):
                    try:
                        out[f"{prefix}/{rel}"] = ("link", f"{rp}/{tgt.relative_to(_tree.resolve()).as_posix()}")
                        break
                    except ValueError:
                        continue
                else:
                    out[f"{prefix}/{rel}"] = ("link", f"خارج الشجرتين: {tgt}")
            else:
                out[f"{prefix}/{rel}"] = ("file", sha(p))
    return out


def repo_manifest(scope: dict):
    out = {}
    # ك-160: كان المسح يعتمد مجلد العمل فيحسب ملفات غير متتبَّعة (مثل __pycache__)
    # «زائدة في المستودع». المصدر الآن ما يتتبعه Git فعلًا.
    try:
        tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z"],
                                 capture_output=True, check=True).stdout.decode("utf-8")
        files = [f for f in tracked.split("\0") if f]
    except Exception:
        files = None
    if files is None:
        for dp, dns, fns in os.walk(REPO):
            dns[:] = [d for d in dns if d != ".git"]
            rd = Path(dp).relative_to(REPO)
            for fn in fns:
                files = (files or []) ; break
        files = []
    if files:
        for rel in files:
            if rel in scope["repo"]["extra_allow"]:
                continue
            p = REPO / rel
            if p.is_symlink():
                # رابط إلى مجلد = اسم شجرة لا ملف محتوى؛ الشجرة المحلية لا تُدرجه
                try:
                    if p.resolve().is_dir():
                        continue
                except OSError:
                    pass
                tgt = os.path.normpath((Path(rel).parent / os.readlink(p)).as_posix())
                while tgt.startswith("./"):
                    tgt = tgt[2:]
                out[rel] = ("link", tgt)
            elif p.is_file():
                out[rel] = ("file", sha(p))
        return out
    for dp, dns, fns in os.walk(REPO):
        dns[:] = [d for d in dns if d != ".git"]
        rd = Path(dp).relative_to(REPO)
        for fn in fns:
            p = Path(dp) / fn
            rel = (rd / fn).as_posix()
            if rel in scope["repo"]["extra_allow"]:
                continue
            if p.is_symlink():
                tgt = os.path.normpath((Path(rel).parent / os.readlink(p)).as_posix())
                while tgt.startswith("./"):
                    tgt = tgt[2:]
                out[rel] = ("link", tgt)
            else:
                out[rel] = ("file", sha(p))
    return out


def _source_git() -> tuple[Path, str, bool]:
    """حدد Git الذي يمثل لقطة المصدر ومسار الجذر داخل ذلك Git."""
    explicit = os.environ.get("SOURCE_GIT_DIR")
    root = Path(explicit) if explicit else REPO
    if explicit or (B / ".git").exists():
        prefix = os.environ.get("SOURCE_GIT_PREFIX", "")
        return root, prefix.strip("/"), True
    return root, "brain", False


def _git_has(root: Path, git_path: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"HEAD:{git_path}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def _git_head_objects(root: Path) -> dict[str, tuple[str, str]]:
    """اقرأ شجرة HEAD مرة واحدة: {المسار: (النوع، object-id)}."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "-z", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    out: dict[str, tuple[str, str]] = {}
    for record in result.stdout.decode("utf-8").split("\0"):
        if not record or "\t" not in record:
            continue
        meta, path = record.split("\t", 1)
        mode, kind, oid = meta.split(" ", 2)
        out[path] = (kind, oid)
    return out


def _git_blob_oid(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _local_path_for(rel: str) -> Path | None:
    if rel.startswith("brain/"):
        return B / rel[len("brain/"):]
    if rel.startswith("site/"):
        return S / rel[len("site/"):]
    if rel.startswith("skills/"):
        root = Path(os.environ.get("SKILLS_DIR") or "/home/ubuntu/skills")
        return root / rel[len("skills/"):]
    return None


def _git_path_for(rel: str, prefix: str, explicit: bool) -> str | None:
    if explicit:
        if rel.startswith("brain/"):
            tail = rel[len("brain/"):]
            return f"{prefix}/{tail}".strip("/") if prefix else tail
        return None
    return rel


def committed_source_manifest(local: dict, scope: dict) -> tuple[dict, list[str]]:
    """أعد محتوى المصدر المطابق لـHEAD وافصل العمل المحلي غير الملتزم."""
    root, prefix, explicit = _source_git()
    try:
        head_objects = _git_head_objects(root)
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
        head_objects = {}
    committed = {}
    uncommitted = []
    for rel, value in sorted(local.items()):
        git_path = _git_path_for(rel, prefix, explicit)
        if not git_path or git_path not in head_objects:
            uncommitted.append(rel)
            continue
        kind, oid = head_objects[git_path]
        local_path = _local_path_for(rel)
        if value[0] != "file" or local_path is None or not local_path.is_file():
            committed[rel] = value
            continue
        if kind != "blob" or _git_blob_oid(local_path) != oid:
            uncommitted.append(rel)
            continue
        committed[rel] = value
    return committed, uncommitted


def _dirty_git_paths(root: Path) -> set[str]:
    """اقرأ status وls-files معًا لتثبيت أن الفروقات غير الملتزمة معلوماتية."""
    try:
        tracked = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout.decode("utf-8").split("\0")
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain=v1", "-z"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout.decode("utf-8").split("\0")
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
        return set()
    tracked_set = {item for item in tracked if item}
    dirty = set()
    for item in status:
        if not item:
            continue
        path = item[3:] if len(item) >= 3 else item
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path in tracked_set or item[:2] == "??":
            dirty.add(path)
    return dirty


def approved_skill_names() -> list[str]:
    """اقرأ نطاق المهارات من السجل الحاكم، وافشل مغلقًا عند فساد العقد."""
    path = B / "runbook" / "approved-skills.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    values = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError("runbook/approved-skills.json يجب أن يحوي قائمة skills غير فارغة")
    names = sorted({value.strip() for value in values})
    if not names:
        raise ValueError("runbook/approved-skills.json لا يجوز أن تكون قائمة skills فارغة")
    return names


def _inside_repo() -> bool:
    """يكتشف التشغيل من داخل نسخة من المستودع نفسه (استنساخ/Codespaces)."""
    repo = Path(__file__).resolve().parents[2]      # <repo>/brain/validators/<file>
    return (repo / "brain" / "validators").is_dir() and (repo / "site" / "generator").is_dir()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["strict", "advisory"], default="advisory")
    a = ap.parse_args()
    try:
        scope = load_scope()
        brain_skip_dirs, brain_skip_files = _root_policy(scope, "brain")
        site_skip_dirs, site_skip_files = _root_policy(scope, "site")
        junk_files = set(scope.get("junk_files", [".DS_Store", ".skill_versions.json"]))
    except ScopeError as exc:
        print(f"  ✘ فشل مغلق — سجل النطاق: {exc}")
        return 2
    if not REPO.exists():
        print(f"  ⚠ لا مستودع نسخ احتياطي في: {REPO} (يُتخطّى الفحص)")
        return 3
    local = manifest(B, brain_skip_dirs, brain_skip_files, "brain", junk_files)
    local.update(manifest(S, site_skip_dirs, site_skip_files, "site", junk_files))
    # عطل ك-60: المقارنة أغفلت جذر المهارات، فظهرت ملفات المستودع «زائدة» كذبًا.
    # القاعدة: كل جذر ينسخه github_backup يجب أن تدخله المقارنة بالنفس.
    sk_root = Path(os.environ["SKILLS_DIR"]) if os.environ.get("SKILLS_DIR") else (Path("/home/ubuntu/skills") if Path("/home/ubuntu/skills").is_dir() else B.parent / "skills")
    try:
        _sk_names = approved_skill_names()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"  ✘ فشل مغلق — تعذّر قراءة نطاق المهارات المعتمد: {type(exc).__name__}: {exc}")
        return 2
    print(f"  نطاق المهارات المعتمد من runbook/approved-skills.json: {len(_sk_names)}")
    for sk in _sk_names:
        d = sk_root / sk
        if not d.is_dir():
            local[f"skills/{sk}/ (مفقودة من المصدر)"] = ("missing-approved-skill", "")
            continue
        local.update(manifest(d, {"__pycache__", ".git"}, set(), f"skills/{sk}", junk_files))
    static = B / "backup-repo"
    if static.exists():
        for dp, dns, fns in os.walk(static):
            for fn in fns:
                p = Path(dp) / fn
                rel = (Path(dp).relative_to(static) / fn).as_posix()
                if rel in scope["repo"]["extra_allow"]:
                    continue
                local[rel] = ("file", sha(p))
    repo = repo_manifest(scope)
    # النطاق الحاكم متناظر على الطرفين: لا تُطلب المهارات العامة غير المعتمدة
    # ولا تُحوَّل ملفاتها المتتبعة في المرآة إلى «زوائد» مانعة.
    repo = {
        rel: value
        for rel, value in repo.items()
        if not rel.startswith("skills/") or len(rel.split("/")) < 2 or rel.split("/")[1] in _sk_names
    }
    repo = {
        rel: value
        for rel, value in repo.items()
        if not any(rel == p or rel.startswith(p) for p in scope["repo"]["only_prefixes"])
    }

    try:
        local_classes = classify_all(local, scope)
        repo_classes = classify_all(repo, scope)
        committed, uncommitted = committed_source_manifest(local, scope)
    except ScopeError as exc:
        print(f"  ✘ فشل مغلق — نطاق التماثل: {exc}")
        return 2
    dirty = _dirty_git_paths(_source_git()[0])
    print(f"  سجل النطاق: {len(scope['categories'])} فئات معلنة · كل مسار مصنّف")
    print(f"  الحالة الملتزمة: {len(committed)} · غير الملتزم: {len(uncommitted)} · Git dirty: {len(dirty)}")
    for rel in uncommitted[:20]:
        print(f"   ℹ غير ملتزم — لا يمنع: {rel}")
    if len(uncommitted) > 20:
        print(f"   … و{len(uncommitted) - 20} ملفات غير ملتزمة أخرى (معلوماتية)")

    drift = []
    for rel, (kind, _value) in sorted(local.items()):
        if kind == "missing-approved-skill":
            drift.append(f"مفقود من المصدر: {rel}")
    # فحص تسرّب الأسرار: أسماء ممنوعة و/أو قيم سرية داخل المدفوع
    import re as _re
    SECRET_NAMES = {".env", ".env.local", ".env.production", "webhook-secret.txt"}
    SECRET_PAT = [
        _re.compile(r"\b\d{9,10}:[A-Za-z0-9_\-]{30,}\b"),          # توكن بوت تلغرام
        _re.compile(r'"chat_id"\s*:\s*"?\d{6,}"?'),                  # معرّف محادثة غير محجوب
        _re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                         # AWS
        _re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),             # مفاتيح خاصة
        _re.compile(r"\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{20,}\b"), # مفاتيح دفع
    ]
    # حدّ الأصل المولَّد (ك-552): ذاكرة الترجمة/الكاش مشتقة من مصدر مفحوص أصلًا،
    # فمسحها ينتج منعًا كاذبًا بلا قيمة أمنية مضافة.
    GENERATED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    for dp, dns, fns in os.walk(REPO):
        if ".git" in Path(dp).parts:
            continue
        if any(part in GENERATED_DIRS for part in Path(dp).parts):
            dns[:] = []
            continue
        for fn in fns:
            rel_scan = (Path(dp).relative_to(REPO) / fn).as_posix()
            if rel_scan in scope["repo"]["protected"]:
                continue          # إعفاء مكتوب السبب: ملف الأسرار المعتمد بقرار المالك (ك-166/ك-168)
            if fn.endswith((".pyc", ".pyo")):
                continue          # أثر مولَّد (ك-552): لا يُفحص ولا يمنع
            if fn in SECRET_NAMES:
                drift.append(f"تسرّب سرّي: {Path(dp).relative_to(REPO) / fn}")
                continue
            q = Path(dp) / fn
            if q.is_symlink() or q.stat().st_size > 3_000_000:
                continue
            try:
                t = q.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "[محجوب]" in t:
                continue
            for rx in SECRET_PAT:
                if rx.search(t):
                    drift.append(f"تسرّب قيمة سرية: {Path(dp).relative_to(REPO) / fn} ({rx.pattern[:28]}…)")
                    break
    for rel, (kind, val) in sorted(committed.items()):
        category = local_classes[rel]
        if category["policy"] != "strict":
            continue
        if rel not in repo:
            drift.append(f"مفقود من المستودع: {rel}")
        elif repo[rel][0] != kind:
            drift.append(f"نوع مختلف (ملف/رابط): {rel}")
        elif repo[rel][1] != val:
            if rel in scope["repo"]["sanitized"]:
                continue                     # مُحجب عمدًا (تنقية أسرار)
            if rel in scope["repo"]["symlink_views"]:
                continue                     # روابط إلى شجرة الموقع: أهدافها تختلف بموضع النسخة (ك-331)
            drift.append(f"محتوى مختلف: {rel}")
    for rel in sorted(repo):
        category = repo_classes[rel]
        if category["policy"] != "strict":
            continue
        if rel not in local and rel not in committed:
            drift.append(f"زائد في المستودع: {rel}")

    print(f"  الشجرة المحلية: {len(local)} · المستودع: {len(repo)} · الروابط: "
          f"{sum(1 for v in local.values() if v[0] == 'link')} محليًا")
    if not drift:
        print("  النتيجة: مطابق — المستودع يعكس الشجرة المحلية كاملة")
        return 0
    for d in drift[:200]:
        print(f"   ✘ {d}")
    if len(drift) > 12:
        print(f"   … و{len(drift) - 12} أخرى")
    if a.mode == "strict":
        print(f"  النتيجة: انحراف مانع ({len(drift)}) — النسخة الاحتياطية غير محدَّثة")
        return 2
    print(f"  النتيجة: انحراف ({len(drift)}) — تنبيه (الوضع التنبيهي قبل خطوة النسخ)")
    return 1


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
