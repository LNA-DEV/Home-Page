#!/usr/bin/env python3
"""Download a Wikimedia Commons reference photo for every dex species.

A species you have not photographed yet still needs to show you what you are
looking for, so each one gets a small Commons thumbnail stored in the repo:

    assets/images/dex/reference/<slug>.jpg

`scripts/dex-enrich.py` records the Commons filename from the species'
Wikidata P18 claim in `reference.commons_file`; this script turns that into an
actual file and writes back the attribution that belongs to the file it
downloaded, so `reference.credit` can never drift away from the image on disk.

Thumbnails are requested at `--width` pixels (900 by default) via the Commons
thumbnail service rather than downloading originals, which run to several
megabytes apiece. Only species you have *not* photographed are fetched, since
the rest display your own photo — pass `--all` to override.

Two things about `--width` are worth knowing before changing it:

  * Commons does not serve arbitrary widths. It snaps the delivered file **up**
    to whichever cached rendition is next largest, so a request for 560–960 all
    return the same ~960px file. The `thumbwidth` the API reports back is the
    width you asked for, not the width you get — check the `NNNpx-` segment of
    the thumbnail URL for the truth. For these files the buckets land at roughly
    500 / 960 / 1280 px, so 900 (→ ~960 px, ~180 KB) and 500 (→ 500 px, ~60 KB)
    are the two sensible settings; anything in between just costs more bytes for
    the same image.
  * 900 is chosen to match the render size of the site owner's own photos, which
    `dex-detail.html` processes at `fill 900x900`. The hero slot is only 300–320
    CSS px wide, so ~960 px is what makes a stand-in look as sharp as a real
    photo on a 3x display instead of visibly softer beside it.

Where a file's original is smaller than the requested width, MediaWiki returns
the original rather than upscaling — so a handful of species stay low-resolution
no matter what `--width` says, and the template must not upscale them either.

The species page dims these images and labels them "reference photo", so they
are never mistaken for the site owner's own work — but they are still CC-licensed
third-party photographs, and the credit is rendered next to every one of them.

Standard library only.

Usage:
    python3 scripts/dex-covers.py --dry-run
    python3 scripts/dex-covers.py
    python3 scripts/dex-covers.py --only red-fox --force
    python3 scripts/dex-covers.py --all              # including already-photographed species
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dex_common import (  # noqa: E402
    DEX_PATH,
    GALLERY_PATH,
    REPO_ROOT,
    dump_dex,
    http_get,
    load_dex,
)

COVER_DIR = REPO_ROOT / "assets" / "images" / "dex" / "reference"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
DELAY = 0.3


def photographed_species():
    """Lowercased scientific names that already have a photo in the gallery."""
    text = GALLERY_PATH.read_text(encoding="utf-8")
    found = (m.strip().lower() for m in re.findall(r"^  species: (.+)$", text, re.M))
    return {name for name in found if name}


def commons_metadata(filename, width):
    """Return (thumb_url, credit, page_url) for a Commons file."""
    data = http_get(
        COMMONS_API,
        {
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": str(width),
            "format": "json",
        },
    )
    time.sleep(DELAY)
    if not data:
        return None, None, None

    for page in (data.get("query", {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        if not info:
            continue
        thumb = info.get("thumburl") or info.get("url")
        meta = info.get("extmetadata") or {}

        artist = meta.get("Artist", {}).get("value", "")
        artist = html.unescape(re.sub(r"<[^>]+>", " ", artist))
        artist = re.sub(r"\s+", " ", artist).strip(" ,")

        licence = meta.get("LicenseShortName", {}).get("value", "")
        licence = html.unescape(re.sub(r"<[^>]+>", "", licence)).strip()

        title = page.get("title", "")
        page_url = (
            "https://commons.wikimedia.org/wiki/"
            + urllib.parse.quote(title.replace(" ", "_"), safe=":/")
            if title
            else None
        )

        parts = [part for part in (artist, licence, "Wikimedia Commons") if part]
        return thumb, ", ".join(parts), page_url
    return None, None, None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", action="append", default=[], help="Limit to these slugs")
    parser.add_argument("--force", action="store_true", help="Redownload existing files")
    parser.add_argument("--dry-run", action="store_true", help="Report, download nothing")
    parser.add_argument(
        "--width", type=int, default=900,
        help="Thumbnail width (default: 900, delivered as ~960px; see module docstring — "
             "Commons snaps up to cached buckets, so 500 is the only cheaper useful value)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Also fetch stand-ins for species you have already photographed "
             "(their own photo is shown instead, so this is normally wasted space)",
    )
    args = parser.parse_args(argv)

    species = load_dex()
    if not species:
        raise SystemExit("data/dex.yaml is empty — run scripts/dex-import.py first")

    caught = photographed_species()
    todo = [s for s in species if not args.only or s.get("slug") in args.only]
    if not args.all:
        # A species you have photographed shows your own photo everywhere, so a
        # Commons stand-in for it would be bytes in the repo that nothing renders.
        # The gallery joins on the scientific name, so that is what we match on.
        todo = [s for s in todo if (s.get("scientific") or "").lower() not in caught]

    header_lines = []
    for line in DEX_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            header_lines.append(line.lstrip("#").lstrip() if line.strip() != "#" else "")
        elif not line.strip():
            continue
        else:
            break
    header = "\n".join(header_lines) or None

    downloaded, skipped, failed = 0, 0, []
    total_bytes = 0
    COVER_DIR.mkdir(parents=True, exist_ok=True)

    for index, entry in enumerate(todo, 1):
        slug = entry.get("slug")
        reference = entry.setdefault("reference", {}) or {}
        entry["reference"] = reference
        target = COVER_DIR / f"{slug}.jpg"

        if target.exists() and not args.force:
            total_bytes += target.stat().st_size
            skipped += 1
            if not reference.get("file"):
                reference["file"] = target.name
            continue

        commons_file = reference.get("commons_file")
        if not commons_file:
            failed.append(f"{slug} (no Wikidata image)")
            continue

        thumb, credit, page_url = commons_metadata(commons_file, args.width)
        if not thumb:
            failed.append(f"{slug} (Commons lookup failed for {commons_file})")
            continue

        raw = http_get(thumb, accept_json=False)
        time.sleep(DELAY)
        if not raw:
            failed.append(f"{slug} (download failed)")
            continue

        kilobytes = len(raw) / 1024
        print(f"  [{index}/{len(todo)}] {slug}: {kilobytes:.0f} KB — {credit}")
        if not args.dry_run:
            target.write_bytes(raw)
        total_bytes += len(raw)
        downloaded += 1

        reference["file"] = target.name
        if credit:
            reference["credit"] = credit
        if page_url:
            reference["credit_url"] = page_url

    print()
    print(f"downloaded: {downloaded}")
    print(f"unchanged : {skipped}")
    print(f"no image  : {len(failed)}")
    for item in failed:
        print(f"    - {item}")
    print(f"\nreference photos on disk: {total_bytes / 1024 / 1024:.1f} MB")

    if args.dry_run:
        print("(dry run — nothing written)")
        return 0
    dump_dex(species, DEX_PATH, header=header)
    print(f"wrote {DEX_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
