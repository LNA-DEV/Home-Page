#!/usr/bin/env python3
"""Close the gaps in the dex numbering.

`number` in `data/dex.yaml` does two jobs: it is the badge on the species card
and hero (`#001`), and it is the sort key for the dex grid — `dex-index.html`
sorts by it and there is no other sort control, so number order is the only order
the grid ever has.

Removing species leaves holes in that sequence (`#037`, `#043`–`#054`, …), which
read as missing entries rather than as history. This script renumbers every
record to a contiguous `001`, `002`, `003`, … **in the order they already have**,
so nothing is reordered — only the holes are closed.

Why not reorder while we are here: the existing sequence is import order from the
`animal-dex` proof of concept and carries no taxonomic meaning, but it is what the
grid has always looked like, and preserving it keeps the change to exactly the one
thing that was wrong.

Note that this does move numbers: every record after the first hole shifts down,
so a species' number is not stable across a renumber. Nothing depends on it —
`number` appears only in those two badges and that one sort, never in a URL, a
deep link, or the likes API (those all key off the slug or the image id).

`scripts/dex-add.py` assigns the lowest free number, so once the sequence is
contiguous a newly added species simply appends as N+1. Run this again after any
removal to close the holes it leaves behind.

Standard library only.

Usage:
    python3 scripts/dex-renumber.py --dry-run
    python3 scripts/dex-renumber.py --write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dex_common import DEX_PATH, dump_dex, load_dex  # noqa: E402


def sort_key(entry):
    """Current position: numeric where possible, unnumbered entries last."""
    raw = str(entry.get("number", "")).strip()
    return (0, int(raw)) if raw.isdigit() else (1, 0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="Apply the renumbering")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default)")
    args = parser.parse_args(argv)

    species = load_dex()
    if not species:
        raise SystemExit("data/dex.yaml is empty")

    ordered = sorted(species, key=sort_key)
    width = max(3, len(str(len(ordered))))

    changes = []
    for index, entry in enumerate(ordered, start=1):
        old = str(entry.get("number", "")).strip()
        new = str(index).zfill(width)
        if old != new:
            changes.append((old or "—", new, entry["slug"]))
        entry["number"] = new

    used = [int(e["number"]) for e in ordered]
    gaps = sorted(set(range(1, len(ordered) + 1)) - set(used))

    print(f"records   : {len(ordered)}")
    print(f"renumbered: {len(changes)}")
    print(f"gaps after: {gaps or 'none'}")
    if changes:
        print("\n  old  ->  new   slug")
        for old, new, slug in changes[:15]:
            print(f"  {old:>4} -> {new:>4}   {slug}")
        if len(changes) > 15:
            print(f"  … and {len(changes) - 15} more")

    if not args.write:
        print("\n(dry run — pass --write to apply)")
        return 0

    header = "\n".join(
        line.lstrip("#").lstrip() if line.strip() != "#" else ""
        for line in DEX_PATH.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    )
    dump_dex(ordered, DEX_PATH, header=header)
    print(f"\nwrote {DEX_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
