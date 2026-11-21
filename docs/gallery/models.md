# Models

A page per person in front of the camera, at `/gallery/models/<slug>/`. It is layered on the gallery the way the dex is — the species design with the nouns swapped — plus the one thing a species does not have: a species cannot change its name, withdraw consent or ask to be forgotten. The reasoning is in `docs/concepts/gallery-models.md`; three questions that concept left open were settled in the build. The section is **`model` / `/gallery/models/`**, not `people` — the photographic term, and the one a *model release* is named after. The gallery home got **no** nav card: the section is reached from the photos that show a person and through the site search, which is as much promotion as a page about someone else's face should get from the gallery's front door. And the licence default was **not** changed: `all-rights-reserved` is not enforced anywhere in the build, and the rights problem is carried by a sentence of text instead (below).

- **Data**: `data/models.yaml`, one record per person. The header comment in that file is the schema reference and is worth reading before editing it. `slug`, `name` and `visibility` are **required**; `consent` (a date — **never rendered**, a note to the author rather than a release store), `bio`, `links` and `cover` are optional. `bio` is per-language (`{en, de, sv}`, or a bare string meaning English — `model-pages.html` normalises the string form before handing it over, because `dex-text.html` *indexes* the field and `index "a string" "de"` is a build error rather than an empty result) and is read through **`dex-text.html`**, so it inherits the same English fallback the dex prose uses and a bio written in one language still renders on all three pages. `links` is `[{name, url}]` where `name` is an icon key `layouts/partials/svg.html` already knows (a chain-link glyph for the rest). `cover` is a gallery photo **UUID**, resolved through `gallery-meta.html`'s `byId`; a uuid that resolves to no photo is a build error rather than a silent fallback, because it is always a typo. **The display name lives in this file and nowhere else** — the photos carry only the slug, so a change of name is a one-line edit instead of a sweep through every photo entry. Two things must never go in the file: contact details of any kind (the repository is public, so every line of it is page content whether it was meant that way or not), and anything the person did not agree to have published.
- **`visibility` is required, has no default, and each value is one whole behaviour** rather than a bundle of flags to keep in step — a record that omits it, or misspells it, is a hard build error naming the record and the value, because consent is a decision somebody made and not something a template may assume. **Both gates are allowlists** (`in (slice "public" "unlisted")`), never `ne "hidden"`, and that is load-bearing: `errorf` marks a build failed but **does not stop template execution** (the same note is in `collect-images.html`), so with a denylist a misspelled `visibility: hiden` would render the page and write the name into `public/` on the way to a failing build. Only `deploy.sh`'s `set -e` would have stopped it shipping. The rule this feature exists to enforce fails **closed**: anything that is not exactly `public` or `unlisted` renders nothing.
  - `public` — page rendered, listed in the `/gallery/models/` grid, indexed, name shown on every photo.
  - `unlisted` — page rendered and reachable by URL, but not listed: the adapter sets `build: {list: never}` plus `robotsNoIndex` and `searchHidden`, which is the Nicklheim-album pattern driven from the adapter instead of front matter. Verified on Hugo 0.166.0: `build` **is** a valid top-level key of `.AddPage` (like `aliases`, unlike params), and `list: never` with `render: always` keeps the page out of `.RegularPages`, the section RSS, the search index (`index.json`) and `sitemap.xml` while leaving the URL reachable. An unlisted page is still linked from the photos that show the person — `unlisted` means "not in a listing", not "unreachable", and the photo pages that link to it are indexed anyway.
  - `hidden` — no page at all, and the name appears **nowhere** in `public/`: not on a photo, not in a caption, not as a slug. Verified against a real build.
