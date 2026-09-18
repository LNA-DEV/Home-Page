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

Two modes:

    (default)   tag, copy and strip every file
    --check     read back DigitalImageGUID and assert it matches the manifest

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
    repo_root,
    source_name,
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

# Removed from the output, whatever the input had. The published original is a
# copy of the source and carries all of it; the variants carry none of it and the
# deletions are simply no-ops there.
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
        help="verify instead of write: every file must carry its photo's UUID",
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
    """One read pass over the photo store: (capture years, sources worth copying).

    A year at or below 2000 is discarded, which is the same rule the site applies
    to a photo's date everywhere else: a camera with an unset clock stamps
    2000:01:01, and 87 files here carry exactly that. "© 2000" would be a worse
    answer than the build year, not a better one.

    The second return value is the set of sources that carry at least one of
    COPY_TAGS. A handful carry none, and asking exiftool to copy from them prints
    a "No writable tags set" warning per output file — 20 lines of noise for a
    file that simply has no camera data, so those skip the copy block entirely.
    """
    if not sources:
        return {}, set()
    args = [exiftool, "-q", "-m", "-j", "-charset", "filename=UTF8"]
    args.extend("-" + tag for tag in COPY_TAGS)
    args.extend(str(p) for p in sources)
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if not proc.stdout.strip():
        return {}, set()
    years = {}
    copyable = set()
    for record in json.loads(proc.stdout):
        name = Path(record["SourceFile"]).name
        match = EXIF_DATE_RE.match(str(record.get("DateTimeOriginal", "")))
        if match and int(match.group(1)) > 2000:
            years[name] = match.group(1)
        if any(record.get(tag) is not None for tag in COPY_TAGS):
            copyable.add(name)
    return years, copyable


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


def photo_args(record, languages, target, source, year, copy_exif, is_variant):
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

    # 1. Strip first, so nothing below can be undone by a deletion.
    args.extend(f"-{tag}=" for tag in STRIP_TAGS)

    # 2. Technical half, straight from the untouched source.
    if copy_exif:
        args.append("-tagsFromFile")
        args.append(str(source))
        args.extend(f"-{tag}" for tag in COPY_TAGS)

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

    # Tags are language-neutral and already filtered through
    # data/galleryTagIgnore.yaml by collect-images.html, so the junk the camera
    # wrote into dc:subject never reaches an output file.
    for tag in base.get("tags") or []:
        args.append(f"-XMP-dc:Subject={tag}")
        args.append(f"-IPTC:Keywords={clip('IPTC:Keywords', tag)}")

    args.append(str(target))
    return args


def build_argfile(jobs, languages, years, copyable):
    """The whole run as one exiftool argument file, commands split by -execute."""
    lines = []
    for record, target, source in jobs:
        # No build-year fallback: an unknown year means no year in the notice.
        year = years.get(source.name) or record[DEFAULT_LANG].get("dateTaken", "")[:4]
        is_variant = target.name != source.name
        lines.append("-overwrite_original")
        lines.append("-m")
        lines.append("-charset")
        lines.append("UTF8")
        lines.append("-charset")
        lines.append("filename=UTF8")
        lines.extend(photo_args(record, languages, target, source, year,
                                source.name in copyable, is_variant))
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


def do_check(exiftool, jobs, public):
    """Every served file must carry its photo's UUID. Read back and compare."""
    targets = [str(t) for _, t, _ in jobs]
    expected = {str(t): r[DEFAULT_LANG]["id"] for r, t, _ in jobs}
    args = [exiftool, "-q", "-m", "-j", "-charset", "filename=UTF8",
            "-XMP-iptcExt:DigitalImageGUID"]
    bad = []
    seen = 0
    # Chunked so the argument list stays well inside any ARG_MAX.
    for i in range(0, len(targets), 500):
        chunk = targets[i:i + 500]
        proc = subprocess.run(args + chunk, capture_output=True, text=True, check=False)
        if not proc.stdout.strip():
            bad.extend(chunk)
            continue
        for record in json.loads(proc.stdout):
            seen += 1
            path = record["SourceFile"]
            got = record.get("DigitalImageGUID")
            if got != expected.get(path):
                bad.append(f"{path} (found {got!r}, expected {expected.get(path)!r})")
    if bad:
        for item in bad[:20]:
            print(f"ERROR: untagged or mismatched: {item}", file=sys.stderr)
        more = len(bad) - 20
        if more > 0:
            print(f"       … and {more} more", file=sys.stderr)
        print(
            f"\n{len(bad)} of {len(targets)} served files do not carry their photo's "
            "UUID. Do NOT deploy; rerun the embedding step.",
            file=sys.stderr,
        )
        return 1
    print(f"OK: {seen} served files carry their photo's UUID.")
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
    by_src = {entry[DEFAULT_LANG]["src"]: entry for entry in by_id.values()}

    # Map every published file to its photo. An unmapped file aborts the run:
    # nothing goes online untagged, and a file the manifest does not know about
    # means the build and this pass disagree about what the gallery contains.
    jobs = []
    unmapped = []
    missing_sources = set()
    for entry in sorted(os.scandir(gallery), key=lambda e: e.name):
        if not entry.is_file():
            continue
        src = source_name(entry.name)
        record = by_src.get(src)
        if record is None:
            unmapped.append(entry.name)
            continue
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
        return do_check(args.exiftool, jobs, args.public)

    years, copyable = read_sources(sorted({source for _, _, source in jobs}),
                                   args.exiftool)
    text = build_argfile(jobs, languages, years, copyable)

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
