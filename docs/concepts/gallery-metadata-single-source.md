# Concept: `gallery.yaml` as the single source of photo metadata

**Status:** **implemented 2026-09-18**, steps 1–8 of §9. Step 9 — the one-time import — is deliberately not done; it is `gallery-metadata-import.md` and closes the fallbacks this document leaves in place. Every number in §7 and §8 below has been re-measured against the full library and corrected where it was off; see *Measured on the real run* at the end of §7 and the notes in §8.
**Measured:** 2026-09-18, against `data/gallery.yaml` (648 entries), the photo store (648 files, 7.0 GB) and the last `public/` build (3,519 variants + 648 published originals, 7.6 GB). Hugo 0.166.0.
**Read against:** the working tree after the per-photo pages landed (`gallery-photo-pages.md`). The photo-page adapter already anticipates the `{en, de, sv}` nesting proposed here.
**Companion:** `gallery-metadata-import.md` — the one-time migration that brings the existing 648 entries into the state this document describes. This document is the steady state; that one is how to get there.

Editorial metadata — title, alt text, licence, artist — is split today between `data/gallery.yaml` and the XMP that Darktable writes into each export, is English-only in both places, and **none of it survives into the files the site actually serves**. This proposes three coupled changes: `data/gallery.yaml` becomes the only source for everything editorial, per language where it is prose; embedded metadata becomes an *output* derived from it, written into `public/` after each build; and the source originals in the photo store are never modified.

## Settled decisions

| | |
|---|---|
| Source of truth | `data/gallery.yaml` for everything editorial. The source file for everything technical (camera, lens, exposure, date, software) — **and for tags**, see §3 |
| Source originals | **Never written to.** The photo store is Darktable's export target and a Nextcloud folder |
| Published originals | **Stay published**, as today. The published *copy* in `public/` is tagged and stripped like every variant; the file in the store is not |
| Where embedding happens | On the build output — every file under `public/images/gallery/`, the published copy of the original included |
| Languages | `title`, `alt`, `description` as `{en, de, sv}` maps; a bare string means `en`; every read falls back to `en` |
| de/sv photo pages | **Always generated**, with English fallback — the same call the dex made |
| Filenames, slugs, URLs | Stay English and language-neutral. No translated slugs |
| Technical EXIF | Stays in the original, is not imported into YAML, is copied into the outputs from the source with `-tagsFromFile` |
| Tags | **Owned by Darktable**, read live from the file at build time; `tags:` in YAML stays an optional addition |
| Copyright notice | `© <capture year> Lukas Nagel`, year from `DateTimeOriginal`. **Revised on implementation:** where the year is unknown the notice carries **no year** (`© Lukas Nagel`) rather than the build year — see the row below |
| Credit line, licensor | `Lukas Nagel / lna-dev.net`; `https://lna-dev.net/en/licensing/` |
| Publisher | Not a per-photo field. It is a constant, and the files disagree on it (`LNA-DEV` vs `Lukas Nagel`) |
| Tool | exiftool for the embedding step — the one external dependency, already installed |
| Order of work | **This document first, in full; the one-time import last**, closing the fallbacks. The manifest in §7 is what makes that order possible — §9 says how |

## Still open — nothing blocking

| | |
|---|---|
| ~~Embedding time~~ | **Settled: 3m40s per build**, 4,161 files / 7.6 GB, one exiftool process. §8 updated |
| ~~Manifest~~ | **Settled: built as described.** `public/<lang>/gallery-metadata.json`, one record per photo, the resolver stayed in `collect-images.html` |
| The 269 YAML-only tag sets | Whether and when to re-tag those photos in Darktable so `tags:` can leave the YAML. Editorial, any time, no code change |
| ~~The copyright year on 92 photos~~ | **Settled: no year at all.** The original rule was "`DateTimeOriginal`, else the build year", on the premise that only 5 photos lack the tag. **643 carry the tag but 87 of them say `2000:01:01`** — an unset camera clock, which the site already discards everywhere else (its `year > 2000` rule) — so the fallback would have hit 92 files, asserting `© 2026` on photos that are older *and* rewriting them every New Year's Day, which costs the step its byte-for-byte determinism. Those 92 now get `© Lukas Nagel`, which is valid and standard. `COPYRIGHT_SYMBOL` in `gallery-embed-metadata.py` |

---

## 1. Where the metadata lives today

The site already treats the YAML as primary and the embedded metadata as fallback. What the fallback still carries is the problem:

