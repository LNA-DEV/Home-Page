# Concept: image URLs that only we can move

**Status:** built 2026-10-14 on the owner's "go", all steps 0–8, not committed and not deployed. What differs from the plan is under *As built* below. The deploy is the owner's step, and either repository can go first (§5.3).
- **Decisions:** all six (D1–D6) were settled by the owner on 2026-10-14, as recommended.
- **D5** (every processed image, not only the gallery) was folded in the same day, at the owner's question. **D6** came with it.
- **Added the same day,** when the owner asked whether this can happen again: §7.1 (each failure mapped to its check), the source check in §7.2, and the live check after a deploy (§7.3).

**Measured:** 2026-10-14, Hugo 0.166.0. Against `main` at `630abb3`, the last `.test-site/` build (2026-10-13), the image cache `resources/_gen/images/` and the Caddy access logs 2026-10-06 → 10-11 (`../Web-Services/.inbox/`). The build had 665 photos and 4,253 processed images, of which 3,614 gallery variants (1.11 GB) and 639 others (42 MB).

**Read against:**
- `gallery-metadata-yaml-only.md` §5: slug file names and the nginx stem map.
- `gallery-metadata-single-source.md`: the embedding pass.
- `duplicate-target-paths.md`: the resource-cache ceiling.

**Corrects:** CLAUDE.md, `gallery-images.html`, `home.nginxmap.map` and `tests/golden/collect.mjs` all say that `_hu_<hash>` "depends only on pixels and spec". It also depends on the Hugo release and on the `imaging:` block (§1.1).

Every processed image on the site is published under Hugo's cache key, `<name>_hu_<hash>.<ext>`, and Hugo owns that hash. This covers gallery variants, post images, covers, dex stand-ins and game screenshots.
- **What happened:** on 2026-09-10 Hugo 0.166.0 gave every gallery variant and every post image a new hash. The files stayed byte for byte the same.
- **What went dead:** every older URL of those. That includes the thumbnails Google Images knows, the image sitemap, link previews, images inside feed items readers have already stored, and the `contentUrl` in every photo page's structured data.
- **Why nobody noticed:** nothing in the repo changed, so nothing in the repo could have caught it.

The rule this concept sets: **an image URL changes only when we change something that is visibly part of it** — the name it is published under, or the processing spec. A Hugo release, the `imaging:` config, a darktable re-export or the image cache never moves it.

## As built — what differs from the plan below

- **Step 0.** 163 aliases appended, computed with Hugo's own `urlize` on a scratch site over `data/gallery.yaml` at the four commits of the filename era (`39a1716`, `2460e42`, `a3493a3`, `f0d08f9`), all 163 underscore forms, identical in all four. 21 of them start with `_`; Hugo writes those alias pages (`/en/gallery/photo/_dsc2784/`, verified). The 489 URLs are in the golden list.
- **`image-variant.html` as planned**, plus one helper: `gallery-oriented-size.html` gives a gallery photo's oriented size from the stored pair and the `fit-4000x4000` variant, so `gallery-image-figure.html` and `story/img.html` cap their ladder without an `AutoOrient` read. Only `image-variants.html` keeps that read (allowlisted). The extension comes from `$v.MediaType.FirstSuffix.Suffix`, never from `.RelPermalink`, which would publish the variant under its `_hu_` name.
- **The collision guard is wider than §2.2 (4).** It fires whenever the target name differs from the source's name (a converted format *or* `.JPG` → `.jpg`, `.jpeg` → `.jpg`) and another processable file in the same bundle or asset directory has the same stem ignoring case. Nothing on the site trips it.
- **A call site the table missed:** `image_gallery_items.html`, the home page's 8-photo strip (`fit 600x600`). `get-cover-url.html` used to publish the bare `AutoOrient` image for a cover under 1200 px; it now always takes `fit 1200x1200` (`fit` never upscales). `gallery-image-figure.html` used to publish the bare `AutoOrient` image for a photo under 480 px; it now takes one `fit` variant at the photo's own width, as `story/img.html` already did. `header.html` goes through the partial (`resize x35`); the logo is an SVG, so nothing is processed.
- **Measured, first build** (warm cache): 4,253 processed images published, as before, and no `_hu_` file. New renders only where the chain changed: the 16 galleryImage/story variants (4 photos), the post and page images, and — not foreseen — the **book and game covers**: `.Fill`/`.Fit` and the `Filter` chain have different cache keys, so 215 covers were rendered once more. Their bytes are identical to the old ones (67 of 67 books, 144 of 148 games with one old hash). Build 43 s; warm rebuilds 20 s.
- **`Duplicate target paths`: yes, intermittently.** The first build listed 235 paths, all of them variants rendered fresh in that build (book and game covers ×3 languages, 14 post WebPs and one post cover, the 4 new galleryImage widths of one photo); three later warm builds listed none. A scratch site with the same chain in three languages (20 covers, cold and warm) shows none, so it is the cache ceiling of `duplicate-target-paths.md` and not a race in the copy: the copies took the resource partition from ~1,200 to ~5,500 entries. Expect it again on a build that renders many new variants — a batch of new photos. **Until `duplicate-target-paths.md` is done, such a build fails the build test and stops `deploy.sh`.** That document now says how its classifier matches a copied variant.
- **Embedding (§4) as planned.** `served_gallery_files()` in `gallery_common.py` does the walk and the classification; jobs carry the variant flag from it. Full run on a production build in the scratchpad: 4,279 files (665 originals + 3,614 variants) in 232 s, `--check` OK in 26 s, a second run left every file byte-identical.
- **History (§5.1).** `scripts/legacy-image-variants.py`, run against the first build. The report:

  | | Equal bytes | Same source, size, format | Ambiguous | Nothing | Source gone |
  |---|---:|---:|---:|---:|---:|
  | Gallery (6,016 old hashes) | 5,827 | 65 | 0 | 124 | 0 |
  | Everything else (2,086) | 1,215 | 419 | 2 | 329 | 121 |

  - The two ambiguous ones are one post image (`wiki-loves-earth`, 1195×499), whose `fit-1200x1200` and `resize-1195x` variants have the same size. Left out.
  - "Nothing" in the gallery is retired specs (a photo that is no longer a model or dex cover), the full-size intermediates of the old two-step chain, which were never published, and half-typed titles from `hugo server`.
  - 17 cache names under `images/gallery/` resolve to no photo: titles typed under `hugo server` and never deployed.
  - `data/legacyImageVariants.yaml`: 5,892 gallery + 1,634 other lines, 0.66 MB. A second run keeps all 7,526 and adds none. Keys are quoted: an all-digit hash, or `1234e56`, would otherwise be a YAML number.
