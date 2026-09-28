# Concept: photo tags as real Hugo tags, and every tag and category page out of the index

**Status:** implemented 2026-09-28, all six steps; `npm test` green (230 passed, 6 skipped — WebKit, as always). The open decisions were answered before the build: no threshold, `photo` / `photography` are ordinary tags, and no search traffic lands on the existing tag and category pages. Where the build departs from the plan below, §12 says so.
**Read against:** the working tree of 2026-09-28 (`96f84a7`), `data/gallery.yaml` at 650 photos (574 general, 76 archive), `.test-site/` from 2026-09-26.

Two changes in one concept, because they are the same question asked twice: what is a listing page *for*? Today the blog's 90 tag and category pages are `index, follow` and in the sitemap, for 20 posts; and a photo page prints its tags as plain text that leads nowhere.

The answer proposed here: a listing page is for the visitor who is already on the site, not for a search engine. So every taxonomy page becomes `noindex, follow` and leaves the sitemap (§2), and photo tags become a real Hugo taxonomy with a page per tag (§3–§5). The second half is only reasonable *because* of the first: ~600 new listing pages in three languages would be exactly the index bloat §2 removes.

## Settled decisions

| | |
|---|---|
| Which pages go noindex | Every page of `.Kind` `taxonomy` or `term` — post tags, categories, photo tags, in all three languages, pagination included |
| Robots value | `noindex, follow` — not `nofollow`, and never a `Disallow:` in robots.txt (§2) |
| Sitemap | Those pages leave it. **One predicate** decides the meta robots and the sitemap, so the two cannot disagree |
| What stays | Every URL, the "Categories" menu entry, the home page's link to `/tags/open-source/`, the post-tag RSS feeds |
| Photo tag taxonomy | A **separate** taxonomy `phototags`, not the posts' `tags` (§3) |
| URL | `/<lang>/gallery/tags/<tag>/`, index at `/<lang>/gallery/tags/` |
| Membership | Non-archive photos only, like the model pages and `/gallery/general/` |
| Threshold | **None.** Every tag on a non-archive photo gets a page — 599 of them, 260 with a single photo (§4) |
| `photo`, `photography` | **Ordinary tags**, with pages like every other — no ignore list, no special case (§4) |
| Term key | The lowercased `.Tags`, never the stored camelCase — 12 tags have two spellings and Hugo would take the page title from whichever photo it met first (§4) |
| Term page | A light index of photo pages — thumbnail, title, link — built from the related-strip tile. No lightbox (§5) |
| Feeds | None for photo tags |
| Unlinked tags | Every tag on an archive photo stays on the photo page as plain text, exactly as today |
| Model names | A tag equal to a model's slug or name stops the build (§6) |
| Search traffic | None lands on `/tags/` or `/categories/` today (checked by the site owner, 2026-09-28), so §2 costs nothing measurable |

No decisions are open.

---

## 1. What the data says

### Posts

| | en | de | sv |
|---|---:|---:|---:|
| posts | 13 | 4 | 3 |
| tag pages | 42 | 22 | 6 |
| … listing at most one post | 24 | 18 | 2 |
| category pages | 7 | 4 | 3 |
| taxonomy URLs in `sitemap.xml` (incl. the two index pages) | 51 | 28 | 11 |

90 listing URLs in the sitemaps for 20 posts. A tag page with one post is that post's summary under a second URL; one with two posts is two summaries. None of them has a line of text of its own.

### Photos

Measured from `.test-site/en/gallery-metadata.json` and `data/gallery.yaml`:

- 612 distinct tags, 6,956 assignments, a median of 10 per photo.
- 267 tags sit on exactly one photo.
- The vocabulary is hashtags, not a curated list: `nature` 447 next to `naturephotography` 260, `landscape` next to `landscapephotography`, `sweden` and `sverige` on the same 98 photos.
- Three tags are on more than half of the 574 general photos: `photo` 573, `photography` 543, `nature` 436.
- **12 tags exist in two spellings across photos** (`naturePhotography` 233 × `naturephotography` 27, `landscapePhotography` 157 × 16, …). `gallery-meta.html` de-duplicates case only *within* one photo.
- Three photo tags collide with a post-tag slug: `photography`, `freedom`, `sverige`.
- The tags are one language-neutral English list, shown identically on all three languages.
- No tag names a person in `data/models.yaml` today (§6).

