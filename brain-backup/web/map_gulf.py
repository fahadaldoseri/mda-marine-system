#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
خريطة تشغيلية مدمجة (SVG خالص) لنطاق التشغيل البحري.

- اللوحة الرئيسية: الخليج العربي ومضيق هرمز وخليج عمان وبحر العرب الشمالي.
- لوحة مصغّرة اختيارية: باب المندب والبحر الأحمر الجنوبي، تُبنى عند وجود وقائع هناك.

المبادئ: لا مكتبات خرائط، ولا موارد شبكية، ولا صور. جغرافية حقيقية من Natural Earth
بقصّ هندسي دقيق عبر shapely، وتُبنى وقت التوليد فتعمل بلا إنترنت وتُطبع بوضوح.
"""

import json
import math

from codes import short_code  # عرض مختصر لرموز الوقائع على الخريطة

REPORT_DATE = None
from pathlib import Path

from shapely.geometry import LineString, MultiPolygon, Polygon, box

DATA = Path(__file__).resolve().parent / "data"  # بيانات الخريطة بجوار الوحدة (مصدر واحد)

MAIN_BBOX = (46.5, 21.2, 62.0, 30.2)
INSET_BBOX_DEFAULT = (38.5, 10.5, 46.0, 20.0)
WIDTH = 1120.0
INSET_WIDTH = 760.0
TOLERANCE = 0.008

# حالة النطاق الحالي (تُضبط قبل رسم كل لوحة)
BBOX = MAIN_BBOX
MID_LAT = (BBOX[1] + BBOX[3]) / 2.0
ASPECT = math.cos(math.radians(MID_LAT))
HEIGHT = WIDTH * (BBOX[3] - BBOX[1]) / ((BBOX[2] - BBOX[0]) * ASPECT)
BOX = box(*BBOX)
_SX = _SY = 1.0

SEAS = [
    ("الخليج العربي", 26.45, 51.30, "lg"),
    ("خليج عمان", 23.95, 59.60, "lg"),
    ("بحر العرب", 21.70, 58.40, "lg"),
    ("مضيق هرمز", 26.98, 55.95, "sm"),
]

PORTS = [
    ("الكويت", 29.37, 47.98, 0, 17),
    ("بندر عباس", 27.18, 56.28, 48, -3),
    ("دبي", 25.20, 55.27, -38, 0),
    ("الدوحة", 25.30, 51.53, -34, 0),
    ("صحار", 24.34, 56.71, -48, -14),
    ("مسقط", 23.61, 58.59, 40, 0),
]

COUNTRIES = [
    ("إيران", 28.30, 53.30),
    ("السعودية", 22.55, 49.10),
    ("الإمارات", 23.45, 54.60),
    ("عُمان", 22.20, 56.30),
]

INSET_SEAS = [
    ("البحر الأحمر", 17.60, 41.20, "lg"),
    ("خليج عدن", 12.40, 46.20, "lg"),
    ("مضيق باب المندب", 12.75, 43.55, "sm"),
]

INSET_PORTS = [
    ("جيبوتي", 11.60, 43.15, -40, -10),
    ("عدن", 12.79, 44.99, 40, 0),
]

INSET_COUNTRIES = [
    ("السعودية", 18.60, 42.60),
    ("اليمن", 14.60, 45.00),
    ("إثيوبيا", 15.80, 39.60),
    ("إريتريا", 15.60, 38.90),
]

KIND_COLOR = {
    "confirm": "var(--danger)",
    "inter": "var(--info)",
    "suspect": "var(--warn)",
    "bg": "var(--muted)",
    "ok": "var(--ok)",
}

GRID_LON = [48, 52, 56, 60]
GRID_LAT = [22, 24, 26, 28]
INSET_GRID_LON = [40, 42, 44, 46]
INSET_GRID_LAT = [12, 14, 16, 18]


def _set_bbox(bbox, width=WIDTH):
    global BBOX, MID_LAT, ASPECT, HEIGHT, BOX, _SX, _SY, WIDTH
    WIDTH = width
    BBOX = bbox
    MID_LAT = (bbox[1] + bbox[3]) / 2.0
    ASPECT = math.cos(math.radians(MID_LAT))
    HEIGHT = WIDTH * (bbox[3] - bbox[1]) / ((bbox[2] - bbox[0]) * ASPECT)
    BOX = box(*bbox)
    _SX = WIDTH / ((bbox[2] - bbox[0]) * ASPECT)
    _SY = HEIGHT / (bbox[3] - bbox[1])


_set_bbox(MAIN_BBOX)


def pt(lon, lat):
    return (lon - BBOX[0]) * ASPECT * _SX, (BBOX[3] - lat) * _SY


def _load(name):
    p = DATA / f"{name}.geojson"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _ring_d(ring):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(c[0], c[1]) for c in ring.coords))
    return f"M{pts}Z"


def _geom_paths(geom):
    if geom.is_empty:
        return []
    geoms = [geom] if isinstance(geom, Polygon) else (list(geom.geoms) if isinstance(geom, MultiPolygon) else [])
    out = []
    for g in geoms:
        if not isinstance(g, Polygon):
            continue
        d = _ring_d(g.exterior)
        for hole in g.interiors:
            d += _ring_d(hole)
        if d:
            out.append(d)
    return out


_LAND_CACHE = {}
_BORDER_CACHE = {}


def _land_paths():
    key = BBOX
    if key in _LAND_CACHE:
        return _LAND_CACHE[key]
    land = _load("ne_50m_land")
    paths = []
    if land:
        for feat in land["features"]:
            g = feat.get("geometry") or {}
            t = g.get("type")
            geoms = []
            if t == "Polygon":
                geoms = [Polygon(g["coordinates"][0], g["coordinates"][1:])]
            elif t == "MultiPolygon":
                geoms = [Polygon(p[0], p[1:]) for p in g["coordinates"]]
            for poly in geoms:
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_empty or not poly.intersects(BOX):
                    continue
                paths.extend(_geom_paths(poly.intersection(BOX).simplify(TOLERANCE, preserve_topology=True)))
    _LAND_CACHE[key] = paths
    return paths


def _border_paths():
    key = BBOX
    if key in _BORDER_CACHE:
        return _BORDER_CACHE[key]
    borders = _load("ne_50m_admin_0_boundary_lines_land")
    paths = []
    if borders:
        for feat in borders["features"]:
            g = feat.get("geometry") or {}
            t = g.get("type")
            lines = [g["coordinates"]] if t == "LineString" else (g["coordinates"] if t == "MultiLineString" else [])
            for line in lines:
                ls = LineString(line)
                if not ls.intersects(BOX):
                    continue
                piece = ls.intersection(BOX).simplify(TOLERANCE)
                parts = [piece] if piece.geom_type == "LineString" else list(getattr(piece, "geoms", []))
                for part in parts:
                    if len(part.coords) < 2:
                        continue
                    coords = [pt(c[0], c[1]) for c in part.coords]
                    paths.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in coords))
    _BORDER_CACHE[key] = paths
    return paths


def _panel(title, points, label_prefix, caption, seas, ports, countries, grid_lon, grid_lat):
    land_svg = "".join(f'<path d="{d}"/>' for d in _land_paths())
    border_svg = "".join(f'<path d="{d}"/>' for d in _border_paths())

    grid_lines, grid_labels = [], []
    for lon in grid_lon:
        x, _ = pt(lon, BBOX[1])
        grid_lines.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{HEIGHT:.0f}"/>')
        grid_labels.append(f'<text class="mp-grid-lbl" x="{x+5:.1f}" y="{HEIGHT-7:.0f}">{lon}°E</text>')
    for lat in grid_lat:
        _, y = pt(BBOX[0], lat)
        grid_lines.append(f'<line x1="0" y1="{y:.1f}" x2="{WIDTH:.0f}" y2="{y:.1f}"/>')
        grid_labels.append(f'<text class="mp-grid-lbl" x="7" y="{y-6:.1f}" text-anchor="start">{lat}°N</text>')

    seas_svg = "".join(
        f'<text class="mp-sea-lbl mp-sea-{size}" x="{pt(lon, lat)[0]:.1f}" y="{pt(lon, lat)[1]:.1f}">{name}</text>'
        for name, lat, lon, size in seas
    )
    ports_svg = "".join(
        f'<g transform="translate({pt(lon, lat)[0]:.1f},{pt(lon, lat)[1]:.1f})">'
        f'<circle class="mp-port-dot" r="2.8"/><text class="mp-port-lbl" x="{dx}" y="{dy+4}">{name}</text></g>'
        for name, lat, lon, dx, dy in ports
    )
    countries_svg = "".join(
        f'<text class="mp-country" x="{pt(lon, lat)[0]:.1f}" y="{pt(lon, lat)[1]:.1f}">{name}</text>'
        for name, lat, lon in countries
    )

    marks, legend = [], []
    for i, p in enumerate(points, start=1):
        x, y = pt(float(p["lon"]), float(p["lat"]))
        color = KIND_COLOR.get(p.get("kind", "bg"), "var(--muted)")
        code = p.get("code") or ""
        ref = p.get("ref") or ""
        marks.append(
            f'<g class="mp-event" transform="translate({x:.1f},{y:.1f})" style="--mk:{color}">'
            f'<circle class="mp-halo" r="14"/><circle class="mp-dot" r="7"/>'
            f'<text class="mp-num" y="3.7">{i}</text></g>'
        )
        bits = [f'<span class="lg-txt">{p.get("label","")}</span>']
        if code:
            bits.append(f'<bdi class="bidi ev-code">{short_code(code, REPORT_DATE)}</bdi>')
        if ref:
            bits.append(f'<bdi class="bidi">{ref}</bdi>')
        legend.append(f'<li><span class="lg-num" style="--mk:{color}">{i}</span>{" ".join(bits)}</li>')

    legend_html = f'<ol class="map-legend">{"".join(legend)}</ol>' if legend else ""
    cap = f'<p class="src-note">{caption}</p>' if caption else ""
    return f"""<div class="map-panel">
  <h3>{title}</h3><p class="blk-lede">مواقع الوقائع داخل نطاق التقرير.</p>
  <div class="map-wrap">
    <svg class="map-svg" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" role="img"
         aria-label="{label_prefix}">
      <rect class="mp-sea-bg" x="0" y="0" width="{WIDTH:.0f}" height="{HEIGHT:.0f}"/>
      <g class="mp-grid">{"".join(grid_lines)}</g>
      <g class="mp-land" fill-rule="evenodd">{land_svg}</g>
      <g class="mp-borders">{border_svg}</g>
      <g class="mp-places">{countries_svg}{ports_svg}{seas_svg}</g>
      <g class="mp-grid-labels">{"".join(grid_labels)}</g>
      <g class="mp-events">{"".join(marks)}</g>
    </svg>
  </div>
  {legend_html}
  {cap}
