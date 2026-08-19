#!/usr/bin/env python3
"""Tag gallery photos with the dex species they show.

The dex joins to the gallery through a single optional field on each
`data/gallery.yaml` entry:

    - id: 6885f633-…
      src: Alpaca behind tree.JPG
      category: animals
      species: Vicugna pacos   # <- this script writes it

The value is the species' **scientific name**, so a gallery entry says what it
shows without a lookup into data/dex.yaml. A species counts as photographed when
at least one gallery entry carries that name, so this field is the only thing
that decides what is "caught". The tables below are keyed by dex slug because
that is what is readable to write by hand; the slug is resolved to the scientific
name at the moment of writing.

Two sources feed a proposal:

  1. `MANUAL` — photographs identified by looking at them. Many gallery entries
     have no alt text at all, and several that do are ambiguous ("a seagull",
     "a lizard"), so their species cannot be derived from the metadata.
  2. Text matching — the alt text, tags and filename of an entry are searched
     for the common names in data/dex.yaml plus the `ALIASES` below. Longer
     phrases win, so "great spotted woodpecker" beats "woodpecker" and
     "mandarin duck" beats "duck".

Entries that already have a `species:` are never touched, and anything that
stays unmatched is simply left alone — an untagged photo is a normal gallery
photo, it just does not appear in the dex.

gallery.yaml is edited as raw text (no YAML dependency), so untouched entries
stay byte-for-byte identical and the diff is limited to inserted lines.

Usage:
    python3 scripts/dex-tag-photos.py --dry-run     # review the proposals
    python3 scripts/dex-tag-photos.py --write       # apply them
    python3 scripts/dex-tag-photos.py --list-unmatched
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dex_common import GALLERY_PATH, load_dex  # noqa: E402

# ---------------------------------------------------------------------------
# Photographs identified visually, keyed by filename.
#
# These are photos whose species the metadata cannot give us: the ~60 entries
# with no alt text at all, plus the ones whose description stops at the genus
# ("a seagull", "a lizard", "a caterpillar"). Every gull in the set is from the
# Adriatic, hence yellow-legged rather than herring gull; every garden lizard is
# a sand lizard (green flanks over a brown dorsal band), not a European green
# lizard; the white ducks on the Inn are domestic, not mallards.
# ---------------------------------------------------------------------------
MANUAL = {
    # --- garden / macro ---
    "DSC_0362.jpg": "buff-tailed-bumblebee",
    "DSC_0363.jpg": "buff-tailed-bumblebee",
    "DSC_2007.jpg": "buff-tailed-bumblebee",
    "P1015709.jpg": "buff-tailed-bumblebee",
    "Bumblebee on the flowers.JPG": "buff-tailed-bumblebee",
    "DSC_2189.jpg": "common-carder-bee",
    "DSC_2196.jpg": "common-carder-bee",
    "DSC_2200.jpg": "common-carder-bee",
    "DSC_0720.jpg": "poplar-hawk-moth",
    "DSC_0728.jpg": "poplar-hawk-moth",
    "DSC_0729.jpg": "poplar-hawk-moth",
    "Caterpillar.JPG": "privet-hawk-moth",
    "Orange Moth.JPG": "silver-washed-fritillary",
    "GreenDragonflyClosed.JPG": "beautiful-demoiselle",
    "GreenDragonflyOpen.JPG": "beautiful-demoiselle",
    # --- reptiles ---
    "DSC_0600.jpg": "sand-lizard",
    "P1017063.jpg": "sand-lizard",
    "P1017069.jpg": "sand-lizard",
    "P1017375.jpg": "sand-lizard",
    "P1017380.jpg": "sand-lizard",
    "P1017390.jpg": "sand-lizard",
    "P1017433.jpg": "sand-lizard",
    "P1017437.jpg": "sand-lizard",
    "P1017463.jpg": "sand-lizard",
    "P1017475.jpg": "sand-lizard",
    "P1017487.jpg": "sand-lizard",
    "P1017497.jpg": "sand-lizard",
    "P1017499.jpg": "sand-lizard",
    "BabyLizard.JPG": "sand-lizard",
    "Green Lizard.JPG": "sand-lizard",
    "Lizard Fight.JPG": "sand-lizard",
    "LizardNextToHedghog.JPG": "sand-lizard",   # the hedgehog is a garden ornament
    "LizardOnTheStone.JPG": "sand-lizard",
    "Lizard from behind.JPG": "sand-lizard",
    "DSC_0673.jpg": "slow-worm",
    "DSC_0679.jpg": "slow-worm",
    # --- molluscs ---
    "ClimbingSnail.JPG": "roman-snail",
    "SlimySnails.JPG": "roman-snail",
    "SnailOnTheTree.JPG": "roman-snail",
    "Snail.JPG": "grove-snail",
    # --- birds ---
    "DSC_0517.jpg": "house-sparrow",
    "DSC_0668.jpg": "house-sparrow",
    "DSC_1004.jpg": "great-tit",
    "DSC_1087.jpg": "great-tit",
    "DSC_1211.jpg": "great-tit",
    "DSC_1277.jpg": "great-tit",
    "DSC_2253.jpg": "goosander",
    "P1015994.jpg": "greylag-goose",
    "P1016134.jpg": "barnacle-goose",
    "P1016186.jpg": "barnacle-goose",
    "P1013559.JPG": "canada-goose",
    "P1013563.JPG": "canada-goose",
    "P1013564.JPG": "canada-goose",
    "P1013568.JPG": "canada-goose",
    "P1013578.JPG": "canada-goose",
    "P1002440.JPG": "mallard",
    "P1002574.JPG": "mallard",
    "Duckys.JPG": "mandarin-duck",
    "DuckInTheWater.JPG": "domestic-duck",
    "DuckInTheWaterLookingToTheLeft.JPG": "domestic-duck",
    "WhiteDucky.JPG": "domestic-duck",
    "DuckOnTheBeach.JPG": "domestic-duck",
    "Black Stork.JPG": "black-stork",
    "Crow in the City.JPG": "carrion-crow",
    "P1013282.jpg": "great-cormorant",
    "Mr Gray Seagull.JPG": "yellow-legged-gull",
    "White Seagull looking to the side.JPG": "yellow-legged-gull",
    "Perfectly aligned seagull.JPG": "yellow-legged-gull",
    "Posing Seagull.JPG": "yellow-legged-gull",
    "Seagull watching sunset.JPG": "yellow-legged-gull",
    "Seagull eating trash.JPG": "yellow-legged-gull",
    "Seagull flying over the sea.JPG": "yellow-legged-gull",
    "Seagull mirroring.JPG": "yellow-legged-gull",
    # --- mammals ---
    "DSC_2484.jpg": "european-bison",
    "DSC_2487.jpg": "european-bison",
    "DSC_2532.jpg": "european-bison",
    "DSC_2537.jpg": "european-bison",
    "DSC_2538.jpg": "european-bison",
    "DSC_2542.jpg": "european-bison",
    "DSC_2055.jpg": "cattle",
    "DSC_2055_01.jpg": "cattle",
    "DSC_2055_02.jpg": "cattle",
    "DSC_2057.jpg": "cattle",
    "P1016680.jpg": "cattle",
    "P1016691.jpg": "cattle",
    "P1016700.jpg": "cattle",
    "P1016721.jpg": "cattle",
    "P1016730.jpg": "cattle",
    "P1016499.jpg": "fallow-deer",
    "P1002086.jpg": "common-vole",
    "Wild deer.JPG": "roe-deer",
    "P1017174.jpg": "domestic-sheep",
    "P1017179.jpg": "domestic-sheep",
    "P1017181.jpg": "domestic-sheep",
    "P1017193.jpg": "domestic-sheep",
    "P1017205.jpg": "domestic-sheep",
    "P1017231.jpg": "domestic-sheep",
    "FunnySheep.jpg": "domestic-sheep",
    "archive--Cat.JPG": "domestic-cat",
    "archive--CatLookingToTheSide.JPG": "domestic-cat",
    "FireSalamander.JPG": "fire-salamander",
}

# ---------------------------------------------------------------------------
# Text aliases: phrase found in alt / tags / filename -> dex slug.
# The common names from data/dex.yaml are matched automatically; this table is
# for the words people actually write ("wild pig", "gosling", "calf").
# ---------------------------------------------------------------------------
ALIASES = {
    "mandarin duck": "mandarin-duck",
    "mallard": "mallard",
    "wild duck": "mallard",
    "duckling": "mallard",
    "ducks": "mallard",
    "duck": "mallard",
    "gosling": "greylag-goose",
    "geese": "greylag-goose",
    "goose": "greylag-goose",
    "gosse": "greylag-goose",
    "swan": "mute-swan",
    "blackbird": "common-blackbird",
    "great spotted woodpecker": "great-spotted-woodpecker",
    "green woodpecker": "green-woodpecker",
    "crow": "carrion-crow",
    "seagull": "yellow-legged-gull",
    "chamois": "chamois",
    "wild pig": "wild-boar",
    "wild boar": "wild-boar",
    "piglet": "wild-boar",
    "boar": "wild-boar",
    "hedgehog": "european-hedgehog",
    "dolphin": "bottlenose-dolphin",
    "alpaca": "alpaca",
    "lamb": "domestic-sheep",
    "sheep": "domestic-sheep",
    "calf": "cattle",
    "cattle": "cattle",
    "cow": "cattle",
    "goat": "domestic-goat",
    "sphynx": "domestic-cat",
    "cat": "domestic-cat",
    "dog": "domestic-dog",
    "chicken": "chicken",
    "bumblebee": "buff-tailed-bumblebee",
    "honeybee": "honeybee",
    "bee": "honeybee",
    "snail": "roman-snail",
    "lizard": "sand-lizard",
    "fox": "red-fox",
    "white-tailed eagle": "white-tailed-eagle",
    "fire salamander": "fire-salamander",
    "salamander": "fire-salamander",
    "deer": "roe-deer",
    "cormorant": "great-cormorant",
}

# Words that must never trigger a match even though they look like a species —
# "hedgehog" here is a garden ornament, "chick" is a chicken not a chick species.
STOP_PHRASES = {"hedgehog figurine", "figurine"}

# Photos whose text would match but whose species is genuinely uncertain. The
# gulls in MANUAL are all Adriatic (yellow-legged); this one is a misty Bavarian
# lake where the birds are too distant to separate from black-headed gull.
SKIP = {"P1002464.JPG"}

CATEGORY_RE = re.compile(r"^  category: (.*)$", re.M)


def split_entries(text):
    """Split gallery.yaml into (prefix, [entry_blocks]) preserving raw text."""
    marker = "\n- id: "
    head, sep, rest = text.partition(marker)
    if not sep:
        raise SystemExit("data/gallery.yaml: no '- id:' entries found")
    blocks = rest.split(marker)
    return head, blocks


def entry_field(block, name):
    match = re.search(rf"^  {name}: (.*)$", block, re.M)
    if not match:
        return ""
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def camel_split(stem):
    """MyGreatPhoto -> 'my great photo', so filenames are searchable."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", stem)
    spaced = re.sub(r"[_\-]+", " ", spaced)
    return spaced.lower()