| Field | YAML filled | supplied by the file | nowhere | Note |
|---|---:|---:|---:|---|
| `license` | 366 | 282 | 0 | Embedded as `dc:rights` + EXIF `Copyright` — holding the *licence name*, not a copyright notice |
| `artist` | 361 | 287 | 0 | Always `Lukas Nagel` |
| `alt` | 307 | 281 | **60** | Darktable's *notes* field, exported as `XMP-acdsee:Notes` — that is the `.XMP.Notes` `image-alt.html` reads |
| `title` | 1 | 21 | rest | The 22 `dc:title` values Darktable wrote are **ignored by every template**; the heading is the filename stem |
| `description` | — | 7 | — | `dc:description` / `ImageDescription`: two distinct 100–150-character captions, not alt text |
| `tags` | 307 | 352 | 27 | 269 YAML-only, 314 file-only, 38 in both with partial overlap. The site already shows the union |
| publisher | — | 287 | — | `dc:publisher`, never read |

Three facts shape the rest:

- **Every one of the 311 XMP language alternatives is `x-default`.** XMP could carry `xml:lang="de"` — `dc:title` and `dc:description` are `rdf:Alt` by definition — but Darktable's UI writes only the default, Hugo's reader hands back one value, and the text would live outside git. That is the same argument that made the photo-page slug derive from the filename rather than the alt text (`gallery-photo-pages.md` §3).
- **282 photos build only because Darktable wrote their licence into the file.** `collect-images.html` falls back to `Exif.Copyright`, and those 282 are exactly the entries with an empty `license:`. A re-export with a changed preset would change what the site says about a photo's licence with no diff in git.
- **The 60 with no alt text anywhere** are the real gap. An earlier count in the discussion said 334; that missed the ACDSee namespace and is wrong.

## 2. What the served files carry

Exactly the wrong things.

**Hugo re-encodes every variant and writes no metadata segment at all.** Checked on the largest published variant (`In the tree tops_hu_…JPG`, 3008×4000): zero tags outside `File` and `JFIF`. That covers the 600 px thumbnails, the 4000 px file the lightbox download button serves, the 1600 px RSS render, the 1200 px OpenGraph image, the dex covers and every shortcode ladder — 3,519 files. A visitor who downloads a photo gets a JPEG with no licence, no creator, no title.

**Meanwhile the untouched original is published anyway**, because the microdata `contentUrl` in `gallery.html:87` and `gallery-portfolio.html:51` references `$image.Permalink`, and referencing a resource publishes it. 648 originals, 7.0 GB, carrying:

| In the published originals | files |
|---|---:|
| Camera body serial number | 514 |
| Lens serial number | 467 |
| MakerNotes blob | 497 |
| Embedded EXIF thumbnail (can show the uncropped frame) | 145 |
| GPS coordinates — all DJI drone shots | 13 |
| Darktable rating / colour labels | 594 / 296 |
| Darktable develop history | **0** — the export preset already excludes it |

So the file with the licence in it is the one nobody is meant to download, and the file offered for download has none. Whatever else this concept does, it inverts that. Publishing the originals stays — the decision is that the published copy gets the same treatment as every variant.

## 3. The model — editorial in YAML, technical and tags in the file

One rule, easy to remember: **everything a person writes for the site lives in `data/gallery.yaml`; everything a camera or Darktable records lives in the original.** Tags are the one deliberate exception, explained below.

| Editorial → YAML | From the original |
|---|---|
| `id`, `src`, `slug` | Make, model, lens |
| `title`, `alt`, `description` (per language) | Aperture, shutter, ISO, focal length |
| `license`, `artist` | `DateTimeOriginal` |
| `species`, `category`, `section`, `project`, `portfolio` | `Software` (darktable / GIMP version) |
| `tags` — optional addition only | **`dc:subject` — the tags set in Darktable** |

### Why the technical half is not imported

It was considered — "import everything into `gallery.yaml`" is the alternative with the cleanest slogan. It loses on four counts:

- **These values have a canonical machine source.** A copy in YAML drifts silently the next time a photo is re-exported (the `Software` version changes; a re-export from a different raw changes the exposure) and nobody notices, because nothing compares the two.
- **The build already reads them for free.** `collect-images.html` pulls EXIF from the untouched source at build time. Importing gains the *site* nothing.
- **Size and tooling.** ~10 fields × 648 photos is roughly 6,500 lines in a file that is already 20,000, plus a sync script in the style of `sync-steam.py` that has to separate machine-owned from human-owned fields on every run.
- **The outputs do not need it either.** exiftool's `-tagsFromFile <source>` copies a whitelist of technical groups into each variant in the same call that writes the editorial fields (§7). Verified.

What *does* fit the model is an optional **override** for the rare case — `lens:` for an adapted manual lens that leaves EXIF empty — resolved YAML → EXIF, exactly as `alt` and `license` resolve today. An override is editorial; a mirror is not.

### Tags — the one editorial field that stays in the file