- **The map (§5.2).** Targets are percent-encoded (`fit-200x300/The%20Testing.jpg`), keys not. Duplicate keys are found through a scratch map: `merge` copies the dict on every call, quadratic over 7,500 lines.
- **nginx (§5.3) needed `map_hash_max_size 16384`.** At the default 2048 nginx loads the config, but warns that it cannot build an optimal hash and *ignores* `map_hash_bucket_size`, which the stem map's long keys need. Both settings are http-wide and must come before the first map (a second `map_hash_max_size` is a duplicate-directive error). Verified in a throwaway `nginx:latest` container over the new `.test-site/`: `nginx -t` clean, and `scripts/check-live-urls.py` against it passed all 364 checks. Of the 1,276 logged requests (2026-10-06 → 11) for a gallery `_hu_` name that answered 404 or 301 → 404, **1,099 now answer 301 → 200 in one hop**; the rest are hashes older than the cache (before 2026-08-19). Elsewhere 272 of 705.
- **Tests.** As in §7.2, in a new `tests/static/image-urls.spec.ts` (no `_hu_`, the source check, spec directories, the variant map, one `contentUrl`), plus `tests/py/test_legacy_image_variants.py` for the D6 rules and the frozen file. `golden:update` added 3,614 gallery variants (and the 489 of step 0 were added by hand). The static specs that were touched pass on the new build: 88 passed, 1 skipped (the production-URL check). The full `npm test` was not run.
- **The live check (§7.3) against today's site** fails where it should: 0 of 60 underscore URLs, 0 of 150 new variant names and 0 of 100 variant-map keys answer, the 25 stem-map originals do, and the three made-up hashes are 404. Against the local container with the new config it passes completely.

## Settled decisions

| | |
|---|---|
| Scope | Point 3 of the 2026-10-14 analysis (variant hashes) for **every** processed image (D5), plus point 1 (underscore photo aliases). Point 2, the size of `/gallery/general/`, is **out** (§11). The photo pages carry the metadata |
| Resource-cache ceiling | **Accepted** (owner, 2026-10-14). The copies (§2.2) add ~4,250 resources. If the build starts reporting `Duplicate target paths`, that is handled through `duplicate-target-paths.md`, not designed around here. It would come sooner or later anyway |
| A fallback for unknown hashes | **No.** Sending any unknown `_hu_` name to "some" image of the same source is a workaround. Old names are redirected only where the build history proves which variant they were (§5, D6) |
| Commits | None during the concept |

## Decisions D1–D6 (settled by the owner on 2026-10-14, as recommended)

| | Decision | Section |
|---|---|---|
| D1 Naming | A directory per spec next to where the source is published, named like the source: `/images/gallery/fit-600x600/<slug>.jpg`, `/en/posts/<post>/resize-720x/cover.jpg`, `/images/books/covers/fit-200x300/<Title>.jpg` | §2.1 |
| D2 One producer | `layouts/partials/image-variant.html` is the only way a processed image is made, site-wide. It always uses one single chain | §2.2 |
| D3 Old URLs | A frozen history built once from the image cache. Hugo renders it into one nginx map, keyed by directory and hash | §5 |
| D4 `contentUrl` | One URL per photo in all structured data and in the image sitemap: the stable 4000 px variant | §3 |
| D5 Other images | **Integrated:** posts, About, links, books, games (covers and screenshots) and dex stand-ins move with the gallery. That is what lets a test forbid `_hu_` anywhere in the build (§7) | §2, §5 |
| D6 Proof for an old URL | Equal bytes, **or** the same source with exactly one current variant of the same pixel size and format. Needed because posts and screenshots lose their two-step chain (§2.2), so their bytes change once. Without D6, their old URLs stay 404 | §5.1 |

---

## 1. What happened

### 1.1 What Hugo hashes

`resources/image.go`, `relTargetPathFromConfig` (v0.166.0):

```go
hash := hashing.HashStringHex(incomingID, i.hash(), conf.Key, imagingConfigSourceHash)
```

| Input | What it is |
|---|---|
| `incomingID` | The hash of the previous step, when a chain is built in two calls (`(.Filter images.AutoOrient).Process …`) |
| `i.hash()` | The **content** of the source file |
| `conf.Key` | The processing spec. Since 0.166.0 it also carries Hugo-internal version numbers for `images.Filter` chains |
| `imagingConfigSourceHash` | A hash of the **raw `imaging:` block** in `hugo.yaml` |

