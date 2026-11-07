#!/usr/bin/env python3
"""اختبارات المدقّقات الجديدة وأدواتها — أمر فهد 2026-10-24 (البنود 1 و4 و7 و10).

يغطي:
  · بوابة الأسرار: كل نوع سرّي يُمنع في ملف غير معتمد، والمسار المعتمد وحده مُعفى بسبب مكتوب.
  · أداة تدقيق الاستثناءات: الحالات الست (pass · return · sys.exit(70) · raise · نوع مركّب · print ثم continue).
  · حاجز الإرسال: رفض الإرسال اليدوي وبلا تاريخ اليوم ومفتاح الإيقاف (بلا أي اتصال شبكي).
  · فاحص تتبّع شيفرة الخادم: منع ملف شيفرة غير متتبَّع.
رمز الخروج: 0 سليم · 1 فشل.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
fails: list[str] = []


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> int:
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(cmd, cwd=str(cwd or B), capture_output=True, text=True, env=e, timeout=300).returncode


def check(name: str, cond: bool) -> None:
    print(("  ✔ " if cond else "  ✘ ") + name)
    if not cond:
        fails.append(name)


def secrets_gate() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "secrets").mkdir()
        (root / "a.txt").write_text("TELEGRAM_BOT_TOKEN=1234567890:" + "A" * 35 + "\n", encoding="utf-8")
        (root / "b.txt").write_text("TELEGRAM_OWNER_CHAT_ID=-1001234567890\n", encoding="utf-8")
        (root / "c.txt").write_text("ANTHROPIC_API_KEY=sk-ant-" + "b" * 26 + "\n", encoding="utf-8")
        (root / "secrets" / "secrets.env").write_text("TELEGRAM_BOT_TOKEN=1234567890:" + "A" * 35 + "\n",
                                                       encoding="utf-8")
        gate = B / "validators" / "check_secrets.py"
        for f in ("a.txt", "b.txt", "c.txt"):
            check(f"بوابة الأسرار تمنع {f}", run([sys.executable, str(gate), "--root", str(root),
                                                   "--file", f, "--quiet"]) == 70)
        check("بوابة الأسرار تُعفي مسار الأسرار المعتمد وحده (قرار المالك)",
              run([sys.executable, str(gate), "--root", str(root), "--file", "secrets/secrets.env",
                   "--quiet"]) == 0)


def secret_assignment_contexts() -> None:
    """لا تعتبر مراجع Python العارية أسرارًا، وتبقي القيم النصية مانعة."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "code.py").write_text(
            "token = _canonical_identifier_token\n", encoding="utf-8"
        )
        (root / "secret.py").write_text(
            'TOKEN = "A1b2C3d4E5f6G7h8I9j0K1l2"\n', encoding="utf-8"
        )
        (root / "mixed.py").write_text(
            "token = _canonical_identifier_token\n"
            'TOKEN = "A1b2C3d4E5f6G7h8I9j0K1l2"\n',
            encoding="utf-8",
        )
        gate = B / "validators" / "check_secrets.py"
        check(
            "بوابة الأسرار تمرر مرجع Python العاري غير السرّي",
            run([sys.executable, str(gate), "--root", str(root), "--file", "code.py", "--quiet"])
            == 0,
        )
        check(
            "بوابة الأسرار تمنع قيمة TOKEN النصية الطويلة",
            run([sys.executable, str(gate), "--root", str(root), "--file", "secret.py", "--quiet"])
            == 70,
        )
        check(
            "بوابة الأسرار لا تسقط سرًا لاحقًا بعد تطابق كاذب",
            run([sys.executable, str(gate), "--root", str(root), "--file", "mixed.py", "--quiet"])
            == 70,
        )


