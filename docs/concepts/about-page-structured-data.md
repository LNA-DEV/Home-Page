# Concept: the About page as a profile — structured data, one person, and `/about`

**Status:** **built, 2026-09-24**, and verified: `npm test` green, validator.schema.org 0 errors / 0 warnings, and Google's Rich Results Test "7 valid items" (§14). Where the build departs from what this file proposed, the file has been corrected rather than the code, and each such spot says so. Not committed.
**Measured:** 2026-09-24, against `.test-site/` of 2026-09-21 (Hugo 0.166.0, production environment). Every "today" count below comes from that build.

External feedback on the About page's structured data said, in short: the JSON-LD is valid JSON but says the wrong things. That holds up. The About page describes itself as a `BlogPosting` published on `0001-01-01`, and the site owner appears as three separate, unlinked `Person`s. The fix is not About-specific, because the About page falls through to the same `BlogPosting` branch of `layouts/partials/templates/schema_json.html` as every other undated page. So this concept covers the About page and the parts of that template it needs: one person defined once, a `ProfilePage` for the About page, and an honest fallback for everything else. It also adds the `/about` redirects that were asked for.

## Settled decisions

| | |
|---|---|
| Scope | The About page (`content/lukas-nagel/`), plus every change to `schema_json.html` and its callers that the About fix needs. The dex, photo and model branches keep their types; only their `publisher`/`creator` references change — §5 |
| Portrait credit (D1) | **Not rendered below the photo.** It goes into the page-resource metadata and from there into the structured data. `{{< img >}}` gets a `showCredit` flag that defaults to **on**; the About page turns it **off** — §7 |
| Page-bundle originals (D2) | **Unchanged.** `responsive-image.html` keeps publishing the originals — §13 |
| Redirects (D3) | `about` in all three languages; localised `/de/ueber-mich/` and `/sv/om-mig/`; and a root `/about/` that goes to the **English** page — §8 |
| Site name (D4) | `WebSite.name: "LNA-DEV"`, with `alternateName: ["Lukas Nagel"]`. **The `<title>` stays as it is**, including the "~ Lukas Nagel" that is there for SEO. Why the site name is the wrong place for that: §4. Confirmed 2026-09-24 |
| `sameAs` (D5) | GitHub, Mastodon, Pixelfed, Bluesky, Instagram, with Pixelfed as **`https://pixelfed.de/LNA-DEV` everywhere**. That includes the Identity page, which today links `pixelfed.de/i/web/profile/482439783472092612` in all three languages. Matrix is left out because `matrix.to` is a link redirector, not a profile page |
| Link previews (D6) | `og:image` = the portrait, `og:type` = `profile` — §9 |
| Dates (D7) | Left out wherever the page has none. No `enableGitInfo` |
| Home page (§4) | Done, because it cannot make anything worse — §4 says what it can improve |
| Owner as a model (§5) | Yes, an exception: the owner's model page shares the About page's person `@id` — §5 |
| Microdata on gallery photos | Left alone. The feedback rated it good, and it is |

## Still open

Nothing. The IndieWeb markup was split out into a follow-up, **`indieweb-basics.md`**, which starts once this change has landed because it reads the person data §2 introduces. §12 below keeps the overview of what IndieWeb needs.

---

## 1. What the feedback got right, and what it did not

| Feedback point | Verdict against the build |
|---|---|
| `datePublished`/`dateModified` = `0001-01-01` | **Correct.** 25 pages across the three languages. In English: gaming, identity, licensing, links, lukas-nagel, payroll, projects, reading-list, search |
| Wrong type (`BlogPosting` for a profile) | **Correct** for those 25. **Wrong** for the guess about photo and dex pages: they were fixed earlier and emit `ImageObject` (1,944 pages) and `WebPage` + `Taxon` (462). Model pages emit `ProfilePage` |
| The person is defined three times, unlinked | **Correct.** `author`, `publisher` and image `creator` each have a bare `name` and no `@id`. `publisher.name` is the site title, not a person's name |
| `logo` on a `Person` | **Correct.** It is not a `Person` property. Every `publisher` block in the template has it, including the dex, model and gallery branches |
| Empty `keywords`, `wordCount` as a string, logo as `image` | **Correct**, all three |
| One-element `BreadcrumbList` | **Correct**, and it is sitewide: no breadcrumb starts at Home. PaperMod's *visible* breadcrumb does (`Home » Posts`), so the markup does not even match the page |
| "Add microdata in the portrait's shortcode (`gallery-image-float`)" | **Half right.** The portrait is rendered by `{{< img >}}`, a page-bundle image and not a gallery photo. `gallery-image-float` is only a CSS class shared by the two shortcodes |
| "Check that `contentUrl` is absolute" | **Not needed.** A microdata `<img itemprop="contentUrl">` takes its value from `src`, and microdata parsers resolve that against the document URL, so a relative path is fine |
| `"publisher": {"@id": "…#person"}` alone | **Not enough on its own.** A bare `@id` only resolves if the node is defined on the same page, and on a post page it is not. Every reference must also carry `name` and `url` — §2 |
| "Home page probably emits `Organization`" | **No.** It emits `Person` (`schema.publisherType: Person`), with the site title as the name, the favicon as the image, and a `sameAs` that contains `""`, `"index.xml"` and `"mailto:info@lna-dev.net"` |
| The code sketch: `else if not .Date.IsZero` → WebPage | **Would leave undated pages with no JSON-LD at all.** Better: a `WebPage` with the dates omitted — §5 |

