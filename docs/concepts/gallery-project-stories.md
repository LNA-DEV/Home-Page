# Concept: project pages that tell a story — "essay" and "journal"

**Status:** concept, nothing implemented. Derived from an external brief (`SPEC.md` plus three static mockups, `essay-desktop.html`, `essay-mobile.html`, `journal-desktop.html`, handed over on 2026-10-06 and not in the repo). That brief was written from the rendered site only. This document is its translation onto the code: §1 answers the brief's "Phase 0" questions, and the *Deviations* table lists every place the brief and the repo disagree. The page-`Store` mechanics in §4 were checked on a scratch site with Hugo 0.166.0, `hugo` and `hugo server` both.
**Read against:** the working tree of 2026-10-06 (`c2eb7f8`), Hugo 0.166.0, 661 photos in the gallery manifest.

A gallery project at `/<lang>/gallery/projects/<slug>/` is today a title, one sentence and the photo grid. The page body is not even rendered: the `gallery-project` branch in `page.html` / `single.html` prints breadcrumb, title and `gallery.html`, and nothing else. This concept lets a project opt into one of two layouts that carry the owner's own text and still show every photo of the project:

- **Essay**: one continuous story, optionally in chapters, with photo blocks between the paragraphs. It suits a project with a theme (*Above the Clouds*).
- **Journal**: a timeline of outings. Each outing is one capture day, built automatically from EXIF. There is text only where the owner writes some. It suits a project that grows over years (*The wildlife of the Inn-Valley*).

A project without the switch looks exactly as it does today. Both layouts keep the grid one click away.

## Settled decisions

| | |
|---|---|
| Switch | `params.project_layout: essay \| journal` in the project's front matter, per language file. Missing → today's grid, byte for byte. `theme` stays `gallery-project` (§3) |
| Photo reference | The photo's **UUID** from `data/gallery.yaml`, as `galleryImage` does. Never a slug (§3) |
| Completeness | Every project photo appears **exactly once** in the story view, the hero included. Recorded through `.Page.Store` with `SetInMap` keyed by shortcode ordinal (§4) |
| Unknown, foreign or duplicate id | Hard build error (`errorf`), naming the page and the id |
| Unplaced photo in an essay | Appended under "More from this project", and **`warnidf "project-unplaced-photos"`** naming them. Like every warning here, it stops the deploy unless that id is put in `ignoreLogs` (§4) |
| Outings | One per **capture day** (`DateTaken`). Undated photos form a last group, "Undated". `{{< outing >}}` blocks only enrich a day, they never create one |
| Journal order | The **existing `sort_order`** front-matter key, which every project already sets to `desc`: newest first. No new `order:` key |
| Areas | A new `data/galleryAreas.yaml`, language-neutral, referenced by slug. **At most 2 decimal places and a radius of at least 1,000 m**, enforced by the build. Never a photo's GPS (§8) |
| Grid view | The existing `gallery.html`, unchanged, lightbox and like counts included |
| Story images | Link to the photo page, like the grid's `href`. **No PhotoSwipe in the story view** in v1: `lightbox.js` is bound to one `#gallery` |
| Widths | Text column `--main-width` (720px), wide blocks `--nav-width` (1060px). Not the brief's 680 / 1040 |
| Colours | PaperMod's variables, plus a new `--accent`: `#d8a657` dark, `#8a5a00` light |
| Font | The site's own Cantarell. No serif in v1 |
| Missing text | `{{< todo "…" >}}`: a visible placeholder under `hugo server`, a `warnf` in every production build (§5.7) |
| URLs | None new. `#grid` and the chapter anchors are fragments, so `tests/golden/published-urls.txt` does not change |

Some of these points I set myself rather than took from the brief. Each is a line to change:
- No lightbox in the story view.
- Reusing `sort_order` for the journal.
- `errorf` instead of the brief's warning for a duplicate or foreign id.
- The site's widths instead of the brief's.
- The `todo` shortcode.
- One map marker per area in the journal, not one per outing (§8).
- Only the hero and thumbnails are cropped (§5.5).
- The shortcode names (§3).

## Decisions still open

| | |
|---|---|
| Map technique | **A:** the dex pattern. Vendored Leaflet, a first paint drawn entirely from this site, and OSM tiles only after a click on a button. **B:** a static SVG per project. Either way the no-JS fallback is the area list as text. The sub-question for A is what the local first paint shows at valley scale (§8). The map can come last: neither first project needs one to ship |
| Unplaced photos | Is `project-unplaced-photos` a deploy gate (the default here, like a missing title) or a note (the id goes into `ignoreLogs`)? |
| Shortcode names | `storyPhoto` / `storyPhotos` / `storySpecies` / `chapter` / `outing` / `todo`. A search-and-replace before step 2 |