Tested on a scratch site (0.166.0) and **without** effect:
- the mount source path (absolute, relative, two different directories);
- the file name;
- the mtime;
- `resources.Copy` of the source.

The mount switch of the same evening (`95aae73`) is innocent.

Tested **with** effect: the same build with and without the site's `imaging:` block gives different hashes. Any edit there moves every processed image.

### 1.2 The 2026-09-10 change, reproduced

One store file (`P1001868.jpg`, "Horns and Bell") went through the gallery's own chain `Filter (slice images.AutoOrient (images.Process "fit 600x600"))` with the site's `imaging:` block. The binaries were the official releases, checksums verified.

| Hugo | Thumbnail | Bytes |
|---|---|---:|
| 0.162.1, 0.163.0, 0.165.0 | `…_hu_38b629237b87108d.jpg` (= the 2026-08-19 cache file) | 39,020 |
| 0.166.0 | `…_hu_a3f12f3dfc63ee01.jpg` (= the 2026-09-10 cache file) | 39,020, identical |

- **The cause** is Hugo commit `d19e0a4b`, *"Bump formatVersionNumbers.PNG and fix version cache busting for images.Filter"*. Since then a `Filter` chain's key includes `MainImageVersionNumber`.
- **What it hit:** the gallery uses `Filter` chains everywhere, and post images start with `.Filter images.AutoOrient`. Plain `.Fit` / `.Fill` calls on an unprocessed source were not hit, which is why Hugo's own test hashes did not move. Book and game covers kept their names this time.
- **Timeline:** Homebrew installed 0.166.0 on 2026-09-10 at 21:25. The cache files appeared from 21:29 to 21:49. On that day 4,432 gallery (photo, bytes) pairs got a second name.
- **It can happen again in any release,** to any of them. Hugo marks the `_hu_` prefix *"Do not change"*. It promises nothing about the hash.

### 1.3 What it cost

**Requests.** In the six logged days, 866 requests asked for a gallery variant hash that is no longer served:

| Requester | Requests |
|---|---:|
| tphotobot | 294 |
| other crawlers | 228 |
| browser-like clients | 172 |
| a `zh-CN` crawler | 154 |
| Baiduspider-image | 18 |
| Googlebot-Image | 4 |

Post images 404 as well, for example `/sv/posts/resa/sverige/2024/cover_hu_….JPG`.

**Redirect chains.** Old gallery store names go through the stem map to `<slug>_hu_<old hash>` and land on a 404.

**Structured data.** One photo carries three different `contentUrl`s across the site (Horns and Bell):

| Where | `contentUrl` | Moved on 09-10 |
|---|---|---|
| Grid microdata (`gallery.html`, `gallery-portfolio.html`) | the original, `…goat.jpg` | no |
| Photo page microdata (`<img itemprop="contentUrl">` takes its `src`) | the 1200 px variant `…_hu_630d…` | yes |
| Photo page JSON-LD, image sitemap `<image:loc>` | the 4000 px variant `…_hu_ae9c…` | yes |

**Oversized originals.** 142 of the 665 originals are larger than 15 MiB; the largest is 38 MiB (§3).

## 2. Stable names (D1, D2, D5)

### 2.1 The scheme

A variant lives in a directory named after its spec, next to where its source is (or would be) published, under the source's name. Only the extension follows the output format.

| Source | Published variant |
|---|---|
| Gallery photo (store `P1001868.jpg`, published as `<fileSlug>.jpg`) | `/images/gallery/fit-600x600/horns-and-bell-portrait-of-an-alpine-goat.jpg` |
| Page resource (post, About, links): `cover.JPG` in the bundle of `/en/posts/x/` | `/en/posts/x/resize-720x/cover.jpg` (one per language, as today) |
| PNG screenshot in a post, converted | `/en/posts/x/resize-720x-webp-q85/screenshot.webp` |
| Global asset `images/books/covers/<Title>.jpg` | `/images/books/covers/fit-200x300/<Title>.jpg` |
| Game screenshot `images/games/screenshots/<slug>/01.png` | `/images/games/screenshots/<slug>/fit-640x640-jpg/01.jpg` |
| Dex stand-in `images/dex/reference/<slug>.jpg` | `/images/dex/reference/fill-480x480-center/<slug>.jpg` |

**Directory name.** The spec, lowercased, with whitespace → `-`: `fit 600x600` → `fit-600x600`, `fill 480x480 Center` → `fill-480x480-center`. Every token stays, format and quality included, because each of them changes the bytes or the extension. A spec whose tokens do not reduce to `[a-z0-9]` (a background colour `#ffffff`) is an `errorf` until the scheme is extended on purpose.

**File name.**
- The gallery uses the photo's `fileSlug`, as the original does.
- Everything else keeps the source's base name, including a page resource's sub-path inside its bundle.
- The extension is the output format's, lowercased.

**Why a directory per spec:**
- **No collisions with names.** No file name contains `/`.
- **Descriptive names.** The file name stays exactly the source's: the slug for a photo, the title for a cover.
- **Slug changes stay easy.** nginx can carry the directory over when a gallery slug changes (§5.3).
- **A spec change is visible.** It changes the URL; for the gallery, the golden test sees it (§7).