## 2. One person, defined once and referenced everywhere

The site owner becomes a single node with a language-neutral id, `<baseURL>/#person` (`https://lna-dev.net/#person`; the Tor build gets its onion equivalent, which keeps each build self-consistent).

- **Full node** in a new `layouts/partials/schema-person.html`. It is emitted only on the home page and the About page: `@type: Person`, `@id`, `name` (`params.author.name`), `alternateName: "LNA-DEV"`, `url` (the About page in the current language), `jobTitle` (new i18n key `person_job_title`: Software Engineer / Softwareentwickler / Programmerare), `image` (the portrait as an `ImageObject`, §7) and `sameAs` (D5).
- **Reference stub** in `layouts/partials/schema-person-ref.html`, everywhere else: `{"@type": "Person", "@id": …, "name": …, "url": …}`. It carries `name` and `url` so that Google's Article check passes on a page where the full node is absent, and `@id` so a consumer that follows ids merges it with the full node.
- **Not included**, because the page itself does not state it or it would only attract spam: `email`, `birthDate`, `homeLocation`, `knowsAbout`. The rule is the same one the model pages follow: structured data says no more than the page does.
- **Config** in `hugo.yaml` goes under `params.author`, which PaperMod already reads for `<meta name="author">`. The same data can later feed an IndieWeb h-card (§12):
  ```yaml
  author:
    name: Lukas Nagel
    alternateName: LNA-DEV
    page: /lukas-nagel        # the About page: Person.url, and the ProfilePage switch in §3
    modelSlug: lukas-nagel    # the owner's record in data/models.yaml, §5
    email: me@lna-dev.net     # unchanged, never emitted in JSON-LD
  schema:
    sameAs:                   # PaperMod's own documented param, reused
      - https://github.com/LNA-DEV
      - https://mastodon.online/@lna_dev
      - https://pixelfed.de/LNA-DEV
      - https://bsky.app/profile/lna-dev.net
      - https://www.instagram.com/lnadev/
  ```
  `schema.publisherType` goes away: after this change nothing reads it.

**Build vs reuse.** No Hugo module does this better. PaperMod's `schema_json.html` is the thing being overridden, and it has been overridden here for a while: three of its branches (dex, model, photo) are site-specific and dispatch on this site's `params.theme`. A generic SEO module would have to be taught that dispatch and would still emit the `BlogPosting` fallback. What is reused: PaperMod's `schema.sameAs` param, `params.author`, Hugo's `.Ancestors` (§6) and Hugo's page-resource metadata (§7).

## 3. The About page becomes a `ProfilePage`

A new branch in `schema_json.html`. It fires when the current page *is* `params.author.page`, which is one switch in config rather than a front-matter flag that a second page could set by accident. It comes before the posts/fallback branches:

```json
{
  "@context": "https://schema.org",
  "@type": "ProfilePage",
  "url": "https://lna-dev.net/en/lukas-nagel/",
  "name": "About me (Lukas Nagel / LNA-DEV)",
  "description": "…front-matter description…",
  "inLanguage": "en",
  "isPartOf": { "@type": "WebSite", "@id": "https://lna-dev.net/#website", "name": "LNA-DEV", "url": "https://lna-dev.net/" },
  "mainEntity": { …the full Person node from §2… }
}
```

No `datePublished`/`dateModified` (D7), no `articleBody`, no `keywords`, no `wordCount`. Those belong to articles.

