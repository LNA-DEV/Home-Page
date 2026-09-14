# Concept: one page per gallery photo

**Status:** implemented, uncommitted. Built and verified against a full site build on 2026-09-14.
**Measured:** 2026-09-14, against `data/gallery.yaml` and the photo store (648 photos — 572 general, 76 archive). Alias behaviour verified on Hugo 0.166.

648 photographs currently live on four list pages and have no URL of their own. This gives each of them a real, indexable page, while the lightbox keeps behaving exactly as it does today.

## Settled decisions

| | |
|---|---|
| URL | `/gallery/photo/<slug>/` |
| Slug | `entry.slug \|\| stem(entry.src)`, derived at build time — 0 collisions, no stored field |
| Heading | The title, never the alt text |
| Permalink | `/gallery/photo/<uuid>/` as an alias |
| Language | English only for now; German and Swedish later |
| Coverage | All 648 photos, no exceptions, no thin-content threshold |

---

## 1. Diagnosis — two separate reasons nothing gets indexed

The first is the obvious one. `/gallery/general/` renders all 572 non-archive photos into a single document, and every photo's anchor points at a `.JPG` binary. A crawler arriving there finds one page with 572 images and no per-image text to attach to any of them. There is nothing to rank because there is nothing to index.

The second is quieter. `layouts/_default/sitemap.xml` already emits `<image:image>` entries — but it builds them from `.Resources`, which is page-bundle images only. Gallery photos are *global* resources reached through `resources.Match "images/gallery/*"`, so they are in **no image sitemap at all**. That is independent of the page work and much cheaper to fix, so it rides along in the same pass.

**A third, found during implementation.** Every page produced by a content adapter was emitting `<priority>0</priority>` in the sitemap — the worst possible value, on 154 dex species pages, long before this work started. Hugo defaults `Sitemap.Priority` to `-1` ("unset") for a file-based page but to `0` for an adapter page, and the template guarded with `ge .Sitemap.Priority 0.0`, which lets the zero through. Changed to `gt`: omitting the element is how "unset" is spelled, and consumers then assume 0.5. Without this fix the 648 new pages would have inherited the same self-sabotage.

## 2. What the metadata actually supports

Reading `data/gallery.yaml` alone badly understates coverage, because `collect-images.html` already merges EXIF and XMP on top of it. Resolved the way the template actually resolves it:

| Field | Resolution order | of 648 |
|---|---|---:|
| **Alt text** | `yaml.alt` → `XMP.Notes` → `Exif.ImageDescription` | **588** |
| Keywords | `Exif/XMP.Subject` → `yaml.tags` | 621 |
| Descriptive filename | `src` stem that is not a camera code | 221 |
| Species | `yaml.species` | 172 |
| **Stored `title:`** | `yaml.title` | **0** |
| *Nothing at all* | no name, no alt, no species, no tags | **4** |

XMP `Notes` alone supplies 281 alt texts the YAML does not have. Only four photos are genuinely empty, which is why there is **no thin-content threshold** in this design — every photo gets a page and they all go in the sitemap. A naive read of the YAML suggests 207 empty photos; that number is wrong and should not be used to justify a conditional branch.

Two things about titles that shape §3 and §5:

- **No image entry has a `title:` value.** 626 of them carry the key with an empty string. Title is, today, an entirely unused field.
- **`Exif.ImageDescription` is not a title.** `collect-images.html` treats it as one, but all seven values present in this library are prose captions of 97–149 characters — and six of them are the *same* paragraph about the Avesta Visentpark. It is caption text, which is what `image-alt.html` already correctly uses it for. It should be dropped from title resolution.

> **Found in passing:** seven files carry an XMP `Description` that `image-alt.html` never reads — it checks `XMP.Notes` then `Exif.ImageDescription` and stops. Adding one fallback recovers seven more alt texts.

## 3. Identity — the slug comes from the filename

```
slug = urlize( entry.slug  ||  stem(entry.src) )
```