**Alternatives considered:**
- **Role names (`thumb/`, `large/`).** The URL would survive a spec change. But one name would then mean different pixels over time, and two call sites with different specs under one role would collide. A collision silently publishes whichever rendered first (§2.2).
- **A suffix (`<name>-600.jpg`).** It can collide with another file's name, and every reader would have to parse names to split it off.

### 2.2 One producer: `image-variant.html`

```
{{ $v := partial "image-variant.html" (dict "image" $res "spec" "fit 600x600") }}
{{ $v := partial "image-variant.html" (dict "image" $res "spec" "resize 720x" "page" .Page) }}
```

The caller passes the **unprocessed** resource. The partial:

1. **Computes the target.**
   - **Gallery photo:** `.Name` starts with `/images/gallery/` and `path.Base .Name` is in `gallery-meta.html`'s `bySrc`. Target: `images/gallery/<dir>/<fileSlug>.<ext>`. `.Name` returns the store name for the copies from `gallery-images.html` and for a raw store resource alike.
   - **Other global resource:** `.Name` starts with `/`. Target: `<path.Dir .Name>/<dir>/<stem>.<ext>`.
   - **Page resource:** `.Name` is bundle-relative, with no leading `/`. Target: `<page.RelPermalink><dir>/<sub-path/stem>.<ext>`. It needs `page`; without it, `errorf`.
   - Verified on a scratch site: `.Name` is `cover.JPG` for a page resource and `/images/games/covers/Some Game.jpg` for a global one. A copy to `en/posts/trip/resize-100x/cover.jpg` and `de/posts/trip/…` lands under each language, with no extra language prefix.
2. **Always runs one chain:** `.Filter (slice images.AutoOrient (images.Process $spec))`. `.Fit "200x300"` and friends become `Process "fit 200x300"`. For a cover without an Orientation tag, `AutoOrient` changes nothing: verified, the `fill 300x450` output is identical with and without it.
3. **Publishes only the copy:** `resources.Copy $target`. It never touches the source's `.RelPermalink`. This keeps the game screenshots' rule ("the original is never published") without a special case.
4. **Guards format conversion.** When the output format differs from the source's (PNG → WebP), two sources with one stem in one place would claim one target. The partial `errorf`s if the bundle, or the asset directory, holds another processable file with the same stem.

**One chain is load-bearing.** `resources.Copy` to a path that is already taken returns the first resource, silently. `--printPathWarnings` prints nothing.
- **Verified:** two chains, one target. Whichever rendered first is the one published.
- **So** two chains for one spec would make the served bytes depend on render order.

**What goes with it:** the two-step form `($img.Filter images.AutoOrient).Process …` (or `.Resize`). It is used by:
- `gallery-image-figure.html` and `story/img.html`;
- `image-variants.html`, via `responsive-image.html` and `resolve-cover-image.html` (every post image and cover);
- `game-detail.html` (screenshots).

That form also **re-encodes an intermediate JPEG.** Verified for `fit 720x7200`: different hash, different bytes. Those images are re-rendered once, a little sharper.

**Reading the size.** `image-variants.html` needs the oriented width to cap its width ladder. It reads `.Width` off an `AutoOrient`ed copy, as it does today. That renders a cache entry and publishes nothing.

Verified on a scratch site: Hugo 0.166.0, two languages, the real store file.
- **Published:** only `images/gallery/fit-600x600/goat.jpg`, 39,020 bytes. No `_hu_` file is written.
- **Cache:** **zero new files** in `resources/_gen/`, so the cache hit. The bytes are identical to the cached `_hu_` file.
- **Repeated calls:** called from two places and two languages, one file is published and there is no warning.
- **Dimensions:** `.Width` and `.Height` work on the copy.

### 2.3 Call sites

**Gallery photos:**

| File | Specs |
|---|---|
| `partials/gallery.html`, `partials/gallery-portfolio.html` | fit 600x600, fit 4000x4000 |
| `partials/gallery-photo.html` | fit 600 / 1200 / 4000; related strip fit 600x600 |
| `partials/gallery-download-attrs.html` | fit 600 / 1200 / 4000 |
| `partials/gallery-image-figure.html`, `partials/story/img.html` | fit `<w>x<10w>` (480/720/1080/1440, capped at the original width); two-step chain removed |
| `partials/story/figure.html`, `story/thumb.html`, `shortcodes/storyPhoto.html`, `gallery-story-outing.html`, `gallery-story-essay.html` | fit 600x600 |
| `phototags/term.html`, `partials/gear-card.html`, `partials/get-gallery.html` | fit 600x600 |
| `partials/model-card.html`, `partials/dex-card.html` | fill 480x480 Center |
| `partials/model-detail.html`, `partials/dex-detail.html` (hero), `templates/schema_json.html` (model `ProfilePage` image) | fill 900x900 Center |
| `templates/schema_json.html` (photo), `_default/sitemap.xml` | fit 4000x4000 (§3) |
| `_default/rss.xml` | fit 1600x1600 |
| `_default/list.html` (gallery home cards) | fill 600x400 |
| `feed/list.html` (photo items) | fill 120x120 |

**Everything else (D5):**

