# Gallery images: processing, file names, embedded metadata

## Embedded metadata in the served files

Hugo cannot write image metadata. It re-encodes every variant and emits no metadata segment at all, so for a long time a visitor who downloaded a photo got a JPEG with no licence, no creator and no title — while the untouched original was published alongside it (the microdata `contentUrl` references `$image.Permalink`, and referencing a resource publishes it) carrying camera serial numbers, GPS on the drone shots, darktable ratings and an embedded EXIF thumbnail that can show the uncropped frame. `scripts/gallery-embed-metadata.py` inverts that, as a post-build pass over `public/`:

```
hugo  →  scripts/gallery-embed-metadata.py  →  --check  →  rsync      (deploy.sh does this twice)
```

- **Source originals are never written to.** The photo store is darktable's export target and a Nextcloud folder. Only build output is touched — every file under `public/images/gallery/`, the published copy of the original included.
- **It resolves nothing itself.** Hugo writes the resolved values to `public/<lang>/gallery-metadata.json` (the `gallerymeta` output format in `hugo.yaml` + `layouts/_default/home.gallerymeta.json`, rendered from `gallery-collected.html`); the script merges the three on `id` and writes them out. A Python re-implementation of the string-or-map language fallbacks, the licence map and the tag union would be a second resolver to keep in step with `collect-images.html`. **Unlike `securitytxt`, `gallerymeta` is in the top-level `outputs.home`** — every language must write its own copy — which also means it has to be restated in `languages.en.outputs.home`, since a per-language `outputs` replaces the top-level list rather than extending it.
- **Clear, then write — for every file.** Each served file, variant or published original, is first cleared of all metadata except the ICC profile (`-all= --ICC_Profile:all`), then gets the technical allowlist copied from the source and the editorial set written from the manifest. The originals used to be stripped from a denylist and kept whatever nobody had listed: the raw file's name (`XMP-xmpMM:DerivedFrom`, 338 files), tags from the file including junk (`zsl_sdr`, `ToBeUploaded`), stale English EXIF captions, drone altitude and attitude (13), a phone portrait's **unedited frame and depth map** in extended XMP (2), an HDR+ burst (1) and the camera's MPF preview JPEG (146). Verified on scratch copies: the clear drops all of those, leaves the ICC profile and the pixels byte-identical, and a second run produces the same bytes. `STRIP_TAGS` stays as a second net.
- **The technical half is copied, not stored.** `-tagsFromFile <source>` pulls camera, lens, exposure, date and software straight out of the original in the same exiftool call. **Never `Orientation` on a variant** — `AutoOrient` bakes the rotation into a variant's pixels, so copying the tag would rotate it a second time in any viewer that honours it. The published **original** does get `Orientation` and its own `ColorSpace` back (`ORIGINAL_ONLY_TAGS`): its pixels are the source's, unrotated, and some of them are rotated.
- **Served files are mapped back through `file`.** They are named after the photo's English slug (*Served image names* below), a variant exactly like its original one spec directory down, so the bare name finds the photo through the manifest's `file` field; its `src` names the store file to copy the technical EXIF from. **Whether a file is a variant is decided by where it sits, never by its name** (`served_gallery_files()` in `gallery_common.py`): `images/gallery/<file>` is the original, `images/gallery/<spec>/<file>` a variant. The walk is recursive — a top-level scan would ship every variant untagged — and anything it cannot place (a deeper directory, a directory that is not a spec, a Hugo `_hu_` name) aborts the run before a file is written, like a name no photo has.
- What is written: `dc:creator`/`Artist`/`By-line`, a real copyright **notice** (`© <capture year> <artist>`, not the licence name — and with **no year** on the photos whose capture year is unknown, since the build year would both assert a wrong year and rewrite those files every New Year's Day), `xmpRights:UsageTerms` with `xml:lang` alternatives, `WebStatement` + `plus:LicensorURL` (the two IPTC fields Google reads for the *Licensable* badge), `photoshop:Credit`, `DigitalImageGUID` = the photo's UUID, `dc:title`/`dc:description` per language, `EXIF:ImageDescription` (the English description, the MWG pairing), and the tag list. Every XMP field gets its IPTC-IIM spelling beside it, clipped to the IIM length limits, because older software reads only IIM. URLs are always clearnet, in the Tor build too — an onion address inside a JPEG is not a useful licensor contact.
- **The ICC profile is left alone** — colour depends on it — but a *variant* gets an explicit `ColorSpace=sRGB`, because Hugo drops the profile and exiftool would otherwise fill the mandatory tag of the EXIF block it creates with "Uncalibrated", telling a colour-managed viewer the pixels are not sRGB when they are.
- **`--check` reads every served file back and holds it against the manifest**: every editorial field (title and its translations, description, `ImageDescription`, tags, creator, notice, usage terms, GUID) must match, **no metadata group outside `ALLOWED_GROUPS`** may appear (a new camera, phone or export tool that adds one stops the deploy), `GPS*`/serials are banned by name, a variant may not carry `Orientation`, and **each published original's image data must be its store file's** (a SHA-256 of the first 256 KiB after the first SOS marker, which exiftool never rewrites, about a hundred times faster than exiftool's whole-image `ImageDataHash`) — the one check that does not go through the name mapping. The full check takes well under a minute per build. `deploy.sh` runs it before each rsync. A published file that maps to no manifest record aborts the run before anything is written.
- Cost: a few minutes per build, and **deterministic** — a second run leaves every file byte-identical, so the pass is idempotent and rsync transfers nothing extra for it.
- Tagging `resources/_gen/images/` instead would make the cost one-off, and is the documented escape hatch if the per-deploy time ever bites. It is not the default: the cache is an intermediate, it is the one thing in this repo that must not be corrupted (a cold rebuild runs past ten minutes), and "outputs yes, sources no" is a cleaner line.

Full design, including what is deliberately out of scope: `docs/concepts/gallery-metadata-single-source.md`; the clear-then-write, the extended check and the slug file names: `docs/concepts/gallery-metadata-yaml-only.md` §5–§6.

## Served image names

Every gallery file is published under the photo's **English slug**, not the store filename: the original at `/images/gallery/three-masts-a-turkish-gulet-in-golden-light.jpg`, each variant under the same name one spec directory down, `/images/gallery/fit-600x600/three-masts-….jpg`, where the store file is `DSC_2632.jpg`. Image search reads a descriptive filename as a (light) signal and a camera counter as none, and the store filename is only a pointer. Design: `docs/concepts/gallery-metadata-yaml-only.md` §5; the variant names: `docs/concepts/stable-image-urls.md` and *Processed images* below.

- **`.fileSlug`** is computed in `gallery-meta.html` exactly like the English page slug (`slug:` if pinned, else `title.en`, folded with the English transliteration table), and **`.file`** adds the source's extension lowercased. It is **language-neutral on purpose** — one file on three pages, and the copy target must be byte-identical in all three builds. Two photos with the same file name stop the build.
- **The original is copied once, in `gallery-images.html`** (`resources.Copy`), so no template needs to know; every variant takes the same name from `image-variant.html`. `.Name` keeps returning the store name. Renaming a store file therefore changes nothing a visitor sees; **rewording an English title moves the photo's image URLs**, like its page URL. (`scripts/gallery-cache-link.py`, one-time, **done**, hardlinked the cached variants to the slug names at the switch; it relied on `_hu_<hash>` not depending on the name, which holds — but the hash *does* depend on the Hugo release and the `imaging:` block, which is why no URL carries it any more.)
- **Old image URLs are redirected by nginx, not Hugo** — Hugo redirects pages through aliases but cannot redirect an image. Two maps, both English home only (like `securitytxt`), both under `/_nginx/`:
  - the **stem map**, `nginxmap` → `/_nginx/gallery-image-redirects.map` from `layouts/_default/home.nginxmap.map`: every store stem, and every `slugAliases` entry, → the current file slug. One line covers the original and all its variants, because nginx carries the spec directory over. The template stops the build on a key that is a live slug (it would redirect an existing file, or loop) and on one key claimed by two photos; nginx matches map strings ignoring case, so both checks are case-insensitive. After a reworded English title, adding the old slug to `slugAliases:` keeps the old page **and** the old image URLs alive.
  - the **variant map**, `nginxvariantmap` → `/_nginx/image-variant-redirects.map` from `layouts/_default/home.nginxvariantmap.map`: every old `<dir>/_hu_<hash>` the site published → the variant it was, out of the frozen `data/legacyImageVariants.yaml` (*Processed images*).
- **The nginx side** (in `../Web-Services`): both maps with a **glob** `include` (a missing list is a no-op, not a startup error), `map_hash_bucket_size 256` (the keys are titles; the 64-byte default makes nginx refuse the whole config) and `map_hash_max_size 16384` (the variant map's thousands of keys; at the default 2048 nginx ignores the bucket size). A regex `location` for any `…/<stem>_hu_<hash>.<ext>` comes **first** and `301`s through the variant map — an unknown hash falls through to a 404, never a 301 into one — then the gallery `location` `301`s `/images/gallery/(<spec>/)<old stem>.<ext>` through the stem map. `404` for `/_nginx/` and `/<lang>/gallery-metadata.json` (build artefacts; the manifest names the store's files). Static tests hold both maps' invariants and every key under 200 bytes.
- **The originals and every gallery variant are in `tests/golden/published-urls.txt`**, so a moved image URL needs `npm run golden:update`, and `urls.spec.ts` accepts a retired one only if an nginx map sends it to a served file.

## Processed images: one producer, stable names

Design: `docs/concepts/stable-image-urls.md`. **`layouts/partials/image-variant.html` is the only way a processed image is made, site-wide** — gallery, posts, About, links, book and game covers, game screenshots, dex stand-ins:

```
{{ $v := partial "image-variant.html" (dict "image" $raw "spec" "fit 600x600") }}
{{ $v := partial "image-variant.html" (dict "image" $raw "spec" "resize 720x" "page" .Page) }}
```

- **Why.** Hugo publishes a processed image under its cache key, `<name>_hu_<hash>.<ext>`, and the hash covers the pixels and the spec **and the raw `imaging:` block and Hugo-internal version numbers**. Hugo 0.166.0 (commit `d19e0a4b`) moved every `images.Filter` variant on 2026-09-10, byte-identical files behind them; every older URL went dead, Google Images', the feeds' and the structured data's included. Now a URL changes only when we change something visibly part of it: the name (a reworded English title, a renamed source), or the spec. A Hugo release, an `imaging:` edit, a re-export or a cold cache never moves one.
- **The name.** `<where the source is (or would be) published>/<spec dir>/<source name>.<ext>`: `images/gallery/fit-600x600/<fileSlug>.jpg`, `/en/posts/x/resize-720x/cover.jpg` (a page resource, one per language, needs `page`), `/images/books/covers/fit-200x300/<Title>.jpg`. The spec directory is the spec lowercased, whitespace → `-` (`fill 480x480 Center` → `fill-480x480-center`), every token kept; a spec that does not reduce to `[a-z0-9-]` is an `errorf`. The extension is the output format's (`resize 720x webp q85` → `.webp`), and two sources that would then share a name stop the build.
- **Pass the RAW resource; the partial always runs one chain**, `Filter (AutoOrient, Process spec)`, and publishes only a `resources.Copy` of the result — never the source, so an unreferenced original (a game screenshot) stays unpublished. **One chain is load-bearing**: `resources.Copy` to a taken path silently returns the first resource, so two chains for one name would make the bytes depend on render order. The two-step `(.Filter images.AutoOrient).Process …` is gone with it (it also re-encoded an intermediate JPEG). `tests/static/image-urls.spec.ts` holds the source: no `.Resize/.Fit/.Fill/.Crop/.Process/.Filter`, `images.Process` or `resources.Copy` anywhere else in `layouts/`, with a two-line allowlist (the originals' copy in `gallery-images.html`; the oriented-width read in `image-variants.html`, which renders a cache entry and publishes nothing). It also fails on any `_hu_` file in the build, theme templates included.
- **Oriented size without processing**: `gallery-oriented-size.html` for a gallery photo (the stored pair, swapped by the 4000 variant's orientation); `image-variants.html` reads `.Width` off an `AutoOrient`ed copy.
- **One `contentUrl` per photo**: the `fit-4000x4000` variant on the grids, the photo page (a `<meta itemprop="contentUrl">`, not the hero's 1200px `src`), its JSON-LD, the image sitemap and `galleryImage`. Not the original: many originals exceed the 15 MB crawlers fetch. The originals stay published (the download dialog offers them).
- **Old `_hu_` URLs** go through the variant map (*Served image names*), built from **`data/legacyImageVariants.yaml`, a frozen history**: `scripts/legacy-image-variants.py` ran once on 2026-10-14 over the image cache (everything rendered since 2026-08-19) against the first build with the new names — on Hugo's **raw** output, before the embedding pass rewrote it. An old hash gets a line only on proof: equal bytes to a variant of the same source, or that source's **one** variant of the same pixel size and format (the chain changed, so the bytes did). Nothing else — no "some image of the same source". Gallery lines store `[photo id, spec dir]`, so a later reworded title cannot break them; other lines the new path. Never recomputed; a rerun only adds lines. Of the 1,276 logged requests for a dead gallery hash (2026-10-06…11), 1,099 now resolve in one hop.
- **`scripts/check-live-urls.py`** is the check the tests cannot make, because they never reach the network: a deterministic sample of the shipped `public/` — variants, keys of both maps, the underscore photo URLs, made-up hashes — asked of the live site with `HEAD`, one redirect followed by hand. `deploy.sh` runs it after the clearnet publish; it reports a broken deploy within seconds and keeps the Tor build from going out on top of it.
- **The resource cache.** Every copy is one more entry in Hugo's count-capped resource LRU (~4,000, see *Achievements* in `docs/gaming/overview.md`); the copies took the site from ~1,200 to ~5,500 (2026-10-14). Past the cap an evicted copy is re-created and published a second time — same chain, same bytes — and `--printPathWarnings` reports **`Duplicate target paths`**, **intermittently** (the first build after the switch listed 235 paths, the next none). The owner accepted that in the concept; it is handled by `docs/concepts/duplicate-target-paths.md`, whose classifier now has to match a copied variant by bytes against the `_hu_` file in its source's cache directory. Until that task is done, a build that hits it fails the build test and stops `deploy.sh` (`--panicOnWarning`).

## Conventions

- Process an image **only** through `layouts/partials/image-variant.html` (`dict "image" <raw resource> "spec" "<Hugo spec>"`, plus `"page"` for a page resource) — never `.Resize`/`.Fit`/`.Fill`/`.Process`/`.Filter` directly, which would publish a Hugo `_hu_<hash>` name that a Hugo release can move (a static test fails on both). Pass the raw resource: the partial applies `AutoOrient` itself. Never reference a raw image URL where a variant belongs.

## Scripts and workflows

### `scripts/gallery-embed-metadata.py` — the photo leaves for the web

The post-build pass that writes the metadata into the files the site serves and
takes the camera's private data back out of the published originals. `deploy.sh`
runs it after each of its two builds; run it by hand only to inspect the result:

```bash
hugo
python3 scripts/gallery-embed-metadata.py --dry-run    # resolve and report, write nothing
python3 scripts/gallery-embed-metadata.py              # ~3m40s for 4,161 files
python3 scripts/gallery-embed-metadata.py --check      # every served file carries its UUID
exiftool "public/images/gallery/<some photo>.JPG"      # see what a visitor downloads
```

- It reads `public/<lang>/gallery-metadata.json`, which Hugo renders — so **run
  `hugo` first**, and re-run it after any change to the gallery data or templates.
- Every file is **cleared first** (all metadata but the ICC profile), then gets the
  technical EXIF from the source and the editorial set from the manifest. Nothing
  darktable, the camera or a phone left in the source survives unless it is
  written again.
- It is idempotent: a second run leaves every file byte-identical.
- It aborts before writing anything if a published file maps to no photo, or if a
  source original is missing from the photo store.
- `--check` is what stands between a wrong file and the live site. It compares
  every editorial field of every served file with the manifest, refuses any
  metadata group outside its allowlist, and checks each published original's
  image data against its store file (well under a minute per build). If it fails, do not deploy — read what it names
  (a stray group from a new camera belongs either in `ALLOWED_GROUPS` or cleared),
  fix, rerun the embedding step.
- After each rsync `deploy.sh` reloads the site's nginx container, so a changed
  image redirect map (`/_nginx/gallery-image-redirects.map`) takes effect.

Do **not** run `./deploy.sh` after either script. That is a separate, explicitly
authorised step.

### `scripts/legacy-image-variants.py` — done, do not re-run on its own

The one-time history behind `data/legacyImageVariants.yaml`
(`docs/concepts/stable-image-urls.md` §5): which stable variant each old
`<dir>/_hu_<hash>` URL was, for the nginx variant map. Run on 2026-10-14 against
the first build with stable names and the image cache. The file is **frozen**,
like `slugAliases`: never edit it by hand, never regenerate it. A rerun only adds
lines, and only makes sense right after a build on **Hugo's raw output** — the
embedding pass rewrites every gallery file, and after that no variant has its
cache file's bytes:

```
hugo -e production -d .test-site --cleanDestinationDir     # raw output
python3 scripts/legacy-image-variants.py --dry-run          # read the report first
```

It writes a line only on proof (equal bytes, or the one variant of the source with
that pixel size and format), prints every ambiguous case, and leaves the rest a 404.

### Processing an image in a template

Only through `layouts/partials/image-variant.html` — pass the **raw** resource and
the spec, plus `page` for a page resource:

```
{{ $t := partial "image-variant.html" (dict "image" .image "spec" "fit 600x600") }}
```

It publishes the variant as `<dir>/<spec dir>/<name>.<ext>` (`fit-600x600/…`), a
name a Hugo release cannot move. `.Resize`/`.Fit`/`.Fill`/`.Process`/`.Filter`
anywhere else in `layouts/` fails `tests/static/image-urls.spec.ts`, and so does
any `_hu_` file in the build. A new spec on a gallery photo is a new published URL:
`npm run golden:update`. Changing an existing spec moves URLs — design the redirect
first (`stable-image-urls.md` §2.4).