Tags are typed by a person, which by the rule above would put them in YAML. They stay in Darktable anyway, for three reasons that do not apply to the title:

- **They are not translated.** The whole point of moving `title` into YAML is that its German and Swedish siblings must live next to it. Tags have no siblings.
- **Darktable is the right tool for them.** Tags are applied to a selection of thirty photos at once, with autocomplete against the existing vocabulary. Editing 648 YAML lists by hand is the wrong tool for that job.
- **The build already reads them.** 314 photos have tags only in the file today, and a re-export after re-tagging is *meant* to change the site. For tags, the "silent drift" argument runs the other way.

Darktable exports them cleanly: a flat `dc:subject` list, no `lr:hierarchicalSubject`, and none of its internal `darktable|…` tags leak — checked on all 282 Darktable-written files. So the build keeps reading `dc:subject` live, `collect-images.html` keeps forming the union with `tags:` in YAML, and the embedded output (§7) carries that same resolved list. The clean end state is to re-tag the 269 YAML-only photos in Darktable and drop `tags:` from the YAML altogether; that is click-work in Darktable, not a script, and it changes no code, so it can happen whenever.

Two housekeeping items ride along:

- **The junk is not Darktable's.** `zsl_sdr` sits on 59 files that carry no `Software` tag at all — a different export chain. The two path-like tags (`100_PANA\P1000899.MP4`) were written by the Panasonic body itself. `ToBeUploaded` is a workflow tag. Darktable already has the fix for the last one: a tag marked **private** is never exported. The other two get a short blacklist in one place — `data/galleryTagIgnore.yaml`, on the pattern of `data/gamingIgnore.yaml`, read by `collect-images.html` — so neither the site nor the served files show them: the embedding step never sees raw tags, only the list the site already filtered (§7).
- **Language is a convention, not code.** Tags appear on the photo page, as RSS categories and in the schema keywords. A few are German (`Eidechse`, `Eidechsenkampf`); place names (`öland`, `malmö`) are proper nouns and fine as they are. The convention: tags in English, place names in their local spelling.

## 4. Data shape — per-language maps

```yaml
- id: 0f23e431-9466-433a-aaf1-8437688254e8
  src: Alpaca Portrait.JPG
  title:
    en: Alpaca portrait
    de: Alpaka-Porträt
    sv: Alpackaporträtt
  alt:
    en: Close-up portrait of an alpaca with a natural backdrop.
    de: Nahaufnahme eines Alpakas vor natürlichem Hintergrund.
  description:                     # optional — longer prose for the photo page
    en: …
  license: cc-by-sa-4.0            # a key into data/licenseMap.yaml, see §5
  artist: Lukas Nagel              # optional; falls back to site.Params.author.name
```

**A bare string stays valid and means `en`.** `gallery-meta.html` normalises each of the three fields to a map, exactly as it already normalises `project:` into `.projects`. None of the 648 existing entries has to change; a translation is added by unfolding the string into a map. The resolver is `dex-text.html`, which already does field-by-language with an English fallback and is generic enough to reuse as-is.

Resolution happens in `collect-images.html`, which turns `.Title` / `.Alt` / `.Description` into per-language values. That partial is not cached; `gallery-collected.html`, which is, is **already keyed on `site.Language.Lang`** because `artist` resolves through `site.Params`. Nothing structural changes.

### Alt and description are different things

`alt` is what a screen reader and an image crawler get: a short account of what is visible. `description` is the story — where it was taken, why it matters. Today `alt` does both jobs, which is why the seven Darktable captions are 100–150 characters long. After this:

```
alt         → <img alt>, ImageObject.description in microdata (short)
description → the photo page's body prose, meta description, dc:description in the file
              falls back to alt when absent
```

### Consumers that must go through the resolver

Every place that reads `alt`, `title` or the filename as a title today:

| Template | Reads today |
|---|---|
| `gallery.html`, `gallery-portfolio.html` | `.Title`, `.Alt` — fine once `collect-images.html` resolves per language |
| `gallery-photo.html`, `gallery-photo-pages.html` | `.DisplayTitle`, `.Alt` — same; `description` becomes the body, alt stays on the `<img>` |
| `gallery-image-figure.html` | `.Alt`, `.Title` — the shortcodes' `alt="…"` override stays as the per-post escape hatch |
| `rss.xml` (gallery branch) | **`$meta.alt` directly**, and `path.Base .Name` as `<title>` — must switch to resolved values |
| `feed/list.html:128` | **`path.Base $image.Name` as the title** — should use the resolved title |
| `sitemap.xml` | `.Alt` as `<image:title>` — harmless either way; Google has ignored `<image:title>` since 2022 |
| `schema_json.html` (`gallery-photo` branch) | `.Alt` as `description` — becomes `description` with alt fallback |
| `dex-detail.html`, `dex-card.html` | `.Alt` — fine |

