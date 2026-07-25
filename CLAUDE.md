# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hugo static site for `lna-dev.net` (personal site of Lukas Nagel). Theme is `hugo-PaperMod`, pulled in as a Hugo Module via `go.mod` (no submodules). Trilingual: English (default), German, Swedish — each language gets its own subdirectory in URLs (`defaultContentLanguageInSubdir: true`).

## Build / Deploy

- Local build: `hugo` — output goes to `public/`.
- Local server: `hugo server -D` (drafts on).
- Deploy: `./deploy.sh` builds twice (clearnet + Tor onion `baseURL`) and rsyncs `public/` to the production server. **Do not run this without the user's say-so** — it pushes live.
- Module bootstrap (only if `go.sum` is missing/broken): `go mod download`.
- Image binaries are intentionally **not in git** and live outside the repo. Hugo mounts them in via `module.mounts` in `hugo.yaml`: the gallery `source` is the repo-root **`gallery-photos`** symlink (gitignored) → the local photo store, mapped to the `assets/images/gallery/` virtual path. Per machine, create the symlink once: `ln -s <photo-store> gallery-photos`. A clean checkout without it builds fine but renders an empty gallery. (Hugo ignores symlinks during resource discovery — which is why the old `assets/images/gallery` directory symlink silently produced an empty gallery — but it *does* resolve one given explicitly as a mount `source`. See memory `project_gallery_mount.md`.)

## Architecture

### Gallery system (the load-bearing part of the site)

The gallery was recently restructured (see memory `project_gallery_overhaul.md`). The model is **one flat image folder + central YAML metadata + theme dispatch**. Understanding this is essential before touching any gallery template.

- **Image source of truth**: the local photo store, mounted to the `assets/images/gallery/` virtual path (via the `gallery-photos` symlink + `module.mounts` — see Build / Deploy). All photos sit flat there as global resources regardless of which view they appear in; templates address them as `images/gallery/*`, unaffected by where the files physically live.
- **Metadata source of truth**: `data/gallery.yaml` — one entry per image with `id` (UUID, stable across renames), `src` (current filename), `category`, `section` (`general` | `archive`), `project` (slug or empty), `portfolio` (bool), `tags`, `alt`, `title`, `license`, `artist`. The `src` field must exactly match the image filename. The `id` is the **stable identifier** used by deep links, the likes API, and `featured_image:` references — when a filename changes, only `src` is updated; `id` stays.
- **Two cached partials underpin everything else**:
  - `layouts/partials/gallery-images.html` — returns all gallery image resources via `resources.Match "images/gallery/*"`. Global resources are inherently language-independent. Always call via `partialCached`. Note: `.Name` on these resources returns a full path like `images/gallery/photo.jpg` — use `path.Base` when looking up by bare filename.
  - `layouts/partials/gallery-meta.html` — returns `{ bySrc, byId }`, two dicts sharing the same metadata entries. `bySrc` is keyed by bare filename (use `path.Base` on resource `.Name` to match); `byId` is for UUID lookups (`featured_image`, etc.). Hard-fails the build if any entry lacks an `id` — run `scripts/add-gallery-ids.py` to populate one. Always call via `partialCached`.
