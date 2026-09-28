#!/usr/bin/env python3
"""One-time: give every entry in data/gaming.yaml a `slug:`.

The slug is a game's page URL (/<lang>/gaming/<slug>/) and the key its copies
are merged on. From now on the syncs write it once, when they first see a game,
and never recompute it (docs/concepts/gaming-game-pages.md §2). This script
does the same for the entries that existed before that rule did.

Copies that share a title get the same slug, so every game that is one card
today stays one card. Two different titles that fold to the same slug
(`Rocket League®` / `Rocket League`) merge — reported, because that is a change
to what the grid shows. Two copies on the SAME platform landing on one slug would
be two different games the build refuses to merge; the script stops without
writing anything if that happens.

The slug line goes directly under `- title:`, which is where the syncs emit it.
Everything else is left byte-for-byte as it was. Entries that already carry a
slug are skipped, so a second run is a no-op.

Standard library only; it writes one file and never runs git.

Usage:
    python3 scripts/gaming-add-slugs.py --dry-run
    python3 scripts/gaming-add-slugs.py
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gaming_common import GAMING_DATA, slugify  # noqa: E402

ENTRY_START = re.compile(r"^-\s")
TITLE_LINE = re.compile(r"^-?\s*title:\s*(.*?)\s*$")


def yaml_scalar(raw):
    """The value of a one-line YAML scalar as the syncs write it."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    return raw


def field(lines, key):
    pat = re.compile(r"^-?\s*" + re.escape(key) + r":\s*(.*?)\s*$")
    for ln in lines:
        m = pat.match(ln)
        if m:
            return yaml_scalar(m.group(1))
    return None


def add_slugs(text):
    """Pure: return (new_text, report). `report` has `added` [(title, platform,
    slug)], `merged` {slug: sorted titles} for slugs that now join different
    titles, and `clashes` {slug: [(platform, title), ...]} for same-platform
    collisions — non-empty clashes mean the caller must not write."""
    lines = text.split("\n")
    starts = [i for i, ln in enumerate(lines) if ENTRY_START.match(ln)]
    bounds = [(s, starts[k + 1] if k + 1 < len(starts) else len(lines))
              for k, s in enumerate(starts)]

    entries = []
    for start, end in bounds:
        chunk = lines[start:end]
        title = field(chunk, "title") or ""
        entries.append({
            "start": start,
            "chunk": chunk,
            "title": title,
            "platform": (field(chunk, "platform") or "manual").lower(),
            "slug": field(chunk, "slug"),
        })

    # Existing slugs win; a title that already has one lends it to its other copies.
    by_title = {}
    for e in entries:
        if e["slug"]:
            by_title.setdefault(e["title"], e["slug"])
    for e in entries:
        if not e["slug"]:
            e["new"] = by_title.get(e["title"]) or slugify(e["title"]) or "game"
            by_title.setdefault(e["title"], e["new"])

    titles, platforms = defaultdict(set), defaultdict(list)
    for e in entries:
        slug = e["slug"] or e["new"]
        titles[slug].add(e["title"])
        platforms[(slug, e["platform"])].append(e["title"])
    merged = {s: sorted(t) for s, t in titles.items() if len(t) > 1}
    clashes = {}
    for (slug, platform), ts in platforms.items():
        if len(ts) > 1:
            clashes.setdefault(slug, []).extend((platform, t) for t in ts)

    added = []
    out = list(lines)
    for e in sorted(entries, key=lambda e: e["start"], reverse=True):
        if e["slug"]:
            continue
        offset = next((k for k, ln in enumerate(e["chunk"]) if TITLE_LINE.match(ln)), 0)
        out.insert(e["start"] + offset + 1, f"  slug: {e['new']}")
        added.append((e["title"], e["platform"], e["new"]))
    added.reverse()
    return "\n".join(out), {"added": added, "merged": merged, "clashes": clashes}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Add a slug to every entry in data/gaming.yaml.")
    parser.add_argument("--data", type=Path, default=GAMING_DATA)
    parser.add_argument("--dry-run", action="store_true", help="Report without writing.")
    args = parser.parse_args(argv)

    text = args.data.read_text(encoding="utf-8")
    new_text, report = add_slugs(text)

    for slug, pairs in sorted(report["clashes"].items()):
        print(f"! {slug}: two copies on one platform — "
              + ", ".join(f"{t} ({p})" for p, t in pairs), file=sys.stderr)
    if report["clashes"]:
        print("Nothing written. Give one of each pair a `slug:` by hand, then rerun.",
              file=sys.stderr)
        return 1

    for slug, ts in sorted(report["merged"].items()):
        print(f"  merge: {slug} <- {' | '.join(ts)}", file=sys.stderr)
    slugs = {s for _, _, s in report["added"]}
    print(f"{len(report['added'])} entries get a slug ({len(slugs)} distinct); "
          f"{len(report['merged'])} slug(s) join different titles.", file=sys.stderr)

    if args.dry_run:
        print("(dry-run: nothing written)", file=sys.stderr)
        return 0
    if new_text != text:
        args.data.write_text(new_text, encoding="utf-8")
        print(f"Wrote {args.data}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
