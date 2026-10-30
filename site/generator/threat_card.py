#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بطاقة مستوى التهديد بالقطاعات الأربعة — مصدر رسم واحد للشاشة والطباعة.

تُبنى من ملف حاكم واحد: brain-marine-news/web/zones/<date>.json
(مُولَّد بـ tools/classify_zones.py من السلّم المعتمد وسجل القطاعات والأحكام المحوكمة).

قواعد ملزمة:
  - لا يُرسم أي مستوى خارج السلّم المعتمد؛ أي لفظ غير معروف ⇒ استثناء (فشل مغلق).
  - لكل مستوى لون مميّز ووسم بصري مستقل (لا يتشارك «حرج» لون «مرتفع»).
  - نص البطاقة كله من **معجم مغلق**: عبارات ثابتة أو أرقام في عناصر مستقلة،
    حتى تُترجم آليًا بلا نصوص حرة (شرط بوابة الترجمة في النسخة الإنجليزية).
  - الأساس مطبوع مفتوح (details[open]) وظاهر على الجوال.
"""
from __future__ import annotations

import json
import os
import pathlib


def _brain_default() -> pathlib.Path:
    """جذر الدماغ: BRAIN أو BRAIN_DIR من البيئة، وإلا الجار الأعلى لمجلد الموقع (قابل للنقل)."""
    env = os.environ.get("BRAIN") or os.environ.get("BRAIN_DIR")
    if env:
        return pathlib.Path(env)
    return pathlib.Path(__file__).resolve().parents[2] / "brain-marine-news"


BRAIN_DEFAULT = _brain_default()

LEVEL_TOKENS = {
    "حرج": "critical",
    "مرتفع جدًا": "severe",
    "مرتفع": "high",
    "متوسط": "medium",
    "منخفض": "low",
}
MARKERS = {"critical": "◆◆", "severe": "◆", "high": "▲", "medium": "●", "low": "▬"}
FALLBACK_COLORS = {
    "critical": "#ff3b30",
    "severe": "#ff7a1a",
    "high": "#ffc02e",
    "medium": "#38bdf8",
    "low": "#4ade80",
}

# ── معجم النص المغلق (يُترجَم آليًا في النسخة الإنجليزية) ─────────────────────
T_CARD_TITLE = "مستوى التهديد حسب القطاعات"
T_WINDOW = "خلال 24 ساعة السابقة"
T_TOP = "أعلى قطاع:"
T_BASIS = "أساس التقدير"
T_NONE = "لا واقعة مؤهّلة"
T_ONE = "واقعة مؤهّلة واحدة"
T_TWO = "واقعتان مؤهّلتان"
T_MANY_SUFFIX = "وقائع مؤهّلة"
T_CARRY = "استمراري · آخر تغيّر:"
T_COUNT_HEAD = "العدّاد:"
T_QUAL = "وقائع مؤهّلة"
T_CONF = "مؤكدة"
T_PROB = "مرجّحة"
T_EXCL = "مستثناة"
T_NONSPATIAL = "غير مكانية"
T_TOTAL = "إجمالي"
T_SEP = "·"
T_DASH = "—"


class ThreatScaleError(RuntimeError):
    """لفظ مستوى خارج السلّم المعتمد ⇒ يُمنع الرسم."""


def level_token(level: str) -> str:
    if level not in LEVEL_TOKENS:
        raise ThreatScaleError(f"مستوى غير معتمد: «{level}» — لا يُرسم أي مستوى خارج السلّم")
    return LEVEL_TOKENS[level]


def _colors(zj: dict) -> dict:
    out = dict(FALLBACK_COLORS)
    for lv in zj.get("scale_levels") or []:
        tok = LEVEL_TOKENS.get(lv.get("ar", ""))
        if tok and lv.get("color"):
            out[tok] = lv["color"]
    return out


def zones_css(zj: dict) -> str:
    c = _colors(zj)
    rules = "\n".join(
        f".tz-badge.t-{k},.tz-lv.t-{k},.tz-dot.t-{k}{{color:{v};border-color:{v}}}"
        for k, v in c.items()
    )
    return f"""
