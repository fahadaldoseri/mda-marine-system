"""اختبار انحدار: جذر brain يُشتق بالقياس لا بالاسم، ويفشل مغلقًا.

يمنع تكرار العطل ك-554: أدوات حيّة كانت تكتب في شجرة قديمة باسم
`brain-marine-news` بمجرد وجودها في سلسلة الآباء.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN / 'tools'))

from brain_root import canonical_brain_root, is_brain  # noqa: E402


def _make_brain(root: Path) -> Path:
    (root / 'runbook').mkdir(parents=True, exist_ok=True)
    (root / 'runbook' / 'runbook.json').write_text('{"steps": []}\n', encoding='utf-8')
    return root


def test_decoy_sibling_named_brain_marine_news_is_ignored(tmp_path: Path) -> None:
    """شجرة قديمة بالاسم القديم لا تخطف الجذر القانوني."""
    decoy = tmp_path / 'brain-marine-news'
    (decoy / 'reports').mkdir(parents=True)
    (decoy / 'reports' / 'old.html').write_text('قديم', encoding='utf-8')

    canonical = _make_brain(tmp_path / 'mda-marine-system' / 'brain')
    (canonical / 'tools').mkdir()

    assert canonical_brain_root(canonical / 'tools') == canonical


def test_is_brain_requires_manifest(tmp_path: Path) -> None:
    (tmp_path / 'runbook').mkdir()
    assert is_brain(tmp_path) is False
    _make_brain(tmp_path)
    assert is_brain(tmp_path) is True


def test_missing_manifest_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('BRAIN_DIR', raising=False)
    (tmp_path / 'a' / 'b').mkdir(parents=True)
    with pytest.raises(SystemExit):
        canonical_brain_root(tmp_path / 'a' / 'b')


def test_env_without_manifest_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('BRAIN_DIR', str(tmp_path / 'not-brain'))
    (tmp_path / 'not-brain').mkdir()
    with pytest.raises(SystemExit):
        canonical_brain_root(tmp_path)


def test_closure_round_resolves_repository_brain() -> None:
    """أداة الإغلاق ترى الجذر القانوني للمستودع لا الشجرة القديمة."""
    spec = importlib.util.spec_from_file_location('closure_round_mod', BRAIN / 'tools' / 'closure_round.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.B == BRAIN
    assert is_brain(mod.B)
    assert 'brain-marine-news' not in str(mod.B)