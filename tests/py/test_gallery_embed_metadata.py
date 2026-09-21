"""The metadata embedding step, as pure functions.

The run itself is 3m40s over 4,161 files and stays in deploy.sh. What is tested
here is what it decides: which tags it writes, which it refuses to write, and
that two runs of the same input produce the same bytes — the property that makes
the pass idempotent and keeps rsync from transferring anything for it.
"""

import json
import tempfile
import unittest
from pathlib import Path

from _load import load

m = load("gallery-embed-metadata")


def record(**over):
    base = {
        "id": "a8ae6f92-8c46-404d-9567-f7b3ec299b28",
        "src": "Red Fox.jpg",
        "artist": "Lukas Nagel",
        "title": "Red Fox",
        "description": "A red fox in the snow.",
        "dateTaken": "2025-12-28",
        "tags": ["fox", "winter"],
        "license": {
            "key": "cc-by-sa-4.0",
            "terms": "Licensed under CC BY-SA 4.0",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/",
        },
    }
    base.update(over)
    return base


def args_for(rec=None, *, languages=("en",), year="2025", copy_exif=False, is_variant=False,
             extra=None):
    full = {"en": rec or record()}
    if extra:
        full.update(extra)
    return m.photo_args(full, list(languages), Path("/out/Red Fox.jpg"),
                        Path("/src/Red Fox.jpg"), year, copy_exif, is_variant)


def tag_value(args, tag):
    prefix = f"-{tag}="
    return [a[len(prefix):] for a in args if a.startswith(prefix)]


class Clip(unittest.TestCase):
    def test_a_value_over_the_iim_limit_is_cut(self):
        tag, limit = next(iter(m.IPTC_LIMITS.items()))
        self.assertEqual(len(m.clip(tag, "x" * (limit + 50))), limit)

    def test_a_short_value_is_untouched(self):
        tag = next(iter(m.IPTC_LIMITS))
        self.assertEqual(m.clip(tag, "short"), "short")

    def test_a_tag_with_no_limit_is_untouched(self):
        self.assertEqual(m.clip("XMP-dc:Description", "x" * 5000), "x" * 5000)


class LangValues(unittest.TestCase):
    def test_a_translation_is_kept(self):
        rec = {"en": {"title": "Red Fox"}, "de": {"title": "Rotfuchs"}}
        self.assertEqual(m.lang_values(rec, "title", ["en", "de"]), {"de": "Rotfuchs"})

    def test_a_language_equal_to_english_is_dropped(self):
        # The fallback already renders it; writing it twice is noise in the file.
        rec = {"en": {"title": "Red Fox"}, "sv": {"title": "Red Fox"}}
        self.assertEqual(m.lang_values(rec, "title", ["en", "sv"]), {})

    def test_a_missing_language_is_dropped(self):
        rec = {"en": {"title": "Red Fox"}}
        self.assertEqual(m.lang_values(rec, "title", ["en", "de", "sv"]), {})

    def test_the_default_language_is_never_a_key(self):
        rec = {"en": {"title": "Red Fox"}, "de": {"title": "Rotfuchs"}}
        self.assertNotIn("en", m.lang_values(rec, "title", ["en", "de"]))


