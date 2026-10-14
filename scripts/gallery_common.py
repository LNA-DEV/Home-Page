"""Shared helpers for the gallery scripts.

Standard library only, like every other script in this folder. What lives here is
the handful of facts more than one gallery script needs to agree on: where the
repo is, where this machine keeps the photo store, and where the build puts the
derived image variants it writes into public/.
"""

import re
from pathlib import Path

# The Hugo mount target the gallery photos are mounted onto. Kept in sync with
# config/_default/module.yaml by reading that file rather than duplicating the path.
GALLERY_MOUNT_TARGET = "assets/images/gallery"

# Where the build puts a gallery photo's files (layouts/partials/image-variant.html,
# docs/concepts/stable-image-urls.md §2):
#
#   images/gallery/<file>          the published original
#   images/gallery/<spec>/<file>   a processed variant, one directory per spec
#
# `<file>` is the photo's published name in both -- the manifest's `file`, the
# English slug (docs/concepts/gallery-metadata-yaml-only.md §5) -- so a served
# file maps to its photo by its name alone, and whether it is a variant is a
# matter of where it sits, never of how it is called. `<spec>` is the Hugo
# processing spec lowercased, whitespace -> "-": fit-600x600, fill-480x480-center.
SPEC_DIR_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Hugo's own cache-key name, "<stem>_hu_<hash>.<ext>". The build no longer
# publishes one; one under images/gallery/ means a template processed an image
# outside image-variant.html.
HUGO_HASH_RE = re.compile(r"_hu_[0-9a-f]+\.[^./]+$")


def repo_root():
    """The repository root, derived from this file's location (<repo>/scripts/)."""
    return Path(__file__).resolve().parent.parent


def photos_dir_from_hugo_mounts(root=None):
    """Return the gallery mount `source` from config/_default/module.yaml, or None.

    Hugo stopped following symlinked mount sources in 0.163.1 (CVE-2026-58403),
    so that file holds an absolute, machine-specific path and is gitignored. It has
    a fixed, tiny shape, so a line-based read keeps this module stdlib-only -- the
    same choice the gallery scripts make for gallery.yaml itself.
    """
    root = root or repo_root()
    config = Path(root) / "config" / "_default" / "module.yaml"
    if not config.is_file():
        return None
    source = None
    for line in config.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # A new list item resets the pending source; `source` always precedes
        # `target` in this file, but a malformed pairing must not leak across items.
        if stripped.startswith("- "):
            source = None
            stripped = stripped[2:].strip()
        if stripped.startswith("source:"):
            source = stripped[len("source:"):].strip().strip("\"'")
        elif stripped.startswith("target:"):
            target = stripped[len("target:"):].strip().strip("\"'")
            if target.strip("/") == GALLERY_MOUNT_TARGET and source:
                return Path(source).expanduser()
    return None


PHOTOS_SETUP_HINT = (
    "       (cp config/_default/module.yaml.example config/_default/module.yaml\n"
    "        and set the gallery mount `source` — see CLAUDE.md \"Build / Deploy\")"
)


def served_gallery_files(gallery):
    """Every file under public/images/gallery/, classified by where it sits.

    Returns (files, problems). `files` is a sorted list of (path, is_variant):
    a file directly in `gallery` is a published original, a file one spec
    directory below it is a variant. `problems` names everything that is
    neither -- deeper nesting, a directory that is not a spec, a Hugo `_hu_`
    name -- each of which the caller must treat as fatal, because a file this
    function cannot place is a file nothing would tag.
    """
    gallery = Path(gallery)
    files, problems = [], []
    for entry in sorted(gallery.iterdir(), key=lambda p: p.name):
        if entry.is_file():
            files.append((entry, False))
        elif entry.is_dir():
            if not SPEC_DIR_RE.match(entry.name):
                problems.append(f"{entry.name}/: not a spec directory")
                continue
            for sub in sorted(entry.iterdir(), key=lambda p: p.name):
                if sub.is_file():
                    files.append((sub, True))
                else:
                    problems.append(f"{entry.name}/{sub.name}: nested deeper than one spec directory")
        else:
            problems.append(f"{entry.name}: neither a file nor a directory")
    for path, _ in files:
        if HUGO_HASH_RE.search(path.name):
            problems.append(f"{path.relative_to(gallery)}: a Hugo `_hu_` name — a template "
                            "processed an image outside image-variant.html")
    files = [(p, v) for p, v in files if not HUGO_HASH_RE.search(p.name)]
    return files, problems


# --- data/licenseMap.yaml ----------------------------------------------------
#
# Read line-wise rather than with a YAML parser, for the same reason gallery.yaml
# is: these scripts are stdlib-only. Only the two things a writer needs are
# extracted -- the keys, and the legacy display strings registered as their
# aliases -- so the file can grow url/label/terms without touching this.

_KEY_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*):\s*$")
_ALIASES_RE = re.compile(r"^  aliases:\s*$")
_ITEM_RE = re.compile(r"^    -\s*(.*?)\s*$")


def license_aliases(root=None):
    """Return {lowercased key or alias: key} from data/licenseMap.yaml."""
    root = root or repo_root()
    path = Path(root) / "data" / "licenseMap.yaml"
    if not path.is_file():
        return {}
    out = {}
    key = None
    in_aliases = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue
        match = _KEY_RE.match(line)
        if match:
            key = match.group(1)
            in_aliases = False
            out[key.lower()] = key
            continue
        if key is None:
            continue
        if _ALIASES_RE.match(line):
            in_aliases = True
            continue
        if in_aliases:
            item = _ITEM_RE.match(line)
            if item:
                out[item.group(1).strip("\"'").lower()] = key
                continue
            in_aliases = False
    return out


def license_key(value, root=None):
    """Map a licence key or legacy display string to its key, or None."""
    if not value:
        return None
    return license_aliases(root).get(str(value).strip().lower())


# --- writing data/gallery.yaml -----------------------------------------------


def yaml_scalar(value):
    """Quote a value only when a bare YAML scalar would not survive the round trip.

    gallery.yaml is written as text by both writers -- sync-gallery.py, which
    appends a stub, and gallery-import-xmp.py, which filled the 648 existing
    entries once -- so the quoting rule lives here rather than in either of them.
    Double quotes with the two escapes YAML needs are enough for editorial prose,
    which is all these write.
    """
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    needs_quotes = (
        not text
        or text[0] in "\"'&*?|->%@`!#[]{},"
        or text[-1] in " \t"
        or ": " in text
        or text.endswith(":")
        # " #" opens a comment mid-scalar and would truncate the value silently.
        or " #" in text
        or text.lower() in ("true", "false", "null", "yes", "no", "on", "off", "~")
    )
    if needs_quotes:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text
