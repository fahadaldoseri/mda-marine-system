from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_gate_coverage():
    spec = importlib.util.spec_from_file_location("gate_coverage_under_test", ROOT / "tools" / "gate_coverage.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skill_gate_audit_reference_keeps_full_declared_path(tmp_path: Path) -> None:
    module = load_gate_coverage()
    rel = "skills/gate-lifecycle-ops/references/legacy/gate-strictness-hardening-ops/scripts/gate_audit.py"
    root = tmp_path / "brain"
    (root / "runbook").mkdir(parents=True)
    (root / rel).parent.mkdir(parents=True)
    (root / rel).write_text("# governed audit asset\n", encoding="utf-8")
    manifest = {
        "steps": [{
            "id": "G066",
            "command": ["python3", rel],
            "links": {"gates": [rel]},
        }]
    }
    (root / "runbook" / "runbook.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    refs = module.PATH_RE.findall(json.dumps(manifest))
    assert rel in refs
    assert "scripts/gate_audit.py" not in refs
    dead, *_ = module.collect(root, manifest["steps"])
    assert dead == []