### German and Swedish photo pages

`gallery-photo-pages.html` already sets `translationKey: photo-<uuid>`. Adding `content/gallery/photo/_content.de.gotmpl` and `_content.sv.gotmpl` makes Hugo link the three as translations; `head.html` and `sitemap.xml` then emit `hreflang` on their own. The slug is language-neutral, so no URL moves.

Decided: **all three are generated always, with English fallback** — the dex does exactly this, and its 4 species without Swedish prose fall back to English text *and* the English credit. The alternative, generating a German page only once a German title exists, would send a `/de/` visitor to `/en/` for most photos. Google treats an `hreflang` cluster as alternates, not duplicates; a German page with English prose simply does not rank in German until the prose arrives.

## 5. Licence as a key, not a label

Today the YAML value *is* the English display string, and `data/licenseMap.yaml` maps that string to a URL. Once labels need translating the string cannot be the key.

```yaml
# data/licenseMap.yaml
cc-by-sa-4.0:
  aliases: ["Creative Commons Attribution-ShareAlike (CC BY-SA)"]   # until the import has run
  url: https://creativecommons.org/licenses/by-sa/4.0/
  url_by_lang:                      # optional — CC publishes translated deeds
    de: https://creativecommons.org/licenses/by-sa/4.0/deed.de
    sv: https://creativecommons.org/licenses/by-sa/4.0/deed.sv
  label: Creative Commons Attribution-ShareAlike 4.0
  terms: Licensed under CC BY-SA 4.0 — https://creativecommons.org/licenses/by-sa/4.0/
all-rights-reserved:
  aliases: ["all rights reserved"]
  url: /licensing/                  # language-relative, see below
  label:
    en: All rights reserved
    de: Alle Rechte vorbehalten
    sv: Alla rättigheter förbehållna
```

CC licence names conventionally stay English in German and Swedish text, so `label` may be a string or a map, resolved the same way as §4. `terms` is the human-readable sentence that goes into `xmpRights:UsageTerms` (§7).

Two things ride along:

- **A live bug.** `all rights reserved` currently maps to `/en/licensing/`, hard-coded, so the licence link on German and Swedish pages points into the wrong language. A language-relative `/licensing/` resolved with `relLangURL` fixes it.
- **The 366 existing strings stay valid until the import.** Each key carries the label string it replaces under `aliases`, so a YAML value — or an `Exif.Copyright` fallback — that still holds the old string resolves to the key. That is what lets this document be implemented before the one-time migration in `gallery-metadata-import.md`: the migration rewrites the 366 strings, removes the aliases, and from then on only keys are accepted.

## 6. The closing step — the one-time import, and the steady state after it

For "YAML is the truth" to be literally true, the 282 licences, the 281 alt texts in Darktable's notes field and the 21 orphaned XMP titles have to move into the YAML once, and the EXIF fallbacks in `collect-images.html` have to go. That migration — what moves, what deliberately does not, how the file is edited without disturbing a byte that is not part of the change, and how the result is verified — is its own document: **`gallery-metadata-import.md`**. It is the **last** step of §9, not the first: everything in this document works with the fallbacks still in place, because every value the embedding step writes is resolved by Hugo (§7), and Hugo resolves through those fallbacks today. The import only narrows where Hugo looks.

What remains here is the steady state after it:

- **The build reads nothing editorial from the file except tags** (§3). Licence, artist, alt, title and description come from YAML alone; a Darktable re-export cannot change what the site says about a photo.
- **Darktable stays the place where the English first value is typed.** `scripts/sync-gallery.py` creates a stub for each new file today; it gains the ability to pull `dc:title`, `XMP-acdsee:Notes`, `dc:description`, `dc:rights` and `dc:creator` out of the new file at stub time (calling exiftool when present, leaving the field empty otherwise). The file is read once, at import — never again at build time. The reader is the same code the one-time import uses, so it lives in a small shared module rather than twice.

## 7. Embedding — a post-build pass over `public/`

Hugo cannot write image metadata. The step therefore runs **after** `hugo`, on the output, and is invoked from `deploy.sh` after each of its two builds:

```
hugo  →  scripts/gallery-embed-metadata.py public/  →  rsync
```

### The build emits a manifest

The step needs, for every photo, the *resolved* values — the title in each language with its fallback, alt and description, the licence's label, URL and terms, the artist, the filtered tag list, the capture date. All of that resolution already exists, once, in `collect-images.html`. Re-implementing it in Python — the string-or-map fallbacks, the licence map with its aliases, the tag union and blacklist — would be a second resolver that has to be kept in step with the first, and the scripts here are stdlib-only, so it would start with a YAML reader.

