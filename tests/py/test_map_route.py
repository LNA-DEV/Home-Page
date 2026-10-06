"""scripts/map-route.py — the pure parts: parsing, the request, the geometry.

No network: fetch_route() is the one function that talks to OSRM, and it is
not called here."""

import unittest

from _load import load

mr = load("map-route")


class ParsePoint(unittest.TestCase):
    def test_lat_lng(self):
        self.assertEqual(mr.parse_point("55.598,13.022"), (55.598, 13.022))

    def test_rejects_garbage_and_range(self):
        for bad in ("55.598", "a,b", "91,10", "10,181", "1,2,3"):
            with self.assertRaises(ValueError, msg=bad):
                mr.parse_point(bad)


class OsrmUrl(unittest.TestCase):
    def test_lng_lat_order_and_full_geometry(self):
        url = mr.osrm_url([(47.85, 12.12), (55.598017, 13.022095)])
        self.assertTrue(url.startswith("https://router.project-osrm.org/route/v1/driving/"))
        self.assertIn("12.120000,47.850000;13.022095,55.598017", url)
        self.assertIn("overview=full", url)
        self.assertIn("geometries=geojson", url)


class Geometry(unittest.TestCase):
    def test_round_line_rounds_and_drops_repeats(self):
        line = [[12.1200001, 47.8500001], [12.1200002, 47.8500002], [12.5, 48.0]]
        self.assertEqual(mr.round_line(line), [[12.12, 47.85], [12.5, 48.0]])

    def test_simplify_keeps_ends_and_corners_drops_collinear(self):
        straight = [[0.0, 0.0], [0.5, 0.0], [1.0, 0.0], [1.0, 1.0]]
        self.assertEqual(mr.simplify(straight, 0.01), [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])

    def test_simplify_short_lines_untouched(self):
        self.assertEqual(mr.simplify([[0, 0], [1, 1]], 0.5), [[0, 0], [1, 1]])

    def test_simplify_thins_a_long_curve(self):
        # A real drive is ~15,000 points of gentle curves; most of them go.
        import math
        arc = [[math.cos(i / 8000), math.sin(i / 8000)] for i in range(15000)]
        out = mr.simplify(arc, 0.0005)
        self.assertEqual(out[0], arc[0])
        self.assertEqual(out[-1], arc[-1])
        self.assertLess(len(out), 200)

    def test_feature_shape(self):
        f = mr.route_feature([(47.85, 12.12), (55.6, 13.02)], [[12.12, 47.85], [13.02, 55.6]], "2026-10-06")
        self.assertEqual(f["type"], "Feature")
        self.assertEqual(f["geometry"]["type"], "LineString")
        self.assertEqual(f["geometry"]["coordinates"], [[12.12, 47.85], [13.02, 55.6]])
        self.assertEqual(f["properties"]["waypoints"], [[47.85, 12.12], [55.6, 13.02]])
        self.assertEqual(f["properties"]["fetched"], "2026-10-06")


class Name(unittest.TestCase):
    def test_name_pattern(self):
        self.assertTrue(mr.NAME_RE.match("sverige-2024-malmo-oland"))
        for bad in ("Sverige", "a_b", "-a", "a-", "a--b", ""):
            self.assertIsNone(mr.NAME_RE.match(bad), bad)


if __name__ == "__main__":
    unittest.main()
