#!/usr/bin/env python3
"""ذاكرة نتائج فحوص G001 — لا يُعاد عند إعادة G001 إلا الفحص الذي تغيّرت مدخلاته (اعتماد فهد 20 نوفمبر 2026).

القياس قبل الإصلاح (20 نوفمبر 2026، main 5dc6b85): run_checks.sh يأخذ 123 ث في كل مرة، ويُعاد
مع كل إعادة آلية للخط بعد إصلاح (3 مرات في الاختبار الحي = 6 دقائق)، وإن لم يتغير ما يقرؤه الفحص.

القاعدة (فشل مغلق في كل شك):
- لا تعمل الذاكرة إلا إن مرّر المستدعي RUN_CHECKS_CACHE (يمرّره أمر G001 وحده)؛ التشغيل اليدوي
  وبوابة التسليم tools/final_gate.sh يبقيان كاملين بلا ذاكرة.
- تُخزَّن نتيجة الفحص الناجح وحده، وبشرط أن يكون أمره بايثون، وأن يكتمل تتبع كل عملياته
  (بداية ونهاية لكل عملية، وكل عملية بايثون فرعية مُتتبَّعة)، وألا يشغّل عملية غير بايثون ولا
  يتصل بالشبكة. غير ذلك يُعاد في كل مرة.
- مفتاح الفحص: اسمه وأمره ومتغيرات بيئته الحاكمة وتاريخ اليوم (UTC).
- تُعاد النتيجة المخزَّنة فقط إن طابقت بصمةُ كل ملف قرأه أو استعلم عنه وكل دليل سرده بصمتَه
  بعد آخر نجاح. أي اختلاف أو غياب أو تلف في الذاكرة = إعادة الفحص.

الأوامر:
  run_checks_cache.py lookup CACHE KEYFILE          رمز 0 = النتيجة المخزَّنة صالحة · 1 = يُعاد الفحص
  run_checks_cache.py record CACHE KEYFILE TRACE RC  يخزّن الناجح القابل للتتبع أو يحذف مدخله
"""
import fcntl
import glob
import hashlib
import json
import os
import sys

SKIP_PREFIXES = tuple(sorted({os.path.realpath(p) + os.sep for p in (sys.prefix, sys.base_prefix)}
                             | {"/proc/", "/sys/", "/dev/", "/usr/lib/", "/usr/local/lib/", "/etc/"}))


def _key(keyfile: str) -> str:
    with open(keyfile, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load(cache: str) -> dict:
    try:
        with open(cache, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(cache: str, d: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(cache)), exist_ok=True)
    tmp = f"{cache}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, cache)


class Fingerprints:
    """بصمات الملفات مع إعادة استعمال sha256 إن لم يتغير الحجم ووقت التعديل."""

    def __init__(self, memo: dict):
        self.memo = memo

    def file(self, path: str) -> str:
        try:
            st = os.stat(path)
        except FileNotFoundError:
            return "absent"
        except OSError as exc:
            return f"err:{type(exc).__name__}"
        if os.path.isdir(path):
            return "dir"
        old = self.memo.get(path)
        if old and old[0] == st.st_size and old[1] == st.st_mtime_ns:
            return old[2]
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
        except OSError as exc:
            return f"err:{type(exc).__name__}"
        sha = h.hexdigest()
        self.memo[path] = [st.st_size, st.st_mtime_ns, sha]
        return sha

    @staticmethod
    def listing(path: str) -> str:
        try:
            names = sorted(os.listdir(path))
        except OSError as exc:
            return f"err:{type(exc).__name__}"
        return hashlib.sha256("\0".join(names).encode("utf-8", "surrogateescape")).hexdigest()

    @staticmethod
    def globbed(spec: str) -> str:
        cwd, _, pattern = spec.partition("|")
        try:
            hits = sorted(glob.glob(pattern, root_dir=cwd or None, recursive=True))
        except (OSError, ValueError) as exc:
            return f"err:{type(exc).__name__}"
        return hashlib.sha256("\0".join(hits).encode("utf-8", "surrogateescape")).hexdigest()

    def of(self, kind: str, target: str) -> str:
        if kind == "l":
            return self.listing(target)
        if kind == "g":
            return self.globbed(target)
        return self.file(target)


def _parse_trace(trace: str, ignore: set[str]) -> tuple[dict | None, str]:
    """يعيد ({نوع: [أهداف]}, "") أو (None, سبب رفض التخزين)."""
    deps: dict[str, set[str]] = {"r": set(), "s": set(), "l": set(), "g": set()}
    began, ended, pychildren = set(), set(), 0
    try:
        with open(trace, encoding="utf-8", errors="surrogateescape") as f:
            lines = f.read().splitlines()
    except OSError:
        return None, "لا تتبع"
    for line in lines:
        kind, _, target = line.partition("\t")
        if kind == "x":
            return None, f"عملية أو اتصال خارج التتبع: {target}"
        if kind == "b":
            began.add(target)
        elif kind == "e":
            ended.add(target)
        elif kind == "p":
            pychildren += 1
        elif kind in deps:
            if kind != "g":
                real = os.path.realpath(target)
                if real.startswith(SKIP_PREFIXES) or real.endswith(".pyc") or real in ignore:
                    continue
                target = real
            deps[kind].add(target)
    if not began:
        return None, "الفحص لم يُشغَّل ببايثون مُتتبَّع"
    if began - ended:
        return None, "عملية انتهت بلا خروج طبيعي (تتبع ناقص)"
    if len(began) < 1 + pychildren:
        return None, "عملية بايثون فرعية لم تُتتبَّع"
    return {k: sorted(v) for k, v in deps.items()}, ""


def lookup(cache: str, keyfile: str) -> int:
    d = _load(cache)
    ent = (d.get("checks") or {}).get(_key(keyfile))
    if not isinstance(ent, dict) or not isinstance(ent.get("deps"), dict):
        return 1
    fp = Fingerprints(d.get("memo") or {})
    for kind, items in ent["deps"].items():
        if not isinstance(items, dict):
            return 1
        for target, want in items.items():
            if fp.of(kind, target) != want:
                return 1
    return 0


def record(cache: str, keyfile: str, trace: str, rc: str) -> int:
    os.makedirs(os.path.dirname(os.path.abspath(cache)), exist_ok=True)
    lock = open(cache + ".lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        d = _load(cache)
        checks = d.setdefault("checks", {})
        key = _key(keyfile)
        checks.pop(key, None)
        why = "رمز خروج غير صفري" if rc != "0" else ""
        deps = None
        if not why:
            deps, why = _parse_trace(trace, {os.path.realpath(p) for p in (trace, cache, cache + ".lock", keyfile)})
        if deps is not None:
            fp = Fingerprints(d.setdefault("memo", {}))
            checks[key] = {"deps": {k: {t: fp.of(k, t) for t in v} for k, v in deps.items()}}
        _save(cache, d)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    if why:
        print(f"      (لا تخزين: {why})")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "lookup":
        return lookup(argv[1], argv[2])
    if len(argv) >= 5 and argv[0] == "record":
        return record(argv[1], argv[2], argv[3], argv[4])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