## 4. The home page: `WebSite` + `Person`

The home branch is replaced by an `@graph` of two nodes:

- `WebSite`: `@id` `<baseURL>/#website`, `name: "LNA-DEV"`, `alternateName: ["Lukas Nagel"]`, `url` = the domain root, `inLanguage`, `publisher: {"@id": …#person}`. Within one `@graph`, a bare `@id` reference *does* resolve.
- The full `Person` node from §2. This also fixes the `sameAs` junk, since the list now comes from `schema.sameAs` and not from the social icons.
- `og:site_name` gets the same `LNA-DEV`. Today it is not emitted at all: `opengraph.html` reads `site.Params.title`, which this site never sets.

The paginated home pages (`/en/page/2/` …) are `IsHome` as well and get the same block. That is correct.

**What it does for SEO.** Structured data is not a ranking factor, so none of this moves positions. What it can change:

- **The name shown above the result URL.** Google picks a site name from several signals, and `WebSite.name` plus `og:site_name` are the two you control. Without them Google guesses, today most likely from the `<title>`.
- **Understanding who "Lukas Nagel" is.** A single `Person` with `sameAs` links to GitHub, Mastodon, Pixelfed, Bluesky and Instagram is how Google connects the site to those profiles. It is the input to a knowledge panel for your name. Nothing guarantees one, and the name has namesakes, which is exactly why the explicit links matter.
- **No more invalid values.** The `""`, `index.xml` and `mailto:` entries in today's `sameAs` are what a validator complains about.
- **Downside: none.** At worst Google ignores it.

**Why "Lukas Nagel" stays in the title, not the site name (D4).** The ranking value of your name comes from the `<title>` (`LNA-DEV ~ Lukas Nagel`), the page text and the Person node, and this change touches none of those. `WebSite.name` has no ranking weight; it only labels the result. Google asks for a concise name there and ignores values that look like a title, so `LNA-DEV ~ Lukas Nagel` would probably be discarded. `LNA-DEV` matches the domain. `alternateName: ["Lukas Nagel"]` is the name Google falls back to if it does not accept the first.

Caveat, stated honestly: Google reads site names from the domain's home page, and `lna-dev.net/` is a meta-refresh to `/en/`. It may or may not credit markup on `/en/`. Adding it costs nothing either way.

## 5. Every other branch

| Branch | Change |
|---|---|
| **`BlogPosting`** | Only for `.Section == "posts"` **and** a non-zero date. `author` and `publisher` use the §2 stub, with no `logo`. `keywords` is omitted when empty. `wordCount` becomes an integer. `name` stops being hand-quoted (`"{{ … }}"`) and goes through the template's JSON escaping like every other value. The `image` logic stays as it is |
| **New fallback: `WebPage`** | Every other page (links, identity, licensing, projects, reading list, gaming, search, payroll): `name`, `url`, `description`, `inLanguage`, `isPartOf` (the WebSite stub), `publisher` (the person stub). `dateModified` only if `.Lastmod` is non-zero, never `0001` |
| `ImageGallery` | `author` and `publisher` become the person stub. `logo` goes |
| Dex `WebPage` | `publisher` becomes the person stub. `logo` goes. Nothing else changes |
| Photo `ImageObject` | `creator` becomes the person stub **only when `.ResolvedArtist` equals `params.author.name`**. A photo by somebody else keeps a plain `{"@type": "Person", "name": …}`, because giving it the owner's `@id` would say the owner took it. *Added in the build:* when the owner is **in** the photo (`model: lukas-nagel`), its `about` entry is the person stub too. It was an unlinked namesake on the 4 self-portraits, which the §10 check caught |
| Model `ProfilePage` | `publisher` becomes the person stub, and `logo` goes. The owner's own record is the exception — below |

**What "logo goes" means.** Every `publisher` block in the JSON-LD currently carries `"logo": {"@type": "ImageObject", "url": ".../Pingüino.svg"}`. schema.org defines `logo` for organisations and brands, not for people, so on a `Person` it is an invalid property and validators flag it. Removing it changes nothing you can see: the penguin stays as the favicon, the header label and the default link preview. It just stops being claimed as a person's logo in the metadata.

**Model pages are people, and already say so.** Each model page emits a `ProfilePage` whose `mainEntity` is a `Person`, with the name, the cover photo and the links from `data/models.yaml`. That stays as it is for every model.

