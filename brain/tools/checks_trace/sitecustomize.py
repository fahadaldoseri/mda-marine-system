"""متتبّع مدخلات فحوص G001 — يُحمَّل فقط حين يمرّره tests/run_checks.sh في PYTHONPATH مع CHECKS_TRACE.

الغرض (اعتماد فهد 20 نوفمبر 2026، المقترح 1): عند إعادة G001 بعد عطل لا يُعاد إلا الفحص الذي تغيّرت
مدخلاته. يسجّل هذا الملف كل ملف يقرؤه الفحص أو يستعلم عن وجوده، وكل دليل يسرده، وكل ما يمنع الوثوق
بالتتبع (عملية فرعية غير بايثون، اتصال شبكي، بايثون معزول -I/-E يتجاوز هذا المتتبّع). الحكم في
tools/run_checks_cache.py؛ هنا تسجيل فقط بلا أي أثر على سلوك الفحص.
"""
import os as _os
import sys as _sys

_TRACE = _os.environ.get("CHECKS_TRACE", "")
_HERE = _os.path.dirname(_os.path.abspath(__file__))


def _chain_original():
    """يحمّل sitecustomize الأصلي للبيئة (إن وُجد) حتى لا يتغير سلوك بايثون بوجود المتتبّع."""
    import importlib.util
    for d in _sys.path:
        if not d or _os.path.abspath(d) == _HERE:
            continue
        cand = _os.path.join(d, "sitecustomize.py")
        if _os.path.isfile(cand):
            spec = importlib.util.spec_from_file_location("_seawatch_orig_sitecustomize", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return


_chain_original()

if _TRACE:
    _seen = set()
    _buf = []
    _PY = ("python", "python3")

    def _emit(kind, path):
        try:
            p = _os.fsdecode(path) if not isinstance(path, int) else ""
        except (TypeError, ValueError):
            return
        if kind in ("r", "s", "l") and not p:
            return
        if kind in ("r", "s", "l") and not _os.path.isabs(p):
            p = _os.path.abspath(p)
        k = (kind, p)
        if k in _seen:
            return
        _seen.add(k)
        _buf.append(f"{kind}\t{p}\n")
        if len(_buf) >= 256:
            _flush()

    def _flush():
        if not _buf:
            return
        data = "".join(_buf)
        _buf.clear()
        fd = _os.open(_TRACE, _os.O_WRONLY | _os.O_APPEND | _os.O_CREAT, 0o600)
        try:
            _os.write(fd, data.encode("utf-8", "surrogateescape"))
        finally:
            _os.close(fd)

    def _is_python(exe, argv):
        name = _os.path.basename(_os.fsdecode(exe or (argv[0] if argv else "")))
        if not name.startswith(_PY):
            return False
        flags = [a for a in argv[1:] if isinstance(a, str) and a.startswith("-") and not a.startswith("--")]
        return not any(set(f[1:]) & set("IESs") for f in flags if f[1:2] != "c" and f[1:2] != "m")

    def _hook(event, args):
        if event == "open":
            path, mode = args[0], args[1]
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            if isinstance(mode, str) and any(c in mode for c in "wax"):
                return
            if flags & (_os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC) and not flags & _os.O_RDWR:
                return
            _emit("r", path)
        elif event in ("os.listdir", "os.scandir", "glob.glob"):
            target = args[0] if args else "."
            if event == "glob.glob":
                _emit("g", f"{args[1] if len(args) > 1 and args[1] else _os.getcwd()}|{target}")
            else:
                _emit("l", target if target not in (None, b"") else ".")
        elif event == "subprocess.Popen":
            exe, argv, env = args[0], args[1], args[3] if len(args) > 3 else None
            if isinstance(argv, (str, bytes)):
                _emit("x", f"popen-shell {argv[:60]!r}")
            elif not _is_python(exe, list(argv or [])):
                _emit("x", f"popen {exe or list(argv or [])[:1]}")
            elif env is not None and env.get("CHECKS_TRACE") != _TRACE:
                _emit("x", "popen python بلا CHECKS_TRACE")
            else:
                _emit("p", f"{len(_seen)}")
        elif event in ("os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty"):
            _emit("x", event)
        elif event in ("socket.connect", "socket.getaddrinfo", "urllib.Request"):
            _emit("x", event)

    def _wrap(fn):
        def inner(path, *a, **k):
            if not isinstance(path, int):
                _emit("s", path)
            return fn(path, *a, **k)
        return inner

    _os.stat = _wrap(_os.stat)
    _os.lstat = _wrap(_os.lstat)
    _sys.addaudithook(_hook)
    # بداية العملية تُكتب فورًا؛ ونهايتها عند الخروج الطبيعي. عملية بلا نهاية (os._exit أو قتل)
    # تعني تتبعًا ناقصًا، فلا تُخزَّن نتيجة الفحص.
    _emit("b", str(_os.getpid()))
    _flush()
    import atexit as _atexit

    def _end():
        _emit("e", str(_os.getpid()))
        _flush()
    _atexit.register(_end)
