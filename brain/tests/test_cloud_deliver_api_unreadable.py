"""wait_deploy: واجهة Cloudflare غير مقروءة (مفتاح Actions) لا تُعلَّق عشر دقائق بل تُحال إلى التحقق الحي."""
import importlib.util
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("cloud_deliver", Path(__file__).resolve().parents[1] / "tools" / "cloud_deliver.py")
cd = importlib.util.module_from_spec(SPEC)
sys.modules["cloud_deliver"] = cd
SPEC.loader.exec_module(cd)


def test_unreadable_api_returns_marker(monkeypatch):
    monkeypatch.setattr(cd, "cf_api", lambda *a, **k: {"success": False, "errors": [{"code": 10000}]})
    monkeypatch.setattr(cd.time, "sleep", lambda s: None)
    out = cd.wait_deploy("abcdef0123", 600)
    assert out["status"] == "api_unreadable"


def test_matching_success_still_wins(monkeypatch):
    row = {"id": "x", "deployment_trigger": {"metadata": {"commit_hash": "abcdef0123456"}},
           "latest_stage": {"name": "deploy", "status": "success"}}
    monkeypatch.setattr(cd, "cf_api", lambda *a, **k: {"success": True, "result": [row]})
    assert cd.wait_deploy("abcdef0123", 600)["status"] == "success"
