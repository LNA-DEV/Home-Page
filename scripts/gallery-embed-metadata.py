#!/usr/bin/env python3
"""Write the gallery's metadata into the JPEGs the site actually serves.

Hugo re-encodes every image variant and writes no metadata segment at all, so a
visitor who downloads a photo gets a file with no licence, no creator and no
title -- while the untouched original is published alongside it carrying camera
serial numbers, GPS coordinates and an embedded thumbnail of the uncropped frame.
This pass inverts that, over everything under public/images/gallery/, the
published original included. See docs/concepts/gallery-metadata-single-source.md.

    hugo  ->  scripts/gallery-embed-metadata.py public/  ->  rsync

Only build OUTPUT is written. The photo store is darktable's export target and a
Nextcloud folder; nothing here opens a file there for writing.

It resolves nothing itself. Every value comes from the manifests Hugo renders at
public/<lang>/gallery-metadata.json -- the same numbers the pages show, resolved
once, by collect-images.html. The technical half (camera, lens, exposure, date,
software) is copied straight out of the source original by exiftool in the same
call. A second, Python-side resolver would be a second thing to keep in step.

Every served file — variant or published original — is CLEARED first (all
metadata except the ICC profile), then gets the technical allowlist copied from
the source and the editorial set written from the manifest. The originals used to
be stripped from a denylist instead, and kept whatever nobody had listed: the raw
file's name, tags from the file, drone altitude, a phone's unedited frame
(docs/concepts/gallery-metadata-yaml-only.md §6).

The build publishes each photo under its English slug, not the store filename
(same concept, §5), so a served file is mapped back to its photo through the
manifest's `file` field, and to its source through `src`.

Two modes:

    (default)   clear, copy and write every file
    --check     read every file back and compare it with the manifest: every
                editorial field, no metadata group outside the allowlist, and
                the published original's pixels against the store file's

Standard library only, plus exiftool -- the one external dependency, and the
reason this is not a Hugo template.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gallery_common import (  # noqa: E402
    PHOTOS_SETUP_HINT,
    photos_dir_from_hugo_mounts,
    published_base,
    repo_root,
)

# Where the gallery lives inside the build output, and how a manifest is named.
GALLERY_SUBDIR = Path("images") / "gallery"
MANIFEST_NAME = "gallery-metadata.json"
DEFAULT_LANG = "en"

# Always the clearnet site, in the Tor build too: deploy.sh builds twice and
# serves the same files from both, and an onion address inside a JPEG is not a
# useful licensor contact for whoever ends up with the file.
SITE_URL = "https://lna-dev.net"
LICENSING_URL = f"{SITE_URL}/{DEFAULT_LANG}/licensing/"
PHOTO_URL = f"{SITE_URL}/{DEFAULT_LANG}/gallery/photo/%s/"
IPTC_DIGITAL_CAPTURE = "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"

# What the copyright notice says when the capture year is unknown -- 92 of the 648
# photos, because 87 carry an unset camera clock (2000:01:01) on top of the 5 with
# no DateTimeOriginal at all. The notice then simply has no year: "© Lukas Nagel"
# is valid and standard, whereas the build year would assert 2026 on a photo taken
# years earlier AND would change the file on every New Year's Day, costing the step
# the byte-for-byte determinism that keeps it out of rsync's way.
COPYRIGHT_SYMBOL = "©"

# Copied from the source original, by name. NEVER Orientation: Hugo's AutoOrient
# bakes the rotation into the pixels of every variant, so copying the tag would
# rotate them a second time in any viewer that honours it. The published original
# keeps whatever it has, its pixels being untouched.
COPY_TAGS = [
    "Make",
    "Model",
    "LensModel",
    "FNumber",
    "ExposureTime",
    "ISO",
    "FocalLength",
    "FocalLengthIn35mmFormat",
    "DateTimeOriginal",
    "OffsetTimeOriginal",
    "Software",
]

# Copied for the published ORIGINAL only. Its pixels are the source's, unrotated,
# so it needs the source's Orientation to display the right way up (22 originals
# are rotated), and its own ColorSpace belongs with its own ICC profile — 86 of
# them legitimately pair "Uncalibrated" with an sRGB profile. A variant gets
# neither: its rotation is baked in, and its ColorSpace is set to sRGB below.
ORIGINAL_ONLY_TAGS = ["Orientation", "ColorSpace"]

# Step 1 of every file: delete ALL metadata except the ICC profile, which colour
# depends on. Verified on scratch copies (2026-09-26): this also drops the MPF
# preview image, a phone's GImage/GDepth extended XMP (the unedited frame and a
# depth map) and an appended Google HDR+ burst, leaves the ICC profile and the
# pixel data byte-identical, and a second run produces the same bytes.
CLEAR_ARGS = ["-all=", "--ICC_Profile:all"]

# The old denylist. CLEAR_ARGS has already removed all of it; it stays as a second
# net and as the record of what must never come back — the check below bans the
# same things by name on top of its group allowlist.
#
# Rating appears twice on purpose: a first pass that stripped only XMP-xmp:Rating
# left IFD0:Rating standing, so the group-less spelling does the work and the
# explicit one documents where the leftover was.
STRIP_TAGS = [
    "SerialNumber",
    "BodySerialNumber",
    "InternalSerialNumber",
    "LensSerialNumber",
    "MakerNotes:all",
    "GPS*",          # the EXIF GPS IFD and any XMP copy of it
    "IFD1:all",      # the embedded thumbnail -- it can show the uncropped frame
    "ThumbnailImage",
    "Rating",
    "RatingPercent",
    "XMP-xmp:Rating",
    "XMP-xmp:Label",     # darktable colour labels
    "XMP-darktable:all",
    "XMP-acdsee:all",    # darktable's notes field; goes out as dc:description
    "IPTC:Keywords",     # replaced below by the resolved list
    "XMP-dc:Subject",
]

# IPTC-IIM is a fixed-width format: exiftool refuses a value over the limit rather
# than truncating it. The XMP spelling of each of these has no limit and carries
# the full value, so clipping the IIM copy loses nothing that is not also written
# in full next to it.
IPTC_LIMITS = {
    "IPTC:ObjectName": 64,
    "IPTC:Keywords": 64,
    "IPTC:Caption-Abstract": 2000,
    "IPTC:Credit": 32,
    "IPTC:By-line": 32,
    "IPTC:CopyrightNotice": 128,
}

EXIF_DATE_RE = re.compile(r"^(\d{4})")


def parse_args(argv):
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "public",
        nargs="?",
        type=Path,
        default=root / "public",
        help="Hugo's build output (default: <repo>/public)",
    )
    parser.add_argument(
        "--photos",
        type=Path,
        default=photos_dir_from_hugo_mounts(root),
        help="the photo store, i.e. the gallery mount `source` in "
        "config/_default/module.yaml -- read only, for the technical EXIF",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify instead of write: every file must say what the manifest says, "
        "carry nothing else, and (for an original) have its store file's pixels",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve and build the exiftool arguments, then stop",
    )
    parser.add_argument(
        "--save-args",
        type=Path,
        help="also write the generated exiftool argument file here, to read",
    )
    parser.add_argument(
        "--exiftool",
        default="exiftool",
        help="exiftool executable (default: exiftool)",
    )
    return parser.parse_args(argv)


def die(message):
    sys.exit(f"ERROR: {message}")


def load_manifests(public):
    """Return (records_by_id, languages). Each record is {lang: manifest entry}."""
    manifests = sorted(public.glob(f"*/{MANIFEST_NAME}"))
    if not manifests:
        die(
            f"no {MANIFEST_NAME} under {public}/*/ — run `hugo` first.\n"
            "       (the manifest is the `gallerymeta` output format in hugo.yaml)"
        )

    by_id = {}
    languages = []
    for path in manifests:
        data = json.loads(path.read_text(encoding="utf-8"))
        lang = data.get("language") or path.parent.name
        languages.append(lang)
        for entry in data.get("photos", []):
            by_id.setdefault(entry["id"], {})[lang] = entry

    if DEFAULT_LANG not in languages:
        die(f"no {DEFAULT_LANG} manifest among {languages} — nothing to fall back to")

    incomplete = [pid for pid, langs in by_id.items() if DEFAULT_LANG not in langs]
    if incomplete:
        die(
            f"{len(incomplete)} photo(s) missing from the {DEFAULT_LANG} manifest, "
            f"e.g. {incomplete[0]} — the three builds disagree; rebuild"
        )
    return by_id, sorted(set(languages))


def read_sources(sources, exiftool):
    """One read pass over the photo store: (capture years, sources worth copying,
    sources with an Orientation/ColorSpace worth copying to the original).

    A year at or below 2000 is discarded, which is the same rule the site applies
    to a photo's date everywhere else: a camera with an unset clock stamps
    2000:01:01, and 87 files here carry exactly that. "© 2000" would be a worse
    answer than the build year, not a better one.

    The second return value is the set of sources that carry at least one of
    COPY_TAGS. A handful carry none, and asking exiftool to copy from them prints
    a "No writable tags set" warning per output file — 20 lines of noise for a
    file that simply has no camera data, so those skip the copy block entirely.
    The third is the same for ORIGINAL_ONLY_TAGS (Orientation, ColorSpace), which
    only the published original asks for.
    """
    if not sources:
        return {}, set(), set()
    args = [exiftool, "-q", "-m", "-j", "-charset", "filename=UTF8"]
    args.extend("-" + tag for tag in COPY_TAGS + ORIGINAL_ONLY_TAGS)
    args.extend(str(p) for p in sources)
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if not proc.stdout.strip():
        return {}, set(), set()
    years = {}
    copyable = set()
    original_copyable = set()
    for record in json.loads(proc.stdout):
        name = Path(record["SourceFile"]).name
        match = EXIF_DATE_RE.match(str(record.get("DateTimeOriginal", "")))
        if match and int(match.group(1)) > 2000:
            years[name] = match.group(1)
        if any(record.get(tag) is not None for tag in COPY_TAGS):
            copyable.add(name)
        if any(record.get(tag) is not None for tag in ORIGINAL_ONLY_TAGS):
            original_copyable.add(name)
    return years, copyable, original_copyable


def clip(tag, value):
    limit = IPTC_LIMITS.get(tag)
    return value[:limit] if limit and len(value) > limit else value


def lang_values(record, field, languages):
    """{lang: value} for one field, dropping languages equal to the default."""
    base = record[DEFAULT_LANG].get(field) or ""
    out = {}
    for lang in languages:
        if lang == DEFAULT_LANG or lang not in record:
            continue
        value = record[lang].get(field) or ""
        if value and value != base:
            out[lang] = value
    return out


def photo_args(record, languages, target, source, year, copy_exif, is_variant,
               copy_original=False):
    """The exiftool arguments for one output file, one per line."""
    base = record[DEFAULT_LANG]
    args = []

    def put(tag, value):
        if value:
            args.append(f"-{tag}={clip(tag, str(value))}")

    def put_lang(tag, field):
        put(tag, base.get(field))
        for lang, value in lang_values(record, field, languages).items():
            args.append(f"-{tag}-{lang}={value}")

    # 1. Clear first, so nothing below can be undone by a deletion and nothing
    #    the source carried survives unless it is written again below.
    args.extend(CLEAR_ARGS)
    args.extend(f"-{tag}=" for tag in STRIP_TAGS)

    # 2. Technical half, straight from the untouched source. The original also
    #    keeps its Orientation and ColorSpace (ORIGINAL_ONLY_TAGS). Each block is
    #    asked for only when the source has something for it: exiftool warns
    #    "No writable tags set" once per output file otherwise.
    copied = list(COPY_TAGS) if copy_exif else []
    if copy_original and not is_variant:
        copied += ORIGINAL_ONLY_TAGS
    if copied:
        args.append("-tagsFromFile")
        args.append(str(source))
        args.extend(f"-{tag}" for tag in copied)

    # Hugo re-encodes a variant and drops the source's ICC profile, and exiftool
    # fills the mandatory ColorSpace of the EXIF block it is about to create with
    # "Uncalibrated" — which tells a colour-managed viewer the pixels are NOT
    # sRGB. They are: every profile in this library is an sRGB variant and Hugo
    # does no colour conversion. So a variant says so explicitly. The published
    # original is left alone: its own ColorSpace and its ICC profile are intact,
    # and 86 of them legitimately pair "Uncalibrated" with an sRGB profile.
    if is_variant:
        args.append("-EXIF:ColorSpace=sRGB")

    # 3. Editorial half, from the manifest.
    #    IPTC-IIM is written beside every XMP field because older software reads
    #    only IIM; CodedCharacterSet is what makes those values legal as UTF-8.
    artist = base.get("artist") or ""
    credit = f"{artist} / lna-dev.net" if artist else "lna-dev.net"
    notice = " ".join(part for part in (COPYRIGHT_SYMBOL, year, artist) if part)
    licence = base.get("license") or {}

    put("IPTC:CodedCharacterSet", "UTF8")

    put("XMP-dc:Creator", artist)
    put("EXIF:Artist", artist)
    put("IPTC:By-line", artist)

    put("XMP-dc:Rights", notice)
    put("EXIF:Copyright", notice)
    put("IPTC:CopyrightNotice", notice)

    put("XMP-xmpRights:Marked", "True")
    put("XMP-xmpRights:UsageTerms", licence.get("terms"))
    for lang in languages:
        if lang == DEFAULT_LANG or lang not in record:
            continue
        terms = (record[lang].get("license") or {}).get("terms")
        if terms and terms != licence.get("terms"):
            args.append(f"-XMP-xmpRights:UsageTerms-{lang}={terms}")

    # WebStatement and cc:license are plain URIs with no language alternative, so
    # they get the default language's deed; the translated deeds are on the page.
    url = licence.get("url") or ""
    if url.startswith("/"):
        url = SITE_URL + url
    put("XMP-xmpRights:WebStatement", url)
    put("XMP-cc:License", url)
    put("XMP-plus:LicensorURL", LICENSING_URL)

    put("XMP-photoshop:Credit", credit)
    put("IPTC:Credit", credit)
    put("XMP-iptcCore:CreatorWorkURL", SITE_URL)

    put("XMP-iptcExt:DigitalImageGUID", base["id"])
    put("XMP-dc:Identifier", PHOTO_URL % base["id"])
    put("XMP-iptcExt:DigitalSourceType", IPTC_DIGITAL_CAPTURE)

    put_lang("XMP-dc:Title", "title")
    put("IPTC:ObjectName", base.get("title"))
    put_lang("XMP-dc:Description", "description")
    put("IPTC:Caption-Abstract", base.get("description"))
    # The EXIF caption field older software reads, paired with dc:description the
    # way Artist and Copyright are paired above (MWG). It used to keep the file's
    # own stale English caption on the originals.
    put("EXIF:ImageDescription", base.get("description"))

    # Tags are language-neutral and come from data/gallery.yaml alone
    # (lowercased by gallery-meta.html); nothing the camera or darktable wrote
    # into the file's own keyword fields reaches an output file.
    for tag in base.get("tags") or []:
        args.append(f"-XMP-dc:Subject={tag}")
        args.append(f"-IPTC:Keywords={clip('IPTC:Keywords', tag)}")

    args.append(str(target))
    return args


def is_variant(record, target):
    """True for a rendered variant, False for the published original.

    The original is published under the photo's `file` name; every variant is
    that name with Hugo's `_hu_<hash>` marker.
    """
    return target.name != record[DEFAULT_LANG]["file"]


def build_argfile(jobs, languages, years, copyable, original_copyable=frozenset()):
    """The whole run as one exiftool argument file, commands split by -execute."""
    lines = []
    for record, target, source in jobs:
        # No build-year fallback: an unknown year means no year in the notice.
        year = years.get(source.name) or record[DEFAULT_LANG].get("dateTaken", "")[:4]
        lines.append("-overwrite_original")
        lines.append("-m")
        lines.append("-charset")
        lines.append("UTF8")
        lines.append("-charset")
        lines.append("filename=UTF8")
        lines.extend(photo_args(record, languages, target, source, year,
                                source.name in copyable, is_variant(record, target),
                                source.name in original_copyable))
        lines.append("-execute")
    return "\n".join(lines) + "\n"


def run_exiftool(exiftool, argfile, quiet_args=("-q", "-q")):
    proc = subprocess.run(
        [exiftool, *quiet_args, "-@", str(argfile)],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc


# --- the check ----------------------------------------------------------------
#
# `--check` stands between the build and rsync on every deploy. It reads every
# served file back and holds it against the manifest, so "the file says what
# data/gallery.yaml says, and nothing else" is verified for all of them, not
# assumed (docs/concepts/gallery-metadata-yaml-only.md §6).

# Metadata groups (exiftool's family 1) a served file may contain. Everything the
# pass writes, the technical EXIF it copies, the ICC profile it keeps, and
# exiftool's own pseudo-groups. A group outside this set fails the deploy: a new
# camera, phone or export tool that adds one is stopped instead of shipped.
ALLOWED_GROUPS = {
    "ExifTool", "File", "System",
    "IFD0", "ExifIFD",
    "IPTC", "Photoshop",
    "XMP-x", "XMP-dc", "XMP-xmpRights", "XMP-cc", "XMP-plus", "XMP-photoshop",
    "XMP-iptcCore", "XMP-iptcExt",
    "ICC_Profile", "ICC-header", "ICC-view", "ICC-meas", "ICC-chrm",
}

# Banned by name on top of the group allowlist, because these are the leaks the
# pass exists to stop and they must stay stopped even inside an allowed group.
BANNED_TAG_RE = re.compile(r"(?i)(^|:)GPS|serial")


def as_list(value):
    if value is None:
        return []
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def expected_editorial(record, languages):
    """{tag: value or [values]} a served file must carry, from its manifest record.

    Mirrors what photo_args writes, spelled the way `exiftool -j -G1` reads it
    back. A translation equal to the English value is not written, so it must be
    ABSENT (None) rather than present.
    """
    base = record[DEFAULT_LANG]
    exp = {
        "XMP-iptcExt:DigitalImageGUID": base["id"],
        "XMP-dc:Title": base.get("title") or None,
        "IPTC:ObjectName": clip("IPTC:ObjectName", base["title"]) if base.get("title") else None,
        "XMP-dc:Description": base.get("description") or None,
        "IPTC:Caption-Abstract": (clip("IPTC:Caption-Abstract", base["description"])
                                  if base.get("description") else None),
        "IFD0:ImageDescription": base.get("description") or None,
        "XMP-dc:Creator": base.get("artist") or None,
        "XMP-xmpRights:UsageTerms": (base.get("license") or {}).get("terms") or None,
        "XMP-dc:Subject": list(base.get("tags") or []),
        "IPTC:Keywords": [clip("IPTC:Keywords", t) for t in base.get("tags") or []],
    }
    for field, tag in (("title", "XMP-dc:Title"), ("description", "XMP-dc:Description")):
        found = lang_values(record, field, languages)
        for lang in languages:
            if lang != DEFAULT_LANG:
                exp[f"{tag}-{lang}"] = found.get(lang)
    return exp


def check_file(got, record, languages, variant):
    """Problems with one served file's metadata (a list of strings; empty = fine)."""
    problems = []
    for tag, want in expected_editorial(record, languages).items():
        have = got.get(tag)
        if isinstance(want, list):
            if as_list(have) != want:
                problems.append(f"{tag}: expected {want}, found {as_list(have)}")
        elif want is None:
            if have not in (None, ""):
                problems.append(f"{tag}: expected nothing, found {have!r}")
        elif str(have) != str(want):
            problems.append(f"{tag}: expected {want!r}, found {have!r}")

    # The notice: identical in all three places, "© [year ]artist".
    artist = record[DEFAULT_LANG].get("artist") or ""
    notices = {str(got.get(t)) for t in ("XMP-dc:Rights", "IFD0:Copyright", "IPTC:CopyrightNotice")}
    notice_re = re.compile(rf"^{COPYRIGHT_SYMBOL} (\d{{4}} )?{re.escape(artist)}$")
    if len(notices) != 1 or not notice_re.match(notices.pop()):
        problems.append("copyright notice missing, malformed or not the same in XMP/EXIF/IPTC")

    for key in got:
        if key == "SourceFile":
            continue
        group = key.split(":", 1)[0]
        if group not in ALLOWED_GROUPS:
            problems.append(f"stray metadata: {key}")
        elif BANNED_TAG_RE.search(key):
            problems.append(f"banned tag: {key}")
    if variant and "IFD0:Orientation" in got:
        problems.append("a variant carries Orientation (its rotation is baked in)")
    return problems