**The owner as a model (the exception).** For the record named by `params.author.modelSlug` (currently `lukas-nagel`), the model page's `Person` gets the same `@id` as the About page, and its `url` points at the About page. A search engine then sees one person with two pages, not two unrelated people who share a name. The About page is the profile; `/gallery/models/lukas-nagel/` is the photos of that person. The match runs on the slug, never on the name. Every other model is untouched and gets no `@id`, because this site makes no identity claims about other people.

## 6. `BreadcrumbList`

Rebuilt from `.Ancestors.Reverse`, not from splitting the parent's permalink on `/`. The current string-splitting is what drops Home, and it can leave position gaps when a path segment is not a section (`posts/media/` has no `_index`). The new list is Home first, then each ancestor section, then the page itself, numbered 1…n with no gaps. *Corrected in the build:* an ancestor that is never rendered is skipped. `/gallery/photo/` has `build: {render: never}` and therefore no URL, and the first build listed it as `{"name": "Photos", "item": ""}` on all 1,944 photo pages. A photo page's breadcrumb is Home › Photography › the photo. For the About page that is **Home › About me**, which matches the visible breadcrumb. The rest of the site gets the same shape, which is the point: the feedback's complaint was about the template, not about one page.

## 7. The portrait

**Credit as data, not as a caption.** Hugo's own page-resource metadata goes into the About page's front matter, once per language file:

```yaml
resources:
  - src: "Lukas Nagel - Nature Photographer Waiting for the Light on a Moorland Boardwalk.jpg"
    params:
      credit: Jan Göbel
      license: all-rights-reserved   # key into data/licenseMap.yaml
      portrait: true                 # the image §2 uses for Person.image
```

- `layouts/shortcodes/img.html` learns one generic thing: if the resource carries `params.credit`, it emits `ImageObject` microdata around the figure. That covers `contentUrl`, `creator`, `creditText`, a `copyrightNotice` of `© <capture year> <credit>`, and `license` only if the licence resolves to an **absolute** URL, i.e. a public deed. *Corrected in the build:* `all-rights-reserved` does have a URL in `data/licenseMap.yaml`, but it is the site's own `/licensing/`. That page licenses the owner's work and cannot speak for another photographer's, so a site-relative licence URL yields no `license` at all. The capture year is read from EXIF `DateTimeOriginal`, the way the embedding pass does it, and is left out when absent. None of this is visible; it sits in `<meta>`/`<link>` tags, like the gallery's microdata.
- **`showCredit` flag**, default `true`: a small visible "Photo: <credit>" line under the figure (new i18n key `photo_credit`). It only renders when the resource has a `credit`. The About page's three calls pass `showCredit="false"`. It is a shortcode parameter, next to `galleryImage`'s `showTitle`/`showExif`, because whether to *show* something is a per-call rendering choice, while *who took it* is a fact about the file.
- **No `acquireLicensePage`.** The site's licensing page cannot license someone else's work, so pointing at it would be a false statement.
- The JSON-LD `Person.image` (§2) reads the same resource through `site.GetPage params.author.page`. One source feeds both the figure and the structured data, and a static test asserts they agree (§10). Any post that shows a third-party image can use the same metadata. It will show the credit line unless the call turns it off.

## 8. Alias redirects

| Source | Produces |
|---|---|
| `index.en.md` aliases `me`, `about` | `/en/me/`, `/en/about/` |
| `index.de.md` aliases `me`, `about`, `ueber-mich` | `/de/me/`, `/de/about/`, `/de/ueber-mich/` |
| `index.sv.md` aliases `me`, `about`, `om-mig` | `/sv/me/`, `/sv/about/`, `/sv/om-mig/` |
| **`static/about/index.html`** | the root `/about/` → `/en/lukas-nagel/` |

*Corrected in the build:* this section proposed an absolute alias `/about` in the English file for the root redirect, on the assumption that an absolute alias lands at the domain root. **It does not.** Tested on Hugo 0.166 in a scratch site: on a multilingual site Hugo prefixes even an absolute alias with the language (`/elsewhere` in an English file becomes `/en/elsewhere/`). So the root redirect is a static file that copies the page Hugo writes for an alias. Its target is root-relative (`/en/lukas-nagel/`), so the Tor build redirects within the onion site. The target is hard-coded, but it is a URL on the golden list, which may only move together with a redirect, and §10 checks that the file reaches the English About page. Redirect pages are not sitemap entries, so `golden:update` is not needed.

## 9. Link previews (D6)