So Hugo writes it down. A custom output format on the home page, exactly the mechanism `security.txt` uses, renders `layouts/_default/home.gallerymeta.json` from `gallery-collected.html` into one JSON file per language:

```
public/en/gallery-metadata.json    public/de/gallery-metadata.json    public/sv/gallery-metadata.json
```

Per language rather than one file with all three, because `collect-images.html` resolves against `site`, which is the site being rendered — a template on the English home cannot ask for German values without threading a language parameter through the resolver. Three files and a merge on `id` in the script is the smaller change. Each record carries `id`, `src`, `slug`, `section`, `dateTaken`, `artist`, `license {key, label, url, terms}`, `title`, `alt`, `description`, `tags`. The files are public, like the HTML that already shows every one of those values, and they sit outside `public/images/gallery/`, so the glob below never sees them. Unlike `security.txt` this format goes into the top-level `outputs.home`, because here every language *should* write its own copy.

### Mechanics

1. Read the three manifests, merge on `id`, index by `src`.
2. Glob `public/images/gallery/*`. Map each file to its record by filename: for a variant, the stem before `_hu_<hash>`; for a published original, the name itself — both against `src`. **A file that maps to no record aborts the deploy**; nothing goes online untagged.
3. Build one exiftool argument file for the whole run and execute it in a single process (`-@ args`). Per file:
   - **Editorial fields from the manifest** — the table below, with `xml:lang` alternatives for every language whose value differs from the English one.
   - **Technical fields from the source original** — `-tagsFromFile <store>/<src>` with an explicit whitelist: `Make`, `Model`, `LensModel`, `FNumber`, `ExposureTime`, `ISO`, `FocalLength`, `FocalLengthIn35mmFormat`, `DateTimeOriginal`, `OffsetTimeOriginal`, `Software`. **Never `Orientation`** — Hugo's `AutoOrient` bakes the rotation into the pixels of every variant, and copying the tag would rotate them a second time in any viewer that honours it. The published original keeps whatever it has, since its pixels are untouched.
   - **Tags** — the manifest's list, which is the union the site shows with the blacklist of §3 already applied. Written fresh rather than copied, so the junk never reaches the output.
   - **The blacklist**, each as both its EXIF and its XMP spelling: `SerialNumber`, `LensSerialNumber`, `InternalSerialNumber`, `MakerNotes:all`, `GPS:all`, `IFD1:all` (the embedded thumbnail), `Rating` (EXIF *and* `XMP-xmp`), `XMP-darktable:all`, `XMP-acdsee:all` (the alt text goes out as `dc:description` anyway; the ACDSee copy is a duplicate in a namespace nothing reads), `IPTC:Keywords` (replaced by the resolved list). The dry run caught the first mistake here: stripping only `XMP-xmp:Rating` left `IFD0:Rating` standing.
   - The ICC profile is not touched. Colour depends on it.
4. `-overwrite_original` writes a temp file and renames it into place, so an interrupted run never leaves a truncated JPEG in `public/`.
5. A `--check` mode reads back every file and asserts that `DigitalImageGUID` equals the record's `id`. `deploy.sh` runs it before rsync.

### What gets written

| Purpose | Tag | Value |
|---|---|---|
| Creator | `dc:creator`, EXIF `Artist`, IPTC `By-line` | resolved artist |
| Copyright notice | `dc:rights`, EXIF `Copyright`, IPTC `CopyrightNotice` | `© <capture year> Lukas Nagel` — the *notice*, no longer the licence name; year from EXIF `DateTimeOriginal` (`> 2000`), then the manifest's `dateTaken`, then **omitted** (`© Lukas Nagel`) |
| Licence, human-readable | `xmpRights:UsageTerms` | `terms` from licenseMap |
| Licence, URL | `xmpRights:WebStatement`, `cc:license` | `url` from licenseMap |
| Where to license | `plus:LicensorURL` | `https://lna-dev.net/en/licensing/` |
| Marked | `xmpRights:Marked` | `True` |
| Credit line | `photoshop:Credit`, IPTC `Credit` | `Lukas Nagel / lna-dev.net` |
| Creator website | `Iptc4xmpCore:CreatorWorkURL` | `https://lna-dev.net` |
| Identifier | `Iptc4xmpExt:DigitalImageGUID`, `dc:identifier` | the UUID; the `/en/gallery/photo/<uuid>/` permalink |
| Title | `dc:title` (+ `-de`, `-sv`), IPTC `ObjectName` | resolved per language |
| Description | `dc:description` (+ `-de`, `-sv`), IPTC `Caption-Abstract` | `description`, else `alt` |
| Keywords | `dc:subject`, IPTC `Keywords` | the resolved tag list (§3) |
| Source type | `Iptc4xmpExt:DigitalSourceType` | `…/digitalCapture` |