- **`hidden` is the tombstone, and deleting a record is a build error on purpose.** Removing a person is *not* done by deleting their record: the photos still carry the slug, `gallery-meta.html` stops the build on it, and that is the correct outcome — the photos themselves still need a decision (stay, move to the archive, or leave the photo store), which is a separate per-case call this feature deliberately does not make. `visibility: hidden` makes the person vanish from every rendered page in one edit and keeps the slug reserved so it is never reused by someone else. **A hidden record may be `slug:` + `visibility:` and nothing else** — `name:` is required only on a record that renders. This file is public on GitHub, history included, so a tombstone forced to keep the name would take it off the site and leave it in the repository forever, which is not what someone asking to be forgotten asked for.
- **The join is a slug on the photo, never a name.** `model: jane-doe` in `data/gallery.yaml` (string or list — a group photo names everyone in it, the same shape as `project:`). The species join runs on the scientific name because that name is stable, self-describing and has an external authority; a person's name is none of those — people marry, transition, adopt a stage name — so the photo stores the identity and the display name is looked up. `gallery-meta.html` normalises `model:` into a derived **`.models`** slice exactly as it does `project:` → `.projects`, with the same rule: filter with `in $meta.models $slug`, never `in` on the raw string. `collect-images.html` exposes it as **`.Models`** with a `model` filter key beside `species` — `.Models`, not `.Model`, because the collector already returns `.CameraModel` from EXIF, whose tag is literally called `Model`.
- **An unknown `model:` slug is a hard build error**, where an unknown `species:` is only a warning. That asymmetry is deliberate: species names are an open external vocabulary and a photo may legitimately be tagged before the species is added, while model slugs are a small closed set the author invented himself, so a miss is always a typo — and the cost of a silent miss is a person losing the credit or the visibility setting they agreed to. `gallery-meta.html` validates the whole of `data/models.yaml` up front (missing `slug`, missing `name`, **duplicate slug**, missing or invalid `visibility`) before it walks the photos, then errors on any `model:` value that is not one of those slugs, naming the photo file and the value.
- **Two partials, and they are two for the reason the dex pair is two**:
  - **`layouts/partials/model-index.html`** is the join, `partialCached` **per language**. It reads `gallery-collected.html` — already cached, already carrying every photo with its EXIF and language-resolved prose — so the join costs one walk over a list in memory and no image processing. Returns `{all, bySlug, listed, total}`; each entry carries `slug`, `name`, `record`, `visibility`, `photos` (portfolio first, newest within each band), `count`, `cover`, `hasPage` and `listed`. Only records that render a page are in `all`; `listed` is the `public` subset, which is what the grid and the nav card read.
  - **`layouts/partials/model-lookup.html`** is the cheap one, slug → `{name, url}` for the current language, with the URL resolved through `site.GetPage` so the link survives the section moving. `gallery.html` renders on every grid, every album, every dex species page and every photo page, and a caption needs a name and a URL — making it depend on the whole-gallery join for one string is the mistake `dex-lookup.html` exists to avoid. **The absence of an entry means print nothing.** This is the one place it differs from `dex-lookup.html`, where a species the dex does not know still prints its scientific name as plain text: a `hidden` record, a record whose page was never generated, and a slug the lookup has never heard of all render as **no row at all**. The name is never derived from the slug, and no caller may invent one.
