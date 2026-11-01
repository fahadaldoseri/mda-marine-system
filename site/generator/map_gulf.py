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

from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, box, shape

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

# موانئ إضافية تظهر في خريطة الشاشة العليا فقط، فلا تتغير خريطة الطباعة المعتمدة
SCREEN_ONLY_PORTS = [
    ("المنامة", 26.23, 50.58, 0, -17),
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


def status_of(p: dict) -> tuple:
    """(مفتاح اللون، التسمية العربية، التسمية الإنجليزية) لحالة الواقعة على الخريطة.

    المصدر الحاكم: حقلا confirmation وqualifying في سجل القطاعات؛ ولا تُخترع حالة
    عند غيابهما، بل تُعلن «حالة غير محددة» بدل إظهار لون محايد بلا معنى.
    """
    conf = (p.get("confirmation") or "").strip().lower()
    qual = p.get("qualifying")
    if qual is True and conf == "confirmed":
        return "confirm", "مؤكد", "confirmed"
    if qual is True and conf == "probable":
        return "inter", "مرجّح", "probable"
    if qual is True:
        return "suspect", "غير مؤكد مؤهل", "unconfirmed (qualifying)"
    if qual is False:
        return "bg", "غير مؤهل — لا يُحتسب", "not qualifying"
    return "bg", "حالة غير محددة", "status not stated"

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
_MARITIME_CACHE = {}


def _line_paths(geom):
    """حوّل LineString/MultiLineString إلى مسارات SVG بعد القص بالنطاق الحالي."""
    if geom.is_empty:
        return []
    lines = [geom] if isinstance(geom, LineString) else (
        list(geom.geoms) if isinstance(geom, MultiLineString) else [])
    out = []
    for line in lines:
        if not isinstance(line, LineString) or len(line.coords) < 2:
            continue
        out.append("M" + "L".join(f"{pt(c[0], c[1])[0]:.1f},{pt(c[0], c[1])[1]:.1f}" for c in line.coords))
    return out


def _maritime_boundary_paths():
    """حدود بحرية مصدرها Marine Regions، لا تُخلط مع حدود اليابسة."""
    key = BBOX
    if key in _MARITIME_CACHE:
        return _MARITIME_CACHE[key]
    data = _load("marine_boundaries")
    paths = []
    if data:
        for feat in data.get("features", []):
            try:
                geom = shape(feat.get("geometry") or {})
                if geom.is_empty or not geom.intersects(BOX):
                    continue
                paths.extend(_line_paths(geom.intersection(BOX).simplify(TOLERANCE)))
            except Exception:
                continue
    _MARITIME_CACHE[key] = paths
    return paths


# هندسة مسارات مضيق هرمز من المخطط الرسمي المحفوظ في imo-tss-derived.json.
# الإحداثيات تمثل خطّي المسارين داخل نطاق Λ؛ لا تُسمّى دخولًا أو خروجًا.
ROUTES = {
    "north": [
        (56.381, 26.554), (56.406, 26.560), (56.430, 26.568),
        (56.455, 26.575), (56.480, 26.581), (56.505, 26.581),
        (56.530, 26.581), (56.555, 26.582), (56.580, 26.578),
        (56.604, 26.559), (56.629, 26.526), (56.654, 26.504),
    ],
    "south": [
        (56.381, 26.534), (56.406, 26.539), (56.430, 26.546),
        (56.455, 26.555), (56.480, 26.565), (56.505, 26.566),
        (56.530, 26.566), (56.555, 26.566), (56.580, 26.553),
        (56.604, 26.527), (56.629, 26.496), (56.654, 26.487),
    ],
}

# حدود منطقة الملاحة الساحلية المتقطعة كما تُقرأ من القناع الرسمي (mask.png)
# بعد تطبيق معايرة المحاور في imo-tss-lanes.json.
INSHORE_ZONE = [
    [(56.342, 26.590), (56.442, 26.620), (56.605, 26.620), (56.691, 26.509)],
    [(56.363, 26.447), (56.300, 26.350), (56.219, 26.243)],
    [(56.595, 26.447), (56.565, 26.395), (56.535, 26.349)],
]


def _route_d(coords):
    return "M" + "L".join(f"{pt(lon, lat)[0]:.1f},{pt(lon, lat)[1]:.1f}" for lon, lat in coords)


def _arrow_d(start, end, width=12.0, head=18.0):
    """محيط سهم اتجاه واحد، دون تسمية دخول/خروج، وفق اتجاه السهم في المخطط."""
    x1, y1 = pt(*start)
    x2, y2 = pt(*end)
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    bx, by = x2 - ux * head, y2 - uy * head
    tx, ty = x1 + ux * 8.0, y1 + uy * 8.0
    points = [
        (tx + nx * width / 2, ty + ny * width / 2),
        (bx + nx * width / 2, by + ny * width / 2),
        (bx + nx * width, by + ny * width),
        (x2, y2),
        (bx - nx * width, by - ny * width),
        (bx - nx * width / 2, by - ny * width / 2),
        (tx - nx * width / 2, ty - ny * width / 2),
    ]
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in points) + "Z"


