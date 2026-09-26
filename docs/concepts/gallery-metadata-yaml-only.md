# Concept: the file carries pixels, `gallery.yaml` carries everything else

**Status:** **implemented 2026-09-26**, all steps of §8, uncommitted and not deployed. The decisions were answered as recommended; decision 2 as **C, the English slug**, with redirects through **nginx**. Where the build departed from this text, *As built* directly below says so; the sections after it are the plan as it was agreed.
**Measured:** 2026-09-26, against `data/gallery.yaml` (650 entries), the photo store (650 files; one exiftool pass, 4.9 s) and the last `.test-site/` build (2026-09-24, 649 photos in `gallery-metadata.json`).
**Read against:** `gallery-metadata-single-source.md` (steady state: editorial in YAML, technical data *and tags* in the file) and `gallery-metadata-import.md` (the one-time import that got there, done 2026-09-18).
**Supersedes:** single-source §3, *Tags: the one editorial field that stays in the file*, and the tags bullet in import §2. Both reversals are argued in §3 below.

Two things about a photo still live outside `data/gallery.yaml`. **Tags** are read live out of the file's `dc:subject` on every build, and 286 photos have tags only there. **The English title** is not read at build time any more, but the workflow still runs through the file. It is typed in darktable, darktable's export pattern turns it into the filename, and `sync-gallery.py` copies it from the XMP into the stub. From there the filename leaks back out: the photo page prints it on all three language versions, so the German page for the newest photo says *Datei: `Time for a Beer - German Man Standing Before a Beer Sign in Gamla Stan.jpg`*.

This proposes one rule and the changes that make it true. **The file supplies pixels and technical EXIF, and nothing else. Everything a person writes lives in `gallery.yaml`. The filename is an opaque pointer: unique and stable, with no meaning.** A darktable export called `DSC_2632.jpg` with an empty title field should produce exactly the same site as one called after its title.

## As built — what differs from the plan below

- **§5 needed no lookup changes.** `resources.Copy` changes a resource's published path but **not its `.Name`**, which keeps returning the store filename (verified on 0.166.0). Every `bySrc` lookup by `path.Base .Name` and every `GetMatch "images/gallery/<src>"` kept working untouched, so the five lookup edits and the `byFile` map §5 lists were not built. The copy lives in `gallery-images.html` alone; appending to an empty `resources.Match` keeps the result a typed `resource.Resources`.
- **nginx needed `map_hash_bucket_size 256`.** With the real map (keys up to 73 bytes) nginx refused the config: `could not build map_hash, you should increase map_hash_bucket_size: 64`. The first spike had used a five-line map and could not see it. On the server this would have failed the reload after the first deploy and stopped the container at its next restart. A static test now holds every key under 200 bytes.
- **nginx also refuses `/<lang>/gallery-metadata.json`.** The manifest is a build artefact for the embedding step, and its `src` field lists the store filenames this concept takes off the site.
- **The map has 920 lines, not ~1,300**: 650 store stems plus the 270 `slugAliases` that differ from their stem ignoring case.
- **The original's Orientation/ColorSpace copy is its own block.** Three sources carry an Orientation but none of `COPY_TAGS`; asking a variant to copy from them printed exiftool's "No writable tags set" once per file. `read_sources` now returns a third set, and only the original asks for those two tags.
- **`deploy.sh` reloads through `docker compose exec`**, per compose project (`homepage` / `homepage`, `homepage-tor` / `nginx`), not `systemctl`: both nginx instances are containers.
- **The golden list gained the 650 originals** (`tests/golden/collect.mjs`), and `urls.spec.ts` accepts a retired image URL when the nginx map sends it to a served file. Before any of this, the suite was red for an unrelated reason: the three URLs of the photo committed just before (`Time for a Beer …`) were missing from the golden list. `npm run golden:update` fixed that first.
- **Measured.** Warm build 13–14 s, down from 15.6 s once the tag work left `collect-images.html`. The switch to slug file names processed **no** image: zero new files in `resources/_gen/images`, after `gallery-cache-link.py` added 5,819 hardlinks. The full verification run (§6) on a complete build in the scratchpad: the embedding pass tagged all 4,179 files in 222 s (as before), `--check` passed on every one of them, and a second pass left every file byte-identical.
- **The image-data check does not use `ImageDataHash`.** exiftool's hash reads the whole image: 140 s for the 650 originals plus their 650 sources, per build, far over the 30 s budget §6 set. Rather than dropping the check to the one-time run, `scan_digest()` hashes the first 256 KiB of the entropy-coded data after the first SOS marker, which exiftool never rewrites. On the full set it gives 650 distinct digests, all equal to their store file's, in **1.4 s**. It still catches two swapped originals (tested). The whole `--check` takes ~25 s per build.

## Settled decisions

| | |
|---|---|
| Tags | One-time import from the files into `tags:` (§3). The build then reads **no** tag from any file. The union logic, the four EXIF reads and `data/galleryTagIgnore.yaml` are removed |
| Import source | Tag set and order come from **Hugo's own manifest** (`gallery-metadata.json`), not from a second resolver in Python. So the import cannot disagree with what the site shows today (§3) |
| Import proof | The three `gallery-metadata.json` files stay **byte-identical** across the import and across the template change. That means the served files are unchanged too, and the deploy re-uploads no image |
| Title | Required on every entry, `slug:` or not. The filename-stem fallbacks in `collect-images.html` and the `DisplayTitle` field are removed. `.Title` is the only title (§4) |
| `sync-gallery.py` | Reads **no prose and no tags** from the file. The stub gets empty `title` / `alt` slots in all three languages and `tags: []`. The build fails, naming the photo, until `title.en` is filled in (§4) |
| Photo page | The *File / Datei / Fil* row goes. The *Identifier* section keeps the UUID permalink (§5) |
| The filename's one remaining job | `src:` joins the entry to its file. It can be anything, and renaming stays a one-line `src:` edit (§5) |
| Existing filenames | Stay as they are. "Irrelevant" means *you may name files anything*, not *you must rename them* |
| `license` / `artist` in the stub | **Still pre-filled from the file** by `sync-gallery.py` (decided 2026-09-26). Neither is prose, neither has a language, both come from a darktable preset, and a wrong `license:` still fails the build because it must be a key. Title, alt, description and tags are **not** read |
| Tag spelling | **The file's spelling is imported** (decided 2026-09-26): 1,504 of the 4,422 tags are camelCase (`bavarianAlps`, `wildlifeOfTheAlps`). Lowercase can be derived, camelCase cannot be recovered. The templates keep lowercasing `.Tags`, so every output stays identical; the import needs exiftool once, for the spelling |
| Image URLs | **Named after the English slug** (decided 2026-09-26, option C of §5): `/images/gallery/<fileSlug>.jpg` and `<fileSlug>_hu_<hash>.jpg`. It is the SEO choice, because a descriptive filename is a (light) Google Images signal and a camera code or a UUID is not. Old image URLs are redirected by **nginx** from a map Hugo emits (§5, *The nginx side*) |
| Served files | **Say exactly what `gallery.yaml` says, and nothing else** (added 2026-09-26, §6). The published originals switch from a strip list to clear-then-write, so no leftover title, tag, caption or camera filename reaches a download. `--check` compares every editorial field and the allowed metadata groups on every file, every deploy. After implementation there is a one-time full run plus a hand-read spot check |