</div>"""


def build_map(points=None, caption=None, inset=None):
    """لوحة رئيسية + لوحة مصغّرة اختيارية لباب المندب."""
    points = points or []
    _set_bbox(MAIN_BBOX)
    panels = [
        _panel(
            "خريطة الوقائع",
            points,
            "خريطة الخليج العربي ومضيق هرمز وخليج عمان مع مواقع وقائع التقرير",
            caption,
            SEAS, PORTS, COUNTRIES, GRID_LON, GRID_LAT,
        )
    ]

    if isinstance(inset, dict) and (inset.get("points") or inset.get("force")):
        _set_bbox(tuple(inset.get("bbox") or INSET_BBOX_DEFAULT), INSET_WIDTH)
        panels.append(
            _panel(
                inset.get("title") or "اللوحة المصغّرة — باب المندب والبحر الأحمر",
                inset.get("points") or [],
                "خريطة باب المندب والبحر الأحمر الجنوبي مع مواقع الوقائع",
                inset.get("caption"),
                INSET_SEAS, INSET_PORTS, INSET_COUNTRIES, INSET_GRID_LON, INSET_GRID_LAT,
            )
        )
    _set_bbox(MAIN_BBOX)

    note = (
        '<p class="map-keys">السواحل والجزر والحدود: بيانات Natural Earth. '
        'الشبكة: خطوط الطول والعرض. العلامات المرقمة: وقائع هذا التقرير.</p>'
    )
    return f'<div class="viz map-viz reveal">{"".join(panels)}{note}</div>'


if __name__ == "__main__":
    pts = [
        {"label": "هجوم داخل مضيق هرمز", "ref": "#164", "code": "MN-2026-10-11-01",
         "lat": 26.50, "lon": 56.50, "kind": "confirm"},
        {"label": "واقعة قرب مرسى صحار", "ref": "#165", "code": "MN-2026-10-11-02",
         "lat": 24.28, "lon": 56.95, "kind": "confirm"},
    ]
    out = build_map(pts, "المصدر: جدول التوزيع الجغرافي للوقائع.", inset={"points": []})
    Path("/tmp/map_test.svg").write_text(out, encoding="utf-8")
    print("svg bytes:", len(out))