"""عقد الجذر القانوني لمولّد الموقع: قياس واحد، والأرشيف مرفوض (ك-571)."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "generator"
sys.path.insert(0, str(GEN))

import brain_root  # noqa: E402


def test_default_is_canonical_root():
    resolved = brain_root.brain_root()
    assert resolved.name == "brain"
    assert resolved.parent.name == "mda-marine-system"
    assert (resolved / "reports").is_dir()


def test_archive_is_never_returned():
    assert brain_root.ARCHIVE_NAME == "brain-marine-news"
    assert brain_root.ARCHIVE_NAME not in brain_root.brain_root().parts


def test_env_override_wins(tmp_path):
    env = dict(os.environ)
    env["BRAIN_DIR"] = str(tmp_path)
    code = (
        "import sys,pathlib;sys.path.insert(0,r'%s');"
        "import brain_root;print(brain_root.brain_root())" % GEN
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert out.returncode == 0, out.stderr
    assert pathlib.Path(out.stdout.strip()) == tmp_path.resolve()


def test_archive_env_is_rejected():
    env = dict(os.environ)
    env["BRAIN_DIR"] = str(pathlib.Path("/home/ubuntu") / brain_root.ARCHIVE_NAME)
    code = (
        "import sys,pathlib;sys.path.insert(0,r'%s');"
        "import brain_root;brain_root.brain_root()" % GEN
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert out.returncode != 0
    assert "الأرشيف المرفوض" in (out.stderr + out.stdout)