## Open decisions

None. Decision 2 was the last one, and it is now in the table above.

---

## 1. Where the file and the filename still matter today

| What | Where | Effect |
|---|---|---|
| Tags, read live | `collect-images.html`: `.Exif.subject`, `.Exif.Subject`, `.Exif.Keywords`, `.XMP.Subject`, unioned with `tags:` and filtered through `galleryTagIgnore.yaml` | A darktable re-tag changes the site with no diff in git. No test can compare data with output, because the data is not in the repo |
| Popup keywords | Same partial, `$keywords`: **first-match-wins** over those four sources, original spelling | The popup shows a different list than the photo page on photos with more than one source |
| English title → file | darktable's title field → export pattern → filename. `sync-gallery.py` → `gallery_xmp.py` → `title.en` in the stub | The process *expects* the file to carry the English title. A photo without one fails the build after sync, so the workaround is to always type it in darktable |
| Filename on the page | `photo-meta.html:108`, `<dt>{{ i18n "photo_file" }}</dt><dd><code>{{ $photo.Name }}</code></dd>` | Every photo page, all three languages, prints the raw filename. That is the English title for 22 photos, another descriptive English name for 201, and a camera counter for 427 |
| Title fallback onto the filename | `collect-images.html`, `$title` from the stem unless it looks like a camera code, and `DisplayTitle` = title or stem | Dead today: `gallery-meta.html` fails the build on a missing title. It is reachable only through `slug:` without a title, which no entry uses. It is still code that names a photo after its file |
| Served file URLs | `/images/gallery/<src>` (published original) and `/images/gallery/<stem>_hu_<hash>.<ext>` (variants) | The filename is in every `<img src>`, `contentUrl`, `og:image` and RSS `media:content`. The *download* is already named after the localised title (`gallery-download-attrs.html`) |
| Sort ties | `sort $images "Date"` is stable, and input order is `resources.Match` order, which is by filename | The 92 photos without a real capture date (87 carry the placeholder `2000:01:01`, 5 have none) are ordered among themselves by filename |
| Join key | `gallery-meta.html`, `bySrc` | Necessary. The one job the filename keeps (§5) |

Messages meant for a developer keep the filename: `errorf` / `warnf` in `gallery-image-figure.html`, `gallery-download-attrs.html` and `gallery-meta.html`. That is the name you look for in the photo store, so it belongs there.

## 2. The rule

| From the file | From `data/gallery.yaml` |
|---|---|
| Pixels | `id`, `src` (pointer only), `slug`, `slugAliases` |
| Camera, lens, exposure, focal length | `title`, `alt`, `description`, per language |
| `DateTimeOriginal`, `Software` | **`tags`** |
| | `license`, `artist`, `category`, `section`, `project`, `portfolio`, `species`, `model` |

Single-source §3 drew the line between *typed by a person* and *recorded by a machine*, then put tags on the wrong side of it on purpose. This concept removes that exception. The technical half stays in the file for the reasons single-source §3 gives, all still true. It has a canonical machine source, the build reads it for free, and a copy would drift.

## 3. Tags: the one-time import

### Why the earlier decision is reversed

Single-source §3 kept tags in darktable for three reasons. Measured against what actually happened since:

- **"darktable is the right tool: batch tagging with autocomplete."** In practice both tools were used, and they grew two vocabularies. 286 photos are tagged in the file only, 304 in the YAML only, and **3 in both, with disjoint lists**. The file vocabulary has 299 distinct tags, the YAML one 406, and they share 90. The same photo series is `lizard` in one place and `Eidechse` in the other. The planned end state, re-tagging the YAML-only photos in darktable, never happened.
- **"Tags are not translated, so they need no siblings."** True, and beside the point. The reason for one place is not the translations, it is *one place*.
- **"A re-export is meant to change the site."** It is also the **only** remaining way a re-export changes the site with nothing in git. For the same reason, tags are the one editorial field no test can check against its output.

### The numbers

| | entries | tag lines |
|---|---:|---:|
| Tags only in the file → written to YAML | 286 | 4,418 |
| Tags in both (disjoint) → union written | 3 | 4 added |
| Tags only in YAML → **untouched** | 304 | — |
| No tags anywhere → untouched | 57 | — |
| **Changed** | **289** | **4,422** |

Of the 289, 262 go from `tags: []` to a block list and 24 have no `tags:` key yet (stubs). `data/gallery.yaml` grows from 14,371 to about 18,800 lines. The block style (`  - tag`, one per line) matches the 307 lists that already exist. A flow list (`tags: [a, b]`) would keep the file shorter, but mixing the two styles, or reformatting 307 entries to avoid mixing, is the worse diff.

The junk stays out: `zsl_sdr` (97 occurrences), `aeb_sdr` (4) and the two Panasonic clip paths are already filtered from the manifest the import reads.

### Mechanics: Hugo decides *which* tags, the file only decides *how they are spelled*

`scripts/gallery-import-tags.py`, one-time, in the style of `gallery-import-xmp.py`:

