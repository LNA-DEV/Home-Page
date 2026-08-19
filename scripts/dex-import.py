#!/usr/bin/env python3
"""One-shot import of the animal-dex proof of concept into data/dex.yaml.

animal-dex keeps one Hugo page bundle per species
(`content/animals/<slug>/index.{en,de}.md`) with all the data in front matter.
This site keeps species in a single central data file, the same way
data/reading.yaml and data/gaming.yaml work, so this script flattens the
bundles into `species:` records:

    animal-dex front matter        ->  data/dex.yaml
    ---------------------------------------------------------------
    title (en/de)                  ->  names.{en,de}
    species                        ->  scientific
    family, number, difficulty     ->  family, number, difficulty
    gbif_taxon_key                 ->  gbif_taxon_key
    height/body_weight/lifespan    ->  same (language-neutral)
    diet                           ->  diet (slugified into the i18n vocab)
    habitat (en/de)                ->  habitat.{en,de}
    description (en/de)            ->  description.{en,de}
    best_time/approach (en/de)     ->  tips.best_time.{en,de}, tips.approach.{en,de}
    image_credit(_url)             ->  reference.credit, reference.credit_url
    (family)                       ->  group, via the offline family table

Deliberately NOT imported: `map_center` / `map_zoom` (the map fits the range
polygon instead) and `locations` (illustrative range examples, whereas
`sightings:` here means "where I actually photographed it").

Existing entries in data/dex.yaml are never overwritten — rerunning only adds
species that are missing, so this is safe to repeat.

Usage:
    python3 scripts/dex-import.py --source ../animal-dex [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dex_common import (  # noqa: E402
    DEX_PATH,
    REPO_ROOT,
    dump_dex,
    group_for,
    load_dex,
    slugify,
)

HEADER = """data/dex.yaml — the photo dex species list.

One record per species. A species counts as "photographed" when at least one
entry in data/gallery.yaml carries its scientific name in `species:` — there is
no separate caught/uncaught flag to keep in sync. The slug stays the URL and the
key for range/reference files; the scientific name is what the gallery joins on.

Language-neutral facts (scientific name, family, measurements, taxon keys) sit
at the top level; anything that reads as prose is nested per language under
names / description / habitat / tips, and falls back to `en` when a language is
missing.

Maintained by scripts/dex-import.py, scripts/dex-enrich.py,
scripts/dex-ranges.py and scripts/dex-covers.py — see AGENTS.md."""

DIET_MAP = {
    "omnivore": "omnivore",
    "allesfresser": "omnivore",
    "carnivore": "carnivore",
    "fleischfresser": "carnivore",
    "herbivore": "herbivore",
    "pflanzenfresser": "herbivore",
    "carnivore (fish)": "piscivore",
    "fleischfresser (fisch)": "piscivore",
    "piscivore": "piscivore",
    "carnivore (insects)": "insectivore",
    "fleischfresser (insekten)": "insectivore",
    "insectivore": "insectivore",
    "herbivore (fruit)": "frugivore",
    "pflanzenfresser (fruechte)": "frugivore",
    "pflanzenfresser (früchte)": "frugivore",
    "herbivore (seeds)": "granivore",
    "pflanzenfresser (samen)": "granivore",
    "herbivore (nectar)": "nectarivore",
    "pflanzenfresser (nektar)": "nectarivore",
    "filter feeder": "filter-feeder",
    "filtrierer": "filter-feeder",
}


def parse_front_matter(path: Path) -> dict:
    """Parse the YAML front matter of an animal-dex markdown file.

    Handles exactly what animal-dex writes: plain scalars, `>` folded blocks,
    flow sequences and one level of nested maps / sequences-of-maps.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    body = text.split("---", 2)
    if len(body) < 3:
        return {}
    lines = body[1].splitlines()

    data: dict = {}
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not line.strip() or line.lstrip().startswith("#"):
            idx += 1
            continue
        match = re.match(r"^([A-Za-z0-9_]+):(?:\s*(.*))?$", line)
        if not match:
            idx += 1
            continue
        key, inline = match.group(1), (match.group(2) or "").strip()
        idx += 1

        if inline in (">", ">-", "|", "|-"):
            chunk = []
            while idx < len(lines) and (not lines[idx].strip() or lines[idx].startswith("  ")):
                chunk.append(lines[idx].strip())
                idx += 1
            data[key] = " ".join(part for part in chunk if part)
            continue

        if inline:
            value = inline
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                data[key] = [part.strip() for part in inner.split(",")] if inner else []
            else:
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                data[key] = value
            continue

        # Nested block — collect it verbatim; the importer only needs to know
        # such a key existed (build:, locations:), not its contents.
        chunk = []
        while idx < len(lines) and (not lines[idx].strip() or lines[idx].startswith("  ")):
            chunk.append(lines[idx])
            idx += 1
        data[key] = chunk
    return data