`WebStatement` + `LicensorURL` are the two IPTC fields Google reads for the *Licensable* badge in image search — the page's structured data already qualifies, and the file then qualifies on its own once it is copied elsewhere. The IPTC-IIM spellings are written alongside the XMP ones because older software reads only IIM. URLs are always clearnet, in the Tor build too: it serves the same files, and an onion address inside a JPEG is not a useful licensor contact.

### Verified on scratch copies

| | Result |
|---|---|
| 6 variants + one 9 MB original, tag + copy + strip | **0.36 s** in one exiftool process |
| Serials, GPS, MakerNotes, IFD1 thumbnail, `XMP-darktable` | gone |
| ICC profile | intact |
| `dc:title` with `-de` / `-sv` | written as proper `xml:lang` alternatives |
| Second run on the same input | **byte-identical** — `md5` unchanged |

Determinism matters twice: the step is idempotent, and rsync sees identical bytes after every deploy, so the pass adds no transfer.

### Measured on the real run

| | Result |
|---|---|
| 4,161 files / 7.6 GB, one exiftool process | **3m40s** — so ~7m30s per deploy |
| Second run over the same output | **byte-identical**, all 4,161 files (md5 over the whole tree) |
| `--check` | 4,161 of 4,161 carry their photo's UUID |
| Serials, GPS, MakerNotes, IFD1 thumbnail, `Rating`, `XMP-darktable`, `XMP-acdsee` | gone from the published originals |
| ICC profile on a published original | intact (`sRGB IEC61966-2.1`) |

Three things the dry run on six files could not have caught:

- **A variant needs an explicit `ColorSpace`.** Hugo drops the source's ICC profile when it re-encodes (387 of the 648 sources have one, all sRGB variants), and exiftool fills the mandatory `ColorSpace` of the EXIF block it is creating with **Uncalibrated** — which tells a colour-managed viewer the pixels are *not* sRGB. They are. Variants therefore get `-EXIF:ColorSpace=sRGB`; published originals are left alone, since 86 of them legitimately pair `Uncalibrated` with an sRGB profile.
- **Sources with no camera data print a warning per output file.** A handful carry none of the copied tags, and `-tagsFromFile` then says "No writable tags set" once per variant — 20 lines of noise for a file that simply has no EXIF. The read pass that collects the capture years now also reports which sources are worth copying from, and the rest skip the copy block.
- **IPTC-IIM refuses over-long values rather than truncating them.** `ObjectName` is capped at 64 bytes, `Keywords` at 64, `Credit` at 32. The script clips the IIM copy; the XMP spelling next to it carries the full value, so nothing is lost.

The junk tags of §3 are real and slightly wider than listed: `zsl_sdr` (59 files), `aeb_sdr` (4) and the two `100_PANA\…MP4` clip paths. `data/galleryTagIgnore.yaml` takes exact titles plus regexes, and the backslash pattern catches the clip-path family rather than the two instances of it. No `ToBeUploaded` exists in the library today.

### Why `public/` and not the image cache

Tagging `resources/_gen/images/` instead would make the cost one-off — Hugo copies cached renders into `public/` verbatim, so tagged cache files would stay tagged across builds. It is rejected as the default because the cache is an intermediate, it is the one thing in this repo that must not be corrupted (a cold rebuild runs past ten minutes), and "outputs yes, sources no" is a cleaner line than "outputs, and also this one cache". It remains the documented escape hatch if the per-deploy time in §8 turns out to bite.

## 8. Cost

With the originals staying published, the cost line is the left column; the right one is what dropping them would have saved, kept for the record.

| | Originals published (decided) | Without |
|---|---:|---:|
| Files per build | 4,167 | 3,519 |
| Bytes rewritten per build | 7.6 GB | ~0.6 GB |
| Embedding time per build (**measured**) | **3m40s** | not measured |
| Per deploy (`deploy.sh` builds twice) | **~7m30s** | not measured |
| `data/gallery.yaml` growth | none until translations are written | — |
| Rendered pages, de/sv photo pages on | +1,296 | — |
| Image variants | **none** — no new render sizes anywhere in this concept | — |

A fresh build emits 4,161 files rather than the 4,167 counted here — the earlier figure came from a `public/` that had accumulated variants across builds. The cost is per-file overhead for the variants and I/O for the originals, and it is wall-clock in one exiftool process; nothing here is parallelised.

## 9. Build order — this document first, the import last