1. **Read the manifest.** `gallery-metadata.json` from a fresh build (`.test-site/` by default, `--site` to override) holds `.Tags` per photo: the union after the ignore list, lowercased and in the order the site uses. That makes it the authoritative *set and order*. The import does not re-implement the union in Python. This follows the embedding step's principle: Hugo resolves, scripts only move values.
2. **Refuse a stale manifest.** Its id set must equal the YAML's, and en / de / sv must agree on tags (tags have no language). Today's `.test-site/` would be refused: it has 649 photos, the YAML 650.
3. **Look up the spelling** (settled: tag spelling). One exiftool pass over `XMP-dc:Subject`, `IPTC:Keywords` and `XPKeywords`, matched case-insensitively against the manifest list. Verified 2026-09-26: the lowercase union of those three plus the YAML equals Hugo's `.Tags` set on **649 of 649** photos, and no tag has two spellings anywhere in the store. A manifest tag with no spelling in either the file or the YAML aborts the run.
4. **Write**, text-level, like every gallery script: only entries whose normalised YAML list differs from the manifest. Existing tags keep their line. For the 3 mixed entries the list is written in manifest order, file tags first, so step 5 holds.
5. **Prove it.** Rebuild with the templates unchanged: all three `gallery-metadata.json` are byte-identical to the baseline. A second `--dry-run` says `Nothing to import`.

### The three German file tags

`Green Lizard.JPG` (`Eidechse`), `Lizard Fight.JPG` (`Eidechse`, `Eidechsenkampf`) and `Snail.JPG` (`Schnecke`) duplicate English YAML tags on the same photos. They are **imported like everything else**, so the proof in step 5 stays clean, and deleted by hand afterwards as an ordinary edit.

### After the import: the template change

| File | Change |
|---|---|
| `layouts/partials/gallery-meta.html` | Normalises `tags` **once per language**, the way it already turns `project:` into `.projects`: trimmed, de-duplicated case-insensitively, stored spelling kept, plus a lowercased twin |
| `layouts/partials/collect-images.html` | The four EXIF keyword reads, the `$tagChunks` union, both blacklist loops and the first-match-wins ladder go. `.Tags` = the lowercased list, `.Keywords` = the stored spelling joined with `, `. This is the hot partial (it runs once per dex species page), so moving the work into the cached one is a speed-up, not only a simplification |
| `data/galleryTagIgnore.yaml` | Deleted. It existed to filter what the camera and the export chain write into a file. With no file read, junk can only arrive by typing it |

**Proof, again:** rebuild, and the three manifests are still byte-identical. That covers the photo page tag lists, RSS `<category>`, JSON-LD `keywords`, the similarity scorer and the embedded `dc:subject` in every served file.

**Visible change:** the lightbox popup's keyword list is now the whole stored list in stored spelling. Before, it was the first EXIF source only. That adds tags on the few photos whose sources differed, and on the 3 mixed entries.

### Tagging from now on

Tags are typed in `gallery.yaml`, in the stub's `tags: []` slot or by hand. darktable's tag field becomes as irrelevant as its title field. Batch tagging, the one thing darktable did better, is **not** part of this concept. If it turns out to be missing, the answer is a small stdlib script in the house style (`gallery-tag.py add <tag> --project x`). `yq` is not: it round-trips the whole file and re-quotes lines that are not part of the change, the reason every gallery script edits text.

## 4. Titles and prose: the file is never asked

### `sync-gallery.py`

`build_stub()` stops using the file's `title`, `alt` and `description`. The stub becomes:

```yaml
- id: 7c1e…
  src: DSC_2632.jpg
  category: others
  section: general
  title:
    en: ""
    de: ""
    sv: ""
  alt:
    en: ""
    de: ""
    sv: ""
  tags: []
  license: cc-by-sa-4.0     # still from darktable's rights preset (settled)
  artist: Lukas Nagel
```

An empty `title.en` fails the build with the message `gallery-meta.html` already prints: *entry "DSC_2632.jpg" (id …) has no title in "en" and none in en*. That is the intended gate, and it already fires today for any photo darktable had no title for. What changes is that the stub no longer makes the file a second, English-only place to write the title, and the slot shows all three languages at once, as `alt` already does.

`gallery_xmp.read()` gains a `fields` argument, and `sync-gallery.py` asks only for `license` and `artist`. The module keeps its full field map, so `gallery-import-xmp.py`, kept for the record, still runs.

### The template side

- **Title required everywhere.** `gallery-meta.html` checks for a title even when `slug:` is set. A pinned slug pins the URL. It does not excuse a photo from having a name.
- **Filename fallbacks deleted.** `$title` from the stem, `$stemAll`, `$displayTitle` and the `archive--` trimming all go from `collect-images.html`.
- **`DisplayTitle` merges into `Title`.** Six call sites switch: `rss.xml`, `feed/list.html`, `gallery-photo-pages.html`, and three in `gallery-photo.html`. With every photo titled, the two were already equal. The output does not change, and the comment in `home.gallerymeta.json` explaining the difference goes.

### darktable afterwards

The title field and the export filename pattern stop mattering. Two settings are worth checking once:

- **Filename pattern:** anything that stays unique, e.g. the raw's own name (`$(FILE.NAME)`). Keeping `$(TITLE)` is harmless too, but then the title is typed twice for no reason.
- **On conflict: "create unique filename", never "overwrite".** This matters more with camera counters than with titles. `DSC_0001` comes round again after 9,999 frames and is shared between bodies. With *overwrite*, a new export would silently replace an old photo's pixels under an entry that still describes the old one.

## 5. The filename: what remains

### Removed from the page

`photo-meta.html` drops the *File* row. The i18n key `photo_file` goes from all three files. The *Identifier* section keeps the permalink with the UUID and the copy button.

### The join key stays, as a pointer

Something has to connect an entry to its file. The alternatives lose:

| | |
|---|---|
| Rename every file to `<uuid>.jpg` | The store is darktable's export target and a Nextcloud share. The next re-export writes the old name back next to it |
| Match on an embedded id | Needs writing into the source originals, which the metadata concept rules out for good reason |
| **`src:` as an opaque pointer** | **Chosen.** Nothing visible derives from it. Renaming a file means updating one `src:` line, as today; `sync-gallery.py` reports the orphan and the newcomer |

