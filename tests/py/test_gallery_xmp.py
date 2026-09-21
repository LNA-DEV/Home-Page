"""The file → YAML field map, without exiftool and without a photo.

This is the half that encodes which tag an `alt:` comes from — and the half that
would silently start reading the wrong one. `read()` is a subprocess call around
`parse_records`; only the mapping is tested here.
"""

import unittest

import _load  # noqa: F401
import gallery_xmp as gx


def exiftool_json(**tags):
    import json
    return json.dumps([dict(SourceFile="/photos/Red Fox.jpg", **tags)])


class FieldMap(unittest.TestCase):
    def test_the_five_documented_tags(self):
        out = gx.parse_records(exiftool_json(
            Title="Red Fox",
            Notes="A red fox in the snow",
            Description="Shot at first light.",
            Rights="cc-by-sa-4.0",
            Creator="Lukas Nagel",
        ))
        self.assertEqual(out, {"Red Fox.jpg": {
            "title": "Red Fox",
            "alt": "A red fox in the snow",
            "description": "Shot at first light.",
            "license": "cc-by-sa-4.0",
            "artist": "Lukas Nagel",
        }})

    def test_alt_comes_from_notes_not_description(self):
        # darktable's *notes* field is the short account of what is visible;
        # dc:description is caption prose. They are different things.
        out = gx.parse_records(exiftool_json(Notes="what is visible", Description="prose"))
        self.assertEqual(out["Red Fox.jpg"]["alt"], "what is visible")
        self.assertEqual(out["Red Fox.jpg"]["description"], "prose")

    def test_a_bag_is_joined(self):
        # dc:creator is a bag and comes back as a list.
        out = gx.parse_records(exiftool_json(Creator=["Lukas Nagel", "Someone Else"]))
        self.assertEqual(out["Red Fox.jpg"]["artist"], "Lukas Nagel, Someone Else")

    def test_empty_and_whitespace_values_are_dropped(self):
        out = gx.parse_records(exiftool_json(Title="  ", Notes="", Creator=["", "  "]))
        self.assertEqual(out, {})

    def test_values_are_stripped(self):
        out = gx.parse_records(exiftool_json(Title="  Red Fox  "))
        self.assertEqual(out["Red Fox.jpg"]["title"], "Red Fox")

    def test_a_record_with_no_fields_is_omitted_entirely(self):
        self.assertEqual(gx.parse_records(exiftool_json()), {})

    def test_the_key_is_the_basename(self):
        import json
        out = gx.parse_records(json.dumps([{"SourceFile": "/deep/path/a b.JPG", "Title": "t"}]))
        self.assertEqual(list(out), ["a b.JPG"])

    def test_malformed_json_is_no_values_not_a_crash(self):
        # A stub with empty fields is a fine outcome; an aborted sync is not.
        self.assertEqual(gx.parse_records("not json"), {})
        self.assertEqual(gx.parse_records(""), {})

    def test_the_tag_map_is_the_documented_one(self):
        self.assertEqual(gx.TAGS, {
            "title": "XMP-dc:Title",
            "alt": "XMP-acdsee:Notes",
            "description": "XMP-dc:Description",
            "license": "XMP-dc:Rights",
            "artist": "XMP-dc:Creator",
        })


if __name__ == "__main__":
    unittest.main()
