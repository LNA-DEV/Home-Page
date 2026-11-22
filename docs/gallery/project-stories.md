# Project stories: essay and journal

Design: `docs/concepts/gallery-project-stories.md`. A gallery project opts into telling a story with **`params.project_layout: essay | journal`**; `grid`, or no key, is today's page byte for byte, and anything else is an `errorf`. `theme` stays `gallery-project` — the switch is one `if` inside that branch of **both** `page.html` and `single.html` → `layouts/partials/gallery-story.html`, so `head.html`, `schema_json.html`, `get-page-images.html` and `newsletter-in-footer.html` keep working unchanged. Per language file, no fallback: a language whose file has no story text keeps the grid. **All three layouts end with the neighbouring projects** (`gallery-project-nav.html`: previous / next among the listed projects by weight, no wrapping; an unlisted page offers the first listed one).

- **Every project photo appears exactly once** in the story view, the hero (`featured_image`, which must be a project photo) included; the grid follows the story unchanged (`gallery-story-grid.html`, `id="grid"`). The project's photos are the grid's: `project:` names the slug, archive excluded. Everything counted (photos, species, outings, periods) comes from `gallery-story-data.html`, `partialCached` per page, built on `gallery-collected.html`.
- **Shortcodes**, all addressing photos by **UUID** (`scripts/project-photos.py <slug>` lists them by capture day): `storyPhoto` (`full|wide|left|right`; with `left`/`right` the inner Markdown sits beside the photo — **self-close it otherwise**, `{{< storyPhoto id="…" />}}`, because a shortcode that can take `.Inner` must be closed), `storyPhotos` (`pair|trio|grid|sequence`), `storySpecies` (dex **slug**), `chapter` (essay), `outing` (journal; renders nothing where it stands), `todo`. Each `errorf`s off a story page, on an unknown or foreign id, on a photo placed twice (found by the layout), and on an `area=` that is not in the page's `areas:`. `todo` renders a dashed placeholder under `hugo server` and **warns in every production build**, so a page with a gap cannot deploy. The portraits page (`docs/gallery/portraits.md`) is an essay without a project — every essay shortcode works there, over its own pool of photos — and brought `storyAuthor`, `storyModels`, `storySteps`, `storyChips`, `storyCards`, `storyFaq` and `storyContact`, which work in any essay too.
- **The page Store is the record of what was placed**, keyed by the shortcode's position (`story/key.html`: `.Ordinal` with the parent's key as a prefix, `"001.002"`), always `SetInMap`, never `Add` — under `hugo server` the Store survives a template-only edit and `Add` would double every entry. The layout calls `.Content` **first**, then reads `storyPlaced`, `storyChapters`, `storyOutings`. Nested shortcodes render before their parent, which is how a chapter counts its own photos, dates and species.
- **Nested story shortcodes emit a token, not HTML** (`story/emit.html`, `story/inner.html`). A paired shortcode renders its inner Markdown with `RenderString`, and the site's Goldmark runs without `unsafe`, so the already-rendered HTML of the shortcodes inside it would come out as `<!-- raw HTML omitted -->`. The child stores its HTML in the Store and writes `XSTORYBLOCKX<key>X`; the parent swaps it back after Markdown. Only `chapter`, `outing` and `storyPhoto` do that swap, so a story shortcode inside anything else writes its HTML as usual. Hugo decides whether a shortcode may be closed by finding `.Inner` **textually in the shortcode's own template** — which is why the partial takes `.Inner` as a parameter instead of reading it.
- **The map** (`gallery-story-map.html`, `assets/js/gallery-story-map.js`): `data/galleryAreas.yaml` and nothing else — **at most `params.galleryAreas.maxDecimals` decimals and a radius of at least `params.galleryAreas.minRadius` (hugo.yaml; without the keys 2 and 1000, set to 4 and 0 = no minimum, so each area's size and precision are the author's call — a raptor's area stays at 2 decimals and ≥ 1,000 m), checked on the data** (`gallery-areas.html`, an `errorf` naming the area; `project-stories.spec.ts` reads the same key), never a photo's position, zoom capped at 13. A project lists its areas in `params.areas`; a chapter or outing points at one of those. On the site's basemap through `basemap.js` (`webgl2Available` is exported for it), built when it nears the viewport; mini maps beside journal outings with text and an area live only near the viewport, **four at most**. Without WebGL2 or JavaScript the area list (always in the HTML, the legend for everyone) stands in. `head.html` loads Leaflet and the script only when `params.areas` is set.
- **Toggle**: `assets/js/gallery-story.js`, state in the hash — `#grid` or a photo's UUID shows the grid (so `lightbox.js` finds the item), anything else the story; the buttons render `hidden` for a visitor without JavaScript, who gets the story and then the grid. **`layouts/partials/footer.html` smooth-scrolls every `a[href^="#"]` with `preventDefault` + `pushState`, which fires no `hashchange`** — so any `#` link that must change state has to be caught before it (the story script takes `#grid` links in the capture phase).
- **Styles**: `assets/css/extended/gallery-story.css` (not `project.css`, which is the software projects page). Colours are the design tokens (`docs/design-system.md`): `--accent` for chapter numbers, timeline dates and dots, sequence numbers and focus; `--panel` and `--rule` for surfaces and rules; the story map's areas and their badges take the data colour `--map-area` (the accent is never drawn on a map). The hero is a 12:5 box up to 1440px (3:2 on a phone), cropped; **`params.hero_position`** (a CSS `object-position`, e.g. `"50% 22%"`) moves the crop so the subject stays whole. Full and wide photos keep their ratio, capped where they would fill the screen's height (full never narrower than wide); a portrait beside text gets a column of its own width; only the hero and thumbnails are cropped.
- **The demo projects** `content/gallery/projects/demo-{essay,journal,essay-minimal,journal-minimal}/` show the feature over the real projects' photos (`project_slug` of Inn-Valley and *Above the Clouds*), unlisted (`build.list: never`, `robotsNoIndex`), so they are in no list, sitemap, feed or search and never in the golden URL list. **The owner deletes them** when they have served their purpose; deleting a folder is all it takes. The real projects stay `grid`.
- **Search**: `index.json` appends a journal's outing texts, which `.Plain` does not hold.
- Tests: `tests/static/project-stories.spec.ts`, `tests/e2e/project-stories.spec.ts`; both find story pages by layout and skip when there are none.

## Writing a project story (essay or journal)

Design: `docs/concepts/gallery-project-stories.md`. A gallery project page is a
grid until its front matter says otherwise.

1. **List the photos.** `python3 scripts/project-photos.py <project_slug>
   [--lang de]` prints them by capture day, newest first, with UUID, title and
   species (the dex slug for `storySpecies`), and an empty `{{< outing >}}` per
   day. The capture days come from the last build's
   `<lang>/gallery-metadata.json`; without a build they are "date unknown". It
   writes nothing.
2. **Switch the page**, per language file: `params.project_layout: essay` or
   `journal`. Keep `theme: gallery-project`. `sort_order` (already on every
   project) orders a journal's days. A language you have not written yet keeps
   `grid` — there is no fallback to the English text.
3. **Areas, if any.** Name them in `params.areas: [slug, …]` (records in
   `data/galleryAreas.yaml`: a named public place, at most
   `params.galleryAreas.maxDecimals` decimals, radius ≥ `params.galleryAreas.minRadius`
   (hugo.yaml; a raptor's area still 2 decimals and ≥ 1,000 m), never a photo's position — the build stops otherwise). A chapter or
   outing can only point at one of the page's own areas.
4. **Write.** Essay: Markdown with `{{< chapter >}}`, `{{< storyPhoto >}}`,
   `{{< storyPhotos >}}`, `{{< storySpecies >}}` between the paragraphs. Every
   project photo appears exactly once: the hero is the `featured_image`, and a
   photo the text does not place lands in "More from this project" by itself.
   Journal: the body is the intro; each `{{< outing date="…" >}}` adds text to
   one capture day. Days without one are compact entries already.
   `{{< storyPhoto … />}}` must be self-closed when it has no text beside it.
5. **Check the hero.** The `featured_image` is shown in a wide, cropped box. If
   the crop cuts the subject, set `params.hero_position` to a CSS
   object-position — `"50% 22%"` moves the window towards the top of the
   photo. Look at it on a wide screen and on a phone.
6. **Mark what is missing** with `{{< todo "what goes here" >}}`, never a literal
   TODO: it shows under `hugo server` and warns in a production build, which
   stops a deploy until the text is written.
7. **Check** under `hugo server` (or a `hugo -d` build): a photo placed twice, a
   photo of another project, an unknown id, a malformed outing date or a lead
   photo from another day are build errors naming the file and line; an outing
   for a day without photos is a warning.

Nothing here touches URLs: `#grid` and the chapter anchors are fragments, so
`tests/golden/published-urls.txt` does not change when a project switches.

The four `demo-*` projects under `content/gallery/projects/` exist only to show
the layouts. They are unlisted; delete their folders when they are no longer
needed — nothing else refers to them.