def build_phrase_map(species):
    """common name / slug -> dex slug, longest phrase first."""
    phrases = dict(ALIASES)
    for entry in species:
        slug = entry.get("slug")
        if not slug:
            continue
        names = entry.get("names") or {}
        for value in list(names.values()) + [slug.replace("-", " ")]:
            if not value:
                continue
            key = str(value).strip().lower()
            # A dex name never overrides a hand-written alias: "duck" must stay
            # mallard even though "Domestic Duck" also contains it.
            phrases.setdefault(key, slug)
    return sorted(phrases.items(), key=lambda kv: -len(kv[0]))


def propose(block, phrase_map, known_slugs):
    src = entry_field(block, "src")
    if not src or src in SKIP:
        return None, None

    manual = MANUAL.get(src)
    if manual:
        if manual not in known_slugs:
            return None, f"manual slug {manual!r} has no scientific name in data/dex.yaml"
        return manual, "visual"

    tags = re.findall(r"^  - (.*)$", block, re.M)
    haystack = " ".join(
        [
            entry_field(block, "alt").lower(),
            " ".join(tag.strip().lower() for tag in tags),
            camel_split(Path(src).stem),
        ]
    )
    for stop in STOP_PHRASES:
        haystack = haystack.replace(stop, " ")

    for phrase, slug in phrase_map:
        # `s?` so a plural in the alt text ("dolphins", "cows") still matches.
        if re.search(rf"(?<![a-z]){re.escape(phrase)}s?(?![a-z])", haystack):
            if slug not in known_slugs:
                continue
            return slug, f"text:{phrase}"
    return None, None