def _routing_svg():
    """تمثيل شاشة مكبّرة لنظام الفصل الرسمي؛ ليس تعليمات ملاحة تشغيلية."""
    band = ROUTES["north"] + list(reversed(ROUTES["south"]))
    band_d = "M" + "L".join(f"{pt(lon, lat)[0]:.1f},{pt(lon, lat)[1]:.1f}" for lon, lat in band) + "Z"
    separator = [
        ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        for a, b in zip(ROUTES["north"], ROUTES["south"])
    ]
    paths = [
        f'<path class="mp-tss-band" d="{band_d}" style="fill:#ee7be8;fill-opacity:.22;stroke:none"/>',
        f'<path class="mp-route mp-route-north" d="{_route_d(ROUTES["north"])}" style="fill:none;stroke:#ff9af5;stroke-width:2.8;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke"/>',
        f'<path class="mp-route mp-route-south" d="{_route_d(ROUTES["south"])}" style="fill:none;stroke:#ff9af5;stroke-width:2.8;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke"/>',
        f'<path class="mp-route-separator" d="{_route_d(separator)}" style="fill:none;stroke:#f8cdf3;stroke-width:1.2;stroke-dasharray:5 4;vector-effect:non-scaling-stroke"/>',
    ]
    for i, coords in enumerate(INSHORE_ZONE, start=1):
        paths.append(
            f'<path class="mp-inshore-boundary mp-inshore-{i}" d="{_route_d(coords)}" '
            'style="fill:none;stroke:#ff4ef4;stroke-width:1.6;stroke-dasharray:6 5;vector-effect:non-scaling-stroke"/>'
        )
    arrows = [
        _arrow_d((56.535, 26.581), (56.415, 26.558)),  # السهم العلوي غربًا كما في المخطط
        _arrow_d((56.415, 26.538), (56.535, 26.563)),  # السهم السفلي شرقًا كما في المخطط
    ]
    paths.extend(
        f'<path class="mp-route-arrow mp-route-arrow-{i}" d="{d}" style="fill:none;stroke:#ff9af5;stroke-width:1.7;stroke-linejoin:round;vector-effect:non-scaling-stroke"/>'
        for i, d in enumerate(arrows, start=1)
    )
    return f'<g class="mp-routes" aria-label="مسارات إرشادية (تمثيل تخطيطي)">{"".join(paths)}</g>'


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
ZOOM_BBOX = (54.6, 23.4, 58.0, 27.0)     # مضيق هرمز وخورفكان وشرق الفجيرة
ZOOM_WIDTH = 520.0
ZOOM_TITLE = "تكبير: مضيق هرمز وخورفكان"
def _zoom_parts(points):
    """(مستطيل المنطقة على اللوحة الرئيسية، لوحة تكبير ثابتة لمضيق هرمز).

    اللوحة لا تعتمد على وجود واقعة مكانية؛ فهي سياق جغرافي وتكبير للهندسة
    نفسها، بينما تُضاف العلامات فقط عندما تحمل الواجهة إحداثيات مثبتة.
    """
    inside = [(i, p) for i, p in enumerate(points, start=1)
              if ZOOM_BBOX[0] <= float(p["lon"]) <= ZOOM_BBOX[2] and ZOOM_BBOX[1] <= float(p["lat"]) <= ZOOM_BBOX[3]]
    x0, y0 = pt(ZOOM_BBOX[0], ZOOM_BBOX[3])
    x1, y1 = pt(ZOOM_BBOX[2], ZOOM_BBOX[1])
    rect = (f'<rect class="mp-zoomrect" x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" '
            f'rx="4" style="fill:none;stroke:var(--accent);stroke-width:1.6;stroke-dasharray:7 5"/>')
    _set_bbox(ZOOM_BBOX, ZOOM_WIDTH)
    try:
        land_svg = "".join(
            f'<path d="{d}" style="fill:#264b68;stroke:#78b7cc;stroke-width:1.2;vector-effect:non-scaling-stroke"/>'
            for d in _land_paths())
        border_svg = "".join(
            f'<path d="{d}" style="fill:none;stroke:#73adc6;stroke-width:.9;stroke-dasharray:6 5;vector-effect:non-scaling-stroke"/>'
            for d in _border_paths())
        maritime_svg = "".join(
            f'<path class="mp-maritime-boundary" d="{d}" style="fill:none;stroke:#b6e7ff;stroke-width:1.5;stroke-dasharray:2 4;vector-effect:non-scaling-stroke"/>'
            for d in _maritime_boundary_paths())
        grid = []
        for lon in range(math.ceil(ZOOM_BBOX[0]), math.floor(ZOOM_BBOX[2]) + 1):
            x, _ = pt(lon, ZOOM_BBOX[1])
            grid.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{HEIGHT:.0f}" style="stroke:#23445f;stroke-width:.7;vector-effect:non-scaling-stroke"/>')
        for lat in range(math.ceil(ZOOM_BBOX[1]), math.floor(ZOOM_BBOX[3]) + 1):
            _, y = pt(ZOOM_BBOX[0], lat)
            grid.append(f'<line x1="0" y1="{y:.1f}" x2="{WIDTH:.0f}" y2="{y:.1f}" style="stroke:#23445f;stroke-width:.7;vector-effect:non-scaling-stroke"/>')
        true_xy = [pt(float(p["lon"]), float(p["lat"])) for _, p in inside]
        shown = _spread_markers(true_xy, sep=2.6 * MARK_SEP)
        marks = []
        for (i, p), (x, y), (tx, ty) in zip(inside, shown, true_xy):
            color = KIND_COLOR.get(p.get("kind") or status_of(p)[0], "var(--muted)")
            if math.hypot(x - tx, y - ty) > 3:
                marks.append(
                    f'<g class="mp-leader"><line x1="{tx:.1f}" y1="{ty:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                    f'style="stroke:var(--map-label);stroke-width:1;opacity:.75"/>'
                    f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="3" style="fill:var(--map-label)"/></g>')
            marks.append(
                f'<g class="mp-event{" mp-approx" if p.get("precision") == "approximate" else ""}" transform="translate({x:.1f},{y:.1f})" style="--mk:{color}">'
                f'<circle class="mp-halo" r="26" style="fill:var(--mk);opacity:.22"/>'
                f'<circle class="mp-dot" r="14" style="{_dot_style(p)}"/>'
                f'<text class="mp-num" y="6" style="font-size:17px;fill:#fff;font-weight:600;text-anchor:middle">{i}</text></g>')
        # مواضع مقاسة مسبقًا: تترك حيزًا فوق نطاق Λ وتفصل أسماء الموانئ عن حدوده.
        place_labels = [
            ("إيران", 26.78, 56.28, "mp-country"),
            ("عُمان", 24.08, 56.62, "mp-country"),
            ("الإمارات", 25.04, 55.34, "mp-country"),
            ("مضيق هرمز", 26.88, 55.72, "mp-sea-lbl mp-sea-sm"),
            ("الخليج العربي", 26.96, 54.98, "mp-sea-lbl mp-sea-lg"),
            ("خليج عمان", 23.78, 57.28, "mp-sea-lbl mp-sea-lg"),
            ("خصب", 26.18, 56.08, "mp-port-lbl"),
            ("الفجيرة", 25.16, 56.46, "mp-port-lbl"),
        ]
        label_svg = "".join(
            f'<text data-map-label="1" class="{cls}" x="{pt(lon, lat)[0]:.1f}" y="{pt(lon, lat)[1]:.1f}" '
            f'style="fill:{"#bce8ff" if "country" in cls else "#b6e7ff" if "sea" in cls else "#e4f6ff"};font-size:{"14" if "country" in cls else "16" if "sea" in cls else "13"}px;font-weight:600;paint-order:stroke;stroke:#081d31;stroke-width:3px;stroke-linejoin:round;direction:rtl;unicode-bidi:isolate">{_esc(text)}</text>'
            for text, lat, lon, cls in place_labels)
        svg = (f'<svg class="hmap-zsvg" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" role="img" aria-label="{_esc(ZOOM_TITLE)}">'
               '<desc>تكبير للخريطة الرئيسية؛ تفاصيل نطاق العرض في وصف البطاقة.</desc>'
               f'<rect class="mp-sea-bg" style="fill:#081d31" x="0" y="0" width="{WIDTH:.0f}" height="{HEIGHT:.0f}"/>'
               f'<g class="mp-grid">{"".join(grid)}</g>'
               f'<g class="mp-land" fill-rule="evenodd">{land_svg}</g>'
               f'<g class="mp-borders">{border_svg}</g>'
               f'<g class="mp-maritime-boundaries">{maritime_svg}</g>'
               f'{_routing_svg()}'
               f'<g class="mp-places">{label_svg}</g>'
               f'{_frame_svg()}'
               f'<g class="mp-events">{"".join(marks)}</g></svg>')
    finally:
        _set_bbox(MAIN_BBOX)
    route_key = (
        '<div class="hmap-route-key" aria-label="مفتاح نظام فصل الملاحة المعتمد">'
        '<strong>نظام فصل الملاحة المعتمد — <bdi dir="ltr">IMO 1968</bdi></strong>'
        '<span><i class="rk-sw rk-lane" role="presentation"></i>مساران داخل النطاق الرسمي · '
        '<i class="rk-sw rk-separator" role="presentation"></i>خط فصل</span>'
        '<span><i class="rk-sw rk-inshore" role="presentation"></i>حدود منطقة الملاحة الساحلية · '
        '<i class="rk-sw rk-arrow" role="presentation"></i>سهم اتجاه · تمثيل توضيحي فقط</span>'
        '</div>'
    )
    return rect, f'<div class="hmap-zoom">{svg}{route_key}<div class="hz-cap">{_esc(ZOOM_TITLE)}</div></div>'


MAP_KEY_STYLE = """<style>
.map-key{list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 22px;margin:14px 0 0;padding:0}
.map-key li{display:flex;align-items:center;gap:8px;font-size:12.5px;line-height:1.55;color:#c3d2e6;margin:0}
.map-key .lg-sw{width:24px;height:14px;border-radius:3px;display:inline-block;flex:0 0 auto;border:1px solid #42677f}
.map-key .sw-land{background:#264b68;border-color:#78b7cc}
.map-key .sw-sea{background:#081d31}
.map-key .sw-border{height:0;border:0;border-top:2px dashed #73adc6}
.map-key .sw-maritime-boundary{height:0;border:0;border-top:2px dashed #b6e7ff}
.map-key .sw-grid{height:0;border:0;border-top:1px solid #9ac7da}
.map-key .sw-port{width:14px;height:14px;border:0;position:relative}
.map-key .sw-port:after{content:"";position:absolute;inset:4px;background:#e4f6ff;border-radius:50%}
.map-key .sw-strait{width:auto;height:auto;padding:0 5px;border:1px solid #b6e7ff;border-radius:999px;color:#b6e7ff}
.map-key .sw-none{border:1px dashed #7895b0;background:transparent}
.map-key .sw-mark-confirm{background:#e2554f;border-color:#f0a9a5}
.map-key .sw-mark-prob{background:#e7b23c;border-color:#f2d79a}
.map-key .sw-mark-unco{background:#4a7fa8;border-color:#9dc3dd}
.map-key .sw-mark-none{background:transparent;border:2px solid #8aa2ba}
.map-key .sw-mark-approx{width:14px;height:14px;border-radius:50%;background:transparent;border:2px dashed #cfe3f2;margin:0 5px}
.map-key .sw-mark-exact{width:14px;height:14px;border-radius:50%;background:#e2554f;border:2px solid #081d31}
.map-legend .lg-st{border:1px solid #42677f;border-radius:999px;padding:0 6px;font-size:11.5px;color:#cfe3f2;white-space:nowrap}
.map-legend .lg-st.st-confirm{border-color:#e2554f;color:#f4b8b5}
.map-legend .lg-st.st-inter{border-color:#e7b23c;color:#f2d79a}
.map-legend .lg-st.st-suspect{border-color:#4a7fa8;color:#bcd8ec}
.map-legend .lg-prec{color:#9fb6cb;font-size:11.5px;white-space:nowrap}
.map-key .lg-none{grid-column:1 / -1;color:#c3e6f4}
@media (max-width:760px){.map-key{grid-template-columns:minmax(0,1fr)}}
.hmap-route-key{display:grid;gap:2px;padding:7px 10px 8px;border-top:1px solid #28405f;background:#0c1626;color:#c3d2e6;font-size:11.5px;line-height:1.45}
.hmap-route-key strong{color:#e9f0f9;font-weight:700}
.hmap-route-key span{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.hmap-route-key .rk-sw{display:inline-block;width:22px;height:0;flex:0 0 auto;border-top:2px solid #ff9af5}
.hmap-route-key .rk-separator{border-top-color:#f8cdf3;border-top-style:dashed;border-top-width:1px}
.hmap-route-key .rk-inshore{border-top-color:#ff4ef4;border-top-style:dashed}
.hmap-route-key .rk-arrow{width:15px;border-top-color:#ff9af5;transform:rotate(-18deg)}
@media (max-width:760px){.hmap-route-key{font-size:11px;padding-inline:8px}}
</style>"""


def _panel(title, points, label_prefix, caption, seas, ports, countries, grid_lon, grid_lat,
           extra_svg="", overlay=""):
    land_svg = "".join(
        f'<path d="{d}" style="fill:#264b68;stroke:#78b7cc;stroke-width:1.2;vector-effect:non-scaling-stroke"/>'
        for d in _land_paths())
    border_svg = "".join(
        f'<path d="{d}" style="fill:none;stroke:#73adc6;stroke-width:.9;stroke-dasharray:6 5;vector-effect:non-scaling-stroke"/>'
        for d in _border_paths())

    grid_lines, grid_labels = [], []
    for lon in grid_lon:
        x, _ = pt(lon, BBOX[1])
        grid_lines.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{HEIGHT:.0f}" style="stroke:#23445f;stroke-width:.7;vector-effect:non-scaling-stroke"/>')
        grid_labels.append(f'<text class="mp-grid-lbl" x="{x+5:.1f}" y="{HEIGHT-7:.0f}" style="fill:#9ac7da">{lon}°E</text>')
    for lat in grid_lat:
        _, y = pt(BBOX[0], lat)
        grid_lines.append(f'<line x1="0" y1="{y:.1f}" x2="{WIDTH:.0f}" y2="{y:.1f}" style="stroke:#23445f;stroke-width:.7;vector-effect:non-scaling-stroke"/>')
        grid_labels.append(f'<text class="mp-grid-lbl" x="7" y="{y-6:.1f}" text-anchor="start" style="fill:#9ac7da">{lat}°N</text>')

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
        f'<text class="mp-sea-lbl mp-sea-{s["sz"]}" x="{s["nx"]:.1f}" y="{s["ny"]:.1f}" '
        f'style="fill:#b6e7ff;paint-order:stroke;stroke:#081d31;stroke-width:3px;stroke-linejoin:round">{s["text"]}</text>'
        for s in specs if s["k"] == "sea"
    )
    ports_svg = "".join(
        f'<g transform="translate({s["px"]:.1f},{s["py"]:.1f})">'
        f'<circle class="mp-port-dot" r="2.8" style="fill:#e4f6ff"/>'
        f'<text class="mp-port-lbl" x="{s["nx"] - s["px"]:.1f}" y="{s["ny"] - s["py"]:.1f}" '
        f'style="fill:#e4f6ff;paint-order:stroke;stroke:#081d31;stroke-width:3px;stroke-linejoin:round">{s["text"]}</text></g>'
        for s in specs if s["k"] == "port"
    )
    countries_svg = "".join(
        f'<text class="mp-country" x="{s["nx"]:.1f}" y="{s["ny"]:.1f}" '
        f'style="fill:#bce8ff;paint-order:stroke;stroke:#081d31;stroke-width:3px;stroke-linejoin:round">{s["text"]}</text>'
        for s in specs if s["k"] == "country"
    )

    marks, legend = [], []
    for i, p in enumerate(points, start=1):
        x, y = shown_xy[i - 1]
        tx, ty = true_xy[i - 1]
        st_key, st_ar, st_en = status_of(p)
        color = KIND_COLOR.get(p.get("kind") or st_key, "var(--muted)")
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
            f'<g class="mp-event{" mp-approx" if p.get("precision") == "approximate" else ""}" transform="translate({x:.1f},{y:.1f})" style="--mk:{color}">'
            f'<circle class="mp-halo" r="14" style="fill:var(--mk);opacity:.22"/>'
            f'<circle class="mp-dot" r="7" style="{_dot_style(p)}"/>'
            f'<text class="mp-num" y="3.7" style="fill:#fff;font-size:9.5px;font-weight:600;text-anchor:middle">{i}</text></g>'
        )
        txt = (p.get("label") or p.get("area") or "").strip()
        bits = [f'<span class="lg-txt">{_esc(txt)}</span>',
                f'<span class="lg-st st-{st_key}">{st_ar}</span>',
                f'<span class="lg-prec">{"موضع تقريبي" if p.get("precision") == "approximate" else "إحداثيات مذكورة"}</span>']
        if code:
            bits.append(f'<bdi class="bidi ev-code">{short_code(code, REPORT_DATE)}</bdi>')
        if ref:
            bits.append(f'<bdi class="bidi">{_esc(ref)}</bdi>')
        legend.append(f'<li><span class="lg-num" style="--mk:{color}">{i}</span>{" ".join(bits)}</li>')

    legend_html = f'<ol class="map-legend">{"".join(legend)}</ol>' if legend else ""
    cap = f'<p class="src-note">{caption}</p>' if caption else ""
    if points:
        _ap_n = sum(1 for p in points if p.get("precision") == "approximate")
        lede = (f"مواقع {len(points)} واقعة داخل نطاق التقرير؛ " +
                (f"منها {_ap_n} بموضع تقريبي داخل المنطقة نفسها لأن المصدر لم يذكر إحداثيات." if _ap_n else
                 "وجميعها بإحداثيات مذكورة في المصادر."))
    else:
        lede = ("لوحة سياق جغرافي: السواحل والمضيق والموانئ وشبكة خطوط الطول والعرض. "
                "لا تُرسم مواقع وقائع لعدم ثبوت إحداثيات في المصادر.")
    desc_text = (_esc(label_prefix) if points else
                 _esc("خريطة سياق جغرافي: السواحل والمضيق والموانئ وشبكة خطوط الطول والعرض؛ بلا علامات وقائع."))
    layers = (
        '<li><span class="lg-sw sw-land" role="presentation"></span>اليابسة</li>'
        '<li><span class="lg-sw sw-sea" role="presentation"></span>البحر</li>'
        '<li><span class="lg-sw sw-border" role="presentation"></span>حدود الدول</li>'
        '<li><span class="lg-sw sw-maritime-boundary" role="presentation"></span>حدود بحرية مرجعية (غير سيادية)</li>'
        '<li><span class="lg-sw sw-grid" role="presentation"></span>شبكة خطوط الطول والعرض</li>'
        '<li><span class="lg-sw sw-port" role="presentation"></span>نقطة مدينة أو ميناء (تقديرية)</li>'
        '<li><span class="lg-sw sw-strait" role="presentation"></span>تسمية بحر أو مضيق</li>'
    )
    if points:
        has_conf = any(status_of(p)[0] == "confirm" for p in points)
        has_prob = any(status_of(p)[0] == "inter" for p in points)
        has_unco = any(status_of(p)[0] == "suspect" for p in points)
        has_ntq = any(status_of(p)[0] == "bg" for p in points)
        has_approx = any(p.get("precision") == "approximate" for p in points)
        has_exact = any(p.get("precision") != "approximate" for p in points)
        marks_key = []
        if has_conf:
            marks_key.append('<li><span class="lg-sw sw-mark-confirm" role="presentation"></span>واقعة مؤكدة على السفن أو ملاحتها</li>')
        if has_prob:
            marks_key.append('<li><span class="lg-sw sw-mark-prob" role="presentation"></span>واقعة مرجّحة</li>')
        if has_unco:
            marks_key.append('<li><span class="lg-sw sw-mark-unco" role="presentation"></span>غير مؤكدة مؤهلة — تُذكر ولا ترفع المستوى وحدها</li>')
        if has_ntq:
            marks_key.append('<li><span class="lg-sw sw-mark-none" role="presentation"></span>بلاغ غير مؤهل — يُذكر ولا يُحتسب</li>')
        if has_approx:
            marks_key.append('<li><span class="lg-sw sw-mark-approx" role="presentation"></span>حلقة مفرّغة: موضع تقريبي داخل المنطقة نفسها (المصدر لم يذكر إحداثيات)</li>')
        if has_exact:
            marks_key.append('<li><span class="lg-sw sw-mark-exact" role="presentation"></span>علامة مصمتة: إحداثيات مذكورة في المصدر</li>')
        layers = "".join(marks_key) + layers
    else:
        layers += ('<li class="lg-none"><span class="lg-sw sw-none" role="presentation"></span>'
                   'لا علامات وقائع — لا إحداثيات مثبتة في المصادر</li>')
    key_html = ('<ul class="map-key mp-key" aria-label="مفتاح طبقات الخريطة ورموزها">' + layers + '</ul>')
    route_svg = _routing_svg() if BBOX == ZOOM_BBOX else ""
    maritime_svg = "".join(
        f'<path class="mp-maritime-boundary" d="{d}" style="fill:none;stroke:#b6e7ff;stroke-width:1.5;stroke-dasharray:2 4;vector-effect:non-scaling-stroke"/>'
        for d in _maritime_boundary_paths())
    return MAP_KEY_STYLE + f"""<div class="map-panel">
  <h3>{title}</h3><p class="blk-lede">{lede}</p>
  <div class="map-wrap">
    <svg class="map-svg" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" role="img"
         aria-label="{label_prefix}">
      <title>{_esc(title)}</title>
      <desc>{desc_text}</desc>
      <rect class="mp-sea-bg" style="fill:#081d31" x="0" y="0" width="{WIDTH:.0f}" height="{HEIGHT:.0f}"/>
      <g class="mp-grid">{"".join(grid_lines)}</g>
      <g class="mp-land" fill-rule="evenodd">{land_svg}</g>
      <g class="mp-borders">{border_svg}</g>
      <g class="mp-maritime-boundaries">{maritime_svg}</g>
      <g class="mp-places">{countries_svg}{ports_svg}{seas_svg}</g>
      <g class="mp-grid-labels">{"".join(grid_labels)}</g>
      {route_svg}
      {extra_svg}
      {_frame_svg()}
      <g class="mp-events">{"".join(marks)}</g>
    </svg>
    {overlay}
  </div>
  {legend_html}
  {key_html}
  {cap}
</div>"""



