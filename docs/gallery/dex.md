# Photo dex

A Pokédex-style species checklist at `/gallery/dex/`, layered on top of the gallery rather than beside it: which animals the gallery already contains, and which are still open. Ported from the `animal-dex` proof of concept (`../animal-dex`), but restructured to this repo's conventions — central data file + templates, not one page bundle per species.

**Data**: `data/dex.yaml` — one record per species, 154 of them. Language-neutral facts (`slug`, `number`, `scientific`, `family`, `group`, `difficulty`, `iucn`, `gbif_taxon_key`, `inat_taxon_id`, `wikidata_id`, `height`, `height_measure`, `body_weight`, `diet`, `lifespan`) sit at the top level; anything that reads as prose is nested per language under `names` / `description` / `habitat` / `tips.best_time` / `tips.approach` and **falls back to `en`** (via `layouts/partials/dex-text.html`) when a language is missing. `diet` and `height_measure` are slugs translated through i18n, not free text. `height_measure` (`shoulder` | `standing` | `length` | `wingspan` | `shell`) says *which* dimension `height` is, and renders as a translated parenthetical after the value — "35–50 cm (shoulder)" / "(Schulterhöhe)" / "(skulderhöjd)". It is a slug rather than part of the `height` string precisely because that string is language-neutral: an inline English "(shoulder)" would show up untranslated on the German and Swedish pages. The English label for the row is "Size", not "Height", since for the 82 birds and 8 insects the conventional measure is body length or wingspan, not height (German/Swedish already said Größe/Storlek). Every record with a `height` must have a `height_measure`. **`tips` is currently empty on every species** — the six seeded examples from the animal-dex import were removed as generic advice rather than the author's own field experience. The capability is fully intact: `dex-detail.html` renders the field-notes section only when `tips.best_time` or `tips.approach` has content (per-language, English fallback), the `dex_field_notes` / `dex_best_time` / `dex_approach` i18n keys exist in all three languages, and `tips` is still in `FIELD_ORDER`, so adding a block back to any species makes the section reappear with no code change. The section simply renders on no species today. Optional `sightings: [{lat, lng, label, date}]` are hand-entered — only 13 of 633 gallery photos carry GPS EXIF. `description_source: {en, de, sv}` holds the URL of the exact Wikipedia article each description was abridged from (resolved from Wikidata sitelinks by `dex-enrich.py`); the species page needs it to satisfy CC BY-SA attribution. Each language's description comes from that language's *own* Wikipedia — nothing is machine-translated — so the three are independent: 150 of 154 species have Swedish prose, and the remaining 4 (`red-kangaroo`, `european-mouflon`, `european-polecat`, `alpaca`) fall back to the English text *and* the English credit, which `dex-pages.html` resolves together. `habitat`, unlike `description`, is hand-written and only carries `en` / `de`. The `reference` block carries `credit` (display string) plus the structured `artist` / `license` / `license_url` parts that the schema.org `ImageObject` microdata needs — public-domain files have no `license_url`, and the template omits `itemprop="license"` rather than inventing a deed.

**The join**: `data/gallery.yaml` entries gained an optional `species: <Scientific name>` field (e.g. `species: Vulpes vulpes`) matching `scientific:` in `data/dex.yaml`. **A species counts as photographed when at least one gallery entry carries its scientific name** — there is no separate caught/uncaught flag to keep in sync, and archive photos count (they just sort last). 169 of the 179 `category: animals` photos are tagged, covering 46 of the 154 species. The join deliberately runs on the scientific name, not the `slug`: it makes a gallery entry self-describing without a lookup into `dex.yaml`. The `slug` remains the dex identity — URLs, `assets/data/dex/ranges/<slug>.geojson`, `assets/images/dex/reference/<slug>.jpg`, `--only` flags. Matching is case-insensitive (`dex-index.html` and the `species` filter in `collect-images.html` both lowercase both sides); a value naming no dex species produces a build **warning**, not a failure, and those photos simply do not appear in the dex.

**`layouts/partials/dex-index.html`** is the single join point and the thing to reach for in any new dex template. Called via `partialCached`, it returns `{all, bySlug, caught, total, groups}`; each entry carries `slug`, `scientific`, `number`, `group`, `caught`, `species` (the raw record), `photos` (portfolio → current → archive) and `cover`. `collect-images.html` gained matching `Species` / `Section` / `Portfolio` fields and a `species` filter key — pass `.scientific` to it, which is what `dex-pages.html` puts in `filter_species`.