## 2. Out of the index: every taxonomy page

### Why

Not crawl budget. With ~2,600 URLs across the three sitemaps this site is far below the size at which Google says budget matters, and it would be the wrong reason to give. The real ones:

1. **They have nothing of their own.** Each is a list of summaries of pages that are indexed in their own right. A search hit on one sends the visitor to a list instead of to the answer.
2. **They compete with the pages that should rank.** `/tags/privacy/` against the privacy posts. For photos it would be worse: `/gallery/tags/fox/` against the dex's red-fox page, which is the curated, indexed version of the same slice and carries text of its own. A noindexed page competes with nothing.
3. **Proportion.** Google assesses quality across a site as well as per page. 90 thin pages next to 20 posts is a poor ratio, and §3 adds ~1,800 more — 260 × 3 of them showing a single photo. That is the one version of the "index bloat" argument that holds for a site this size.
4. **Three languages multiply it for photo tags.** `/de/gallery/tags/fox/` and `/en/gallery/tags/fox/` show the same photos under the same English hashtag and differ only in the chrome.

What could be lost: a tag page that ranks for some long-tail query. None does — no search entries land on `/tags/` or `/categories/` today.

### `noindex, follow`, never robots.txt

- **`follow`**, so the links on the page are still crawled. Google has also said that a page which stays `noindex` long enough is eventually treated as `nofollow` too. That is fine here, because nothing depends on a term page to be discovered: every photo page is in the image sitemap and linked from its grid, its neighbours and the related strip; every post from the post list and the feed. The tag pages are for visitors.
- **No `Disallow:`.** A crawler that may not fetch a page never sees its `noindex`, and can still index the bare URL from links pointing at it. robots.txt stays as Hugo generates it.

### How: one predicate, two callers

`layouts/partials/robots-indexable.html` returns whether a page belongs in the index: `false` for `.Kind` `taxonomy` or `term`, for `robotsNoIndex: true`, and for theme `gallery-page-hidden` (the two conditions `head.html` checks today); `true` otherwise. It knows nothing about the environment — `head.html` keeps its own production check.

- **`head.html`** line 4 becomes three-way: not production → `noindex, nofollow` (unchanged); indexable → `index, follow`; taxonomy or term → `noindex, follow`; anything else → `noindex, nofollow` (unchanged for `robotsNoIndex`).
- **`layouts/_default/sitemap.xml`** skips every page the predicate rejects.

Today the two are kept in step by hand: the `robotsNoIndex` pages are absent from the sitemap only because they also carry `build: {list: never}`. The predicate makes the agreement structural, and a test (§7) checks it from the output side.

Hugo's own `sitemap: {disable: true}` via `cascade` was the alternative. It does reach term pages (verified), but this repo's `sitemap.xml` ignores `.Sitemap.Disable` — its `range .Data.Pages` has no filter, unlike Hugo's embedded template — so it needs a template change anyway, plus a stub per taxonomy per language to carry the cascade (nine files). One partial keyed on `.Kind` needs neither, and covers a future taxonomy for free.

### What does not change

The URLs; the "🔖 Categories" menu entry; the home text's link to `/en/tags/open-source/`; the post term RSS feeds; and `tests/golden/published-urls.txt`, which is append-only, keeps the 90 URLs, and still finds them all resolving — the golden test passes untouched.

### Escape hatch — documented, not built

If a term ever deserves to rank — say Open Source becomes a real landing page, with an introduction of its own in `content/tags/open-source/_index.<lang>.md` — the predicate is the one place to let a `robotsIndex: true` on that page override the Kind rule. Not built: no page needs it today.

## 3. Photo tags as a Hugo taxonomy

### A separate taxonomy, not `tags`