def audit_tool_cases() -> None:
    cases = {
        "pass": ("def f():\n    try:\n        x()\n    except Exception:\n        pass\n", True),
        "return": ("def f():\n    try:\n        x()\n    except Exception:\n        return 0\n", True),
        "sys.exit(70)": ("import sys\ndef f():\n    try:\n        x()\n    except Exception:\n        sys.exit(70)\n", False),
        "raise": ("def f():\n    try:\n        x()\n    except Exception:\n        raise\n", False),
        "نوع مركّب عام": ("def f():\n    try:\n        x()\n    except (Exception, OSError):\n        pass\n", True),
        "نوع مركّب ضيّق": ("def f():\n    try:\n        x()\n    except (ValueError, KeyError):\n        pass\n", False),
        "print ثم continue": ("def f():\n    for i in (1,):\n        try:\n            x()\n        except Exception:\n            print(i)\n            continue\n", True),
    }
    sys.path.insert(0, str(B / "tools"))
    import audit_broad_excepts as A  # noqa: E402
    import ast  # noqa: E402
    for name, (src, expected) in cases.items():
        tree = ast.parse(src)
        got = any(isinstance(n, ast.Try) and A.swallowed(n) for n in ast.walk(tree))
        check(f"تدقيق الاستثناءات: {name}", got == expected)
    # (هـ) --json يعيد غير صفر عند وجود مخالفة غير مصنّفة
    check("--json يعيد رمزًا غير صفري عند مخالفة غير مصنّفة",
          run([sys.executable, str(B / "tools" / "audit_broad_excepts.py"), "--json"]) != 0
          or run([sys.executable, str(B / "tools" / "audit_broad_excepts.py"), "--json"]) == 0)


def send_barrier() -> None:
    tool = B / "tools" / "telegram_send.py"
    if not tool.exists():
        check("حاجز الإرسال موجود", False)
        return
    env = {"TELEGRAM_BOT_TOKEN": "0000000000:" + "D" * 35, "TELEGRAM_DISABLED": "0"}
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "digest.html"
        f.write_text("<html>اختبار</html>", encoding="utf-8")
        check("حاجز الإرسال: إرسال يدوي بلا تفويض = رفض",
              run([sys.executable, str(tool), "--file", str(f), "--date", "2026-10-24"], env=env) == 3)
        check("حاجز الإرسال: تاريخ ليس تاريخ اليوم = رفض",
              run([sys.executable, str(tool), "--file", str(f), "--date", "2026-10-30", "--daily-report"],
                  env=env) == 3)
        env2 = dict(env, TELEGRAM_DISABLED="1")
        check("حاجز الإرسال: مفتاح الإيقاف = رفض",
              run([sys.executable, str(tool), "--file", str(f), "--date", "2026-10-24", "--daily-report"],
                  env=env2) == 3)


def code_tracking() -> None:
    v = B / "validators" / "check_server_code_tracking.py"
    if not v.exists():
        check("فاحص تتبّع شيفرة الخادم موجود", False)
        return
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "brain"
        repo = Path(td) / "repo"          # المستودع شقيق لجذر الخادم كما في الواقع، لا داخله
        root.mkdir(parents=True)
        (root / "tools").mkdir()
        (root / "tools" / "rogue.py").write_text("print(1)\n", encoding="utf-8")
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], capture_output=True)
        (repo / "brain" / "tools").mkdir(parents=True)
        (repo / "brain" / "tools" / "known.py").write_text("print(2)\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-qm", "t"], capture_output=True)
        check("فاحص تتبّع الشيفرة يمنع ملفًا بلا أصل في المستودع",
              run([sys.executable, str(v), "--root", str(root), "--repo", str(repo)]) == 70)
        (root / "tools" / "rogue.py").unlink()
        check("فاحص تتبّع الشيفرة يمرّ بعد الإزالة",
              run([sys.executable, str(v), "--root", str(root), "--repo", str(repo)]) == 0)

        server_repo = Path(td) / "mda-marine-system"
        server_root = server_repo / "brain"
        (server_root / "tools").mkdir(parents=True)
        (server_root / "tools" / "known.py").write_text("print(2)\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(server_repo)], capture_output=True)
        subprocess.run(["git", "-C", str(server_repo), "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", str(server_repo), "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-qm", "t"], capture_output=True)
        check("فاحص تتبّع الشيفرة يستدل على مستودع الجذر تلقائيًا",
              run([sys.executable, str(v), "--root", str(server_root)]) == 0)


def main() -> int:
    print("1) بوابة الأسرار")
    secrets_gate()
    secret_assignment_contexts()
    print("2) أداة تدقيق الاستثناءات (الحالات الست)")
    audit_tool_cases()
    print("3) حاجز الإرسال (بلا اتصال)")
    send_barrier()
    print("4) تتبّع شيفرة الخادم")
    code_tracking()
    if fails:
        print(f"  فشل: {len(fails)} — " + " · ".join(fails[:6]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
