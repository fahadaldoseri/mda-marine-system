"""حكم النشر الموحّد (tools/publish_verdict.py) — اختبار موجب وسالب.

العطل المقيس (2026-11-19): أمر النشر طلب «رمز final_gate 0 أو 3»، والبوابة لا تُخرج إلا
0 أو 1 أو 2، فاجتهد المشغّل في تفسير الرمز 1. والتقرير المودَع خالف بصمة النص التي
سجّلتها البوابة. الأداة تقرأ ما كتبته البوابة والعلامة فقط وتترجمه إلى سلّم المالك.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = "2026-11-09"


def load():
    spec = importlib.util.spec_from_file_location("publish_verdict_t", ROOT / "tools" / "publish_verdict.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def tree(tmp: pathlib.Path, *, gate_rc=0, overall="ok", steps=None, stage="final", text="نص", stamp_text=None):
    (tmp / "reports").mkdir(parents=True, exist_ok=True)
    gd = tmp / "logs" / f"gate-{D}"
    gd.mkdir(parents=True, exist_ok=True)
    (tmp / "reports" / f"{D}-sectioned.md").write_text(text, encoding="utf-8")
    sha = hashlib.sha256((stamp_text if stamp_text is not None else text).encode("utf-8")).hexdigest()
    (gd / f".text-hash-{D}.json").write_text(json.dumps({"date": D, "sha256": sha}), encoding="utf-8")
    (gd / "gate.json").write_text(json.dumps({
        "date": D, "status": {0: "ok", 1: "warn", 2: "block"}[gate_rc], "exit_code": gate_rc,
        "stage": stage, "steps": steps or [{"step": "x", "status": "ok"}]}), encoding="utf-8")
    (tmp / "logs" / f"pipeline-{D}.json").write_text(json.dumps({
        "date": D, "overall": overall, "final_gate": {"exit_code": gate_rc}}), encoding="utf-8")


def test_sound_run_is_zero(tmp_path):
    tree(tmp_path)
    r = load().verdict(tmp_path, D)
    assert r["verdict"] == 0 and r["publish_allowed"], r


def test_warning_with_degraded_mark_is_three(tmp_path):
    tree(tmp_path, gate_rc=1, overall="degraded", steps=[{"step": "y", "status": "warn"}])
    r = load().verdict(tmp_path, D)
    assert r["verdict"] == 3 and r["publish_allowed"], r


def test_block_or_crash_is_two(tmp_path):
    tree(tmp_path, gate_rc=2, steps=[{"step": "z", "status": "block"}])
    assert load().verdict(tmp_path, D)["verdict"] == 2
    tree(tmp_path, gate_rc=1, steps=[{"step": "z", "status": "crash"}])
    assert load().verdict(tmp_path, D)["verdict"] == 2


def test_text_changed_after_gate_is_two(tmp_path):
    tree(tmp_path, text="نص بعد البوابة", stamp_text="نص البوابة")
    r = load().verdict(tmp_path, D)
    assert r["verdict"] == 2 and not r["publish_allowed"]


def test_provisional_gate_or_failed_mark_is_two(tmp_path):
    tree(tmp_path, stage="provisional")
    assert load().verdict(tmp_path, D)["verdict"] == 2
    tree(tmp_path, overall="failed")
    assert load().verdict(tmp_path, D)["verdict"] == 2


def test_missing_gate_is_two(tmp_path):
    (tmp_path / "logs").mkdir()
    assert load().verdict(tmp_path, D)["verdict"] == 2
