#!/usr/bin/env python3
"""One-time migration: move the editorial metadata out of the JPEGs into gallery.yaml.

THIS HAS RUN. It is kept for the record, not for reuse — see
docs/concepts/gallery-metadata-import.md. A second run finds nothing to do and
says so, which is the intended way to confirm that.

Darktable is where the first English title, alt text and licence of a photo get
typed, and it writes them into the exported JPEG. The site used to read them back
at build time through fallbacks in collect-images.html, which meant a re-export
could change what the site said about a photo with no diff in git. This copies
those values into data/gallery.yaml once, rewrites the licence display strings
into keys of data/licenseMap.yaml on the way, and the fallbacks are then deleted.
After that the build reads nothing editorial out of a file except the tags, which
stay darktable-owned by design (main concept §3).

    exiftool ──> gallery_xmp.read() ──> fill EMPTY fields only ──> data/gallery.yaml

What moves: `license`, `alt`, `title`, `description`. Not tags, not technical
EXIF, not publisher. `artist` only with --artist: all 287 file values are
"Lukas Nagel", which is also site.Params.author.name and already the fallback, so
importing them adds 287 identical lines and no information.

Rules this script holds itself to:

  * The photo store is opened read-only, through exiftool. Nothing is ever
    written back to a source file.
  * An existing YAML value always wins, whatever the file says. Only an empty or
    missing field is filled, and no key is ever deleted.
  * data/gallery.yaml is edited as TEXT, not parsed and re-serialised: a YAML
    round trip would re-quote, re-order and re-wrap ~9,700 lines that are not
    part of the change and the diff would be unreviewable. Same reason
    sync-gallery.py does it.
  * The whole plan is built before anything is written, so an abort leaves the
    file untouched rather than half-migrated.

Standard library only, like every other script in this folder.
"""

import argparse
import difflib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gallery_common import (  # noqa: E402
    PHOTOS_SETUP_HINT,
    license_aliases,
    photos_dir_from_hugo_mounts,
    repo_root,
    yaml_scalar,
)
import gallery_xmp  # noqa: E402

# Same set sync-gallery.py uses, so the two agree on what counts as a photo.
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff"}

# The four editorial fields that move, in the order the phases run.
FIELDS = ("license", "alt", "title", "description")

# Where a key that the entry does not have yet is appended. This is the order the
# 626 complete entries already use (`… tags, alt, title, license, artist`), not
# the illustrative order of main concept §4 — the point of editing as text is
# that untouched lines stay untouched, so the file's own shape wins.
APPEND_ORDER = ("alt", "title", "license", "artist")

ENTRY_START = "- "
KEY_RE = re.compile(r"^(?:- |  )([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?$")
LIST_ITEM_RE = re.compile(r"^  - ")


def parse_args(argv):
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data",
        type=Path,
        default=root / "data" / "gallery.yaml",
        help="Path to gallery.yaml (default: <repo>/data/gallery.yaml)",
    )
    parser.add_argument(
        "--photos",
        type=Path,
        default=photos_dir_from_hugo_mounts(root),
        help="Path to the photos folder (default: the gallery mount `source` in "
        "config/_default/module.yaml, i.e. whatever Hugo itself builds from)",
    )
    parser.add_argument(
        "--artist",
        action="store_true",
        help="Also import `artist` from the files. Off by default: every value is "
        "\"Lukas Nagel\", which site.Params.author.name already supplies.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the diff and change nothing.",
    )
    return parser.parse_args(argv)


# --- reading data/gallery.yaml ------------------------------------------------