- **Archive photos do not count for a model** — unlike the dex, where they do. "Have I photographed this species" is a question about the whole body of work, so the dex counts retired shots; a person's page is a page that is published *today*, and the archive is where retired shots go. `model-index.html` skips `section: archive` before it groups, `gallery.html` never sets `include_archive` on a model page, and **a record whose photos are all archived therefore renders no page at all** — as does a record with no photos, since a page that is a name and a link list with nothing to show has no purpose (there is no "uncaught" state here, unlike a dex species).
- **Pages come from a content adapter**, like the dex and unlike the per-photo pages: `content/gallery/models/_content.{en,de,sv}.gotmpl`, one file per language because Hugo scopes an adapter to the language of its filename, each calling `layouts/partials/model-pages.html`, which does the `.AddPage` loop over `model-index.html`'s `all`. **All three languages**, because a model page has the bio, which the author writes and can translate. The slug is language-neutral, so the three share a URL segment and are linked through `translationKey: model-<slug>`. The section index is a plain `content/gallery/models/_index.{en,de,sv}.md` stub with `params.theme: models-home`.
- **Theme dispatch lives in both `layouts/_default/page.html` and `layouts/_default/single.html`** for theme `model` (the dex species pages need the same pair, for the same Hugo 0.146+ template-system reason — see `docs/conventions.md`), and `models-home` is dispatched in `layouts/_default/list.html`. **The gallery home links it as a text link, never a card** — there are three nav cards (Projects / Dex / All Photos), and Models sits in the text row below them (Tags · Models · Gear · Archive). That link is conditional on `model-index.html` having a `listed` record: this section is built from `data/models.yaml` and can legitimately be empty, unlike the other three, and a link onto an empty grid is worse than none. Beyond that, `/gallery/models/` is entered from a photo that shows the person, from the site search, or by URL. `layouts/_default/index.json` adds `/gallery/models/` to the search index explicitly — branch pages are not in `site.RegularPages` and would otherwise be unsearchable, the same reason `/travel` is added there — guarded on `model-index.html` having a `listed` record, since a search hit landing on an empty grid is the same mistake as a nav card onto one. The individual model pages need no such help; they are ordinary regular pages.
- **`layouts/partials/model-detail.html`** renders the page: breadcrumb, `fill 900x900` hero from `cover`, the name as H1, the bio as `.Content` (nothing at all when empty — a placeholder line about a person is worse than no line), the links, the photo strip and the rights note. The strip is the ordinary **`gallery.html`** driven by the page's `filter_model` param, so PhotoSwipe, the like counters, the EXIF captions and the `ImageObject` microdata come for free — the same move `dex-detail.html` makes. `layouts/partials/model-card.html` is one tile of the grid.
- **Where the model row appears**: the `gallery.html` grid caption and the `gallery-photo.html` hero each emit one `<span class="caption-model" data-field="model" data-model-url="…">` per person inside the hidden `.pswp-caption-content`, after `.caption-species`; `assets/js/lightbox.js` reads those spans and renders a linked **Model** / **Models** section under Species (label picked by count, from the `modelLabel` / `modelsLabel` i18n keys passed through the JS params in `head.html`); `photo-meta.html` prints a `photo-model` row on the photo page — resolved by the *caller*, not by that partial, precisely because "resolves to nothing" is a meaningful state that must produce no row; and `gallery-photo.html`'s **"Appears in"** list links the model page(s) after the dex link. `gallery.html` hoists the lookup out of its loop because that range runs once per photo on the general grid.
- **Structured data**: a `ProfilePage` branch in `layouts/partials/templates/schema_json.html` emits `mainEntity: Person {name, image, sameAs: [links]}` for theme `model`. The owner's own record (`params.author.modelSlug`) is the one exception: its Person carries the site-wide `#person` `@id` and points at the About page (see *Structured data and the site owner* in `docs/seo.md`). Without it the page fell through to that file's `BlogPosting` branch, which would claim the site owner as `author` of somebody else's bio and stamp `datePublished: 0001-01-01` on it — the same bug the dex and the photo pages each had to fix. The photo `ImageObject` gains `about: [{@type: Person, name, url}]`, built from `model-lookup.html` so it names **only people the rendered page already names visibly** — structured data must never say more about a person than the page does, which is what makes a `hidden` record invisible there too.
- **The gallery feed names the people in a photo, for the autouploader** in HomePageCompanion, which tags them on the platform it posts to. The contract is that repo's `docs/concepts/autouploader-model-tags.md` — change it in both repos or not at all. Per item, `rss.xml` emits a `<media:credit role="performer">` and an `<lna:model slug name url autotag>` (namespace `xmlns:lna="https://lna-dev.net/ns/gallery/1"`) with one `<lna:profile platform url/>` per entry of `links:`, `platform` being the icon key lowercased. **`public` only** — `unlisted` people are named on the photo pages but not here, because a feed is a listing and readers keep every item they have seen. Name, page and profiles are **always** given; **`autotag:`** on the record (bool, default false) is the consent to be tagged, written out as `"true"` / `"false"`, and the uploader alone acts on it. The prefix `lna` is part of the contract: gofeed files an unknown namespace under the prefix the feed declares. `model-lookup.html` carries `permalink`, `visibility`, `autotag` and `profiles` for this; `autotag` is true only for a literal YAML `true`, and `gallery-meta.html` stops the build on a non-bool `autotag:` and on a link with no `name:` or a URL that is not absolute http(s). Tests: the *gallery feed* block of `tests/static/models.spec.ts`.
- **`rel="noopener"` on the model's links, and never `rel="me"`.** PaperMod's `social_icons.html` emits `rel="me"` because those are the *site owner's* profiles and `rel=me` is an identity claim about the site's author; a model page links to somebody else, so making that claim would be false. That is also why `social_icons.html` is not reused (it iterates `site.Params.socialIcons` rather than an argument). The honest place for those URLs is `sameAs` in the `ProfilePage` JSON-LD, which is a statement about the *Person*, not about the author.
- **There is deliberately no rights notice on the page.** An earlier revision printed one translated sentence on the model page and in the licence section of any photo page with a model, saying that the licence covers the photograph and grants nothing over the depicted person. The site owner decided against it and it was removed — markup, CSS and the `models_rights_note` i18n keys. **This was a decision, not an oversight; do not re-add it unasked.** The reasoning it carried still holds and is worth knowing: a photo licence covers the **photographer's copyright and nothing else** — Creative Commons' own FAQ says its licences do not touch publicity, privacy or personality rights, and German law (§22 KUG, GDPR on top for the name-to-likeness link) says the same from the other side, so a CC BY-SA portrait is a photo anyone may adapt and republish of a person who consented only to this site. `all-rights-reserved` is already a key in `data/licenseMap.yaml` and is the per-photo lever for that; it is **not** enforced by the build, so it is set deliberately or not at all.
- The section stubs set **`outputs: [HTML]`**: `layouts/_default/rss.xml` branches on `eq .Section "gallery"`, so every section below `/gallery/` otherwise emits the *same* full gallery feed — hundreds of KB per language per build, with `<link>`s pointing at `/gallery/models/#<uuid>`, anchors that do not exist on that page. (`/gallery/dex/` and `/gallery/projects/` still do this; only the new section was fixed.) The model's links carry **no `safeURL`**, unlike `social_icons.html`: that partial serves the owner's own config, this one serves whatever a third party handed the author, and `safeURL` switches Hugo's scheme filter off — without it a `javascript:`/`data:` URL renders as `#ZgotmplZ` instead of executing. `gallery-portfolio.html` emits the caption spans too, not just `gallery.html` — the portfolio is the grid the gallery home leads with, and leaving it out meant the Model row appeared everywhere except the most-seen page. i18n lives under the `# Models` block in `i18n/{en,de,sv}.yaml`; styles are `assets/css/extended/models.css` (auto-bundled, PaperMod theme variables only, no palette of its own, and it also holds the `.photo-model` rule the photo page uses). That same commit added **`photoCount` and `albumCount` to `i18n/sv.yaml`**, where they had been missing entirely — every Swedish gallery count had been silently falling back to the English string.

