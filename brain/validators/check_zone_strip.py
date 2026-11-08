#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس شريط نسب القطاعات أسفل الخريطة.

يقارن DOM المبني بمصدر القطاعات الذي يقرأه المولّد، ويعيد 2 عند أي غياب،
تكرار، انحراف، أو عدم اتساق في مجموع مكوّنات القطاع.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE = ROOT.parent / "seawatch"
LABELS = {
    "مؤكدة": "confirmed",
    "مرجّحة": "probable",
    "مؤهلة غير مؤكدة": "unconfirmed_qualifying",
    "مستثناة": "excluded",
    "إجمالي": "total",
}


def _norm(value: str) -> str:
    return " ".join(html.unescape(value or "").split())


class _ZoneStripParser:
    """قارئ DOM صغير يلتقط الشريط وعقده، ولا يبحث في النص الحر خارج الشريط."""

    def __init__(self) -> None:
        self.stack: list[str] = []
        self.strip_depth: int | None = None
        self.strip_count = 0
        self.zone_depth: int | None = None
        self.current: dict | None = None
        self.zones: list[dict] = []
        self.capture: tuple[str, int, list[str]] | None = None

    def feed(self, source: str) -> None:
        from html.parser import HTMLParser

        parser = self

        class _Parser(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)

            def handle_starttag(self, tag, attrs):
                parser.start(tag, dict(attrs))

            def handle_startendtag(self, tag, attrs):
                parser.start(tag, dict(attrs))
                parser.end(tag)

            def handle_endtag(self, tag):
                parser.end(tag)

            def handle_data(self, data):
                parser.data(data)

        _Parser().feed(source)

    def start(self, tag: str, attrs: dict[str, str]) -> None:
        depth = len(self.stack)
        classes = set((attrs.get("class") or "").split())
        if tag == "div" and "hmap-zstrip" in classes:
            self.strip_count += 1
            if self.strip_depth is None:
                self.strip_depth = depth
        if self.strip_depth is not None and tag == "li" and self.zone_depth is None:
            self.zone_depth = depth
            # المعرّف الآلي يُقرأ من سمة البيانات (لا من نص مرئي) لأن قرار المالك
            # يمنع عرض رموز القطاعات للقارئ؛ ويُقبل وسم zs-id القديم للتوافق.
            self.current = {"id": _norm(attrs.get("data-zone-id") or ""), "name": "", "metrics": {}}
        if self.zone_depth is not None and tag == "span":
            field = None
            if "zs-nm" in classes:
                field = "name"
            elif "zs-id" in classes:
                field = "id"
            elif "zs-p" in classes:
                field = "metric"
            if field:
                self.capture = (field, depth, [])
        self.stack.append(tag)

    def end(self, tag: str) -> None:
        if not self.stack:
            return
        self.stack.pop()
        if self.capture is not None:
            field, depth, parts = self.capture
            if len(self.stack) == depth:
                text = _norm(" ".join(parts))
                if field == "name" and self.current is not None:
                    self.current["name"] = text
                elif field == "id" and self.current is not None and not self.current.get("id"):
                    self.current["id"] = text
                elif field == "metric" and self.current is not None:
                    self._add_metric(text)
                self.capture = None
        if self.zone_depth is not None and len(self.stack) == self.zone_depth:
            if self.current is not None:
                self.zones.append(self.current)
            self.current = None
            self.zone_depth = None
        if self.strip_depth is not None and len(self.stack) == self.strip_depth:
            self.strip_depth = None

    def data(self, value: str) -> None:
        if self.capture is not None:
            self.capture[2].append(value)

    def _add_metric(self, text: str) -> None:
        if self.current is None:
            return
        for label, key in LABELS.items():
            if not text.startswith(label):
                continue
            tail = text[len(label):].strip()
            values = re.findall(r"(?<!\d)\d+(?!\d)", tail)
            if len(values) == 1:
                self.current["metrics"][key] = int(values[0])
            return


def _source_counts(zone: dict) -> tuple[dict[str, int] | None, list[str]]:
    errors: list[str] = []
    zone_id = str(zone.get("id") or "?")
    try:
        qualifying = int(zone.get("qualifying") or len(zone.get("qualifying_codes") or []))
        confirmed = int(zone.get("confirmed") or 0)
        probable = int(zone.get("probable") or 0)
        excluded = int(zone.get("excluded") or 0)
        total = int(zone.get("events") or 0)
    except (TypeError, ValueError) as exc:
        return None, [f"مصدر القطاع {zone_id} يحوي عدادًا غير رقمي: {exc}"]
    unconfirmed = qualifying - confirmed - probable
    values = {
        "confirmed": confirmed,
        "probable": probable,
        "unconfirmed_qualifying": unconfirmed,
        "excluded": excluded,
        "total": total,
    }
    if min(values.values()) < 0:
        errors.append(f"عداد قطاع سالب: {zone_id}")
    components = confirmed + probable + unconfirmed + excluded
    if components != total:
        errors.append(f"مجموع مكوّنات القطاع {zone_id}={components} لا يساوي الإجمالي={total}")
    return values, errors


