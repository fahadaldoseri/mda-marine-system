#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قياس وصول المصادر المسجّلة إلى دفتر الوقائع اليومي.

الأداة لا تجلب الشبكة ولا تعدّل دفتر الوقائع؛ تقرأ فقط:
- appendices/sources-manifest.json ثم سجل المصدر المشار إليه فيه.
- tools/check_feeds.py وtools/source_channels.py لتحديد المسار المعلن.
- feeds/feeds-<date>.status.json لإثبات فحص التشغيل.
- cumulative-2026/daily/*.json لعدّ الوقائع عبر source وsource_excerpt_from.

الاستخدام:
  python3 tools/measure_source_ledger_coverage.py --brain /path/to/brain \
      --date 2026-11-01 --days 30 --json-out logs/...json --md-out logs/...md
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import importlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


BLOCK_MARKERS = (
    "403", "401", "405", "429", "captcha", "cloudflare", "حجب", "تحقق بشري",
    "human verification", "access denied", "connection reset", "timed out",
    "remote end closed", "refused", "تحدٍ أمني",
)


def norm(value: Any) -> str:
    text = html.unescape(str(value or "")).lower()
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in unicodedata.normalize("NFD", text)
                    if unicodedata.category(ch) != "Mn")
    text = text.replace("ـ", "")
    return re.sub(r"\s+", " ", text).strip()


def tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9\u0621-\u064a]{3,}", norm(value)))


def valid_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"التاريخ ليس YYYY-MM-DD: {value}") from exc


def load_registry(brain: Path) -> list[dict[str, Any]]:
    manifest_path = brain / "appendices" / "sources-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rel = manifest.get("source_list_json")
    if not isinstance(rel, str) or not rel:
        raise ValueError("sources-manifest.json لا يعلن source_list_json")
    source_path = brain / rel
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"سجل المصادر ليس قائمة: {source_path}")
    rows: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, list) or len(row) < 3:
            raise ValueError(f"سجل مصدر غير صالح: {row!r}")
        rows.append({"num": int(row[0]), "name": str(row[1]), "url": str(row[2]),
                     "classification": row[3] if len(row) > 3 else "",
                     "reliability": row[4] if len(row) > 4 else ""})
    declared = manifest.get("approved_source_count")
    if declared is not None and int(declared) != len(rows):
        raise ValueError(f"المانيفست يعلن {declared} مصدرًا بينما السجل يحوي {len(rows)}")
    nums = [r["num"] for r in rows]
    if len(nums) != len(set(nums)):
        raise ValueError("أرقام المصدر مكررة في السجل الحاكم")
    return rows


def load_routes(brain: Path) -> tuple[list[dict[str, Any]], set[int], dict[int, str], dict[int, dict[str, str]], set[int]]:
    tools = brain / "tools"
    sys.path.insert(0, str(tools))
    try:
        check_feeds = importlib.import_module("check_feeds")
        channels = importlib.import_module("source_channels")
        feeds = [{"num": int(x["num"]), "name": str(x.get("name", "")),
                  "url": str(x.get("url", ""))} for x in check_feeds.feeds()]
        manual = {int(x) for x in channels.MANUAL_REFERENCE}
        manual_reasons = {int(k): str(v) for k, v in getattr(channels, "MANUAL_REFERENCE_REASON", {}).items()}
        browser = {int(k): dict(v) for k, v in getattr(channels, "BROWSER_ROUTES", {}).items()}
        browser_only = {int(k) for k in getattr(channels, "BROWSER_ONLY", {}).keys()}
    finally:
        # Keep the process import-safe for callers that use the module twice.
        try:
            sys.path.remove(str(tools))
        except ValueError:
            pass
    return feeds, manual, manual_reasons, browser, browser_only


def load_status(brain: Path, date: str) -> dict[str, Any]:
    path = brain / "feeds" / f"feeds-{date}.status.json"
    if not path.is_file():
        raise FileNotFoundError(f"ملف حالة التشغيل مفقود: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"ملف الحالة ليس كائنًا: {path}")
    checked = data.get("checked_feeds")
    if not isinstance(checked, list):
        raise ValueError("ملف الحالة لا يحوي checked_feeds")
    return data


def daily_files(brain: Path, end: dt.date, days: int) -> tuple[list[tuple[dt.date, Path]], list[str]]:
    start = end - dt.timedelta(days=days - 1)
    directory = brain / "cumulative-2026" / "daily"
    selected: list[tuple[dt.date, Path]] = []
    invalid: list[str] = []
    for path in sorted(directory.glob("*.json")):
        try:
            day = valid_date(path.stem)
        except ValueError:
            invalid.append(path.name)
            continue
        if start <= day <= end:
            selected.append((day, path))
    return selected, invalid


def read_events(files: list[tuple[dt.date, Path]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for day, path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("events", data.get("items", []))
        if not isinstance(data, list):
            raise ValueError(f"دفتر اليوم ليس قائمة وقائع: {path}")
        for index, event in enumerate(data, 1):
            if not isinstance(event, dict):
                raise ValueError(f"واقعة ليست كائنًا: {path}#{index}")
            events.append({"_ledger_date": day.isoformat(), "_ledger_file": str(path),
                           "_ledger_index": index, **event})
    return events


def host(value: str) -> str:
    parsed = urlparse(value if "://" in value else "https://" + value)
    return (parsed.hostname or "").lower().removeprefix("www.")


def path_part(value: str) -> str:
    parsed = urlparse(value if "://" in value else "https://" + value)
    return norm(parsed.path).strip("/")


# Only unambiguous aliases are used here. Ambiguous labels such as bare UKMTO
# are resolved by an explicit feed number or URL in source_excerpt_from instead.
STATIC_ALIASES: dict[int, tuple[str, ...]] = {
    1: ("ukmto — recent incidents", "ukmto 179-26", "ukmto 180-26"),
    2: ("ukmto — warnings", "ukmto warning"),
    3: ("ukmto — advisories", "ukmto advisory"),
    4: ("ukmto — weekly reports",),
    5: ("imo — highlighted confirmed incidents", "imo confirmed incident", "imo"),
    6: ("straits.live",),
    7: ("gcaptain",),
    8: ("tradewinds",),
    9: ("seatrade maritime",),
    10: ("الجزيرة نت", "ajnet"),
    11: ("الجزيرة الإنجليزية", "aljazeera english"),
    12: ("ofac",),
    14: ("قناة العربية", "alarabiya"),
    20: ("جريدة الأيام", "alayam"),
    21: ("جريدة أخبار الخليج", "akhbar-alkhaleej"),
    22: ("جريدة البلاد", "albiladpress"),
    24: ("قنا", "وكالة الأنباء القطرية"),
    25: ("وام", "وكالة أنباء الإمارات"),
    26: ("واس", "وكالة الأنباء السعودية"),
    27: ("كونا", "وكالة الأنباء الكويتية"),
    28: ("وكالة الأنباء العمانية", "omannews"),
    29: ("البحرية الملكية البريطانية", "royal navy"),
    30: ("القيادة المركزية الامريكية", "القيادة المركزية الأميركية", "سنتكوم", "centcom"),
    31: ("jmic", "combined maritime forces"),
    32: ("imb/icc", "imb/icc", "المكتب البحري الدولي"),
    33: ("marad/msci", "marad",),
    34: ("mscio",),
    35: ("splash 247",),
    36: ("lloyd's list", "لويدز ليست"),
    37: ("marinelink",),
    38: ("jerusalem post", "جيروزاليم بوست"),
    40: ("marinetraffic",),
    41: ("usni news",),
    42: ("naval news", "نافال نيوز"),
    43: ("the maritime executive", "maritime executive"),
    44: ("windward",),
    45: ("irib news",),
    46: ("isna",),
    47: ("mehr", "مهر"),
    48: ("institute for the study of war", "isw"),
    49: ("sanaa center",),
    50: ("navy times",),
    51: ("baird maritime",),
    52: ("synmax",),
    53: ("new york times",),
    54: ("bloomberg",),
    55: ("axios",),
    56: ("yemenresistanc1",),
    57: ("spokespersonyem",),
    58: ("yafm",),
    59: ("army21ye",),
    60: ("cjfcspox",),
    61: ("eryanim",),
    62: ("yemenarmyeng",),
}


def build_metadata(rows: list[dict[str, Any]], feeds: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    by_num: dict[int, dict[str, Any]] = {r["num"]: {**r, "feed_routes": []} for r in rows}
    for feed in feeds:
        if feed["num"] in by_num:
            by_num[feed["num"]]["feed_routes"].append(feed)
    return by_num


def number_from_excerpt(text: str, approved: set[int]) -> set[int]:
    found: set[int] = set()
    # Feed records use a stable "· <number>. <name>" marker.
    for match in re.finditer(r"(?:^|[·|])\s*(\d{1,2})\s*\.\s+", text):
        number = int(match.group(1))
        if number in approved:
            found.add(number)
    return found


def explicit_url_matches(text: str, metadata: dict[int, dict[str, Any]]) -> set[int]:
    value = norm(text)
    found: set[int] = set()
    text_hosts = {host(u) for u in re.findall(r"https?://[^\s·|]+", text)}
    for number, row in metadata.items():
        urls = [row["url"]] + [f["url"] for f in row["feed_routes"]]
        for url in urls:
            h = host(url)
            p = path_part(url)
            if h and h in text_hosts:
                # Shared X host needs the handle/path; other hosts are unique enough
                # only when they belong to one registered source.
                if h != "x.com":
                    found.add(number)
                elif p and p in value:
                    found.add(number)
            if norm(url) in value:
                found.add(number)
            if h and h != "x.com" and h in value and (not p or p in value):
                found.add(number)
            if h == "x.com" and p and p in value:
                found.add(number)
    return found


def label_matches(text: str, metadata: dict[int, dict[str, Any]]) -> set[int]:
    value = norm(text)
    found: set[int] = set()
    # First accept full labels. This is deterministic and avoids prefix collisions.
    for number, row in metadata.items():
        labels = [row["name"]] + [f["name"] for f in row["feed_routes"]]
        labels += list(STATIC_ALIASES.get(number, ()))
        for label in labels:
            key = norm(label)
            if len(key) >= 3 and key in value:
                found.add(number)
                break
    # A unique registry brand may be used without its full name.
    brands: dict[str, set[int]] = defaultdict(set)
    for number, row in metadata.items():
        brand = row["name"].split("—", 1)[0].strip()
        if len(norm(brand)) >= 3:
            brands[norm(brand)].add(number)
    for brand, nums in brands.items():
        if len(nums) == 1 and brand in value:
            found.update(nums)
    return found


def match_event(event: dict[str, Any], metadata: dict[int, dict[str, Any]], approved: set[int]) -> tuple[set[int], set[int], set[int]]:
    source = str(event.get("source") or "")
    excerpt = str(event.get("source_excerpt_from") or "")
    direct = explicit_url_matches(source, metadata) | label_matches(source, metadata)
    excerpt_ids = number_from_excerpt(excerpt, approved)
    excerpt_ids |= explicit_url_matches(excerpt, metadata) | label_matches(excerpt, metadata)
    all_ids = direct | excerpt_ids
    return all_ids, direct, excerpt_ids


def status_by_num(status: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in status.get("checked_feeds", []):
        if isinstance(item, dict) and "num" in item:
            result[int(item["num"])].append(item)
    return result


def reason_for_zero(number: int, manual: set[int], feed_routes: list[dict[str, Any]], status_items: list[dict[str, Any]], checked_nums: set[int]) -> tuple[str, str]:
    if number in manual:
        return "أ", "لا مسار استخراج آلي؛ المصدر معلن مرجعية يدوية"
    if not feed_routes:
        return "أ", "لا صف مسار آلي ولا قيد مرجعية يدوية"
    if number not in checked_nums:
        return "ج", "المصدر المسجّل لم يظهر في checked_feeds ولم يُعلن يدويًا في ملف الحالة"
    if not status_items:
        return "ج", "مسار معلن لكن لا سجل فحص له في ملف الحالة"
    failures = [str(x.get("error") or x.get("block_reason") or "") for x in status_items if not x.get("ok")]
    if failures and not any(bool(x.get("ok")) for x in status_items):
        joined = " | ".join(failures)
        if any(marker in norm(joined) for marker in BLOCK_MARKERS):
            return "ج", f"كل المسارات متعذّرة/محجوبة: {joined[:400]}"
        return "ب", f"المسار موجود لكنه لم ينتج مادة مقروءة: {joined[:400]}"
    item_count = sum(int(x.get("items_count") or 0) for x in status_items if x.get("ok"))
    if item_count == 0:
        return "ب", "المسار فُحص دون عناصر مقروءة"
    return "ب", f"المسار أنتج {item_count} عنصرًا في التغذية لكن لم تُسجّل واقعة دفترية خلال الفترة"


def measure(brain: Path, date: str, days: int) -> dict[str, Any]:
    end = valid_date(date)
    if days < 1:
        raise ValueError("--days يجب أن يكون موجبًا")
    registry = load_registry(brain)
    approved = {r["num"] for r in registry}
    feeds, manual, manual_reasons, browser_routes, browser_only = load_routes(brain)
    metadata = build_metadata(registry, feeds)
    status = load_status(brain, date)
    by_status = status_by_num(status)
    checked_nums = set(by_status) | {int(x) for x in status.get("manual_reference", [])}
    files, invalid_daily_names = daily_files(brain, end, days)
    events = read_events(files)
    counts: dict[int, int] = defaultdict(int)
    direct_counts: dict[int, int] = defaultdict(int)
    excerpt_counts: dict[int, int] = defaultdict(int)
    last_access: dict[int, str] = {}
    unmatched: defaultdict[str, int] = defaultdict(int)
    event_matches: list[dict[str, Any]] = []
    for event in events:
        all_ids, direct, excerpt_ids = match_event(event, metadata, approved)
        if not all_ids:
            unmatched[str(event.get("source") or "<missing>")] += 1
        for number in all_ids:
            counts[number] += 1
            if number in direct:
                direct_counts[number] += 1
            if number in excerpt_ids:
                excerpt_counts[number] += 1
            last_access[number] = max(last_access.get(number, ""), event["_ledger_date"])
        event_matches.append({"date": event["_ledger_date"], "code": event.get("code"),
                              "matched_source_numbers": sorted(all_ids),
                              "source": event.get("source", ""),
                              "source_excerpt_from": event.get("source_excerpt_from", "")})
    sources: list[dict[str, Any]] = []
    for row in registry:
        number = row["num"]
        route_rows = metadata[number]["feed_routes"]
        statuses = by_status.get(number, [])
        ok_routes = [x for x in statuses if x.get("ok")]
        failed_routes = [x for x in statuses if not x.get("ok")]
        if number in manual:
            route_kind = "مرجعية يدوية"
        elif route_rows:
            route_kind = "مسار آلي"
        else:
            route_kind = "معطّل"
        if number in manual:
            route_state = "مرجعية يدوية"
        elif not route_rows or number not in checked_nums or (statuses and not ok_routes):
            route_state = "معطّل"
        else:
            route_state = "مسار آلي"
        category, reason = ("", "")
        if counts[number] == 0:
            category, reason = reason_for_zero(number, manual, route_rows, statuses, checked_nums)
        sources.append({
            "num": number, "name": row["name"], "url": row["url"],
            "route_kind": route_kind, "route_state": route_state,
            "route_count": len(route_rows), "status_route_count": len(statuses),
            "status_ok_route_count": len(ok_routes), "status_failed_route_count": len(failed_routes),
            "feed_items_count": sum(int(x.get("items_count") or 0) for x in ok_routes),
            "event_count": counts[number], "direct_source_count": direct_counts[number],
            "source_excerpt_count": excerpt_counts[number],
            "last_access": last_access.get(number, ""),
            "zero_category": category, "zero_reason": reason,
            "manual_reason": manual_reasons.get(number, ""),
            "manual": number in manual,
            "browser_route": browser_routes.get(number),
            "browser_only": number in browser_only,
        })
    route_nums = {int(x["num"]) for x in feeds}
    missing_checked = sorted(approved - checked_nums)
    unknown_checked = sorted(checked_nums - approved)
    status_manual = {int(x) for x in status.get("manual_reference", [])}
    return {
        "date": date, "period_start": (end - dt.timedelta(days=days - 1)).isoformat(),
        "period_end": end.isoformat(), "days": days,
        "manifest_path": str(brain / "appendices" / "sources-manifest.json"),
        "registry_path": str(brain / "appendices" / "source-reliability-40.json"),
        "approved_source_count": len(registry), "manifest_declared_source_count": 62,
        "route_declared_unique_count": len(route_nums), "route_declared_row_count": len(feeds),
        "manual_reference_count": len(manual), "manual_reference": sorted(manual),
        "manual_reference_reasons": {str(k): v for k, v in sorted(manual_reasons.items())},
        "checked_unique_count": len(set(by_status)), "checked_union_manual_count": len(checked_nums),
        "checked_missing_sources": missing_checked, "checked_unknown_sources": unknown_checked,
        "status_manual_reference": sorted(status_manual),
        "status_file": str(brain / "feeds" / f"feeds-{date}.status.json"),
        "status_value": status.get("status"), "status_declared_checked": status.get("checked"),
        "status_declared_ok": status.get("ok"), "status_declared_failed": status.get("failed"),
        "daily_files_count": len(files), "daily_files": [p.name for _, p in files],
        "daily_invalid_names": invalid_daily_names, "daily_event_count": len(events),
        "sources_reaching_ledger_count": sum(1 for x in sources if x["event_count"] > 0),
        "sources_without_ledger_events_count": sum(1 for x in sources if x["event_count"] == 0),
        "sources": sources, "unmatched_source_values": dict(sorted(unmatched.items(), key=lambda x: (-x[1], x[0]))),
        "event_matches": event_matches,
    }


def md_table(result: dict[str, Any]) -> str:
    lines = [
        f"# قياس وصول المصادر إلى دفتر الوقائع — {result['date']}", "",
        f"الفترة المقاسة: {result['period_start']} إلى {result['period_end']} ({result['days']} يومًا).",
        f"السجل الحاكم: {result['approved_source_count']} مصدرًا · المسارات الآلية المعلنة: {result['route_declared_unique_count']} مصدرًا ({result['route_declared_row_count']} صفًا) · المرجعية اليدوية: {result['manual_reference_count']} · وصول فعلي إلى الدفتر: {result['sources_reaching_ledger_count']}.",
        f"الوقائع المقروءة: {result['daily_event_count']} في {result['daily_files_count']} ملفًا يوميًا · فحص التشغيل: {result['checked_unique_count']} مصدرًا آليًا + {result['manual_reference_count']} يدويًا = {result['checked_union_manual_count']}.",
        "",
        "| الرقم | المصدر | المسار | الوقائع | آخر وصول | حالة عدم الوصول/السبب |",
        "|---:|---|---|---:|---|---|",
    ]
    for row in result["sources"]:
        reason = f"{row['zero_category']} — {row['zero_reason']}" if row["event_count"] == 0 else "—"
        lines.append(f"| {row['num']} | {row['name']} | {row['route_state']} | {row['event_count']} | {row['last_access'] or 'لا وصول'} | {reason} |")
    lines += ["", "## فجوة فحص التشغيل", ""]
    lines.append(f"- المصادر المسجّلة غير الموجودة في اتحاد `checked_feeds` و`manual_reference`: {result['checked_missing_sources'] or 'لا شيء'}")
    lines.append(f"- أرقام زائدة في ملف الحالة: {result['checked_unknown_sources'] or 'لا شيء'}")
    lines += ["", "## قيم source غير المطابقة", ""]
    if result["unmatched_source_values"]:
        for value, count in list(result["unmatched_source_values"].items())[:40]:
            lines.append(f"- {count} × `{value}`")
    else:
        lines.append("- لا شيء")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = measure(Path(args.brain).resolve(), args.date, args.days)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, ImportError) as exc:
        print(f"✘ فشل القياس: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        out = Path(args.md_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md_table(result), encoding="utf-8")
    if not args.quiet:
        print(md_table(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
