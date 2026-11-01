#!/usr/bin/env python3
"""مشتق نقاط الخريطة — مواضع الوقائع على الخريطة التشغيلية.

القاعدة (قرار المالك 2026-11-01):
  1) إن ذكر المصدر إحداثيات في نص الواقعة → تُستعمل كما هي (`precision: exact`).
  2) إن لم يذكرها → مِرساة تقريبية داخل المنطقة نفسها من `appendices/area-coordinates.json`
     (`precision: approximate`) مع بيان أساسها — ولا يوضع الموضع في أي مكان آخر على الخريطة.
  3) فشل مغلق (رمز 2): منطقة بحرية بلا مِرساة · مِرساة على اليابسة · مِرساة خارج سطح الرسم.
  4) تحذير (رمز 1): واقعة في منطقة خارج نطاق الخريطة — تُفصح في تسمية الخريطة ولا تُرسم.

الاستخدام:
  python3 tools/derive_map_points.py --date 2026-11-01 --write
  python3 tools/derive_map_points.py --date 2026-11-01 --json /tmp/points.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANCHORS = ROOT / "appendices" / "area-coordinates.json"
LAND = Path("/home/ubuntu/seawatch/generator/data/ne_50m_land.geojson")

_DIAC = dict.fromkeys(range(0x064B, 0x0653))


class FailClosed(Exception):
    """خطأ مانع: لا يُكتب شيء ويُعاد الرمز 2."""


def norm_area(s: str) -> str:
    """توحيد اسم المنطقة: بلا تشكيل، وتوحيد الألف والياء والتاء والهمزات."""
    s = unicodedata.normalize("NFKC", str(s or "")).strip()
    s = s.translate(_DIAC)
    s = re.sub(r"[إأآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


NUM = r"(\d{1,3}(?:\.\d+)?)"
_LAT = re.compile(NUM + r"\s*(?:°|درجة)?\s*(?:(\d{1,2}(?:\.\d+)?)\s*(?:['′]|دقيقة)?\s*)?"
                        r"(?:(\d{1,2}(?:\.\d+)?)\s*(?:[\"″]|ثانية)?\s*)?\s*N(?![A-Za-z])", re.I)
_LON = re.compile(NUM + r"\s*(?:°|درجة)?\s*(?:(\d{1,2}(?:\.\d+)?)\s*(?:['′]|دقيقة)?\s*)?"
                        r"(?:(\d{1,2}(?:\.\d+)?)\s*(?:[\"″]|ثانية)?\s*)?\s*E(?![A-Za-z])", re.I)


def _val(m: re.Match) -> float:
    d = float(m.group(1))
    mi = float(m.group(2) or 0)
    se = float(m.group(3) or 0)
    return d + mi / 60.0 + se / 3600.0


def extract_coords(text: str) -> tuple[float, float] | None:
    """يستخرج أول زوج إحداثيات مذكور نصًّا (شمالًا/شرقًا)."""
    if not text:
        return None
    lm = _LAT.search(text)
    om = _LON.search(text)
    if not (lm and om):
        return None
    lat, lon = _val(lm), _val(om)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def load_land() -> list[tuple[float, float, float, float, list]]:
    """مضلعات اليابسة مع صندوق محيط لكل مضلّع (لتسريع الفحص)."""
    out = []
    if not LAND.exists():
        raise FailClosed(f"بيانات اليابسة غير موجودة: {LAND}")
    d = json.loads(LAND.read_text(encoding="utf-8"))
    for feat in d.get("features", []):
        g = feat.get("geometry") or {}
        gt, co = g.get("type"), g.get("coordinates") or []
        polys = [co] if gt == "Polygon" else (co if gt == "MultiPolygon" else [])
        for poly in polys:
            if not poly or len(poly[0]) < 3:
                continue
            ring = poly[0]
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            out.append((min(xs), min(ys), max(xs), max(ys), [poly]))
    return out


def on_land(lat: float, lon: float, land) -> bool:
    """فحص نقطة داخل مضلّع (ray casting) بعد ترشيح صندوق المحيط."""
    for x0, y0, x1, y1, polys in land:
        if not (x0 - 0.05 <= lon <= x1 + 0.05 and y0 - 0.05 <= lat <= y1 + 0.05):
            continue
        for poly in polys:
            for ring in poly:
                inside = False
                n = len(ring)
                for i in range(n):
                    xi, yi = ring[i][0], ring[i][1]
                    xj, yj = ring[(i - 1) % n][0], ring[(i - 1) % n][1]
                    if (yi > lat) != (yj > lat):
                        xint = (xj - xi) * (lat - yi) / (yj - yi) + xi
                        if lon < xint:
                            inside = not inside
                if inside:
                    return True
    return False


def load_anchors() -> tuple[dict, dict, dict]:
    d = json.loads(ANCHORS.read_text(encoding="utf-8"))
    by_key: dict[str, dict] = {}
    for a in d.get("anchors", []):
        for name in [a["area"], *(a.get("aliases") or [])]:
            by_key[norm_area(name)] = a
    excluded = {norm_area(e["area"]): e for e in d.get("excluded_areas", [])}
    return d.get("surfaces", {}), by_key, excluded


def in_surface(lat: float, lon: float, surf: dict) -> bool:
    x0, y0, x1, y1 = surf["bbox"]
    return (x0 <= lon <= x1) and (y0 <= lat <= y1)


def derive(date: str) -> dict:
    meta_p = ROOT / "web" / "meta" / f"{date}.json"
    if not meta_p.exists():
        raise FailClosed(f"ملف الواجهة غير موجود: {meta_p}")
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    surfaces, anchors, excluded = load_anchors()
    land = load_land()

    events = meta.get("event_keys") or []
    # حالة كل واقعة من سجل القطاعات الحاكم (تصنيف · تحقق · أهلية · قطاع).
    # عند غياب الملف لا تُخترع حالة، بل تُترك فارغة وتُعلن على الخريطة «حالة غير محددة».
    zstat: dict[str, dict] = {}
    zones_p = ROOT / "web" / "zones" / f"{date}.json"
    if zones_p.exists():
        try:
            _zj = json.loads(zones_p.read_text(encoding="utf-8"))
            for _ze in (_zj.get("events") or []):
                zstat[str(_ze.get("code") or "")] = {
                    "confirmation": _ze.get("confirmation"),
                    "qualifying": _ze.get("qualifying"),
                    "zone": _ze.get("zone"),
                    "class": _ze.get("class"),
                }
        except Exception:
            zstat = {}
    points, off_map, errors = [], [], []
    stats = {"events": len(events), "with_area": 0, "drawn": 0, "exact": 0, "approximate": 0,
             "off_map": 0, "excluded": 0, "confirmed": 0, "probable": 0, "unconfirmed": 0,
             "not_qualifying": 0, "status_unknown": 0}

    for e in events:
        area = (e.get("area") or "").strip()
        code = e.get("code") or ""
        if not area:
            continue
        stats["with_area"] += 1
        key = norm_area(area)
        if key in excluded:
            stats["excluded"] += 1
            continue
        a = anchors.get(key)
        if not a:
            errors.append(f"منطقة بلا مِرساة معتمدة: «{area}» ({code}) — تُضاف مِرساة موثقة في area-coordinates.json")
            continue
        text = " ".join(str(e.get(k) or "") for k in ("title", "status", "detail", "text", "note"))
        coords = extract_coords(text)
        if coords:
            lat, lon, prec, basis = coords[0], coords[1], "exact", "إحداثيات مذكورة في نص الواقعة"
        else:
            lat, lon, prec = float(a["lat"]), float(a["lon"]), "approximate"
            basis = a.get("basis", "")
        surf_name = a.get("surface", "main")
        surf = surfaces.get(surf_name)
        if surf_name != "off_map":
            if not surf:
                errors.append(f"سطح رسم غير معرَّف «{surf_name}» للمنطقة «{area}»")
                continue
            if not in_surface(lat, lon, surf):
                errors.append(f"مِرساة «{area}» ({lat}, {lon}) خارج سطح «{surf_name}» — لا تُرسم في موضع غير منطقتها")
                continue
            if on_land(lat, lon, land):
                errors.append(f"مِرساة «{area}» ({lat}, {lon}) تقع على اليابسة — تُصحَّح إلى مياه منطقتها")
                continue
            _z = zstat.get(code, {})
            points.append({"code": code, "area": area, "lat": round(lat, 4), "lon": round(lon, 4),
                           "precision": prec, "surface": surf_name, "basis": basis,
                           "source": a.get("source", ""),
                           "label": (str(e.get("title") or "").strip()[:64] or area),
                           "confirmation": _z.get("confirmation"),
                           "qualifying": _z.get("qualifying"),
                           "zone": _z.get("zone"),
                           "class": _z.get("class")})
            stats["drawn"] += 1
            stats["exact" if prec == "exact" else "approximate"] += 1
        else:
            off_map.append({"code": code, "area": area, "lat": round(lat, 4), "lon": round(lon, 4),
                            "reason": a.get("basis", "خارج نطاق الخريطة")})
            stats["off_map"] += 1

    if errors:
        raise FailClosed(" · ".join(errors))

    note = ("المواضع المعروضة مواضع وقائع اليوم على الخريطة؛ والموضع التقريبي يعني أن المصدر لم يذكر إحداثيات "
            "فوُضع داخل المنطقة نفسها لا في موضع آخر. "
            f"وتوزيع الحالة: مؤكد {stats['confirmed']} · مرجّح {stats['probable']} · "
            f"غير مؤكد مؤهل {stats['unconfirmed']} · غير مؤهل {stats['not_qualifying']} · "
            f"حالة غير محددة {stats['status_unknown']}.")
    if off_map:
        note += " ووقائع خارج نطاق الخريطة تُذكر في جدول التوزيع الجغرافي: " + \
                " · ".join(f'{o["area"]} ({o["code"]})' for o in off_map) + "."
    meta.setdefault("map", {})
    meta["map"]["points"] = points
    meta["map"]["points_note"] = note
    for _p in points:
        _q, _c = _p.get("qualifying"), (_p.get("confirmation") or "").strip().lower()
        if _q is True and _c == "confirmed":
            stats["confirmed"] += 1
        elif _q is True and _c == "probable":
            stats["probable"] += 1
        elif _q is True:
            stats["unconfirmed"] += 1
        elif _q is False:
            stats["not_qualifying"] += 1
        else:
            stats["status_unknown"] += 1
    meta["map"]["points_stats"] = stats
    if off_map:
        meta["map"]["off_map"] = off_map
    else:
        meta["map"].pop("off_map", None)
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--write", action="store_true", help="يكتب النقاط في ملف الواجهة")
    ap.add_argument("--json", help="مسار ملف للكتابة بدل ملف الواجهة")
    args = ap.parse_args()
    try:
        meta = derive(args.date)
    except FailClosed as e:
        print(f"  ✘ فشل مغلق: {e}")
        return 2
    st = meta["map"]["points_stats"]
    print(f"  ✔ نقاط الخريطة: مرسومة {st['drawn']} من {st['with_area']} واقعة بمنطقة "
          f"(دقيقة {st['exact']} · تقريبية {st['approximate']}) · خارج النطاق {st['off_map']} · مستثناة {st['excluded']}")
    dest = Path(args.json) if args.json else (ROOT / "web" / "meta" / f"{args.date}.json")
    if args.write or args.json:
        dest.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  كُتب: {dest}")
    return 1 if st["off_map"] else 0


if __name__ == "__main__":
    sys.exit(main())