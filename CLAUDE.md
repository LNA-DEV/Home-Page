# CLAUDE.md

Hugo static site for `lna-dev.net` (personal site of Lukas Nagel): posts, a photo
gallery with a species dex, a reading list, games and travel. Theme is
`hugo-PaperMod`, pulled in as a Hugo Module via `go.mod` (no submodules).
Trilingual: English (default), German, Swedish — each language gets its own
subdirectory in URLs (`defaultContentLanguageInSubdir: true`).

This file holds the rules and the map. The details are in `docs/` — read the
matching doc before touching its area (table at the end).

## Working rules

### Talk first, build on "go"

- A request opens a discussion. First lay out what would change, where, and what
  it affects (SEO included, see below) — then wait.
- Files are edited, and commands that write are run, only after an explicit
  **"go"**. Answers to open questions, "sounds good" or "let's do it" during the
  discussion are not a go.
- Before the go, read-only work is fine: reading, searching, a build into a
  scratch directory to check something. A plan in `docs/concepts/` that is under
  discussion may be edited.
- A go covers what was discussed. Anything outside it that turns up during the
  work goes back to discussion first.
- A request that already carries the go ("… go", "do it right away") counts as one.
- After a go on a concept in `docs/concepts/`, implement its whole build order in
  one turn and report at the end, rather than stopping after each phase.

### Never commit unasked

- Commit and push only when explicitly asked. A go is not a commit, and neither
  is finished work.
- A commit message is one short lowercase English line in the style of the
  history (`model pages`, `fix photo page slug`): no body, no Claude or
  `Co-Authored-By` attribution.
- `.claude/settings.json` turns Claude Code's commit and PR attribution off, and
  `.claude/hooks/check-commit-msg.py` blocks any `git commit` that is not a
  single short lowercase `-m` line.

### SEO is part of every change

Every proposal states what the change does to search — one line if nothing:
*SEO: no effect*. Check at least:

- **URLs** — does a published URL (page, photo, image file, feed) move or
  disappear? It needs a redirect (`aliases`, `slugAliases`, the nginx maps), and
  the golden-list rule below applies. Rewording a photo's English title moves its
  page *and* its image URLs.
- **Indexing** — `noindex`, sitemap membership, canonical, `hreflang`
  (`translationKey`). All of it goes through `robots-indexable.html`; never a
  `robots.txt` `Disallow` for something meant to be noindexed.
- **Titles and text** — `<title>`, meta description, headings, `og:*`, alt text,
  in all three languages.
- **Structured data** — valid, every URL absolute, never more than the visible
  page says.
- **Weight and speed** — HTML size (`/gallery/general/` is close to the 2 MB
  Googlebot reads), image sizes and `srcset`, `width`/`height` against layout
  shift, render-blocking CSS/JS.
- **Internal links** — nothing left pointing at a removed or renamed page; new
  pages are reachable.

Where SEO trades against something else (privacy, URL stability, a clean
structure), name the trade-off and let the owner decide. Where it all lives:
`docs/seo.md`.

### English in the repo

Code, comments, identifiers, script output, commit messages and all
documentation (`CLAUDE.md`, `docs/`, READMEs) are English, whatever language the
conversation is in. The exception is the site's translated text: German and
Swedish content files, `i18n/{de,sv}.yaml`, and the `de`/`sv` values in `data/`.

### Knowledge lives in the repo

- No local memory: auto memory is off for this repo (`.claude/settings.json`),
  and no notes are kept anywhere else outside it either.
- What is worth keeping goes into the repo, where it belongs: how to work here and
  the hard rules → this file; how something works or how to do X →
  `docs/<topic>.md`; why something is built this way → `docs/concepts/`.
- When a correction, a lesson or a measurement comes up, propose the exact line
  and its file at the end of the answer; it is written with the go, like any
  other change. Documentation that belongs to a change is part of that change.
- A doc that contradicts the code is reported, not silently worked around.

### Working with the owner

- When the owner says an issue is fine or already handled, stop touching it, and
  never re-apply a change the owner reverted.