1. **Vocabulary.** The post tags are 70 curated topics across three languages (`open-source`, `truenas`). The photo tags are ~600 hashtags. One `/tags/` index would drown the topics.
2. **Language.** Post tags are per-language content — the German posts carry German tags. Photo tags are English on all three languages; `/de/tags/` would turn into a page of English hashtags.
3. **Rendering.** A post term page is a list of summaries, a photo term page a grid of thumbnails. The collisions would put posts and photos on one page — `/tags/photography/` would be 5 posts and 543 photos — with one template to serve both.
4. **Place.** A photo tag belongs under `/gallery/`, with the gallery's breadcrumb.

What a shared taxonomy would give — "posts about Bavaria" on the Bavaria photo tag — is a link, not a merge, and is out of scope (§11).

### Configuration

```yaml
taxonomies:          # declaring the key REPLACES Hugo's defaults — both are restated
  tag: tags
  category: categories
  phototag: phototags
permalinks:
  taxonomy:
    phototags: /gallery/tags/
  term:
    phototags: /gallery/tags/:slug/
```

plus `content/phototags/_index.{en,de,sv}.md`, each with the translated title and `cascade: {outputs: [HTML]}`, which removes the feeds.

### Verified on a scratch site (Hugo 0.166.0)

- **A content-adapter page takes its terms in `params`** — `"params" (dict "phototags" …)`. As a top-level key of `.AddPage`, where `aliases`, `build` and `translationKey` go, they are silently ignored: no term, no warning. It is the exact opposite of `translationKey`, and just as easy to get wrong.
- The permalinks above produce `/<lang>/gallery/tags/<slug>/`. A multi-word tag is urlized (`fall colors` → `fall-colors`). Non-ASCII letters are kept, not folded: `öland` and `land` are two terms, unlike the photo slugs' transliteration — which is what we want here.
- `bavarianAlps` and `bavarianalps` on two pages **merge into one term**, titled after whichever page Hugo met first and capitalised by `capitalizeListTitles` (`BavarianAlps`). Hence the lowercased key in §4.
- `cascade: {outputs: [HTML]}` in a language's `_index` reaches the taxonomy page and every term — but only in the language that has the file. Hence three files. Post tags keep their feeds.
- `layouts/phototags/term.html` and `layouts/phototags/taxonomy.html` are picked over `_default/list.html`; post tags and categories keep PaperMod's.
- **A term page's `.Path` is `/phototags/<term>`, not `/gallery/…`**, whatever its URL. `head.html` loads the gallery stylesheet and the lightbox parameters on `strings.Contains .Path "/gallery"`, so a term page gets neither. That is fine for §5's tiles, whose CSS is in `assets/css/extended/gallery-photo.css` and bundled site-wide — and it is the first thing to change if the lightbox is ever wanted there.

## 4. Which tags become terms

Per photo, in `gallery-photo-pages.html`: `phototags` = the photo's `.Tags`, and nothing at all for an archive photo. No counting, no index partial, no ignore list — without a threshold the decision is local to the photo.

| | |
|---:|---|
| **599** | terms, i.e. ~1,800 term pages across the three languages |
| 6,818 | tiles per language |
| 260 / 89 | terms with one / two photos |
| 13 | tags that sit only on archive photos, and so get no page |
| 573 / 574 | general photos with at least one linked tag |

**No threshold** means 260 pages showing one photo each. That is acceptable precisely because they are `noindex`: for a visitor, "what else is tagged `claas`" has the honest answer "nothing yet", and a page saying so is not worse than a tag that is not a link. It also keeps the rule simple enough to hold in one line of the adapter.

**Why lowercase.** `.Tags` already is the lowercased list, and it is what the photo page prints and what RSS, the schema keywords and the embedded files use. Passing the stored spelling would make a term's title depend on which photo Hugo visits first for the 12 tags with two spellings — a determinism-test failure waiting to happen. The term template prints `#<term>` in lowercase, the same form the photo page shows. (The `<title>` element keeps Hugo's capitalised `.Title`; not worth a special case on a noindexed page.)

**`photo` and `photography`** are ordinary tags. On 573 and 543 of the 574 general photos, their pages are near-copies of `/gallery/general/` without the filters — harmless under `noindex`, and a special case in the build would cost more than the two pages do. The data stays exactly as it is, so no served file changes.

**Not in scope:** merging the hashtag pairs (`landscape` / `landscapephotography`, `sweden` / `sverige`). The tag index will make that mess visible, which argues for a vocabulary pass later — it is not a prerequisite.

