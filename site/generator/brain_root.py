# -*- coding: utf-8 -*-
"""جذر brain القانوني لمولّد الموقع — قياس واحد بدل مسارات مثبَّتة (ك-571).

السبب المقيس: كانت وحدات المولّد تحسب جذر الدماغ بمسار ثابت
``parents[2] / "brain-marine-news"`` وهو أرشيف قراءة فقط، فيسقط البناء عند غياب
متن اليوم فيه: «لم تُبنَ نسخة إنجليزية: ... brain-marine-news/reports/...».
القاعدة الآن: ``BRAIN_DIR`` من البيئة أولًا، ثم الجذر القانوني
``<parent>/mda-marine-system/brain``، ثم ``<parent>/brain``، ويُرفض الأرشيف
رفضًا مغلقًا كي لا يعود الخطأ صامتًا.
"""

from __future__ import annotations

import os
import pathlib

ARCHIVE_NAME = "brain-marine-news"


def site_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def brain_root() -> pathlib.Path:
    env = os.environ.get("BRAIN_DIR")
    if env:
        candidate = pathlib.Path(env).resolve()
        if ARCHIVE_NAME in candidate.parts:
            raise SystemExit(f"✘ BRAIN_DIR يشير إلى الأرشيف المرفوض: {candidate}")
        if candidate.is_dir():
            return candidate
        raise SystemExit(f"✘ BRAIN_DIR معلَن لكنه غير موجود: {candidate}")
    parent = site_root().parent
    for candidate in (parent / "mda-marine-system" / "brain", parent / "brain"):
        if (candidate / "reports").is_dir():
            return candidate
    raise SystemExit(
        "✘ تعذّر قياس جذر brain القانوني: عيّن BRAIN_DIR أو تأكد من وجود "
        f"{parent / 'mda-marine-system' / 'brain'}. لا يُستعمل الأرشيف {ARCHIVE_NAME} كمصدر."
    )


def under_brain(*parts: str) -> pathlib.Path:
    root = brain_root()
    path = root.joinpath(*parts)
    if ARCHIVE_NAME in path.parts:
        raise SystemExit(f"✘ مسار أرشيفي مرفوض كمصدر حاكم: {path}")
    return path