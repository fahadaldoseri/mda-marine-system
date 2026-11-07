#!/usr/bin/env python3
"""اختبار انحدار لحارس preflight مع استثناءات النسخ الحقيقية.

المطلوب: المسارات التي لا تدخل نطاق العملية (secrets/state وملفات env النموذجية)
لا تمنع العملية، بينما يبقى الاسم الحساس غير المستثنى مانعًا.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "../skills/destructive-op-guard-ops/scripts/preflight_guard.py"
GUARD = GUARD.resolve()


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def make_fixture(with_unexcluded_sensitive: bool) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    source = root / "source"
    source.mkdir()
    (source / "secrets").mkdir()
    (source / "secrets" / "secrets.env").write_text("placeholder\n", encoding="utf-8")
    (source / "state").mkdir()
    (source / "state" / "webhook-secret.txt").write_text("placeholder\n", encoding="utf-8")
    (source / ".env.example").write_text("TOKEN=replace-me\n", encoding="utf-8")
    if with_unexcluded_sensitive:
        (source / "config").mkdir()
        (source / "config" / "secret").write_text("placeholder\n", encoding="utf-8")

    bare = root / "origin.git"
    repo = root / "repo"
    assert run(["git", "init", "--bare", str(bare)], root).returncode == 0
    assert run(["git", "clone", str(bare), str(repo)], root).returncode == 0
    assert run(["git", "config", "user.name", "preflight-test"], repo).returncode == 0
    assert run(["git", "config", "user.email", "preflight-test@example.invalid"], repo).returncode == 0
    target = repo / "managed"
    target.mkdir()
    for path in source.rglob("*"):
        if path.is_file():
            rel = path.relative_to(source)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (target / "README.md").write_text("managed\n", encoding="utf-8")
    assert run(["git", "add", "managed"], repo).returncode == 0
    assert run(["git", "commit", "-m", "fixture"], repo).returncode == 0
    assert run(["git", "branch", "-M", "main"], repo).returncode == 0
    assert run(["git", "push", "-u", "origin", "main"], repo).returncode == 0
    assert run(["git", "status", "--porcelain"], repo).stdout == ""
    return tmp, source, target


def invoke(source: Path, target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(GUARD),
            "--source",
            str(source),
            "--target",
            str(target),
            "--exclude",
            "secrets",
            "--exclude",
            "state",
            "--exclude",
            ".env.example",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    failures = 0
    tmp, source, target = make_fixture(False)
    try:
        result = invoke(source, target)
        clean_ok = result.returncode == 0
        print(f"  {'✔' if clean_ok else '✘'} الاستثناءات المقصودة لا تمنع العملية (rc={result.returncode})")
        if not clean_ok:
            print(result.stdout)
        failures += not clean_ok
    finally:
        tmp.cleanup()

    tmp, source, target = make_fixture(True)
    try:
        result = invoke(source, target)
        blocked = result.returncode == 2 and "config/secret" in result.stdout
        print(f"  {'✔' if blocked else '✘'} الاسم الحساس غير المستثنى يبقى مانعًا (rc={result.returncode})")
        if not blocked:
            print(result.stdout)
        failures += not blocked
    finally:
        tmp.cleanup()

    print("  الحصيلة:", "كل اختبارات preflight نجحت ✔" if not failures else f"فشل {failures} اختبارًا ✘")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
