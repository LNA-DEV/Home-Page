#!/usr/bin/env python3
"""Freeze the site's old `_hu_` image URLs into data/legacyImageVariants.yaml.

Until 2026-10 every processed image was published under Hugo's cache key,
`<name>_hu_<hash>.<ext>`, and Hugo owns that hash: Hugo 0.166.0 moved all of them
on 2026-09-10 with byte-identical files behind them. The build now publishes each
variant under a name of its own (layouts/partials/image-variant.html,
`<dir>/<spec>/<name>.<ext>`), and this script works out, once, which new file each
old hash was -- so nginx can redirect the URLs search engines, feed readers and
link previews still hold. docs/concepts/stable-image-urls.md §5.

    hugo  ->  scripts/legacy-image-variants.py [SITE_DIR]  ->  read the report
          ->  (only then) scripts/gallery-embed-metadata.py

It must run on Hugo's RAW output: the embedding pass rewrites every file under
images/gallery/, and after that no gallery variant has the bytes of its cache
file any more.

What it reads
  - every file in a spec directory of SITE_DIR (default .test-site): its bytes,
    its source and its pixel size -- the NEW variants;
  - every `*_hu_*` file in resources/_gen/images/, the image cache, which mirrors
    the published paths and holds everything this machine has rendered since
    2026-08-19, under old and new names (hardlinks are read once per inode) --
    the OLD URLs.

How it decides (D6), per old hash
  1. equal bytes to a new variant of the same source              -> a line
  2. else exactly ONE new variant of the same source with the same
     pixel size and format (the chain changed, so the bytes did,
     but source, size and format say it is the same picture)     -> a line
  3. anything else -- several candidates, a re-cropped source, a
     retired spec, a source that is gone                          -> nothing
  There is deliberately no "send it to some image of the same source": an old
  name is redirected only where the build history proves which variant it was.

What it writes
  gallery:   "<hash>": ["<photo id>", "<spec dir>"]   the current slug is
                                                       rendered by Hugo, so a later
                                                       reworded title cannot break
                                                       the line
  other:     "<old dir>/_hu_<hash>": "<new path>"     a decoded URL path
  Both are rendered into /_nginx/image-variant-redirects.map by
  layouts/_default/home.nginxvariantmap.map.

The file is FROZEN, like slugAliases: never recomputed, and a rerun only adds
lines -- an existing line is never changed or dropped, and the cache is not
needed for it afterwards. It prints a report (counts per rule and per area, and
every ambiguous case) for the owner to read before the file is committed.
Standard library only.
"""

import argparse
import hashlib
import json
import os
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gallery_common import repo_root  # noqa: E402

# A spec directory as image-variant.html names it. The action comes first in
# every spec the site uses, which is what tells a spec directory apart from an
# ordinary directory of a page bundle.
SPEC_DIR_RE = re.compile(r"^(?:resize|fit|fill|crop)-[a-z0-9]+(?:-[a-z0-9]+)*$")
CACHED_RE = re.compile(r"^(?P<stem>.+)_hu_(?P<hash>[0-9a-f]+)\.(?P<ext>[A-Za-z0-9]+)$")
FORMATS = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif",
           "tif": "tiff", "tiff": "tiff", "bmp": "bmp"}
GALLERY_DIR = "images/gallery"

HEADER = """\
# Old `_hu_<hash>` image URLs -> the file each one was, now published under a
# stable name. GENERATED ONCE by scripts/legacy-image-variants.py and FROZEN,
# like slugAliases: never recomputed, a rerun only adds lines. Rendered into
# /_nginx/image-variant-redirects.map by layouts/_default/home.nginxvariantmap.map.
# docs/concepts/stable-image-urls.md §5.
#
#   gallery:  "<hash>": ["<photo id>", "<spec dir>"]   (Hugo renders the current slug)
#   other:    "<old dir>/_hu_<hash>": "<new path>"
"""


# --- pixel size from the header ---------------------------------------------