def read_back(exiftool, paths, extra_args=()):
    """{path: exiftool -j -G1 record} for the given files, chunked under ARG_MAX."""
    out = {}
    args = [exiftool, "-q", "-q", "-m", "-j", "-G1", "-a", "-x", "Composite:all",
            "-charset", "filename=UTF8", *extra_args]
    for i in range(0, len(paths), 400):
        chunk = [str(p) for p in paths[i:i + 400]]
        proc = subprocess.run(args + chunk, capture_output=True, text=True, check=False)
        if proc.stdout.strip():
            for rec in json.loads(proc.stdout):
                out[rec["SourceFile"]] = rec
    return out


# How much of the compressed image data scan_digest() hashes. exiftool never
# rewrites the entropy-coded data, only the segments before it, so the served
# original and its store file share these bytes exactly — and two different photos
# never do. exiftool's own ImageDataHash reads the WHOLE image: 140 s for the 650
# originals and their 650 sources, twice per deploy. This reads ~0.3 GB instead.
SCAN_PREFIX = 256 * 1024


def scan_digest(path, limit=SCAN_PREFIX):
    """SHA-256 of the first `limit` bytes of a JPEG's image data, or None.

    Walks the marker segments from SOI to the first SOS (start of scan), skipping
    every metadata segment by its length, and hashes from there. Metadata that
    exiftool adds, removes or rewrites therefore cannot change the result; the
    pixels can.
    """
    import hashlib
    with open(path, "rb") as fh:
        if fh.read(2) != b"\xff\xd8":
            return None
        while True:
            byte = fh.read(1)
            if not byte:
                return None
            if byte != b"\xff":
                continue
            marker = fh.read(1)
            while marker == b"\xff":          # fill bytes
                marker = fh.read(1)
            if not marker:
                return None
            code = marker[0]
            if code == 0xD8 or 0xD0 <= code <= 0xD7 or code == 0x01:
                continue                        # no length field
            size = fh.read(2)
            if len(size) < 2:
                return None
            length = int.from_bytes(size, "big")
            if code == 0xDA:                    # SOS: the image data starts here
                fh.seek(length - 2, 1)
                return hashlib.sha256(fh.read(limit)).hexdigest()
            fh.seek(length - 2, 1)


