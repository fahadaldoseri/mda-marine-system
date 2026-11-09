#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار تجميد لفظ «الموقع» على أسطح الخريطة (شديد على عطل ك-480).

الحالتان:
- سالب: إعادة «الموضع» داخل قسم الخريطة في الصفحة المبنية يجب أن تُمنع.
- موجب: الصفحة اليومية الفعلية تمرّ بلا مخالفة.

الغرض من الاختبار: إثبات أن الحاجز يمنع، لا أن الوضع الحالي سليم فقط.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
_site_candidates = [__import__("os").environ.get("SITE_DIR"),
                    __import__("os").environ.get("SITE"),
                    str(ROOT.parent / "site"), str(ROOT.parent / "seawatch"),
                    str(ROOT.parent.parent / "seawatch")]
SITE = next((pathlib.Path(p).resolve() for p in _site_candidates if p and
             (pathlib.Path(p) / "generator").is_dir()), (ROOT.parent / "site").resolve())
sys.path.insert(0, str(SITE / "generator"))

import check_map_contract as cmc  # noqa: E402

FAILED = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"   {'✔' if ok else '✘'} {name}{(' — ' + detail) if detail and not ok else ''}")
    if not ok:
        FAILED.append(name)


BAN = "الموضع"


def _fixture(term: str) -> str:
    """صفحة مصغّرة تحمل قسم خريطة مكتملًا مع لفظ الموقع المراد اختباره."""
    return (
        '<!doctype html><html lang="ar" dir="rtl"><body>'
        '<section class="map-panel"><div class="map-viz">'
        f'<svg><desc>الخريطة ترسم 1 واقعة؛ {term} تقريبي لغياب الإحداثيات.</desc></svg>'
        '<ol class="map-legend"><li>MN-2026-11-03-01 — حادث: {term} تقريبي داخل المنطقة</li></ol>'
        '</div></section></body></html>'
    ).replace("{term}", term)


def main() -> int:
    # 1) سالب: عودة اللفظ الممنوع تُمنع بصراحة
    bad = cmc.verify(_fixture(BAN), {"map": {"points": [{"precision": "approximate"}]}})
    hit = [x for x in bad if "«الموضع»" in x]
    check("سالب: «الموضع» في قسم الخريطة يُمنع", bool(hit), " | ".join(bad)[:160])

    # 2) موجب: اللفظ المعتمد لا يُنتج مخالفة اللفظ
    good = cmc.verify(_fixture("الموقع"), {"map": {"points": [{"precision": "approximate"}]}})
    check("موجب: «الموقع» لا يُنتج مخالفة لفظ", not [x for x in good if "«الموضع»" in x])

    # 3) موجب حي: صفحة اليوم المبنية تمرّ بلا مخالفة عقد
    args = sys.argv[1:]
    date = "2026-11-03"
    if "--date" in args:
        date = args[args.index("--date") + 1]
    elif args and args[0][:2] == "20":
        date = args[0]
    page = SITE / "dist" / "reports" / f"{date}.html"
    meta_path = ROOT / "web" / "meta" / f"{date}.json"
    if page.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        found = cmc.verify(page.read_text(encoding="utf-8"), meta)
        check(f"موجب حي: صفحة {date} المبنية بلا مخالفة عقد", not found, " | ".join(found)[:200])
        text = cmc._map_block(page.read_text(encoding="utf-8"))
        check(f"موجب حي: صفر «{BAN}» في قسم الخريطة المنشور", text.count(BAN) == 0, f"{text.count(BAN)} مرة")
    else:
        check(f"موجب حي: صفحة {date} المبنية", False, "الصفحة أو ملف الواجهة غير موجود")

    print(f"\n   النتيجة: {'اجتاز' if not FAILED else 'منع — ' + ' · '.join(FAILED)}")
    return 0 if not FAILED else 2


if __name__ == "__main__":
    sys.exit(main())