.tz{{border:1px solid var(--line,#243244);border-radius:14px;padding:14px 16px;background:var(--card,#0e1726);margin:10px 0}}
.tz-head{{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;justify-content:space-between}}
.tz-head h3{{margin:0;font-size:1.05rem}}
.tz-win{{font-size:.8rem;opacity:.75}}
.tz-top{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:10px 0 6px}}
.tz-badge{{font-weight:700;font-size:1.5rem;line-height:1.2}}
.tz-sub{{margin:0;font-size:.85rem;opacity:.85}}
.tz-zones{{list-style:none;margin:10px 0 0;padding:0;display:grid;gap:6px}}
.tz-z{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;padding:7px 9px;border:1px solid var(--line,#243244);border-radius:10px}}
.tz-n{{font-size:.9rem}}
.tz-lv{{font-weight:700;font-size:.9rem}}
.tz-dot{{font-size:.8rem}}
.tz-c{{font-size:.78rem;opacity:.8}}
.tz-basis{{margin-top:10px;border-top:1px dashed var(--line,#243244);padding-top:8px}}
.tz-basis summary{{cursor:pointer;font-weight:600;font-size:.9rem}}
.tz-basis p{{margin:6px 0 0;font-size:.86rem;line-height:1.7}}
.tz-count{{opacity:.85}}
@media (max-width:640px){{
  .tz{{padding:12px}}
  .tz-badge{{font-size:1.3rem}}
  .tz-z{{flex-direction:column;align-items:flex-start}}
}}
{rules}
@media print{{
  /* ضغط الورق (2026-10-30): بطاقة القطاعات الأربعة أُضيفت إلى الترويسة فزاد طول الإصدار
     إلى 13 صفحة خارج النطاق 7–12. الضغط هنا للطباعة فقط ولا يمسّ هيئة الشاشة. */
  .tz{{break-inside:auto;page-break-inside:auto;border-color:#999;padding:2.2mm 3mm;margin:1.5mm 0}}
  .tz-head h3{{font-size:10.4pt}}
  .tz-win{{font-size:7.6pt}}
  .tz-top{{margin:1.1mm 0 .7mm;gap:2mm}}
  .tz-badge{{font-size:13pt;line-height:1.1}}
  .tz-sub{{font-size:8pt}}
  .tz-zones{{margin:1.1mm 0 0;gap:.7mm}}
  .tz-z{{padding:1mm 1.4mm;border-radius:1.2mm;gap:2mm}}
  .tz-n,.tz-lv,.tz-c,.tz-dot{{font-size:8pt;line-height:1.35}}
  .tz-basis{{margin-top:1.1mm;padding-top:.9mm}}
  .tz-basis summary{{font-size:8.5pt}}
  .tz-basis p{{margin:.7mm 0 0;font-size:8pt;line-height:1.35}}
  .tz-basis>*{{display:block!important}}
  .tz-basis summary{{list-style:none}}
}}
"""


def _n(value) -> str:
    """رقم في عنصر مستقل ليعبر بلا ترجمة."""
    return f'<span class="bidi">{value}</span>'


def count_phrase(n: int) -> str:
    if n <= 0:
        return T_NONE
    if n == 1:
        return T_ONE
    if n == 2:
        return T_TWO
    return f"{_n(n)} {T_MANY_SUFFIX}"


def _zone_basis(z: dict) -> str:
    if z.get("carry_over"):
        return f"{T_CARRY} {_n(z.get('carry_from', ''))}"
    parts = [count_phrase(len(z.get("qualifying_codes") or []))]
    cats = z.get("categories") or []
    if cats:
        parts.append(f"{T_DASH} " + f" {T_SEP} ".join(cats))
    return " ".join(parts)


def _counter_line(zj: dict) -> str:
    c = zj.get("counter") or {}
    return " ".join([
        T_COUNT_HEAD,
        f"{T_QUAL} {_n(c.get('qualifying', 0))}",
        f"{T_SEP} {T_CONF} {_n(c.get('confirmed', 0))}",
        f"{T_SEP} {T_PROB} {_n(c.get('probable', 0))}",
        f"{T_SEP} {T_EXCL} {_n(c.get('excluded', 0))}",
        f"{T_SEP} {T_NONSPATIAL} {_n(c.get('nonspatial', 0))}",
        f"{T_SEP} {T_TOTAL} {_n(c.get('total', 0))}",
    ])


def zones_card(zj: dict, *, variant: str = "screen") -> str:
    """يبني بطاقة القطاعات. variant: screen | print."""
    overall = zj.get("overall") or {}
    tok = level_token(overall.get("level", ""))
    rows = []
    for z in zj.get("zones") or []:
        ztok = level_token(z.get("level", ""))
        rows.append(
            '<li class="tz-z">'
            f'<span class="tz-n">{z.get("name", "")}</span>'
            f'<span class="tz-lv t-{ztok}"><span class="tz-dot t-{ztok}" aria-hidden="true">{MARKERS[ztok]}</span> {z.get("level", "")}</span>'
            f'<span class="tz-c">{count_phrase(len(z.get("qualifying_codes") or []))}</span>'
            "</li>"
        )
    basis_html = "".join(
        f'<p>{z.get("name","")}: {_zone_basis(z)}</p>' for z in (zj.get("zones") or [])
    )
    style = f"<style>{zones_css(zj)}</style>"
    return (
        style
        + f'<section class="tz tz-{variant}" aria-label="{T_CARD_TITLE}">'
        '<header class="tz-head">'
        f"<h3>{T_CARD_TITLE}</h3>"
        f'<span class="tz-win">{zj.get("window") or T_WINDOW}</span>'
        "</header>"
        '<div class="tz-top">'
        f'<span class="tz-badge t-{tok}"><span aria-hidden="true">{MARKERS[tok]}</span> {overall.get("level","")}</span>'
        f'<p class="tz-sub">{T_TOP} {overall.get("top_zone","")}</p>'
        "</div>"
        f'<ul class="tz-zones">{"".join(rows)}</ul>'
        f'<details class="tz-basis" open><summary>{T_BASIS}</summary>'
        f"{basis_html}"
        f'<p class="tz-count">{_counter_line(zj)}</p>'
        "</details>"
        "</section>"
    )


def load_zones(date_iso: str, brain: pathlib.Path | str | None = None) -> dict | None:
    root = pathlib.Path(brain) if brain else BRAIN_DEFAULT
    p = root / "web" / "zones" / f"{date_iso}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_zones_site(date_iso: str, site: pathlib.Path | str | None = None) -> dict | None:
    """يقرأ ملف القطاعات من مصادر الموقع (sources/zones) أو من الدماغ كبديل."""
    if site:
        p = pathlib.Path(site) / "sources" / "zones" / f"{date_iso}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return load_zones(date_iso)


def closed_vocabulary() -> list[str]:
    """العبارات الثابتة التي يجب أن تكون في معجم الترجمة الإنجليزية."""
    words = [
        T_CARD_TITLE, T_WINDOW, T_TOP, T_BASIS, T_NONE, T_ONE, T_TWO, T_MANY_SUFFIX,
        T_CARRY, T_COUNT_HEAD, T_QUAL, T_CONF, T_PROB, T_EXCL, T_NONSPATIAL, T_TOTAL,
        T_SEP, T_DASH,
    ]
    words += list(LEVEL_TOKENS.keys())
    return words


if __name__ == "__main__":  # فحص سريع
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--brain", default=str(BRAIN_DEFAULT))
    a = ap.parse_args()
    zj = load_zones(a.date, a.brain)
    if not zj:
        raise SystemExit(f"لا يوجد ملف قطاعات لـ {a.date}")
    print(zones_card(zj)[:800])
    print("   ── معجم النص المغلق ──")
    print("   " + " | ".join(closed_vocabulary()))