def find_images_block(lines):
    """Return (start, end) line indices of the entries under the `images:` key.

    `projects:` follows the image list in this file and has `title:`,
    `description:` and `category:` keys of its own, so the block bounds are not
    cosmetic — without them the licence rewrite would walk into project records.
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
        line = lines[i]
        # Only a bare column-0 key ends the list; entries and comments also start
        # in column 0.
        if line and not line[0].isspace() and line[0] not in "-#":
            end = i
            break
    return start, end


def parse_entries(lines, start, end):
    """Split the images block into entries with a line index per field.

    Returns a list of dicts: {lo, hi, fields: {name: (index, raw_value)}}. `hi` is
    the index of the entry's last line, which is where a missing key is appended.

    Anything that is not a `key: value` line, a bare `key:` header or a `- item`
    list item aborts the run: the text-level edit below is only safe on the flat,
    single-line shape this file actually has (no block scalars, no nesting), and
    the moment that stops being true the script must stop rather than guess.
    """
    entries = []
    current = None
    problems = []
    for i in range(start, end):
        line = lines[i]
        # A blank line or a comment must NOT move `hi`: an appended key would then
        # land after it, detached from the entry it belongs to.
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(ENTRY_START):
            current = {"lo": i, "hi": i, "fields": {}}
            entries.append(current)
        elif current is None:
            problems.append((i, line))
            continue
        if LIST_ITEM_RE.match(line):
            current["hi"] = i
            continue
        match = KEY_RE.match(line)
        if not match:
            problems.append((i, line))
            continue
        name, value = match.group(1), match.group(2)
        # A duplicate key is a data bug, not something to silently pick from.
        if name in current["fields"]:
            problems.append((i, line))
            continue
        current["fields"][name] = (i, value)
        current["hi"] = i

    if problems:
        for i, line in problems[:20]:
            print(f"ERROR: {i + 1}: cannot read as a single-line `key: value`: {line!r}",
                  file=sys.stderr)
        sys.exit(
            f"\n{len(problems)} line(s) in the images block are not the flat shape this "
            "script can edit as text. Nothing was written."
        )
    return entries


def is_empty(value):
    """True when a field is present but holds no value (`alt: ""`, `alt:`)."""
    if value is None:
        return True
    return value.strip() in ("", '""', "''", "~", "null")


def unquote(value):
    """The readable value of a raw YAML scalar, for reporting only."""
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


# --- the plan -----------------------------------------------------------------


class Plan:
    """Line edits to apply to data/gallery.yaml, built completely before any write.

    Replacements are keyed by line index and insertions by the index they follow,
    so applying them is one bottom-up pass and no index ever shifts under another
    edit.
    """

    def __init__(self):
        self.replace = {}      # index -> new line
        self.insert_after = {} # index -> [new lines]
        self.counts = {}

    def set_line(self, index, line, phase):
        self.replace[index] = line
        self.counts[phase] = self.counts.get(phase, 0) + 1

    def add_line(self, after, line, phase):
        self.insert_after.setdefault(after, []).append(line)
        self.counts[phase] = self.counts.get(phase, 0) + 1

    def touched(self):
        return bool(self.replace or self.insert_after)

    def apply(self, lines):
        out = []
        for i, line in enumerate(lines):
            out.append(self.replace.get(i, line))
            out.extend(self.insert_after.get(i, ()))
        return out


def build_plan(entries, xmp, aliases, import_artist):
    """Decide every line edit. Aborts on an unknown licence rather than writing one."""
    plan = Plan()
    unknown = []
    still_empty = []

    for entry in entries:
        fields = entry["fields"]
        src_field = fields.get("src")
        if src_field is None:
            sys.exit(f"ERROR: entry at line {entry['lo'] + 1} has no `src:`.")
        src = unquote(src_field[1])
        from_file = xmp.get(src, {})

        # Phase 1 — rewrite an existing licence display string to its key. This
        # runs on entries the later phases skip, which is the point: 366 of them
        # already have a licence and it is spelled the old way.
        license_field = fields.get("license")
        if license_field and not is_empty(license_field[1]):
            current = unquote(license_field[1])
            key = aliases.get(current.lower())
            if key is None:
                unknown.append((src, current, "data/gallery.yaml"))
            elif key != current:
                plan.set_line(license_field[0], f"  license: {key}", "license-key")

        # Phases 2-5 — fill what is empty or missing, from the file.
        wanted = {}
        for field in FIELDS + (("artist",) if import_artist else ()):
            value = from_file.get(field)
            if not value:
                continue
            existing = fields.get(field)
            if existing is not None and not is_empty(existing[1]):
                continue  # an existing YAML value always wins
            if field == "license":
                key = aliases.get(value.lower())
                if key is None:
                    unknown.append((src, value, "the file"))
                    continue
                value = key
            wanted[field] = value

        # In place where the key exists, appended where it does not. The append
        # block follows the file's own field order so a filled stub ends up
        # shaped like the 626 entries that were never stubs.
        appended = []
        for field in APPEND_ORDER:
            if field not in wanted:
                continue
            value = wanted[field]
            line = f"  {field}: {yaml_scalar(value)}"
            existing = fields.get(field)
            if existing is not None:
                plan.set_line(existing[0], line, field)
            else:
                appended.append((field, line))

        for field, line in appended:
            plan.add_line(entry["hi"], line, field)

        # `description` is a new key everywhere and goes directly after `alt`,
        # which is where main concept §4 puts it relative to the other prose.
        if "description" in wanted:
            line = f"  description: {yaml_scalar(wanted['description'])}"
            existing = fields.get("description")
            if existing is not None:
                plan.set_line(existing[0], line, "description")
            elif "alt" in fields:
                plan.add_line(fields["alt"][0], line, "description")
            else:
                # No alt line at all: it was just appended, so follow it there.
                plan.add_line(entry["hi"], line, "description")

        alt_field = fields.get("alt")
        has_alt = "alt" in wanted or (alt_field is not None and not is_empty(alt_field[1]))
        if not has_alt:
            still_empty.append(src)

    if unknown:
        for src, value, where in unknown:
            print(f"ERROR: {src}: licence {value!r} in {where} is neither a key nor an "
                  "alias in data/licenseMap.yaml", file=sys.stderr)
        sys.exit(
            f"\n{len(unknown)} unknown licence value(s). Add the key to "
            "data/licenseMap.yaml or fix the value — nothing was written."
        )

    return plan, still_empty


# --- main ---------------------------------------------------------------------


def list_disk_images(photos_dir):
    return {
        entry.name
        for entry in os.scandir(photos_dir)
        if entry.is_file() and Path(entry.name).suffix.lower() in IMAGE_EXTS
    }


PHASE_LABELS = {
    "license-key": "licence display strings rewritten to keys",
    "license": "`license` filled from the file",
    "alt": "`alt` filled from the file",
    "title": "`title` filled from the file",
    "description": "`description` added from the file",
    "artist": "`artist` filled from the file",
}


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if not args.data.is_file():
        sys.exit(f"ERROR: data file not found: {args.data}")
    if args.photos is None:
        sys.exit(
            "ERROR: no gallery mount found in config/_default/module.yaml, and no "
            "--photos given\n" + PHOTOS_SETUP_HINT
        )
    if not args.photos.is_dir():
        sys.exit(
            f"ERROR: photos folder not found or not a directory: {args.photos}\n"
            + PHOTOS_SETUP_HINT
        )
    if not gallery_xmp.available():
        sys.exit(
            "ERROR: exiftool not found. It is the only way this reads the files, and "
            "a partial import would be worse than none."
        )

    aliases = license_aliases()
    if not aliases:
        sys.exit("ERROR: could not read any licence keys from data/licenseMap.yaml.")

    raw = args.data.read_text(encoding="utf-8")
    lines = raw.split("\n")
    trailing_newline = raw.endswith("\n")
    if trailing_newline:
        lines = lines[:-1]

    start, end = find_images_block(lines)
    entries = parse_entries(lines, start, end)
    srcs = {unquote(e["fields"]["src"][1]) for e in entries if "src" in e["fields"]}
    disk = list_disk_images(args.photos)

    # Drift means the join key is unreliable, and a file this script cannot see is
    # a field it would silently leave empty. Bring the two in step first.
    missing = sorted(srcs - disk)
    extra = sorted(disk - srcs)
    if missing or extra:
        for name in missing:
            print(f"ERROR: gallery.yaml references a missing file: {name}", file=sys.stderr)
        for name in extra:
            print(f"ERROR: photo with no gallery.yaml entry: {name}", file=sys.stderr)
        sys.exit(
            "\nYAML and photo store are out of step. Run `python3 scripts/sync-gallery.py` "
            "first — nothing was written."
        )

    xmp = gallery_xmp.read(args.photos / name for name in sorted(disk))
    plan, still_empty = build_plan(entries, xmp, aliases, args.artist)

    if not plan.touched():
        print(f"Nothing to import: {len(entries)} entries, every field already set.")
        return 0

    new_lines = plan.apply(lines)

    if args.dry_run:
        diff = difflib.unified_diff(
            lines, new_lines,
            fromfile=f"a/{args.data.name}", tofile=f"b/{args.data.name}",
            lineterm="", n=1,
        )
        print("\n".join(diff))
        print()

    verb = "Would change" if args.dry_run else "Changed"
    print(f"{verb} {len(entries)} entries in {args.data}:")
    for phase in ("license-key",) + FIELDS + ("artist",):
        count = plan.counts.get(phase)
        if count:
            print(f"  {count:4d}  {PHASE_LABELS[phase]}")
    if not args.artist:
        print("        (`artist` not imported — site.Params.author.name covers it; "
              "pass --artist to change that)")

    if not args.dry_run:
        out = "\n".join(new_lines) + ("\n" if trailing_newline else "")
        args.data.write_text(out, encoding="utf-8")

    if still_empty:
        print(f"\n{len(still_empty)} photos have no alt text in the YAML or in the file. "
              "They are the editorial backlog, not a failure of this import:")
        for name in sorted(still_empty):
            print(f"  - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
