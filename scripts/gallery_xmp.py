"""Read the five editorial fields darktable writes into an exported JPEG.

One reader, two callers: `sync-gallery.py`, which pre-fills a new photo's stub in
data/gallery.yaml from the file it was just handed, and the one-time import in
docs/concepts/gallery-metadata-import.md, which does the same for the 648 photos
that predate the stub enrichment. Keeping it in one place is the point — the two
must never disagree about which tag an `alt:` comes from.

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


def available():
    """True when exiftool is on PATH."""
    return shutil.which(EXIFTOOL) is not None


def read(paths):
    """Return {basename: {field: value}} for the given image paths.

    Only non-empty values appear. Returns {} when exiftool is missing or fails —
    a stub with empty fields is a fine outcome, an aborted sync is not.
    """
    paths = [str(p) for p in paths]
    if not paths or not available():
        return {}

    args = [EXIFTOOL, "-j", "-charset", "UTF8", "-m", "-q"]
    for tag in TAGS.values():
        args.append("-" + tag)
    args.extend(paths)

    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError:
        return {}
    if not proc.stdout.strip():
        return {}
    try:
        records = json.loads(proc.stdout)
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
