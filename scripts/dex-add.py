#!/usr/bin/env python3
"""Add a species to data/dex.yaml by hand.

Creates a minimal stub — slug, number, scientific name, family, group,
difficulty and the English common name. Everything else (description,
measurements, diet, lifespan, IUCN status, GBIF/iNaturalist taxon keys, German
name, reference photo) is left for `scripts/dex-enrich.py` to fill in from
GBIF / Wikidata / Wikipedia.

The dex number is assigned automatically as the lowest free one, so entries
stay unique without any bookkeeping.

Standard library only.

Usage:
    python3 scripts/dex-add.py "Sand Lizard" --scientific "Lacerta agilis" \\
        --family Lacertidae --difficulty moderate
    python3 scripts/dex-add.py "Cattle" --scientific "Bos taurus" \\
        --family Bovidae --difficulty easy --slug cattle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dex_common import DEX_PATH, dump_dex, group_for, load_dex, slugify  # noqa: E402

HEADER_PATH = Path(__file__).resolve().parent / "dex-import.py"


def _header():
    """Reuse the file header dex-import.py writes, so rewrites keep it."""
    text = DEX_PATH.read_text(encoding="utf-8") if DEX_PATH.exists() else ""
    lines = []
    for line in text.splitlines():
        if line.startswith("#"):
            lines.append(line.lstrip("#").lstrip() if line.strip() != "#" else "")
        elif not line.strip():
            continue
        else:
            break
    return "\n".join(lines) if lines else None


def next_number(species):
    used = {int(e["number"]) for e in species if str(e.get("number", "")).isdigit()}
    candidate = 1
    while candidate in used:
        candidate += 1
    return f"{candidate:03d}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", help="English common name, e.g. \"Sand Lizard\"")
    parser.add_argument("--scientific", required=True, help="Binomial, e.g. \"Lacerta agilis\"")
    parser.add_argument("--family", default="", help="Taxonomic family, e.g. Lacertidae")
    parser.add_argument("--group", default="", help="Dex group; inferred from family when omitted")
    parser.add_argument(
        "--difficulty",
        default="moderate",
        choices=["easy", "moderate", "challenging"],
        help="How hard it is to photograph (default: moderate)",
    )
    parser.add_argument("--slug", default="", help="URL slug; derived from the name when omitted")
    parser.add_argument("--de", default="", help="German common name (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Report, do not write")
    args = parser.parse_args(argv)

    species = load_dex()
    slug = args.slug or slugify(args.name)

    for entry in species:
        if entry.get("slug") == slug:
            print(f"already present: {slug} (#{entry.get('number')})")
            return 0

    record = {
        "slug": slug,
        "number": next_number(species),
        "scientific": args.scientific,
        "family": args.family,
        "group": args.group or group_for(args.family),
        "difficulty": args.difficulty,
        "names": {"en": args.name},
    }
    if args.de:
        record["names"]["de"] = args.de

    print(f"+ #{record['number']} {slug} — {args.scientific} ({record['group']})")
    if args.dry_run:
        print("(dry run — nothing written)")
        return 0

    species.append(record)
    dump_dex(species, DEX_PATH, header=_header())
    print(f"wrote {DEX_PATH.name} ({len(species)} species)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
