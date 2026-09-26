"""The quoting rule, the variant-name rule and the two small readers.

These are the functions that decide what ends up in data/gallery.yaml as text.
A bug in yaml_scalar is a data file that no longer parses, or — worse — one that
parses into something other than what was written.
"""

import tempfile
import unittest
from pathlib import Path

import _load  # noqa: F401  (puts scripts/ on sys.path)
import gallery_common as gc


class YamlScalar(unittest.TestCase):
    def assert_roundtrip(self, value):
        """What we emit must read back as exactly what we were given."""
        import json
        emitted = gc.yaml_scalar(value)
        if emitted.startswith('"'):
            self.assertEqual(json.loads(emitted), str(value).strip())
        else:
            self.assertEqual(emitted, str(value).strip())

    def test_plain_prose_is_left_bare(self):
        self.assertEqual(gc.yaml_scalar("A red fox in the snow"), "A red fox in the snow")

    def test_a_hash_mid_scalar_is_quoted(self):
        # " #" opens a comment and would truncate the value silently.
        self.assertEqual(gc.yaml_scalar("Wild boar #3"), '"Wild boar #3"')

    def test_leading_indicator_characters_are_quoted(self):
        for text in ("- not a list item", "? maybe", "* star", "& anchor", "! bang",
                     "[bracket", "{brace", "@at", "`tick", "%percent", "|pipe", ">fold"):
            with self.subTest(text=text):
                self.assertTrue(gc.yaml_scalar(text).startswith('"'), text)

    def test_colon_space_is_quoted(self):
        self.assertEqual(gc.yaml_scalar("Alpaca: a portrait"), '"Alpaca: a portrait"')

    def test_trailing_colon_is_quoted(self):
        self.assertTrue(gc.yaml_scalar("Title:").startswith('"'))

    def test_booleanish_words_are_quoted(self):
        for text in ("yes", "No", "true", "FALSE", "on", "off", "null", "~"):
            with self.subTest(text=text):
                self.assertTrue(gc.yaml_scalar(text).startswith('"'), text)

    def test_empty_is_quoted(self):
        self.assertEqual(gc.yaml_scalar(""), '""')

    def test_quotes_and_backslashes_are_escaped(self):
        self.assertEqual(gc.yaml_scalar('a "b" c: d'), '"a \\"b\\" c: d"')
        self.assertEqual(gc.yaml_scalar("back\\slash: x"), '"back\\\\slash: x"')

    def test_no_newline_survives(self):
        # A raw newline inside a bare scalar ends the value; both characters are
        # replaced individually, so a CRLF collapses to two spaces rather than one.
        self.assertEqual(gc.yaml_scalar("two\nlines"), "two lines")
        self.assertNotIn("\n", gc.yaml_scalar("crlf\r\nlines"))
        self.assertNotIn("\r", gc.yaml_scalar("crlf\r\nlines"))

    def test_roundtrip_of_the_awkward_cases(self):
        for value in ('a "b"', "a: b", "x #y", "yes", "", "- dash", "trailing "):
            with self.subTest(value=value):
                self.assert_roundtrip(value)


class PublishedBase(unittest.TestCase):
    # A served file maps to its photo's published name — the manifest's `file`,
    # the English slug — not to the store filename (gallery-metadata-yaml-only §5).
    def test_a_hugo_variant_maps_back_to_its_published_original(self):
        self.assertEqual(gc.published_base("red-fox-in-the-snow_hu_1f1561eb0ac2d2ce.jpg"),
                         "red-fox-in-the-snow.jpg")

    def test_a_published_original_is_returned_unchanged(self):
        self.assertEqual(gc.published_base("red-fox-in-the-snow.jpg"), "red-fox-in-the-snow.jpg")

    def test_only_a_hex_hash_is_stripped(self):
        # The hash is hex, so "_hu_b" IS a variant marker and "_hu_z" is not.
        self.assertEqual(gc.published_base("a_hu_b.jpg"), "a.jpg")
        self.assertEqual(gc.published_base("a_hu_z.jpg"), "a_hu_z.jpg")

    def test_the_extension_is_kept_as_published(self):
        self.assertEqual(gc.published_base("alpaca_hu_deadbeef01234567.JPG"), "alpaca.JPG")


class PhotosDirFromHugoMounts(unittest.TestCase):
    def write(self, text):
        root = Path(tempfile.mkdtemp())
        cfg = root / "config" / "_default"
        cfg.mkdir(parents=True)
        (cfg / "module.yaml").write_text(text, encoding="utf-8")
        return root

    def test_reads_the_gallery_mount_source(self):
        root = self.write(
            "mounts:\n"
            "  - source: assets\n"
            "    target: assets\n"
            "  - source: /srv/photos\n"
            "    target: assets/images/gallery\n"
        )
        self.assertEqual(gc.photos_dir_from_hugo_mounts(root), Path("/srv/photos"))

    def test_a_missing_file_is_not_an_error(self):
        self.assertIsNone(gc.photos_dir_from_hugo_mounts(Path(tempfile.mkdtemp())))

    def test_a_source_does_not_leak_across_list_items(self):
        # source always precedes target in this file; a malformed pairing must
        # not hand the previous item's source to the gallery target.
        root = self.write(
            "mounts:\n"
            "  - source: /srv/photos\n"
            "    target: assets\n"
            "  - target: assets/images/gallery\n"
        )
        self.assertIsNone(gc.photos_dir_from_hugo_mounts(root))

    def test_comments_are_ignored(self):
        root = self.write(
            "mounts:\n"
            "  # - source: /wrong\n"
            "  #   target: assets/images/gallery\n"
            "  - source: /srv/photos\n"
            "    target: assets/images/gallery\n"
        )
        self.assertEqual(gc.photos_dir_from_hugo_mounts(root), Path("/srv/photos"))


class LicenseKeys(unittest.TestCase):
    def test_every_key_in_the_real_map_resolves_to_itself(self):
        aliases = gc.license_aliases()
        self.assertIn("cc-by-sa-4.0", aliases)
        self.assertEqual(aliases["cc-by-sa-4.0"], "cc-by-sa-4.0")
        self.assertEqual(gc.license_key("CC-BY-SA-4.0"), "cc-by-sa-4.0")

    def test_an_unknown_value_is_none(self):
        self.assertIsNone(gc.license_key("Creative Commons, probably"))
        self.assertIsNone(gc.license_key(""))
        self.assertIsNone(gc.license_key(None))


if __name__ == "__main__":
    unittest.main()