*Automatic rename detection* was measured and left out. `DateTimeOriginal` + `SubSecTimeOriginal` + `Model` + `SerialNumber` is unique for only 548 of 650 photos. The 87 placeholder dates are the main hole, and a few frames were exported twice. A pairing that is wrong one time in six must not be applied automatically. It could at most *suggest*, and that is not worth building before a real bulk rename comes up.

### Decision 2: the served file URLs

**Where a camera name is visible today**, checked on the photo page for `DSC_2632.jpg` (`/de/gallery/photo/drei-masten-eine-tuerkische-gulet-im-goldenen-licht/`):

| Where | Visible to whom | After this concept |
|---|---|---|
| The *File* row: `Datei: DSC_2632.jpg` as page text, on all 1,944 photo pages (648 × 3) | Everyone | **Gone** (§5) |
| Image addresses: `/images/gallery/DSC_2632.jpg` (the "full size" link and `contentUrl`) and `DSC_2632_hu_<hash>.jpg` (`src`, `srcset`, the download ladder, `og:image`, RSS `media:content`) | Only someone who opens an image in its own tab or copies its address | **The English slug under C**; unchanged under A |
| Old photo page URLs `/gallery/photo/dsc-2632/`: 427 camera-code segments from the filename era, kept as `slugAliases` | Only someone following an old link or an old search result. They redirect to the title URL | Unchanged. They exist to keep old links alive |
| Downloads named `DSC_2632_hu_<hash>.jpg` | Everyone who downloaded before 2026-09-19 | Already fixed by the download dialog: title in the reader's language |

**What Google says** (Search Central, *Google Images SEO best practices*, read 2026-09-26):

- "the filename can give Google very light clues about the subject matter of the image … `my-new-black-kitten.jpg` is better than `IMG00023.JPG`."
- "The most important attribute when it comes to providing more metadata for an image is the alt text."
- "consistently reference the image with the same URL, so that Google can cache and reuse the image."
- "If you localize your images, remember to also translate the filenames."
- The site-move guide adds: include images in the move, and tell "users and Googlebot about their new location" (redirects).

What follows from that:

- **A UUID is as generic as a camera counter.** B would move every image URL and gain nothing in search, so it is out.
- **This concept, left at A, makes image SEO slightly worse.** Today's workaround (the English title as filename) is what gives new photos descriptive image URLs: 223 of the 650 have one, 427 carry a camera code. Export as `DSC_xxxx` from now on and every new photo joins the 427.
- **Alt text outweighs the filename.** The 60 photos with no alt text are a bigger SEO lever than every filename together. That is editorial backlog, outside this concept, and worth doing first.

**A, keep the store names.** No move, no cost. The 427 stay generic and every new photo is generic too.

**B, `<uuid>.<ext>`.** Out, as argued above.

**C, the English slug (recommended).** Every served file is named after the photo's English slug, which the build already computes for the page URL:

```
/images/gallery/three-masts-a-turkish-gulet-in-golden-light.jpg                  original
/images/gallery/three-masts-a-turkish-gulet-in-golden-light_hu_1bae91b599940877.jpg   variants
```

*Why English and not per language.* It is one image on three pages. Per-language copies would put identical pixels at three URLs, where Google picks one anyway and splits the signals between them. They would also triple the files on the server and the embedding time (~11 min per build). Google's "translate the filenames" is about *localised images*. Ours are not localised; the page around them is, and its alt text and title, in three languages, are the stronger signals. English is the site's default language and its `x-default`.

*Mechanics, verified in a spike on Hugo 0.166.0 (2026-09-26, scratch site, a real photo from the store):*

- **One choke point.** `gallery-images.html` wraps each source in `resources.Copy "images/gallery/<fileSlug><ext, lowercased>"` before anything processes or publishes it. Every template downstream gets the new names without a change of its own.
- **Nothing is lost.** The copy keeps `.Meta`: EXIF date and camera model read back correctly. Processing works on it, and the original is published only under the new name. No store filename appears anywhere in the output.
- **The hash does not move.** `_hu_<hash>` depends on pixels and processing spec, not on the name or the extension case. `DSC_TEST.jpg` and `Upper.JPG` with the same pixels both came out `_hu_1fb9b00b98b12d13`, before and after the copy.
- **The cache stays warm.** The cache file *is* keyed by name, so a plain rename would be the 10+ minute cold rebuild (verified: a new file appears in `resources/_gen/images`). Because the hash is name-independent, hardlinking each cache entry `<old stem>_hu_<hash>.<ext>` to `<fileSlug>_hu_<hash>.<ext, lowercased>` turns the renamed build into a pure cache hit. Verified: no cache file written or changed. Hardlinks cost no disk space, leave every old entry in place and delete nothing. A one-time script with `--dry-run` does it before the first renamed build.
- **`fileSlug` is language-neutral.** It is `urlize(slug || title.en)` with the English transliteration table, computed in `gallery-meta.html` next to the per-language `.slug`. It has to be: the copy target must be byte-identical in all three language builds, or each writes its own copy. It is unique because the English page slugs are (zero collisions, a build error otherwise).
- **Lookups.** `collect-images.html` and four other partials (`get_images.html`, `get-gallery.html`, `image_gallery_items.html`, `gallery-section-cover.html`) find a photo's entry by `path.Base .Name` in `bySrc`. After the copy, `.Name` is the file slug, so `gallery-meta.html` also returns a `byFile` map. The `.Name` that `collect-images.html` exposes becomes `$meta.src`, so developer messages and the manifest keep naming the store file.
- **Embedding.** `source_name()` in `gallery_common.py` strips `_hu_…` to find the store file. It maps the published stem back through the manifest instead (new field `file`), and `--check` works unchanged.

*Stability.* The file slug moves when the English title is reworded, exactly as the page URL does. Two guards:

1. **The original's URL joins `tests/golden/published-urls.txt`.** A move cannot happen unnoticed. It needs `npm run golden:update`, the rule this repo already applies to page URLs.
2. **A redirect map for nginx**, emitted by Hugo, below. Hugo redirects pages through aliases, but on static hosting it cannot redirect an image, so the web server has to. The map covers the migration (store stem → file slug) and later rewordings (a former slug in `slugAliases` → the current one).