- **`layouts/partials/collect-images.html`** is the single entry point for collecting+filtering images. It merges YAML metadata with EXIF/XMP, resolves license via `data/licenseMap.yaml` (errors hard if a license string isn't mapped), and resolves artist (data → EXIF → `site.Params.author.name`). Filter keys: `category`, `section`, `portfolio`, `project`, `excludeArchive` (default true). Each returned item exposes `.Id` (UUID from YAML) — use it as the stable identifier in any new template. Use this — do not iterate the bundle directly.
- **`layouts/partials/resolve-featured-image.html`** resolves a `featured_image:` front-matter value (UUID, with legacy filename fallback) to a bundle resource. Used by `get-gallery.html` and `templates/_funcs/get-page-images.html`.
- **Theme dispatch**: gallery pages select a renderer through their front-matter `params.theme`, branched in `layouts/_default/list.html` and `layouts/_default/single.html`. Themes:
  - `gallery-home` → `content/gallery/_index.*` — hero portfolio + nav cards to Projects/General + Archive link.
  - `gallery-general-home` → `content/gallery/general/_index.*` — all non-archive images with category filter bubbles (`gallery-filter-bubbles.html`, JS-only client-side filtering on `data-category`).
  - `gallery-archive` → archive view (forces `section=archive` filter).
  - `gallery-portfolio` → curated subset (`portfolio: true`).
  - `gallery-projects-list` → index of project mini-albums.
  - `gallery-project` → single project album (filters by `project_slug`).
  - `gallery-page` / `gallery-page-hidden` → generic gallery single pages.
- **Lightbox**: PhotoSwipe, wired up in `assets/js/lightbox.js`; thumbnail and full-size images are generated by Hugo image processing in `gallery.html` (600px and 4000px fits).

### Software projects page (different from gallery projects)

`content/projects/index.{en,de}.md` lists the user's software projects in front-matter (`projects:` array). Rendered by `layouts/projects/single.html`, which fetches live GitHub stats per repo/org via `resources.GetRemote` against the GitHub API (allowed by the `security.http.urls` whitelist in `hugo.yaml`). Don't confuse these with gallery `projects/` (photo series).

### Activity feed

`content/feed/_index.*` + `layouts/feed/list.html` builds a unified activity timeline by merging:
1. All `RegularPages` in the `posts` section across all languages (`lang.Merge`),
2. Photos from the gallery headless bundle (filtered to non-archive, dated >2000),
3. Talks from `data/talks.yaml`.

Items are grouped by year/month and filterable client-side. Photo permalinks use `#<FNV32a hash of RelPermalink>` so they jump to the right gallery item — `gallery.html` writes the matching `data-id` attribute. Keep this hash scheme consistent if you change either side.

### RSS

Custom `layouts/_default/rss.xml`. The gallery overhaul preserves RSS URL stability — when moving images around, generate redirects rather than breaking old item links.

### Reading list

Books the user has read. **Data**: `data/reading.yaml` — a flat list, one entry per book. Fields: `title`, `series` (optional), `author`, `genres[]`, `year`, `link`, `cover`, `pages`, `originalLanguage` (2-letter code), `languagesRead[]` / `languagesListened[]`, and optional `rating` (1–5), `dateRead` (`"YYYY-MM-DD"`, drives the `recentReading` preview order), `notes`. **Covers**: committed JPEG/WebP files in `assets/images/books/covers/`, referenced as `images/books/covers/<Title>.<ext>` and resized to a 200×300 fit by Hugo. Unlike gallery photos, these images *are* in git. Rendered by `layouts/shortcodes/readingList.html` (full list) and `layouts/shortcodes/recentReading.html` (profile-page preview).

**Adding a book — use `scripts/add-book.py`** (stdlib only; see `AGENTS.md` for the full workflow). It looks the book up on Open Library (free, no key), downloads the cover into the covers folder, and appends a YAML entry (`--append`) or prints a paste-ready block. It auto-fills `title`/`author`/`year`/`pages`/`cover`, proposes a `link` (Wikipedia → Open Library → Goodreads-search, always verify), and suggests `genres` mapped onto the existing vocabulary. It **cannot** know `originalLanguage`, `rating`, `dateRead`, `languagesRead`/`languagesListened` — those are left as TODO/empty for a human. Always eyeball the link and genres before committing (subject mapping produces occasional false positives). Do **not** run `./deploy.sh` after adding — that is a separate, explicitly-authorized step.

### i18n

UI strings in `i18n/{en,de,sv}.yaml`. Per-language menus, descriptions, and home content live under `languages.<lang>.params` in `hugo.yaml`. Content files use `index.<lang>.md` for branch bundles and `_index.<lang>.md` for sections.

## Conventions worth knowing

- Use Hugo image processing (`images.Process`, `images.AutoOrient`) — never reference raw image URLs directly, and always `AutoOrient` first so EXIF rotation is applied.
- New gallery images: drop the file into the photo store (the `gallery-photos` mount target), then add a matching entry to `data/gallery.yaml` **including a UUID `id`** (the build will hard-fail without one — `scripts/add-gallery-ids.py` populates missing ids in bulk).
- Renaming an existing gallery image: rename the file in the photo store (`gallery-photos` target) and update only the matching `src:` in `data/gallery.yaml`. Do not touch `id` — deep links, the likes API key, and any `featured_image:` referencing it all use the id.
- New license values must be added to `data/licenseMap.yaml` or the build will `errorf`.
- Gallery scripting/migration helpers are written in Python (per project memory).
