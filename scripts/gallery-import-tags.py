#!/usr/bin/env python3
"""One-time migration: move the tags out of the JPEGs into gallery.yaml.

Until this ran, tags were the one editorial field the build still read out of the
photo files: collect-images.html unioned the file's dc:subject with `tags:` in
data/gallery.yaml on every build, so a darktable re-tag changed the site with no
diff in git, and 286 photos had their tags only in the file. This copies them into
the YAML once. collect-images.html then stops reading them
(docs/concepts/gallery-metadata-yaml-only.md §3).

    Hugo's manifest  (WHICH tags, in WHAT order)  ─┐
                                                   ├─>  tags: in data/gallery.yaml
    the file, via exiftool  (how each is SPELLED) ─┘

The set and the order come from `gallery-metadata.json`, the manifest Hugo writes
from collect-images.html — the same list the photo page, the RSS categories, the
schema keywords and the embedded files show today, after the ignore list and the
union. So the import cannot disagree with the site: rebuilding afterwards leaves
all three manifests byte-identical, which is the proof the concept asks for. The
only thing Hugo does not keep is the spelling (`.Tags` is lowercased), and the
file's camelCase (`bavarianAlps`) is worth keeping, so exiftool is asked for it.

Rules this script holds itself to:

  * The photo store is opened read-only, through exiftool.
  * Only entries whose tag list differs from the manifest (compared ignoring
    case) are touched. A tag already in the YAML keeps its line and its spelling.
  * data/gallery.yaml is edited as TEXT, like every gallery script, so lines that
    are not part of the change stay byte-identical.
  * The manifest must be fresh: its photo ids must be exactly the YAML's, and the
    three languages must agree on every tag list. A stale build aborts the run.
  * The whole plan is built before anything is written.

Standard library only, plus exiftool.
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gallery_common import (  # noqa: E402
    PHOTOS_SETUP_HINT,
    photos_dir_from_hugo_mounts,
    repo_root,
    yaml_scalar,
)
import gallery_xmp  # noqa: E402

LANGUAGES = ("en", "de", "sv")

ENTRY_RE = re.compile(r"^- ([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?$")
FIELD_RE = re.compile(r"^  ([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?$")
ITEM_RE = re.compile(r"^  - (.*)$")
NESTED_RE = re.compile(r"^    \S")

# Where a missing `tags:` key goes: after the first of these that the entry has.
# This is the order the complete entries already use
# (`… section, project, portfolio, tags, alt, title …`).
INSERT_AFTER = ("portfolio", "project", "section", "category", "src")


def parse_args(argv):
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=root / "data" / "gallery.yaml",
                        help="Path to gallery.yaml (default: <repo>/data/gallery.yaml)")
    parser.add_argument("--site", type=Path, default=root / ".test-site",
                        help="A fresh Hugo build holding <lang>/gallery-metadata.json "
                        "(default: <repo>/.test-site, what `npm test` builds)")
    parser.add_argument("--photos", type=Path, default=photos_dir_from_hugo_mounts(root),
                        help="The photo store, read only, for the tags' spelling")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change and write nothing.")
    parser.add_argument("--diff", action="store_true",
                        help="Also print the unified diff.")
    return parser.parse_args(argv)


# --- inputs ------------------------------------------------------------------


def load_manifest_tags(site):
    """{id: [tag, …]} from the three manifests, which must agree with each other."""
    per_lang = {}
    for lang in LANGUAGES:
        path = Path(site) / lang / "gallery-metadata.json"
        if not path.is_file():
            sys.exit(f"ERROR: no manifest at {path} — build first (`npm test`, or the "
                     "`build` project alone).")
        data = json.loads(path.read_text(encoding="utf-8"))
        per_lang[lang] = {p["id"]: list(p.get("tags") or []) for p in data["photos"]}
    base = per_lang[LANGUAGES[0]]
    for lang in LANGUAGES[1:]:
        if per_lang[lang] != base:
            differ = sorted(i for i in base if per_lang[lang].get(i) != base[i])[:5]
            sys.exit(f"ERROR: the {lang} manifest disagrees with the en one on the tags "
                     f"of {differ} — tags have no language, so the build is stale or broken.")
    return base


def find_images_block(lines):
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
        if line and not line[0].isspace() and line[0] not in "-#":
            end = i
            break
    return start, end


def unquote(value):
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        inner = text[1:-1]
        if text[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return text


def parse_flow_list(value):
    """`[a, "b c"]` → ["a", "b c"]; `[]` → []. Only the flat form this file uses."""
    inner = value.strip()[1:-1].strip()
    if not inner:
        return []
    return [unquote(part) for part in inner.split(",") if part.strip()]


def parse_entries(lines, start, end):
    """Each entry as {lo, id, src, fields: {name: index}, tags, tag_lines, tag_key}.

    `tags` is the list as written (None when there is no `tags:` key), `tag_key`
    the index of the `tags:` line, `tag_lines` the indices of its block items.
    Nested `    en: …` lines belong to the key above them and are skipped; any line
    that is none of the known shapes aborts, because a text edit on a shape this
    parser does not understand is how a file gets corrupted.
    """
    entries = []
    current = None
    last_key = None
    problems = []
    for i in range(start, end):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = ENTRY_RE.match(line)
        if m:
            current = {"lo": i, "fields": {}, "tags": None, "tag_lines": [], "tag_key": None}
            entries.append(current)
            name, value = m.group(1), m.group(2)
        elif current is None:
            problems.append((i, line))
            continue
        else:
            item = ITEM_RE.match(line)
            if item:
                if last_key == "tags" and current["tags"] is not None:
                    current["tags"].append(unquote(item.group(1)))
                    current["tag_lines"].append(i)
                continue  # a block list item of some other key (slugAliases, project)
            if NESTED_RE.match(line):
                continue  # the {en, de, sv} of a prose field
            f = FIELD_RE.match(line)
            if not f:
                problems.append((i, line))
                continue
            name, value = f.group(1), f.group(2)
        if name in current["fields"]:
            problems.append((i, line))
            continue
        current["fields"][name] = i
        last_key = name
        if name == "id":
            current["id"] = unquote(value)
        elif name == "src":
            current["src"] = unquote(value)
        elif name == "tags":
            current["tag_key"] = i
            v = (value or "").strip()
            if v.startswith("["):
                current["tags"] = parse_flow_list(v)
                current["flow"] = True
            elif v:
                problems.append((i, line))
            else:
                current["tags"] = []
                current["flow"] = False
    if problems:
        for i, line in problems[:20]:
            print(f"ERROR: {i + 1}: not a shape this script can edit as text: {line!r}",
                  file=sys.stderr)
        sys.exit(f"\n{len(problems)} line(s) not understood. Nothing was written.")
    return entries


# --- the plan ----------------------------------------------------------------


def normalise(tags):
    """Lowercased, trimmed, de-duplicated — the form Hugo's `.Tags` has."""
    out = []
    for t in tags or []:
        t = str(t).strip().lower()
        if t and t not in out:
            out.append(t)
    return out