*One-time cost.* All 4,161 served files get new names, so rsync uploads 7.6 GB per target (clearnet and onion) once, and `--delete` removes the old names. The embedding pass takes as long as before. Every image URL moves once, which is exactly the case the redirect map exists for.

### The nginx side

The site is served by nginx (decided 2026-09-26). The map is **data from the repo, rules on the server**: Hugo writes the list, and nginx gets a small one-time config that reads it.

**The map.** A new output format on the English home page, built like `securitytxt` and listed under `languages.en.outputs.home` only, writes `/_nginx/gallery-image-redirects.map`. The file has no `baseURL` in it, so the clearnet and onion builds write the same bytes. One line per old name:

```nginx
"DSC_2632"             three-masts-a-turkish-gulet-in-golden-light;
"Alpaca behind tree"   tree-cover-alpaca-peeking-out-from-behind-a-trunk;
"alpaca-behind-tree"   tree-cover-alpaca-peeking-out-from-behind-a-trunk;   # a slugAlias
```

- **Keys are stems, not URLs.** One line covers the original *and* every variant: the `_hu_<hash>` part is the same before and after (§5, verified), so nginx carries it over unchanged. A list of full URLs would need every variant's hash on the Hugo side and would run to ~4,200 lines instead of ~1,300.
- **Keys are quoted.** 125 store stems contain spaces, one an apostrophe (`It's Always Cozy…`) and two non-ASCII letters. nginx matches against the decoded `$uri`, so the key is the name as it is stored, not `%20`-encoded.
- **Keys match regardless of case.** nginx compares map strings case-insensitively. The store has no two stems that differ only in case (checked). The template still errors if two keys collide, because two photos behind one key would redirect one of them wrongly.
- **A key must never be a live file slug.** If an old store stem happened to equal a current `fileSlug`, nginx would redirect a file that exists. The template refuses that case with an error rather than emitting the line.
- **Size.** ~650 store stems plus the `slugAliases` that differ from the file slug. Entries where the stem already *is* the slug are left out.

**The server config.** The site is served by two `nginx:latest` containers defined in the **Web-Services** repo: `homepage/` (clearnet, behind Nginx Proxy Manager, which terminates TLS) and `homepage-tor/` (onion). Each bind-mounts its own `nginx.conf`, and its site directory at `/usr/share/nginx/html`. The two configs differ only in a comment. There is no existing image `location`, so nothing has to be folded in. The same change goes into both files, `Web-Services/homepage/nginx.conf` and `Web-Services/homepage-tor/nginx.conf`:

```nginx
# http {}, before server {}
    # Gallery image renames (Home-Page docs/concepts/gallery-metadata-yaml-only.md):
    # old store stem or former slug -> current file slug. Hugo writes the list into
    # the site; the glob makes a missing list a no-op instead of a startup error.
    map $gallery_stem $gallery_new_stem {
        default "";
        include /usr/share/nginx/html/_nginx/gallery-image-redirects*.map;
    }
    map $gallery_ext $gallery_ext_lc {
        default $gallery_ext;
        JPG     jpg;
        JPEG    jpeg;
    }

# server {}, before location / {}
        location ~ "^/images/gallery/(?<gallery_stem>[^/]+?)(?<gallery_hu>_hu_[0-9a-f]+)?\.(?<gallery_ext>[A-Za-z]+)$" {
            root /usr/share/nginx/html;
            if ($gallery_new_stem) {
                return 301 /images/gallery/$gallery_new_stem$gallery_hu.$gallery_ext_lc;
            }
        }

        location ^~ /_nginx/ {
            return 404;
        }
```

- **`root` is repeated in the new location**, because the existing config sets it inside `location /` rather than at `server` level, and a regex location does not inherit from a sibling. Moving `root` up one level would be the tidier fix, but it touches every existing request; this touches only the new ones.
- **The `include` is a glob on purpose.** A literal path to a missing file stops nginx from starting. A glob that matches nothing is not an error. So the order of the two deploys cannot take the site down: before the first Home-Page deploy that writes the map, the block simply redirects nothing.
- **Exact lookups, not 650 regexes.** One regex splits the path into stem, hash and extension, and the map is a hash lookup on the stem. The cost per image request does not grow with the number of photos.
- **`301`, relative `Location`.** `301` is the permanent move Google's site-move guide asks for. The `Location` stays relative because the config already has `absolute_redirect off` (TLS ends upstream), the same reason the existing `location = /` redirect works.
- **The extension is lowercased** (`.JPG` → `.jpg`), matching the copy (§5). 309 of the 650 store files end in `.JPG`, and there are only these two extensions.

**Verified 2026-09-26** against the real `homepage/nginx.conf` with this block added, in the production image (`nginx:latest`, local container, site directory mounted read-only):

| Request | Answer |
|---|---|
| `nginx -t` with **no map file** present | `syntax is ok`, `test is successful` |
| `/images/gallery/DSC_2632.jpg` | `301 /images/gallery/three-masts-a-turkish-gulet-in-golden-light.jpg` |
| `/images/gallery/DSC_2632_hu_1bae91b599940877.jpg` (variant) | `301 …/three-masts-a-turkish-gulet-in-golden-light_hu_1bae91b599940877.jpg` (hash carried over) |
| `/images/gallery/Alpaca%20behind%20tree_hu_564ab7caf97be6b0.JPG` (spaces, `.JPG`) | `301 …/tree-cover-alpaca-peeking-out-from-behind-a-trunk_hu_564ab7caf97be6b0.jpg`, and following it answers `200` |
| `/images/gallery/It's%20Always%20Cozy%20in%20the%20Sun.jpg` (apostrophe) | `301 …/its-always-cozy-in-the-sun.jpg` |
| `/images/gallery/%C3%96resundsbron.JPG` (non-ASCII) | `301 …/oresund-bridge.jpg` |
| `/images/gallery/alpaca-behind-tree_hu_….JPG` (a `slugAliases` entry) | `301` to the current slug |
| `/images/gallery/dsc_2632.jpg` (other case) | `301`, since nginx matches map strings ignoring case |
| A current file name | `200`, served directly |
| `/images/gallery/Unknown.jpg` | `404` |
| `/_nginx/gallery-image-redirects.map` | `404` |
| `/` | `301 /en/`, the existing behaviour unchanged |

