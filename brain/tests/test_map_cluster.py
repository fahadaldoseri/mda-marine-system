"""اختبار انحدار لوحدة العنقود والتفكيك والترقيم الموحّد.

موجب: عنقود من واقعتين يُفكَّك شعاعيًّا، وترقيم موحّد، وصفر مخالفات.
سالب: وقائع متطابقة الموضع بلا تفكيك تُكشف كتراكب، وواقعة مُسقطة تُكشف.
"""

import pathlib
import sys
import unittest

SITE = pathlib.Path("/home/ubuntu/seawatch")
sys.path.insert(0, str(SITE / "generator"))

import map_cluster as mc  # noqa: E402


def project_factory(scale=20.0):
    def project(lon, lat):
        return ((lon - 50.0) * scale, (30.0 - lat) * scale)
    return project


def pt(pid, lon, lat):
    return {"id": pid, "lon": lon, "lat": lat}


class MapClusterTests(unittest.TestCase):
    def test_small_cluster_spiderfies_and_numbers_are_unified(self):
        points = [pt("MN-1", 56.40, 26.56), pt("MN-2", 56.405, 26.565), pt("MN-3", 51.00, 25.00)]
        items = mc.layout(points, project_factory())
        problems = mc.check_layout(points, items)
        self.assertEqual(problems, [], f"مخالفات غير متوقعة: {problems}")
        self.assertEqual(mc.assign_numbers(points), {"MN-1": 1, "MN-2": 2, "MN-3": 3})
        spidered = [it for it in items if it["leader"]]
        self.assertEqual(len(spidered), 2, "العنقود الصغير يجب أن يُفكَّك شعاعيًّا كاملًا")
        self.assertGreaterEqual(mc.min_separation(items), mc.MIN_SEP_PX)

    def test_large_cluster_becomes_single_badge(self):
        points = [pt(f"MN-{i}", 56.40 + i * 0.001, 26.56 + i * 0.001) for i in range(6)]
        items = mc.layout(points, project_factory())
        badges = [it for it in items if it["kind"] == "badge"]
        self.assertEqual(len(badges), 1)
        self.assertEqual(badges[0]["count"], 6)
        self.assertEqual(mc.check_layout(points, items), [])

    def test_overlap_without_spiderfy_is_caught(self):
        points = [pt("MN-1", 56.40, 26.56), pt("MN-2", 56.40, 26.56)]
        project = project_factory()
        raw = [{"kind": "marker", "point": p, "number": i + 1,
                "count": 2, "members": points, "x": project(p["lon"], p["lat"])[0],
                "y": project(p["lon"], p["lat"])[1], "leader": None}
               for i, p in enumerate(points)]
        problems = mc.check_layout(points, raw)
        self.assertTrue(any("تراكب" in x for x in problems), f"لم يُكشف التراكب: {problems}")

    def test_dropped_incident_is_caught(self):
        points = [pt("MN-1", 56.40, 26.56), pt("MN-2", 51.00, 25.00)]
        items = [it for it in mc.layout(points, project_factory())
                 if str(it.get("point", {}).get("id")) != "MN-2"]
        problems = mc.check_layout(points, items)
        self.assertTrue(any("لم تُرسم" in x for x in problems), f"لم يُكشف الإسقاط: {problems}")


if __name__ == "__main__":
    unittest.main(verbosity=2)