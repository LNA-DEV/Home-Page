"""The frozen history of old `_hu_` image URLs (scripts/legacy-image-variants.py).

What is tested is the decision (D6, docs/concepts/stable-image-urls.md §5.1):
an old hash gets a redirect only where the build history PROVES which variant it
was -- equal bytes, or the one variant of its source with the same pixel size and
format -- and never by "some image of the same source". And that the data file
is frozen: a rerun keeps every line and only adds.
"""

import shutil
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from _load import load

m = load("legacy-image-variants")


def png(w, h, seed=0):
    raw = b"".join(b"\x00" + bytes([seed]) * (w * 3) for _ in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def jpeg(w, h, tail=b""):
    """A minimal byte stream with an SOF0 header — enough for image_size."""
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, h, w, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 4) + b"\x00\x00" + sof + b"\xff\xd9" + tail


class Tree(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def put(self, rel, data):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p


class ImageSize(Tree):
    def test_png_and_jpeg_headers(self):
        self.assertEqual(m.image_size(self.put("a.png", png(7, 3))), (7, 3))
        self.assertEqual(m.image_size(self.put("a.jpg", jpeg(640, 427))), (640, 427))

    def test_webp_vp8x(self):
        head = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"VP8X" + b"\x00" * 8
        head += (1199).to_bytes(3, "little") + (629).to_bytes(3, "little")
        self.assertEqual(m.image_size(self.put("a.webp", head + b"\x00" * 40)), (1200, 630))

    def test_not_an_image_is_none(self):
        self.assertIsNone(m.image_size(self.put("a.txt", b"hello world")))


class Decide(Tree):
    """new = {source key: [variant]}, old = {(dir, hash): (source key, path)}."""

    def variant(self, rel, data, spec):
        p = self.put(f"site/{rel}", data)
        return {"path": "/" + rel, "spec": spec, "sha": m.sha256(p), "size": m.image_size(p),
                "format": m.fmt(rel)}

    def old(self, name, data):
        return self.put(f"cache/{name}", data)

    def test_equal_bytes_wins(self):
        a = self.variant("p/fit-600x600/a.jpg", jpeg(600, 400, b"A"), "fit-600x600")
        new = {"/p/a": [a]}
        old = {("/p/", "aa"): ("/p/a", self.old("a_hu_aa.jpg", jpeg(600, 400, b"A")))}
        lines, stats, amb = m.decide(old, new)
        self.assertEqual(lines[("/p/", "aa")]["path"], "/p/fit-600x600/a.jpg")
        self.assertEqual(stats["other"]["equal bytes"], 1)

    def test_one_variant_of_that_size_and_format_is_proof_enough(self):
        # The chain changed, so the bytes did; source, size and format did not.
        a = self.variant("p/resize-720x/a.jpg", jpeg(720, 480, b"new"), "resize-720x")
        b = self.variant("p/resize-360x/a.jpg", jpeg(360, 240, b"new"), "resize-360x")
        old = {("/p/", "bb"): ("/p/a", self.old("a_hu_bb.JPG", jpeg(720, 480, b"old")))}
        lines, stats, _ = m.decide(old, {"/p/a": [a, b]})
        self.assertEqual(lines[("/p/", "bb")]["path"], "/p/resize-720x/a.jpg")
        self.assertEqual(stats["other"]["same source, size, format"], 1)

    def test_two_candidates_of_that_size_are_left_out(self):
        # A 3:2 photo's `fit 600x600` and `fill 600x400` are both 600x400.
        a = self.variant("images/gallery/fit-600x600/x.jpg", jpeg(600, 400, b"1"), "fit-600x600")
        b = self.variant("images/gallery/fill-600x400/x.jpg", jpeg(600, 400, b"2"), "fill-600x400")
        old = {("/images/gallery/", "cc"): ("/images/gallery/ID", self.old("x_hu_cc.jpg", jpeg(600, 400, b"3")))}
        lines, stats, amb = m.decide(old, {"/images/gallery/ID": [a, b]})
        self.assertEqual(lines, {})
        self.assertEqual(stats["gallery"]["ambiguous"], 1)
        self.assertEqual(len(amb), 1)

    def test_a_different_size_or_format_is_no_proof(self):
        a = self.variant("p/resize-720x/a.webp", b"RIFF\x00\x00\x00\x00WEBPVP8X" + b"\x00" * 8
                         + (719).to_bytes(3, "little") + (479).to_bytes(3, "little") + b"\x00" * 40,
                         "resize-720x")
        old = {("/p/", "dd"): ("/p/a", self.old("a_hu_dd.jpg", jpeg(720, 480))),
               ("/p/", "ee"): ("/p/a", self.old("a_hu_ee.png", png(5, 5)))}
        lines, stats, _ = m.decide(old, {"/p/a": [a]})
        self.assertEqual(lines, {})
        self.assertEqual(stats["other"]["no match"], 2)

    def test_equal_bytes_of_another_source_is_no_proof(self):
        # The same picture in two language bundles: each language keeps its own.
        en = self.variant("en/p/resize-720x/a.jpg", jpeg(720, 480, b"same"), "resize-720x")
        old = {("/de/p/", "ff"): ("/de/p/a", self.old("a_hu_ff.jpg", jpeg(720, 480, b"same")))}
        lines, stats, _ = m.decide(old, {"/en/p/a": [en]})
        self.assertEqual(lines, {})
        self.assertEqual(stats["other"]["source gone"], 1)


class Frozen(Tree):
    def test_a_rerun_keeps_every_line(self):
        out = self.root / "legacy.yaml"
        text = m.render({"abc123": ["id-1", "fit-600x600"]},
                        {"/en/x/_hu_def": "/en/x/resize-720x/A Cover \"quoted\".jpg"})
        out.write_text(text, encoding="utf-8")
        gallery, other = m.read_existing(out)
        self.assertEqual(gallery, {"abc123": ["id-1", "fit-600x600"]})
        self.assertEqual(other, {"/en/x/_hu_def": "/en/x/resize-720x/A Cover \"quoted\".jpg"})
        self.assertEqual(m.render(gallery, other), text)

    def test_hash_keys_are_quoted(self):
        # An all-digit hash, or one like 1234e56, would be a YAML number.
        text = m.render({"1234e56": ["id", "fit-600x600"]}, {})
        self.assertIn('  "1234e56": ["id", "fit-600x600"]', text)


if __name__ == "__main__":
    unittest.main()
