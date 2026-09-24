# Concept: IndieWeb basics — h-card, `rel="me"`, h-entry

**Status:** **follow-up, not started.** It starts after `about-page-structured-data.md` has landed, because it reads the person data that change introduces: `params.author`, `params.schema.sameAs` and the About page's `portrait: true` resource.
**Measured:** 2026-09-24, against `.test-site/` of 2026-09-21 and one read-only `curl` of the live root.

The About page says its author is getting into the IndieWeb. In practice the site already follows the principles: its own domain, content published here first, and copies sent out to other platforms (POSSE, which is what the Pixelfed and Bluesky auto-posters do). But its markup says almost none of this. This concept is the first stage: **markup only**. No service, nothing hosted, no visible change.

Webmention and IndieAuth are **not** part of it, and neither is required; `about-page-structured-data.md` §12 explains why. Both can be added later on top of this without changing it.

## Today

| | |
|---|---|
| `rel="me"` | 8 links, **on the home page only**. They come from `layouts/partials/social_icons.html`, which puts `me` on *every* icon, including the RSS feed (`index.xml`) and the notification button (`href="#"`). Neither of those is an identity. The Identity page, whose whole purpose is to list "the accounts that are genuinely mine", has no `rel="me"` at all |
| h-card | None |
| h-entry / h-feed | None |
| Machine-readable dates | None. PaperMod's `post_meta.html` (not overridden here) prints `<span title='2024-01-27 20:45:02 +0100 CET'>January 27, 2024</span>` |
| The root URL | `https://lna-dev.net/` answers with an **HTTP 301** to `/en/` (nginx, verified live). Tools that follow redirects, such as IndieLogin and Mastodon's link verification, therefore reach the English home page. Hugo's meta-refresh `index.html` at the root is never served there, and nothing here may depend on it |

## Goal

1. Given `lna-dev.net`, a microformats2 parser finds a **representative h-card** with name, nickname, URL, uid, photo and a one-line bio.
2. `rel="me"` points at **exactly** the author's identities, on the home page and on the Identity page, and each of those profiles links back.
3. Every post parses as an **h-entry** with name, summary, content, published date, URL, author and categories.
4. The post lists parse as an **h-feed**.
5. **Nothing changes visually.** The work is classes, a `<time>` element in place of a `<span>`, and invisible `<data>` values.

## 1. The representative h-card (home page)

- **Where:** the `home-info` box the home page already shows (`partial "home_info.html"` in `layouts/_default/home.html`), with the social icons inside it. The home page is where IndieWeb tools look.
- **Data**, all of it from the About change except the bio:
  - `p-name` ← `params.author.name`
  - `p-nickname` ← `params.author.alternateName`
  - `u-photo` ← the portrait (the same `fit 1200x1200` variant as `og:image`)
  - `p-job-title` ← i18n `person_job_title`
  - `u-url` / `u-uid` ← see below
  - `p-note` ← **new**: a one-line bio per language, which you write
- **How, with no visible change:** microformats2 reads a `p-*` value from `<data value="…">` and a `u-*` value from `<data value="…">` as well. The box keeps its look, and the name, photo and URLs ride along as `<data>` elements inside it.
- **URL and uid.** The representative-h-card rule wants an h-card whose `u-url` and `u-uid` match the URL of the page the parser landed on. After the 301 that is `https://lna-dev.net/en/`. So each language home sets `u-uid` and `u-url` to its own clearnet URL, plus a second `u-url` for the bare `https://lna-dev.net/`. These are **clearnet URLs in the Tor build too**, the same rule the metadata-embedding pass follows: the identity is the clearnet domain.
- The partial is one new file, `layouts/partials/h-card.html`. Posts reuse it in small form as their `p-author` (§3).

## 2. `rel="me"`

- **`social_icons.html`:** `me` only on an icon whose URL is in `params.schema.sameAs`, plus `mailto:`. IndieLogin can sign you in by email through a `mailto:` `rel="me"`, and that is the IndieWeb convention. The RSS and notification icons lose `me`, and so does Matrix: `matrix.to` is a redirector and can never link back. Every icon stays visible.
- **Identity page:** its Markdown links cannot carry a `rel` attribute, so the existing `layouts/_markup/render-link.html` hook adds `rel="me"` to a link when the page sets `relMe: true` in its front matter **and** the link's URL is in `params.schema.sameAs`. The list of identities therefore stays one list in `hugo.yaml`. A link on the Identity page that is not in it gets no `me`, which covers Matrix and the project domains (`fedodo.*`, `fachinformatiker…`), because controlling a domain does not make it a profile of you. All three language files get the flag.
- **Back-links**, checked by hand during implementation from the public profile pages: every profile should list `https://lna-dev.net` in its website field. GitHub (profile *Website*), Mastodon (a profile metadata field; this is what gives the verified checkmark), Pixelfed (*Website*), Instagram (the bio link). Bluesky needs nothing, because its handle *is* the domain, verified through DNS/HTTP rather than `rel="me"`. I report what I find. Changing a profile is yours to do.

