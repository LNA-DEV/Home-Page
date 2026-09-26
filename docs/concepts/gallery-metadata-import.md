# Concept: one-time import — moving the editorial metadata out of the files into `gallery.yaml`

**Status:** **DONE — ran 2026-09-18.** `scripts/gallery-import-xmp.py` is kept for the record; a second run prints `Nothing to import` and changes nothing. The fallbacks of §4 are gone, so the build now hard-fails on a photo with no licence. Do not re-run as a fix for anything; see `AGENTS.md`.
**Outcome against §5:** every expected number matched, with one correction — **22** titles moved, not 21 (the "1 already filled" in §5's table was a `projects:` entry, not a photo; no image had a title). 366 licences rewritten, 282 `license`, 281 `alt`, 22 `title`, 7 `description`; `artist` left at 361; 60 photos still have no alt text anywhere. Build green, page counts identical to the pre-import baseline, no new warnings.
**Measured:** 2026-09-18, against `data/gallery.yaml` (648 entries) and the photo store (648 files). The exiftool read in §3 was timed on the real store.
**Read against:** `gallery-metadata-single-source.md`. That document describes the steady state — YAML owns everything editorial, the files own the technical data and the tags. This one is the single migration that takes the existing 648 entries there. It is the **closing step** of that document's §9: everything there is implemented first and works through the fallbacks that exist today; this migration then removes them.

Today 282 photos have their licence, 281 their alt text and 21 their title only inside the exported JPEG, where Darktable put them. The site reads those values through fallbacks at build time, so a Darktable re-export can change what the site says with no diff in git. This copies them into `data/gallery.yaml` once, rewrites the licence labels into keys on the way, and then removes the fallbacks — after which the build reads nothing editorial from a file except tags.

## 0. Preconditions — check these first, in a fresh session

This document is written to be executed from a fresh chat with nothing but the repository in front of it. Before touching anything:

| Check | How | Expected |
|---|---|---|
| The main concept is committed | `git status --short` | Clean tree. On 2026-09-18 the implementation was staged but uncommitted; the import must not be mixed into that commit |
| The build is green | `hugo` | No errors, no new warnings. This is also the baseline the verification in §5 compares against |
| YAML and store are in step | `python3 scripts/sync-gallery.py --dry-run` | `In sync: 648 entries, 648 files.` |
| exiftool is present | `python3 -c 'import sys; sys.path.insert(0,"scripts"); import gallery_xmp; print(gallery_xmp.available())'` | `True` |
| The licence aliases are in place | `grep -c aliases data/licenseMap.yaml` | ≥ 2 — `gallery_common.license_key` maps the two label strings through them |
| The two open decisions are answered | "Still open" below | Defaults if nobody says otherwise: do not import `artist`; write all seven descriptions and review afterwards |

Two modules the implementation left behind do most of the work, and the import script should use them rather than carry its own copies:

- **`scripts/gallery_xmp.py`** — `read(paths)` returns the five editorial fields per file through one exiftool process; its `FIELDS` table already maps `alt → XMP-acdsee:Notes`, `title → XMP-dc:Title`, `license → XMP-dc:Rights` and so on. `available()` says whether exiftool is installed.
- **`scripts/gallery_common.py`** — `license_key(value)` turns a label string into its key via the aliases in `data/licenseMap.yaml` and rejects anything unknown; `photos_dir_from_hugo_mounts()` finds the store the way Hugo does.

`scripts/sync-gallery.py` shows the text-level editing style (§3) and already imports both modules; its stub enrichment is the steady-state twin of this migration.

## Settled decisions

| | |
|---|---|
| Direction | Files → YAML, **once**. Never the other way; never again at build time |
| Scope | `license`, `alt`, `title`, `description`. **Not** tags (Darktable-owned, main concept §3), not technical EXIF, not publisher |
| Fill rule | Only an empty or missing field is written. An existing YAML value always wins, whatever the file says |
| Editing | Text-level, as `sync-gallery.py` does it. Every line that is not part of the change stays byte-identical |
| Source files | Read only. One exiftool process over the store |
| Afterwards | The EXIF fallbacks leave `collect-images.html` and `rss.xml`, the label aliases leave `licenseMap.yaml`. A missing or unknown licence then hard-fails the build — that is the test |

## Decided at run time

Both open questions took the default this document recommended.

| | |
|---|---|
| `artist` | **Not imported.** All 287 file values are `Lukas Nagel` = `site.Params.author.name`, which is now the only fallback. `--artist` is the one-flag switch if uniformity is ever preferred. |
| The six identical captions | **Kept on all six.** The script writes what the files say; whether six photos of one series should share a paragraph is editorial, and the entries are now in git where that is a normal edit. |

---

## 1. What moves

| Source tag in the file | Target in YAML | Written when | entries |
|---|---|---|---:|
| `dc:rights` (= EXIF `Copyright`), mapped to a key | `license` | empty or missing | 282 |
| `XMP-acdsee:Notes` — Darktable's *notes* field | `alt` | empty or missing | 281 |
| `dc:title` | `title` | empty | 21 |
| `dc:description` (= EXIF `ImageDescription`) | `description` — a new key | always; the key does not exist yet | 7 |
| *(already in YAML)* | `license`: label string → key | the two known strings | 366 |

Two label strings exist, in the YAML and in the files alike, and both map to a key of the new `data/licenseMap.yaml` shape (main concept §5):

```
"Creative Commons Attribution-ShareAlike (CC BY-SA)"  →  cc-by-sa-4.0     632 photos
"all rights reserved"                                  →  all-rights-reserved   16 photos
```

Both keys, with the two strings as their `aliases`, already exist in `data/licenseMap.yaml` when this runs (main concept §5, step 1 of its §9); the script reads the mapping from there rather than carrying its own copy. Any other string — in the YAML or coming out of a file — aborts the run. There is no third licence in this library, and a typo should not become a key.

The seven descriptions are two distinct texts: one about the Avesta Visentpark on six photos, one about plastic waste on a seagull photo. Both are 100–150-character captions, which is why they were never alt text (main concept §1) and why they land in `description`, not `alt`. The script writes them and prints them; whether six photos of a series should share one paragraph is an editorial call made after the import, not by it.

## 2. What deliberately does not move

- **Tags.** They stay in Darktable and are read live at build time — the reasoning is main concept §3. Copying them here would create exactly the two-source situation this migration ends for the other fields. *(Superseded 2026-09-26: a second one-time import, `scripts/gallery-import-tags.py`, moved them after all — `gallery-metadata-yaml-only.md` §3.)*
- **`artist`.** All 287 file values, like all 361 YAML values, are `Lukas Nagel`, which is also `site.Params.author.name`. `collect-images.html` already falls back to that, and it is config in git — not a file dependency. Importing 287 identical lines adds nothing but noise, so the recommendation is: import nothing, leave the 361 existing lines exactly as they are, drop only the `Exif.Artist` fallback. The alternative — import them all so every entry is explicit — is a one-line switch in the script if uniformity is preferred.
- **Publisher.** A constant, and inconsistent in the files (`LNA-DEV` / `Lukas Nagel`). Not a per-photo field.
- **Technical EXIF, GPS, serial numbers.** Never in YAML by design.

## 3. Mechanics

### Read — one exiftool process

```
exiftool -j -XMP-acdsee:Notes -XMP-dc:Title -XMP-dc:Description -EXIF:ImageDescription \
            -XMP-dc:Rights -EXIF:Copyright -ext jpg -ext jpeg <store>
```

Measured: **4.5 s** for all 648 files, JSON out, one subprocess. exiftool is already the dependency of the embedding step and of the read side of `sync-gallery.py`'s stub enrichment; reading XMP without it is possible — the packet is plain XML in APP1 — but reinvents namespace handling for a script that runs once.

The reader lives in a small shared module, `scripts/gallery_xmp.py`, because the same five fields are what `sync-gallery.py` pulls out of a *new* file at stub time in the steady state (main concept §6). One reader, two callers.

### Match — by `src`

Entries and files are joined on the bare filename, the same key `sync-gallery.py` and `gallery-meta.html` use. The script refuses to run while `sync-gallery.py --dry-run` reports drift — a `src:` with no file, or a file with no entry — so the two are brought in step first. Every one of the 648 entries currently has its file.

### Write — text-level, in place

The YAML is edited as text, not parsed and re-serialised, for the same reason `sync-gallery.py` does it: a round-trip through a YAML library would re-quote, re-order and re-wrap lines that are not part of the change, and the diff would be unreviewable. Two facts about the file make the text approach safe, both checked:

- **No block scalars.** No `alt: >`, `alt: |` or multi-line value exists anywhere. Every field is one `  key: value` line.
- **The 281 notes are plain.** None contains a newline, a double quote or `: `. The longest is 327 characters.

The script still applies a quoting rule rather than trusting that: a value is double-quoted when it begins with a character YAML treats specially, or contains `: `, ` #`, or a quote. Otherwise it is written bare, matching the 307 existing alt lines.

Three cases per field:

| Current state | Action |
|---|---|
| `alt: ""` (319 entries) | Replace the value on the same line |
| Key missing (22 stub entries: `id`, `src`, `category`, `section` only) | Append the line at the end of the entry block |
| Non-empty | Leave untouched, even if the file disagrees |

`description` is a new key on the seven entries that get one; it goes directly after `alt`, where the shape in main concept §4 puts it.

Phases, in order, in one run: rewrite the 366 licence labels to keys → fill `license` (282) → fill `alt` (281) → fill `title` (21) → write `description` (7). `--dry-run` prints the diff and changes nothing. A second run finds nothing to fill and exits saying so.

### Rules the script enforces on itself

- Never writes to the photo store. It opens files there read-only, through exiftool.
- Never overwrites a non-empty value and never deletes a key.
- Aborts on an unknown licence string, on drift between YAML and store, on any entry whose fields it cannot read as single-line `key: value`.
- Writes the YAML only after the whole plan is built — no partial file on error.

## 4. After the import — closing the fallback

This is the step that makes "YAML is the truth" literally true, and it is a template change, not a data change:

| Template | Remove |
|---|---|
| `collect-images.html` | The `Exif.Copyright` licence fallback, the `Exif.Artist` fallback, and the `image-alt.html` call for alt text |
| `rss.xml` (gallery branch) | The `image-alt.html` fallback beside `$meta.alt` |
| `data/licenseMap.yaml` | The `aliases` of the two keys — from here on only keys are accepted |

`image-alt.html` itself stays: `sitemap.xml` uses it for page-bundle images, which are not gallery photos and not in scope here.

Once the licence fallback and the aliases are gone, an entry without a licence — or one still holding a label string — is a hard build error; `collect-images.html` already `errorf`s in both cases. So the verification of the whole migration is: **the build passes.** If any of the 282 was missed, it fails by name.

From here on, a new photo gets its English first values through `sync-gallery.py`, which reads them out of the new file once, at stub time (main concept §6). The file is never consulted again.

## 5. Verification

Expected state of `data/gallery.yaml` after the run:

| Field | before | after |
|---|---:|---:|
| `license` filled / empty or missing | 366 / 282 | 648 / 0 |
| `license` values that are keys | 0 | 648 |
| `alt` filled / empty or missing | 307 / 341 | 588 / 60 |
| `title` filled | 1 | 22 |
| `description` present | 0 | 7 |
| `artist` filled | 361 | 361 (if §2's recommendation holds) |

Then: a full `hugo` build with the fallbacks of §4 removed passes; the 60 photos without alt text still render (an empty alt is a warning in the shortcode, not an error); `git diff --stat` is roughly a thousand changed or added lines and touches nothing else; a second `--dry-run` reports nothing to do.

The 60 remaining alt-less photos are listed by the script at the end. They are the editorial backlog, not a defect of the import.

## 6. Cost

| | |
|---|---|
| exiftool read | 4.5 s, once |
| Diff | ~1,000 lines: 366 rewritten, ~590 filled or added |
| Review | The seven descriptions, by eye |
| Build after | Unchanged — the fallbacks it removes were cheap; nothing new is computed |

## 7. Files touched

### New

| Path | Purpose |
|---|---|
| `scripts/gallery-import-xmp.py` | The migration: licence keys, then the four fields; `--dry-run` |

### Existing, reused

| Path | Provides |
|---|---|
| `scripts/gallery_xmp.py` | `read()`, `FIELDS`, `available()` — the exiftool reader, shared with `sync-gallery.py` |
| `scripts/gallery_common.py` | `license_key()`, `license_aliases()`, `photos_dir_from_hugo_mounts()` |

### Modified

| Path | Change |
|---|---|
| `data/gallery.yaml` | 366 licence strings → keys; 282 `license`, 281 `alt`, 21 `title` filled; 7 `description` added |
| `data/licenseMap.yaml` | Remove the two label aliases; keys only from here on |
| `layouts/partials/collect-images.html` | Drop the `Exif.Copyright`, `Exif.Artist` and `image-alt.html` fallbacks |
| `layouts/_default/rss.xml` | Drop the `image-alt.html` fallback in the gallery branch |
| `AGENTS.md` | The new script, and a note that it has run and is not to be re-run |

## 8. Deliberately out of scope

- **Translations.** This imports English only. The `{en, de, sv}` maps are main concept §4 and need no data change to exist.
- **Tags.** Owned by Darktable; see main concept §3.
- **The 60 photos with no alt text anywhere.** Editorial backlog; the script lists them.
- **Tidying the 361 explicit `artist:` lines** that the fallback would cover. They are correct; removing them is churn.