**`layouts/partials/dex-lookup.html`** maps a scientific name → `{slug, name, url}` for the current language, so a gallery photo can link to the species' dex page: the gallery stores the scientific name while the dex page lives at its slug. Deliberately *not* `dex-index.html`, which joins every species against every photo — a caption link does not need that, and `gallery.html` renders on many pages unrelated to the dex. The lightbox info panel (`assets/js/lightbox.js`) reads `.caption-species` (with `data-dex-url`) and `.caption-software` out of the hidden `.pswp-caption-content` span and renders them as the **Species** (linked) and **Edited with** rows; the labels come from the `speciesLabel` / `softwareLabel` i18n keys passed through the JS params in `head.html`. Items in that span carry `data-field` so the popup labels values by field rather than by document order.

**Pages** are generated by a **content adapter**, not by content files: `content/gallery/dex/_content.{en,de,sv}.gotmpl` each call `layouts/partials/dex-pages.html`, which does the `.AddPage` loop. There is one adapter per language because Hugo scopes an adapter to the language of its filename — a bare `_content.gotmpl` only produces pages for English. Species pages set `params.theme: dex-species` plus `filter_species`/`include_archive`, so the photo strip is the ordinary `gallery.html` partial and inherits PhotoSwipe, the like counters and the EXIF captions for free.

**SEO / structured data**: species pages emit `WebPage` + `about: {@type: Taxon}` from `layouts/partials/templates/schema_json.html` (the taxon facts arrive as `dex_scientific` / `dex_family` / `dex_wikidata` page params from the content adapter). They previously fell through to that file's `BlogPosting` branch, which asserted three untrue things on all 558 species pages: the site owner as `author` of Wikipedia's text, that text as his `articleBody`, and `datePublished: 0001-01-01`. **Do not add a cross-domain `rel=canonical` to Wikipedia or Commons** — that would ask Google to de-index these pages in favour of the source. Attribution is a licensing act and belongs in the page body, which is where it is. Duplicate Wikipedia prose is not penalised, it simply will not rank; the pages' only rankable content is the owner's own (photos, `tips`, `sightings`).

**Theme dispatch**: `dex-home` in `layouts/_default/list.html` → `dex-overview.html`; `dex-species` in **both** `page.html` and `single.html` → `dex-detail.html`. The gallery home has a fourth nav card (`dex_cover` param picks its image, else the first tagged animal photo).

**Map** (`dex-map.html` + `assets/js/dex-map.js`): the default view is **entirely local** — Natural Earth land/borders drawn as GeoJSON instead of raster tiles, plus the species' simplified iNaturalist range and any sighting pins. A species page therefore makes **zero third-party requests** on load, which is what makes it usable on the Tor onion build. A "detailed map" button is the explicit opt-in that swaps the drawn world for the site's own basemap (`docs/maps.md`) + the GBIF density overlay, **both through the companion** (`<companion>/api/tiles/gbif/<taxonKey>/{z}/{x}/{y}.png`), so even that mode contacts no third party; it stays an opt-in because MapLibre is ~300 KB and the drawn world is the right default for a range map. The basemap sits in its own `dex-basemap` pane (z 150, under the GBIF tiles); without WebGL2 the drawn world stays under the GBIF overlay. The range polygon stays on top in both modes. Leaflet is already vendored at `/packages/leaflet/` and is loaded per-page from `head.html`, not site-wide.

Three things in that file are load-bearing and easy to break:
- **Every vector layer is drawn at three longitude offsets** (`COPIES = [-360, 0, 360]`). A raster base repeats forever but a GeoJSON world is drawn once, so land, borders, ocean and range must all be duplicated together — duplicating only the range leaves its copies floating over empty sea at the edges of a zoomed-out map. Panning is capped at ±360° so there is always a further copy past the edge, and `worldCopyJump` is **off** (it would snap the view for no gain now that the overlays exist in every copy).
- **Stacking order is pinned by panes**, not by load order: `dex-land` 410 → `dex-range` 420 → `dex-ocean` 430 → `dex-lines` 440. These are independent fetches that finish in any order, and a shared renderer paints as layers arrive — which once put the range *underneath* the land, visible only over the sea.
- **The ocean layer is a mask.** iNaturalist's geomodel is a thresholded prediction raster, so a widespread terrestrial species' polygon genuinely covers open water (wild boar contains the north Pacific in the raw source data — this is not a simplification artifact). Repainting the ocean over the range clips it to the coastline. Species with `marine: true` in `data/dex.yaml` skip that layer, or whales, seals, sea turtles and penguins would be masked down to nothing — 17 species carry the flag. In detailed mode the mask is painted in the basemap flavor's water colour (`waterColor()`), and follows a theme switch.

