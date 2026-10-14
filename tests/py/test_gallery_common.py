"""The quoting rule, the variant-path rule and the two small readers.

These are the functions that decide what ends up in data/gallery.yaml as text.
A bug in yaml_scalar is a data file that no longer parses, or — worse — one that
parses into something other than what was written.
"""

import shutil
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


class ServedGalleryFiles(unittest.TestCase):
    # images/gallery/<file> is an original, images/gallery/<spec>/<file> a variant
    # of it under the SAME name (docs/concepts/stable-image-urls.md §4). Where a
    # file sits is the only thing that tells them apart, and a path that is
    # neither must surface as a problem, never be skipped.
    def tree(self, *paths):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        for p in paths:
            (root / p).parent.mkdir(parents=True, exist_ok=True)
            (root / p).write_bytes(b"x")
        return root

    def test_an_original_and_its_variants_share_a_name(self):
        root = self.tree("red-fox.jpg", "fit-600x600/red-fox.jpg", "fill-480x480-center/red-fox.jpg")
        files, problems = gc.served_gallery_files(root)
        self.assertEqual(problems, [])
        self.assertEqual(
            sorted((str(p.relative_to(root)), v) for p, v in files),
            [("fill-480x480-center/red-fox.jpg", True), ("fit-600x600/red-fox.jpg", True),
             ("red-fox.jpg", False)])
        self.assertEqual({p.name for p, _ in files}, {"red-fox.jpg"})

    def test_the_variants_are_found_at_all(self):
        # os.scandir over the top level skipped directories without a word; every
        # variant would then have shipped untagged and gone unchecked.
        files, _ = gc.served_gallery_files(self.tree("fit-4000x4000/a.jpg"))
        self.assertEqual([v for _, v in files], [True])

    def test_a_hugo_hash_name_is_a_problem_wherever_it_sits(self):
        root = self.tree("a.jpg", "a_hu_1f1561eb0ac2d2ce.jpg", "fit-600x600/a_hu_b.jpg")
        files, problems = gc.served_gallery_files(root)
        self.assertEqual([str(p.relative_to(root)) for p, _ in files], ["a.jpg"])
        self.assertEqual(len(problems), 2, problems)
        self.assertTrue(all("_hu_" in p for p in problems), problems)

    def test_only_a_hex_hash_counts_as_hugo_s(self):
        files, problems = gc.served_gallery_files(self.tree("a_hu_z.jpg"))
        self.assertEqual(problems, [])
        self.assertEqual(len(files), 1)

    def test_deeper_nesting_is_a_problem(self):
        _, problems = gc.served_gallery_files(self.tree("fit-600x600/deeper/a.jpg"))
        self.assertTrue(any("deeper" in p for p in problems), problems)

    def test_a_directory_that_is_not_a_spec_is_a_problem(self):
        for name in ("Fit 600x600", "thumbs_", "-fit"):
            with self.subTest(name=name):
                _, problems = gc.served_gallery_files(self.tree(f"{name}/a.jpg"))
                self.assertTrue(any("not a spec directory" in p for p in problems), problems)


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