def image_size(path):
    """(width, height) from the file header, or None. JPEG, PNG, WebP, GIF."""
    with open(path, "rb") as fh:
        head = fh.read(64)
        if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
            return struct.unpack(">II", head[16:24])
        if head[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", head[6:10])
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            chunk = head[12:16]
            if chunk == b"VP8 ":
                w, h = struct.unpack("<HH", head[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if chunk == b"VP8L":
                b = head[21:25]
                w = 1 + (((b[1] & 0x3F) << 8) | b[0])
                h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
                return w, h
            if chunk == b"VP8X":
                w = 1 + int.from_bytes(head[24:27], "little")
                h = 1 + int.from_bytes(head[27:30], "little")
                return w, h
            return None
        if head[:2] == b"\xff\xd8":
            fh.seek(2)
            while True:
                marker = fh.read(2)
                if len(marker) < 2 or marker[0] != 0xFF:
                    return None
                code = marker[1]
                if code in (0xD8, 0x01) or 0xD0 <= code <= 0xD7:
                    continue
                length = struct.unpack(">H", fh.read(2))[0]
                if 0xC0 <= code <= 0xCF and code not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">xHH", fh.read(5))
                    return w, h
                fh.seek(length - 2, 1)
    return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fmt(name):
    return FORMATS.get(name.rsplit(".", 1)[-1].lower())


# --- the gallery's names ----------------------------------------------------

def gallery_names(site, gallery_yaml):
    """{lowercased old or current name stem: photo id}, and {file: id}.

    A gallery file has been published under three kinds of name: the store
    filename (until 2026-09-26), the current file slug, and a former file slug
    -- which, after a reworded English title, is what `slugAliases` keeps.
    """
    manifest = json.loads((site / "en" / "gallery-metadata.json").read_text(encoding="utf-8"))
    by_file, names = {}, {}
    for p in manifest["photos"]:
        by_file[p["file"]] = p["id"]
        names[p["file"].rsplit(".", 1)[0].lower()] = p["id"]
        names[p["src"].rsplit(".", 1)[0].lower()] = p["id"]
    current = None
    for line in gallery_yaml.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^- id: (\S+)\s*$", line)
        if m:
            current = m.group(1)
            continue
        m = re.match(r"^  slugAliases: \[(.*)\]\s*$", line)
        if m and current:
            for alias in m.group(1).split(","):
                alias = alias.strip().strip("\"'").lower()
                if alias:
                    names.setdefault(alias, current)
    return names, by_file


# --- the two sides ----------------------------------------------------------

def new_variants(site, by_file):
    """Every file in a spec directory of the build: {source key: [variant]}.

    The source key is the URL path the source has (or would have) without its
    extension: "/images/gallery/<photo id>" for a gallery photo -- the id, so a
    store name and a slug of one photo meet -- else "<dir>/<sub-path/stem>".
    """
    out = defaultdict(list)
    for dirpath, dirnames, filenames in os.walk(site):
        dirnames.sort()
        rel_dir = Path(dirpath).relative_to(site)
        parts = rel_dir.parts
        spec_at = [i for i, part in enumerate(parts) if SPEC_DIR_RE.match(part)]
        if not spec_at:
            continue
        i = spec_at[-1]
        spec = parts[i]
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if "/".join(parts[:i]) == GALLERY_DIR and i == len(parts) - 1:
                photo = by_file.get(name)
                if photo is None:
                    continue
                key = f"/{GALLERY_DIR}/{photo}"
            else:
                rest = parts[:i] + parts[i + 1:]
                key = "/" + "/".join((*rest, name.rsplit(".", 1)[0]))
            out[key].append({
                "path": "/" + "/".join((*parts, name)),
                "spec": spec,
                "sha": sha256(path),
                "size": image_size(path),
                "format": fmt(name),
            })
    return out


def old_variants(cache, names):
    """Every `_hu_` file in the image cache: [(old dir, hash, source key, file)].

    One entry per (dir, hash): the same hash under a store name and under a slug
    is one cache entry Hugo hardlinked (scripts/gallery-cache-link.py), and the
    redirect is keyed by directory and hash alone.
    """
    out = {}
    unresolved = 0
    for dirpath, dirnames, filenames in os.walk(cache):
        dirnames.sort()
        rel = Path(dirpath).relative_to(cache).as_posix()
        old_dir = "/" if rel == "." else f"/{rel}/"
        for name in sorted(filenames):
            m = CACHED_RE.match(name)
            if not m or fmt(name) is None:
                continue
            path = Path(dirpath) / name
            key = (old_dir, m.group("hash"))
            if key in out:
                continue
            stem = m.group("stem")
            if rel == GALLERY_DIR:
                photo = names.get(stem.lower())
                if photo is None:
                    unresolved += 1
                    continue
                source = f"/{GALLERY_DIR}/{photo}"
            else:
                source = old_dir + stem
            out[key] = (source, path)
    return out, unresolved


# --- deciding ---------------------------------------------------------------

def decide(old, new):
    """Apply D6. Returns (lines, report), lines = {(old dir, hash): variant}."""
    lines = {}
    stats = defaultdict(lambda: defaultdict(int))
    ambiguous = []
    sha_cache = {}
    for (old_dir, h), (source, path) in sorted(old.items()):
        area = "gallery" if old_dir == f"/{GALLERY_DIR}/" else "other"
        candidates = new.get(source, [])
        if not candidates:
            stats[area]["source gone"] += 1
            continue
        # Hardlinks (a store name and a slug for one cache entry) are hashed once.
        inode = path.stat().st_ino
        if inode not in sha_cache:
            sha_cache[inode] = sha256(path)
        same = sorted((c for c in candidates if c["sha"] == sha_cache[inode]), key=lambda c: c["path"])
        if same:
            lines[(old_dir, h)] = same[0]
            stats[area]["equal bytes"] += 1
            continue
        size, form = image_size(path), fmt(path.name)
        alike = [c for c in candidates if c["size"] == size and c["format"] == form]
        if len(alike) == 1:
            lines[(old_dir, h)] = alike[0]
            stats[area]["same source, size, format"] += 1
        elif len(alike) > 1:
            stats[area]["ambiguous"] += 1
            ambiguous.append((f"{old_dir}_hu_{h}", size, [c["path"] for c in alike]))
        else:
            stats[area]["no match"] += 1
    return lines, stats, ambiguous


# --- the data file ----------------------------------------------------------

def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def read_existing(path):
    """The frozen lines already in the data file: ({hash: [id, dir]}, {key: path})."""
    gallery, other = {}, {}
    if not path.is_file():
        return gallery, other
    section = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("gallery:"):
            section = gallery
            continue
        if line.startswith("other:"):
            section = other
            continue
        m = re.match(r'^  "((?:[^"\\]|\\.)*)": (.*)$', line)
        if not m or section is None:
            continue
        section[json.loads(f'"{m.group(1)}"')] = json.loads(m.group(2))
    return gallery, other


def render(gallery, other):
    out = [HEADER, "gallery:"]
    for h in sorted(gallery):
        photo, spec = gallery[h]
        out.append(f"  {q(h)}: [{q(photo)}, {q(spec)}]")
    out.append("other:")
    for k in sorted(other):
        out.append(f"  {q(k)}: {q(other[k])}")
    return "\n".join(out) + "\n"


def main(argv=None):
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("site", nargs="?", type=Path, default=root / ".test-site",
                        help="Hugo's raw build output, BEFORE the embedding pass (default: .test-site)")
    parser.add_argument("--cache", type=Path, default=root / "resources" / "_gen" / "images")
    parser.add_argument("--out", type=Path, default=root / "data" / "legacyImageVariants.yaml")
    parser.add_argument("--dry-run", action="store_true", help="report, write nothing")
    args = parser.parse_args(argv)

    if not (args.site / "en" / "gallery-metadata.json").is_file():
        sys.exit(f"ERROR: no build at {args.site} — run `hugo` first")
    if not args.cache.is_dir():
        sys.exit(f"ERROR: no image cache at {args.cache}")

    names, by_file = gallery_names(args.site, root / "data" / "gallery.yaml")
    new = new_variants(args.site, by_file)
    if not new:
        sys.exit(f"ERROR: no spec directories under {args.site} — is this a build with stable names?")
    old, unresolved = old_variants(args.cache, names)
    lines, stats, ambiguous = decide(old, new)

    gallery, other = read_existing(args.out)
    kept = len(gallery) + len(other)
    added = 0
    for (old_dir, h), variant in sorted(lines.items()):
        if old_dir == f"/{GALLERY_DIR}/":
            if h not in gallery:
                photo = variant["path"].rsplit("/", 1)[-1]
                gallery[h] = [by_file[photo], variant["spec"]]
                added += 1
        else:
            key = f"{old_dir}_hu_{h}"
            if key not in other:
                other[key] = variant["path"]
                added += 1

    print(f"New variants indexed: {sum(len(v) for v in new.values())} "
          f"for {len(new)} sources")
    print(f"Old hashes in the cache: {len(old)} (gallery names that resolve to no "
          f"photo: {unresolved})")
    for area in ("gallery", "other"):
        print(f"  {area}:")
        for rule in ("equal bytes", "same source, size, format", "ambiguous", "no match", "source gone"):
            print(f"    {rule:28} {stats[area][rule]:6}")
    if ambiguous:
        print(f"\nAmbiguous ({len(ambiguous)}) — more than one new variant of the source "
              "has that size and format; left out:")
        for key, size, cands in ambiguous:
            print(f"  {key} {size[0]}x{size[1]}" if size else f"  {key}")
            for c in cands:
                print(f"      {c}")
    print(f"\n{kept} line(s) kept, {added} added -> {len(gallery)} gallery + {len(other)} other")
    if args.dry_run:
        print("(dry run: nothing written)")
        return 0
    args.out.write_text(render(gallery, other), encoding="utf-8")
    print(f"Written to {args.out.relative_to(root) if args.out.is_relative_to(root) else args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