`og:image` / `twitter:image` on the About page come from a `fit 1200x1200` variant of the portrait instead of the site logo. The branch goes in `get-page-images.html`, next to the gallery ones, and finds the image through the same `portrait: true` resource metadata. `og:type` becomes `profile`, with `profile:username` = `LNA-DEV`, instead of PaperMod's blanket `article` for every page. The site-wide `og:site_name` is covered in §4.

## 10. Tests (`tests/static/html.spec.ts`, *structured data*)

- No JSON-LD date anywhere starts with `0001`.
- `BlogPosting` appears only on `post` pages. The existing test only checks the reverse.
- No node that is a `Person` has `logo`. No `keywords` array is empty. `wordCount` is a number.
- The About page in each language: a `ProfilePage` whose `mainEntity["@id"]` is `<base>/#person`, whose `sameAs` equals `params.schema.sameAs`, and whose `image.creator.name` equals the resource's `credit` in the front matter and the microdata `creator` in the page body. The figure has **no** visible credit line (`showCredit="false"`).
- The owner's model page: its `Person` carries `<base>/#person`. No other model page's `Person` has an `@id`.
- The home page: a `WebSite` and a `Person` with the same `@id`, and every `sameAs` is `https://`. `og:site_name` is present.
- Every `Person` named `params.author.name` carries the `@id`. This is the check that the graph is actually linked.
- Every `BreadcrumbList` starts with the language home, numbers 1…n without gaps, and has a URL on every item.
- The redirects in §8 exist, each pointing at the About page of its language, and `/about/` points at the English one.
- `pageKind` gains `profile` for `/lukas-nagel/`, and the per-theme `@type` table gains `profile: "ProfilePage"`.

## 11. Build order (on "go")

1. `hugo.yaml`: `params.author` (§2), `schema.sameAs` (D5), drop `schema.publisherType`. i18n: `person_job_title`, `photo_credit`.
2. Identity pages ×3: Pixelfed link → `https://pixelfed.de/LNA-DEV`.
3. `schema-person.html` and `schema-person-ref.html`.
4. `schema_json.html`: home (§4), breadcrumb (§6), ProfilePage (§3), the branch table (§5).
5. `img.html`: credit microdata and `showCredit` (§7).
6. About content ×3: `resources:` metadata, aliases (§8), `showCredit="false"`.
7. `get-page-images.html` / `opengraph.html` (§9, and `og:site_name` from §4).
8. Tests (§10).
9. `hugo` into my own directory (warm cache, never cleared), then `npm test`. Then paste the built About, home, one post and one photo page into Google's Rich Results Test and validator.schema.org in **code-snippet mode**, through the browser. That sends page source only; nothing gets published.
10. Report. **No commit, no deploy** unless asked.

## 12. IndieWeb — what it would need (not in this change)

The About page says you are getting into the IndieWeb, but the site has almost none of its markup. Today there is `rel="me"` on the home page's header icons, and nothing else: no h-card, no h-entry, no Webmention endpoint.

| Piece | What it does | Data it needs | Where the data comes from |
|---|---|---|---|
| **h-card** (microformats2) | Your identity, readable by IndieWeb tools, the way the `Person` node is for search engines | `p-name`, `p-nickname`, `u-url` + `u-uid` (the clearnet home page, also in the Tor build), `u-photo`, `p-note` (a one-line bio), `p-job-title`, the `rel="me"` links; `u-email` optional | **Exactly the §2 data**: `params.author`, `schema.sameAs` and the portrait resource. One data set, two formats. The only new field is the bio line, per language |
| **`rel="me"`** | Two-way identity links. They give the verified checkmark on Mastodon, and IndieLogin uses them to sign you in | The profile URLs, **and each profile must link back** to `lna-dev.net` | Today on the home page only, and it wrongly includes the RSS feed (`index.xml`) as "me". The Identity page, the list of "accounts that are genuinely mine", has none, and it is the natural place for them. Checking which profiles link back is a manual step on each platform |
| **h-entry** | Each post as a machine-readable entry, for feed readers, Webmention senders and Bridgy | `p-name`, `e-content`, `dt-published`, `u-url`, `p-author` (h-card), `p-category` | All of it already exists (title, date, content, tags). Template-only |
| **h-feed** | The post list as a feed | Nothing new | List templates. Template-only |
| **Webmention** (receive) | Replies, likes and mentions from other sites, and via Bridgy from Mastodon and Bluesky | An endpoint in `<link rel="webmention" href="…">`, plus a decision about whether and how to show received mentions (moderation, privacy of the people mentioning you) | A static site cannot receive them. It needs webmention.io (a third party) or a receiver in the HomePageCompanion API, which the site already talks to for likes |
| **Webmention** (send) | Notifying the pages you link to | Nothing new | A post-deploy step, for example a script over the RSS feed |
| **IndieAuth** | "Sign in with lna-dev.net" on IndieWeb services | `rel="indieauth-metadata"`, or authorization and token endpoints | A provider. IndieLogin.com works from `rel="me"` → GitHub or email, with nothing to host |
| Micropub | Posting from apps | — | Does not fit a static Hugo site. Skip |