def spelling_index(*sources):
    """lower → first spelling, over the given tag lists in order."""
    index = {}
    for tags in sources:
        for t in tags or []:
            t = str(t).strip()
            if t and t.lower() not in index:
                index[t.lower()] = t
    return index


def tag_line(tag):
    return f"  - {yaml_scalar(tag)}"


class Plan:
    def __init__(self):
        self.replace = {}       # index -> list of lines (empty list deletes)
        self.insert_after = {}  # index -> list of lines

    def apply(self, lines):
        out = []
        for i, line in enumerate(lines):
            if i in self.replace:
                out.extend(self.replace[i])
            else:
                out.append(line)
            out.extend(self.insert_after.get(i, ()))
        return out

    def touched(self):
        return bool(self.replace or self.insert_after)


def build_plan(entries, manifest, keywords):
    """Every line edit, plus a report. `keywords` is {src: [file tag, …]}."""
    plan = Plan()
    report = {"entries": 0, "tags": 0, "keys_added": 0, "from_empty": 0,
              "rewritten": [], "dropped": [], "missing_spelling": []}

    yaml_ids = {e.get("id") for e in entries}
    manifest_ids = set(manifest)
    if yaml_ids != manifest_ids:
        only_yaml = sorted(i for i in yaml_ids - manifest_ids if i)[:5]
        only_manifest = sorted(manifest_ids - yaml_ids)[:5]
        sys.exit("ERROR: the manifest is not a build of this data file — ids only in the "
                 f"YAML: {only_yaml}, only in the manifest: {only_manifest}. Rebuild first.")

    for entry in entries:
        want = manifest[entry["id"]]
        have = entry["tags"] or []
        if normalise(have) == want:
            continue

        spell = spelling_index(have, keywords.get(entry.get("src"), []))
        new = []
        for t in want:
            s = spell.get(t)
            if s is None:
                report["missing_spelling"].append((entry.get("src"), t))
                s = t
            new.append(s)
        dropped = [t for t in normalise(have) if t not in want]
        if dropped:
            report["dropped"].append((entry.get("src"), dropped))

        lines_new = [tag_line(t) for t in new]
        added = sum(1 for t in want if t not in normalise(have))
        report["entries"] += 1
        report["tags"] += added
        if entry["tag_key"] is None:
            anchor = next(entry["fields"][k] for k in INSERT_AFTER if k in entry["fields"])
            plan.insert_after.setdefault(anchor, []).extend(["  tags:"] + lines_new)
            report["keys_added"] += 1
        else:
            if not have:
                report["from_empty"] += 1
            if have and not entry.get("flow"):
                report["rewritten"].append(entry.get("src"))
            plan.replace[entry["tag_key"]] = ["  tags:"] + lines_new
            for i in entry["tag_lines"]:
                plan.replace[i] = []

    if report["missing_spelling"]:
        for src, t in report["missing_spelling"][:20]:
            print(f"ERROR: {src}: the manifest has the tag {t!r}, but neither the YAML nor "
                  "the file spells it", file=sys.stderr)
        sys.exit("\nThe manifest and the files disagree — is the build stale? "
                 "Nothing was written.")
    return plan, report


