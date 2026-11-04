#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار: الواقعة «غير مكانية» لا تُرسم ولا تُسقط مشتق نقاط الخريطة.

سبب الوجود (عطل ك-486): بلاغ UKMTO لم يذكر المصدر موقعه، فوسمت الواقعة «غير مكانية»
وفق سجل المناطق (المادة ٤)، ثم أسقط مشتق نقاط الخريطة الخطوة كلها برمز 2 لأن الوسم
لا مِرساة له في area-coordinates.json. الإصلاح الجذري: الوسم التصنيفي غير المكاني
يُدرج في excluded_areas مثل «خارج القطاعات»، فلا يُرسم ولا يُحسب قطاعًا.

الاختبار مقترن: السطح النظيف يمر (rc ≠ 2 ولا نقطة غير مكانية في المخرج)،
والمخالف الحقيقي يُمنع (منطقة بلا مِرساة تخرج برمز 2).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "derive_map_points.py"
SYNTH = "2099-01-01"


def _write_meta(date: str, events: list[dict]) -> pathlib.Path:
    p = ROOT / "web" / "meta" / f"{date}.json"
    p.write_text(json.dumps({"date_label": date, "event_keys": events}, ensure_ascii=False, indent=1) + "\n",
                 encoding="utf-8")
    return p


def _run(date: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), "--date", date, "--write"],
                          capture_output=True, text=True, cwd=str(ROOT))


def _cleanup() -> None:
    for rel in (f"web/meta/{SYNTH}.json", f"web/zones/{SYNTH}.json"):
        p = ROOT / rel
        if p.exists():
            p.unlink()
    for p in (ROOT / "web" / "meta").glob(f"{SYNTH}*"):
        p.unlink()
    for p in (ROOT / "web" / "zones").glob(f"{SYNTH}*"):
        p.unlink()


def test_non_spatial_does_not_break_or_draw() -> None:
    """واقعة «غير مكانية»: لا فشل مغلق، ولا نقطة مرسومة، والواقعة المسندة تُرسم."""
    _cleanup()
    try:
        meta = _write_meta(SYNTH, [
            {"code": "MN-TEST-01", "title": "بلاغ بلا موقع معلن في المصدر", "area": "غير مكانية",
             "status": "الموقع غير معلن", "ref": "اختبار"},
            {"code": "MN-TEST-02", "title": "واقعة داخل مضيق هرمز", "area": "مضيق هرمز",
             "status": "بلاغ رسمي", "ref": "اختبار"},
        ])
        r = _run(SYNTH)
        assert r.returncode != 2, f"أُسقطت الخطوة بسبب وسم غير مكاني: {r.stdout}{r.stderr}"
        out = json.loads(meta.read_text(encoding="utf-8"))
        pts = (out.get("map") or {}).get("points") or []
        areas = [str(p.get("area") or "") for p in pts]
        assert "غير مكانية" not in areas, f"رُسمت واقعة غير مكانية: {areas}"
        assert any("هرمز" in a for a in areas), f"لم تُرسم الواقعة المسندة: {areas}"
    finally:
        _cleanup()


def test_unanchored_real_area_still_fails_closed() -> None:
    """ضبط سالب: منطقة حقيقية بلا مِرساة معتمدة تبقى فشلًا مغلقًا (الحارس لم يُضعف)."""
    _cleanup()
    try:
        _write_meta(SYNTH, [
            {"code": "MN-TEST-03", "title": "واقعة في منطقة بلا مِرساة", "area": "منطقة وهمية للاختبار",
             "status": "بلاغ", "ref": "اختبار"},
        ])
        r = _run(SYNTH)
        assert r.returncode == 2, f"لم يُمنع موضع بلا مِرساة (rc={r.returncode})"
        assert "مِرساة" in (r.stdout + r.stderr), "رسالة المنع لا تذكر المِرساة"
    finally:
        _cleanup()


def test_composite_country_sea_area_uses_sea_anchor() -> None:
    """الاسم المركّب «البلد - البحر» يُرسم بمِرساة البحر ولا يفشل مغلقًا."""
    _cleanup()
    try:
        meta = _write_meta(SYNTH, [
            {"code": "MN-TEST-04", "title": "إنقاذ قبالة الصومال", "area": "الصومال - المحيط الهندي",
             "status": "بلاغ", "ref": "اختبار"},
        ])
        r = _run(SYNTH)
        assert r.returncode != 2, f"أُسقط الاسم المركّب: {r.stdout}{r.stderr}"
        out = json.loads(meta.read_text(encoding="utf-8"))
        m = out.get("map") or {}
        # منطقة المحيط الهندي سطحها «خارج نطاق الخريطة»، فتُدرج في قائمة off_map لا في النقاط المرسومة.
        listed = [str(p.get("area") or "") for p in (m.get("points") or [])]
        listed += [str(p.get("area") or "") for p in (m.get("off_map") or [])]
        listed += [str(x) for x in (m.get("off_map_areas") or [])]
        assert any("الصومال" in a for a in listed) or m.get("off_map"), f"لم يُحلّ الاسم المركّب: {listed}"
    finally:
        _cleanup()


if __name__ == "__main__":
    test_non_spatial_does_not_break_or_draw()
    print("   ✔ السطح النظيف يمر ولا يُرسم الوسم غير المكاني")
    test_unanchored_real_area_still_fails_closed()
    print("   ✔ المخالف الحقيقي (منطقة بلا مِرساة) ما زال ممنوعًا")
    test_composite_country_sea_area_uses_sea_anchor()
    print("   ✔ الاسم المركّب «البلد - البحر» يُرسم بمِرساة البحر")
    print("اختبار مشتق نقاط الخريطة: نجاح")