**Reloading after a Home-Page deploy.** nginx reads the map when it loads its config, so a changed map needs a reload. The site directory is a *directory* bind mount, so the new map is visible inside the container as soon as rsync has written it. `deploy.sh` reloads each container after its rsync, through the compose projects the Web-Services deploy puts in `/home/lnadev/services-v2/`:

```bash
ssh "$REMOTE" 'cd /home/lnadev/services-v2/homepage     && docker compose exec -T homepage sh -c "nginx -t && nginx -s reload"'
ssh "$REMOTE" 'cd /home/lnadev/services-v2/homepage-tor && docker compose exec -T nginx    sh -c "nginx -t && nginx -s reload"'
```

`nginx -t` refuses a broken config before anything reloads, and the reload is graceful. The map changes only at the migration and after a reworded title; on every other deploy the reload is a no-op.

**Applying the `nginx.conf` change itself** needs more than a Web-Services deploy. `nginx.conf` is a *single-file* bind mount. rsync replaces a changed file with a new inode, and a single-file mount keeps pointing at the old one, so a plain reload inside the container can still read the old config. `docker compose up -d` does not recreate the container either, because the compose file did not change. So after deploying Web-Services, recreate both containers once: `docker compose up -d --force-recreate homepage` in `homepage/`, and `… nginx` in `homepage-tor/`. The same probably applies to any earlier `nginx.conf` change: it only took effect once `nginx:latest` pulled a new image and the container was recreated for that reason.

**Deploy order for the migration:** Web-Services first (the block goes live and redirects nothing, since there is no map yet), then Home-Page (renamed files, map, reload). This way old image URLs redirect from the moment they stop existing. The reverse order leaves them at `404` until the nginx change is deployed.

### Sort ties

The 92 undated photos keep filename order among themselves. This is accepted: it is an order, not something displayed, and the proper fix is capture dates on those photos, not a different tie-breaker.

## 6. What the served files carry

The point of all of the above is that a downloaded photo says what `gallery.yaml` says: the title in three languages, the tags, the description, the licence, and nothing left over from darktable or the camera. Most of that is already true and stays true. One part is not, and was not planned until now.

### What stays exactly as it is

The embedding step writes whatever the manifest holds, and the manifest proofs in §3 hold it byte-identical. So title (`dc:title` x-default + `de` + `sv`, `IPTC:ObjectName`), description, tags (`dc:subject`, `IPTC:Keywords`, still lowercased as today), creator, copyright notice, `UsageTerms`, `WebStatement` and the UUID come out the same. Two things are new: the renamed files (C) are mapped back to their photo through the manifest's new `file` field, and the originals get the clean-up below.

### The gap: the published originals keep fields nobody writes

`STRIP_TAGS` is a **denylist**. Whatever the source carries that is not on the list, and not overwritten by the editorial set, goes out with the published original. Measured on all 649 originals of the 2026-09-24 build, after the embedding pass:

| Left in the served original | Files | What it holds |
|---|---:|---|
| `XMP-xmpMM:DerivedFrom` | 338 | The raw file's name (`_DSC3176.NEF`): the camera filename this concept takes off the page, still inside the download |
| `XMP-microsoft:LastKeywordXMP` | 68 | `zsl_sdr` (59), `aeb_sdr` (4), `Eidechse`: tags from the file, junk included, which the site filters everywhere else |
| `XMP-iptcCore:Keywords` | 33 | `ToBeUploaded` (31), `zsl_sdr`: the workflow tag darktable was supposed to keep private |
| `IFD0:XPKeywords`, `XPComment`, `XPTitle`, `XPSubject` | 36 / 36 / 23 / 23 | `zsl_sdr`, an app version, `default` |
| `IFD0:ImageDescription` | 325 | 318 empty, and the 7 old English-only captions. `dc:description` beside them carries the current text in three languages; EXIF keeps the stale English one |
| `XMP-drone-dji:*` | 13 | Flight altitude (`AbsoluteAltitude +552.16`), relative altitude, aircraft and gimbal attitude. GPS itself is stripped; this is the part of the location that is not |
| `XMP-GImage:ImageData`, `XMP-GDepth:DepthImage` | 2 | Phone portrait mode keeps the **unedited frame** and a depth map inside the XMP (`Caterpillar.JPG`, `Green Lizard.JPG`). This is the same class of leak the `IFD1` thumbnail strip exists for |
| `Google:PayloadFrame0…13`, `MergedImage`, `FinishedImage` | 1 | An HDR+ burst's frames appended to the file (`Snail.JPG`) |
| `MPF` + `MPImage2` | 146 | The camera's embedded preview JPEG, ~1 MB each |
| `XMP-crd` / `crs`, `XMP-OPMedia`, `XMP-GCamera`, `XMP-Device`, `PrintIM`, `PanasonicTitle`, `File:Comment`, `UserComment` | up to 215 | Raw-converter settings, phone modes, camera printing hints: noise |

Variants are not affected: Hugo writes no metadata into them, so they carry exactly what the script writes.

### The fix: clear, then write, for originals and variants alike

The originals switch from the denylist to an allowlist, the model the variants already follow:

1. **Clear everything except the ICC profile** (`-all= --ICC_Profile:all`). Colour depends on the profile, which the metadata concept already ruled must stay.
2. **Copy the technical allowlist from the source** (`-tagsFromFile <source>` + `COPY_TAGS`: camera, lens, exposure, date, software), the call the variants already get. **The original additionally keeps `Orientation` and its own `ColorSpace`.** Its pixels are the source's, unrotated, so it needs the tag to display the right way up (22 originals are rotated, e.g. `Fire.JPG`, `Rotate 90 CW`). The variants still never get it, because their rotation is baked in.
3. **Write the editorial set** as today. `EXIF:ImageDescription` joins it with the English description, the same MWG pairing the script already applies to `Artist` and `Copyright`, so the one EXIF caption field older software reads is current rather than stale.

`STRIP_TAGS` becomes redundant for the originals. It stays as a second net, and as documentation of what must never come back.

