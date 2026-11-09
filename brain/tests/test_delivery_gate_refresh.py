#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار لعقد تجديد البوابة المتقادمة عند حدّ خطوة التسليم (ك-591).

العطل الذي يمنعه هذا الاختبار: بوابة أُعيد تشغيلها قبل خطوة نشر (D016) تبقى مسجّلة
بوقت أقدم من تلك الخطوة، فيُرفض إرسال تلغرام (D030) بحكم «سجل قديم» بلا مانع حقيقي.
الإصلاح: التجديد يُقاس عند خطوة التسليم نفسها، ويُعاد تشغيل البوابة المتقادمة بقياس
حقيقي عبر المحرّك، ويبقى المانع الحقيقي مانعًا.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "refresh_stale_gates.py"
PUBLISH = ROOT / "tools" / "publish_site.sh"


def _load():
    spec = importlib.util.spec_from_file_location("refresh_stale_gates", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_delivery_step_is_passed_to_verdict(tmp_path, monkeypatch):
    """موجب: الأداة تمرّر خطوة التسليم المطلوبة إلى حكم البوابات لا خطوة ثابتة."""
    mod = _load()
    seen: dict[str, str] = {}
    out = tmp_path / "verdict.json"

    class Done:
        returncode = 0

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        seen["cmd"] = " ".join(str(c) for c in cmd)
        out.write_text(json.dumps({"verdicts": {}}), encoding="utf-8")
        return Done()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    rc, _doc = mod.verdict("2026-11-09", tmp_path, out, "D030")
    assert rc == 0
    assert "--delivery-step D030" in seen["cmd"], seen["cmd"]
    assert "--delivery-step D010" not in seen["cmd"], seen["cmd"]


def test_circular_gate_is_not_refreshed(tmp_path, monkeypatch):
    """سالب: بوابة يستدعي أمرها أداة التجديد لا تُجدَّد داخلها (منع الحلقة ك-568)."""
    mod = _load()
    (tmp_path / "runbook").mkdir(parents=True)
    (tmp_path / "logs").mkdir(parents=True)
    (tmp_path / "tools").mkdir(parents=True)
    (tmp_path / "runbook" / "runbook.json").write_text(
        json.dumps({"steps": [
            {"id": "D010", "command": ["bash", "-lc", "python3 tools/refresh_stale_gates.py --date {date}"]},
            {"id": "G011", "command": ["bash", "-lc", "true"]},
        ]}, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "logs" / "gate-verdict-2026-11-09.json"

    class Blocked:
        returncode = 2

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        out.write_text(json.dumps({"verdicts": {
            "G011": {"why": ["سجل G011 قديم بعد تشغيل D016 — أعد تشغيله عبر --redo G011"]},
            "D010": {"why": ["سجل D010 قديم — أعد تشغيله عبر --redo D010"]},
        }}, ensure_ascii=False), encoding="utf-8")
        return Blocked()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("GATE_REFRESH_DEPTH", "0")
    assert mod.main.__name__ == "main"
    argv = sys.argv
    try:
        sys.argv = ["refresh_stale_gates.py", "--date", "2026-11-09", "--root", str(tmp_path)]
        assert mod.main() == 2
    finally:
        sys.argv = argv


def test_publish_site_refreshes_before_verdict():
    """عقد السكربت: التجديد يُنفَّذ قبل حكم البوابات، وبحدّ خطوة التسليم نفسها."""
    text = PUBLISH.read_text(encoding="utf-8")
    i_refresh = text.index("refresh_stale_gates.py")
    i_verdict = text.index("gate_verdict.py")
    assert i_refresh < i_verdict, "التجديد يجب أن يسبق حكم البوابات"
    assert '--delivery-step "$DELIVERY_STEP"' in text[i_refresh:i_refresh + 220]