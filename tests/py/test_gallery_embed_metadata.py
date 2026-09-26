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
        "file": "red-fox.jpg",
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
             extra=None, copy_original=False):
    full = {"en": rec or record()}
    if extra:
        full.update(extra)
    return m.photo_args(full, list(languages), Path("/out/red-fox.jpg"),
                        Path("/src/Red Fox.jpg"), year, copy_exif, is_variant, copy_original)


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
    def test_a_variant_never_gets_orientation(self):
        # AutoOrient bakes the rotation into a variant's pixels; copying the tag
        # would rotate it a second time in any viewer that honours it.
        self.assertNotIn("Orientation", m.COPY_TAGS)
        args = args_for(copy_exif=True, is_variant=True, copy_original=True)
        self.assertFalse([a for a in args if "Orientation" in a], args)

    def test_the_original_keeps_its_orientation_and_colorspace(self):
        # Its pixels are the source's, unrotated, and it is cleared first — so the
        # tag has to be copied back or 22 rotated originals would lie on their side.
        args = args_for(copy_exif=True, copy_original=True)
        self.assertIn("-Orientation", args)
        self.assertIn("-ColorSpace", args)
        i = args.index("-tagsFromFile")
        self.assertEqual(args[i + 1], "/src/Red Fox.jpg")

    def test_a_source_with_only_an_orientation_is_copied_for_the_original_alone(self):
        self.assertIn("-Orientation", args_for(copy_original=True))
        self.assertNotIn("-tagsFromFile", args_for(copy_original=True, is_variant=True))

    def test_every_file_is_cleared_first_except_the_icc_profile(self):
        # The denylist left the raw file's name, file tags, drone altitude and a
        # phone's unedited frame in the originals; clear-then-write cannot.
        for variant in (False, True):
            with self.subTest(variant=variant):
                args = args_for(is_variant=variant)
                self.assertEqual(args[:2], ["-all=", "--ICC_Profile:all"])

    def test_the_exif_caption_is_the_description(self):
        self.assertEqual(tag_value(args_for(), "EXIF:ImageDescription"), ["A red fox in the snow."])

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
        self.assertEqual(args_for()[-1], "/out/red-fox.jpg")


class IsVariant(unittest.TestCase):
    def test_the_published_original_is_the_file_name(self):
        rec = {"en": record()}
        self.assertFalse(m.is_variant(rec, Path("/out/red-fox.jpg")))
        self.assertTrue(m.is_variant(rec, Path("/out/red-fox_hu_1f1561eb0ac2d2ce.jpg")))
        # The store filename is not what is served.
        self.assertTrue(m.is_variant(rec, Path("/out/Red Fox.jpg")))


def good_readback(rec=None, languages=("en",), extra=None, variant=False):
    """What `exiftool -j -G1` reads back from a correctly written file."""
    rec = rec or record()
    full = {"en": rec, **(extra or {})}
    got = {"SourceFile": "/out/red-fox.jpg", "File:FileSize": "1 MB", "ExifTool:ExifToolVersion": 13.5,
           "IFD0:Copyright": "© 2025 Lukas Nagel", "XMP-dc:Rights": "© 2025 Lukas Nagel",
           "IPTC:CopyrightNotice": "© 2025 Lukas Nagel", "IFD0:Make": "NIKON CORPORATION",
           "ICC_Profile:ProfileDescription": "sRGB"}
    for tag, value in m.expected_editorial(full, list(languages)).items():
        if value is not None and value != []:
            got[tag] = value[0] if isinstance(value, list) and len(value) == 1 else value
    if not variant:
        got["IFD0:Orientation"] = "Rotate 90 CW"
    return full, got


