"""عقد سقف كلمات قسم «مستوى التهديد»: سقف المالك + كلفة كل قطاع زائد عن ثلاثة.

الخلفية المقيسة: سقف المالك 110 كلمات كُتب لأربعة أقسام بثلاثة قطاعات معلنة. عند إضافة
قطاع إلزامي (سطر إعلان مستواه + صفّه في الجدول ≈ 18 كلمة) يصبح السقف الثابت غير قابل
للتحقق بنيويًا، فيمنع كل إصدار بلا سبب. الحل: سقف مشتق من عدد القطاعات المعلنة في بطاقتها
الحاكمة (`web/zones/<date>.json`) لا رقم ثابت، مع بقاء السقف الأساسي 110.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "hygiene_under_test", ROOT / "validators" / "check_surface_hygiene.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cap_scales_with_declared_sectors(monkeypatch):
    module = _load()
    cases = {2: 110, 3: 110, 4: 128, 5: 146, 6: 164}
    for count, expected in cases.items():
        monkeypatch.setattr(module, "_zone_count", lambda _d, c=count: c)
        limit, seen = module._word_limit("2026-11-09")
        assert (limit, seen) == (expected, count), (count, limit, seen)


def test_unknown_sector_count_falls_back_to_base_cap(monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "_zone_count", lambda _d: None)
    limit, seen = module._word_limit("2026-11-09")
    assert limit == module.BASE_THREAT_WORD_LIMIT == 110
    assert seen is None


def _page(words: int, title: str) -> str:
    body = " ".join(["كلمة"] * words)
    return (
        "<html><body>"
        f"<h2>{title}</h2><p>{body}</p>"
        "<h2>قسم آخر</h2><p>نص</p>"
        "</body></html>"
    )


def _run_gate(module, monkeypatch, words: int, limit: int, tmp_path):
    report = tmp_path / "2026-11-09.html"
    additions = tmp_path / "additions.html"
    report.write_text(_page(words, module.THREAT_TITLE), encoding="utf-8")
    additions.write_text(
        f"<html><body><h2>{module.NEWS_TITLE}</h2><p>نص</p></body></html>", encoding="utf-8"
    )
    monkeypatch.setattr(module, "_resolve_report", lambda _v: report)
    monkeypatch.setattr(module, "_resolve_additions", lambda _v: additions)
    monkeypatch.setattr(module, "_word_limit", lambda _d: (limit, 5))
    return module.violations()


def test_over_cap_is_blocked(monkeypatch, tmp_path):
    module = _load()
    failures = _run_gate(module, monkeypatch, words=40, limit=20, tmp_path=tmp_path)
    assert any("يتجاوز السقف" in item for item in failures), failures


def test_within_cap_passes(monkeypatch, tmp_path):
    module = _load()
    failures = _run_gate(module, monkeypatch, words=12, limit=20, tmp_path=tmp_path)
    assert not any("يتجاوز السقف" in item for item in failures), failures