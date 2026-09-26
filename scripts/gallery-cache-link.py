#!/usr/bin/env python3
"""One-time: keep the image cache warm across the switch to slug file names.

The build publishes every gallery photo under its English slug instead of the
store filename (docs/concepts/gallery-metadata-yaml-only.md §5): gallery-images.html
copies each resource to `images/gallery/<fileSlug><ext>` before anything
processes it. Hugo keys its processed-image cache by that name, so without help
the first build after the switch would re-render all ~3,500 variants — the 10+
minute cold rebuild the cache exists to avoid.

It does not have to. The `_hu_<hash>` part of a cached variant depends on the
pixels and the processing spec, not on the name or the extension's case (checked
on Hugo 0.166.0). So each cached variant

    resources/_gen/images/images/gallery/<store stem>_hu_<hash>.<ext>

is hardlinked to the name the renamed build will look for,

    resources/_gen/images/images/gallery/<fileSlug>_hu_<hash>.<ext, lowercased>

and that build is a pure cache hit.

Rules:

  * Only ADDS hardlinks. Nothing in the cache is deleted, moved or overwritten; a
    target that already exists is left alone (and reported if it is a different
    file). The old entries stay until `hugo --gc` retires them, if ever.
  * The store-stem → file-slug mapping comes from Hugo's own manifest
    (`gallery-metadata.json`, fields `src` and `file`), never from a second slug
    implementation in Python. Build once with the `file` field in place and the
    copy NOT yet active, then run this, then switch the copy on.
  * `--dry-run` prints the plan and touches nothing. A second run finds nothing
    to do.

Standard library only.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gallery_common import repo_root  # noqa: E402

CACHED_RE = re.compile(r"^(?P<stem>.+)_hu_(?P<hash>[0-9a-f]+)\.(?P<ext>[A-Za-z0-9]+)$")


def parse_args(argv):
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--site", type=Path, default=root / ".test-site",
                        help="A build whose en/gallery-metadata.json has `src` and `file` "
                        "(default: <repo>/.test-site)")
    parser.add_argument("--cache", type=Path,
                        default=root / "resources" / "_gen" / "images" / "images" / "gallery",
                        help="Hugo's processed-image cache for the gallery")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan, link nothing.")
    return parser.parse_args(argv)


def stem_map(manifest_photos):
    """{store stem: file slug} from manifest records carrying `src` and `file`."""
    out = {}
    for p in manifest_photos:
        src, file = p.get("src") or "", p.get("file") or ""
        if not src or not file:
            sys.exit(f"ERROR: manifest record {p.get('id')} has no `src`/`file` — build with "
                     "the `file` field in place first.")
        out[os.path.splitext(src)[0]] = os.path.splitext(file)[0]
    return out


def plan_links(names, mapping):
    """(links, skipped) for the cache file names: links is [(old, new)], in order.

    A name that is not a cached variant, or whose stem is no store stem, is not
    touched. A stem that already IS its slug needs no link.
    """
    links = []
    for name in sorted(names):
        m = CACHED_RE.match(name)
        if not m:
            continue
        slug = mapping.get(m.group("stem"))
        if slug is None:
            continue
        new = f"{slug}_hu_{m.group('hash')}.{m.group('ext').lower()}"
        if new != name:
            links.append((name, new))
    return links


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    manifest = args.site / "en" / "gallery-metadata.json"
    if not manifest.is_file():
        sys.exit(f"ERROR: no manifest at {manifest} — build first.")
    if not args.cache.is_dir():
        sys.exit(f"ERROR: no image cache at {args.cache} — nothing to keep warm.")

    mapping = stem_map(json.loads(manifest.read_text(encoding="utf-8"))["photos"])
    links = plan_links(os.listdir(args.cache), mapping)

    made = present = conflicts = 0
    for old, new in links:
        src, dst = args.cache / old, args.cache / new
        if dst.exists():
            if os.path.samefile(src, dst):
                present += 1
            else:
                conflicts += 1
                print(f"WARNING: {new} exists and is a different file — left alone", file=sys.stderr)
            continue
        if not args.dry_run:
            os.link(src, dst)
        made += 1

    verb = "Would link" if args.dry_run else "Linked"
    print(f"{verb} {made} cached variant(s) under their slug names "
          f"({present} already linked, {conflicts} conflict(s), "
          f"{len(mapping)} photos in the manifest).")
    return 1 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