class Check(unittest.TestCase):
    def problems(self, mutate=None, variant=False, languages=("en",), extra=None):
        full, got = good_readback(languages=languages, extra=extra, variant=variant)
        if mutate:
            mutate(got)
        return m.check_file(got, full, list(languages), variant)

    def test_a_correct_file_passes(self):
        self.assertEqual(self.problems(), [])
        self.assertEqual(self.problems(variant=True), [])

    def test_a_wrong_title_is_caught(self):
        p = self.problems(lambda g: g.update({"XMP-dc:Title": "Wrong"}))
        self.assertTrue(any("XMP-dc:Title" in x for x in p), p)

    def test_a_missing_translation_is_caught(self):
        extra = {"de": {"id": "x", "title": "Rotfuchs"}}
        p = self.problems(lambda g: g.pop("XMP-dc:Title-de"), languages=("en", "de"), extra=extra)
        self.assertTrue(any("Title-de" in x for x in p), p)

    def test_a_translation_equal_to_english_must_be_absent(self):
        extra = {"de": {"id": "x", "title": "Red Fox"}}
        p = self.problems(lambda g: g.update({"XMP-dc:Title-de": "Red Fox"}),
                          languages=("en", "de"), extra=extra)
        self.assertTrue(any("expected nothing" in x for x in p), p)

    def test_a_surplus_or_missing_tag_is_caught(self):
        p = self.problems(lambda g: g.update({"XMP-dc:Subject": ["fox", "winter", "zsl_sdr"]}))
        self.assertTrue(any("XMP-dc:Subject" in x for x in p), p)
        p = self.problems(lambda g: g.update({"IPTC:Keywords": "fox"}))
        self.assertTrue(any("IPTC:Keywords" in x for x in p), p)

    def test_a_stray_group_is_caught(self):
        for key in ("XMP-xmpMM:DerivedFrom", "XMP-microsoft:LastKeywordXMP", "MPF0:MPFVersion",
                    "XMP-drone-dji:AbsoluteAltitude", "XMP-GImage:ImageData", "IFD1:ThumbnailImage"):
            with self.subTest(key=key):
                p = self.problems(lambda g: g.update({key: "x"}))
                self.assertIn(f"stray metadata: {key}", p)

    def test_gps_and_serials_are_banned_even_in_an_allowed_group(self):
        for key in ("IFD0:GPSLatitude", "ExifIFD:SerialNumber", "XMP-dc:GPSAltitude"):
            with self.subTest(key=key):
                p = self.problems(lambda g: g.update({key: "x"}))
                self.assertIn(f"banned tag: {key}", p)

    def test_a_variant_with_orientation_is_caught(self):
        p = self.problems(lambda g: g.update({"IFD0:Orientation": "Rotate 90 CW"}), variant=True)
        self.assertTrue(any("Orientation" in x for x in p), p)

    def test_the_notice_must_agree_in_all_three_places(self):
        p = self.problems(lambda g: g.update({"IPTC:CopyrightNotice": "Creative Commons"}))
        self.assertTrue(any("copyright notice" in x for x in p), p)
        self.assertEqual(self.problems(lambda g: g.update({
            "IFD0:Copyright": "© Lukas Nagel", "XMP-dc:Rights": "© Lukas Nagel",
            "IPTC:CopyrightNotice": "© Lukas Nagel"})), [])


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


def jpeg(app1=b"Exif\x00\x00meta", scan=b"\x12\x34" * 1000):
    """A minimal marker-level JPEG: SOI, APP1, DQT, SOS, entropy data, EOI."""
    seg = lambda code, body: b"\xff" + bytes([code]) + (len(body) + 2).to_bytes(2, "big") + body
    return (b"\xff\xd8" + seg(0xE1, app1) + seg(0xDB, b"\x00" * 65)
            + seg(0xDA, b"\x01\x01\x00\x00\x3f\x00") + scan + b"\xff\xd9")


class ScanDigest(unittest.TestCase):
    """The pixel check that does not go through the name mapping."""

    def digest(self, data):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fh:
            fh.write(data)
        try:
            return m.scan_digest(fh.name)
        finally:
            Path(fh.name).unlink()

    def test_rewritten_metadata_does_not_change_it(self):
        # What exiftool does to a file: segments before the scan change, the
        # image data does not.
        self.assertEqual(self.digest(jpeg(app1=b"Exif\x00\x00a")),
                         self.digest(jpeg(app1=b"Exif\x00\x00" + b"b" * 5000)))

    def test_other_pixels_change_it(self):
        self.assertNotEqual(self.digest(jpeg(scan=b"\x01" * 100)), self.digest(jpeg(scan=b"\x02" * 100)))

    def test_not_a_jpeg_is_none(self):
        self.assertIsNone(self.digest(b"PNG\r\n"))
        self.assertIsNone(self.digest(b"\xff\xd8\xff\xe1\x00"))


if __name__ == "__main__":
    unittest.main()