To verify in the implementation, on scratch copies, before the full run: `-all=` also drops the `MPF` preview and the Google payload trailer (if not, add `-trailer:all=`). The two portrait files lose `GImage` and `GDepth`, which live in extended XMP. A rotated original still displays upright. The ICC profile survives byte-identical. A second run leaves every file byte-identical, so the idempotence the deploy relies on still holds.

### `--check`: from "has a UUID" to "says what the YAML says"

`--check` runs before every rsync and today reads one field, `DigitalImageGUID`. It becomes a full comparison, on every served file, every deploy:

- **Editorial fields match the manifest:** `dc:title` x-default / `de` / `sv`, `IPTC:ObjectName` (clipped), `dc:description` and its languages, `EXIF:ImageDescription`, `IPTC:Caption-Abstract`, `dc:subject` == the tag list, `IPTC:Keywords`, `dc:creator`, `dc:rights`, `UsageTerms`, `WebStatement`, GUID.
- **Nothing else is present:** every metadata group must be on an allowlist (the ones the script writes, plus the technical EXIF subset and the ICC profile). A new camera, phone or export tool that adds a group fails the deploy instead of shipping it. Specific bans on top: `GPS*`, serial numbers, `Orientation` on a variant.
- **The original is the right photo:** the image data of each served original must equal its store file's. This is the check that does not go through the name mapping. It proves that after the renaming (C), every original sits under the photo it belongs to. Variants are right by construction: Hugo names each one after the resource it rendered.

Cost: the read-back is one exiftool pass over metadata, seconds. For the image data see *As built*: exiftool's `ImageDataHash` took 140 s, so a cheaper digest replaced it.

### The one-time verification after implementation

A full build into the scratchpad (never `public/`), the full embedding pass over it, the new `--check` over all 4,161 files, and on top a **spot check read out by hand**, original and 1200 px variant each:

| Photo | Why this one |
|---|---|
| `Time for a Beer - …` | Newest; `all-rights-reserved`; a model; three titles |
| `DSC_2632.jpg` (*Three Masts …*) | Camera-code name → renamed; variants carry the hash over |
| `Alpaca behind tree.JPG` | `.JPG`, spaces, an MPF preview, a `slugAliases` entry |
| `Alpaca Portrait.JPG` | `ToBeUploaded` gone |
| One of the 286 file-tagged photos | Tags now from the YAML, same lowercased list as before |
| `Lizard Fight.JPG` | The German tags deleted by hand; `LastKeywordXMP` gone |
| One Avesta photo | `ImageDescription` now matches `dc:description`; de/sv present |
| `DJI_0862.jpg` | No altitude, no attitude, no GPS |
| `Snail.JPG`, `Green Lizard.JPG` | No burst frames; no unedited frame, no depth map |
| `Fire.JPG` | Rotated original: `Orientation` kept on the original, absent on the variant, both display upright (viewed, not only read) |
| `archive--The Tree.JPG` | Archive photos are embedded like the rest |

The result goes into the final report as a table: per photo and field, expected (YAML) against found (file).

## 7. Tests

| Layer | New or changed |
|---|---|
| `python` | `test_sync_gallery.py`: the stub has empty `title` / `alt` slots in three languages and `tags: []`, and takes **no** title from the file even when the XMP has one. `license` / `artist` are still pre-filled. New `test_gallery_import_tags.py`: stale-manifest refusal, en/de/sv disagreement, spelling lookup, abort on a tag with no spelling, the mixed-entry order, text-level write, idempotence. All without exiftool, on fixtures, using the `parse_records` split `gallery_xmp.py` already makes. `source_name()` maps through the manifest, and the cache-link script's plan (old entry → new name, lowercased extension, nothing overwritten, idempotent) |
| `static` | **Tags, data ↔ output:** every photo page's tag list equals its entry's `tags:`, lowercased and de-duplicated. This was impossible while half the tags lived outside the repo. **No filename on the page:** no photo page's visible text contains its `src`. **no store filename in any published path.** Every file under `images/gallery/` is `<fileSlug>.<ext>` or `<fileSlug>_hu_<hash>.<ext>` for some manifest record, so a template that publishes a raw resource and bypasses the copy fails the test. **The nginx map:** every value is a live file slug, no key is one, keys are unique ignoring case, and every store stem that differs from its slug has a line |
| `python` (embedding) | `test_gallery_embed_metadata.py`: the argument builder clears before it writes; `Orientation` and `ColorSpace` are copied for an original and never for a variant; `EXIF:ImageDescription` is written; the extended check flags a wrong title, a missing tag, a surplus tag, a stray metadata group and a pixel-hash mismatch, on fixture JSON without exiftool |
| `build` | Unchanged. No new warning may appear |

Golden URLs: no page URL moves. The 650 originals' URLs join `published-urls.txt` in the same commit that renames them. The variants stay out, because their hash changes on every re-export by design.

## 8. Build order

