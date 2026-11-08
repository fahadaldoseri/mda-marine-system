"""اختبار انحدار: حدّ الأصل المولَّد في فحص تسرّب الأسرار (ك-552).

السلوك المطلوب: ذاكرة الترجمة/الكاش (__pycache__ · *.pyc · .pytest_cache) لا تُفحص
ولا تُنتج منعًا كاذبًا، مع بقاء الفحص صارمًا على المصدر والبيانات.
"""
import pathlib
import re
import subprocess
import sys

BRAIN = pathlib.Path(__file__).resolve().parents[1]
SCAN = BRAIN / "validators" / "check_backup_parity.py"
TOKEN_SHAPE = re.compile(r"\b\d{9,10}:[A-Za-z0-9_\-]{30,}\b")


def test_contract_declares_generated_boundary():
    src = SCAN.read_text(encoding="utf-8")
    assert 'GENERATED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}' in src
    assert 'if fn.endswith((".pyc", ".pyo")):' in src


def test_generated_cache_holding_token_shape_does_not_block():
    cache = BRAIN / "tests" / "__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    decoy = cache / "test_secrets_generated_boundary_probe.pyc"
    # القيم تُبنى وقت التشغيل: لا شكل سرّي حرفي في المصدر نفسه (ك-553)
    key = "chat" + "_" + "id"
    decoy.write_text(f'{key}="{1 * 10}" bot="{123456789}:{"AA" + "b" * 34}"\n', encoding="utf-8")
    try:
        env = {
            "PATH": "/usr/bin:/bin",
            "BRAIN_DIR": str(BRAIN),
            "SITE_DIR": str(pathlib.Path.home() / "seawatch"),
            "BACKUP_REPO_DIR": "/home/ubuntu/mda-marine-system",
        }
        r = subprocess.run([sys.executable, str(SCAN), "--mode", "strict"],
                           capture_output=True, text=True, env=env, cwd=str(BRAIN), timeout=600)
        assert "تسرّب قيمة سرية" not in r.stdout, r.stdout[-500:]
        assert r.returncode == 0, (r.returncode, r.stdout[-500:])
    finally:
        decoy.unlink(missing_ok=True)
