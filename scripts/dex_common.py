#!/usr/bin/env python3
"""Shared helpers for the dex scripts (import / tag / enrich / ranges / covers).

Standard library only — no PyYAML. `data/dex.yaml` is written by a tiny emitter
in this module and read back by a tiny parser, both of which understand exactly
the subset of YAML the emitter produces:

  * a top-level `species:` key holding a list of maps
  * scalars (strings, ints, floats, bools, null)
  * nested maps, one level of indentation each
  * lists of scalars (flow style: `[a, b, c]`)
  * lists of maps (block style, used for `sightings:`)
  * long text as double-quoted scalars with escaped newlines avoided by
    folding — see `_emit_scalar`

Keeping this self-contained means the dex scripts run on a bare `python3` the
same way `add-book.py` and `sync-steam.py` do.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEX_PATH = REPO_ROOT / "data" / "dex.yaml"
GALLERY_PATH = REPO_ROOT / "data" / "gallery.yaml"

USER_AGENT = "lna-dev.net dex tooling (https://lna-dev.net/; me@lna-dev.net)"

# Field order used when writing dex.yaml. Anything not listed is appended
# afterwards in sorted order, so an unknown field is preserved rather than lost.
FIELD_ORDER = [
    "slug",
    "number",
    "scientific",
    "family",
    "group",
    "difficulty",
    "marine",
    "iucn",
    "gbif_taxon_key",
    "inat_taxon_id",
    "wikidata_id",
    "height",
    "height_measure",
    "body_weight",
    "diet",
    "lifespan",
    "habitat",
    "reference",
    "sightings",
    "names",
    "description",
    "description_source",
    "tips",
]

# Taxonomic class (from GBIF) -> dex group. The dex groups are coarser than
# real taxonomy on purpose: they exist to drive the filter pills.
CLASS_TO_GROUP = {
    "mammalia": "mammals",
    "aves": "birds",
    "reptilia": "reptiles",
    "squamata": "reptiles",
    "testudines": "reptiles",
    "crocodylia": "reptiles",
    "amphibia": "amphibians",
    "insecta": "insects",
    "arachnida": "arachnids",
    "gastropoda": "molluscs",
    "cephalopoda": "molluscs",
    "bivalvia": "molluscs",
    "actinopterygii": "fish",
    "chondrichthyes": "fish",
    "elasmobranchii": "fish",
    "teleostei": "fish",
    "malacostraca": "crustaceans",
}

# Family -> dex group, used as the offline first pass so every species has a
# group even before `dex-enrich.py` confirms it against GBIF.
FAMILY_TO_GROUP = {
    # mammals
    "ailuridae": "mammals", "balaenopteridae": "mammals", "bovidae": "mammals",
    "canidae": "mammals", "castoridae": "mammals", "caviidae": "mammals",
    "cervidae": "mammals", "dasyuridae": "mammals", "delphinidae": "mammals",
    "elephantidae": "mammals", "equidae": "mammals", "erinaceidae": "mammals",
    "felidae": "mammals", "giraffidae": "mammals", "gliridae": "mammals",
    "hippopotamidae": "mammals", "hominidae": "mammals", "leporidae": "mammals",
    "macropodidae": "mammals", "monodontidae": "mammals", "mustelidae": "mammals",
    "odobenidae": "mammals", "ornithorhynchidae": "mammals",
    "phascolarctidae": "mammals", "phocidae": "mammals",
    "rhinocerotidae": "mammals", "sciuridae": "mammals", "suidae": "mammals",
    "ursidae": "mammals", "vespertilionidae": "mammals", "vombatidae": "mammals",
    "physeteridae": "mammals", "camelidae": "mammals", "muridae": "mammals",
    "talpidae": "mammals", "soricidae": "mammals", "cricetidae": "mammals",
    "myocastoridae": "mammals", "hystricidae": "mammals",
    # birds
    "accipitridae": "birds", "aegithalidae": "birds", "alcedinidae": "birds",
    "alcidae": "birds", "anatidae": "birds", "apterygidae": "birds",
    "ardeidae": "birds", "casuariidae": "birds", "certhiidae": "birds",
    "charadriidae": "birds", "ciconiidae": "birds", "cinclidae": "birds",
    "columbidae": "birds", "corvidae": "birds", "emberizidae": "birds",
    "falconidae": "birds", "fringillidae": "birds", "hirundinidae": "birds",
    "laridae": "birds", "meropidae": "birds", "motacillidae": "birds",
    "muscicapidae": "birds", "paridae": "birds", "passeridae": "birds",
    "phalacrocoracidae": "birds", "phasianidae": "birds",
    "phoenicopteridae": "birds", "picidae": "birds", "ramphastidae": "birds",
    "regulidae": "birds", "spheniscidae": "birds", "stercorariidae": "birds",
    "strigidae": "birds", "sturnidae": "birds", "troglodytidae": "birds",
    "turdidae": "birds", "tytonidae": "birds", "upupidae": "birds",
    "rallidae": "birds", "podicipedidae": "birds", "sylviidae": "birds",
    "prunellidae": "birds", "laniidae": "birds", "gruidae": "birds",
    "threskiornithidae": "birds", "scolopacidae": "birds", "pandionidae": "birds",
    # reptiles
    "alligatoridae": "reptiles", "cheloniidae": "reptiles",
    "crocodylidae": "reptiles", "dermochelyidae": "reptiles",
    "lacertidae": "reptiles", "testudinidae": "reptiles",
    "colubridae": "reptiles", "viperidae": "reptiles", "anguidae": "reptiles",
    "emydidae": "reptiles",
    # amphibians
    "ambystomatidae": "amphibians", "salamandridae": "amphibians",
    "bufonidae": "amphibians", "ranidae": "amphibians", "hylidae": "amphibians",
    # fish
    "lamnidae": "fish", "mobulidae": "fish", "pomacentridae": "fish",
    "rhincodontidae": "fish", "sphyrnidae": "fish", "salmonidae": "fish",
    "cyprinidae": "fish", "esocidae": "fish", "percidae": "fish",
    # insects
    "apidae": "insects", "lampyridae": "insects", "nymphalidae": "insects",
    "vespidae": "insects", "libellulidae": "insects", "coenagrionidae": "insects",
    "acrididae": "insects", "coccinellidae": "insects", "papilionidae": "insects",
    "pieridae": "insects", "formicidae": "insects", "sphingidae": "insects",
    "aeshnidae": "insects", "calopterygidae": "insects", "tettigoniidae": "insects",
    "carabidae": "insects", "cerambycidae": "insects", "syrphidae": "insects",
    # arachnids
    "araneidae": "arachnids", "salticidae": "arachnids", "lycosidae": "arachnids",
    # molluscs
    "enteroctopodidae": "molluscs", "helicidae": "molluscs",
    "arionidae": "molluscs", "cepaeidae": "molluscs", "limacidae": "molluscs",
}

# Diet vocabulary — stored as a slug in dex.yaml and translated through i18n,
# so a species record stays language-neutral.
DIET_SLUGS = {
    "omnivore", "carnivore", "herbivore", "piscivore", "insectivore",
    "frugivore", "granivore", "nectarivore", "detritivore", "filter-feeder",
}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def http_get(url, params=None, accept_json=True, retries=3, timeout=30):
    """GET a URL, returning parsed JSON (or raw bytes). None on 404."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": USER_AGENT}
    if accept_json:
        headers["Accept"] = "application/json"
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8")) if accept_json else raw
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            last_err = exc
            if exc.code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_err = exc
            time.sleep(1.0 * (attempt + 1))
    if last_err:
        print(f"    ! {url}: {last_err}")
    return None


