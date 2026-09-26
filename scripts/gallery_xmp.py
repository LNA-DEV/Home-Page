"""Read the editorial fields darktable writes into an exported JPEG.

One reader, three callers: `sync-gallery.py`, which pre-fills a new photo's
`license` and `artist` from the file it was just handed (and nothing else — the
prose and the tags are typed in data/gallery.yaml, see
docs/concepts/gallery-metadata-yaml-only.md §4); and the two one-time imports,
docs/concepts/gallery-metadata-import.md (the five fields below) and
gallery-metadata-yaml-only.md §3 (the tags' spelling, `read_keywords`). Keeping it
in one place is the point — they must never disagree about which tag a value
comes from.

The direction is always file → YAML, and always ONCE, at the moment a photo
enters the data file. Hugo does not read these tags at build time any more (the
`alt` and `license` fallbacks in collect-images.html are what the import removes),
so nothing here runs during a build.

exiftool is optional: every function degrades to "no values" when it is absent, so
a machine without it can still add photos — it just fills the fields by hand.

Field map (docs/concepts/gallery-metadata-single-source.md §1):

    title        dc:title              21 of 648 carry one; every template ignored it
    alt          XMP-acdsee:Notes      darktable's *notes* field, 281 of 648
    description  dc:description        caption prose, 7 of 648 — NOT alt text
    license      dc:rights             holds the licence NAME, not a copyright notice
    artist       dc:creator            always "Lukas Nagel" in this library
"""

import json
import shutil
import subprocess

# exiftool's own tag names, in the order the docstring lists them. XMP-acdsee is
# where darktable puts its "notes" field; nothing else reads that namespace, which
# is why the embedding step strips it from the served copies.
TAGS = {
    "title": "XMP-dc:Title",
    "alt": "XMP-acdsee:Notes",
    "description": "XMP-dc:Description",
    "license": "XMP-dc:Rights",
    "artist": "XMP-dc:Creator",
}

EXIFTOOL = "exiftool"


# Where a tag list can sit in a file. These are the three places the build used to
# read tags from (collect-images.html's `.Exif.subject` / `.Exif.Subject` /
# `.Exif.Keywords` / `.XMP.Subject`): on 2026-09-26 the lowercase union of these
# three plus the YAML equalled Hugo's `.Tags` on all 649 photos. Only the one-time
# tag import (scripts/gallery-import-tags.py) reads them, and only for spelling.
KEYWORD_TAGS = ("XMP-dc:Subject", "IPTC:Keywords", "EXIF:XPKeywords")


def available():
    """True when exiftool is on PATH."""
    return shutil.which(EXIFTOOL) is not None


def read(paths, fields=None):
    """Return {basename: {field: value}} for the given image paths.

    `fields` limits the read to a subset of TAGS' keys; sync-gallery.py asks only
    for `license` and `artist`, because the prose is typed in data/gallery.yaml
    (docs/concepts/gallery-metadata-yaml-only.md §4). The default is all five,
    which is what the one-time import used.

    Only non-empty values appear. Returns {} when exiftool is missing or fails —
    a stub with empty fields is a fine outcome, an aborted sync is not.
    """
    paths = [str(p) for p in paths]
    if not paths or not available():
        return {}
    wanted = {f: TAGS[f] for f in (fields or TAGS)}

    args = [EXIFTOOL, "-j", "-charset", "UTF8", "-m", "-q"]
    for tag in wanted.values():
        args.append("-" + tag)
    args.extend(paths)

    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError:
        return {}
    if not proc.stdout.strip():
        return {}
    return select(parse_records(proc.stdout), wanted)


def select(records, fields):
    """Keep only the named fields of {basename: {field: value}}.

    parse_records maps every field it knows; this drops the ones not asked for,
    so a subset read cannot leak a value the caller deliberately does not want —
    sync-gallery.py must never see a title, even from a file that has one.
    """
    out = {}
    for name, values in records.items():
        kept = {f: v for f, v in values.items() if f in fields}
        if kept:
            out[name] = kept
    return out


def read_keywords(paths):
    """Return {basename: [tag, …]} — every tag a file carries, in file order.

    The order is XMP dc:subject, then IPTC Keywords, then EXIF XPKeywords, and
    within each the order the file stores. A delimited string ("a;b", "a, b") is
    split the way collect-images.html split it. Duplicates are kept: the caller
    decides what a duplicate means. Returns {} when exiftool is missing.
    """
    paths = [str(p) for p in paths]
    if not paths or not available():
        return {}
    args = [EXIFTOOL, "-j", "-charset", "UTF8", "-charset", "filename=UTF8", "-m", "-q"]
    args.extend("-" + tag for tag in KEYWORD_TAGS)
    args.extend(paths)
    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError:
        return {}
    if not proc.stdout.strip():
        return {}
    return parse_keyword_records(proc.stdout)


def parse_keyword_records(json_text):
    """exiftool JSON → {basename: [tag, …]}. Split out so it tests without exiftool."""
    try:
        records = json.loads(json_text)
    except json.JSONDecodeError:
        return {}
    out = {}
    for record in records:
        name = record.get("SourceFile", "").rsplit("/", 1)[-1]
        tags = []
        for tag in KEYWORD_TAGS:
            value = record.get(tag.split(":", 1)[1])
            if value is None:
                continue
            items = value if isinstance(value, list) else [value]
            for item in items:
                for part in str(item).replace(";", ",").split(","):
                    part = part.strip()
                    if part:
                        tags.append(part)
        if tags:
            out[name] = tags
    return out


def parse_records(json_text):
    """Map exiftool's JSON output to {basename: {field: value}}.

    Split out of `read()` so the mapping can be tested without exiftool and
    without a photo: it is the half that encodes the field map, and the half that
    would silently start reading the wrong tag.
    """
    try:
        records = json.loads(json_text)
    except json.JSONDecodeError:
        return {}

    out = {}
    for record in records:
        source = record.get("SourceFile", "")
        name = source.rsplit("/", 1)[-1]
        fields = {}
        for field, tag in TAGS.items():
            # exiftool reports the tag without its group prefix.
            value = record.get(tag.split(":", 1)[1])
            # A repeated XMP property (dc:creator is a bag) comes back as a list.
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value if str(v).strip())
            if value is None:
                continue
            value = str(value).strip()
            if value:
                fields[field] = value
        if fields:
            out[name] = fields
    return out