def insert_species(block, scientific):
    """Insert `  species: <Scientific name>` right after the category line."""
    def repl(match):
        return f"{match.group(0)}\n  species: {scientific}"

    new_block, count = CATEGORY_RE.subn(repl, block, count=1)
    if count == 0:
        raise SystemExit(f"entry has no category line:\n{block[:200]}")
    return new_block


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="Apply the proposals")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default)")
    parser.add_argument(
        "--list-unmatched", action="store_true", help="Only list photos with no proposal"
    )
    parser.add_argument("--category", default="animals", help="Gallery category to tag")
    args = parser.parse_args(argv)

    species = load_dex()
    if not species:
        raise SystemExit("data/dex.yaml is empty — run scripts/dex-import.py first")
    # The gallery stores the scientific name, so a species without one cannot be
    # tagged at all — surface that here rather than writing an empty field.
    scientific_by_slug = {
        entry["slug"]: entry["scientific"]
        for entry in species
        if entry.get("slug") and entry.get("scientific")
    }
    nameless = sorted(
        entry["slug"]
        for entry in species
        if entry.get("slug") and not entry.get("scientific")
    )
    if nameless:
        print(f"warning: no scientific name, cannot be tagged: {', '.join(nameless)}")
    known_slugs = set(scientific_by_slug)
    phrase_map = build_phrase_map(species)

    text = GALLERY_PATH.read_text(encoding="utf-8")
    head, blocks = split_entries(text)

    proposals, unmatched, already, problems = [], [], [], []
    out_blocks = []

    for block in blocks:
        category = entry_field(block, "category")
        src = entry_field(block, "src")
        if category != args.category:
            out_blocks.append(block)
            continue
        if entry_field(block, "species"):
            already.append(src)
            out_blocks.append(block)
            continue

        slug, how = propose(block, phrase_map, known_slugs)
        if slug is None:
            if how:
                problems.append((src, how))
            else:
                unmatched.append(src)
            out_blocks.append(block)
            continue

        proposals.append((src, slug, how))
        out_blocks.append(insert_species(block, scientific_by_slug[slug]))

    if args.list_unmatched:
        for src in unmatched:
            print(src)
        return 0

    by_slug = {}
    for src, slug, how in proposals:
        by_slug.setdefault(slug, []).append((src, how))
    for slug in sorted(by_slug):
        entries = by_slug[slug]
        print(f"{slug} -> {scientific_by_slug[slug]}  ({len(entries)})")
        for src, how in entries:
            print(f"    {src}   [{how}]")

    print()
    print(f"proposed : {len(proposals)} photos across {len(by_slug)} species")
    print(f"already  : {len(already)}")
    print(f"unmatched: {len(unmatched)}")
    for src in unmatched:
        print(f"    ? {src}")
    for src, why in problems:
        print(f"    ! {src}: {why}")

    if not args.write:
        print("\n(dry run — pass --write to apply)")
        return 0

    GALLERY_PATH.write_text(head + "\n- id: " + "\n- id: ".join(out_blocks), encoding="utf-8")
    print(f"\nwrote {GALLERY_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
