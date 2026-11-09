#!/usr/bin/env python3
"""اختبار انحدار لبوابتي الطباعة: بصمة النمط المقفل وقياس كتلة الخريطة.

يحمي عطلين جذريين مُثبتين بالقياس (2026-11-09):
  ك-XXX-1: فحص بصمة النمط كان يجزّئ قيمة الملف المقفل مرتين، فلا يمرّ أبدًا.
  ك-XXX-2: قياس كتلة الخريطة كان لونيًا تقديريًا وحده، فيسقط على خريطة بلوحة
           فاتحة مضغوطة ويُعلن «لم تُعثر كتلة» وهي موجودة.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

B = pathlib.Path(__file__).resolve().parents[1]
FROZEN = B / "templates" / "approved-pdf" / "print-css-frozen.css"
PROFILE = B / "templates" / "approved-pdf" / "print-profile.json"
def _site() -> pathlib.Path:
    """جذر الموقع: SITE_DIR، ثم seawatch الشقيق، ثم النسخة المتداخلة — بلا مسار مطلق."""
    import os
    v = os.environ.get("SITE_DIR")
    if v:
        return pathlib.Path(v)
    for cand in (B.parent / "seawatch", B / "site"):
        if cand.is_dir():
            return cand
    return B.parent / "seawatch"


REF_PDF_NO_IMAGE = _site() / "dist" / "reports" / "pdf" / "2026-10-30.pdf"
TODAY_PDF = _site() / "dist" / "reports" / "pdf" / "2026-11-08.pdf"


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pdf_format():
    return _load("cpf_gate", B / "validators" / "check_pdf_format.py")


def _print_quality():
    return _load("cpq_gate", B / "validators" / "check_print_quality.py")


def test_css_fingerprint_compares_once():
    """موجب: النص نفسه يطابق · سالب: أي تغيّر حرفي يُرفض (فشل مغلق)."""
    m = _pdf_format()
    frozen = FROZEN.read_text(encoding="utf-8")
    assert m.css_fingerprint_failure(frozen, frozen) is None
    assert m.css_fingerprint_failure(frozen, frozen + "\n") is not None
    changed = frozen.replace("}", "", 1)
    assert changed != frozen, "تعذّر بناء حالة سالبة: لا يوجد «}» في النمط المقفل"
    assert m.css_fingerprint_failure(frozen, changed) is not None


def test_frozen_css_matches_profile_and_generator():
    """عقد الحوكمة: البصمة المقفلة = بصمة الملف التعريفي = بصمة المولّد الحالي."""
    m = _pdf_format()
    frozen_hash = m.sha(FROZEN.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    assert profile["print_css_sha16"] == frozen_hash, "الملف التعريفي لا يطابق النمط المقفل"
    assert m.sha(m.current_print_css()) == frozen_hash, "مولّد التقرير انحرف عن النمط المقفل"


def test_map_geometry_is_measured_for_embedded_map():
    """موجب: PDF اليوم يحمل صورة خريطة بمقاس فوق الأرضية المعتمدة."""
    if not TODAY_PDF.is_file():
        return
    m = _print_quality()
    geo = m._map_image_geometry(TODAY_PDF)
    assert geo is not None, "لم تُقرأ صورة الخريطة المضمَّنة"
    assert geo["w_mm"] >= 210 * 0.70 - 0.5, f"عرض الخريطة {geo['w_mm']:.1f} مم دون الأرضية"
    assert geo["h_mm"] >= 297 * 0.32 - 0.5, f"ارتفاع الخريطة {geo['h_mm']:.1f} مم دون الأرضية"


def test_map_geometry_returns_none_without_embedded_image():
    """سالب: حين لا صورة مضمَّنة يعود None فيبقى الكشف اللوني مسارًا احتياطيًا."""
    if not REF_PDF_NO_IMAGE.is_file():
        return
    m = _print_quality()
    assert m._map_image_geometry(REF_PDF_NO_IMAGE) is None


def test_map_geometry_fails_closed_on_missing_file():
    """سالب: ملف غير موجود لا يُنتج قياسًا ولا يمرّ بلا دليل."""
    m = _print_quality()
    assert m._map_image_geometry(pathlib.Path("/tmp/لا-يوجد-مثل-هذا.pdf")) is None