That is the whole rule. Both inputs live in `data/gallery.yaml`, both are git-tracked, and across all 648 photos it produces **zero collisions** at an average of 19 characters. Because nothing in it depends on data outside git, the slug does **not** need to be a stored field — it is derived at build time, with an optional `slug:` override for the cases where a URL has to be pinned by hand.

That removes the entire migration: no 648-line diff, no bulk generator script, no collision review.

### Why not the alt text

Measured, not assumed. Slugifying alt prose gives 52 colliding slugs across 131 photos and produces URLs like `photo-was-taken-avesta-visentpark-which` and `image-water-body-forest-background-there`. The alt text has two registers — clean descriptive noun phrases, and conversational sentences — and only the first slugifies. Adding `Exif.ImageDescription` to the source chain is worse still: one of its values yields a 147-character slug.

### Why not tags or species

Also measured, also worse: 82 colliding slugs across 253 photos, including `zsl-sdr` 26 times from a camera-written tag. Tags are noisier than prose, and `birdlife-waterfront-marine` is a worse URL for a seagull photograph than anything derived from the name.

### What this costs

427 of 648 photos still have camera-code filenames, so they land on `/gallery/photo/p1002301/` with a matching `P1002301` heading. That is the honest price of tying identity to the name, and the fix is renaming the file — which is already the documented workflow in `CLAUDE.md` (rename in the photo store, update `src:`, never touch `id`) and already the convention for newer work:

```
Heavy Early Mornings - White-Tailed Eagle Skimming a Fog-Covered Bog Lake.jpg
It's Always Cozy in the Sun - Spring Lamb Curled Up in a Sunlit Meadow.jpg
Sunrise Patrol - White-tailed Eagle Gliding Over a Bavarian Bog.jpg
```

221 filenames are already descriptive; 20 of those use the `<Title> - <Description>` form above. Both the full stem and the title half slugify with zero collisions, so the split is a free choice — see §5.

A useful side effect: the URL mirrors the filename exactly, so a photo can be traced from a live URL to the file on disk and back without consulting any lookup table.

### Renaming after publication

Renaming a file changes its slug and therefore its URL. Two things keep that safe:

- The `/gallery/photo/<uuid>/` alias is derived from `id`, which never changes, so a permanent address always resolves.
- Setting `slug:` on the entry pins the URL regardless of what the file is called. Rename freely before a photo is published; pin it afterwards if the old URL matters.

## 4. Generation — a content adapter, exactly like the dex

`content/gallery/photo/_content.en.gotmpl` calls a new `layouts/partials/gallery-photo-pages.html`, which loops `collect-images.html` with `excludeArchive false` and emits one `.AddPage` per entry. The renderer is a new `gallery-photo.html`, dispatched on `params.theme` in **both** `page.html` and `single.html` (see the template-dispatch note in `CLAUDE.md`).

```go-html-template
{{ $.AddPage (dict
  "path"     $slug
  "kind"     "page"
  "title"    $title
  "content"  (dict "mediaType" "text/markdown" "value" $alt)
  "aliases"  (slice (printf "/gallery/photo/%s/" $id))   {{/* top level, NOT params */}}
  "params"   (dict
    "theme"     "gallery-photo"
    "filter_id" $id
    "cover"     (dict "image" $og.Permalink "alt" $alt))
) }}
```

Two things worth recording:

- **`aliases` is a top-level key of `AddPage`, not a param.** Verified against Hugo 0.166, where it emits a redirect page carrying `rel=canonical` back to the slug URL. Putting it under `params` does nothing.
- **`params.cover.image` is the cheapest route to social images.** Setting it to the 1200px variant means PaperMod's own `opengraph` and `twitter_cards` partials pick the right image up with no theme edit at all. `cover.html` is never called, because the `gallery-photo` branch in `page.html` bypasses it — so the cover params only feed metadata, never the rendered page.