## Deviations from the brief

| The brief says | Here | Why |
|---|---|---|
| `projectLayout:`, or Hugo's own `layout` field | `params.project_layout` | Single pages dispatch on `params.theme` in `page.html` *and* `single.html` (Hugo 0.146+ template system). `head.html`, `schema_json.html`, `get-page-images.html` and `newsletter-in-footer.html` all key on `theme: gallery-project`. Hugo's `layout` would bypass that, and a new theme value would have to be added in five places. A param keeps all five working |
| `id` is a slug or UUID, whichever is stable | UUID | The slug is **per language** and **moves when the English title is reworded**. A German essay would need German slugs. The brief's examples (`heavy-early-mornings`) are not even real slugs: the real one is `heavy-early-mornings-white-tailed-eagle-skimming-a-fog-covered-bog-lake` |
| `areas:` in the front matter | `data/galleryAreas.yaml` | Coordinates are language-neutral and would be copied into three files. The bog belongs to two projects. Only one place can check the "coarse" rule. The repository is public, so the rule must hold for the data, not just for the HTML |
| Duplicate or foreign id → warning | `errorf` | Both are always an editing mistake. Precedent: an unknown `galleryImage` id and an unknown `model:` slug are hard errors |
| An essay with unplaced photos "builds anyway, with a warning" | It builds, and the warning stops the deploy | Every `WARN` fails the `build` test project, and `deploy.sh` builds with `--panicOnWarning`. `warnidf` makes the gate removable by id |
| `order: newest \| oldest` | `sort_order: desc \| asc` | It already exists on every project and means the same thing for the grid |
| Text column 680px, wide 1040px | 720px / 1060px | `--main-width` and `navbar.css`'s `--nav-width`, so the essay lines up with every other page |
| EXIF as `600 mm`, `1/1250 s` | The strings `collect-images.html` already produces | Lightbox and photo page print them. A second formatter would drift. Changing the spacing is a separate edit to the collector, for every surface at once |
| The mockups load Source Serif 4 from Google Fonts | No third-party font | The Tor build and the dex map's zero-third-party rule. The site's font is self-hosted (`static/fonts/`). Note that the mockups load the serif without using it: every paragraph is set in the system sans |
| A visible `TODO` in the Markdown | `{{< todo >}}` | A literal TODO would be deployed. The shortcode makes a missing text a deploy gate instead, which is how a missing photo title already works |
| Journal outings as `h3` (mockup) | `h2` | The brief's own rule: one `h1`, chapters or outings `h2`, blocks inside them `h3` |
| The essay mockup uses *Inn-Valley* with three chapters and two areas | *Inn-Valley* becomes the journal | As the brief proposes. So chapters and areas have **no real first user** in v1 (*Above the Clouds* has neither), and the tests in §10 are the only thing exercising them |
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
- A journal **with no `outing` block at all** is already a complete page of nine compact entries, so *Inn-Valley* can switch on day one with no text written. 8 of its 9 days have one to four photos, so most entries stay compact or medium even once text exists. Only the bog morning is a "full" entry.
- *Above the Clouds* exercises the edge cases the brief names: three undated photos, so the period line covers only the dated ones ("2022"), and zero species, so the species count is **left out**, not printed as "0 species".
- The 12 photos of 2026-08-09 are also the unlisted Nicklheim album. Nothing here changes that album.

## 3. Switching a project, and what the author writes

```yaml
# content/gallery/projects/above-the-clouds/index.en.md (and .de, .sv)
params:
  theme: gallery-project            # unchanged
  project_slug: above-the-clouds
  featured_image: 1cd410f4-…        # the hero, as today
  project_layout: essay             # new; missing → the grid
  areas: [nicklheimer-filzen]       # optional; slugs into data/galleryAreas.yaml
```

- **Per language file**, like everything else in a project's front matter. A language whose file lacks the key keeps the grid. That is what a translation looks like before its text exists, and the page body does **not** fall back to English: the shortcodes would print English prose on a German page, and posts do not fall back either.
- The dispatch is one `if` inside the existing `gallery-project` branch of `page.html` and `single.html` → `layouts/partials/gallery-story.html`, which branches on `essay` / `journal`. An unknown value is an `errorf`.

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
  - In an essay they go to the "More from this project" block and are listed by `warnidf "project-unplaced-photos"`.
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
- JS: `assets/js/gallery-story.js`, loaded from `head.html` only when `project_layout` is set. Lightbox and `main.scss` keep loading as they do now, because the theme is still `gallery-project`.

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

