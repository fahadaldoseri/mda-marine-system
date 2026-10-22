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


# ---------------------------------------------------------------- منع التصادم (ك-107 · ك-108)
DOT_R = 7.0                 # نصف قطر نقطة العلامة
MARK_SEP = 22.0             # أدنى مسافة بين مركزي علامتين: قطرا نقطتين وهامش
LABEL_GAP = 4.0             # أدنى فراغ بين تسميتين
SEA_FONT = {"lg": 19, "sm": 15}
COUNTRY_FONT = 15
PORT_FONT = 14


def _spread_markers(coords, sep=MARK_SEP, iters=80):
    """يفصل العلامات المتقاربة أو المتطابقة (ك-108): دفع متبادل حتى تتباعد مراكزها بمقدار sep.

    الترتيب ثابت: مدخلات واحدة تعطي مواضع واحدة. المتطابقتان تُزاحان بزاوية تعتمد على رقم العلامة.
    """
    pos = [[float(x), float(y)] for x, y in coords]
    n = len(pos)
    # علامة خارج إطار اللوحة (واقعة خارج النطاق) لا تُزاح ولا تُرسم لها خطوط إسناد
    inside = [0 <= p[0] <= WIDTH and 0 <= p[1] <= HEIGHT for p in pos]
    lo_x, hi_x = DOT_R + 2, WIDTH - DOT_R - 2
    lo_y, hi_y = DOT_R + 2, HEIGHT - DOT_R - 2
    for _ in range(iters):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                if not (inside[i] and inside[j]):
                    continue
                dx, dy = pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]
                d = math.hypot(dx, dy)
                if d >= sep:
                    continue
                if d < 0.01:
                    ang = j * 2.399963
                    dx, dy, d = math.cos(ang), math.sin(ang), 1.0
                push = (sep - d) / 2 + 0.25
                ux, uy = dx / d, dy / d
                pos[i][0] -= ux * push
                pos[i][1] -= uy * push
                pos[j][0] += ux * push
                pos[j][1] += uy * push
                moved = True
        for k, p in enumerate(pos):
            if inside[k]:
                p[0] = min(max(p[0], lo_x), hi_x)
                p[1] = min(max(p[1], lo_y), hi_y)
        if not moved:
            break
    return [(p[0], p[1]) for p in pos]