The section index at `/gallery/photo/` gets `build: {list: never, render: never}` via a `content/gallery/photo/_index.en.md` stub — `/gallery/general/` already is that page, and a second copy of it would compete with the original.

### Languages

English only for now. The German and Swedish gallery grids link across to the `/en/` photo page.

This deliberately does **not** copy the dex approach. The dex generates all three languages because it has genuine per-language prose with an English fallback; a photo page would have nothing per-language except chrome, so three near-identical pages would be pure duplicate surface. The switch later is: nest `alt` and `title` as `{en, de, sv}` maps in `data/gallery.yaml`, add `_content.de.gotmpl` and `_content.sv.gotmpl`. The slug does not change, so this adds pages without moving any.

## 5. Anatomy — what is on the page

### Title and alt are different things

```
title = entry.title  ||  stem(entry.src)        → the H1
alt   = entry.alt || XMP.Notes || Exif.ImageDescription   → body prose
```

The heading is the **title**. The alt text is never promoted into it — it is body copy that sits under the photograph, where its length is an asset rather than a problem. Keeping the two apart is what lets the alt stay a full descriptive sentence for screen readers and for search, while the heading stays a name.

`Exif.ImageDescription` is deliberately absent from the title chain (§2): in this library it only ever holds caption prose.

Two open choices, both free — either spelling collides with nothing:

- **The `<Title> - <Description>` filenames.** 20 files use the form `Sunrise Patrol - White-tailed Eagle Gliding Over a Bavarian Bog`. Splitting on `" - "` gives a short punchy H1 plus a descriptive subtitle line; not splitting gives one long heading. Slug is unaffected either way.
- **The fallback for the 427 untitled photos.** The heading is `P1002301` unless something else stands in. 98 of them carry a species, so `title → species common name → filename stem` would replace a quarter of those with *Red Fox*, at the cost of a heading that no longer matches the slug. Leaving it as the stem is the consistent option; the real fix for both is renaming the file.

`.DisplayTitle` is derived once in `collect-images.html` and is never empty: the title where one exists, the filename stem where it does not. The page heading, the prev/next labels and the related-photo captions all read it, so they cannot drift apart. `.Title` stays blank for camera-code filenames so the grid does not caption a photo the author never named.

One partial was added that the plan did not anticipate. `collect-images.html` walks all 648 photos pulling EXIF for each and is not `partialCached` at its call sites — affordable for a handful of list pages, but 648 per-photo pages would have turned it into 648 × 648 full EXIF extractions. `gallery-collected.html` runs it once behind `partialCached` and returns `byId` / `bySlug` / `neighbours`, so a page that wants one photo does an O(1) lookup.

### Everything else

| Element | Detail |
|---|---|
| **Hero** | Responsive `srcset` over the existing 600px and 4000px renders plus one new 1200px variant. Wrapped in an `id="gallery"` container holding a single `.gallery-item`, so likes, PhotoSwipe and the info popup all work with **zero new JavaScript**. Its `href` is the 4000px file, so clicking without JS gets the full image. |
| **Alt text** | Visible prose beneath the photo *and* the `alt` attribute. This is the page's indexable body, and the reason 588 of 648 pages are worth crawling. |
| **Species** | Common name linked to its dex entry through `dex-lookup.html`, with the scientific name beside it. 172 photos; also a real internal link into the dex. |
| **Capture** | Date, camera, lens, focal length, aperture, shutter, ISO, editing software — all already resolved by `collect-images.html`, nothing new to compute. |
| **Licence** | Licence text and artist resolved through `data/licenseMap.yaml`, linked to `/licensing/`, with the same schema.org `ImageObject` microdata `gallery.html` emits. |
| **Identifiers** | The UUID in monospace, labelled as the stable identifier, next to the permanent `/gallery/photo/<uuid>/` URL that resolves to this page whatever the filename becomes. |
| **Appears in** | Links back to the general gallery, to each project album the photo belongs to, to the archive where applicable, and to the dex species page. Internal linking is what gives a crawler a reason to reach these pages at all. |
| **Prev / next** | Neighbours in the gallery's own sort order, so the whole set is walkable without returning to the index. |
| **Related** | Six similar photographs, scored at build time — see §6. |
| **JSON-LD** | A proper `ImageObject` branch in `schema_json.html`. Without it these pages fall through to `BlogPosting` and assert a `datePublished` of `0001-01-01` — the same bug the dex pages had. |