So switching a project to a story either lands together with its text, or it stops the deploy. This is the same reminder mechanism a photo without a title already uses. The mockups' bracketed prompts ("[What you were waiting for, and for how long.]") are exactly these placeholders. The mockups' draft prose is **not** copied in: it is a draft, and the owner writes the final text.

### 5.8 i18n

New keys go under a `# Project stories` block in all three files.

| Group | Keys |
|---|---|
| Counts | `speciesCount` and `outingCount`, both plural (`photoCount` exists) |
| Toggle and end of page | `story_view_story`, `story_view_grid`, `story_toggle_label`, `story_show_as_grid`, `story_prefer_grid`, `story_that_was_all` (plural on the photo count) |
| Section headings | `story_more_from_project`, `story_more_from_outing`, `story_species_in_project`, `story_species_in_chapter`, `story_species_in_dex` (plural) |
| Navigation and map | `story_next_project`, `story_map`, `story_map_note` |
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
8. "More from this project" (`h2`): the unplaced photos as thumbnails, only if there are any.
9. End of page: "That was all 8 photos.", "Show as grid" (`#grid`), and a **Next project** card. Its target is the next listed project by `weight`, wrapping around: `.CurrentSection.RegularPages.ByWeight`, which already leaves out the unlisted Nicklheim album (`build.list: never`). The card shows the project's cover and photo count. There is no card when the current project is the only one listed.

*Above the Clouds* becomes the first essay: no chapters, no areas, `todo` placeholders where text belongs, in all three languages.

## 7. Journal

- **Header**: title, description, the computed sentence, and the intro (the body outside any `outing`). On the right sits the overview map with one marker per area that has outings, labelled with the count of those outings. Below come the species index as chips with counts, each linked to the dex.
- **Timeline**: a gutter with the year at the first entry of each year, a vertical rule, and one accent dot per entry. Every entry carries its date. On mobile the gutter goes away and the date becomes a line above the entry. Container width: `--nav-width`.
- **Entry sizes**, computed per day and overridable with `size=`:

  | Size | When | Contents |
  |---|---|---|
  | **full** | text and at least 3 photos | `h2` with date, title and "12 photos, 5 species". The lead photo across the column (`lead=` or the first photo). The text, with a mini map beside it when the outing has an area. Then the remaining photos as six-column thumbnails under "More from this outing" (`h3`) |
  | **medium** | text and 1–2 photos | Photo (440px) and text side by side, alternating left and right from entry to entry. A second photo sits below as a pair |
  | **compact** | no text | Date, title and two-column thumbnails. The title is, in order: `title=`, then the dex names of the day's species, then the title of the day's first photo (*Above the Clouds* has no species). Consecutive compact entries of one year share a row of three |

- Inside a day, photos are ordered by capture time, earliest first. A day is a sequence, whatever `sort_order` says about the order of the days.

*The wildlife of the Inn-Valley* becomes the first journal. Without a single `outing` block it shows nine compact entries. That is the brief's acceptance criterion 4, and it can ship before any text is written.

## 8. The map, and what it must never show

The rule comes first and does not depend on the technique: **nest sites of white-tailed eagles and ospreys must not be readable.** The rule holds four ways:
1. **No photo position, ever.** The collector has no GPS field, and the served files have their GPS removed. The map draws only `data/galleryAreas.yaml`.
2. **Coarse by construction.** `lat`/`lng` may have at most **2 decimal places** (≈1.1 km north–south, ≈0.75 km east–west at 47°N), and `radius` must be **at least 1,000 m**. Anything else is an `errorf` naming the area. The check is on the **data** because the repository is public: a precise coordinate in `data/` is published the moment it is pushed, rendered or not.
3. **The centre is the area, not the sighting.** A bog, a ridge, a valley floor. The label is free text and must not name the nest either. That part is the author's job, and the header comment of the data file says so.
4. **Circles, not pins.** In the journal, outings in one area share one marker with a count. Spreading them out would invent positions, and invented positions read as real ones.

For comparison: the dex's `sightings:` are exact pins by design. Today no species has one. If a raptor ever gets one, that would undo this rule from another page. This concept does not change the dex, but anyone adding a sighting should know.

