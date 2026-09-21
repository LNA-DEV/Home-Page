"""The hand-written YAML subset every dex script trusts.

`dex_common` parses and re-emits data/dex.yaml without PyYAML, and it has never
been exercised outside its happy path. The load-bearing property is the round
trip: load → dump → load must be equal, over the real 154-species file, or a
`dex-enrich.py` run silently rewrites something it did not mean to touch.
"""

import tempfile
import unittest
from pathlib import Path

import _load  # noqa: F401
import dex_common as dc

REPO = Path(__file__).resolve().parent.parent.parent
REAL = REPO / "data" / "dex.yaml"


class RoundTrip(unittest.TestCase):
    def test_the_real_file_survives_load_dump_load(self):
        first = dc.load_dex(REAL)
        self.assertGreater(len(first), 100)
        out = Path(tempfile.mkdtemp()) / "dex.yaml"
        dc.dump_dex(first, out)
        second = dc.load_dex(out)
        self.assertEqual(first, second)

    def test_a_second_dump_is_byte_identical(self):
        species = dc.load_dex(REAL)
        tmp = Path(tempfile.mkdtemp())
        a, b = tmp / "a.yaml", tmp / "b.yaml"
        dc.dump_dex(species, a)
        dc.dump_dex(dc.load_dex(a), b)
        self.assertEqual(a.read_bytes(), b.read_bytes())


class Snippets(unittest.TestCase):
    def parse(self, text):
        path = Path(tempfile.mkdtemp()) / "dex.yaml"
        path.write_text(text, encoding="utf-8")
        return dc.load_dex(path)

    def test_a_per_language_map(self):
        got = self.parse(
            "species:\n"
            "  - slug: red-fox\n"
            "    names:\n"
            "      en: Red fox\n"
            "      de: Rotfuchs\n"
            "      sv: Rödräv\n"
        )
        self.assertEqual(got[0]["names"], {"en": "Red fox", "de": "Rotfuchs", "sv": "Rödräv"})

    def test_a_flow_list(self):
        got = self.parse("species:\n  - slug: x\n    tags: [a, b, \"c, d\"]\n")
        self.assertEqual(got[0]["tags"], ["a", "b", "c, d"])

    def test_a_quoted_scalar_keeps_its_leading_zeros(self):
        got = self.parse('species:\n  - slug: x\n    number: "001"\n')
        self.assertEqual(got[0]["number"], "001")

    def test_a_list_of_maps(self):
        got = self.parse(
            "species:\n"
            "  - slug: x\n"
            "    sightings:\n"
            "      - lat: 47.8\n"
            "        lng: 12.1\n"
            "        label: Inn valley\n"
        )
        self.assertEqual(got[0]["sightings"], [{"lat": 47.8, "lng": 12.1, "label": "Inn valley"}])

    def test_a_boolean(self):
        got = self.parse("species:\n  - slug: x\n    marine: true\n")
        self.assertIs(got[0]["marine"], True)

    def test_a_colon_inside_a_quoted_value(self):
        got = self.parse('species:\n  - slug: x\n    description: "a: b"\n')
        self.assertEqual(got[0]["description"], "a: b")

    def test_a_value_needing_quotes_is_re_emitted_quoted(self):
        out = Path(tempfile.mkdtemp()) / "dex.yaml"
        dc.dump_dex([{"slug": "x", "note": "a: b", "number": "001"}], out)
        again = dc.load_dex(out)
        self.assertEqual(again[0]["note"], "a: b")
        self.assertEqual(again[0]["number"], "001")


class Helpers(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(dc.slugify("Red Fox"), "red-fox")
        self.assertEqual(dc.slugify("Bergs-Kiebitz!"), "bergs-kiebitz")

    def test_group_for_a_known_family(self):
        self.assertTrue(dc.group_for("Canidae"))


if __name__ == "__main__":
    unittest.main()
