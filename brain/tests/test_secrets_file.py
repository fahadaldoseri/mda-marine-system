#!/usr/bin/env python3
"""telegram_send يقرأ الرمز من secrets/secrets.env عند غيابه من البيئة، وقالب الأسرار بلا قيم، وسجل code-paths يصنّفها.
الاستعمال: python3 tests/test_secrets_file.py"""
import importlib.util, os, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
T = Path(tempfile.mkdtemp())
(T / "secrets").mkdir()
(T / "secrets" / "secrets.env").write_text("# تعليق\nTELEGRAM_BOT_TOKEN='tok-123'\n", encoding="utf-8")
os.environ["BRAIN_DIR"] = str(T)
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
spec = importlib.util.spec_from_file_location("ts", HERE / "tools" / "telegram_send.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = 0
def ok(c, n):
    global f
    print(("  ✔ " if c else "  ✘ ") + n); f += not c
ok(m._token_from_env_file() == "tok-123", "الرمز يُقرأ من secrets/secrets.env")
ex = (HERE / "secrets" / "secrets.env.example").read_text(encoding="utf-8")
ok(all(l.split("=", 1)[1].strip() == "" for l in ex.splitlines() if "=" in l and not l.startswith("#")), "القالب بلا قيم")
sys.path.insert(0, str(HERE / "tools")); import code_paths
spec2 = code_paths.load_spec(HERE)  # جذر الدماغ: يكتشف المواصفات في التخطيطين
ok(code_paths.classify("brain/secrets/secrets.env", spec2) == "data" and code_paths.classify("brain/secrets/README.md", spec2) == "code", "التصنيف: القيم data والتوثيق code")
sys.exit(1 if f else 0)