## Conventions

- Adding a model: write the record in `data/models.yaml` **first** (`slug`, `name`, and an explicit `visibility:` — the build errors without one), then add `model: <slug>` to the photo entries in `data/gallery.yaml`. A slug with no record is a hard build error; removing someone is `visibility: hidden`, never a deleted record. Set `artist:` on any photo the owner did not take — it otherwise resolves to the site author. Full workflow below.

## Adding a model

A "model" is a person who appears in a gallery photo and has a page at
`/gallery/models/<slug>/`. The data model and the reasoning are
above. There is **no script** for this — it is a handful of
YAML lines per person, and every one of them is a decision somebody made about
their own likeness, so nothing about it is automated.

The order matters: the record first, the photos second. A `model:` slug that
names no record is a hard build error, so tagging the photos first leaves the
site unbuildable until you catch up.

1. **Write the record** in `data/models.yaml`, under the top-level `models:`
   list. The file's header comment is the schema reference; the minimum is
   three lines:

   ```yaml
     - slug: jane-doe          # URL segment + the key photos join on. Never changes.
       name: Jane Doe          # display name — lives here and nowhere else
       visibility: public      # REQUIRED: public | unlisted | hidden
   ```

   `visibility` has **no default** and the build refuses a record without a valid
   one. Pick it deliberately:

   - `public` — page rendered, listed on `/gallery/models/`, indexed, name shown
     on every photo.
   - `unlisted` — page rendered and reachable by URL, but not listed, not in the
     sitemap, not in the search index, `noindex`. The name still shows on the
     photos that link to it. This is the setting for "fine to show to someone who
     was handed the link, not something a search engine should surface".
   - `hidden` — no page, and the name appears nowhere on the site. See
     *Withdrawing consent* below.

   Then the optional fields, all of which are page content — remember the
   repository is public, so nothing goes in here that the person has not agreed
   to have published, and **never any contact details**:

   ```yaml
       consent: "2026-09-18"   # date the release / consent was given; never rendered
       cover: 5ebb463e-…       # a gallery photo UUID for the hero; else the first
                               # portfolio photo, else the newest
       bio:                    # per language, English fallback; a bare string
                               # (bio: "…") also works and means English
         en: |
           Two or three sentences, in the person's own framing.
         de: |
           …
       links:                  # name = an icon key svg.html knows (instagram,
         - name: website       # mastodon, pixelfed, bluesky, github, website, …);
           url: https://…      # unknown keys get a chain-link glyph
   ```

   A `cover:` uuid that is not a gallery photo fails the build, so paste it from
   the photo's `id:` in `data/gallery.yaml` rather than typing it.

