#!/usr/bin/env python3
"""اختبار تخطي الخطوات المعطلة: لا يلمس المشروع الحقيقي ولا يشغّل الطباعة."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ENGINE = HERE / "tools" / "runbook.py"
REASON = "تعطيل بطلب المالك — يُفعّل بأمره الصريح"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="runbook-disabled-") as td:
        root = Path(td)
        (root / "tools").mkdir()
        (root / "runbook").mkdir()
        (root / "docs").mkdir()
        shutil.copy2(ENGINE, root / "tools" / "runbook.py")
        marker = root / "UNEXPECTED_COMMAND_EXECUTED"
        command = ["bash", "-lc", f"touch {marker}; exit 99"]
        manifest = {
            "version": 1,
            "ledger_dir": "logs/runbook",
            "print": {"enabled": False, "reason": REASON},
            "exempt": ["runbook/*", "docs/*", "tools/runbook.py"],
            "exempt_reasons": {
                "runbook/*": "ملفات المحرّك",
                "docs/*": "كتيب مولّد",
                "tools/runbook.py": "المحرّك نفسه",
            },
            "steps": [
                {
                    "id": "B020",
                    "title": "تصدير PDF المعتمد",
                    "kind": "script",
                    "phase": "build",
                    "disabled": True,
                    "reason": REASON,
                    "command": command,
                    "assert": [{"type": "cmd", "command": ["bash", "-lc", "false"]}],
                    "links": {"rules": ["الطباعة"], "files": ["tools/runbook.py"], "tests": []},
                    "on_fail": "stop",
                },
                {
                    "id": "B030",
                    "title": "بوابتا جودة الطباعة على PDF نفسه",
                    "kind": "script",
                    "phase": "build",
                    "disabled": True,
                    "reason": REASON,
                    "command": command,
                    "assert": [{"type": "cmd", "command": ["bash", "-lc", "false"]}],
                    "links": {"rules": ["الطباعة"], "files": ["tools/runbook.py"], "tests": []},
                    "on_fail": "stop",
                },
            ],
            "sections": [],
        }
        (root / "runbook" / "runbook.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        date = "2099-01-01"
        result = subprocess.run(
            [sys.executable, str(root / "tools" / "runbook.py"), "run", "--date", date, "--root", str(root)],
            capture_output=True,
            text=True,
            env={k: v for k, v in os.environ.items() if k not in {"BRAIN_DIR", "SITE_DIR"}},
        )
        output = result.stdout + result.stderr
        ledger = (root / "logs" / "runbook" / f"{date}.jsonl").read_text(encoding="utf-8")
        ok = (
            result.returncode == 0
            and "B020" in output
            and "B030" in output
            and "skipped/disabled" in output
            and output.count("لم يُنفَّذ الأمر") == 2
            and not marker.exists()
            and ledger.count('"status": "skipped"') == 2
        )
        print(output, end="")
        print(f"DISABLED_STEPS_EXIT={result.returncode}")
        print(f"COMMAND_MARKER_EXISTS={marker.exists()}")
        print(f"SKIPPED_LEDGER_ENTRIES={ledger.count(chr(34) + 'status' + chr(34) + ': ' + chr(34) + 'skipped' + chr(34))}")
        print(f"DISABLED_STEPS_TEST={'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