# ---------------------------------------------------------------------------
# Minimal YAML reader for the subset dex.yaml uses
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")


def _parse_scalar(text):
    text = text.strip()
    if text == "" or text == "~" or text == "null":
        return None
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return json.loads(text)
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1].replace("''", "'")
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in _split_flow(inner)]
    if _NUM_RE.match(text):
        return int(text)
    if _FLOAT_RE.match(text):
        return float(text)
    return text


def _split_flow(inner):
    """Split a flow sequence body on commas that are not inside quotes."""
    parts, buf, quote = [], [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _indent_of(line):
    return len(line) - len(line.lstrip(" "))


def _parse_block(lines, idx, indent):
    """Parse a mapping or sequence at `indent`. Returns (value, next_idx)."""
    # Decide whether this block is a sequence or a mapping.
    probe = idx
    while probe < len(lines) and (not lines[probe].strip() or lines[probe].lstrip().startswith("#")):
        probe += 1
    if probe >= len(lines):
        return None, probe
    is_seq = lines[probe].lstrip().startswith("- ") or lines[probe].strip() == "-"

    if is_seq:
        items = []
        while idx < len(lines):
            line = lines[idx]
            if not line.strip() or line.lstrip().startswith("#"):
                idx += 1
                continue
            if _indent_of(line) < indent:
                break
            stripped = line.lstrip()
            if not stripped.startswith("-"):
                break
            rest = stripped[1:].lstrip()
            if not rest:
                idx += 1
                value, idx = _parse_block(lines, idx, indent + 2)
                items.append(value)
                continue
            # `- key: value` starts an inline mapping whose remaining keys are
            # indented to the column the key starts at.
            key_match = re.match(r"^([A-Za-z0-9_.-]+):(\s|$)", rest)
            if key_match:
                item_indent = _indent_of(line) + (len(stripped) - len(rest))
                synthetic = [" " * item_indent + rest] + lines[idx + 1:]
                value, consumed = _parse_block(synthetic, 0, item_indent)
                items.append(value)
                idx = idx + consumed
            else:
                items.append(_parse_scalar(rest))
                idx += 1
        return items, idx

    mapping = {}
    while idx < len(lines):
        line = lines[idx]
        if not line.strip() or line.lstrip().startswith("#"):
            idx += 1
            continue
        cur = _indent_of(line)
        if cur < indent:
            break
        if line.lstrip().startswith("- "):
            break
        key_match = re.match(r"^([A-Za-z0-9_.-]+):(?:\s+(.*))?$", line.strip())
        if not key_match:
            idx += 1
            continue
        key, inline = key_match.group(1), key_match.group(2)
        idx += 1
        if inline is not None and inline.strip() != "":
            mapping[key] = _parse_scalar(inline)
            continue
        # Nested block (or an explicitly empty value). A sequence may sit at
        # the same indent as its key (`species:` followed by `- slug: …`), so
        # that case counts as a nested block too.
        probe = idx
        while probe < len(lines) and (not lines[probe].strip() or lines[probe].lstrip().startswith("#")):
            probe += 1
        if probe < len(lines):
            probe_indent = _indent_of(lines[probe])
            is_seq_here = probe_indent == cur and lines[probe].lstrip().startswith("-")
            if probe_indent > cur or is_seq_here:
                value, idx = _parse_block(lines, probe, probe_indent)
                mapping[key] = value
                continue
        mapping[key] = None
    return mapping, idx


def load_dex(path=DEX_PATH):
    """Read data/dex.yaml -> list of species dicts (empty list if absent)."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    root, _ = _parse_block(lines, 0, 0)
    if not root:
        return []
    return root.get("species") or []


# ---------------------------------------------------------------------------
# Minimal YAML writer
# ---------------------------------------------------------------------------

_PLAIN_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _./()'’,+&-]*$")
_NUMERIC_LOOKING = re.compile(r"^[-+]?[0-9][0-9_]*(\.[0-9]+)?([eE][-+]?[0-9]+)?$")


def _emit_scalar(value):
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(text.split())  # dex text is always single-paragraph
    if text == "":
        return '""'
    # Keep plain style for short, unambiguous values; quote everything else so
    # colons, hashes and unicode punctuation can never break the file. Anything
    # that *looks* like a number is always quoted — `number: 001` would come
    # back from a YAML parser as the integer 1 and destroy the dex numbering.
    if len(text) <= 60 and _PLAIN_SAFE.match(text) and not text.endswith(" "):
        reserved = {"yes", "no", "true", "false", "on", "off", "null", "~"}
        if text.lower() not in reserved and not _NUMERIC_LOOKING.match(text):
            return text
    return json.dumps(text, ensure_ascii=False)


def _emit(key, value, indent, out):
    pad = " " * indent
    if isinstance(value, dict):
        if not value:
            return
        out.append(f"{pad}{key}:")
        for sub_key, sub_value in value.items():
            _emit(sub_key, sub_value, indent + 2, out)
        return
    if isinstance(value, list):
        if not value:
            return
        if all(not isinstance(item, (dict, list)) for item in value):
            rendered = ", ".join(_emit_scalar(item) for item in value)
            out.append(f"{pad}{key}: [{rendered}]")
            return
        out.append(f"{pad}{key}:")
        for item in value:
            if isinstance(item, dict):
                first = True
                for sub_key, sub_value in item.items():
                    prefix = f"{pad}  - " if first else f"{pad}    "
                    if isinstance(sub_value, (dict, list)):
                        buf = []
                        _emit(sub_key, sub_value, 0, buf)
                        out.append(prefix + buf[0])
                        out.extend(f"{pad}    " + line for line in buf[1:])
                    else:
                        out.append(f"{prefix}{sub_key}: {_emit_scalar(sub_value)}")
                    first = False
            else:
                out.append(f"{pad}  - {_emit_scalar(item)}")
        return
    out.append(f"{pad}{key}: {_emit_scalar(value)}")


def _prune(value):
    """Drop empty strings / dicts / lists / None so the file stays readable."""
    if isinstance(value, dict):
        cleaned = {}
        for key, sub in value.items():
            sub = _prune(sub)
            if sub is not None:
                cleaned[key] = sub
        return cleaned or None
    if isinstance(value, list):
        cleaned = [_prune(item) for item in value]
        cleaned = [item for item in cleaned if item is not None]
        return cleaned or None
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def dump_dex(species, path=DEX_PATH, header=None):
    """Write the species list back to dex.yaml in a stable field order."""
    out = []
    if header:
        out.extend(f"# {line}" if line else "#" for line in header.splitlines())
        out.append("")
    out.append("species:")
    for entry in sorted(species, key=lambda item: str(item.get("number", ""))):
        cleaned = _prune(entry) or {}
        ordered = {}
        for field in FIELD_ORDER:
            if field in cleaned:
                ordered[field] = cleaned[field]
        for field in sorted(set(cleaned) - set(FIELD_ORDER)):
            ordered[field] = cleaned[field]
        first = True
        for key, value in ordered.items():
            buf = []
            _emit(key, value, 0, buf)
            if not buf:
                continue
            out.append(("- " if first else "  ") + buf[0])
            out.extend("  " + line for line in buf[1:])
            first = False
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def slugify(text):
    text = str(text).strip().lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = text.replace("ß", "ss").replace("å", "a").replace("é", "e")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def group_for(family, taxon_class=None):
    """Best-effort dex group from a taxonomic class, falling back to family."""
    if taxon_class:
        hit = CLASS_TO_GROUP.get(str(taxon_class).strip().lower())
        if hit:
            return hit
    if family:
        hit = FAMILY_TO_GROUP.get(str(family).strip().lower())
        if hit:
            return hit
    return "other"
