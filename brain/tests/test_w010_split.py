"""W010 على خمس مجموعات: التغطية، تجميع بلا فقد، استئناف الجزء الصالح، إعادة الفاشل وحده."""
import re
import shutil
import sys
from pathlib import Path

import pytest

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B / "tools"))
import agent_write_llm as a  # noqa: E402
import w010_split as w  # noqa: E402

M = a.runbook.load(str(B))
DATES = ["2026-11-20", "2026-11-21", "2026-11-22", "2026-11-26"]


def group_of(order):
    by_order = {s["order"]: s["id"] for s in w.written_sections(M)}
    return next(g for g, c in w.GROUPS.items() if by_order[order] in c["sections"])


def split_report(text):
    parts = {g: "" for g in w.GROUPS}
    secs = w.written_sections(M)
    cur = None
    for h, blk in w.parse_blocks(text):
        o = w.section_order(h, secs)
        if o is not None:
            cur = group_of(o)
        parts[cur] += blk + "\n\n"
    return parts


def test_groups_cover_manifest_exactly():
    assert w.supported(M)
    assert sorted(i for g in w.GROUPS.values() for i in g["sections"]) == sorted(s["id"] for s in w.written_sections(M))


@pytest.mark.parametrize("d", DATES)
def test_assemble_roundtrip_identical(d):
    orig = (B / "reports" / f"{d}-sectioned.md").read_text(encoding="utf-8")
    assert w.assemble(d, split_report(orig), M) == orig.rstrip("\n") + "\n"


def test_unsupported_manifest_falls_back():
    m = {"sections": M["sections"] + [{"id": "new", "order": 99, "heading": "جديد", "title": "جديد"}]}
    assert not w.supported(m)


def test_examples_and_sections_subset():
    ex = (B / "sections" / "20-examples.md").read_text(encoding="utf-8")
    sub = w.examples_subset(ex, [1, 4])
    assert re.findall(r"(?m)^## (\d+)\)", sub) == ["1", "4"]
    rend = a.runbook.render_sections(str(B), "2026-11-26")
    s = w.sections_subset(rend, {2, 6, 7})
    assert re.findall(r"(?m)^### (\d+)\.", s) == ["2", "6", "7"]


def test_template_blocks_exist_and_are_routed():
    src = (B / "runbook" / "prompts" / "write-report.md").read_text(encoding="utf-8")
    titles = [w.block_title(b) for b in w.split_blocks(src)]
    for p in list(w.DROP_BLOCKS) + list(w.ONLY_BLOCKS):  # إن تغيّر عنوان كتلة يفشل الاختبار بدل أن تتسرب
        assert any(t.startswith(p) for t in titles), p
    kept = lambda g: [t for b in w.split_blocks(src) if w.keep_block(b, g) for t in [w.block_title(b)]]  # noqa: E731
    assert any(t.startswith("قسم «مستوى التهديد»") for t in kept("A"))
    assert not any(t.startswith("قسم «مستوى التهديد»") for t in kept("B"))
    assert not any(t.startswith("شروط الإتمام") for t in kept("A"))


def test_lexicon_filter_keeps_header_and_drops_unrelated():
    lex = (B / "sections" / "20-lexicon.md").read_text(encoding="utf-8")
    out = w.filter_lexicon(lex, "النافذة")
    assert "| المعنى | اكتب | لا تكتب |" in out and "## ب)" in out and "## د)" in out
    assert "| النافذة | فترة التقرير | النافذة |" in out
    assert len(out) < len(lex) * 0.6


def test_group_prompts_small_and_scoped():
    s = next(x for x in M["steps"] if x["id"] == "W010")
    pa = a.build_group_prompt(s, "2026-11-26", "A")
    pb = a.build_group_prompt(s, "2026-11-26", "B")
    assert "قسم «مستوى التهديد»" in pa and "قسم «مستوى التهديد»" not in pb
    assert "### 8." in pb and "### 8." not in pa
    assert f"logs/runbook/2026-11-26/W010-parts/B.md" in pb
    assert "## الملف: feeds/feeds-2026-11-26.md" in pb and "## الملف: feeds/" not in pa


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    for d in ("runbook", "sections", "tools"):
        shutil.copytree(B / d, tmp_path / d, ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "feeds").mkdir()
    shutil.copy(B / "feeds" / "feeds-2026-11-26.md", tmp_path / "feeds")
    (tmp_path / "appendices").mkdir()
    shutil.copy(B / "appendices" / "estimate-code-map.json", tmp_path / "appendices")
    monkeypatch.setattr(a, "ROOT", tmp_path)
    monkeypatch.setenv("LLM_GAP_SECONDS", "0")
    return tmp_path


def _fake(calls, orig_parts, break_once=None):
    seen = set()

    def chat(prompt):
        g = re.search(r"W010-parts/(\w)\.md>>>", prompt).group(1)
        calls.append(g)
        txt = orig_parts[g]
        if break_once == g and g not in seen:
            seen.add(g)
            txt = txt.split("\n\n")[0]  # قسم واحد فقط: ناقص
        return f"<<<FILE logs/runbook/2026-11-26/W010-parts/{g}.md>>>\n{txt.strip()}\n<<<END>>>"
    return chat


def test_resume_and_retry_failed_group_alone(sandbox, monkeypatch):
    d = "2026-11-26"
    orig = (B / "reports" / f"{d}-sectioned.md").read_text(encoding="utf-8")
    parts = split_report(orig)
    s = next(x for x in M["steps"] if x["id"] == "W010")
    calls = []
    monkeypatch.setattr(a, "chat", _fake(calls, parts, break_once="C"))
    assert a.write_w010(s, d) == [f"reports/{d}-sectioned.md"]
    assert calls.count("C") == 2 and all(calls.count(g) == 1 for g in "ABDE")  # C أُعيد وحده
    assert (sandbox / "reports" / f"{d}-sectioned.md").read_text(encoding="utf-8") == orig.rstrip("\n") + "\n"
    calls.clear()  # استئناف: كل الأجزاء محفوظة صالحة
    assert a.write_w010(s, d)
    assert calls == []
    calls.clear()  # رفض محرّك ينسب إلى قسم المراقبة (المجموعة D) فيُعاد D وحده
    assert a.write_w010(s, d, "G999: قسم «المراقبة المستمرة» مخالف")
    assert calls == ["D"]


def test_failed_group_returns_empty_and_keeps_good_parts(sandbox, monkeypatch):
    d = "2026-11-26"
    parts = split_report((B / "reports" / f"{d}-sectioned.md").read_text(encoding="utf-8"))
    s = next(x for x in M["steps"] if x["id"] == "W010")
    monkeypatch.setattr(a, "chat", lambda p: "رد بلا علامات" if "W010-parts/E.md>>>" in p else _fake([], parts)(p))
    assert a.write_w010(s, d) == []
    assert (a.parts_dir(d) / "B.md").is_file() and not (a.parts_dir(d) / "E.md").is_file()
    assert not (sandbox / "reports" / f"{d}-sectioned.md").exists()