class PhotoArgs(unittest.TestCase):
    def test_orientation_is_never_copied(self):
        # AutoOrient bakes the rotation into a variant's pixels; copying the tag
        # would rotate it a second time in any viewer that honours it.
        self.assertNotIn("Orientation", m.COPY_TAGS)
        args = args_for(copy_exif=True)
        self.assertFalse([a for a in args if "Orientation" in a], args)

    def test_the_copyright_notice_is_a_notice_not_a_licence_name(self):
        args = args_for()
        self.assertEqual(tag_value(args, "XMP-dc:Rights"), ["© 2025 Lukas Nagel"])

    def test_an_unknown_capture_year_writes_no_year(self):
        # The build year would both assert a wrong year and rewrite those files
        # every New Year's Day.
        args = args_for(year="")
        self.assertEqual(tag_value(args, "XMP-dc:Rights"), ["© Lukas Nagel"])

    def test_colorspace_is_set_on_a_variant_only(self):
        self.assertIn("-EXIF:ColorSpace=sRGB", args_for(is_variant=True))
        self.assertNotIn("-EXIF:ColorSpace=sRGB", args_for(is_variant=False))

    def test_the_uuid_is_written_as_the_digital_image_guid(self):
        args = args_for()
        self.assertEqual(tag_value(args, "XMP-iptcExt:DigitalImageGUID"),
                         ["a8ae6f92-8c46-404d-9567-f7b3ec299b28"])

    def test_urls_are_clearnet_even_in_the_tor_build(self):
        # An onion address inside a JPEG is not a useful licensor contact.
        args = args_for()
        for value in tag_value(args, "XMP-plus:LicensorURL") + tag_value(args, "XMP-iptcCore:CreatorWorkURL"):
            self.assertTrue(value.startswith("https://lna-dev.net"), value)
        self.assertFalse([a for a in args if ".onion" in a])

    def test_every_xmp_field_has_its_iim_spelling_beside_it(self):
        args = args_for()
        for xmp, iim in (("XMP-dc:Creator", "IPTC:By-line"),
                         ("XMP-dc:Rights", "IPTC:CopyrightNotice"),
                         ("XMP-dc:Title", "IPTC:ObjectName"),
                         ("XMP-dc:Description", "IPTC:Caption-Abstract"),
                         ("XMP-photoshop:Credit", "IPTC:Credit")):
            with self.subTest(xmp=xmp):
                self.assertTrue(tag_value(args, xmp), xmp)
                self.assertTrue(tag_value(args, iim), iim)

    def test_the_strip_list_is_applied_first(self):
        # Nothing written below may be undone by a later deletion.
        args = args_for()
        first_write = next(i for i, a in enumerate(args) if a.endswith("=UTF8"))
        last_strip = max(i for i, a in enumerate(args) if a.endswith("="))
        self.assertLess(last_strip, first_write)

    def test_what_is_stripped(self):
        args = args_for()
        stripped = {a[1:-1] for a in args if a.endswith("=") and a.startswith("-")}
        for tag in ("GPS*", "IFD1:all", "XMP-darktable:all", "XMP-acdsee:all"):
            with self.subTest(tag=tag):
                self.assertIn(tag, m.STRIP_TAGS)
        self.assertTrue(stripped.issuperset(set(m.STRIP_TAGS)))

    def test_the_icc_profile_is_left_alone(self):
        # Colour depends on it.
        self.assertFalse([t for t in m.STRIP_TAGS if "ICC" in t.upper()])

    def test_translations_are_written_with_a_language_suffix(self):
        args = args_for(extra={"de": {"title": "Rotfuchs", "id": "x"}}, languages=("en", "de"))
        self.assertIn("-XMP-dc:Title-de=Rotfuchs", args)

    def test_every_tag_is_written_to_both_namespaces(self):
        # The empty value each of these opens with is the strip line: the keyword
        # lists are cleared before they are rewritten, or a re-run would append.
        args = args_for()
        self.assertEqual([v for v in tag_value(args, "XMP-dc:Subject") if v], ["fox", "winter"])
        self.assertEqual([v for v in tag_value(args, "IPTC:Keywords") if v], ["fox", "winter"])
        self.assertEqual(tag_value(args, "XMP-dc:Subject")[0], "")

    def test_the_target_is_the_last_argument(self):
        self.assertEqual(args_for()[-1], "/out/Red Fox.jpg")


class BuildArgfile(unittest.TestCase):
    def jobs(self):
        return [({"en": record()}, Path("/out/Red Fox.jpg"), Path("/src/Red Fox.jpg"))]

    def test_the_same_jobs_produce_the_same_bytes(self):
        # The whole pass is deterministic, which is what makes it idempotent and
        # keeps rsync from transferring anything extra for it.
        a = m.build_argfile(self.jobs(), ["en"], {"Red Fox.jpg": "2025"}, {"Red Fox.jpg"})
        b = m.build_argfile(self.jobs(), ["en"], {"Red Fox.jpg": "2025"}, {"Red Fox.jpg"})
        self.assertEqual(a, b)

    def test_each_command_ends_with_execute(self):
        text = m.build_argfile(self.jobs(), ["en"], {}, set())
        self.assertEqual(text.strip().splitlines()[-1], "-execute")

    def test_the_capture_year_falls_back_to_the_manifest_date(self):
        text = m.build_argfile(self.jobs(), ["en"], {}, set())
        self.assertIn("© 2025 Lukas Nagel", text)

    def test_a_photo_with_no_date_at_all_gets_no_year(self):
        jobs = [({"en": record(dateTaken="")}, Path("/out/a.jpg"), Path("/src/a.jpg"))]
        text = m.build_argfile(jobs, ["en"], {}, set())
        self.assertIn("© Lukas Nagel", text)
        self.assertNotIn("© 2", text)

    def test_a_source_that_carries_no_camera_data_skips_the_copy_block(self):
        text = m.build_argfile(self.jobs(), ["en"], {}, set())
        self.assertNotIn("-tagsFromFile", text)
        text = m.build_argfile(self.jobs(), ["en"], {}, {"Red Fox.jpg"})
        self.assertIn("-tagsFromFile", text)


class LoadManifests(unittest.TestCase):
    def write(self, **by_lang):
        root = Path(tempfile.mkdtemp())
        for lang, photos in by_lang.items():
            d = root / lang
            d.mkdir()
            (d / m.MANIFEST_NAME).write_text(
                json.dumps({"language": lang, "count": len(photos), "photos": photos}),
                encoding="utf-8")
        return root

    def test_three_languages_merge_on_id(self):
        root = self.write(
            en=[{"id": "1", "title": "Red Fox"}],
            de=[{"id": "1", "title": "Rotfuchs"}],
            sv=[{"id": "1", "title": "Rödräv"}],
        )
        by_id, languages = m.load_manifests(root)
        self.assertEqual(languages, ["de", "en", "sv"])
        self.assertEqual(by_id["1"]["de"]["title"], "Rotfuchs")

    def test_a_photo_missing_from_english_stops_the_run(self):
        root = self.write(en=[{"id": "1"}], de=[{"id": "1"}, {"id": "2"}])
        with self.assertRaises(SystemExit):
            m.load_manifests(root)

    def test_no_manifest_at_all_stops_the_run(self):
        with self.assertRaises(SystemExit):
            m.load_manifests(Path(tempfile.mkdtemp()))


if __name__ == "__main__":
    unittest.main()