## 6. Related photos, scored at build time

The tag vocabulary is 609 distinct tags at a median of 10 per photo, and it has a very heavy head: `photo` is on 589 of 648 images, `photography` on 557, `nature` on 446. Matching on raw tag overlap would rank almost everything against almost everything.

Inverse document frequency solves that **without a hand-curated stopword list**. A tag carried by 589 photos scores near zero; a tag carried by three is highly discriminative, and stays that way as the library grows. Nothing has to be maintained.

```
score(a, b) =  Σ idf(t) for t in tags(a) ∩ tags(b)      idf(t) = log(N / df(t))
               + 3.0   same species
               + 2.0   same project album
               + 0.5   same category
               − 1.0   b is archived and a is not

tags with df > 60 are skipped entirely — 23 tags, all of them the head above
```

Skipping that head is what makes this affordable. Walking an inverted index over every tag costs **1,259,759** posting-pair visits; capping at `df > 60` drops it to **64,022** — for the entire gallery, computed once in a `partialCached`, not per page. The 23 discarded tags contribute an IDF of roughly 0.1 each, so quality loss is nil.

**What it returns:** 585 of 648 photos get a full six. The 32 that get nothing are exactly the untagged ones, and they fall back to same-category, nearest-capture-date. Spot-checks: `Alpaca behind tree` returns four other alpacas ahead of the rest of the animal set; a mallard frame returns five other ducks, matched on `duck` and `waterfowl` rather than on `animal` or `nature`.

> **Measured, not predicted.** This was flagged as the one part to time rather than guess. A full build goes from 10.4 s to 11.1 s with the strip enabled, so the similarity pass costs about **0.7 seconds** for the whole gallery. `newScratch` was the deciding detail — `merge` copies the entire map on every write, which at 648 photos × ~10 tags is millions of map copies. The `scripts/gallery-related.py` fallback is not needed.

One dependency: 352 photos get their keywords from EXIF/XMP `Subject` rather than the YAML, so the scorer has to read *resolved* tags. `collect-images.html` currently joins them into a comma-delimited `.Keywords` string — it needs to also expose `.Tags` as a real slice.

## 7. Behaviour — HTML links out, JavaScript intercepts

In `gallery.html` the item's `href` changes from the raw image to the photo page. PhotoSwipe already calls `preventDefault` on clicks within `.gallery-item`, so a visitor with JavaScript sees no change whatsoever — the lightbox opens exactly as it does now, the `#<uuid>` deep links keep working, and `openFromHash` is untouched.

> **One thing breaks if missed.** The lightbox download button does `el.href = pswp.currSlide.data.element.href`. Once `href` is the photo page, **every download serves an HTML file**. The full-size URL has to move to a `data-download` attribute and `lightbox.js` has to read it from there. Ship both halves in one commit.

## 8. Cost

| Dimension | Now | After | Note |
|---|---:|---:|---|
| Rendered pages | 750 | ~1,400 | English only; ×3 later if de/sv are turned on |
| Image variants | 2 / photo | 3 / photo | 648 new 1200px renders, one-off — 600 and 4000 already exist, so nothing re-renders |
| Search index | 732 KB | ~830 KB | Page body is just the alt sentence, so photos become searchable cheaply |
| Similarity pass | — | 64,022 | Posting-pair visits for the whole gallery, computed once — the only figure here worth timing |
| Sitemap URLs | 750 | ~1,400 | Each photo page also carries an `<image:image>` entry |

