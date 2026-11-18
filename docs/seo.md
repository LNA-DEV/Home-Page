# SEO

Every proposed change states its effect on search (the working rule in
`CLAUDE.md`). This file collects where the site's search-relevant behaviour
lives; most of it is documented next to the feature it belongs to.

## Where it lives

- **URL stability.** A published URL never moves without a redirect: pages through
  Hugo `aliases` and `slugAliases:`, image files through the nginx maps
  (`docs/gallery/images.md`, *Served image names*). `tests/golden/published-urls.txt`
  holds every published URL; a new one needs `npm run golden:update`, and a retired
  one may leave the list only in the commit that adds its redirect
  (`docs/testing.md`).
- **Photo page and image URLs** come from the English title, so rewording one
  moves both (`docs/gallery/photo-pages.md`).
- **Indexing.** `layouts/partials/robots-indexable.html` is the one predicate
  behind the meta robots and `sitemap.xml`. Taxonomy pages are `noindex, follow`,
  never a `robots.txt` `Disallow` (`docs/gallery/tags.md`); game pages are
  noindexed (`docs/gaming/overview.md`); unlisted albums and models use
  `build.list: never` + `robotsNoIndex` (`docs/gallery/overview.md`,
  `docs/gallery/models.md`).
- **hreflang** pairs translations through `translationKey`, a top-level `.AddPage`
  key (`docs/conventions.md`).
- **Images.** One `contentUrl` per photo (the 4000px variant), stable variant
  names, licence metadata embedded in the served files for Google's *Licensable*
  badge (`docs/gallery/images.md`).
- **Structured data and link previews**: below.

## Structured data and the site owner

`layouts/partials/templates/schema_json.html` (PaperMod's, overridden) writes the JSON-LD for every page, in production builds only. Design and measurements: `docs/concepts/about-page-structured-data.md`.

- **One person.** The owner is a single schema.org `Person` with the language-neutral `@id` `<baseURL>/#person`. The full node (`layouts/partials/schema-person.html`) appears only on the home page and the About page. Every `author`, `publisher` and owner-`creator` elsewhere is `schema-person-ref.html`: `@id` + `name` + `url`, because a bare `@id` only resolves when the full node is on the same page. The data lives in `hugo.yaml`: `params.author` (`name`, `alternateName`, `page` = the About page, `modelSlug`) and `params.schema.sameAs` (profiles only — no feed, no `mailto:`, no `matrix.to`). `ShortTitle` is the `WebSite.name` and the `og:site_name`. No `logo` on a Person; that property belongs to organisations.
- **Page types.** Home → an `@graph` of `WebSite` + `Person`. The About page → `ProfilePage`. A `BlogPosting` only for a *dated* page in `posts`; every other page → `WebPage`, with a date only when it has one — **never `0001-01-01`**, which PaperMod stamped on every undated page. The dex, model, photo and gallery branches keep their own types. The owner's model record (`modelSlug`) and the owner inside a photo's `about` share the Person `@id`. No other person ever gets one.
- **Breadcrumbs** are built from `.Ancestors`: Home first, numbered 1…n. A never-rendered section (`/gallery/photo/`) is skipped rather than listed without a URL.
- **Credit for a page-bundle image by someone else** is Hugo page-resource metadata in the page's front matter (`resources: [{src, params: {credit, license}}]`), resolved by `layouts/partials/resource-credit.html`. `{{< img >}}` turns it into `ImageObject` microdata and a visible "Photo: …" line; `showCredit="false"` removes only the line. A licence link is emitted only for an absolute deed URL: `all-rights-reserved` points at the owner's own licensing page, which cannot license another photographer's work. The About portrait is such an image. `portrait: true` marks it for `Person.image` and `og:image` (both via `author-portrait.html`, the same `fit 1200x1200` variant), and its credit line is switched off.
- **The root `/about/` is a static file**, `static/about/index.html`. On a multilingual site Hugo prefixes even an absolute alias with the language, so no alias can write the domain root. `/<lang>/about/`, `/de/ueber-mich/` and `/sv/om-mig/` are ordinary aliases on the About page.
- **Every URL in the JSON-LD is absolute**, and a test enforces it. Microdata resolves a relative `href` against the page; JSON-LD does not. `licenseMap.yaml`'s `all-rights-reserved` URL is the site-relative `/licensing/`, so any JSON-LD that prints a licence URL needs `absURL`.
- **Link previews (`og:image`, via `templates/_funcs/get-page-images.html`) show a photo wherever the page has one of its own**: the photo, the portfolio hero (`featured_image`) on the portfolio and the gallery home, a model's cover, a photographed species' cover. The projects list, All Photos and the dex overview use the photo on their card on the gallery home. That pick lives in `layouts/partials/gallery-section-cover.html` (`projects_cover` / `general_cover` / `dex_cover`, else the first photo that fits), so card and preview cannot drift. **A species nobody has photographed keeps the site logo on purpose:** its hero is a Wikimedia Commons stand-in, mostly CC BY-SA, and a link preview shows it without the attribution the licence requires.
- **Tests:** the *structured data — one person, no invented dates* and *link previews* blocks in `tests/static/html.spec.ts`.

## Search Console findings (2026-10-14)

- The image-metadata report swinging between ~580 and ~15 items is **one page**:
  `/<lang>/gallery/general/` carries ~589 `ImageObject`s, every other page 76 at
  most. The swings follow that page entering and leaving Google's index, not
  hundreds of broken photos; structured data on a page that is not indexed is not
  counted. When the report drops again, check the indexing status of the general
  pages before suspecting the image names.
- That page is ~1.91 MB (en) / 1.93 MB (de). **Googlebot reads only the first
  2 MB**, headers included, so roughly 50 more photos and the tail of the grid goes
  unseen. Weigh that cap before adding markup to the gallery grid.
- On 2026-09-10 every `_hu_` variant hash changed with byte-identical output (Hugo
  0.166.0, commit `d19e0a4b`), and the filename-era photo URLs (live
  2026-09-14…18) kept underscores that Googlebot still requested. Both are fixed —
  the stable variant names and the frozen redirects in `docs/gallery/images.md`,
  deployed and verified live on 2026-10-14. The owner prefers stable, self-chosen
  names to hashed URLs held together by redirects.