## 5. The pages

### Term page — `/gallery/tags/<tag>/`

- Breadcrumb *Gallery / Tags / #tag*, built by hand like `gallery-photo.html`'s: a term's logical parent is the taxonomy, not the gallery section.
- H1 `#fox` and a count line.
- A grid of related-strip tiles: the 600 px variant every photo already has (no new image processing), the title, a link to the photo page. Portfolio first, then newest — the model strip's order.
- **No lightbox, no like counters, no captions.** The page's job is to route to photo pages, which carry the full experience and are the pages meant to rank. And size: a `gallery.html` tile is ~3.1 KB (1.78 MB for the 574 on `/gallery/general/`), a related tile ~540 B. 6,818 tiles in three languages come to ~11 MB as related tiles and ~63 MB as gallery tiles. It also means no `head.html` change (§3).

### Index — `/gallery/tags/`

All 599 tags, alphabetical, each with its count. Reached from the breadcrumb of every term page. **Not linked from the gallery home** — for the same reason the models section has no card there: an unindexed list of hashtags does not earn the gallery's front door. It can be added later without touching anything else.

### Photo page

In `photo-meta.html`'s tag list, a tag with a page becomes `<a href="…" rel="tag">`; an archive photo's tags stay plain text. `gallery-photo.html` hands it a map tag → term URL built from `.GetTerms "phototags"` — Hugo's own answer, so a link exists exactly when its page does. `rel="tag"` is the microformat for precisely this and costs nothing.

The lightbox popup keeps its tags as plain text: linking them would add a URL per tag per tile to every grid (~10 × 574 on the general page) for a click the photo page already offers.

### Structured data

Nothing new. A term page gets whatever `schema_json.html` emits for a list page today; `CollectionPage` would be more precise, but structured data on a noindexed page is not read.

## 6. Guard: a tag must not name a model

The models design promises that a `hidden` person's name appears nowhere in `public/`. A tag is an uncontrolled free-text channel into the same output, and a tag page would put a name into a URL and an H1. No tag names a person today.

The guard: `gallery-meta.html`, which already validates `data/models.yaml` before it walks the photos, stops the build when a lowercased tag equals a model's slug, its slug without hyphens, its lowercased name or its name without spaces — `jane-doe`, `janedoe`, `jane doe` — whatever the record's visibility. It checks the slug on a `hidden` tombstone too, which is the one field such a record still has.

It is a tripwire for the obvious case, not a guarantee: a tag `jane` gets through. It is worth having regardless of tag pages — a plain-text tag already puts a name on the photo page and into the file's embedded keywords.

## 7. Tests

In `tests/static`:

- **robots** (`html.spec.ts`): every taxonomy and term page says `noindex, follow` — the prefixes are derived from `taxonomies` and `permalinks.taxonomy` in `hugo.yaml` (`isTaxonomyUrl` in `tests/support/site.ts`), so a future taxonomy is covered without a test edit; the home page, a post, the About page, a photo page and a dex page still say `index, follow`.
- **sitemap** (`feeds.spec.ts`): no `<loc>` whose page carries `noindex` — the predicate's promise stated from the output side — and no taxonomy URL at all.
- **photo tags** (`tags.spec.ts`): the term pages per language are exactly the distinct tags of the non-archive photos in `gallery-metadata.json`, compared by the tag each page's H1 prints (catches the adapter and Hugo keying a term differently); every term page lists at least one photo and no archived one; every tag on a non-archive photo page is a link and none on an archive one (the `.Title`-lowered round trip, for every tag); no `index.xml` under `/gallery/tags/`; the index links every term page. That the links resolve is the link check's job.
- `data-output.spec.ts`'s "the tag list is exactly the entry's tags" read `<li>text</li>`; it now reads the text of an item whether it is a link or not.
- **golden**: nothing to do. The post term URLs stay on the list and still resolve. The photo term URLs never enter it — they are in no sitemap and no feed — and that is deliberate: a tag page exists as long as some general photo carries the tag. **Tag pages are not part of the URL-stability promise.**

## 8. Cost