The first four are template work over data that either exists already or that this change creates, which is why §2 keeps the person in one place. Webmention and IndieAuth each need a service decision first.

**Neither Webmention nor IndieAuth is required.** The IndieWeb is a set of principles first: your own domain, your content published there first, and copies sent out to the silos (POSSE). This site already does all three; the Pixelfed and Bluesky auto-posters are POSSE. The markup only makes that machine-readable. Webmention is for interactions *between* sites. IndieAuth is only needed to sign *in* somewhere with the domain, and even then IndieLogin.com does it from `rel="me"` alone, with no endpoint on this site. A useful first stage is h-card + clean `rel="me"` + h-entry, and it needs no service. Webmention and IndieAuth can be added later without changing it, but webmention.io signs you in through IndieLogin, so the `rel="me"` cleanup is the prerequisite for both.

## 13. Deliberately not in this change

- **Page-bundle originals stay published (D2).** `responsive-image.html:33` takes the original's `.RelPermalink` before choosing a variant, so every processable page-bundle image ships its full-size original. For the portrait that is 3 × 5.3 MB, and the files carry the camera's `Artist`, `SerialNumber` and `LensSerialNumber` EXIF. 56 post originals are published the same way. It was decided not to change this.
- `articleBody` stays in `BlogPosting`. It doubles each post's HTML weight, but nobody asked about it, and removing it is a separate trade.
- The gallery microdata's `copyrightNotice` has no year (`© Lukas Nagel`), while the embedded file metadata has one. That is worth aligning, but it is the gallery's business, not the About page's.
- Content nits on the About page itself. The Swedish Privacy paragraph opens "Allmän skola har rätt …" ("Public school has the right …", presumably meant "Alla har rätt …"). The Swedish link text says "Fotografie". And all three languages link the gallery as the absolute `https://lna-dev.net/en/gallery`, which sends German and Swedish readers to the English gallery and leaves the Tor build. **Say the word and I fix these too.** They are one-line edits, but they are prose, and prose is yours.

## 14. Verification (2026-09-24)

| Check | Result |
|---|---|
| `hugo -e production` | No warnings, 15 s with a warm cache |
| `npm test` | 204 passed, 6 skipped (the suite's existing data-dependent skips: no hidden or unlisted model, Chromium-only clipboard), 0 failed |
| The new §10 tests against the **old** deployed `public/` | All 8 fail, so they catch what they were written for |
| Sitewide sweep of the new build | JSON-LD types: `ImageObject` 1,944, `WebPage` 485, `BlogPosting` 20, `ImageGallery` 15, `ProfilePage` 6 (3 About + 3 owner model pages), home `@graph` 8 (3 language homes + 5 paginator pages). No `0001` date, no `logo` on a Person, no empty `keywords`, no unlinked owner Person, no breadcrumb gap. `/en/tools/` is the one dated page outside `posts`; it is now a `WebPage` with its real date, not a `BlogPosting` |
| validator.schema.org (code snippet: About, home, a post, a photo, Links, the owner's model page) | 0 errors, 0 warnings. The home page's `WebSite.publisher` `{"@id": …#person}` resolves to the full Person node |
| Google Rich Results Test (code snippet, production URLs) | **7 valid items**: Article, 3 Breadcrumbs, Profile page, 2 Image metadata. The only notes are "missing `license` / `acquireLicensePage` (optional)" on the portrait, which is deliberate (§7). With the test build's `localhost` URLs Google marks the image items invalid ("Invalid URL in field `url`"). That comes from testing locally, not from the markup |
| Redirects | `/about/` → `/en/lukas-nagel/`; `/en/about/`, `/de/about/`, `/de/ueber-mich/`, `/sv/about/`, `/sv/om-mig/` → their language's About page; `/<lang>/me/` unchanged |