def validate_zone_strip(page_html: str, source: dict) -> list[str]:
    """Return all contract violations; the CLI maps any non-empty result to 2."""
    errors: list[str] = []
    parser = _ZoneStripParser()
    parser.feed(page_html)
    if parser.strip_count != 1:
        errors.append(f"شريط نسب القطاعات غير قابل للتعيين: وُجد {parser.strip_count} بدل 1")
        return errors
    source_zones = source.get("zones") if isinstance(source, dict) else None
    if not isinstance(source_zones, list) or not source_zones:
        return ["مصدر القطاعات مفقود أو بلا قائمة قطاعات"]
    expected: dict[str, dict[str, int]] = {}
    by_name: dict[str, str] = {}
    for zone in source_zones:
        if not isinstance(zone, dict) or not str(zone.get("id") or "").strip():
            errors.append("مصدر القطاعات يحوي قطاعًا بلا معرّف")
            continue
        zone_id = str(zone["id"])
        zone_name = _norm(zone.get("name") or "")
        if zone_id in expected:
            errors.append(f"معرّف قطاع مكرر في المصدر: {zone_id}")
            continue
        if zone_name:
            if zone_name in by_name:
                errors.append(f"اسم قطاع مكرر في المصدر: {zone_name}")
            by_name[zone_name] = zone_id
        counts, count_errors = _source_counts(zone)
        errors.extend(count_errors)
        if counts is not None:
            expected[zone_id] = counts
    seen: list[str] = []
    for row in parser.zones:
        # الهوية بالاسم المرئي أولًا: رموز القطاعات ممنوعة على سطح القارئ
        # فتُنقّى من الوسوم، ويبقى الاسم ثابتًا وقابلًا للمطابقة.
        row_name = _norm(row.get("name") or "")
        zone_id = by_name.get(row_name, "") if row_name else ""
        if not zone_id:
            zone_id = _norm(row.get("id") or "")
        if not zone_id:
            errors.append(f"صف في شريط القطاعات بلا معرّف مطابق للمصدر: {row_name or 'بلا اسم'}")
            continue
        if zone_id in seen:
            errors.append(f"قطاع مكرر في شريط النسب: {zone_id}")
            continue
        seen.append(zone_id)
        if zone_id not in expected:
            errors.append(f"قطاع ظاهر بلا سجل حاكم: {zone_id}")
            continue
        metrics = row.get("metrics") or {}
        missing = sorted(set(LABELS.values()) - set(metrics))
        if missing:
            errors.append(f"شريط القطاع {zone_id} يفتقد عدادات: {', '.join(missing)}")
            continue
        for key, wanted in expected[zone_id].items():
            actual = metrics[key]
            if actual != wanted:
                label = next(label for label, mapped in LABELS.items() if mapped == key)
                errors.append(f"{zone_id}: عداد {label} في الصفحة={actual} والمصدر={wanted}")
        components = sum(metrics[key] for key in ("confirmed", "probable", "unconfirmed_qualifying", "excluded"))
        if components != metrics["total"]:
            errors.append(f"{zone_id}: مجموع مكوّنات الصفحة={components} لا يساوي الإجمالي={metrics['total']}")
    if seen != list(expected):
        missing = [zone_id for zone_id in expected if zone_id not in seen]
        extra = [zone_id for zone_id in seen if zone_id not in expected]
        if missing:
            errors.append(f"قطاعات المصدر غير ظاهرة في الشريط: {', '.join(missing)}")
        if extra:
            errors.append(f"قطاعات الشريط الزائدة: {', '.join(extra)}")
    return errors


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_governed_source(date: str, brain: Path, site: Path) -> tuple[dict | None, list[str]]:
    brain_path = brain / "web" / "zones" / f"{date}.json"
    site_path = site / "sources" / "zones" / f"{date}.json"
    brain_data = _load_json(brain_path) if brain_path.is_file() else None
    site_data = _load_json(site_path) if site_path.is_file() else None
    errors: list[str] = []
    if brain_data is None and site_data is None:
        errors.append(f"مصدر القطاعات مفقود: {site_path} أو {brain_path}")
        return None, errors
    if brain_data is not None and site_data is not None and brain_data != site_data:
        errors.append(f"مصدر القطاعات غير متزامن بين {site_path} و{brain_path}")
    # load_zones_site reads sources/zones first and falls back to brain/web/zones.
    return site_data if site_data is not None else brain_data, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--brain", default=str(ROOT))
    parser.add_argument("--site", default=str(DEFAULT_SITE))
    parser.add_argument("--html", default="")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    brain = Path(args.brain)
    site = Path(args.site)
    html_path = Path(args.html) if args.html else site / "dist" / "reports" / f"{args.date}.html"
    source, source_errors = _load_governed_source(args.date, brain, site)
    errors = list(source_errors)
    if not html_path.is_file():
        errors.append(f"صفحة التقرير مفقودة: {html_path}")
    elif source is not None:
        errors.extend(validate_zone_strip(html_path.read_text(encoding="utf-8"), source))
    if args.as_json:
        print(json.dumps({"date": args.date, "errors": errors}, ensure_ascii=False))
    else:
        for error in errors:
            print(f"✘ {error}")
        if not errors:
            print(f"✔ شريط نسب القطاعات مطابق للمصدر: {args.date}")
    return 2 if errors else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