- Pages: ~1,800 term pages and 3 index pages, ~11 MB of HTML across the three languages, zero image processing.
- Build: one param per photo in the adapter, one map lookup per photo per term page. Seconds.
- Tests: the static suite reads ~1,800 more small files.
- Deploy: the new pages. The metadata embed pass and the served image files are untouched.

## 9. Build order

Each step builds and passes `npm test` on its own.

1. **Noindex.** `robots-indexable.html`, `head.html`, `sitemap.xml`, the robots and sitemap tests. Shippable alone; the half that depends on nothing else.
2. **Taxonomy.** `taxonomies:` and `permalinks:` in `hugo.yaml`; `content/phototags/_index.{en,de,sv}.md`; the `phototags` param in `gallery-photo-pages.html`.
3. **Pages.** `layouts/phototags/term.html` and `taxonomy.html`, CSS.
4. **Photo-page links** in `photo-meta.html` and `gallery-photo.html`.
5. **Model guard** in `gallery-meta.html`.
6. The photo-tag tests; `CLAUDE.md` (gallery section, and a short *Tag pages* section); `npm test`.

## 10. Files touched

### New

- `layouts/partials/robots-indexable.html`
- `layouts/phototags/term.html`, `layouts/phototags/taxonomy.html`
- `content/phototags/_index.{en,de,sv}.md`
- `assets/css/extended/gallery-tags.css` — the term grid's spacing and the index's pills
- `tests/static/tags.spec.ts`

### Modified

- `hugo.yaml` — `taxonomies`, `permalinks`
- `layouts/partials/head.html` — the three-way robots meta
- `layouts/_default/sitemap.xml` — the predicate
- `layouts/partials/gallery-photo-pages.html` — the `phototags` param
- `layouts/partials/gallery-photo.html`, `layouts/partials/photo-meta.html` — linked tags
- `layouts/partials/gallery-meta.html` — the model guard
- `assets/css/extended/gallery-photo.css` — the linked tag pill
- `tests/static/html.spec.ts`, `tests/static/feeds.spec.ts`, `tests/static/data-output.spec.ts`
- `tests/support/site.ts` — `taxonomyPrefixes`, `isTaxonomyUrl`, `metaRobots`, and a `taxonomy` kind in `pageKind`
- `CLAUDE.md`, `AGENTS.md`

## 11. Deliberately out of scope

- **Photo `category` as a taxonomy.** The filter bubbles on `/gallery/general/` already do it client-side; a page per category would duplicate a filter state.
- **Species and models as taxonomies.** They already have curated, indexed pages — which is precisely what a tag page is not.
- **Cross-links** between a post tag and the photo tag of the same name.
- **Linked tags in the lightbox popup** (§5).
- **A vocabulary pass** — merging the hashtag pairs (§4).
- **Translated tags.** The tags are one English list; translating ~600 hashtags is a vocabulary project, not a template change.
- **Switching `robotsNoIndex` pages from `nofollow` to `follow`.** Possible, unrelated.

## 12. As built

- **No i18n keys.** The taxonomy page's title and description sit in the three `content/phototags/_index.<lang>.md` stubs, which exist anyway for the cascade; the term page's count line is the existing `photoCount`.
- **The term page's H1 is `lower .Title`**, not `.Data.Term`: the latter is Hugo's normalised key, and `.Title` is the passed (lowercase) tag capitalised, so lowering it gives the tag back exactly — `fall colors`, `öland`. The photo page matches its tags to their terms the same way, and `tags.spec.ts` holds the round trip for every tag.
- **Breadcrumb:** *Gallery / Photo tags / #tag*, with the taxonomy page's own title as the middle crumb — no separate "Tags" string.
- **The term grid's CSS** went into a new `gallery-tags.css` rather than `gallery-photo.css`; only the linked pill lives in the latter.
- **Verified, beyond the tests:** the 90 URLs left the sitemaps exactly (51 / 28 / 11), and against a pre-change build nothing else changed but the taxonomy pages and the three sitemaps; 599 term pages per language, no feeds; the model guard stops the build on a photo tagged `Markus Penninger` (checked on a scratch edit, reverted); screenshots of the term page (desktop and phone), the index and the linked tag list.