- When proposing custom code, name the existing library or tool that could do the
  job and say concretely why the custom route wins (or loses).
- Run `npm test` only when asked (`docs/testing.md` has the shorter path for the
  golden list).

## Hard rules

- **Never render into RAM** — no `hugo --renderToMemory`, no plain `hugo server`
  (which renders to memory by default). The site is far too large for it (~7.8 GB
  of gallery output); it has crashed every machine it ran on, more than once.
  Build to disk: `hugo -d <scratch dir>`, or `npm test`. A PreToolUse hook in
  `.claude/settings.json` (`.claude/hooks/block-hugo-memory.py`) blocks both; do
  not try to get around it.
- **Never run `./deploy.sh` without the owner's say-so** — it pushes live.
- **Never clear the image cache** (`resources/_gen/`, `hugo --gc`): a cold
  rebuild runs past ten minutes (`docs/build-deploy.md`).
- **Never write to the photo store** — darktable's export target and a Nextcloud
  share. Only build output is touched; image binaries are not in git.
- **Process an image only through `layouts/partials/image-variant.html`**
  (`docs/gallery/images.md`).
- **A warning blocks a deploy.** Every Hugo `WARN` fails the build test; loosen
  one through `ignoreLogs` in `hugo.yaml`, keyed by warning id, never by
  weakening a test.
- **A new published URL needs `npm run golden:update`**, and a retired one may
  only leave `tests/golden/published-urls.txt` in the commit that adds its
  redirect.
- **Scripts never run git.** Pull, review, commit and push are the owner's steps.

## Commands

- `hugo -d <scratch dir>` — build to disk.
- `npm test` — the deploy gate; it builds into `.test-site/`, never `public/`
  (only `deploy.sh` writes that).
- `hugo server -D --renderToDisk` — the owner's dev server, not Claude's.
- Once per machine: `cp config/_default/module.yaml.example
  config/_default/module.yaml` and put that machine's photo-store path in the
  gallery `source` (`docs/build-deploy.md`).

## Where the details are

| Before touching… | read |
|---|---|
| building, deploying, the gallery mount, the image cache, nginx | `docs/build-deploy.md` |
| tests, the golden URL list, checking a page by hand | `docs/testing.md` |
| URLs, indexing, structured data, link previews, Search Console | `docs/seo.md` |
| Hugo templates in general, content adapters, Markdown links | `docs/conventions.md` |
| CSS and styling: colours, spacing, type, widths, breakpoints, the styleguide | `docs/design-system.md` |
| `data/gallery.yaml`, gallery templates, adding or renaming photos, licences | `docs/gallery/overview.md` |
| image processing, served file names, embedded metadata, image redirects | `docs/gallery/images.md` |
| photo pages and their URLs | `docs/gallery/photo-pages.md` |
| photo tags, taxonomy and term pages | `docs/gallery/tags.md` |
| `galleryImage` / `galleryImageText` in a post | `docs/gallery/in-posts.md` |
| project essays and journals, `data/galleryAreas.yaml` | `docs/gallery/project-stories.md` |
| the photo dex, `data/dex.yaml`, the dex scripts | `docs/gallery/dex.md` |
| models, `data/models.yaml` | `docs/gallery/models.md` |
| cameras and lenses, `data/gear.yaml` | `docs/gallery/gear.md` |
| games, game pages, achievements, `data/gamePages.yaml` | `docs/gaming/overview.md` |
| the Steam, Epic and GOG syncs, gaming devices | `docs/gaming/syncs.md` |
| the reading list, adding a book | `docs/reading-list.md` |
| maps, the basemap, route maps | `docs/maps.md` |
| `/travel/` and trips | `docs/travel.md` |
| the newsletter | `docs/newsletter.md` |
| software projects page, activity feed, RSS, `security.txt`, i18n, the other-languages block and the root page | `docs/site.md` |
| writing, reviewing or proofreading a post, posts in more than one language | `docs/posts.md` |
| why something is built the way it is | `docs/concepts/<topic>.md` — design records; their status lines can lag behind the code |