## 3. h-entry on posts

Only for `.Section == "posts"`, in the generic `<article class="post-single">` branch of **both** `layouts/_default/page.html` and `single.html` (the same pair the theme dispatch lives in). The About, Links and Identity pages are not entries and get none of this.

| Property | On |
|---|---|
| `h-entry` | `<article class="post-single">` |
| `p-name` | the `<h1 class="post-title">` |
| `p-summary` | `.post-description` |
| `e-content` | `.post-content` |
| `dt-published` / `dt-updated` | `post_meta.html`, **overridden**: the date `<span title=…>` becomes `<time datetime="…" title=…>` with the same visible text. `dt-updated` only when `.Lastmod` differs from `.Date` |
| `u-url` | `<data class="u-url" value="{{ .Permalink }}">` |
| `p-author h-card` | the author name in the post meta (`layouts/partials/author.html`), carrying the name and the About page URL; nothing about it becomes a link |
| `p-category` | each tag link in `.post-tags` |

## 4. h-feed on the post lists

The home page's post list (`layouts/_default/home.html`) and the section lists (`layouts/_default/list.html`, around `post_meta.html` at line 236) get an `h-feed`. Each `<article class="post-entry">` in them becomes an `h-entry`: `p-name` on its `<h2>`, `u-url` on the existing `<a class="entry-link">`, `p-summary` on the excerpt, and `dt-published` from the same `post_meta.html` override. On the home page the feed's author resolves to the representative h-card of §1 by the standard authorship rules, so no entry needs its own author.

## 5. Tests

- **A real parser, not regexes over class names.** `microformats-parser` (npm, pure JavaScript, MIT) goes in as a devDependency. A regex would only check the spelling of the class names; the parser checks what a consumer actually reads. It runs offline, so it keeps to the suite's no-network rule.
- The home page in each language: exactly one h-card, with `name`, `nickname`, `photo`, `note`, and a `url`/`uid` equal to that page's clearnet URL.
- `rels.me` on the home page = the `sameAs` URLs among the icons + `mailto:`, and nothing else (no `index.xml`, no `#`).
- `rels.me` on the Identity page, all three languages = `params.schema.sameAs`.
- Every post page: exactly one h-entry, `published` is ISO 8601 and not `0001`, `url` equals the canonical URL, and `author.name` equals `params.author.name`.
- `/<lang>/posts/` and the home page parse as an h-feed with as many entries as they show.
- No other page (About, Links, gallery, dex …) contains an h-entry.

## 6. Build order

1. `social_icons.html`: the `rel="me"` rule (§2).
2. `render-link.html` + `relMe: true` on the three Identity files (§2).
3. `layouts/partials/h-card.html`, then placed in the home-info box (§1). i18n: the `p-note` bio (your text).
4. The `post_meta.html` override, `author.html`, and the h-entry classes in `page.html` / `single.html` and on the tag links (§3).
5. h-feed and h-entry on the list and home templates (§4).
6. Tests (§5).
7. `hugo` into my own directory with a warm cache, then `npm test`. Then paste the built home page, the Identity page and one post into php.microformats.io's HTML box, through the browser. That sends page source only, and nothing is published. Then run the back-link check from §2.
8. Report. **No commit, no deploy** unless asked.

## Decisions to take when this starts

| | Recommendation |
|---|---|
| h-card: invisible `<data>` values, or a visible name and photo in the home box | **Invisible.** The goal is no visual change; putting a face on the home page is a design decision, not an IndieWeb one |
| `rel="me"` on Matrix | **No.** The icon stays, and the `me` goes |
| `rel="me"` on `mailto:` | **Keep.** It is the IndieWeb convention, and IndieLogin's email sign-in relies on it |
| The `p-note` bio | **You write it**, one line per language. It is prose |
| `microformats-parser` as a devDependency | **Yes**; see §5 |

## Not in this stage

Webmention (receiving and sending), IndieAuth endpoints, Micropub, Bridgy backfeed, `u-syndication` links to POSSE copies, and gallery photo pages as h-entries. Each needs either a service or a decision of its own. None of them needs any of the above to be redone.