| File | Images | Specs |
|---|---|---|
| `partials/image-variants.html` ← `responsive-image.html` (`_markup/render-image.html`, shortcodes `figure`, `img`, `person`) | post and page images | `resize <w>x` for 360/480/720/1080/1500/cap; PNG as `webp q85` |
| `partials/resolve-cover-image.html` → `cover.html`, `templates/_funcs/get-cover-url.html` | post covers | the ladder above; fit 1200x1200 |
| `templates/_funcs/get-page-images.html`, `partials/featured.html` | link previews, page resources and gallery photos | fit 1200x630 |
| `partials/author-portrait.html` | the About portrait | fit 1200x1200 |
| `shortcodes/readingList.html`, `recentReading.html` | book covers | fit 200x300 |
| `shortcodes/gamingList.html`, `recentGaming.html`, `partials/game-detail.html` | game covers; screenshots | fill 300x450; fit 640x640 jpg, fit 1920x1920 jpg (two-step chain removed) |
| `partials/dex-card.html`, `partials/dex-detail.html` | dex stand-ins | fill 480x480 Center; fill `<n>x<n>` Center |
| `feed/list.html` (awards, publications) | their images | fill 120x120 |

`partials/header.html` resizes a logo that is not configured. PaperMod's `index_profile.html` (profile mode, off) is the only theme template that processes an image. Both go through the partial anyway or stay unused. The site-wide test (§7) catches any call site that was missed.

Fingerprinted CSS and JS (`stylesheet.<hash>.css`) are **not** in scope. Their hash is meant to follow their content.

### 2.4 What still moves a URL

**Moves, by our own hand:**
- **A reworded English photo title.** It moves the slug, and every URL of the photo with it, as today. `slugAliases` plus the nginx stem map, extended to carry the spec directory (§5.3), keep the old ones alive.
- **A renamed source file outside the gallery,** or a moved post. As today, there is no automatic redirect for an image of a page that moved; that is outside this concept.
- **A deliberate spec change in a template.** For the gallery, the golden test fails (§7) and the redirect is designed when it first happens, most likely one nginx rewrite per retired directory. Elsewhere the old variant simply goes. This also applies when a replaced post image has a different width ladder.

**Moves no longer:** a Hugo release, an edit of `imaging:`, a re-export from darktable, a cold image cache.

**Bytes behind an unchanged URL** can still change: a re-export, a replaced post image, an encoder change in Hugo, the embedded metadata. For the gallery that is already the case today, because the embedding pass rewrites a variant whenever a title changes, under the same `_hu_` name. ETag and Last-Modified cover it as they do now.

## 3. One `contentUrl` per photo (D4)

**Decided (D4):** use the stable 4000 px variant, `fit-4000x4000/<fileSlug>.jpg`, everywhere a photo is described:
- grid microdata (`gallery.html`, `gallery-portfolio.html`);
- photo page microdata. A `<meta itemprop="contentUrl">` replaces the `itemprop` on the `<img>`, whose `src` is the 1200 px variant;
- photo page JSON-LD;
- the image sitemap;
- `gallery-image-figure.html`.