**Technique (open):**
- **A, the dex pattern.** Vendored Leaflet and a first paint drawn from this site, so zero third-party requests and the page works over Tor. The "detailed map" button is the explicit opt-in for OSM tiles, which is exactly the brief's "load map on click". `dex-map.js`'s load-bearing parts are the `±360` world copies and the ocean mask, and neither is needed at valley zoom. A small `gallery-story-map.js` sharing the vendored package fits better than a mode switch inside `dex-map.js`. The catch: Natural Earth's world layers are useless at a scale where an area is 2 km across. The first paint would be circles on blank land until the visitor opts in, unless a regional base layer is added, and its source and licence have to be settled first.
- **B, a static SVG** per project, with no JS and no requests, but also no interaction. It needs a base drawing from somewhere: hand-drawn, like the mockups, or derived from OSM data, which is ODbL and needs attribution.
- **Both:** no JS → the areas as a plain list (label, linked chapter or outing count) under the map's heading. That is a meaningful fallback, and the brief asks for one.

Neither first project needs a map to ship, so the map is step 6.

## 9. SEO, search, feeds

- **Structured data**: unchanged. Project pages keep their `ImageGallery` branch in `schema_json.html`, with `author`/`publisher` = the `#person` reference. No `BlogPosting`: a project has no date, and that branch is where `0001-01-01` came from.
- **Search**: `index.json` indexes `.Plain` of every regular page. That means essay text becomes searchable, while today the body is not even rendered. Journal text is held in the Store rather than printed inline, so `index.json` must call `.Content` and append the outing texts for a journal page.
- **Feeds, sitemap, hreflang, `og:image`**: unchanged. The pages and their URLs stay the same.

## 10. Tests

All tests run against `.test-site/`, as always.

**`tests/static/project-stories.spec.ts`**, for every project page with a `project_layout`, in every language:
- the multiset of `data-id`s inside `.story` equals the project's photos from `data/gallery.yaml`, each **exactly once**, the hero included (criterion 2);
- every story `<img>` has `width`, `height` and a non-empty `alt` (criteria 8 and 9);
- every story `<img>` except the hero has `loading="lazy"`;
- one `h1`;
- the toggle buttons carry `aria-pressed` and render `hidden`;
- every coordinate in a map's `data-*` has at most 2 decimals and every radius is at least 1,000 (criterion 7).

For a project **without** the key, there is no `.story` and the grid is the page's only content. That is criterion 1, and the unlisted album is the standing example.

**`tests/e2e/`**:
- at 390px (`mobile-chrome`), `scrollWidth <= clientWidth` on both layouts in light and dark (criteria 5 and 6), and the trio is a scrollable strip;
- the toggle can be reached with Tab and switched with Enter, after which `aria-pressed` flips and the hash reads `#grid` (criterion 8).

**Not covered by a fixture:** the warning and error paths (unplaced, duplicate, foreign, coarse area). The `build` project already turns any `WARN` into a failure, and the suite has no fixture-site mechanism to provoke one on purpose. They are checked by hand on a scratch copy during step 2, with what was seen written down here.

## 11. Build order

1. **Data**: `gallery-story-data.html`; `data/galleryAreas.yaml` with its validation partial (coarse rule, label fallback); `scripts/project-photos.py`.
2. **Shortcodes**: `storyPhoto`, `storyPhotos`, `storySpecies`, `chapter`, `outing`, `todo`, with the Store recording of §4 and every error and warning path. `gallery-story.css` comes with them, mobile first, then desktop. Then provoke each failure once on a scratch copy.
3. **Dispatch and chrome**: the `project_layout` branch in `page.html` **and** `single.html` → `gallery-story.html`; the toggle; `gallery-story.js` and its conditional load in `head.html`.
4. **Essay**; switch *Above the Clouds* in en/de/sv, with `todo` placeholders.
5. **Journal**; switch *The wildlife of the Inn-Valley* in en/de/sv, with no `outing` blocks yet.
6. **Map**, after the decision.
7. **i18n** for de/sv, the light theme, the `index.json` outing text, and the tests of §10.
8. **Documentation**: a *Project stories* section in `CLAUDE.md` (switch, shortcodes, the Store rule, the areas rule) and the author workflow in `AGENTS.md`.

## 12. Out of scope

- **Multi-day outings.** A later `outing date="2026-08-09..2026-08-11"` would group a range. v1 groups by day only.
- **PhotoSwipe in the story view.** It needs `lightbox.js` to handle more than one gallery root.
- **A serif reading font.** If it ever comes, it is self-hosted under `static/fonts/` (OFL), next to Cantarell, and loaded only on story pages.
- **Chapters or areas on *Above the Clouds*,** and any story for the unlisted Nicklheim album. Those are the owner's calls, not the feature's.
- **The EXIF spacing** (`600 mm` vs `600mm`), a change to `collect-images.html` for the whole site.
