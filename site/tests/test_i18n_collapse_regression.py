#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس تقارب ضغط تكرار المصدر داخل صفحة التقرير الإنجليزية."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
import i18n_en as I  # noqa: E402


def test_inline_source_collapse_converges_and_is_idempotent() -> None:
    """مدخل يومي مصغّر يتقارب، ومخرجه لا يتغير عند إعادة التشغيل."""
    report_like = (
        '<article><p>المصدر الرسمي UKMTO Official source '
        '<span class="ltr">UKMTO</span> Official source.</p>'
        '<p>تحديث من المصدر الرسمي UKMTO Official source '
        '<span class="ltr">UKMTO</span> Official source.</p></article>'
    )

    first = I._collapse_inline_source_duplicates(report_like)
    second = I._collapse_inline_source_duplicates(first)

    assert first != report_like
    assert second == first
    assert '<span class="ltr">UKMTO</span>' in first
    assert 'UKMTO Official source <span class="ltr">UKMTO</span>' not in first

    # يثبت الاختبار أيضًا أن الحارس ليس حلقة مساواة غير مسقوفة؛
    # يجب أن يكون لكل دورة سقف مشتق من المقياس الانقاصي وفشل مغلق.
    source = inspect.getsource(I._collapse_inline_source_duplicates)
    assert "max_iterations" in source
    assert "raise RuntimeError" in source