0. **Preconditions.** Clean tree (the `Time for a Beer` entry is committed; only this concept is untracked). `npm test` green. `sync-gallery.py --dry-run` says in sync. exiftool present.
1. **Baseline.** Build, and copy the three `.test-site/<lang>/gallery-metadata.json` to the scratchpad.
2. **Import.** Write `gallery-import-tags.py` with its tests. Run `--dry-run`, review, write. Expect 289 entries and 4,422 tag lines.
3. **Proof 1.** Rebuild with the templates untouched: manifests byte-identical. *Natural commit boundary.*
4. **Template change** (§3): `gallery-meta.html`, `collect-images.html`, delete `galleryTagIgnore.yaml`. **Proof 2:** manifests byte-identical again. *Commit boundary.*
5. **The three German tags** deleted by hand, after proof 2 and before anything reads the manifest again.
6. **Titles** (§4): title required despite `slug:`, the stem fallbacks and `DisplayTitle` go, the six call sites switch, the `photo_file` row and key go.
7. **`sync-gallery.py`** stub shape, `gallery_xmp.read(fields=…)`, tests.
8. **Image names** (§5), in this order: `fileSlug` and `byFile` in `gallery-meta.html`, then the five lookups. Next the cache-link script: `--dry-run`, review, run. It only adds hardlinks. Then the copy in `gallery-images.html`, `source_name()` via the manifest, the nginx map output format, the `deploy.sh` reload lines, and the block in both `Web-Services/homepage*/nginx.conf` (edited, not committed or deployed). **Proof:** the rebuild processes no image (no new file in `resources/_gen/images`, wall time of a warm build). The manifests differ only by the new `file` field. `published-urls.txt` gains the 650 originals. The embedding step's `--dry-run` maps every published file. A local `nginx:latest` container with the edited config, serving `.test-site/`, answers the real map for a sample of photos with a `301` to a URL that answers `200`.
9. **Embedding** (§6): clear-then-write for originals, `ImageDescription`, the extended `--check`, after verifying the open points on scratch copies. Then the **one-time verification**: full build into the scratchpad, full embedding pass, `--check` over all 4,161 files, and the spot-check table.
10. **Static tests** (§7).
11. **Docs.** `CLAUDE.md`: the `tags` bullet in *Gallery system*, the `collect-images.html` bullet, the `gallery-images.html` note on `.Name` (with C it is the file slug, no longer the store filename), the sync-gallery convention, the title note in *Photo page URLs*, and *Embedded metadata* (what is written, the allowlist instead of the strip list, what `--check` verifies). `AGENTS.md`: the sync-gallery section, plus the new import script as "done, do not re-run". Supersede notes at single-source §3 and import §2.
12. `npm test` green. No deploy: that stays a separate, explicit step. The first deploy after this is the 7.6 GB-per-target upload. **Deploy Web-Services first**, with the two containers recreated (§5, *The nginx side*), then Home-Page. Both deploys are yours.

## 9. Cost

| | |
|---|---|
| exiftool read | 5 s, once |
| Diff | ≈4,450 added and 262 changed lines, all inside `tags:` blocks. Templates: net removal |
| Build | Expected faster: the per-photo tag work leaves the uncached partial. Measure in step 4 |
| Deploy | Tags and titles: embedded files unchanged (manifest identical), so rsync ships HTML only. The photo pages change (the *File* row) and so do the grids (popup keywords) |
| Deploy, image names | Once: all 4,161 served files under new names, **7.6 GB per target** (clearnet and onion), old names deleted by `rsync --delete`. After that: back to shipping what changed |
| Embedding | Same order as today (~3m40s per build), since the files are rewritten either way. The originals shrink by the MPF previews and phone payloads. `--check` grows by the metadata read-back (seconds) and possibly the pixel hash (§6)|
| Image cache | **No reprocessing.** The hardlink pass takes seconds and adds no disk usage (verified in the spike) |

## 10. Files touched

| Path | Change |
|---|---|
| `scripts/gallery-import-tags.py` | **New.** The one-time import |
| `tests/py/test_gallery_import_tags.py` | **New** |
| `data/gallery.yaml` | +4,422 tag lines on 289 entries, then −4 German tag lines on 3 entries |
| `data/galleryTagIgnore.yaml` | **Deleted** |
| `layouts/partials/gallery-meta.html` | Normalises `tags`. Title required even with `slug:` |
| `layouts/partials/collect-images.html` | No EXIF tag reads, no ignore filter, no filename fallbacks, no `DisplayTitle` |
| `layouts/partials/photo-meta.html` | *File* row removed |
| `layouts/partials/gallery-photo.html`, `gallery-photo-pages.html`, `layouts/feed/list.html`, `layouts/_default/rss.xml` | `.DisplayTitle` → `.Title` |
| `layouts/_default/home.gallerymeta.json` | Comment only |
| `i18n/{en,de,sv}.yaml` | `photo_file` removed |
| `scripts/sync-gallery.py`, `scripts/gallery_xmp.py` | Stub shape. `fields` argument |
| `tests/py/test_sync_gallery.py`, `tests/py/test_gallery_xmp.py`, `tests/static/*.spec.ts` | §7 |
| `layouts/partials/gallery-images.html` | `resources.Copy` to `images/gallery/<fileSlug><ext>` |
| `gallery-meta.html`, `collect-images.html`, `get_images.html`, `get-gallery.html`, `image_gallery_items.html`, `gallery-section-cover.html` | `fileSlug`, `byFile`, and lookups by file slug |
| `hugo.yaml` + new `layouts/_default/home.nginxmap.map` | The nginx map output format (English home only, like `securitytxt`) |
| `deploy.sh` | `nginx -t && nginx -s reload` in each container after its rsync |
| `../Web-Services/homepage/nginx.conf`, `../Web-Services/homepage-tor/nginx.conf` | The map and the `location` (§5), in the other repo |
| `scripts/gallery-cache-link.py` | **New.** The one-time hardlink pass over `resources/_gen/images` |
| `scripts/gallery_common.py`, `scripts/gallery-embed-metadata.py`, `layouts/_default/home.gallerymeta.json` | `source_name()` via the manifest; manifest gains `file` |
| `tests/golden/published-urls.txt` | +650 original image URLs |
| `scripts/gallery-embed-metadata.py`, `tests/py/test_gallery_embed_metadata.py` | Clear-then-write for originals, `ImageDescription`, the extended `--check` (§6) |
| `CLAUDE.md`, `AGENTS.md`, the two sibling concepts | §8, the docs step |

## 11. Deliberately out of scope

- **Translating tags.** They stay English by convention; the photo page shows them as they are on all three languages.
- **Tag cleanup.** Now it is an ordinary diff, and it is overdue. `photo` sits on 591 photos and `photography` on 559, which says nothing. `sverige` and `sweden` are both on the same 98. 269 tags are used exactly once. That is an editorial pass, and this concept only makes it possible.
- **Showing the stored spelling everywhere** (`wildlifeOfTheAlps` instead of `wildlifeofthealps` on the photo page and in RSS). It is easy once the camelCase spelling is stored, but it changes the manifest and therefore the embedded keywords in about 2,000 served files. It is a visible change of its own.
- **Renaming files in the photo store** (never needed: with C the served name no longer comes from the store), **UUID file URLs** (rejected, §5), **per-language image filenames** (§5), **automatic rename detection** (§5), **a batch-tagging script** (§3).
- **The 60 photos without alt text.** The strongest image-SEO lever on the site, and editorial work rather than code.
- **Deploying Web-Services** and recreating its two nginx containers. The edit lands in that repo; shipping it is yours.