def build_record(slug: str, en: dict, de: dict) -> dict:
    scientific = en.get("species") or de.get("species") or ""
    family = en.get("family") or de.get("family") or ""

    diet_raw = (en.get("diet") or de.get("diet") or "").strip().lower()
    diet = DIET_MAP.get(diet_raw, slugify(diet_raw) if diet_raw else "")

    record = {
        "slug": slug,
        "number": str(en.get("number") or de.get("number") or ""),
        "scientific": scientific,
        "family": family,
        "group": group_for(family),
        "difficulty": (en.get("difficulty") or "moderate").strip().lower(),
        "gbif_taxon_key": en.get("gbif_taxon_key") or de.get("gbif_taxon_key") or "",
        "height": en.get("height") or de.get("height") or "",
        "body_weight": en.get("body_weight") or de.get("body_weight") or "",
        "diet": diet,
        "lifespan": en.get("lifespan") or "",
        "habitat": {"en": en.get("habitat") or "", "de": de.get("habitat") or ""},
        "reference": {
            "credit": en.get("image_credit") or de.get("image_credit") or "",
            "credit_url": en.get("image_credit_url") or de.get("image_credit_url") or "",
        },
        "names": {"en": en.get("title") or "", "de": de.get("title") or ""},
        "description": {
            "en": en.get("description") or "",
            "de": de.get("description") or "",
        },
        "tips": {
            "best_time": {
                "en": en.get("best_time") or "",
                "de": de.get("best_time") or "",
            },
            "approach": {
                "en": en.get("approach") or "",
                "de": de.get("approach") or "",
            },
        },
    }
    if isinstance(record["gbif_taxon_key"], str) and record["gbif_taxon_key"].isdigit():
        record["gbif_taxon_key"] = int(record["gbif_taxon_key"])
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source",
        type=Path,
        default=REPO_ROOT.parent / "animal-dex",
        help="Path to the animal-dex repository (default: ../animal-dex)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report, do not write")
    args = parser.parse_args(argv)

    content_dir = args.source / "content" / "animals"
    if not content_dir.is_dir():
        parser.error(f"no animal bundles at {content_dir}")

    existing = load_dex()
    known_slugs = {entry.get("slug") for entry in existing}
    known_numbers = {str(entry.get("number")) for entry in existing}

    added, skipped = [], []

    for bundle in sorted(content_dir.iterdir()):
        if not bundle.is_dir():
            continue
        en_path = bundle / "index.en.md"
        if not en_path.is_file():
            continue
        slug = bundle.name
        if slug in known_slugs:
            skipped.append(slug)
            continue

        en = parse_front_matter(en_path)
        de_path = bundle / "index.de.md"
        de = parse_front_matter(de_path) if de_path.is_file() else {}
        if not en.get("species"):
            skipped.append(f"{slug} (no scientific name)")
            continue

        record = build_record(slug, en, de)
        if record["number"] in known_numbers:
            record["number"] = ""
        known_numbers.add(record["number"])

        # The six fully-built animal-dex species ship a local photo, but those
        # are ~7 MB Commons originals. scripts/dex-covers.py fetches a uniform
        # 400px thumbnail for every species instead, so nothing is copied here.

        existing.append(record)
        known_slugs.add(slug)
        added.append(slug)

    # Renumber anything that ended up without a number, continuing the sequence.
    used = {int(e["number"]) for e in existing if str(e.get("number", "")).isdigit()}
    next_number = 1
    for entry in existing:
        if str(entry.get("number", "")).isdigit():
            continue
        while next_number in used:
            next_number += 1
        entry["number"] = f"{next_number:03d}"
        used.add(next_number)

    print(f"animal-dex bundles at {content_dir}")
    print(f"  added   {len(added)}")
    print(f"  skipped {len(skipped)} (already present or unusable)")
    groups: dict[str, int] = {}
    for entry in existing:
        groups[entry.get("group", "other")] = groups.get(entry.get("group", "other"), 0) + 1
    print("  groups: " + ", ".join(f"{k}={v}" for k, v in sorted(groups.items())))

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    dump_dex(existing, DEX_PATH, header=HEADER)
    print(f"\nwrote {DEX_PATH.relative_to(REPO_ROOT)} ({len(existing)} species)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
