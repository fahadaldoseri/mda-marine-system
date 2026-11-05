"""عنقود علامات الخريطة والتفكيك الشعاعي والترقيم الموحّد.

مبني على المواصفة المعتمدة: audit/المواصفة-النهائية-لقسم-الخريطة.md
- تجميع حتمي: كل وقائع تقلّ المسافة بينها عن الحدّ المعلوم تُجمَّع عنقودًا واحدًا.
- عنقود حتى أربع وقائع: تفكيك شعاعي مباشر مع خطوط قائدة ونقطة موضع أصلية ظاهرة.
- عنقود خمس فأكثر: شارة واحدة تحمل العدد.
- الترقيم موحّد بين الخريطة الرئيسية ولوحة التكبير: الرقم نفسه للواقعة نفسها.
- قاعدة الفصل الأدنى 22 بكسل: يُزاح العرض بخط قائد ولا يُزوَّر الموضع.

الدوال نقية بلا تبعية خارجية وبلا حالة عامة، فتُختبر وحدها وتُستخدم في السطحين.
"""

from __future__ import annotations

import math

MIN_SEP_PX = 22.0          # قاعدة الفصل الأدنى المعتمدة (بكسل)
SPIDER_MAX = 4             # أقصى عدد وقائع يُفكَّك شعاعيًّا


def assign_numbers(points: list[dict]) -> dict[str, int]:
    """ترقيم موحّد: الرقم نفسه للواقعة نفسها في كل الأسطح.

    الترتيب حتمي: معرّف الواقعة تصاعديًّا، فيثبت الرقم بين الإصدارات وبين السطحين.
    """
    ids = sorted({str(p["id"]) for p in points})
    return {pid: i + 1 for i, pid in enumerate(ids)}


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def cluster_points(points: list[dict], project, min_sep: float = MIN_SEP_PX) -> list[dict]:
    """تجميع حتمي بالتقارب (إغلاق تعدٍّي) على إحداثيات العرض.

    project: دالة (lon, lat) -> (x, y) بإحداثيات اللوحة النهائية.
    يعيد قائمة عناقيد، كل عنقود: {"members": [...], "anchor": (x, y), "centroid": (x, y)}.
    """
    items = []
    for p in sorted(points, key=lambda q: str(q["id"])):
        x, y = project(float(p["lon"]), float(p["lat"]))
        items.append({"point": p, "xy": (x, y)})

    n = len(items)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    for i in range(n):
        for j in range(i + 1, n):
            if _dist(items[i]["xy"], items[j]["xy"]) < min_sep:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    clusters = []
    for root in sorted(groups):
        members = [items[i] for i in groups[root]]
        xs = [m["xy"][0] for m in members]
        ys = [m["xy"][1] for m in members]
        centroid = (sum(xs) / len(xs), sum(ys) / len(ys))
        clusters.append({
            "members": [m["point"] for m in members],
            "anchor": members[0]["xy"],
            "centroid": centroid,
        })
    return clusters


def layout(points: list[dict], project, min_sep: float = MIN_SEP_PX) -> list[dict]:
    """يوزّع العلامات: مفكوكة شعاعيًّا للعنقود الصغير، وشارة مرقّمة للكبير.

    يعيد قائمة عناصر عرض: {"kind": "marker"|"badge", "point", "number", "x", "y", "leader"}
    leader: (x0, y0, x1, y1) خط قائد من الموضع الحقيقي إلى موضع العرض، أو None.
    """
    numbers = assign_numbers(points)
    out: list[dict] = []

    for cl in cluster_points(points, project, min_sep):
        members = cl["members"]
        cx, cy = cl["centroid"]

        if len(members) > SPIDER_MAX:
            out.append({
                "kind": "badge",
                "point": None,
                "number": None,
                "count": len(members),
                "members": members,
                "x": cx,
                "y": cy,
                "leader": None,
            })
            continue

        if len(members) == 1:
            p = members[0]
            ax, ay = cl["anchor"]
            out.append({
                "kind": "marker", "point": p, "number": numbers[str(p["id"])],
                "count": 1, "members": members, "x": ax, "y": ay, "leader": None,
            })
            continue

        # تفكيك شعاعي: موزّعون على محيط دائرة، وخط قائد إلى الموضع الحقيقي.
        radius = max(min_sep * 0.75, 12.0)
        for k, p in enumerate(sorted(members, key=lambda q: str(q["id"]))):
            ang = (2 * math.pi * k / len(members)) - math.pi / 2
            px, py = project(float(p["lon"]), float(p["lat"]))
            mx, my = cx + radius * math.cos(ang), cy + radius * math.sin(ang)
            out.append({
                "kind": "marker", "point": p, "number": numbers[str(p["id"])],
                "count": len(members), "members": members,
                "x": mx, "y": my, "leader": (px, py, mx, my),
            })

    return out


def min_separation(items: list[dict]) -> float:
    """أقرب مسافة بين أي عنصرَي عرض — يُستخدم في بوابة الفصل الأدنى."""
    pts = [(it["x"], it["y"]) for it in items]
    if len(pts) < 2:
        return float("inf")
    return min(
        _dist(pts[i], pts[j])
        for i in range(len(pts))
        for j in range(i + 1, len(pts))
    )


def check_layout(points: list[dict], items: list[dict], min_sep: float = MIN_SEP_PX) -> list[str]:
    """فحوص العقد التي تفشل مغلقًا. يعيد قائمة المخالفات (فارغة = مطابق)."""
    problems: list[str] = []
    drawn = [it for it in items if it["kind"] == "marker"]
    # وقائع الشارة المرقّمة ممثَّلة بعددها المعروض، فلا تُعدّ مسقطة.
    drawn_ids = {str(it["point"]["id"]) for it in drawn}
    for it in items:
        if it["kind"] == "badge":
            drawn_ids |= {str(p["id"]) for p in it.get("members", [])}

    expected = {str(p["id"]) for p in points}
    missing = expected - drawn_ids
    if missing:
        problems.append(f"وقائع لم تُرسم: {sorted(missing)}")

    numbers = assign_numbers(points)
    seen: dict[int, str] = {}
    for it in drawn:
        pid = str(it["point"]["id"])
        if it["number"] != numbers[pid]:
            problems.append(f"رقم غير موحّد للواقعة {pid}: {it['number']} بدل {numbers[pid]}")
        if it["number"] in seen and seen[it["number"]] != pid:
            problems.append(f"رقم مكرّر {it['number']} بين {seen[it['number']]} و{pid}")
        seen[it["number"]] = pid

    sep = min_separation(items)
    if sep < min_sep:
        problems.append(f"تراكب: أقرب مسافة {sep:.1f} بكسل أقل من الحدّ {min_sep:.0f}")

    for it in items:
        if it["kind"] == "badge" and (not it.get("count") or it["count"] <= SPIDER_MAX):
            problems.append("شارة عنقود بعدد لا يستدعيها")
    return problems
