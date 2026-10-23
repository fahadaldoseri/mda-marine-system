#!/usr/bin/env python3
"""تصنيف الأعطال المعروفة — قاعدة آلية لا حكم بشري (قرار صاحب القرار 2026-10-23 · ح-4).

كل عطل في التشغيل يُصنَّف: إمّا معروف مسموح بإفصاحه (وفق appendices/known-faults.json)،
وإمّا غير معروف ⇒ يمنع التسليم. لا اجتهاد: القائمة هي الحاكم.
"""
from __future__ import annotations

import json
from pathlib import Path

B = Path(__file__).resolve().parent.parent
CONFIG = B / "appendices" / "known-faults.json"


def expired(item: dict, today: str | None = None) -> bool:
    """البند المنتهي صلاحيته لا يُفصح عنه: يصير عطلًا غير مسموح فيمنع التسليم."""
    exp = (item or {}).get("expires")
    if not exp:
        return False
    import datetime as _dt
    d = today or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    return exp < d


def load() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _match(entry: dict, component: str, text: str) -> bool:
    if expired(entry):
        return False  # البند المنتهي صلاحيته لا يُفصح عنه ⇒ يبقى العطل غير مسموح فيمنع
    if component not in (entry.get("applies_to") or []):
        return False
    pats = entry.get("reason_patterns") or []
    return any(p.lower() in text.lower() for p in pats)


def classify_component(component: str, status: str, text: str, items: list[str] | None = None) -> dict:
    """يصنّف عطل مكوّن واحد.

    items: قائمة نصوص الأعطال المفردة (مثل أسباب تعذّر التغذيات) — تُصنَّف فردًا فردًا.
    يعيد: {allowed, entry_id, reason_ar, uncovered: [نصوص لم تُغطَّ], covered: int}
    """
    cfg = load()
    items = items or []
    if status == "ok":
        return {"allowed": True, "entry_id": None, "reason_ar": "", "reason_ar_full": "",
                "uncovered": [], "covered": 0}

    if items:
        covered = 0
        uncovered: list[str] = []
        entry_id = None
        reason_ar = ""
        per_entry: dict[str, int] = {}
        for it in items:
            hit = next((e for e in cfg["allowed"] if _match(e, component, it)), None)
            if not hit:
                uncovered.append(it)
                continue
            per_entry[hit["id"]] = per_entry.get(hit["id"], 0) + 1
            cap = hit.get("max_items")
            if cap is not None and per_entry[hit["id"]] > int(cap):
                uncovered.append(f"{it} (تجاوز حدّ «{hit['id']}» = {cap})")
                continue
            covered += 1
            entry_id = entry_id or hit["id"]
            reason_ar = reason_ar or hit["reason_ar"]
        hit0 = next((e for e in cfg["allowed"] if e["id"] == entry_id), None) if entry_id else None
        return {"allowed": not uncovered, "entry_id": entry_id, "reason_ar": reason_ar,
                "reason_ar_full": (hit0.get("reason_ar_full") if hit0 else reason_ar) or reason_ar,
                "uncovered": uncovered, "covered": covered}

    hit = next((e for e in cfg["allowed"] if _match(e, component, f"{status} {text}")), None)
    if hit:
        return {"allowed": True, "entry_id": hit["id"], "reason_ar": hit["reason_ar"],
                "reason_ar_full": hit.get("reason_ar_full") or hit["reason_ar"],
                "uncovered": [], "covered": 1}
    return {"allowed": False, "entry_id": None, "reason_ar": "", "reason_ar_full": "",
            "uncovered": [f"{component}: {status} — {text[:120]}"], "covered": 0}


def degraded_components(mark: dict) -> list[tuple[str, str, str, list[str]]]:
    """يستخرج كل مكوّن حالته ليست ok مع نصّه وأعطاله المفردة."""
    out: list[tuple[str, str, str, list[str]]] = []
    SKIP = {"final_gate", "sources", "written_stage", "ledger", "pipeline"}
    for k, v in (mark or {}).items():
        if k in SKIP or not isinstance(v, dict) or "status" not in v:
            continue
        st = str(v.get("status"))
        if st == "ok":
            continue
        items: list[str] = []
        if k == "feeds":
            for f in (v.get("failed_feeds") or []):
                if isinstance(f, dict):
                    items.append(str(f.get("block_reason") or f.get("reason") or f.get("name") or f))
                else:
                    items.append(str(f))
        out.append((k, st, str(v.get("note") or v.get("lasterror") or ""), items))
    return out