def _text_rect(x, y, size, text):
    w = max(len(str(text)), 1) * size * 0.5 + 6
    h = size * 1.35
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def _rects_hit(a, b, gap=LABEL_GAP):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def _place_labels(specs, avoid_pts, step=7, tries=10):
    """يزيح التسمية رأسيًا حتى لا تتقاطع مع تسمية أسبق منها ولا مع علامة (ك-107).

    specs مرتبة بالأولوية: الأولى لا تتحرك. إن لم يوجد موضع خالٍ تبقى التسمية في موضعها الأصلي.
    """
    placed = []
    avoid = [(x - 13, y - 13, x + 13, y + 13) for x, y in avoid_pts]
    out = []
    for s in specs:
        x, y = s["x"], s["y"]
        best = (x, y)
        for k in range(tries + 1):
            off = 0 if k == 0 else ((k + 1) // 2) * step * (1 if k % 2 else -1)
            r = _text_rect(x, y + off, s["size"], s["text"])
            if not any(_rects_hit(r, o) for o in placed + avoid):
                best = (x, y + off)
                break
        placed.append(_text_rect(best[0], best[1], s["size"], s["text"]))
        out.append(best)
    return out



def _esc(v):
    import html as _h
    return _h.escape(str(v if v is not None else ""), quote=True)


# ---------------------------------------------------------------- تكبير هرمز (لخريطة الشاشة العليا فقط)
ZOOM_BBOX = (54.6, 24.0, 58.0, 27.0)     # مضيق هرمز وخورفكان وشرق الفجيرة
ZOOM_WIDTH = 520.0
ZOOM_MIN_POINTS = 2                      # لا يظهر التكبير إلا إن تجمّعت وقائع فيه
ZOOM_TITLE = "تكبير: مضيق هرمز وخورفكان"


def _zoom_parts(points):
    """(مستطيل المنطقة على اللوحة الرئيسية، لوحة التكبير) أو ("", "") عند قلة الوقائع فيها.

    يُستدعى واللوحة الرئيسية هي النطاق الحالي، ويعيدها قبل الرجوع.
    """
    inside = [(i, p) for i, p in enumerate(points, start=1)
              if ZOOM_BBOX[0] <= float(p["lon"]) <= ZOOM_BBOX[2] and ZOOM_BBOX[1] <= float(p["lat"]) <= ZOOM_BBOX[3]]
    if len(inside) < ZOOM_MIN_POINTS:
        return "", ""
    x0, y0 = pt(ZOOM_BBOX[0], ZOOM_BBOX[3])
    x1, y1 = pt(ZOOM_BBOX[2], ZOOM_BBOX[1])
    rect = (f'<rect class="mp-zoomrect" x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" '
            f'rx="4" style="fill:none;stroke:var(--accent);stroke-width:1.6;stroke-dasharray:7 5"/>')
    _set_bbox(ZOOM_BBOX, ZOOM_WIDTH)
    try:
        land_svg = "".join(f'<path d="{d}"/>' for d in _land_paths())
        border_svg = "".join(f'<path d="{d}"/>' for d in _border_paths())
        grid = []
        for lon in range(math.ceil(ZOOM_BBOX[0]), math.floor(ZOOM_BBOX[2]) + 1):
            x, _ = pt(lon, ZOOM_BBOX[1])
            grid.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{HEIGHT:.0f}"/>')
        for lat in range(math.ceil(ZOOM_BBOX[1]), math.floor(ZOOM_BBOX[3]) + 1):
            _, y = pt(ZOOM_BBOX[0], lat)
            grid.append(f'<line x1="0" y1="{y:.1f}" x2="{WIDTH:.0f}" y2="{y:.1f}"/>')
        true_xy = [pt(float(p["lon"]), float(p["lat"])) for _, p in inside]
        shown = _spread_markers(true_xy, sep=2 * MARK_SEP)
        marks = []
        for (i, p), (x, y), (tx, ty) in zip(inside, shown, true_xy):
            color = KIND_COLOR.get(p.get("kind", "bg"), "var(--muted)")
            if math.hypot(x - tx, y - ty) > 3:
                marks.append(
                    f'<g class="mp-leader"><line x1="{tx:.1f}" y1="{ty:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                    f'style="stroke:var(--map-label);stroke-width:1;opacity:.75"/>'
                    f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="3" style="fill:var(--map-label)"/></g>')
            marks.append(
                f'<g class="mp-event" transform="translate({x:.1f},{y:.1f})" style="--mk:{color}">'
                f'<circle class="mp-halo" r="26"/><circle class="mp-dot" r="14"/>'
                f'<text class="mp-num" y="6" style="font-size:17px">{i}</text></g>')
        svg = (f'<svg class="hmap-zsvg" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" role="img" aria-label="{_esc(ZOOM_TITLE)}">'
               f'<rect class="mp-sea-bg" x="0" y="0" width="{WIDTH:.0f}" height="{HEIGHT:.0f}"/>'
               f'<g class="mp-grid">{"".join(grid)}</g>'
               f'<g class="mp-land" fill-rule="evenodd">{land_svg}</g>'
               f'<g class="mp-borders">{border_svg}</g>'
               f'<g class="mp-events">{"".join(marks)}</g></svg>')
    finally:
        _set_bbox(MAIN_BBOX)
    return rect, f'<div class="hmap-zoom">{svg}<div class="hz-cap">{_esc(ZOOM_TITLE)}</div></div>'



def _panel(title, points, label_prefix, caption, seas, ports, countries, grid_lon, grid_lat,
           extra_svg="", overlay=""):
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

    true_xy = [pt(float(p["lon"]), float(p["lat"])) for p in points]
    shown_xy = _spread_markers(true_xy)

    # أولوية التسميات عند التصادم: المضيق ثم الموانئ ثم البحار ثم الدول
    specs = []
    for name, lat, lon, size in seas:
        x, y = pt(lon, lat)
        specs.append({"k": "sea", "text": name, "x": x, "y": y, "size": SEA_FONT.get(size, 15), "sz": size,
                      "prio": 0 if size == "sm" else 2})
    for name, lat, lon, dx, dy in ports:
        px, py = pt(lon, lat)
        specs.append({"k": "port", "text": name, "x": px + dx, "y": py + dy + 4, "size": PORT_FONT,
                      "px": px, "py": py, "prio": 1})
    for name, lat, lon in countries:
        x, y = pt(lon, lat)
        specs.append({"k": "country", "text": name, "x": x, "y": y, "size": COUNTRY_FONT, "prio": 3})
    specs.sort(key=lambda s: s["prio"])
    for s, (nx, ny) in zip(specs, _place_labels(specs, shown_xy)):
        s["nx"], s["ny"] = nx, ny

    seas_svg = "".join(
        f'<text class="mp-sea-lbl mp-sea-{s["sz"]}" x="{s["nx"]:.1f}" y="{s["ny"]:.1f}">{s["text"]}</text>'
        for s in specs if s["k"] == "sea"
    )
    ports_svg = "".join(
        f'<g transform="translate({s["px"]:.1f},{s["py"]:.1f})">'
        f'<circle class="mp-port-dot" r="2.8"/>'
        f'<text class="mp-port-lbl" x="{s["nx"] - s["px"]:.1f}" y="{s["ny"] - s["py"]:.1f}">{s["text"]}</text></g>'
        for s in specs if s["k"] == "port"
    )
    countries_svg = "".join(
        f'<text class="mp-country" x="{s["nx"]:.1f}" y="{s["ny"]:.1f}">{s["text"]}</text>'
        for s in specs if s["k"] == "country"
    )

    marks, legend = [], []
    for i, p in enumerate(points, start=1):
        x, y = shown_xy[i - 1]
        tx, ty = true_xy[i - 1]
        color = KIND_COLOR.get(p.get("kind", "bg"), "var(--muted)")
        code = p.get("code") or ""
        ref = p.get("ref") or ""
        if math.hypot(x - tx, y - ty) > 3:
            # علامة أُزيحت عن موضعها الحقيقي: خط إسناد ونقطة صغيرة في الموضع الفعلي
            marks.append(
                f'<g class="mp-leader"><line x1="{tx:.1f}" y1="{ty:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                f'style="stroke:var(--map-label);stroke-width:1;opacity:.75"/>'
                f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="2.4" style="fill:var(--map-label)"/></g>'
            )
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
      {extra_svg}
      <g class="mp-events">{"".join(marks)}</g>
    </svg>
    {overlay}
  </div>
  {legend_html}
  {cap}
</div>"""


def build_map(points=None, caption=None, inset=None, zoom=False):
    """لوحة رئيسية + لوحة مصغّرة اختيارية لباب المندب."""
    points = points or []
    _set_bbox(MAIN_BBOX)
    zrect, zhtml = _zoom_parts(points) if zoom else ("", "")
    panels = [
        _panel(
            "خريطة الوقائع",
            points,
            "خريطة الخليج العربي ومضيق هرمز وخليج عمان مع مواقع وقائع التقرير",
            caption,
            SEAS, PORTS, COUNTRIES, GRID_LON, GRID_LAT,
            extra_svg=zrect, overlay=zhtml,
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