The 1200px pass is the only real cost, and it is paid once. **Do not clear `resources/_gen/images`** to make it happen — a cold rebuild of the whole gallery runs well past ten minutes.

## 9. Build order

Each step leaves the site working, and nothing links to the new pages until step 05.

1. **Derive the slug** — `gallery-meta.html` computes `.slug` from `entry.slug || stem(src)` as a derived key beside `.projects`, and hard-fails on a duplicate. No data migration; `data/gallery.yaml` is untouched at this step.
2. **Split title from alt** — `collect-images.html` drops `Exif.ImageDescription` from the title chain, and exposes `.Slug` and `.Tags`. Verify the lightbox caption still reads correctly, since it shares `.Title`.
3. **Adapter, renderer, styles, i18n** — the pages now exist and resolve, but nothing on the site points at them yet, so they are safe to inspect before committing to the link swap.
4. **Related photos** — `gallery-related.html` plus its strip on the page. Separate from step 3 so its build cost can be timed on its own.
5. **Swap the gallery link and the download attribute** — the `href` change in `gallery.html` and the `data-download` change in `lightbox.js` are a pair. One without the other breaks downloads.
6. **Structured data and sitemap** — the `ImageObject` branch in `schema_json.html`, and gallery photos finally reaching the image sitemap.
7. **Verify against a fresh build** — a photo page, a working download button, and `/gallery/photo/<uuid>/` redirecting. Use a fresh build or a separate port; the long-running `hugo server` on :1313 misses newly created layout files.

## 10. Files touched

### New

| Path | Purpose |
|---|---|
| `content/gallery/photo/_content.en.gotmpl` | Content adapter, English only |
| `content/gallery/photo/_index.en.md` | Section stub, `build: {list: never, render: never}` |
| `layouts/partials/gallery-photo-pages.html` | The `.AddPage` loop |
| `layouts/partials/gallery-photo.html` | The page renderer |
| `layouts/partials/gallery-collected.html` | The whole gallery collected once, with `byId` / `bySlug` / `neighbours` indexes |
| `layouts/partials/gallery-related.html` | IDF similarity index for the whole gallery, `partialCached` once |
| `assets/css/extended/gallery-photo.css` | Auto-bundled, theme-variable based |

### Modified

| Path | Change |
|---|---|
| `data/gallery.yaml` | Nothing required. `slug:` and `title:` are optional per-entry overrides |
| `layouts/partials/gallery-meta.html` | Derive `.slug` from `entry.slug \|\| stem(src)`; hard-fail on a duplicate |
| `layouts/partials/collect-images.html` | Expose `.Slug`, `.Tags`, `.Projects`, `.DisplayTitle`; drop `Exif.ImageDescription` from the title chain |
| `layouts/partials/gallery.html` | `href` → photo page; add `data-download` |
| `assets/js/lightbox.js` | Download button reads `data-download` |
| `layouts/_default/page.html`, `single.html` | Dispatch `gallery-photo` |
| `layouts/partials/templates/schema_json.html` | `ImageObject` branch |
| `layouts/_default/sitemap.xml` | Emit `<image:image>` for gallery photos; fix the adapter-page `<priority>0</priority>` bug |
| `i18n/{en,de,sv}.yaml` | Labels under a new `# Photo page` block |

## 11. Deliberately out of scope

- The `galleryImage` shortcode currently links to `/gallery/general/#<uuid>`. Once photo pages exist that is the better target, but it is a separate change with its own blast radius across every post.
- The activity feed keys photo permalinks on an FNV32a hash of the gallery `RelPermalink`. It keeps working untouched, and could later point at the real page instead.
- Turning on German and Swedish, once `alt` and `title` are nested as `{en, de, sv}` maps in `data/gallery.yaml`.
- Renaming the 427 camera-code files in the photo store. It is the single highest-value follow-up — it fixes the heading and the URL together — but it is ordinary editorial work, not part of this build.
- `content/gallery/images/` is an empty leftover directory.
