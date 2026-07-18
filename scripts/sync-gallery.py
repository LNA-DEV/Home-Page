#!/usr/bin/env python3
"""Sync data/gallery.yaml with the gallery photos folder.

The gallery model is one flat photo folder + central metadata in
data/gallery.yaml (one entry per image, keyed by `src` = bare filename).
This script keeps the two in lockstep:

  * If gallery.yaml references a `src:` that has no file on disk, that is
    treated as an ERROR (likely a rename to fix by hand) — the script
    reports every such entry and exits non-zero WITHOUT modifying the file.

  * If a photo on disk has no gallery.yaml entry, a minimal stub entry is
    appended to the end of the `images:` list:

        - id: <fresh uuid4>
          src: <filename>
          category: others
          section: general

    Nothing else is filled in — the Hugo build will error on such photos
    until a license is added, which usefully flags them as needing work.

Paths default to the repo layout (this script lives in <repo>/scripts/).
The photos folder is the gitignored `gallery-photos` symlink at the repo
root (see hugo.yaml module.mounts). Use --data / --photos to override,
mainly for testing against fixtures.

Standard library only — no YAML dependency. gallery.yaml is edited as text
so existing entries stay byte-for-byte unchanged and the git diff is limited
to the appended lines.
"""

import argparse
import os
import re
import sys
import uuid
from pathlib import Path

# Extensions we treat as gallery images (case-insensitive), so stray files
# like .DS_Store never get a stub entry.
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff"}

SRC_RE = re.compile(r"^  src: (.*)$")


def parse_args(argv):
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data",
        type=Path,
        default=repo_root / "data" / "gallery.yaml",
        help="Path to gallery.yaml (default: <repo>/data/gallery.yaml)",
    )
    parser.add_argument(
        "--photos",
        type=Path,
        default=repo_root / "gallery-photos",
        help="Path to the photos folder (default: <repo>/gallery-photos)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing anything.",
    )
    return parser.parse_args(argv)


def find_images_block(lines):
    """Return (start, end) line indices for entries within the `images:` list.

    `start` is the index of the first line after `images:`.
    `end` is the index of the next top-level key (e.g. `projects:`) or EOF;
    new entries are inserted immediately before it.
    """
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^images:\s*$", line):
            start = i + 1
            break
    if start is None:
        sys.exit("ERROR: could not find a top-level `images:` key in the data file.")

    end = len(lines)
    for i in range(start, len(lines)):
        # The next top-level mapping key (e.g. `projects:`) ends the block.
        # List items (`- ...`) also sit in column 0, so exclude them and
        # comments; only a bare column-0 key terminates the images list.
        line = lines[i]
        if line and not line[0].isspace() and line[0] not in "-#":
            end = i
            break
    return start, end


def collect_src(lines, start, end):
    srcs = set()
    for i in range(start, end):
        m = SRC_RE.match(lines[i])
        if m:
            srcs.add(m.group(1).rstrip())
    return srcs


def list_disk_images(photos_dir):
    names = set()
    for entry in os.scandir(photos_dir):
        if entry.is_file() and Path(entry.name).suffix.lower() in IMAGE_EXTS:
            names.add(entry.name)
    return names


def build_stub(filename):
    return [
        f"- id: {uuid.uuid4()}",
        f"  src: {filename}",
        "  category: others",
        "  section: general",
    ]


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if not args.data.is_file():
        sys.exit(f"ERROR: data file not found: {args.data}")
    # Follows the symlink; a clean checkout without `gallery-photos` lands here.
    if not args.photos.is_dir():
        sys.exit(
            f"ERROR: photos folder not found or not a directory: {args.photos}\n"
            "       (create the `gallery-photos` symlink — see CLAUDE.md / hugo.yaml)"
        )

    raw = args.data.read_text(encoding="utf-8")
    # keepends=False; we re-join with "\n" and restore a trailing newline below.
    lines = raw.split("\n")
    trailing_newline = raw.endswith("\n")
    if trailing_newline:
        lines = lines[:-1]

    start, end = find_images_block(lines)
    srcs = collect_src(lines, start, end)
    disk = list_disk_images(args.photos)

    missing_files = sorted(srcs - disk)
    new_files = sorted(disk - srcs)

    # Error case: YAML entry with no file on disk. Never write in this case.
    if missing_files:
        for name in missing_files:
            print(f"ERROR: gallery.yaml references missing file: {name}", file=sys.stderr)
        n = len(missing_files)
        print(
            f"\n{n} gallery.yaml entr{'y' if n == 1 else 'ies'} "
            f"point{'s' if n == 1 else ''} to files that do not exist on disk.\n"
            "Fix these first (rename the `src:` or restore the file) — no changes were made.",
            file=sys.stderr,
        )
        return 1

    if not new_files:
        print(f"In sync: {len(srcs)} entries, {len(disk)} files.")
        return 0

    # Build stub entries for the new files and insert before the block end.
    additions = []
    for name in new_files:
        additions.extend(build_stub(name))

    noun = "entry" if len(new_files) == 1 else "entries"

    if args.dry_run:
        print(f"Would add {len(new_files)} stub {noun} for:")
        for name in new_files:
            print(f"  + {name}")
        print("\n--- entries that would be inserted ---")
        print("\n".join(additions))
        return 0

    new_lines = lines[:end] + additions + lines[end:]
    out = "\n".join(new_lines)
    if trailing_newline:
        out += "\n"
    args.data.write_text(out, encoding="utf-8")

    print(f"Added {len(new_files)} stub {noun}:")
    for name in new_files:
        print(f"  + {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