**Why not the original.**
- 142 originals exceed 15 MiB, up to 38 MiB.
- Google documents 15 MB as the default fetch limit for its crawlers other than Googlebot ([crawler docs change, Feb 2026](https://ppc.land/google-rewrites-googlebots-rulebook-2mb-limits-ip-moves-and-what-crawlers-really-are/)). That the figure covers Googlebot-Image is only reported second-hand.
- So the grid currently names files Google may not read whole.

**Why the 4000 px variant.**
- Every one is under 4 MB.
- It is the file the lightbox shows.
- It carries the same embedded metadata.
- After §2 it is as stable as the original.

**The originals stay published.** The download dialog references them (`data-downloads`), so the 665 originals in the golden list are unaffected. Check this after the switch; the golden test will.

## 4. The embedding pass (`gallery-embed-metadata.py`, `gallery_common.py`)

It only ever reads `public/images/gallery/`, so D5 does not touch it. Three things in it assume the `_hu_` names, and each of them would fail **silently**:

| Today | With §2 | Change |
|---|---|---|
| `os.scandir(gallery)` reads the top level and skips directories without a word | Every variant ships **untagged**, and `--check` never looks at it | Walk recursively. `images/gallery/<file>` is an original, `images/gallery/<dir>/<file>` a variant. Anything else (deeper nesting, a `_hu_` name, a name no record has) aborts the run, as an unmapped file does today |
| `is_variant()`: "the name differs from the record's `file`" | A variant's name now **equals** the original's. Every variant is taken for an original and gets `Orientation` copied in: **22 rotated photos would display rotated twice** | Decide by path. `--check`'s "a variant may not carry Orientation" stays and is exactly the net for this |
| `published_base()` / `VARIANT_RE` strip `_hu_<hash>` | Nothing to strip | Map by basename; both go. A `_hu_` file under `images/gallery/` becomes an error |

The file count and the cost (~3m40s per build, `--check` ~25 s) stay the same. It is still deterministic: a second run must leave every file byte-identical, and the one-time verification checks that.

## 5. Old URLs (D3, D6)

### 5.1 A frozen history, built once

`data/legacyImageVariants.yaml`, generated once by `scripts/legacy-image-variants.py` (stdlib only). It has two sections:

```yaml
gallery:   # <hash>: [<photo id>, <spec dir>] — Hugo renders the current slug
  a3f12f3dfc63ee01: [f3e00148-fd0a-46d9-af55-26451587ac92, fit-600x600]
other:     # "<old dir>/_hu_<hash>": "<new path>"
  "/sv/posts/resa/sverige/2024/_hu_2de41cb0570c577a": "/sv/posts/resa/sverige/2024/resize-720x/cover.jpg"
```

**When it runs:** after the first `hugo` with the new names and **before** the embedding pass, while `public/` still holds Hugo's raw bytes.

1. **Index the new variants.** For every file in a spec directory under `public/`, record its SHA-256, its source and its pixel size.
   - Source = directory + name. For the gallery it is the photo, through the manifest's `file`.
   - The pixel size comes from a header read (JPEG SOF, PNG IHDR, WebP VP8/VP8L/VP8X).
2. **Walk every `*_hu_*` file in `resources/_gen/images/`.** The cache mirrors the published paths, language directories included. It holds everything this machine has rendered since 2026-08-19, under old and new names (hardlinks, read once per inode).
   - The source is the cache file's directory plus the stem before `_hu_`.
   - For the gallery, the stem is resolved through store stems, `slugAliases` and file slugs to the photo.
3. **Decide each old hash (D6).**
   - **Equal bytes** to a new variant: write a line.
   - **Otherwise:** the same source with **exactly one** new variant of the same pixel size and format: write a line. This is the case where the chain changed (§2.2), so the bytes did too, but source, size and format say it is the same picture.
   - **Anything else:** nothing. That covers more than one candidate (a 3:2 photo's `fit 600x600` and `fill 600x400` are both 600×400), a re-cropped source and a retired spec.
4. **Print a report**: counts per rule and per area, plus every ambiguous case. The owner reads it before the file is committed.

**Measured against today's build and cache.** This is before the switch, so it is an estimate. The script's report in step 4 is the real figure.

| | Bytes | Same source, size, format, unique | Nothing |
|---|---:|---:|---:|
| Gallery, older hashes (2,394) | 2,229 | 32\* | 133 |
| Everything else, older hashes (917) | 426 | 48 | 443 |

- **The gallery's 3,614 current hashes resolve by bytes,** except the few from the former two-step sites; those resolve by D6.
- **The 607 current hashes elsewhere** resolve by bytes where the chain stays the same (covers, dex, link previews). Where it changes (posts, screenshots), they resolve by D6.
- **Logged requests:** of the 866 logged requests for an old gallery hash, 693 match by bytes alone.
- \* **The estimate undercounts the gallery's D6 column.** It compares stems literally, so it misses old gallery names under the store stem. The script resolves those through the manifest.

**Frozen, like `slugAliases`:**
- The file is never recomputed, and the cache is not needed for it afterwards.
- A rerun only adds lines.
- Gallery lines store **ids, not paths**, so a later reworded title does not break them: Hugo renders the current slug.
- Size: estimate ~8,000 lines, ~0.6 MB.

### 5.2 The map

A new output format, `nginxvariantmap` (English home only, like `nginxmap`). `layouts/_default/home.nginxvariantmap.map` writes `/_nginx/image-variant-redirects.map`:

```
"/images/gallery/_hu_a3f12f3dfc63ee01" /images/gallery/fit-600x600/horns-and-bell-portrait-of-an-alpine-goat.jpg;
"/sv/posts/resa/sverige/2024/_hu_2de41cb0570c577a" /sv/posts/resa/sverige/2024/resize-720x/cover.jpg;
```

- **The key is directory + hash.** The stem is left out, so a gallery file requested under its store name or its slug, as `.JPG` or `.jpg`, is one hop.
- **The directory is in the key** because one hash exists once per language for a page resource, and each language has its own target.
- **Missing photo ids are skipped.** A photo that is gone has no original either.
- **Targets are tested.** That every target is a served file is a static test (§7), not a template check, because a template cannot see what other pages publish.

### 5.3 nginx (`../Web-Services/homepage{,-tor}/nginx.conf`)

| Request | Response |
|---|---|
| `/images/gallery/fit-600x600/<slug>.jpg`, `/en/posts/x/resize-720x/cover.jpg` | 200 |
| `<dir>/<any stem>_hu_<known hash>.<ext>` | 301 → its new path |
| `<dir>/<any stem>_hu_<unknown hash>.<ext>` | 404, **no** 301 → 404 chain |
| `/images/gallery/<store stem>.JPG` (old original name) | 301 → `/images/gallery/<slug>.jpg` (unchanged) |
| `/images/gallery/<spec>/<former slug>.jpg` (a `slugAliases` entry) | 301 → `/images/gallery/<spec>/<slug>.jpg` |

Sketch, **to be verified in a local nginx container** before any deploy, as on 2026-10-11. The `_hu_` location comes **first**: regex locations match in order, and the gallery one below would otherwise take gallery `_hu_` requests.

```nginx
map "$legacy_dir$legacy_hu" $legacy_variant_new {
    default "";
    include /usr/share/nginx/html/_nginx/image-variant-redirects*.map;
}
location ~ "^(?<legacy_dir>/(?:[^/]+/)*)[^/]+?(?<legacy_hu>_hu_[0-9a-f]+)\.[A-Za-z0-9]+$" {
    root /usr/share/nginx/html;
    if ($legacy_variant_new) { return 301 $legacy_variant_new; }
}
# Gallery renames: the stem map as today, without a hash part, carrying the spec directory.
location ~ "^/images/gallery/(?<gallery_dir>[a-z0-9-]+/)?(?<gallery_stem>[^/]+?)\.(?<gallery_ext>[A-Za-z]+)$" {
    root /usr/share/nginx/html;
    if ($gallery_new_stem) { return 301 /images/gallery/$gallery_dir$gallery_new_stem.$gallery_ext_lc; }
}
```

- **No rule here returns 404 itself.** An unknown hash falls through to the file system.
- **So the deploy order does not matter.** If nginx goes first, its new map file is missing (the glob makes that a no-op) and today's `_hu_` files are still served. If Home-Page goes first, old `_hu_` requests 404 until nginx follows.
- **Both configs need the change,** `homepage/` and `homepage-tor/`. They are single-file bind mounts, so `docker compose up -d --force-recreate` is required.
- **Bucket size:** keys up to ~70 bytes fit the existing `map_hash_bucket_size 256`. The static test's 200-byte limit extends to this map.

## 6. Point 1: old photo page URLs with an underscore (step 0)

- **What was live.** From `39a1716` (2026-09-14) to `a40d8ec` (2026-09-18), a photo page's segment was `urlize(stem(src))`. Hugo's `urlize` **keeps** `_` (verified: `DSC_2721` → `dsc_2721`, `_DSC2831` → `_dsc2831`).
- **What the migration wrote.** The filename→title migration wrote the aliases as `dsc-2721`.
- **Recomputed.** For all 648 photos of that time, from `data/gallery.yaml` at `a40d8ec^` and at `39a1716` (identical results): 485 aliases are right and **163 are wrong**, every one of them an underscore case.
- **The damage.** 163 × 3 languages = **489 URLs answer 404**. Googlebot (66.249.65.x) requested `/en/gallery/photo/dji_0901/` and `/en/gallery/photo/dsc_2721/` during the logged week.
- **The hyphen aliases** redirect from URLs that never existed.

**Fix:**
- **Append the old form** to those 163 entries' `slugAliases`: `[dsc-2721]` → `[dsc-2721, dsc_2721]`.
  - Compute it with Hugo's own `urlize`, using a scratch template over the git history as in this analysis. Do not re-implement it in Python.
  - The hyphen forms stay: they have been published alias pages since 2026-09-18 and cost nothing.
- **Add the 489 URLs** to `tests/golden/published-urls.txt` by hand. They were published, and the list's job is to keep every URL that ever was alive.
- **nginx stem map:** nothing to do. The new alias equals the store stem ignoring case, and `home.nginxmap.map` already de-duplicates a key that points at the same photo.
- **To verify:** Hugo writes an alias whose segment starts with `_` (`/en/gallery/photo/_dsc2831/`).

## 7. Tests

### 7.1 What went wrong, and what stops it now

Every failure behind this concept, including the ones the plan itself could have caused, mapped to the check that now catches it.

**Where the checks run:** `npm test` runs all of them. `deploy.sh` runs the whole `static` project a second time over the very `public/` it is about to rsync, so every `static` check below is also a **deploy gate**.

| What went wrong (or would have) | What stops it now |
|---|---|
| Hugo 0.166 renamed every variant (2026-09-10), and nothing noticed | Names no longer contain a hash (§2). **No `_hu_` anywhere** in the build. The gallery variants are in the golden list, so any variant URL that disappears fails `urls.spec.ts`, whatever the cause |
| Old variant URLs answered 404, or 301 → 404 | Every variant-map target must be a served file. The stem redirect never carries a hash any more. The **live check** after the deploy (§7.3) requests a sample on the real server |
| 163 photo aliases pointed at URLs that never existed: 489 × 404 for four weeks | The 489 URLs join the golden list. Every photo page URL has been in it since 2026-09-21, so a future slug migration with a wrong formula fails `urls.spec.ts` before the deploy |
| One photo had three different `contentUrl`s | The structured-data test (§7.2) |
| *Would have:* the embedding pass silently skipping the new subdirectories, or copying `Orientation` onto variants | Python tests. The pass aborts on any file it cannot classify. `--check` refuses a variant that carries `Orientation` |
| *Would have:* two chains under one name, where the first rendered wins | The source check (§7.2): no image processing outside `image-variant.html` |
| *Would have:* a changed `nginx.conf` whose container was never recreated (single-file bind mount), so the map is silently not loaded | The live check (§7.3) |

**What no test here can see:** Google's side. Whether Search Console counts an item depends on Google's indexing (§11), not on this build.

### 7.2 The checks

| Where | Assertion |
|---|---|
| `static` (new) | **No file anywhere in the build has a `_hu_` name.** Possible only because of D5, and it is the guard against every call site that was missed, theme included |
| `static` (new), over the source | **No template outside `image-variant.html` processes an image.** No `.Resize`, `.Fit`, `.Fill`, `.Crop`, `.Process`, `images.Process` or `resources.Copy` of an image anywhere else in `layouts/`. Short allowlist with a reason per line: the originals' copy in `gallery-images.html`, and the oriented-width read in `image-variants.html`. This keeps one chain per target at the source, which the output cannot prove: a second chain under a taken name publishes nothing new |
| `static` (new) | Every processed image sits in a directory matching the spec pattern. Its file name is its source's: under `images/gallery/`, a live original's name |
| `tests/golden/collect.mjs` | Also collects the **gallery** variants: ~3,600 more lines. The switch is one deliberate `golden:update`. From then on a gallery variant URL can only leave the list together with its redirect. Variants elsewhere stay out: their set follows each source's width, and replacing a post image may legitimately change it |
| `urls.spec.ts` `redirectedImage()` | The stem redirect carries the spec directory; a `_hu_` URL resolves through the variant map |
| `static`, variant map | Every target is a served file, every key is a directory + `_hu_` + hex, no key twice, every key under 200 bytes |
| `static`, structured data | On every photo page, microdata and JSON-LD `contentUrl` are equal, equal the sitemap's `<image:loc>`, and equal the grid's |
| `gaming.spec.ts:203` | "Only processed variants under `screenshots/`, never an original", now read as "only spec directories" |
| `tests/py` | Recursive walk; `is_variant` by path; a `_hu_` file and an unknown name both abort |
| `html.spec.ts:479`, `data-output.spec.ts:284` | Their `_hu_` stem parsing reads the directory form |

### 7.3 The live check after a deploy

**Why it exists.** The tests never reach the network, so they cannot see the server. Twice now, the failure has sat exactly there: a redirect that ended in a 404, and an nginx change that needs a recreated container.

**What it is:** `scripts/check-live-urls.py` (stdlib, `urllib`), run by `deploy.sh` right after the clearnet publish and its nginx reload, before the Tor build.

**What it requests:** a **deterministic sample** from the artefact just shipped. Every n-th line, so two runs check the same URLs. It uses HEAD and follows exactly one redirect.

| Sample | Expected |
|---|---|
| ~100 gallery variants and ~50 other variants from `public/` | 200 |
| ~100 keys of the variant map | 301 to the target, which answers 200 |
| ~50 keys of the stem map (store stems, `slugAliases`) | 301 to the target, which answers 200 |
| The 489 underscore photo URLs (§6), sampled | 200 (the alias page) |
| A few `_hu_` names with a made-up hash that is in no map | 404, not a 301 |

**What a failure does:** it stops the script. The clearnet site is already live at that point, so the check cannot prevent the failure. It does report it within seconds of the deploy instead of weeks later, and the Tor build is not published on top of it.

**Limits:** it checks the clearnet site only. The onion serves the same files under the same nginx rules.

**Cost:** ~350 HEAD requests against our own server, a few seconds.

## 8. Build order

0. **Point 1** (§6). Independent.
1. **`image-variant.html` and the gallery call sites** (§2.3, first table). Build, then measure: no new cache files except at the former two-step sites; file count; `Duplicate target paths` yes or no (accepted either way).
2. **The other call sites** (§2.3, second table). `image-variants.html`, `responsive-image.html` and `resolve-cover-image.html` hand the partial the raw resource. Build and measure the same way.
3. **`contentUrl`** (§3).
4. **Embedding pass** (§4) and its Python tests. Full run, `--check`, then a second run that must leave every file byte-identical.
5. **History script** (§5.1): run it, and the owner reads its report. Then the data file, the output format and the map template (§5.2).
6. **Tests** (§7.2), then `golden:update`. Then the live check (§7.3) and its call in `deploy.sh`. Run it once by hand against today's live site: it must fail where the site is broken today (the underscore URLs, the 301 → 404 chains) and pass after the deploy.
7. **`../Web-Services`** (§5.3), verified in a local container.
8. **Docs.**
   - CLAUDE.md: *Served image names*, *Embedded metadata*, *Inlining a gallery photo*, the reading-list and gaming paragraphs that describe `.Fit` / `.Fill`, and the conventions bullet "Use Hugo image processing".
   - `AGENTS.md:138`.
   - The comments in `gallery-images.html`, `home.nginxmap.map`, `collect.mjs` and `image-variants.html`.
   - A pointer from `gallery-metadata-yaml-only.md` §5 to this file.
   - `duplicate-target-paths.md`: its classifier recognises a processed image by the `_hu_` path that `resources/_gen/` mirrors. A copied variant has to be matched by bytes against a `_hu_` file in the cache directory of its source instead.

The deploy is the owner's step, and either repository can go first (§5.3).

## 9. Cost

- **Build:** the gallery needs no reprocessing (cache hit verified). The sites that lose the two-step chain are rendered once: 282 post and page images, the game screenshots, and the galleryImage and story images (4 content files). Small files, seconds.
- **Embedding:** the same number of files.
- **First deploy:** ~1.15 GB under new names, once per site (clearnet and Tor). That is 1.11 GB of gallery variants and 42 MB of the rest. rsync cannot see a rename across directories. `--delete` removes the 4,253 `_hu_` files.
- **Repository:** the data file ~0.6 MB; the golden list ~3,600 lines longer.

## 10. Files touched

- **New:**
  - `layouts/partials/image-variant.html`
  - `layouts/_default/home.nginxvariantmap.map`
  - `scripts/legacy-image-variants.py`
  - `data/legacyImageVariants.yaml`
  - `scripts/check-live-urls.py` (§7.3)
  - a static test file for §7.2 (output and source checks)
- **Changed:**
  - every template in §2.3;
  - `hugo.yaml` (output format; `languages.en.outputs.home`);
  - `deploy.sh` (the live check after the clearnet publish);
  - `scripts/gallery-embed-metadata.py`, `scripts/gallery_common.py` and their tests;
  - `tests/golden/collect.mjs`, `tests/golden/published-urls.txt`, `tests/static/urls.spec.ts`, `html.spec.ts`, `data-output.spec.ts`, `gaming.spec.ts`;
  - `data/gallery.yaml` (163 `slugAliases`);
  - the docs in step 8;
  - `../Web-Services/homepage{,-tor}/nginx.conf`.

## 11. Deliberately out of scope

- **Point 2: the size of `/gallery/general/`.** It is 1.91–1.93 MB live, against Googlebot's 2 MB per-file cap. Not pursued (owner, 2026-10-14): each photo's page carries its own metadata.
- **Fingerprinted CSS and JS.** Their content hash is the point of them.
- **Redirects for images of a page whose URL moved.** Pages move through aliases; their images never followed, then or now.
- **Pinning the Hugo version.** Not needed once no URL depends on it.
