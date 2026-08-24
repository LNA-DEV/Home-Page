#!/usr/bin/env python3
"""Fill in the empty fields of data/dex.yaml from public taxonomic databases.

Only fields that are currently empty are ever written — anything already in the
file (including hand-written photography tips and corrected names) survives a
rerun untouched. That makes this safe to run repeatedly as species are added.

Per species, in this order:

  GBIF        species/match on the scientific name
              -> gbif_taxon_key, family, and the taxonomic class that decides
                 the dex `group`
  Wikipedia   pageprops on the scientific name
              -> the Wikidata QID (and, by resolving redirects, the canonical
                 article title)
  Wikidata    wbgetentities claims + labels + sitelinks
              -> height (P2048), body_weight (P2067), lifespan (P2250),
                 diet (P1034), IUCN status (P141), reference photo (P18),
                 and the common names in en / de / sv
  Wikipedia   REST summary for en, de and sv
              -> description, trimmed to the first two or three sentences
  iNaturalist taxa search on the scientific name
              -> inat_taxon_id, which scripts/dex-ranges.py needs

Every description is the summary of that language's *own* Wikipedia article,
resolved through the Wikidata sitelink — nothing here is machine-translated. A
language is only filled where a real sitelink exists, so a species with no
sv.wikipedia article keeps falling back to the English text on the Swedish page.

Standard library only. Be polite: there is a delay between requests, so a full
run over ~190 species takes a few minutes.

Usage:
    python3 scripts/dex-enrich.py --dry-run
    python3 scripts/dex-enrich.py
    python3 scripts/dex-enrich.py --only red-fox --only sand-lizard
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dex_common import (  # noqa: E402
    DEX_PATH,
    dump_dex,
    group_for,
    http_get,
    load_dex,
)

DELAY = 0.34  # seconds between outbound requests

# Wikidata unit QIDs -> short label
UNIT_MAP = {
    "Q11573": "m", "Q174728": "cm", "Q174789": "mm",
    "Q11570": "kg", "Q41803": "g",
    "Q577": "yr", "Q24564698": "yr", "Q5151": "yr",
}

# Wikidata P1034 (main food source) -> dex diet slug
DIET_MAP = {
    "Q164509": "omnivore", "Q57814795": "omnivore", "Q27971516": "omnivore",
    "Q830976": "carnivore", "Q193462": "carnivore", "Q1329239": "carnivore",
    "Q221392": "herbivore", "Q4071346": "herbivore",
    "Q59099": "insectivore", "Q201705": "insectivore",
    "Q13194463": "piscivore",
    "Q28813": "granivore",
    "Q1141466": "frugivore",
    "Q199960": "nectarivore",
}

# Wikidata P141 (IUCN conservation status) -> IUCN code
IUCN_MAP = {
    "Q211005": "LC", "Q719675": "NT", "Q278113": "VU",
    "Q11394": "EN", "Q219127": "CR", "Q239509": "EW",
    "Q237350": "EX", "Q3245245": "DD", "Q2793753": "NE",
}

# Fields this script is allowed to create. Nested paths use dots.
FILLABLE = [
    "gbif_taxon_key", "family", "group", "inat_taxon_id", "wikidata_id",
    "height", "body_weight", "diet", "lifespan", "iucn",
    "names.de", "names.sv",
    "description.en", "description.de", "description.sv",
    "reference.commons_file",
]


# Fields a human deliberately emptied. "Fill only what is empty" cannot tell a
# never-populated field from a corrected one, so without this table every rerun
# puts these straight back:
#
#   * A **domesticated form has no IUCN assessment.** The Red List assesses the
#     wild ancestor; carrying its category over to the farm animal asserts
#     something untrue on the species page.
#   * A **Europe-only regional assessment is not a global one.** Wikidata files
#     the regional category for these two bees in the same P141 slot as a global
#     one, behind a qualifier this script does not read.
#
# See AGENTS.md, "Fill in the facts".
PROTECTED = {
    "honeybee": {"iucn"},
    "common-carder-bee": {"iucn"},
    "alpaca": {"iucn"},
    "cattle": {"iucn"},
    "chicken": {"iucn"},
    "domestic-cat": {"iucn"},
    "domestic-dog": {"iucn"},
    "domestic-duck": {"iucn"},
    "domestic-goat": {"iucn"},
    "domestic-sheep": {"iucn"},
}


# ---------------------------------------------------------------------------
# Nested get/set on the species record
# ---------------------------------------------------------------------------

def get_path(record, path):
    node = record
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def set_path(record, path, value):
    parts = path.split(".")
    node = record
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


def is_empty(value):
    return value is None or (isinstance(value, str) and not value.strip())


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def gbif_match(scientific):
    data = http_get("https://api.gbif.org/v1/species/match", {"name": scientific})
    time.sleep(DELAY)
    if not data or data.get("matchType") == "NONE":
        return {}
    return {
        "key": data.get("usageKey"),
        "family": data.get("family") or "",
        "class": data.get("class") or "",
    }


def wikidata_qid(scientific):
    """Resolve a scientific name to a Wikidata QID via the English Wikipedia."""
    data = http_get(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "titles": scientific,
            "prop": "pageprops",
            "redirects": "1",
            "format": "json",
        },
    )
    time.sleep(DELAY)
    if not data:
        return None, None
    for page in (data.get("query", {}).get("pages") or {}).values():
        qid = (page.get("pageprops") or {}).get("wikibase_item")
        if qid:
            return qid, page.get("title")
    return None, None


def wikidata_entity(qid):
    data = http_get(
        "https://www.wikidata.org/w/api.php",
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims|labels|sitelinks",
            "languages": "en|de|sv",
            "format": "json",
        },
    )
    time.sleep(DELAY)
    if not data:
        return None
    return (data.get("entities") or {}).get(qid)


def claim_values(entity, prop):
    return [
        claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        for claim in (entity.get("claims") or {}).get(prop, [])
        if claim.get("mainsnak", {}).get("datavalue")
    ]


def quantity_range(entity, prop, keep_unit=True):
    """Format all quantity statements for `prop` as e.g. '35–50 cm'.

    `keep_unit=False` returns the bare range. Lengths and masses use symbols
    that read the same in every language, but "yr" does not — so lifespan is
    stored unitless and the template appends the translated word.
    """
    values, unit = [], ""
    for value in claim_values(entity, prop):
        if not isinstance(value, dict) or "amount" not in value:
            continue
        unit_qid = str(value.get("unit", "")).rsplit("/", 1)[-1]
        label = UNIT_MAP.get(unit_qid, "")
        if not label:
            continue
        if unit and label != unit:
            continue  # mixing kg with g would produce nonsense
        unit = label
        try:
            values.append(float(value["amount"]))
        except (TypeError, ValueError):
            continue
    if not values:
        return ""

    def fmt(number):
        if number == int(number) and abs(number) < 100000:
            return str(int(number))
        return f"{number:.1f}"

    if not keep_unit:
        unit = ""
    low, high = min(values), max(values)
    if low == high:
        return f"{fmt(low)} {unit}".strip()
    return f"{fmt(low)}–{fmt(high)} {unit}".strip()


def entity_id_values(entity, prop):
    out = []
    for value in claim_values(entity, prop):
        if isinstance(value, dict) and value.get("id"):
            out.append(value["id"])
    return out


# A chunk ending like this is an abbreviation, not a sentence end — without
# this, "…including L. a. agilis" gets cut to "…including L. a."
_ABBREV_END = re.compile(
    r"(?:^|\s)(?:[A-Za-z]|sp|ssp|subsp|var|cf|etc|ca|vs|approx|Dr|St|bzw|ggf|u|z|d)\.$"
)


def split_sentences(text):
    chunks = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for chunk in chunks:
        if out and _ABBREV_END.search(out[-1]):
            out[-1] = f"{out[-1]} {chunk}"
        else:
            out.append(chunk)
    return out


def wikipedia_summary(title, lang):
    if not title:
        return ""
    quoted = urllib.parse.quote(title.replace(" ", "_"), safe="")
    data = http_get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quoted}")
    time.sleep(DELAY)
    if not data:
        return ""
    extract = (data.get("extract") or "").strip()
    if len(extract) < 50:
        return ""
    sentences = split_sentences(extract)
    text = " ".join(sentences[:3])
    if len(text) > 480:
        text = " ".join(sentences[:2])
    return text


def inat_taxon(scientific):
    data = http_get(
        "https://api.inaturalist.org/v1/taxa",
        {"q": scientific, "per_page": 5},
    )
    time.sleep(DELAY)
    if not data:
        return None
    results = data.get("results") or []
    for result in results:
        if str(result.get("name", "")).lower() == scientific.lower():
            return result.get("id")
    return results[0].get("id") if results else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def enrich(record, verbose=True):
    """Fill empty fields on one species. Returns the list of fields written."""
    scientific = (record.get("scientific") or "").strip()
    if not scientific:
        return []

    protected = PROTECTED.get(record.get("slug") or "", frozenset())
    wanted = [path for path in FILLABLE
              if path not in protected and is_empty(get_path(record, path))]
    if not wanted:
        return []

    written = []

    # --- GBIF -------------------------------------------------------------
    if {"gbif_taxon_key", "family", "group"} & set(wanted) or "group" in wanted:
        gbif = gbif_match(scientific)
        if gbif.get("key") and "gbif_taxon_key" in wanted:
            set_path(record, "gbif_taxon_key", gbif["key"])
            written.append("gbif_taxon_key")
        if gbif.get("family") and "family" in wanted:
            set_path(record, "family", gbif["family"])
            written.append("family")
        # `group` is refined even when already set: the offline family table is
        # a guess, GBIF's class is authoritative.
        if gbif.get("class"):
            better = group_for(record.get("family"), gbif["class"])
            if better != "other" and better != record.get("group"):
                set_path(record, "group", better)
                written.append("group")

    # --- Wikidata ---------------------------------------------------------
    needs_wikidata = {
        "wikidata_id", "height", "body_weight", "diet", "lifespan", "iucn",
        "names.de", "names.sv",
        "description.en", "description.de", "description.sv",
        "reference.commons_file",
    } & set(wanted)
    if needs_wikidata:
        qid = record.get("wikidata_id")
        en_title = None
        if not qid:
            qid, en_title = wikidata_qid(scientific)
        if qid:
            if "wikidata_id" in wanted:
                set_path(record, "wikidata_id", qid)
                written.append("wikidata_id")
            entity = wikidata_entity(qid)
            if entity:
                labels = entity.get("labels") or {}
                sitelinks = entity.get("sitelinks") or {}

                for lang in ("de", "sv"):
                    path = f"names.{lang}"
                    label = labels.get(lang, {}).get("value")
                    if path in wanted and label:
                        # Swedish species names are conventionally lowercase on
                        # Wikidata; the dex shows them as headings, so raise the
                        # first letter without touching the rest.
                        set_path(record, path, label[:1].upper() + label[1:])
                        written.append(path)

                if "height" in wanted:
                    value = quantity_range(entity, "P2048")
                    if value:
                        set_path(record, "height", value)
                        written.append("height")
                if "body_weight" in wanted:
                    value = quantity_range(entity, "P2067")
                    if value:
                        set_path(record, "body_weight", value)
                        written.append("body_weight")
                if "lifespan" in wanted:
                    value = quantity_range(entity, "P2250", keep_unit=False)
                    if value:
                        set_path(record, "lifespan", value)
                        written.append("lifespan")
                if "diet" in wanted:
                    for diet_qid in entity_id_values(entity, "P1034"):
                        if diet_qid in DIET_MAP:
                            set_path(record, "diet", DIET_MAP[diet_qid])
                            written.append("diet")
                            break
                if "iucn" in wanted:
                    for iucn_qid in entity_id_values(entity, "P141"):
                        if iucn_qid in IUCN_MAP:
                            set_path(record, "iucn", IUCN_MAP[iucn_qid])
                            written.append("iucn")
                            break
                if "reference.commons_file" in wanted:
                    images = claim_values(entity, "P18")
                    if images and isinstance(images[0], str):
                        set_path(record, "reference.commons_file", images[0])
                        written.append("reference.commons_file")

                # --- Wikipedia descriptions -------------------------------
                for lang in ("en", "de", "sv"):
                    path = f"description.{lang}"
                    if path not in wanted:
                        continue
                    title = (sitelinks.get(f"{lang}wiki") or {}).get("title")
                    sitelink_title = title
                    if not title and lang == "en":
                        title = en_title or scientific
                    text = wikipedia_summary(title, lang)
                    if text:
                        set_path(record, path, text)
                        written.append(path)
                        # Wikipedia text is CC BY-SA, so the species page has to
                        # link the exact article it was abridged from. Only record
                        # a real sitelink — a guessed title (the scientific-name
                        # fallback above) may resolve through a redirect to an
                        # article under a different name, and a credit link that
                        # might be wrong is worse than none.
                        if sitelink_title:
                            quoted = urllib.parse.quote(
                                sitelink_title.replace(" ", "_"), safe="():,'!-")
                            set_path(record, f"description_source.{lang}",
                                     f"https://{lang}.wikipedia.org/wiki/{quoted}")
                            written.append(f"description_source.{lang}")

    # --- iNaturalist ------------------------------------------------------
    if "inat_taxon_id" in wanted:
        taxon_id = inat_taxon(scientific)
        if taxon_id:
            set_path(record, "inat_taxon_id", taxon_id)
            written.append("inat_taxon_id")

    return written


def file_header():
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", action="append", default=[], help="Limit to these slugs")
    parser.add_argument("--dry-run", action="store_true", help="Report, do not write")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N species")
    args = parser.parse_args(argv)

    species = load_dex()
    if not species:
        raise SystemExit("data/dex.yaml is empty — run scripts/dex-import.py first")

    header = file_header()
    todo = [s for s in species if not args.only or s.get("slug") in args.only]
    if args.limit:
        todo = todo[: args.limit]

    print(f"enriching {len(todo)} of {len(species)} species\n")
    touched = 0
    for index, record in enumerate(todo, 1):
        slug = record.get("slug", "?")
        missing = [p for p in FILLABLE if is_empty(get_path(record, p))]
        if not missing:
            continue
        written = enrich(record)
        if written:
            touched += 1
            print(f"  [{index}/{len(todo)}] {slug}: +{', '.join(written)}")
        else:
            print(f"  [{index}/{len(todo)}] {slug}: nothing found")

        # Write incrementally so a long run is never lost to a network blip.
        if not args.dry_run and touched and index % 10 == 0:
            dump_dex(species, DEX_PATH, header=header)

    print(f"\n{touched} species updated")
    if args.dry_run:
        print("(dry run — nothing written)")
        return 0
    dump_dex(species, DEX_PATH, header=header)
    print(f"wrote {DEX_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