def _frame_svg() -> str:
    """إطار خرائطي: مقياس رسم بالميل البحري والكيلومتر + سهم الشمال + إفصاح المرجع.

    المقياس محسوب من عرض النطاق عند متوسط خط العرض (إسقاط مستوٍ محلي على WGS 84)،
    ويُعلن كتقدير للسياق لا كقياس ملاحي معتمد.
    """
    lat_mid = (BBOX[1] + BBOX[3]) / 2.0
    km_per_unit = ((BBOX[2] - BBOX[0]) / WIDTH) * 111.32 * math.cos(math.radians(lat_mid))
    target = None
    for cand in (10, 20, 25, 50, 100, 200, 500):
        if cand / km_per_unit >= WIDTH * 0.16:
            target = cand
            break
    target = target or 500
    bar = target / km_per_unit
    nm = target / 1.852
    x0, y0 = 14.0, HEIGHT - 24.0
    half = bar / 2.0
    ticks = (f'<line x1="{x0 + half:.1f}" y1="{y0 - 5:.1f}" x2="{x0 + half:.1f}" y2="{y0 + 5:.1f}" '
             f'style="stroke:#cfe3f2;stroke-width:1.2"/>')
    bar_svg = (
        f'<rect x="{x0 - 5:.1f}" y="{y0 - 11:.1f}" width="{bar + 12:.1f}" height="22" rx="3" '
        f'style="fill:#081d31;opacity:.72"/>'
        f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x0 + bar:.1f}" y2="{y0:.1f}" style="stroke:#cfe3f2;stroke-width:2.2"/>'
        f'<line x1="{x0:.1f}" y1="{y0 - 5:.1f}" x2="{x0:.1f}" y2="{y0 + 5:.1f}" style="stroke:#cfe3f2;stroke-width:1.2"/>'
        f'{ticks}'
        f'<line x1="{x0 + bar:.1f}" y1="{y0 - 5:.1f}" x2="{x0 + bar:.1f}" y2="{y0 + 5:.1f}" style="stroke:#cfe3f2;stroke-width:1.2"/>'
        f'<text x="{x0 + bar + 8:.1f}" y="{y0 + 4:.1f}" style="fill:#cfe3f2;font-size:11px;direction:rtl;unicode-bidi:isolate">'
        f'{target:g} كيلومتر · {nm:.0f} ميل بحري</text>'
    )
    nx, ny = WIDTH - 26.0, 34.0
    north_svg = (
        f'<g class="mp-north" aria-label="سهم الشمال">'
        f'<path d="M{nx:.1f} {ny - 15:.1f} L{nx + 6:.1f} {ny + 6:.1f} L{nx:.1f} {ny + 1:.1f} L{nx - 6:.1f} {ny + 6:.1f} Z" '
        f'style="fill:#cfe3f2"/>'
        f'<text x="{nx:.1f}" y="{ny + 19:.1f}" text-anchor="middle" style="fill:#cfe3f2;font-size:11px;font-weight:600">N</text></g>'
    )
    return f'<g class="mp-frame">{bar_svg}{north_svg}</g>'


