"""Shared helpers for the gallery scripts.

Standard library only, like every other script in this folder. What lives here is
the handful of facts more than one gallery script needs to agree on: where the
repo is, where this machine keeps the photo store, and how Hugo names the derived
image variants it writes into public/.
"""

import re
from pathlib import Path

# The Hugo mount target the gallery photos are mounted onto. Kept in sync with
# config/_default/module.yaml by reading that file rather than duplicating the path.
GALLERY_MOUNT_TARGET = "assets/images/gallery"

# Hugo names a processed image "<stem>_hu_<hash><ext>" next to the untouched
# original "<stem><ext>". Stripping the marker therefore maps any file under
# public/images/gallery/ back to its `src:` in data/gallery.yaml -- the published
# original included, which matches with no substitution at all.
VARIANT_RE = re.compile(r"_hu_[0-9a-f]+(\.[^.]+)$")


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


def source_name(published_name):
    """Map a file under public/images/gallery/ back to its `src:` in gallery.yaml."""
    return VARIANT_RE.sub(r"\1", published_name)


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