2. **Tag the photos.** Add `model: <slug>` to each photo's entry in
   `data/gallery.yaml`, right under `category:` (the same slot `species:` uses).
   String form for one person, list form for a group shot:

   ```yaml
   - id: 0c16ee6e-67b6-4cb0-9812-162da7df7922
     src: DSC_2340.jpg
     category: portrait
     model: jane-doe
   ```

   ```yaml
     model: [jane-doe, john-roe]
   ```

   Check what you tagged:

   ```
   grep -c "^  model: " data/gallery.yaml
   grep -B3 "^  model: .*jane-doe" data/gallery.yaml
   ```

   **Only non-archive photos count.** Unlike the dex, a `section: archive` photo
   does not put a person on their page — and a record whose photos are *all*
   archived (or that has no photos at all) renders no page and no card.

3. **Set `artist:` on any photo the site owner did not take.** This is the step
   that is easy to miss and impossible to see afterwards: `collect-images.html`
   resolves the photographer as `data/gallery.yaml` `artist:` → `site.Params.author.name`,
   so a photo with no `artist:` line silently credits **Lukas Nagel** — which is
   exactly wrong for a photo *of* him taken by somebody else. Self-portraits and
   photos he did shoot need nothing.

   ```yaml
     artist: Someone Else
   ```

4. **Check the licence, per photo.** The gallery's default is CC BY-SA, which
   covers the photographer's copyright and **nothing else** — it grants no rights
   over the depicted person. The site says nothing about this anywhere (a rights
   notice was built and then deliberately removed — see above; do not re-add
   it unasked), and the build enforces nothing per model, so the licence field is
   the only lever there is. `all-rights-reserved` is already a key in
   `data/licenseMap.yaml` and is the sensible choice for model work:

   ```yaml
     license: all-rights-reserved
   ```

