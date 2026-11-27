"""agent_write_llm: البرومت يضمّ صيغة الإخراج، ولا يُكتب إلا مسار معلن للخطوة."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import agent_write_llm as a  # noqa: E402


def test_prompt_and_allowed_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "ROOT", tmp_path)
    s = {"id": "W020", "writes": ["web/meta/{date}.json"]}
    txt = ("<<<FILE web/meta/2026-01-01.json>>>\n{\"ok\": 1}\n<<<END>>>\n"
           "<<<FILE ../evil.txt>>>\nx\n<<<END>>>")
    assert a.write_outputs(s, "2026-01-01", txt) == ["web/meta/2026-01-01.json"]
    assert (tmp_path / "web/meta/2026-01-01.json").read_text() == '{"ok": 1}\n'
    assert not (tmp_path.parent / "evil.txt").exists()


def test_real_prompt_renders():
    m = a.runbook.load(str(a.ROOT))
    s = next(x for x in m["steps"] if x["id"] == "W020")
    p = a.build_prompt(s, "2026-11-22", problems="سبب")
    assert "<<<FILE" in p and "web/meta/2026-11-22.json" in p and "سبب" in p
