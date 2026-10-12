#!/usr/bin/env python3
"""List a gallery project's photos, ready to paste into an essay or a journal.

    python3 scripts/project-photos.py wildlife-of-inn-valley
    python3 scripts/project-photos.py above-the-clouds --lang de

The story shortcodes (docs/concepts/gallery-project-stories.md) address photos
by UUID, which nobody can type from memory. This prints the project's photos
grouped by capture day, newest first, each with its UUID, its title and its
species (dex slug for {{< storySpecies >}}), plus a ready-made {{< outing >}}
line per day. It writes nothing.

The photos are the grid's: every entry in data/gallery.yaml whose `project:`
names the slug, archive excluded. Capture days are the BUILD's, read from the
gallery manifest Hugo writes (<lang>/gallery-metadata.json) -- the same EXIF
date the journal groups by, and the one thing this script cannot read from the
data file. It takes the newest of .test-site/ and public/, or --manifest. With
no build at all, every photo lands under "date unknown".

Standard library only, like every script here.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dex_common import load_yaml  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def as_list(value):
    """`project:` is a string or a list, like gallery-meta.html normalises it."""
    if not value:
        return []
    items = value if isinstance(value, list) else [value]
    return [str(v).strip() for v in items if str(v).strip()]


def pick(field, lang):
    """A per-language field (bare string = English), English fallback."""
    if isinstance(field, dict):
        return field.get(lang) or field.get("en") or ""
    return field or ""


def find_manifest(lang, explicit=None):
    if explicit:
        return Path(explicit)
    candidates = [ROOT / d / lang / "gallery-metadata.json" for d in (".test-site", "public")]
    existing = [p for p in candidates if p.is_file()]
    return max(existing, key=lambda p: p.stat().st_mtime) if existing else None


def capture_days(manifest):
    if not manifest:
        return {}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return {p["id"]: p.get("dateTaken") or "" for p in data.get("photos", [])}


def group(entries, days, slug, lang, dex_by_sci):
    """[(day or "", [row, ...]), ...] newest day first, the undated last."""
    rows = {}
    for e in entries:
        if slug not in as_list(e.get("project")) or e.get("section") == "archive":
            continue
        sci = (e.get("species") or "").strip()
        dex = dex_by_sci.get(sci.lower(), {})
        rows.setdefault(days.get(e["id"], ""), []).append({
            "id": e["id"],
            "title": pick(e.get("title"), lang),
            "species": pick(dex.get("names"), lang) or sci,
            "dex": dex.get("slug", ""),
        })
    dated = sorted((d for d in rows if d), reverse=True)
    return [(d, sorted(rows[d], key=lambda r: r["title"])) for d in dated] + (
        [("", rows[""])] if "" in rows else []
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug", help="the project slug (params.project_slug)")
    ap.add_argument("--lang", default="en", choices=["en", "de", "sv"], help="language of titles and names")
    ap.add_argument("--manifest", help="a gallery-metadata.json to take the capture days from")
    args = ap.parse_args(argv)

    entries = load_yaml(ROOT / "data" / "gallery.yaml").get("images", [])
    dex = {(s.get("scientific") or "").lower(): s for s in load_yaml(ROOT / "data" / "dex.yaml").get("species", [])}
    manifest = find_manifest(args.lang, args.manifest)
    groups = group(entries, capture_days(manifest), args.slug, args.lang, dex)
    if not groups:
        sys.exit(f"no photo in data/gallery.yaml names project {args.slug!r}")

    total = sum(len(rows) for _, rows in groups)
    source = manifest.relative_to(ROOT) if manifest and manifest.is_relative_to(ROOT) else manifest
    print(f"# {args.slug}: {total} photos, {sum(1 for d, _ in groups if d)} capture days")
    print(f"# capture days from {source or 'nowhere — build the site first (npm test, or the build project)'}")
    for day, rows in groups:
        print()
        if day:
            print(f"## {day} — {len(rows)} photo{'s' if len(rows) != 1 else ''}")
            print(f'{{{{< outing date="{day}" title="" >}}}}')
            print("{{< /outing >}}")
        else:
            print(f"## {'date unknown' if not manifest else 'undated'} — {len(rows)}")
        for r in rows:
            species = f"  [{r['species']}{', dex: ' + r['dex'] if r['dex'] else ''}]" if r["species"] else ""
            print(f"{r['id']}  {r['title']}{species}")


if __name__ == "__main__":
    main()
