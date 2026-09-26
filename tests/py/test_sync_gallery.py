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

    def test_title_and_alt_are_empty_slots_in_all_three_languages(self):
        # Typed in the data file, never taken from darktable
        # (docs/concepts/gallery-metadata-yaml-only.md §4). An empty title stops
        # the build, which is the reminder to write one.
        lines = sg.build_stub("a.jpg")
        for field in ("title", "alt"):
            with self.subTest(field=field):
                i = lines.index(f"  {field}:")
                self.assertEqual(lines[i + 1:i + 4], ['    en: ""', '    de: ""', '    sv: ""'])

    def test_the_stub_has_an_empty_tags_list(self):
        self.assertIn("  tags: []", sg.build_stub("a.jpg"))

    def test_no_prose_is_taken_from_the_file_even_when_it_has_some(self):
        # The file's title is irrelevant now, and so are its alt text and caption.
        lines = sg.build_stub("a.jpg", {
            "title": "Red Fox", "alt": "a fox", "description": "a story",
        })
        joined = "\n".join(lines)
        for text in ("Red Fox", "a fox", "a story"):
            self.assertNotIn(text, joined)
        self.assertNotIn("  description:", lines)

    def test_only_license_and_artist_are_read_from_the_file(self):
        self.assertEqual(sg.FILE_FIELDS, ("license", "artist"))

    def test_the_artist_is_still_taken_from_the_file(self):
        self.assertIn("  artist: Lukas Nagel", sg.build_stub("a.jpg", {"artist": "Lukas Nagel"}))

    def test_a_licence_key_is_written_as_is(self):
        lines = sg.build_stub("a.jpg", {"license": "cc-by-sa-4.0"})
        self.assertIn("  license: cc-by-sa-4.0", lines)

    def test_a_licence_display_string_is_written_as_its_key(self):
        # dc:rights holds the display NAME; the data file takes the key. These
        # are the two spellings darktable actually writes into the photo store.
        cases = {
            "all rights reserved": "all-rights-reserved",
            "All Rights Reserved": "all-rights-reserved",
            "Creative Commons Attribution-ShareAlike (CC BY-SA)": "cc-by-sa-4.0",
            "  CC  BY-SA 4.0 ": "cc-by-sa-4.0",
        }
        for line, key in cases.items():
            with self.subTest(line=line):
                lines = sg.build_stub("a.jpg", {"license": line})
                self.assertIn(f"  license: {key}", lines)

    def test_every_mapped_key_exists_in_the_licence_map(self):
        # A typo in LICENSE_LINES would otherwise write a key the build rejects.
        import gallery_common as gc
        known = set(gc.license_aliases().values())
        self.assertTrue(known)
        self.assertLessEqual(set(sg.LICENSE_LINES.values()), known)

    def test_an_unmapped_licence_is_left_verbatim(self):
        # So it surfaces as a build error naming the photo rather than vanishing.
        lines = sg.build_stub("a.jpg", {"license": "Some Other Licence"})
        self.assertIn("  license: Some Other Licence", lines)

    def test_an_artist_that_needs_quoting_gets_it(self):
        lines = sg.build_stub("a.jpg", {"artist": "Nagel: Lukas"})
        self.assertIn('  artist: "Nagel: Lukas"', lines)

    def test_the_stub_parses_as_yaml(self):
        import json
        lines = sg.build_stub("Red Fox.jpg", {
            "license": "cc-by-sa-4.0", "artist": "Lukas Nagel #3",
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