Two independent chains, and the one-time import as the closing step after both. Nothing in the language chain is needed for the embedding chain or the other way round: the embedding step writes `x-default` only until the maps exist, and the maps render fine without the embedding step.

```
  embedding chain   1. licence keys + aliases ─→ 2. tag blacklist file ─→ 3. manifest ─→ 4. embedding step + deploy.sh
  language chain    5. language maps ─→ 6. description on the photo page ─→ 7. de/sv pages
                                                                              └─→ translations (editorial, open-ended)
  closing step      9. one-time import (gallery-metadata-import.md): rewrite the 366 strings, fill the ~590 fields,
                       remove the fallbacks and the aliases
```

**Why the import can come last.** An earlier draft put it first, because the embedding step writes the licence of all 648 photos and 282 of them have it only in the file. The manifest (§7) dissolves that dependency: the embedding step resolves nothing itself, it writes what Hugo resolved — and Hugo resolves those 282 through the `Exif.Copyright` fallback today, mapped to a key through the aliases of §5. So the served files carry the right licence from step 4 on. What the import changes is only *where Hugo looks*: after it, the fallbacks and the aliases go, and a photo without a licence in YAML fails the build instead of being rescued from the file.

**Why embedding before languages.** Steps 1–4 fix two things that are wrong on the live site today — the download carries no licence, the published originals carry serial numbers — and they are done when they are done. Steps 5–7 change nothing a visitor can see until translations are written, which is open-ended editorial work. Bounded fix before open-ended work; no technical dependency forces it.

Each step leaves the site building, and nothing visible changes until the step says so. **Steps 1–8 are done** (2026-09-18); step 9 is not, and is the whole of `gallery-metadata-import.md`.

1. ✅ **Licence keys and aliases** — new `licenseMap.yaml` shape (§5) with the two label strings as aliases; templates resolve keys and aliases alike; the `/en/licensing/` fix. Visible change: German and Swedish licence links point into their own language. `data/gallery.yaml` is untouched.
2. ✅ **Tag blacklist** — `data/galleryTagIgnore.yaml` with `zsl_sdr`, `aeb_sdr` and a backslash pattern for the clip-path family; `collect-images.html` filters the union through it. **Measured, and not quite what this line predicted:** 63 photos carry one, and all 63 also have `tags:` in the YAML — which the old RSS preferred, so the junk was never in the feed. Without the blacklist it shows up in 204 built files: the 63 per-photo pages × 3 languages (`.Tags` is the union there) plus the two gallery feeds, which step 5 moved onto the union as well. So the blacklist *removes* it from the new photo pages and *prevents* it in the feeds. The grids and `/feed/` never showed it either way — `$keywords` is first-match-wins and those photos' YAML tags won.
3. ✅ **Manifest** — the output format in `hugo.yaml`, `home.gallerymeta.json`, one file per language. Inspect `public/en/gallery-metadata.json` by eye before going on: it is the contract the next step relies on.
4. ✅ **Embedding** — `scripts/gallery-embed-metadata.py`, its `--check` mode, the two calls in `deploy.sh`. Verify on a fresh build: `exiftool` on a served 4000 px variant shows the licence block; on the published original the serials are gone; the lightbox download saves a file that names its licence. Time the run and write the number into §8.
5. ✅ **Language maps** — string-or-map normalisation in `gallery-meta.html`, per-language resolution in `collect-images.html`, the `description` field, and route the consumers in §4 through it. No visible change yet: every value is still `en`. From here the manifests differ per language, and the embedding step starts writing `xml:lang` alternatives without a change of its own.
6. ✅ **Photo page body** — `description` as the prose, `alt` stays on the `<img>`; `schema_json.html` and the adapter follow.
7. ✅ **German and Swedish photo pages** — the two adapter files. Verify `hreflang` on a `/de/gallery/photo/…/` page and that the German grid now links to it rather than to `/en/`.
8. ✅ **Documentation** — `CLAUDE.md` (gallery system, conventions, the deploy step, the manifest), `AGENTS.md` (the scripts).
9. ⬜ **The one-time import** — `gallery-metadata-import.md`, end to end. It removes the fallbacks and the aliases; the build is the test. **Not done.**

### What steps 1–8 turned out to need that this document did not list