**Committed assets** (unlike gallery photos, these *are* in git): `assets/data/dex/world-{land,borders}.geojson` (Natural Earth, public domain, ~215 KB), `assets/data/dex/ranges/<slug>.geojson` (iNaturalist, CC BY 4.0, 150 species, ~4.5 MB — simplified and coordinate-rounded to fit a 45 KB per-species budget), and `assets/images/dex/reference/<slug>.jpg` (Wikimedia Commons stand-ins, 108 files / ~21 MB, fetched only for species with no photo of the user's own, always rendered dimmed and credited). These are fetched at `--width 900`, which Commons delivers as ~960px — deliberately matching the `fill 900x900` a real hero photo gets, because the hero slot is only 300–320 CSS px and a 320px stand-in looked visibly softer than the owner's own photos on any HiDPI screen. Commons snaps thumbnail widths **up** to cached buckets (~500 / 960 / 1280 for these files), so 900 and 500 are the only two settings worth using. `dex-detail.html` caps the render at `min(width, height, 900)` so a low-resolution stand-in is never upscaled — a square `fill` is limited by the *shorter* side, and most Commons photos are landscape, so 73 of the 108 land in the 640–899 band rather than at a full 900.

**Scripts** (stdlib only, sharing `scripts/dex_common.py` for the YAML reader/writer): `dex-import.py` (one-shot animal-dex import), `dex-add.py` (add one species by hand, auto-numbered), `dex-tag-photos.py` (propose `species:` for gallery photos; carries a `MANUAL` table of visually identified files and refuses to guess), `dex-enrich.py` (fill *empty* fields only, from GBIF/Wikidata/Wikipedia), `dex-ranges.py`, `dex-covers.py`, `dex-renumber.py` (close gaps in `number` after a removal; preserves the existing order). Full workflow below. Styles are `assets/css/extended/dex.css`; i18n lives under the `# Photo dex` block in `i18n/{en,de,sv}.yaml`.

## Working on the photo dex

The dex at `/gallery/dex/` is a Pokédex-style checklist of animal species: which
ones the photo gallery already contains, and which are still open. The data model is
above. All seven scripts are
standard-library only and edit `data/dex.yaml` through the shared reader/writer
in `scripts/dex_common.py`, so field order and quoting stay stable and the git
diff only shows what actually changed.

### The scripts, in the order they are normally used

| Script | Owns | Rerunnable |
|---|---|---|
| `dex-import.py` | one-shot import of the `animal-dex` proof of concept | yes, only adds missing species |
| `dex-add.py` | adding one species by hand | yes |
| `dex-tag-photos.py` | the `species:` field in `data/gallery.yaml` | yes, never retags |
| `dex-enrich.py` | the empty fields of `data/dex.yaml` | yes, never overwrites |
| `dex-ranges.py` | `assets/data/dex/**` | yes, `--force` to refetch |
| `dex-covers.py` | `assets/images/dex/reference/**` + `reference.*` | yes, `--force` to refetch |
| `dex-renumber.py` | the `number` field — closes gaps after a removal | yes, idempotent |

### Adding a species you just photographed

1. **Add the photo** to the gallery the normal way (drop it in the photo store,
   then `python3 scripts/sync-gallery.py` and fill in the stub entry).

2. **Make sure the species exists** in `data/dex.yaml`:
   ```
   python3 scripts/dex-add.py "Sand Lizard" --scientific "Lacerta agilis" \
       --family Lacertidae --difficulty moderate
   ```
   The dex number is assigned automatically. Skip this if the species is
   already listed — the script tells you and does nothing.

3. **Tag the photo.** Either add `species: <Scientific name>` under the entry's
   `category:` line by hand (`species: Lacerta agilis` — the scientific name, not
   the slug, and it must match `scientific:` in `data/dex.yaml`), or let the
   tagger propose it:
   ```
   python3 scripts/dex-tag-photos.py --dry-run
   python3 scripts/dex-tag-photos.py --write
   ```
   The tagger only ever fills in entries that have no `species:` yet, so it is
   safe to rerun. Its `MANUAL`/`ALIASES` tables are keyed by slug because that is
   what is readable to write by hand; it resolves the slug to the scientific name
   as it writes. Photos it cannot identify are listed and left alone — an
   untagged photo is a normal gallery photo, it just is not in the dex. A
   `species:` value that matches no dex species logs a build warning and drops
   those photos from the dex; the build still succeeds.

4. **Fill in the facts** (only touches empty fields):
   ```
   python3 scripts/dex-enrich.py --only sand-lizard
   ```
   **Check `body_weight`, `height` and `lifespan` by hand afterwards — do not
   trust them.** A full audit of all 186 species then in the dex (August 2026; 34 were
   removed afterwards) found 82 of the 83 `body_weight` values this script had
   produced were wrong, several by three
   to six orders of magnitude (whale shark `12`, humpback `1.5–45` with no unit,
   giant panda `104–117.5 g`, common buzzard `0.9–966.5 kg`, giraffe `54.5 kg`).
   The cause is `quantity_range()` in `scripts/dex-enrich.py`: it takes
   `min()`/`max()` across *every* Wikidata mass statement for the taxon while
   ignoring the qualifiers that distinguish them, so a newborn's mass becomes the
   low end and a record specimen the high end; it also silently discards any
   value whose unit QID is missing from the 5-entry `UNIT_MAP` (pounds, tonnes),
   leaving an incoherent partial set. `lifespan` has the same shape of problem —
   it tends to land on the record-longevity figure rather than the typical adult
   range. The audit also established the house conventions those fields follow:
   en-dash ranges, `mm`/`cm`/`m` and `g`/`kg`/`t`, a bare year range for
   `lifespan`, and a `height_measure` slug on every record that has a `height`.

   Also note two rules the script cannot know: a **domesticated form has no IUCN
   assessment**, so `iucn` must be absent on dog/cat/cattle/sheep/goat/chicken/
   domestic duck/alpaca rather than carrying the wild ancestor's category, and a
   **Europe-only regional assessment is not a global one** (the honeybee and
   carder bee had regional categories that had to be removed). Both rules are now
   held by the `PROTECTED` table at the top of `scripts/dex-enrich.py`: "fill only
   what is empty" cannot tell a never-populated field from a deliberately emptied
   one, so a rerun used to put those twelve `iucn` values straight back. **If you
   ever correct a field by clearing it, add it to `PROTECTED`** or the next run
   undoes you.

5. **Fetch its map and, if you have not photographed it, its stand-in photo:**
   ```
   python3 scripts/dex-ranges.py --only sand-lizard
   python3 scripts/dex-covers.py --only sand-lizard
   ```

6. **Check the build**: `hugo` should succeed and the species should appear at
   `/en/gallery/dex/sand-lizard/`.

Do **not** run `./deploy.sh` — deployment is a separate step the user authorizes
explicitly.

### Removing a species

Nothing automates this, and the order matters:

1. **Check it is not photographed first.** A species counts as photographed when a
   `data/gallery.yaml` entry carries its scientific name. Removing a dex entry that
   photos still point at leaves those photos referencing nothing — the build warns
   but does not fail, and they silently drop out of the dex:
   ```
   grep -c "^  species: <Scientific name>$" data/gallery.yaml
   ```
   If it is non-zero, retag or keep the species; do not remove it.

2. **Delete the record** from `data/dex.yaml` (match on `slug`).

3. **Delete the assets it owned**, or they become orphans nothing renders:
   ```
   rm -f assets/data/dex/ranges/<slug>.geojson
   rm -f assets/images/dex/reference/<slug>.jpg
   ```

4. **Close the numbering gap** it left behind:
   ```
   python3 scripts/dex-renumber.py --dry-run
   python3 scripts/dex-renumber.py --write
   ```
   `number` is both the badge and the grid's only sort key, so holes read as
   missing entries. The renumber preserves the existing order and only closes the
   holes. It does shift numbers, which is safe: `number` appears in the two badges
   and that one sort, never in a URL, a deep link, or the likes API.

5. **Update the counts** in this file (species total, range/reference file counts,
   `marine: true` count) and rebuild.

### What the scripts deliberately leave for a human

- **Species identification.** `dex-tag-photos.py` matches alt text, tags and
  filenames against the dex names, and carries a `MANUAL` table of photos that
  were identified by eye. It will not guess: a gull that could be two species
  stays untagged.
- **`difficulty`** — how hard the animal is to photograph is a judgement call,
  so `dex-add.py` defaults it to `moderate`.
- **`tips.best_time` / `tips.approach`** — the field notes are yours to write;
  nothing generates them.
- **`sightings`** — where you actually saw it. Only 13 of the gallery photos
  carry GPS EXIF, so these coordinates are hand-entered.
- **Habitat prose, in every language.** `dex-enrich.py` fills `description` in
  all three languages — each one abridged from that language's *own* Wikipedia
  article via the Wikidata sitelink, so nothing is machine-translated — but
  `habitat` is hand-written and only ever carries `en` and `de`. Where a language
  has no article (4 species have no `svwiki` sitelink, and the sv summary for
  `european-polecat` is a 28-character stub the script's 50-character floor
  rejects), the page falls back to English and credits the English article.

### If a species' range looks wrong on the map

Work through it in this order — the first two are rendering, the third is the data.

1. **Green floating in open ocean at the left/right edge, mirroring a landmass.**
   That is the ±360° copies showing without a base map under them. Every vector
   layer must be duplicated together; see the map notes above.
2. **Green everywhere *except* on land.** The range is painting under the land
   instead of over it — check the pane z-indexes in `assets/js/dex-map.js`.
3. **Green spilling a few hundred km out from the coast, or across a whole sea.**
   That is the source data, not the pipeline: iNaturalist's geomodel is a coarse
   thresholded prediction and genuinely includes water for widespread species.
   The ocean mask hides it for terrestrial species. If a *marine* species looks
   wrong, check its `marine: true` flag — without it the mask erases its range.
4. **A wrong animal's range entirely.** Check `inat_taxon_id`. `dex-enrich.py`
   resolves it by name and falls back to iNaturalist's first search hit, which
   can silently attach the wrong taxon. Fix the id by hand, then
   `python3 scripts/dex-ranges.py --only <slug> --force`.
5. **Scattered fragments where the animal is actually widespread.** The geomodel
   itself is thin for that species — nothing downstream can recover it. Compare
   against its peers with `python3 scripts/dex-ranges.py --audit`, which lists
   the area every stored range covers. Red fox is the known case: 608 sq deg
   against 7,748 for grey wolf and 25,189 for wild boar, and it renders as
   coastal fringes. Small numbers are not automatically wrong — the Galapagos
   giant tortoise is legitimately 3 sq deg.

Note that the ocean mask makes simplification much less visible — coarsened
outlines mostly get clipped away at the coast — so raising `--max-kb` buys less
than it looks like it should.

### Sizes to keep an eye on

`dex-ranges.py` simplifies the iNaturalist polygons until each fits `--max-kb`
(45 KB), coarsening a wide-ranging species rather than dropping its map. The
whole set is ~4.2 MB. `dex-covers.py` fetches ~960px Commons thumbnails (`--width 900`; see that script's docstring for why, and why Commons ignores widths in between) and, by
default, only for species you have *not* photographed — the rest show your own
photo, so a stand-in for them would be bytes nothing renders.

### Audits: what the enrichment gets wrong

- **`dex-enrich.py`'s numbers cannot be trusted.** An audit of every species on
  2026-08-19 found 82 of the 83 `body_weight` values it had produced wrong, several
  by three to six orders of magnitude (whale shark `12` with no unit, giant panda
  `104–117.5 g`, jaguar `800 g`). `quantity_range()` takes the min and max across
  *every* Wikidata mass statement while ignoring the qualifiers that tell them
  apart, so a newborn becomes the low end and a record specimen the high end, and
  values whose unit is missing from the five-entry `UNIT_MAP` (pounds, tonnes) are
  dropped silently. `lifespan` fails the same way and lands on record longevity.
  The script only fills *empty* fields, so audited data is safe — but a new species
  gets garbage again. **After every run, check `body_weight`, `height` and
  `lifespan` by hand against a real source.** House conventions from that audit:
  en-dash ranges; `mm`/`cm`/`m` and `g`/`kg`/`t`; a bare year range for `lifespan`;
  a `height_measure` on every record with a `height`; domesticated species carry
  **no** `iucn` (never the wild ancestor's), and a Europe-only regional assessment
  is not a global one.
- **Verify `inat_taxon_id`s in bulk; don't eyeball maps.** The same audit found 17
  of 184 ids mismatched, 11 of them flatly wrong (`wolverine` pointed at the
  goosander, a duck; `eurasian-lynx` at the lynx *spiders*). Two silent failure
  modes: an id at family, order or class rank — iNaturalist publishes ranges only
  at species rank, so the species just has no range layer — and an id that
  resolves to the wrong species, which writes the wrong animal's range. The check:
  the iNaturalist API takes batched ids (`/v1/taxa/<id1>,<id2>,…`, 30 per call);
  compare `name` with `scientific` and require `rank == "species"`. Then
  `md5sum assets/data/dex/ranges/*.geojson | sort | uniq -w32 -D` — any duplicate
  pair means two species share one taxon id. GBIF keys and Wikidata ids were
  almost all fine. Legitimately without a range: domesticated species and
  subspecies records (`bengal-tiger`, `grizzly-bear`, `mountain-gorilla`,
  `european-mouflon`).
