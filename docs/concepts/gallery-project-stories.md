# Concept: project pages that tell a story — "essay" and "journal"

**Status:** implemented 2026-10-12, build order §11 complete; where the code departs from this text, §13 says so. Derived from an external brief (`SPEC.md` plus three static mockups, `essay-desktop.html`, `essay-mobile.html`, `journal-desktop.html`, handed over on 2026-10-06; the three mockups lie in the gitignored `.inbox/`, not in git). That brief was written from the rendered site only. This document is its translation onto the code: §1 answers the brief's "Phase 0" questions, and the *Deviations* table lists every place the brief and the repo disagree. The page-`Store` mechanics in §4 were checked on a scratch site with Hugo 0.166.0, `hugo` and `hugo server` both.
**Updated 2026-10-12:** decided by the owner: `grid` stays a third layout, unplaced photos, shortcode names, the map (the site's own basemap, with mini maps), the real projects stay `grid` and the feature is shown on unlisted demo projects (§3.1), and the three areas. §8 rewritten for that basemap (`self-hosted-maps.md`), which every map now draws from the companion. Implemented on the owner's "go" the same day; nothing committed or pushed.
**Read against:** the working tree of 2026-10-06 (`c2eb7f8`), Hugo 0.166.0, 661 photos in the gallery manifest.

A gallery project at `/<lang>/gallery/projects/<slug>/` is today a title, one sentence and the photo grid. The page body is not even rendered: the `gallery-project` branch in `page.html` / `single.html` prints breadcrumb, title and `gallery.html`, and nothing else. This concept lets a project opt into one of two layouts that carry the owner's own text and still show every photo of the project:

- **Essay**: one continuous story, optionally in chapters, with photo blocks between the paragraphs. It suits a project with a theme (*Above the Clouds*).
- **Journal**: a timeline of outings. Each outing is one capture day, built automatically from EXIF. There is text only where the owner writes some. It suits a project that grows over years (*The wildlife of the Inn-Valley*).

Today's page stays a third choice: `project_layout: grid`, or no key at all, looks exactly as it does today. Both new layouts keep the grid one click away.

## Settled decisions

| | |
|---|---|
| Switch | `params.project_layout: grid \| essay \| journal` in the project's front matter, per language file. `grid` is today's page, byte for byte, and a missing key means `grid`, so no existing project needs an edit. Any other value is an `errorf`. `theme` stays `gallery-project` (owner, 2026-10-12; §3) |
| Photo reference | The photo's **UUID** from `data/gallery.yaml`, as `galleryImage` does. Never a slug (§3) |
| Completeness | Every project photo appears **exactly once** in the story view, the hero included. Recorded through `.Page.Store` with `SetInMap` keyed by shortcode ordinal (§4) |
| Unknown, foreign or duplicate id | Hard build error (`errorf`), naming the page and the id |
| Unplaced photo in an essay | Shown at the end under "More from this project", as a thumbnail grid. **No warning**: that block is where such photos are meant to go, so an essay that leaves some to it is not a mistake to stop a deploy over (owner, 2026-10-12; §4) |
| Outings | One per **capture day** (`DateTaken`). Undated photos form a last group, "Undated". `{{< outing >}}` blocks only enrich a day, they never create one |
| Journal order | The **existing `sort_order`** front-matter key, which every project already sets to `desc`: newest first. No new `order:` key |
| Areas | A new `data/galleryAreas.yaml`, language-neutral, referenced by slug. **At most 2 decimal places and a radius of at least 1,000 m**, enforced by the build. Never a photo's GPS (§8) |
| Grid view | The existing `gallery.html`, unchanged, lightbox and like counts included |
| Story images | Link to the photo page, like the grid's `href`. **No PhotoSwipe in the story view** in v1: `lightbox.js` is bound to one `#gallery` |
| Widths | Text column `--main-width` (720px), wide blocks `--nav-width` (1060px). Not the brief's 680 / 1040 |
| Colours | PaperMod's variables, plus a new `--accent`: `#d8a657` dark, `#8a5a00` light |
| Font | The site's own Cantarell. No serif in v1 |
| Missing text | `{{< todo "…" >}}`: a visible placeholder under `hugo server`, a `warnf` in every production build (§5.7) |
| Map | The site's own basemap from the companion, through `basemap.js`: one overview map per page plus a **mini map beside every outing with text and an area**. Each map is built when it nears the viewport, with no button. Only a few mini maps are alive at once; one leaving the viewport is removed again. Zoom capped at 13. The area list is the fallback without JS or WebGL2. No static SVG (owner, 2026-10-12; §8) |
| Real projects | **Not switched.** Inn-Valley, *Above the Clouds* and the Nicklheim album stay `grid`. The feature is shown and tested on four unlisted demo projects that the owner deletes when done (owner, 2026-10-12; §3.1) |
| URLs | None new. `#grid` and the chapter anchors are fragments, so `tests/golden/published-urls.txt` does not change |

Some of these points I set myself rather than took from the brief. Each is a line to change:
- No lightbox in the story view.
- Reusing `sort_order` for the journal.
- `errorf` instead of the brief's warning for a duplicate or foreign id.
- The site's widths instead of the brief's.
- The `todo` shortcode.
- One map marker per area in the journal, not one per outing (§8).
- Only the hero and thumbnails are cropped (§5.5).
- The four demos and their text (§3.1).
- The mini maps' limits: four alive, built within half a viewport, removed beyond two (§8).
- The shortcode names (§3). The owner left them to me on 2026-10-12; a rename stays a search-and-replace.

## Decisions still open

| | |
|---|---|
| — | None. Implemented 2026-10-12 (§13); nothing committed or pushed by me |

## Deviations from the brief

| The brief says | Here | Why |
|---|---|---|
| `projectLayout:`, or Hugo's own `layout` field | `params.project_layout` | Single pages dispatch on `params.theme` in `page.html` *and* `single.html` (Hugo 0.146+ template system). `head.html`, `schema_json.html`, `get-page-images.html` and `newsletter-in-footer.html` all key on `theme: gallery-project`. Hugo's `layout` would bypass that, and a new theme value would have to be added in five places. A param keeps all five working |
| `id` is a slug or UUID, whichever is stable | UUID | The slug is **per language** and **moves when the English title is reworded**. A German essay would need German slugs. The brief's examples (`heavy-early-mornings`) are not even real slugs: the real one is `heavy-early-mornings-white-tailed-eagle-skimming-a-fog-covered-bog-lake` |
| `areas:` in the front matter | `data/galleryAreas.yaml` | Coordinates are language-neutral and would be copied into three files. The bog belongs to two projects. Only one place can check the "coarse" rule. The repository is public, so the rule must hold for the data, not just for the HTML |
| Duplicate or foreign id → warning | `errorf` | Both are always an editing mistake. Precedent: an unknown `galleryImage` id and an unknown `model:` slug are hard errors |
| An essay with unplaced photos "builds anyway, with a warning" | It builds, with no warning | The photos are shown at the end anyway. Here a warning is not a note: every `WARN` fails the `build` test project, and `deploy.sh` builds with `--panicOnWarning` |
| The map loads on click | It loads when it nears the viewport, with no button | The click was the opt-in to a third party's tiles. The tiles now come from the companion, and `{{< map >}}` and the trips load theirs without one. What is left to save is MapLibre's ~300 KB, and a map nobody scrolls to never loads it (§8) |
| Dots on the map: one per outing (journal), loose ones for a chapter without an area (essay) | One circle per area, with a count. No area, no place on the map | A dot per outing needs a position per outing, which only the photos' GPS could give, and spreading dots by hand invents positions that read as real ones (§8, rules 1 and 4) |
| `order: newest \| oldest` | `sort_order: desc \| asc` | It already exists on every project and means the same thing for the grid |
| Text column 680px, wide 1040px | 720px / 1060px | `--main-width` and `navbar.css`'s `--nav-width`, so the essay lines up with every other page |
| EXIF as `600 mm`, `1/1250 s` | The strings `collect-images.html` already produces | Lightbox and photo page print them. A second formatter would drift. Changing the spacing is a separate edit to the collector, for every surface at once |
| The mockups load Source Serif 4 from Google Fonts | No third-party font | The Tor build and the dex map's zero-third-party rule. The site's font is self-hosted (`static/fonts/`). Note that the mockups load the serif without using it: every paragraph is set in the system sans |
| A visible `TODO` in the Markdown | `{{< todo >}}` | A literal TODO would be deployed. The shortcode makes a missing text a deploy gate instead, which is how a missing photo title already works |
| Journal outings as `h3` (mockup) | `h2` | The brief's own rule: one `h1`, chapters or outings `h2`, blocks inside them `h3` |
| The essay mockup uses *Inn-Valley* with three chapters and two areas, the journal mockup too | Both become **demo projects** over Inn-Valley's photos (§3.1). No real project is switched | The owner's call: see the feature and test it without changing a published page. It also gives chapters and areas a first user, which neither real project would have had |
| "Wait for an okay after every phase" | One build order (§11) | The concept is the Phase 0 report. The build order is executed end to end after "go", like every concept here |

---

## 1. What the repo already has (the brief's Phase 0)

| Brief's question | Answer |
|---|---|
| Hugo version, theme, overrides | Hugo **0.166.0** extended. PaperMod is a **Hugo Module** (`go.mod`), not a fork and not a submodule. It is overridden by files in the project's own `layouts/`. Single pages dispatch on `params.theme` in **both** `layouts/_default/page.html` and `single.html` |
| Photo data model | Editorial data lives in **`data/gallery.yaml`**: `id` (UUID), `src`, `title`/`alt`/`description` (string or `{en,de,sv}`, English fallback), `species` (scientific name), `project`, `license` (key into `licenseMap.yaml`), `artist`, `tags`. Technical data is **EXIF read at build time** by `collect-images.html`: `DateTaken`, `FocalLength`, `Aperture`, `ShutterSpeed`, `ISO`, `CameraModel`, `LensModel`, `Software`. **No GPS field exists** in the collector, and the served files are stripped of GPS by `gallery-embed-metadata.py`. Photo pages at `/<lang>/gallery/photo/<slug>/` come from the content adapters under `content/gallery/photo/` (`gallery-photo-pages.html`). The slug is per language, derived from the title, and `/gallery/photo/<uuid>/` is a permanent alias |
| Project → photos | `project:` on the **photo** (string or list), normalised to `.projects` in `gallery-meta.html`. The project page names itself with `params.project_slug`, and `collect-images.html`'s `project` filter does the join. "Appears in" (`gallery-photo.html`) lists the albums the projects index lists |
| Dex | `data/dex.yaml`, 154 species, with `scientific`, per-language `names` and `slug`. A photo joins a species through its scientific name. Pages come from content adapters. **`dex-lookup.html`** maps scientific name → `{slug, name, url}` cheaply. **`dex-index.html`** is the full join (photo counts, archive included) |
| Grid, lightbox, anchors | `gallery.html`: `fit 600x600` thumbnails, `fit 4000x4000` for PhotoSwipe, `data-id` = UUID, `href` = the photo page. `assets/js/lightbox.js` binds to the single `#gallery` and opens `#<uuid>` from the URL hash. The photo page's "View in gallery" links to its parent grid with `#<uuid>` |
| Translations | Per-language files: `index.<lang>.md` for these leaf bundles, paired by path. Generated pages use a **top-level** `translationKey`. UI strings live in `i18n/{en,de,sv}.yaml` |
| CSS, JS, CSP | `assets/css/extended/*.css` is auto-bundled by PaperMod. Page-specific JS is loaded from `head.html`, keyed on the theme. Leaflet is vendored at `/packages/leaflet/`. Template values reach JS through `data-*` attributes, never through an inline `<script>` (`dex-map.html`). **Neither `nginx.conf` sets a CSP today.** Inline `style=` attributes are already in use (`gallery.html`) |

Two more facts the brief could not see:
- `assets/css/extended/project.css` belongs to the **software** projects page. The new stylesheet needs a different name (§5.6).
- The mockups' colours are PaperMod's dark tokens exactly:

  | Mockup colour | PaperMod token |
  |---|---|
  | `#1d1e20` | `--theme` |
  | `#2e2e33` | `--entry` |
  | `#dadadb` | `--primary` |
  | `#9b9c9d` | `--secondary` |
  | `#414244` | `--tertiary` |
  | `#c4c4c5` | `--content` |
  | `#333333` | `--border` |

  The only colour PaperMod does not have is the accent.

## 2. What the data says

| | Inn-Valley | Above the Clouds | Nicklheim (unlisted) |
|---|---:|---:|---:|
| Photos | 28 | 8 | 15 |
| Capture days | 9 | 2 | 4 |
| Undated | 0 | **3** | 0 |
| Species (all in the dex) | 13 | 0 | 7 |
| Portfolio | 7 | 0 | — |
| Without alt text | 0 | 0 | — |

Inn-Valley's days, newest first: 2026-09-12 (2), **2026-08-09 (12)**, 2026-06-13 (1), 2026-04-25 (1), 2025-06-08 (4), 2025-06-01 (3), 2025-05-31 (2), 2023-10-06 (1), 2022-07-27 (2). That is exactly the brief's "28 photos from 9 outings and 13 species, July 2022 to September 2026".

What the numbers fix for the design:
- A journal **with no `outing` block at all** is already a complete page of nine compact entries, so a real project can be switched later without its text written first. 8 of its 9 days have one to four photos, so most entries stay compact or medium even once text exists. Only the bog morning is a "full" entry.
- *Above the Clouds*' photos exercise the edge cases the brief names, which is why two demos use them (§3.1): three undated photos, so the period line covers only the dated ones ("2022"), and zero species, so the species count is **left out**, not printed as "0 species".
- The 12 photos of 2026-08-09 are also the unlisted Nicklheim album. Nothing here changes that album.

## 3. Switching a project, and what the author writes

```yaml
# content/gallery/projects/above-the-clouds/index.en.md (and .de, .sv)
params:
  theme: gallery-project            # unchanged
  project_slug: above-the-clouds
  featured_image: 1cd410f4-…        # the hero, as today
  project_layout: essay             # new: grid | essay | journal; missing → grid
  areas: [nicklheimer-filzen]       # optional; slugs into data/galleryAreas.yaml
```

- **Per language file**, like everything else in a project's front matter. A language whose file says `grid`, or lacks the key, keeps the grid. That is what a translation looks like before its text exists, and the page body does **not** fall back to English: the shortcodes would print English prose on a German page, and posts do not fall back either.
- The dispatch is one `if` inside the existing `gallery-project` branch of `page.html` and `single.html` → `layouts/partials/gallery-story.html`, which branches on `essay` / `journal`. `grid` and a missing key take today's path unchanged. An unknown value is an `errorf`.

Shortcodes, all taking **UUIDs**:

| Shortcode | Purpose |
|---|---|
| `{{< chapter title="…" subtitle="…" area="…" >}}…{{< /chapter >}}` | Essay chapter. Numbered automatically |
| `{{< storyPhoto id="…" layout="full\|wide\|left\|right" caption="…" >}}` | One photo. With `left`/`right`, the inner Markdown is the text beside it, rendered like `galleryImageText`'s |
| `{{< storyPhotos ids="…, …" layout="pair\|trio\|grid\|sequence" title="…" note="…" >}}` | Several photos |
| `{{< storySpecies id="osprey" >}}` | Species card. `id` is the **dex slug**, the dex's own identity |
| `{{< outing date="2026-08-09" title="…" area="…" lead="<uuid>" size="full\|medium\|compact" >}}…{{< /outing >}}` | Journal: enriches one day |
| `{{< todo "Why this project exists" >}}` | Placeholder (§5.7) |

The `story` prefix says the shortcodes work only on a project page. Each one `errorf`s anywhere else, because it needs the project to check membership against. `galleryImage` / `galleryImageText` stay the shortcodes for posts. Those were built for the 720px post column, with captions off and the link pointing at the general grid, and widening them with a `layout=` that means something else on a different kind of page would make them harder to read.

UUIDs are unreadable when writing. The cheap fix is a stdlib `scripts/project-photos.py <slug>`. It prints the project's photos grouped by capture day, each with UUID, title and species, ready to paste. It writes nothing.

```yaml
# data/galleryAreas.yaml — public in git, like every data file; see §8
- slug: nicklheimer-filzen
  label: { en: "Bog", de: "Moor", sv: "Mosse" }   # or a bare string = English
  lat: 47.90
  lng: 12.20
  radius: 2000          # metres
```

### 3.1 Demo projects

The real projects are **not switched**. *The wildlife of the Inn-Valley*, *Above the Clouds* and the Nicklheim album stay `grid` (owner, 2026-10-12). The feature is shown and tested on four demo projects, which the owner deletes again when they have served their purpose.

- **Ordinary project bundles**, `content/gallery/projects/demo-<name>/index.{en,de,sv}.md`, with `theme: gallery-project` and a `project_layout` like any project. No adapter, no switch in the build. Deleting a demo means deleting its folder.
- **Their photos are the real projects'.** A demo sets `project_slug` to an existing project, so its photos are that project's, and `data/gallery.yaml` is not touched. Nothing looks a project page up by `project_slug`: the param is only ever a filter (`gallery.html`, `get-gallery.html`, `head.html`). "Appears in" on a photo page finds albums by path (`site.GetPage "/gallery/projects/<slug>"`), so a demo never shows up there, and `data-output.spec.ts` only checks that a photo's slug names a folder.
- **Unlisted, so deleting them costs nothing.** `build: {list: never, render: always}` plus `robotsNoIndex: true`, the Nicklheim album's pattern. A demo is then in no list, sitemap, feed or search, and therefore never in `tests/golden/published-urls.txt`. A listed demo would enter that list, and removing it would then need a redirect. They are in every build, a deploy included: deployed before they are deleted, they are reachable by URL and nothing else. "Next project" on a demo page starts at the first listed project, because the demo itself is not in that list.
- **No demo flag, no `todo`.** A demo is an ordinary project and nothing marks it as one (owner, 2026-10-12). So it carries no `todo` either: every `todo` warns in a production build, which would fail the build test and stop a deploy for as long as the demos exist. `todo` is checked by hand like the other warning paths (§10).
- **Text.** Written by me in en/de/sv, from what the photos' titles and descriptions already say and nothing more.
- **Areas** (confirmed by the owner, 2026-10-12): the Nicklheimer Filzen, the Riesenkopf and the Inn valley floor near Rosenheim, at 2 decimals, chosen as named public places and never from a photo's GPS. They stay in `data/galleryAreas.yaml` when the demos go.
- **Cost.** The story-size variants of 36 photos join every build and pass through `gallery-embed-metadata.py` once. If that ever reaches the resource-cache ceiling (`duplicate-target-paths.md`), the build test reports it as `Duplicate target paths`.

| Demo | Photos of | Shows |
|---|---|---|
| `demo-essay` | Inn-Valley (28) | The essay mockup: hero, three chapters, two areas, every block (`full`, `wide`, `left`, `right`, `pair`, `trio`, `grid`, `sequence`), a `storySpecies` card, chapter species chips, the overview map with chapter chips. A few photos are left out on purpose for "More from this project" |
| `demo-journal` | Inn-Valley (28) | The journal mockup: intro, header map with counts, species index. `outing` text on seven of the nine days, five of them with an area, so scrolling reaches the limit of four live mini maps. Full and medium entries, each with and without an area, and two compact days |
| `demo-essay-minimal` | *Above the Clouds* (8) | No chapters, no areas, no map. Three undated photos (period "2022"), zero species (no count), and most photos unplaced, so a large "More" block |
| `demo-journal-minimal` | *Above the Clouds* (8) | No text at all: two days and the "Undated" group, with compact titles taken from the photo titles (no species) |

## 4. Completeness: how a page knows which photos it placed

The rule "every photo exactly once" needs the layout to know, after the body has rendered, which photos the shortcodes placed. Hugo's page `Store` carries that information, but the obvious way of using it is broken. On the scratch site:

| Scenario | `.Store.Add "placed" (slice $id)` | `.Store.SetInMap "placed" <ordinal key> $id` |
|---|---|---|
| `hugo` build, JSON output also calling `.Plain` | `[a b a]`: correct, not doubled | correct |
| `hugo server`, after a **content** edit | correct: the page is recreated | correct |
| `hugo server`, after a **template-only** edit | **`[a b a a b a]`**: the Store survives and every photo looks duplicated | correct: same content, same keys |

So:
- Every photo shortcode records into a **map keyed by its position**: `printf "%03d" .Ordinal`, prefixed with `.Parent.Ordinal` when nested (`001.002`), plus `/n` for the n-th id of a `storyPhotos`. `.Position` cannot serve as the key: for a nested shortcode it reports `1:1`. `.Ordinal` is relative to the parent, hence the prefix.
- The layout calls **`.Content` first**, into a variable, and only then reads the Store.
- A **chapter** reads its own children: nested shortcodes render before the parent's template runs (verified), so after `.Inner` the chapter sees the keys under its own prefix. From those it computes its photo count, its date or period, and its species chips. It numbers itself by counting the `chapters` entries with a smaller key (verified in source order).
- A **duplicate** is two keys with the same id. A **foreign** id is a UUID in `data/gallery.yaml` whose `.projects` does not contain this project. An **unknown** id is in neither. All three are `errorf`.
- **Unplaced** = project photos − hero − every recorded id.
  - In an essay they go to the "More from this project" block at the end. No warning: that block is their intended place, not a fallback.
  - In a journal nothing is ever unplaced. The timeline is built from the photos, and the shortcodes only add text to days.
- **Journal text**: an `outing` renders nothing inline. It stores `{title, area, lead, size, html}` under its date (`SetInMap`, idempotent). The body's remaining output is therefore exactly the intro. Two blocks for one date are an `errorf`, and a date with no photo is a `warnf`.

## 5. Shared building blocks

### 5.1 Data partial

`layouts/partials/gallery-story-data.html`, `partialCached` per page and language. It calls `collect-images.html` once with `project: <slug>` and returns:
- `photos`, `byId`,
- `days` (ordered by `sort_order`; `Undated` last),
- `species` (scientific name → `{name, url, count}` via `dex-lookup.html`),
- `period` (first and last dated month),
- `count`.

Everything a page counts comes from here, and nothing is maintained by hand.

### 5.2 Captions

- **Large images** carry a caption. On the left is the title, linked to the photo page (same `$photoBase` + `.Slug` as `gallery.html`), optionally followed by the shortcode's `caption`. On the right are `FocalLength · Aperture · ShutterSpeed · ISO`, as far as they exist.
- **Thumbnails** carry the title as a small label inside the image.
- **Alt text** is always the photo's `.Alt`, from `data/gallery.yaml`, in the page's language. No shortcode takes an `alt`.
- Story figures emit **no `ImageObject` microdata**. The grid below already does, for every photo, and two entities for one image is the contradiction `gallery.html` once had to remove.

### 5.3 Species

- Chips and cards link to the dex page through `dex-lookup.html`.
- A species missing from the dex prints as plain text, the lookup's own rule. Today all 13 are in it.
- Counts:
  - Inside a chapter, the species chips count photos in that chapter.
  - In the journal header, the species index counts photos in the project.
  - On `storySpecies`, the card counts photos in the dex (`dex-index.html`, archive included, like the dex page itself).

### 5.4 Story / Grid toggle

- Two real `<button>`s with `aria-pressed`, inside a labelled group, top right next to the breadcrumb.
- The state lives in the hash: `#grid` shows the grid. A hash that is a **UUID** also switches to the grid, so the lightbox's `openFromHash` lands on a visible item.
- **Without JS** the buttons render `hidden`, the pattern `game-achievements.html` uses so a no-JS visitor never meets a dead control. The grid then simply follows the story, with `id="grid"`, so "Show as grid" is a working anchor in both cases.
- The grid's thumbnails are lazy. Hidden behind `display: none`, they are not fetched at all.
- JS: `assets/js/gallery-story.js`, loaded from `head.html` only when `project_layout` is `essay` or `journal`. Lightbox and `main.scss` keep loading as they do now, because the theme is still `gallery-project`.

### 5.5 Images

- Reuse the `galleryImage` ladder from `gallery-image-figure.html` (`fit` 480/720/1080/1440, height bound 10× the width, never upscaled, `AutoOrient` first). Thumbnails reuse the grid's `fit 600x600`.
- Only `full` and the hero add a **2048** step. That is one new file per photo that uses it, and each new file passes once through `gallery-embed-metadata.py`. For the 36 photos in question the cost is negligible.
- `sizes` follows the block: 100vw for `full`, `--nav-width` for `wide`, `min(600px, 100vw)` for `left`/`right`, ½ or ⅓ of the wide column for `pair`/`trio`.
- Every `<img>` carries `width`/`height`.
- Everything except the hero is `loading="lazy"`. The hero gets `fetchpriority="high"`.
- **Crop only where the box is fixed.** The hero (≈520px desktop, ≈260px mobile) and the thumbnails use `object-fit: cover` on a `fit` variant. `full`, `wide`, `left` and `right` keep the photo's own ratio, so a story never re-crops the owner's composition.

### 5.6 Tokens, type, layout

- **Stylesheet:** `assets/css/extended/gallery-story.css`, classes `story-*` / `journal-*`. It must not be `project.css`, which is the software projects page.
- **Colours:** PaperMod variables only, plus:

  ```css
  :root { --accent: #8a5a00; }                  /* 5.93:1 on white, 5.44:1 on #f5f5f5 */
  :root[data-theme="dark"] { --accent: #d8a657; } /* 7.56:1 on --theme, 6.12:1 on --entry */
  ```

  The accent is used sparingly: chapter numbers, timeline dates and dots, map areas, the active toggle. The mockups also colour `a:hover` with it. That is a site-wide change and stays out.
- **Type:** PaperMod already sets body text at **18px / 1.6**. The story raises only the line height of its own paragraphs to 1.75, and drops to 17px below 768px. Captions are 13px in `--secondary`.
- **Breaking out of the column** (`full`, `wide`) uses the technique `galleryImageText` already proved: `margin-left: 50%` + `translateX(-50%)`, with the width capped at `100vw − 2 × --gap`, because `100vw` includes the scrollbar and would scroll sideways. `full` therefore keeps a 24px gutter. Going truly edge to edge would need `overflow-x: clip` on an ancestor, and the 390px test (§10) decides whether that is worth it.
- **Mobile first:** `left`/`right` stack (photo first for `left`, text first for `right`), `trio` becomes a `scroll-snap` strip with no JS, `grid` and `sequence` become two columns, and touch targets are at least 44px.
- **Spacing:** 40–56px between blocks, 72–88px between chapters.

### 5.7 Text the owner has not written yet

The brief rightly says: invent nothing, mark the gap. A literal `TODO` in the Markdown would ship.
- `{{< todo "Why this project exists" >}}` renders a visible dashed placeholder when `hugo.IsDevelopment` (that is, under `hugo server`).
- In every production build — the `build` test, `deploy.sh` — it renders nothing and `warnf`s with the page and the prompt.

So switching a real project to a story either lands together with its text, or it stops the deploy. This is the same reminder mechanism a photo without a title already uses. The mockups' bracketed prompts ("[What you were waiting for, and for how long.]") are exactly these placeholders. The mockups' draft prose is **not** copied in: it is a draft, and the owner writes the final text.

### 5.8 i18n

New keys go under a `# Project stories` block in all three files.

| Group | Keys |
|---|---|
| Counts | `speciesCount` and `outingCount`, both plural (`photoCount` exists) |
| Toggle and end of page | `story_view_story`, `story_view_grid`, `story_toggle_label`, `story_show_as_grid`, `story_prefer_grid`, `story_that_was_all` (plural on the photo count) |
| Section headings | `story_more_from_project`, `story_more_from_outing`, `story_species_in_project`, `story_species_in_chapter`, `story_species_in_dex` (plural) |
| Navigation and map | `project_previous`, `project_next`, `project_nav_label`, `story_map`, `story_map_note` |
| Dates | `story_undated`, `story_period` ("{{ .from }} to {{ .to }}" / "bis" / "till") |
| Placeholder | `story_todo` |

How the sentences and dates are assembled:
- **Sentences** like "28 photos from 9 outings and 13 species, July 2022 to September 2026." are assembled from the plural parts with one wrapper key. go-i18n allows a single plural count per message.
- **Days** use `time.Format ":date_long"`. **Months** use `time.Format "January 2006"`. Hugo localises the names of both. The game pages already use `:date_medium` the same way.

## 6. Essay

Top to bottom:
1. Breadcrumb (`gallery-breadcrumb.html`) and the toggle.
2. **Hero**: `featured_image`, resolved by `resolve-featured-image.html`, the same photo as the `og:image`. It carries an EXIF chip at the bottom right and counts as placed.
3. Title block: `h1`, description, and a computed meta line. The line reads "8 photos · 2022" or "28 photos · 13 species · 2022 to 2026", and a species count of 0 is left out.
4. Chapter chips, only if the essay has chapters. A "Map" chip is added if the project has areas.
5. Intro: the body before the first chapter.
6. Overview map, if the project has areas. A click on an area that a chapter names jumps to that chapter.
7. The chapters, or without chapters simply the text with its blocks. A chapter head has a rule, the number in the accent colour at a light weight, an `h2` title, the subtitle, and on the right a computed "9 Aug 2026 · 13 photos". The chapter ends with its species chips. Anchors are `anchorize` of the title, like every heading on the site.
8. "More from this project" (`h2`): the unplaced photos as a thumbnail grid, only if there are any.
9. End of page: "That was all 8 photos.", "Show as grid" (`#grid`), and a **Next project** card. Its target is the next listed project by `weight`, wrapping around: `.CurrentSection.RegularPages.ByWeight`, which already leaves out the unlisted Nicklheim album (`build.list: never`). The card shows the project's cover and photo count. There is no card when the current project is the only one listed.

`demo-essay` and `demo-essay-minimal` are the first essays (§3.1). The real projects stay `grid` until the owner switches one.

## 7. Journal

- **Header**: title, description, the computed sentence, and the intro (the body outside any `outing`). On the right sits the overview map with one marker per area that has outings, labelled with the count of those outings. Below come the species index as chips with counts, each linked to the dex.
- **Timeline**: a gutter with the year at the first entry of each year, a vertical rule, and one accent dot per entry. Every entry carries its date. On mobile the gutter goes away and the date becomes a line above the entry. Container width: `--nav-width`.
- **Entry sizes**, computed per day and overridable with `size=`:

  | Size | When | Contents |
  |---|---|---|
  | **full** | text and at least 3 photos | `h2` with date, title and "12 photos, 5 species". The lead photo across the column (`lead=` or the first photo). The text, with a mini map of the outing's area beside it (§8). Then the remaining photos as six-column thumbnails under "More from this outing" (`h3`) |
  | **medium** | text and 1–2 photos | Photo (440px) and text side by side, alternating left and right from entry to entry. A second photo sits below as a pair. With an area, the mini map takes the photo's place beside the text and the photos sit below as a pair, as in the mockup's ibex entry |
  | **compact** | no text | Date, title and two-column thumbnails. The title is, in order: `title=`, then the dex names of the day's species, then the title of the day's first photo (*Above the Clouds* has no species). Consecutive compact entries of one year share a row of three |

- Inside a day, photos are ordered by capture time, earliest first. A day is a sequence, whatever `sort_order` says about the order of the days.

`demo-journal` and `demo-journal-minimal` are the first journals (§3.1). Without a single `outing` block, Inn-Valley's photos would make nine compact entries. That is the brief's acceptance criterion 4, so a real project can be switched before any text is written.

## 8. The map, and what it must never show

The rule comes first and does not depend on the technique: **nest sites of white-tailed eagles and ospreys must not be readable.** The rule holds four ways:
1. **No photo position, ever.** The collector has no GPS field, and the served files have their GPS removed. The map draws only `data/galleryAreas.yaml`.
2. **Coarse by construction.** `lat`/`lng` may have at most **2 decimal places** (≈1.1 km north–south, ≈0.75 km east–west at 47°N), and `radius` must be **at least 1,000 m**. Anything else is an `errorf` naming the area. The check is on the **data** because the repository is public: a precise coordinate in `data/` is published the moment it is pushed, rendered or not.
3. **The centre is the area, not the sighting.** A bog, a ridge, a valley floor. The label is free text and must not name the nest either. That part is the author's job, and the header comment of the data file says so.
4. **Circles, not pins.** In the journal, outings in one area share one marker with a count. Spreading them out would invent positions, and invented positions read as real ones. The same goes for the mockups' loose dots: "each dot is one outing" in the journal header, and five dots for the essay's chapter without an area. A chapter or outing without an area is simply not on the map.

For comparison: the dex's `sightings:` are exact pins by design. Today no species has one. If a raptor ever gets one, that would undo this rule from another page. This concept does not change the dex, but anyone adding a sighting should know.

**Technique: A, on the site's own basemap (recommended, to confirm).** This section first weighed A (the dex pattern: a local first paint, OSM tiles after a click) against B (a static SVG). Since `self-hosted-maps.md`, every map on the site draws the Protomaps basemap that the companion serves (`basemap.js`), and that settles most of it:
- **A's catch is gone.** The first paint was going to be circles on blank land, because Natural Earth means nothing at valley scale. The basemap goes to z15, has labels in en/de/sv and a light and a dark flavor, and shows what the mockups drew by hand: the river, the town, the lakes. No regional layer, no new source, no new licence: the attribution is `BASEMAP_ATTRIBUTION`, as on every map.
- **B has no advantage left.** Its point was a map without JS and requests, but it needed a base drawing of its own, hand-drawn or made from OSM data, which is a second map pipeline next to the one the site now has. Without JS the area list stands in for the map, and that is all B would have given.
- **No button.** The dex keeps its click because its drawn world is a useful view without one. Here there is nothing local worth showing, and the click's original job, opting in to a third party, is gone: the tiles come from the companion, and `{{< map >}}` and the trips load theirs without asking. The map is built when it nears the viewport (`IntersectionObserver`), so MapLibre's ~300 KB loads only for visitors who scroll there. As in `route-map.js`, the wheel zooms only after a click into the map, so scrolling through an essay is not caught by it.
- **Several mini maps, few of them alive.** Every basemap is its own MapLibre instance with its own WebGL context, and browsers keep only a limited number alive (Chromium 16, dropping the oldest after that). A journal that grows for years with a mini map beside every outing would reach that limit, and each instance costs memory on a phone well before then. So a mini map exists only near the viewport:
  - It is **created** when it comes within half a viewport height, and **removed** once it is more than two away. The gap between the two keeps fast scrolling from building and tearing down the same map.
  - At most **four** mini maps live at once, the overview map not counted. A fifth evicts the one furthest from the viewport.
  - Removing frees the context: `maplibre-gl-leaflet`'s `onRemove` calls MapLibre's `remove()`, which calls `WEBGL_lose_context` (checked in the vendored 6.12.0).
  - MapLibre and the TileJSON load once per page (`basemap.js` already does that), and the tiles are immutable and stay in the browser cache, so building a map a second time costs almost nothing.
  - A mini map is a picture, not a tool: no dragging, no zoom, no controls. It is framed on its circle (`fitBounds`, capped at 13 like the overview) and carries the compact attribution, since each one can be the only map in view. A click leads to the overview map, which highlights the area.
  - Before it is built, and for good without WebGL2, its place shows the area's label as a chip leading to the overview map, the same fallback as the area list.
- **WebGL2 is required, so the list is the fallback.** Without WebGL2, `addBasemap` resolves to null. The dex still has its drawn world and a trip its lines, but circles on an empty field say nothing. So the area list is always in the HTML: label, the chapter or outing it leads to, and the count. The script checks WebGL2 first and adds the map only when it can draw one; `basemap.js` exports its `webgl2Available()` for that, a one-line change. If loading fails after that, the map is removed again and the list stays. Tor Browser at its stricter levels probably has no WebGL (not checked yet, `self-hosted-maps.md` *Still open*), so those visitors get the list. The onion build reaches the clearnet companion through an exit node like every map (`self-hosted-maps.md` §9).
- **Zoom capped at 13.** The old first paint was empty, but the basemap is detailed, and MapLibre draws z15 tiles sharp far beyond z15: the other maps allow 18 and 19. Zoomed into a 1 km circle, every stand of trees and every path in it is readable, which invites exactly the search this section exists to prevent. At z13 a 1,000 m radius is ≈ 150 px across at 47°N: a place in its landscape, not a target. Rule 2 keeps the data coarse; this keeps the drawing from inviting a closer look.
- **Code:** `assets/js/gallery-story-map.js`, the size of `route-map.js`: a Leaflet map, `addBasemap`, one `L.circle` per area in `--accent` with a dashed edge and a chip (number, name, count, as in the mockups; a numbered badge below 768px, as in the mobile mockup) linking to its chapter or outing, the theme observer `route-map.js` already has, and the mini-map lifecycle above. Areas reach the script through `data-*`, as before. `head.html` loads Leaflet and the script only on a story page whose project has areas, and passes `basemapTileJson` like the other map scripts. Under the map sits `story_map_note`, the mockups' "Areas are drawn loosely on purpose, so nesting birds of prey stay undisturbed."

Neither first project needs a map to ship, so the map is step 6.

## 9. SEO, search, feeds

- **Structured data**: unchanged. Project pages keep their `ImageGallery` branch in `schema_json.html`, with `author`/`publisher` = the `#person` reference. No `BlogPosting`: a project has no date, and that branch is where `0001-01-01` came from.
- **Search**: `index.json` indexes `.Plain` of every regular page. That means essay text becomes searchable, while today the body is not even rendered. Journal text is held in the Store rather than printed inline, so `index.json` must call `.Content` and append the outing texts for a journal page.
- **Feeds, sitemap, hreflang, `og:image`**: unchanged. The pages and their URLs stay the same.

## 10. Tests

All tests run against `.test-site/`, as always. Until the owner switches a real project, the pages with an `essay` or `journal` layout are the four demos (§3.1). The tests find them by layout, not by name, so they keep working after the demos are deleted; with no such page left, the story tests skip instead of failing.

**`tests/static/project-stories.spec.ts`**, for every project page whose `project_layout` is `essay` or `journal`, in every language:
- the multiset of `data-id`s inside `.story` equals the project's photos from `data/gallery.yaml`, each **exactly once**, the hero included (criterion 2);
- every story `<img>` has `width`, `height` and a non-empty `alt` (criteria 8 and 9);
- every story `<img>` except the hero has `loading="lazy"`;
- one `h1`;
- the toggle buttons carry `aria-pressed` and render `hidden`;
- every coordinate in a map's `data-*` has at most 2 decimals and every radius is at least 1,000 (criterion 7).

For a project with `project_layout: grid` or without the key, there is no `.story` and the grid is the page's only content. That is criterion 1, and in the test build it holds for all three real projects, the unlisted album included.

**`tests/e2e/`**:
- at 390px (`mobile-chrome`), `scrollWidth <= clientWidth` on both layouts in light and dark (criteria 5 and 6), and the trio is a scrollable strip;
- the toggle can be reached with Tab and switched with Enter, after which `aria-pressed` flips and the hash reads `#grid` (criterion 8);
- the map, once there is a project with areas: with the companion's tiles mocked (`tests/support/network.ts`), it is drawn and asks the companion and nobody else; under `withoutWebGL2` (`tests/support/webgl.ts`) there is no map and the area list is visible; it cannot zoom past 13; scrolling through a journal from top to bottom never shows more than four live mini maps at once (counted by their `data-flavor` containers). `maps.spec.ts` already fails the build on any third-party tile host.

**Not covered by a fixture:** the warning and error paths (duplicate, foreign, coarse area, `todo`). The happy paths have their fixtures in the demos. The `build` project already turns any `WARN` into a failure, and the suite has no fixture-site mechanism to provoke one on purpose. They are checked by hand on a scratch copy during step 2, with what was seen written down here.

**Checked by hand, 2026-10-12** — a throwaway project page and a temporarily coarsened `data/galleryAreas.yaml`, built into a scratch directory, both removed again. Every path below stopped the build (`ERROR`) or warned (`WARN`) as listed, naming the file and, for a shortcode, the line:

| Provoked | Seen |
|---|---|
| a photo placed twice; the hero placed again | ERROR "appears twice in the story" (", once as the hero" for the second) |
| a photo of another project | ERROR "is not in project …", with the file name |
| an id not in `data/gallery.yaml` | ERROR "no photo with id …" |
| `storyPhotos layout="pair"` with one id | ERROR "takes 2 photos, got 1" |
| `chapter area=` not in the page's `areas:`; an area slug not in the data | ERROR, each |
| `storySpecies` with an unknown dex slug | ERROR |
| `outing` on an essay, `storyPhoto` on a journal | ERROR "works only on a gallery project with project_layout …" |
| two outings for one date; a malformed date; `size="huge"` | ERROR, each |
| an outing `lead` from another day | ERROR "is not a photo of project … taken on …" |
| an outing for a day with no photo | WARN "is not shown" |
| `project_layout: story` | ERROR "must be grid, essay or journal" |
| `lat: 47.7085`; `radius: 500` | ERROR naming the area, each |
| `{{< todo >}}`, top level and inside a chapter | production: WARN with file:line and the prompt; `-e development`: the dashed placeholder, in both places |

## 11. Build order

1. **Data**: `gallery-story-data.html`; `data/galleryAreas.yaml` with the three areas and its validation partial (coarse rule, label fallback); `scripts/project-photos.py`.
2. **Shortcodes**: `storyPhoto`, `storyPhotos`, `storySpecies`, `chapter`, `outing`, `todo`, with the Store recording of §4 and every error and warning path. `gallery-story.css` comes with them, mobile first, then desktop. Then provoke each failure once on a scratch copy.
3. **Dispatch and chrome**: the `project_layout` branch in `page.html` **and** `single.html` → `gallery-story.html`; the toggle; `gallery-story.js` and its conditional load in `head.html`.
4. **Essay**; `demo-essay` and `demo-essay-minimal` in en/de/sv.
5. **Journal**; `demo-journal` and `demo-journal-minimal` in en/de/sv.
6. **Map** (§8): `gallery-story-map.js` on the site's basemap, overview map and mini maps with their lifecycle, the `webgl2Available` export in `basemap.js`, the area list and chips as the fallback.
7. **i18n** for de/sv, the light theme, the `index.json` outing text, and the tests of §10.
8. **Documentation**: a *Project stories* section in `CLAUDE.md` (switch, shortcodes, the Store rule, the areas rule, the demos) and the author workflow in `AGENTS.md`.

## 12. Out of scope

- **Multi-day outings.** A later `outing date="2026-08-09..2026-08-11"` would group a range. v1 groups by day only.
- **PhotoSwipe in the story view.** It needs `lightbox.js` to handle more than one gallery root.
- **A serif reading font.** If it ever comes, it is self-hosted under `static/fonts/` (OFL), next to Cantarell, and loaded only on story pages.
- **Switching a real project** (Inn-Valley, *Above the Clouds*, the Nicklheim album) to a story. That is the owner's call once the text exists; the demos show what it would look like.
- **The EXIF spacing** (`600 mm` vs `600mm`), a change to `collect-images.html` for the whole site.

## 13. Implementation notes (2026-10-12)

Built in the order of §11, end to end. Where the code departs from the text above:

- **Nested shortcodes go through a token.** §4 assumed a chapter could print its inner Markdown and the blocks inside it. It cannot as written: a paired shortcode renders `.Inner` with `RenderString`, the nested shortcodes have already rendered into it, and the site's Goldmark runs without `unsafe` — their HTML came out as `<!-- raw HTML omitted -->` (checked on a scratch site). So a story shortcode inside `chapter`, `outing` or `storyPhoto` stores its HTML in the page Store under its key and writes a plain token; the parent puts the HTML back after Markdown (`layouts/partials/story/emit.html`, `inner.html`). The Store keys of §4 are unchanged and carry this too.
- **`.Inner` is passed to the partial**, not read there: Hugo decides whether a shortcode may be closed by finding `.Inner` in the shortcode's own template text. A consequence for authors: `storyPhoto` can take text, so without text it must be self-closed, `{{< storyPhoto id="…" />}}`.
- **A chapter or outing `area=` must be one of the page's `areas:`.** That keeps one declaration of what the map shows, catches a typo, and lets `head.html` decide from the front matter alone whether to load Leaflet and the map script.
- **The essay's intro** is split from the chapters at a marker comment the chapter writes (`<!--story-chapter-->`), which is where the map goes.
- **The area list stays visible** under every map, as its legend, instead of only standing in without WebGL2. The map chips sit beside their circle (anchored at its east edge, with room left on the right by `fitBounds`); below 768px they become numbered badges on the circle. A journal's chip shows its outing count. The map field's space is reserved as soon as the script knows WebGL2 is there, so nothing jumps when the map is built.
- **Heights.** A photo keeps its ratio (§5.5), but a `full` or `wide` landscape frame 1,200px wide is taller than most screens. Both are capped where the photo alone would fill the screen's height (`100vh − 40px` × ratio); the same cap on both keeps a `full` photo from ever being narrower than a `wide` one, which an earlier 85% cap did on short laptop screens. A portrait beside text takes a column of its own width (`min(600px, 58%, 80vh × ratio)`), so a capped portrait does not leave a gap before the text; a journal's lead is capped at 80% and a single photo where a pair was laid out at 70% (and 60% of the width). `pair` and `trio` give each photo a share of the width proportional to its ratio, so a row has one height and nothing is cropped.
- **Medium entries** with the photo beside the text stack one or two photos in that column; §7 left the second photo's place open. A day with **one photo and an area** is laid out the same way, with the small map under the text: as text-and-map with the photos below, a single photo sat half-width under a short text and left both columns half empty. Only a day with two photos and an area keeps the mockup's text-and-map row with the pair below. Entries with the photo beside the text alternate sides.
- **`#grid` links and footer.html.** The site's footer smooth-scrolls every `a[href^="#"]` with `preventDefault` and `pushState`, which fires no `hashchange`, so "Show as grid" at the end of a story did nothing. `gallery-story.js` takes that one link in the capture phase, before the footer's handler. The grid itself takes the story's width (`--nav-width`), so in the grid view it lines up with the bar and the title.
- **Rules** (chapter heads, the timeline, compact days) use `--tertiary` in the light theme: PaperMod's light `--border` all but disappears as a 1px line on white. Headings use `text-wrap: balance`.
- **Captions and tiles print the short title**, the part before " - ", as the mockups do; the link's `title` and the image's alt carry the rest.
- **i18n** gained, beyond §5.8: `story_view_journal` and `journal_prefer_grid` (the journal's own wording, as in the mockup), `story_contents`, `story_grid_heading` (a visually hidden heading over the grid), `story_map_show_area`, `journal_summary` / `journal_summary_nospecies` and `journal_order_desc` / `_asc`. German puts the journal sentence as a list ("28 Fotos, 9 Ausflüge und 13 Arten, …"), because "von 9 Ausflügen" needs a dative the shared `outingCount` cannot give.
- **The three areas** are the Rosenheimer Stammbeckenmoore around Nicklheim (47.79, 12.06, r 2,000 m — the centre of the bog complex, from Wikipedia, not the eagle's lake), the Großer Riesenkopf (47.71, 12.11, r 1,500 m) and the Inn valley floor south of Rosenheim (47.83, 12.12, r 3,000 m).
- **The demos** are as §3.1 lists them. `demo-journal` has text on seven days, five with an area (ibex and chamois on the Riesenkopf, the bog morning at the Filzen, the fox and the hawk moth on the valley floor), the sandpiper and the caravan without, and two compact days.
- **Tests:** `tests/static/project-stories.spec.ts` and `tests/e2e/project-stories.spec.ts` as §10 describes, plus a check of `data/galleryAreas.yaml` itself, that a `grid` project carries no story markup, and that "Show as grid" switches the view. Story pages are found through `projectPages()` in `tests/support/site.ts`.

### Second review in Chrome (2026-10-12, with the owner)

- **The hero** was 1872 × 520 on the owner's ultrawide screen, a 3.6 : 1 strip. It is now a fixed 12 : 5 shape up to 1440px wide (about 520px tall at 1250px, as the mockup has it), never taller than 70% of the screen, and 3 : 2 below 768px. `full` blocks stop at 1440px too.
- **`hero_position`** (front matter, a CSS `object-position` such as `"50% 22%"`) moves the hero's crop, so the subject stays whole: the centred crop cut off the eagle's raised wings on *Sunrise Patrol*. `demo-essay` sets `"50% 22%"`. Anything that is not an object-position is a build error.
- **Text beside a portrait.** In an essay, photo and text are one unit, centred in the wide block: the text keeps a 520px measure, and a portrait is no taller than min(75vh, 640px). In a journal, the photo beside the text gets a column from its ratio (no taller than min(65vh, 520px)) and the text a 560px measure; a full day whose lead is a portrait is laid out with the photo beside the text, like a medium one.
- **Previous / next project on all three layouts** (the owner's request): `gallery-project-nav.html` closes the grid page as well as the essay and the journal, after the grid. It replaces §6's wrapping "Next project" card: neighbours among the listed projects by weight, without wrapping — with two listed projects, wrapping offered the same project as previous and next. An unlisted page offers the first listed project. **The grid layout is therefore no longer today's page byte for byte**; it gained this one block. i18n: `story_next_project` became `project_next`, with `project_previous` and `project_nav_label`.
- The project cards are at most 440px wide, each at the edge it leads to (half the page width left a lone card mostly empty), and their thumbnail fills its box: `main.scss`'s `.main img { height: auto }` had left it short, the same rule every cropped story image needs a second class against.
- Smaller: Leaflet's zoom buttons and attribution follow the theme (they were white in the dark one), and a compact day with three photos shows them in one row.
