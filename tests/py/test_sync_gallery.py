"""Where a new photo's stub is inserted, and what it says.

`sync-gallery.py` edits data/gallery.yaml as text, so the two things that can go
wrong are finding the wrong block and writing a line that does not parse.
"""

import unittest

from _load import load

sg = load("sync-gallery")


class FindImagesBlock(unittest.TestCase):
    def test_the_block_ends_at_the_next_top_level_key(self):
        lines = [
            "images:",
            "- id: 1",
            "  src: a.jpg",
            "projects:",
            "- slug: x",
        ]
        self.assertEqual(sg.find_images_block(lines), (1, 3))

    def test_the_block_runs_to_eof_when_it_is_last(self):
        lines = ["images:", "- id: 1", "  src: a.jpg"]
        self.assertEqual(sg.find_images_block(lines), (1, 3))

    def test_comments_and_list_items_do_not_end_the_block(self):
        lines = [
            "images:",
            "# a comment in column 0",
            "- id: 1",
            "  src: a.jpg",
            "- id: 2",
            "  src: b.jpg",
        ]
        self.assertEqual(sg.find_images_block(lines), (1, 6))

    def test_a_file_without_images_is_a_clean_exit(self):
        with self.assertRaises(SystemExit):
            sg.find_images_block(["projects:", "- slug: x"])

    def test_collect_src_reads_every_filename(self):
        lines = ["images:", "- id: 1", "  src: a b.JPG", "- id: 2", "  src: c.jpg"]
        start, end = sg.find_images_block(lines)
        self.assertEqual(sg.collect_src(lines, start, end), {"a b.JPG", "c.jpg"})


class BuildStub(unittest.TestCase):
    def test_the_minimum_stub(self):
        lines = sg.build_stub("Red Fox.jpg")
        self.assertTrue(lines[0].startswith("- id: "))
        self.assertEqual(lines[1], "  src: Red Fox.jpg")
        self.assertIn("  category: others", lines)
        self.assertIn("  section: general", lines)

    def test_the_id_is_a_fresh_uuid_every_time(self):
        a = sg.build_stub("a.jpg")[0]
        b = sg.build_stub("a.jpg")[0]
        self.assertNotEqual(a, b)
        self.assertEqual(len(a[len("- id: "):]), 36)

    def test_prose_is_written_as_an_en_map(self):
        # The shape gallery-meta.html normalises every entry to, so adding a
        # German title later is one more indented line, not a restructure.
        lines = sg.build_stub("a.jpg", {"title": "Red Fox", "alt": "a fox"})
        self.assertIn("  title:", lines)
        self.assertIn("    en: Red Fox", lines)
        self.assertIn("  alt:", lines)
        self.assertIn("    en: a fox", lines)

    def test_a_licence_display_string_is_written_as_its_key(self):
        # dc:rights holds the display NAME; the data file takes the key.
        lines = sg.build_stub("a.jpg", {"license": "cc-by-sa-4.0"})
        self.assertIn("  license: cc-by-sa-4.0", lines)

    def test_an_unmapped_licence_is_left_verbatim(self):
        # So it surfaces as a build error naming the photo rather than vanishing.
        lines = sg.build_stub("a.jpg", {"license": "Some Other Licence"})
        self.assertIn("  license: Some Other Licence", lines)

    def test_prose_that_needs_quoting_gets_it(self):
        lines = sg.build_stub("a.jpg", {"title": "Fox: a portrait"})
        self.assertIn('    en: "Fox: a portrait"', lines)

    def test_the_stub_parses_as_yaml(self):
        import json
        lines = sg.build_stub("Red Fox.jpg", {
            "title": "Fox #3", "alt": "yes", "description": "a: b", "artist": "Lukas Nagel",
        })
        # No PyYAML here either; assert the properties a bare scalar must have.
        for line in lines:
            value = line.split(":", 1)[1].strip() if ":" in line else ""
            if value.startswith('"'):
                json.loads(value)  # raises if the escaping is wrong
            else:
                self.assertNotIn(" #", value)
                self.assertNotIn(": ", value)


if __name__ == "__main__":
    unittest.main()