def _dot_style(p: dict) -> str:
    """نمط العلامة داخل العنصر نفسه — لا يعتمد على ورقة الأنماط.

    ترميز مزدوج: اللون للحالة، والشكل للدقة — فلا تُقرأ الخريطة بالألوان وحدها.
    """
    key, _, _ = status_of(p)
    if p.get("precision") == "approximate":
        return "fill:none;stroke:var(--mk);stroke-width:2.4;stroke-dasharray:3.5 2.5"
    if key == "confirm":
        return "fill:var(--mk);stroke:var(--bg);stroke-width:2.2"
    if key == "bg":
        return "fill:none;stroke:var(--mk);stroke-width:1.8;opacity:.85"
    return "fill:var(--mk);stroke:#081d31;stroke-width:3.4"


def build_map(points=None, caption=None, inset=None, zoom=False):
    """لوحة رئيسية + لوحة مصغّرة اختيارية لباب المندب."""
    points = points or []
    map_title = "خريطة الوقائع" if points else "السياق الجغرافي"
    if points:
        _n = len(points)
        _ap = sum(1 for p in points if p.get("precision") == "approximate")
        _ex = _n - _ap
        _by = {}
        for _p in points:
            _by[status_of(_p)[1]] = _by.get(status_of(_p)[1], 0) + 1
        _mix = " · ".join(f"{k} {v}" for k, v in _by.items())
        map_label = (f"خريطة وقائع التقرير: {_n} واقعة مرسومة على الخليج العربي ومضيق هرمز وخليج عمان "
                     f"(إحداثيات مذكورة {_ex} · مواضع تقريبية {_ap}). الحالات: {_mix}. "
                     "الموضع التقريبي يعني أن المصدر لم يذكر إحداثيات فوُضعت العلامة داخل المنطقة نفسها لا في موضع محدد.")
    else:
        map_label = ("خريطة سياق جغرافي للقطاعات المعتمدة: السواحل والمضيق والموانئ وخطوط الطول والعرض؛ بلا علامات وقائع")
    _set_bbox(MAIN_BBOX)
    zrect, zhtml = _zoom_parts(points) if zoom else ("", "")
    panels = [
        _panel(
            map_title,
            points,
            map_label,
            caption,
            SEAS, PORTS + (SCREEN_ONLY_PORTS if zoom else []), COUNTRIES, GRID_LON, GRID_LAT,
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

    _has_approx = any((p.get("precision") == "approximate") for p in points)
    note = (
        '<p class="map-keys"><span class="mk-src">'
        'المصادر: اليابسة والحدود السياسية من Natural Earth بمقياس 1:50 مليون · '
        'الحدود البحرية من Marine Regions (VLIZ) وتشمل خطوطًا لم يُتفق عليها بعد وخطوط منتصف لا تُعدّ حدودًا سيادية · '
        'نظام فصل الملاحة في مضيق هرمز حسب مخطط المنظمة البحرية الدولية (اعتُمد 1968) بتمثيل تخطيطي · '
        'تسميات المدن والموانئ مواضع تمثيلية تقديرية لغياب مرجع هيدروغرافي معلن. '
        'الإسقاط: مستوٍ محلي على WGS 84 · الشبكة: خطوط الطول والعرض. '
        'هذه الخريطة سياق إخباري وليست خريطة ملاحية ولا بديلًا عن التحذيرات الرسمية.'
        '</span><span class="mk-note">' +
        ((('العلامات المرقمة: وقائع هذا التقرير.' +
          (' والعلامة المفرّغة: موضع تقريبي داخل المنطقة نفسها لأن المصدر لم يذكر إحداثيات.' if _has_approx else ''))
         if points else
         'لا توجد إحداثيات وقائع مثبتة في ملف الواجهة؛ اللوحة سياق جغرافي للقطاعات فقط.')) +
        '</span>'
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
