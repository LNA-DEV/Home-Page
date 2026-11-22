# The portraits page

`/de/gallery/portraits/` — portrait photography and TFP shoots, the one page on
the site that asks people to be photographed. Why it exists and why it is built
this way: `docs/concepts/gallery-portraits.md`.

## How it works

- **An essay without a project.** `content/gallery/portraits/index.<lang>.md`
  with `params.theme: gallery-portraits`. `page.html` and `single.html` dispatch
  that theme to `layouts/partials/gallery-portraits.html`, which renders
  `.Content` first (the story shortcodes record what they placed in the page
  Store) and then the page: breadcrumb (with the `linkTitle`), the hero from
  `featured_image`, the title block, the chapter chips, the body and two end
  links (Models, Photography). No story/grid toggle, no "More from this
  project", no grid, no project neighbours, no counted meta line — it is a
  hand-picked page, not an album.
- **Its photos are the pool, not a project.** `gallery-story-data.html` has a
  second pool for this theme: every non-archive photo with a `model:` whose
  people are **all `public`** in `data/models.yaml` (an allowlist through
  `model-lookup.html`, like every visibility gate). The page is a listing of
  people, and `unlisted` means "in no listing". A photo outside the pool — the
  hero included — is a build error naming the photo and the rule.
- **The essay shortcodes work here unchanged** (`story/context.html` lets them
  in): `chapter`, `storyPhoto`, `storyPhotos`, `storySpecies`, `todo`. Two
  differences, both keyed on the theme: a chapter prints no period or photo
  count (`chapter.html`), and a photo caption names the people instead of the
  EXIF (`story/figure.html` with `people`, names from `story/people.html`). Every
  photo at most once, the hero included, as in an essay.
- **Shortcodes this page brought** — they work in any essay too; each is
  documented at the top of its file:
  - `storyAuthor` — the About page's `portrait: true` image (`author-portrait.html`)
    beside a text, through `responsive-image.html` with the About page as its
    page, so it reuses the files that page publishes; credit from the resource
    metadata (`photo_credit`). Needs `alt=`.
  - `storyModels ids="a, b" notes="… | …" invite="#kontakt"` — one card per
    person, linking their model page; **`public` records only**, anything else
    is a build error. The thumbnail is the `fill 480x480 Center` variant the
    models grid already publishes. `invite` adds a dashed last card (i18n
    `portraits_invite_*`).
  - `storySteps` — wraps a Markdown ordered list whose items open with `###`;
    numbers and the joining line are CSS.
  - `storyChips "a, b, c"` — plain chips (places), no links.
  - `storyCards` — cuts its Markdown at each `###` into cards; `style=outline`,
    `icons="eye, link, eye-off"`, `title=` / `note=` like `storyPhotos`.
  - `storyFaq` — cuts at each `###` into `<details>` with the h3 in the
    `<summary>`. No FAQPage schema (Google shows it for government and health
    sites only since 2023).
  - `storyContact channels="email, instagram, matrix" id="kontakt"` — buttons
    resolved from `params.socialIcons` by name, else from `params.schema.sameAs`
    by host; it never takes a URL. Label for email: i18n `contact_email`.
  Paired ones render their Markdown through `story/inner.html`, so story
  shortcodes inside them (a `todo`, `storyChips`) work; `story/emit.html` lists
  them as parents that swap the tokens back.
- **Styles**: `assets/css/extended/story-portraits.css` (after
  `gallery-story.css` in the bundle; overrides of story-body defaults carry
  `.story-body` for specificity), tokens only.
- **Front matter**: `title` is the `<title>` and carries the search terms;
  `params.heading` is the visible h1 and `params.kicker` the line above it,
  inside the h1; `params.facts` the short line under the description;
  `titleSuffix: "LNA-DEV"` keeps the `<title>` near 60 characters.
  `params.teaser {title, text}` and `params.invite` are the words the links to
  this page use elsewhere (below).

## Links to it

All conditional on `site.GetPage "/gallery/portraits"` — the page exists in
the languages it is written in, and nowhere else shows a link to it:

- `/gallery/models/` — a box under the grid, from `params.teaser`
  (`layouts/_default/list.html`, `.model-teaser` in `models.css`).
- Every model page except the owner's — a line after the photos, from
  `params.invite` (`model-detail.html`, `.model-invite`).
- The gallery home — the text row after Models, with the `linkTitle`.
- The About page (German) — a sentence in *Fotografie*.

## Writing and changing it

- Text still to decide is a `{{< todo >}}`: it warns in every production build,
  which stops the deploy until it is written.
- A new photo for the page: give it `model:` in `data/gallery.yaml`; everyone in
  it must be `public`. A person who goes `unlisted` or `hidden` takes their
  photos off this page with the next build — the build fails on a placement
  that is no longer allowed, which is the point.
- Another language: add `index.en.md` / `index.sv.md` with the same `theme` and
  a `translationKey` on all of them; the links above appear in that language by
  themselves. Then `npm run golden:update`.
- Tests: *the portraits page shows and names only public people* in
  `tests/static/models.spec.ts`.