5. **Rebuild and look.** Use a fresh `hugo` build, not the long-running server on
   :1313, which misses newly created layout and content files:

   ```
   hugo
   ls public/en/gallery/models/
   ```

   Then check, per language: the page at `/en/gallery/models/<slug>/` (hero, bio,
   links, photo strip), the card on `/en/gallery/models/` (which is
   **not** linked from the gallery home — go there by URL or through a photo), the
   **Model** row in the lightbox on `/en/gallery/general/`, the row and the
   "Appears in" link on the photo page, and — for an `unlisted` record — that the
   URL works while the slug appears in neither the grid nor `sitemap.xml`:

   ```
   grep -c "gallery/models/<slug>" public/sitemap.xml public/en/index.json
   ```

Do **not** run `./deploy.sh` — deployment is a separate step the user authorizes
explicitly.

### Withdrawing consent / removing a person

**Set `visibility: hidden`. Never delete the record.**

```yaml
  - slug: jane-doe
    visibility: hidden
```

`name:` may go with it — it is required only on a record that renders. This file
is public on GitHub, **history included**, so a tombstone that had to keep the
name would take it off the site and leave it in the repository forever. If the
request was to be forgotten, drop `name`, `bio`, `links` and `cover` and leave the
slug and the flag. (The name stays in the git history of earlier commits either
way; removing that is a history rewrite, not an edit.)

That is one edit and it is complete: no page is generated, no card, no caption
span, no lightbox row, no "Appears in" link, no JSON-LD — the name and the slug
leave `public/` entirely (verified against a real build). The record staying
behind is the point: it keeps the slug reserved so it can never be reused for
somebody else, and it keeps the photos building.

Deleting the record instead fails the build, because the photos still carry the
slug. That is the intended outcome, not an obstacle — **the photos themselves are
a separate decision** and the failure is what forces it. Whether they stay in the
gallery untagged, move to `section: archive`, or leave the photo store altogether
is a per-case call, made with the workflows that already exist:

- stay, but no longer attributed to a person → remove the `model:` line from the
  photo entry;
- retired from the current gallery → `section: archive` (the photos keep their
  `model:`, they simply stop counting for the page);
- gone → delete the file from the photo store and its entry from
  `data/gallery.yaml`, the normal photo-removal path.

Neither `hidden` nor archiving unpublishes a file somebody already downloaded, so
if the request was to take the images down, it is the photo store and
`data/gallery.yaml` that have to change, not just the visibility flag.

### What the build will refuse

All five are hard errors naming the file and the value, not warnings — unlike a
`species:` that matches no dex entry, which only warns. A person losing a credit
or a visibility setting silently is not an acceptable failure mode, and the slugs
are a small closed set, so a miss is always a typo:

- **`model:` naming no record** — *data/gallery.yaml: photo "DSC_2340.jpg" names
  model "jane-do", which is not a slug in data/models.yaml*.
- **A record with no `visibility:`, or an invalid one** — *model "jane-doe" must
  set visibility: to one of public | unlisted | hidden*. The same loop also fails
  on a record with no `slug:`, and on a **rendering** record with no `name:` (a
  `hidden` one may omit it). An invalid value also fails *closed*: the record
  renders nothing at all rather than being treated as published.
- **A duplicate `slug:`** — a slug is an identity and is never reused, so two
  records claiming one would make a page silently overwrite the other.
- **A `cover:` that is not a gallery photo id** — *data/models.yaml: model
  "jane-doe" has cover "…", which is not a gallery photo id*.
- **A tag that spells a model's slug or name** — *data/gallery.yaml: photo
  "DSC_2340.jpg" has the tag "janedoe", which names model "jane-doe"*. Checked
  for every record, `hidden` included: a tag would put the name on the photo
  page, into the file's keywords and onto a `/gallery/tags/` page of its own,
  around the record's `visibility:`. Remove the tag; `model:` is the credit.

Do **not** run `./deploy.sh` — deployment is a separate step the user authorizes
explicitly.