def do_check(exiftool, jobs, languages):
    """Read every served file back; compare it with the manifest. 0 = all good."""
    started = time.monotonic()
    got = read_back(exiftool, [t for _, t, _ in jobs])
    bad = []
    for record, target, _ in jobs:
        rec = got.get(str(target))
        if rec is None:
            bad.append((target.name, ["exiftool could not read it"]))
            continue
        problems = check_file(rec, record, languages, is_variant(record, target))
        if problems:
            bad.append((target.name, problems))
    read_s = time.monotonic() - started

    # The one check that does not go through the name mapping: a published
    # original must carry exactly the pixels of the store file it claims to come
    # from. After the rename to slugs (§5), this is what proves every original
    # sits under the right photo. Variants are right by construction — Hugo names
    # each one after the resource it rendered.
    started = time.monotonic()
    originals = [(t, s) for r, t, s in jobs if not is_variant(r, t)]
    for target, source in originals:
        a, b = scan_digest(target), scan_digest(source)
        if not a or a != b:
            bad.append((target.name, [f"pixels differ from the store file {source.name}"]))
    hash_s = time.monotonic() - started

    if bad:
        # One file can fail both halves (its fields and its pixels); report it once.
        # A pixel mismatch goes first: it means the file is the wrong photo, and
        # the field differences below it are only the consequence.
        merged = {}
        for name, problems in bad:
            merged.setdefault(name, []).extend(problems)
        bad = [(n, sorted(p, key=lambda x: not x.startswith("pixels"))) for n, p in merged.items()]
        for name, problems in bad[:20]:
            print(f"ERROR: {name}:", file=sys.stderr)
            for p in problems[:6]:
                print(f"         {p}", file=sys.stderr)
        more = len(bad) - 20
        if more > 0:
            print(f"       … and {more} more file(s)", file=sys.stderr)
        print(f"\n{len(bad)} of {len(jobs)} served files do not say what the manifest "
              "says. Do NOT deploy; rerun the embedding step.", file=sys.stderr)
        return 1
    print(f"OK: {len(jobs)} served files match the manifest field for field, carry no "
          f"metadata outside the allowlist, and {len(originals)} originals have their "
          f"store file's image data ({read_s:.1f}s read-back, {hash_s:.1f}s image data).")
    return 0


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    gallery = args.public / GALLERY_SUBDIR
    if not gallery.is_dir():
        die(f"no gallery output at {gallery} — run `hugo` first")
    if args.photos is None:
        die("no gallery mount found in config/_default/module.yaml, and no "
            "--photos given\n" + PHOTOS_SETUP_HINT)
    if not args.photos.is_dir():
        die(f"photos folder not found or not a directory: {args.photos}\n"
            + PHOTOS_SETUP_HINT)

    by_id, languages = load_manifests(args.public)
    # Served files are named after the photo's `file` (its English slug), not its
    # store filename, so that is the key; `src` then says which store file is the
    # source.
    by_file = {entry[DEFAULT_LANG]["file"]: entry for entry in by_id.values()}

    # Map every published file to its photo. An unmapped file aborts the run:
    # nothing goes online untagged, and a file the manifest does not know about
    # means the build and this pass disagree about what the gallery contains.
    jobs = []
    unmapped = []
    missing_sources = set()
    for entry in sorted(os.scandir(gallery), key=lambda e: e.name):
        if not entry.is_file():
            continue
        record = by_file.get(published_base(entry.name))
        if record is None:
            unmapped.append(entry.name)
            continue
        src = record[DEFAULT_LANG]["src"]
        source = args.photos / src
        if not source.is_file():
            missing_sources.add(src)
            continue
        jobs.append((record, Path(entry.path), source))

    if unmapped:
        for name in unmapped[:20]:
            print(f"ERROR: no manifest record for published file: {name}", file=sys.stderr)
        more = len(unmapped) - 20
        if more > 0:
            print(f"       … and {more} more", file=sys.stderr)
        die(f"{len(unmapped)} published file(s) map to no photo — nothing was written")
    if missing_sources:
        for name in sorted(missing_sources)[:20]:
            print(f"ERROR: source original missing from the photo store: {name}",
                  file=sys.stderr)
        die(f"{len(missing_sources)} source original(s) missing — nothing was written")
    if not jobs:
        die(f"no files under {gallery}")

    if args.check:
        return do_check(args.exiftool, jobs, languages)

    years, copyable, original_copyable = read_sources(
        sorted({source for _, _, source in jobs}), args.exiftool)
    text = build_argfile(jobs, languages, years, copyable, original_copyable)

    # Never inside public/: an interrupted run would leave it there to be rsynced.
    if args.save_args:
        args.save_args.write_text(text, encoding="utf-8")
        print(f"Arguments written to {args.save_args}")
    if args.dry_run:
        print(f"Would tag {len(jobs)} file(s) for {len(by_id)} photo(s) "
              f"in {len(languages)} language(s): {', '.join(languages)}")
        sources = {s for _, _, s in jobs}
        from_manifest = sum(
            1 for r in by_id.values()
            if r[DEFAULT_LANG].get("dateTaken") and r[DEFAULT_LANG]["src"] not in years
        )
        print(f"Copyright year: {len(years)} from EXIF DateTimeOriginal, "
              f"{from_manifest} from the manifest's dateTaken, "
              f"{len(sources) - len(years) - from_manifest} unknown "
              f"(notice written without a year)")
        return 0

    handle, argfile = tempfile.mkstemp(prefix="gallery-embed-", suffix=".args")
    argfile = Path(argfile)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            fh.write(text)
        started = time.monotonic()
        proc = run_exiftool(args.exiftool, argfile)
        elapsed = time.monotonic() - started
    finally:
        argfile.unlink(missing_ok=True)

    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)
    if proc.returncode != 0:
        die(f"exiftool exited {proc.returncode}")

    print(f"Tagged {len(jobs)} file(s) for {len(by_id)} photo(s) in {elapsed:.1f}s "
          f"({', '.join(languages)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
