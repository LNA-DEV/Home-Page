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


class Subset(unittest.TestCase):
    def test_only_the_requested_fields_survive(self):
        # sync-gallery.py asks for license and artist and must never see a title.
        records = gx.parse_records(exiftool_json(
            Title="Red Fox", Notes="a fox", Rights="cc-by-sa-4.0", Creator="Lukas Nagel"))
        self.assertEqual(gx.select(records, {"license": 1, "artist": 1}), {
            "Red Fox.jpg": {"license": "cc-by-sa-4.0", "artist": "Lukas Nagel"}})

    def test_a_file_with_none_of_the_requested_fields_is_omitted(self):
        records = gx.parse_records(exiftool_json(Title="Red Fox"))
        self.assertEqual(gx.select(records, {"license": 1}), {})


class Keywords(unittest.TestCase):
    def test_all_three_places_in_file_order(self):
        out = gx.parse_keyword_records(exiftool_json(
            Subject=["bavarianAlps", "fox"], Keywords="redFox", XPKeywords="zsl_sdr"))
        self.assertEqual(out, {"Red Fox.jpg": ["bavarianAlps", "fox", "redFox", "zsl_sdr"]})

    def test_delimited_strings_are_split_like_the_build_split_them(self):
        out = gx.parse_keyword_records(exiftool_json(XPKeywords="a;b, c ;; ", Subject="d"))
        self.assertEqual(out["Red Fox.jpg"], ["d", "a", "b", "c"])

    def test_spelling_and_duplicates_are_kept(self):
        # The caller decides what a duplicate means; the spelling is the point.
        out = gx.parse_keyword_records(exiftool_json(Subject=["Fox"], Keywords=["fox"]))
        self.assertEqual(out["Red Fox.jpg"], ["Fox", "fox"])

    def test_a_file_without_tags_is_omitted(self):
        self.assertEqual(gx.parse_keyword_records(exiftool_json()), {})
        self.assertEqual(gx.parse_keyword_records("not json"), {})

    def test_the_three_places_are_the_ones_the_build_read(self):
        self.assertEqual(gx.KEYWORD_TAGS, ("XMP-dc:Subject", "IPTC:Keywords", "EXIF:XPKeywords"))


if __name__ == "__main__":
    unittest.main()
