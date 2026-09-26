"""The one-time tag import: which tags, how they are spelled, and the text edit.

`gallery-import-tags.py` takes the SET and ORDER of each photo's tags from Hugo's
manifest and only the SPELLING from the file, and edits data/gallery.yaml as
text. What can go wrong is a stale manifest, a tag nobody spells, an edit in the
wrong place, and a second run that is not a no-op. All tested here without
exiftool, on fixtures.
"""

import json
import tempfile
import unittest
from pathlib import Path

from _load import load

it = load("gallery-import-tags")

YAML = """\
images:
- id: a
  src: Fox.jpg
  category: animals
  section: general
  project: ""
  portfolio: false
  tags: []
  title:
    en: Fox
    de: Fuchs
- id: b
  slugAliases: [old-b]
  src: Lizard.JPG
  section: general
  tags:
  - lizard
  - photo
  alt:
    en: a lizard
- id: c
  src: DSC_1.jpg
  category: others
  section: general
  title:
    en: Stub
projects:
- slug: x
  title: Not a photo
"""


def lines_of(text):
    return text.rstrip("\n").split("\n")


def entries_of(text):
    lines = lines_of(text)
    start, end = it.find_images_block(lines)
    return lines, it.parse_entries(lines, start, end)


class Parse(unittest.TestCase):
    def test_nested_prose_and_flow_lists_are_understood(self):
        _, entries = entries_of(YAML)
        self.assertEqual([e["id"] for e in entries], ["a", "b", "c"])
        self.assertEqual([e["src"] for e in entries], ["Fox.jpg", "Lizard.JPG", "DSC_1.jpg"])
        self.assertEqual(entries[0]["tags"], [])
        self.assertEqual(entries[1]["tags"], ["lizard", "photo"])
        self.assertIsNone(entries[2]["tags"])

    def test_the_projects_block_is_not_read(self):
        _, entries = entries_of(YAML)
        self.assertEqual(len(entries), 3)

    def test_an_unknown_shape_aborts(self):
        with self.assertRaises(SystemExit):
            entries_of("images:\n- id: a\n  src: a.jpg\n  tags: |\n    x\n")


class Plan(unittest.TestCase):
    MANIFEST = {"a": ["bavarianalps", "fox"], "b": ["eidechse", "lizard", "photo"], "c": ["stub"]}
    KEYWORDS = {"Fox.jpg": ["bavarianAlps", "fox", "zsl_sdr"], "Lizard.JPG": ["Eidechse"],
                "DSC_1.jpg": ["Stub"]}

    def run_plan(self, manifest=None, keywords=None):
        lines, entries = entries_of(YAML)
        plan, report = it.build_plan(entries, manifest or self.MANIFEST,
                                     self.KEYWORDS if keywords is None else keywords)
        return lines, plan.apply(lines), report

    def test_the_file_spelling_is_kept(self):
        _, out, _ = self.run_plan()
        i = out.index("  src: Fox.jpg")
        self.assertIn("  - bavarianAlps", out[i:i + 10])

    def test_an_empty_list_becomes_a_block_list_in_manifest_order(self):
        _, out, report = self.run_plan()
        i = out.index("  tags:")
        self.assertEqual(out[i:i + 3], ["  tags:", "  - bavarianAlps", "  - fox"])
        self.assertEqual(report["from_empty"], 1)

    def test_a_missing_key_goes_after_section(self):
        _, out, report = self.run_plan()
        i = out.index("  src: DSC_1.jpg")
        self.assertEqual(out[i + 3:i + 5], ["  tags:", "  - Stub"])
        self.assertEqual(out[i + 2], "  section: general")
        self.assertEqual(report["keys_added"], 1)

    def test_existing_yaml_tags_keep_their_line_and_file_tags_come_first(self):
        # The order the site showed: the file's tags, then the YAML's.
        _, out, report = self.run_plan()
        i = out.index("  src: Lizard.JPG")
        self.assertEqual(out[i + 2:i + 6], ["  tags:", "  - Eidechse", "  - lizard", "  - photo"])
        self.assertEqual(report["rewritten"], ["Lizard.JPG"])

    def test_only_tag_lines_change(self):
        before, out, _ = self.run_plan()
        added = [l for l in out if l not in before]
        removed = [l for l in before if l not in out]
        self.assertTrue(all(l.startswith("  - ") or l == "  tags:" for l in added))
        self.assertEqual(removed, ["  tags: []"])

    def test_counts(self):
        _, _, report = self.run_plan()
        self.assertEqual(report["entries"], 3)
        self.assertEqual(report["tags"], 2 + 1 + 1)

    def test_a_second_run_is_a_no_op(self):
        _, out, _ = self.run_plan()
        start, end = it.find_images_block(out)
        entries = it.parse_entries(out, start, end)
        plan, report = it.build_plan(entries, self.MANIFEST, self.KEYWORDS)
        self.assertFalse(plan.touched())
        self.assertEqual(report["entries"], 0)

    def test_equal_ignoring_case_is_left_alone(self):
        manifest = dict(self.MANIFEST, b=["lizard", "photo"])
        text = YAML.replace("  - lizard", "  - Lizard")
        lines, entries = entries_of(text)
        plan, _ = it.build_plan(entries, manifest, self.KEYWORDS)
        out = plan.apply(lines)
        self.assertIn("  - Lizard", out)

    def test_a_tag_nobody_spells_aborts(self):
        with self.assertRaises(SystemExit):
            self.run_plan(keywords={})

    def test_a_manifest_of_another_data_file_aborts(self):
        with self.assertRaises(SystemExit):
            self.run_plan(manifest={"a": [], "b": [], "zzz": []})


class Manifest(unittest.TestCase):
    def write(self, root, per_lang):
        for lang, photos in per_lang.items():
            d = Path(root) / lang
            d.mkdir(parents=True)
            (d / "gallery-metadata.json").write_text(json.dumps(
                {"language": lang, "photos": [{"id": i, "tags": t} for i, t in photos.items()]}))

    def test_three_agreeing_languages_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, {l: {"a": ["fox"]} for l in ("en", "de", "sv")})
            self.assertEqual(it.load_manifest_tags(tmp), {"a": ["fox"]})

    def test_languages_that_disagree_abort(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, {"en": {"a": ["fox"]}, "de": {"a": ["fuchs"]}, "sv": {"a": ["fox"]}})
            with self.assertRaises(SystemExit):
                it.load_manifest_tags(tmp)

    def test_a_missing_build_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                it.load_manifest_tags(tmp)


if __name__ == "__main__":
    unittest.main()