- **`layouts/partials/license-index.html`** — a new cached partial resolving `data/licenseMap.yaml` into one flat `{key or alias → {key, label, url, terms}}` lookup for the current language. §5 put the resolution in `collect-images.html`; that partial is not cached at its call sites and runs once per dex species page, so the licence map would have been rebuilt a few hundred times per build.
- **`scripts/gallery_common.py`** — the mount-path reader `sync-gallery.py` already had, plus the variant→`src` name rule and a line-based reader for the licence keys and aliases. Two scripts now need all three.
- **`site.Params.licensingPage` was the *same* bug as the licence URL**, hard-coded `/en/licensing/` and fed to `absURL` in four microdata blocks. It is language-relative now, resolved with `absLangURL`.
- **Three consumers read the raw `$meta` entry rather than a collected item** and would have printed a Go map literal once the prose became maps: the gallery branch of `rss.xml` (which also titled every item with the raw filename and carried a second, unfiltered copy of the keyword ladder), `feed/list.html` (same filename titles, used as the thumbnail alt too) and `image_gallery_items.html` — the home page's photo strip, which read only the file's EXIF and so ignored `alt:` in `data/gallery.yaml` entirely, in all three languages. All three go through `gallery-collected.html` now.
- **`content/gallery/photo/_index.{de,sv}.md`** — the branch bundle needs a file per language, not just the adapter.

## 10. Files touched

The one-time import's files are listed in `gallery-metadata-import.md`.

### New

| Path | Purpose |
|---|---|
| `scripts/gallery-embed-metadata.py` | The post-build pass (§7): read the manifests, map, tag, strip, `--check` |
| `layouts/_default/home.gallerymeta.json` | The manifest template — one JSON record per photo from `gallery-collected.html` |
| `data/galleryTagIgnore.yaml` | Tag blacklist (§3), on the pattern of `data/gamingIgnore.yaml` |
| `scripts/gallery_xmp.py` | Shared reader for the five editorial XMP fields — used by the import and by `sync-gallery.py` |
| `content/gallery/photo/_content.de.gotmpl`, `_content.sv.gotmpl` | The other two languages (§4) |

### Modified

| Path | Change |
|---|---|
| `data/gallery.yaml` | Untouched by this document. The import rewrites licence strings and fills empty fields; maps replace strings only as translations are written |
| `data/licenseMap.yaml` | Key → `{aliases, url, url_by_lang, label, terms}`; the aliases leave with the import |
| `hugo.yaml` | Output format `gallerymeta` (`baseName: gallery-metadata`, `notAlternative: true`) added to the top-level `outputs.home` |
| `layouts/partials/gallery-meta.html` | Normalise `title`, `alt`, `description` to maps beside `.projects` and `.slug` |
| `layouts/partials/collect-images.html` | Resolve the three per language via `dex-text.html`; expose `.Description`; licence keys and aliases; tag blacklist via `data/galleryTagIgnore.yaml`; optional `lens:` override. (The fallback removal is the import's step) |
| `layouts/partials/gallery-photo.html`, `gallery-photo-pages.html` | `description` as body and meta description |
| `layouts/partials/gallery-image-figure.html` | Read resolved values; `alt="…"` override unchanged |
| `layouts/_default/rss.xml` | Gallery branch reads resolved title/alt instead of `$meta.alt` and the filename |
| `layouts/feed/list.html` | Photo item title from the resolved title, not `path.Base` |
| `layouts/partials/templates/schema_json.html` | `description` with alt fallback in the `gallery-photo` branch |
| `layouts/partials/photo-meta.html`, `gallery.html`, `gallery-portfolio.html` | Licence label and URL from the new licenseMap shape |
| `scripts/sync-gallery.py` | Stub enrichment through `gallery_xmp.py` |
| `deploy.sh` | Embedding + `--check` after each build |
| `i18n/{en,de,sv}.yaml` | Nothing new expected; licence labels live in `licenseMap.yaml` |
| `CLAUDE.md`, `AGENTS.md` | Gallery system, conventions, scripts, deploy |

## 11. Deliberately out of scope

- **Writing the translations.** 648 titles and 60 missing alts, times two languages, is editorial work. The fallback makes partial coverage safe; a sensible order is the 27 portfolio photos, then the 172 with a species, then the rest.
- **Re-tagging the 269 YAML-only photos in Darktable.** The clean end state of §3, and pure Darktable work. Until then `tags:` in YAML keeps contributing to the union.
- **Translated slugs.** Rejected, not deferred: `defaultContentLanguageInSubdir` already gives every language its own URL, the URL's language is a very weak ranking signal next to `hreflang`, `<title>`, H1 and alt, and translated slugs would triple the aliases and the collision checks and add redirect upkeep on every rename.
- **Renaming the 427 camera-code files.** Still the highest-value editorial follow-up (`gallery-photo-pages.md` §11); untouched here.
- **C2PA content credentials.** A different mechanism with signing keys and a toolchain of its own. IPTC `DigitalSourceType` is the cheap honest signal until then.
- **Restructuring `deploy.sh`** to build once and rsync twice. It would halve the embedding time but is unrelated to metadata.
- **`hugo server` output.** Dev renders are never tagged. Nothing consumes them.