# --- main --------------------------------------------------------------------


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if not args.data.is_file():
        sys.exit(f"ERROR: data file not found: {args.data}")
    if args.photos is None or not args.photos.is_dir():
        sys.exit("ERROR: photo store not found (no gallery mount in "
                 "config/_default/module.yaml, and no --photos)\n" + PHOTOS_SETUP_HINT)

    manifest = load_manifest_tags(args.site)

    raw = args.data.read_text(encoding="utf-8")
    lines = raw.split("\n")
    trailing_newline = raw.endswith("\n")
    if trailing_newline:
        lines = lines[:-1]
    start, end = find_images_block(lines)
    entries = parse_entries(lines, start, end)

    # Only the entries that will change need a spelling, and only from their file.
    needing = [e for e in entries if normalise(e["tags"]) != manifest.get(e.get("id"), [])]
    keywords = {}
    if needing:
        if not gallery_xmp.available():
            sys.exit("ERROR: exiftool not found — it is the only source of the tags' "
                     "spelling. Nothing was written.")
        keywords = gallery_xmp.read_keywords(args.photos / e["src"] for e in needing)

    plan, report = build_plan(entries, manifest, keywords)
    if not plan.touched():
        print(f"Nothing to import: all {len(entries)} entries already carry the tags "
              "the build shows.")
        return 0

    new_lines = plan.apply(lines)
    if args.diff:
        print("\n".join(difflib.unified_diff(
            lines, new_lines, fromfile=f"a/{args.data.name}", tofile=f"b/{args.data.name}",
            lineterm="", n=1)))
        print()

    verb = "Would change" if args.dry_run else "Changed"
    print(f"{verb} {report['entries']} of {len(entries)} entries in {args.data}:")
    print(f"  {report['tags']:5d}  tags added")
    print(f"  {report['from_empty']:5d}  entries whose `tags: []` becomes a list")
    print(f"  {report['keys_added']:5d}  entries that get a `tags:` key")
    if report["rewritten"]:
        print(f"\n{len(report['rewritten'])} entries had tags in both places; their list "
              "is rewritten in the order the site shows it (file tags first):")
        for src in report["rewritten"]:
            print(f"  - {src}")
    if report["dropped"]:
        print(f"\n{len(report['dropped'])} entries lose YAML tags the site already hid "
              "(the former data/galleryTagIgnore.yaml):")
        for src, tags in report["dropped"]:
            print(f"  - {src}: {', '.join(tags)}")

    if not args.dry_run:
        out = "\n".join(new_lines) + ("\n" if trailing_newline else "")
        args.data.write_text(out, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
