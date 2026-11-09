#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حلّ جذر الموقع (seawatch) من مصدر واحد معلن.

سبب الوجود (ك-590): بوابات عدّة كانت تفترض أن الموقع تحت `mda-marine-system/seawatch`
أو تشتقّه بعدد ثابت من الآباء، فتنهار في التخطيط القانوني حيث الموقع في مجلد المنزل
(`$HOME/seawatch`) لا تحت مجلد المشروع.

الترتيب المعتمد: متغيّر البيئة `SITE_DIR` ثم `SITE` ثم مرشّحات التخطيط القانوني،
ويُشترط في المرشّح أن يحتوي `dist` أو `generator` حتى لا يُختار مجلد قديم بلا مخرج.
"""
from __future__ import annotations

import os
from pathlib import Path

BRAIN_DIR = Path(__file__).resolve().parents[1]


def candidates() -> list[Path]:
    """مرشّحات جذر الموقع بترتيب الأسبقية (البيئة أولًا)."""
    out: list[Path] = []
    for key in ("SITE_DIR", "SITE"):
        value = os.environ.get(key)
        if value and value.strip():
            out.append(Path(value.strip()).expanduser())
    out.extend(
        [
            BRAIN_DIR.parent / "seawatch",
            BRAIN_DIR.parent.parent / "seawatch",
            Path.home() / "seawatch",
        ]
    )
    return out


def looks_like_site(path: Path) -> bool:
    """المرشّح مقبول فقط إن كان مجلدًا يحمل مخرجًا أو مولّدًا."""
    try:
        if not path.is_dir():
            return False
    except OSError:
        return False
    return (path / "dist").is_dir() or (path / "generator").is_dir()


def resolve_site_root() -> Path | None:
    """يعيد جذر الموقع المقبول، أو None إن لم يوجد مرشّح صالح (فشل مغلق عند المستدعي)."""
    seen: set[Path] = set()
    for raw in candidates():
        try:
            path = raw.resolve()
        except OSError:
            continue
        if path in seen:
            continue
        seen.add(path)
        if looks_like_site(path):
            return path
    return None
