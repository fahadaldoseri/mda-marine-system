#!/usr/bin/env python3
"""مواءمة طبقات بطاقات المؤشرات في ملف الواجهة مع مصدرها الحاكم.

المشكلة التي يمنعها هذا الملف: بطاقة في `web/meta/{date}.json` تحمل قيمتي
`cumulative` و`updated` غير مطابقتين لمقاييس `web/kpis-totals/{date}.json`
التي يعرّفها عقد البطاقة في `appendices/card_registry.json`.

الاستعمال:
    python3 tools/sync_card_layers.py --date 2026-11-02 [--check]

- بلا `--check`: يكتب المواءمة في ملف الواجهة.
- مع `--check`: لا يكتب، ويخرج بالرمز 2 إذا وُجد انحراف (فشل مغلق).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


class FailClosed(Exception):
    """انحراف يمنع المتابعة."""


def load(path: pathlib.Path) -> dict:
    if not path.exists():
        raise FailClosed(f"ملف مفقود: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_plan(meta: dict, registry: dict, kpis: dict) -> list[dict]:
    """يبني قائمة المواءمات المطلوبة لكل بطاقة لها عقد طبقات."""
    cards = {c["id"]: c for c in registry["hero_kpis"]["cards"]}
    metrics = {m["id"]: m for m in kpis["metrics"]}
    plan = []
    for card in meta.get("hero_kpis") or []:
        contract = cards.get(card["id"])
        if not contract:
            continue
        layers = contract.get("layers") or {}
        for field_name, layer in layers.items():
            if layer.get("kind") != "kpis_totals":
                continue
            metric = metrics.get(layer.get("id"))
            if metric is None:
                raise FailClosed(
                    f"بطاقة {card['id']}: لا يوجد مقياس {layer.get('id')} في kpis-totals")
            want = metric.get(layer.get("field"))
            if want is None:
                raise FailClosed(
                    f"بطاقة {card['id']}: حقل {layer.get('field')} غائب في المقياس {layer.get('id')}")
            got = card.get(field_name)
            if str(got) != str(want):
                plan.append({"id": card["id"], "field": field_name, "from": got, "to": want})
                card[field_name] = want
    return plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--check", action="store_true", help="بلا كتابة: يفشل مغلقًا عند الانحراف")
    args = ap.parse_args()

    meta_path = ROOT / "web" / "meta" / f"{args.date}.json"
    kpis_path = ROOT / "web" / "kpis-totals" / f"{args.date}.json"
    reg_path = ROOT / "appendices" / "card_registry.json"

    try:
        meta = load(meta_path)
        kpis = load(kpis_path)
        registry = load(reg_path)
        plan = build_plan(meta, registry, kpis)
    except FailClosed as exc:
        print(f"   ✘ منع (فشل مغلق): {exc}")
        return 2

    if not plan:
        print(f"   ✔ طبقات البطاقات مطابقة لمصدرها ({args.date})")
        return 0

    for row in plan:
        print(f"   • {row['id']}.{row['field']}: «{row['from']}» → «{row['to']}»")

    if args.check:
        print(f"   ✘ انحراف في {len(plan)} طبقة بطاقة — شغّل بلا --check للمواءمة")
        return 2

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load(meta_path)
    print(f"   ✔ وُوفّقت {len(plan)} طبقة في {meta_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
