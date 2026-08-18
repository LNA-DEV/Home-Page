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

### Gaming

Games the user has played, modelled on the reading list. **Data**: `data/gaming.yaml` — a flat, unordered list, one entry per game, written by **multiple sources**. The `platform` field is the discriminator (`steam` | `epic` | `gog` | `switch` | `playstation` | `manual` | …). Fields: `title`, `platform` (both required), `appid` (Steam only — the **stable key** the Steam sync matches on) / `appName` (Epic + GOG — the stable key those syncs match on; for GOG it's the numeric product id), `playtimeMinutes`, `lastPlayed` (`"YYYY-MM-DD"`), `achievementsUnlocked` / `achievementsTotal`, `cover`, `link`, and the optional human-owned `rating` (1–5), `genres[]` / `tags[]`, `notes`, `extraMinutes` (hand-entered untracked/estimated minutes, **added to `playtimeMinutes`** in every UI total — folded in at the `gaming-merged.html` sum). **Covers**: committed JPEGs in `assets/images/games/covers/` named after the game title (`<Title>.jpg`, like book covers — `scripts/sync-steam.py` writes them that way), referenced as `images/games/covers/<file>` — in git, unlike gallery photos. **Rendered by** `layouts/shortcodes/gamingList.html` — a Steam-library-style cover grid at `/gaming/` with a stats header (game count, total hours, achievements), client-side sort (playtime / recently-played / A–Z), and a platform-filter row shown only when ≥2 distinct platforms are present — plus `layouts/shortcodes/recentGaming.html`, a recently-played preview row on the About page mirroring `recentReading`. Content pages are `content/gaming/index.{en,de,sv}.md` (leaf bundles whose body is just `{{< gamingList >}}` — no `theme` dispatch); styles are `assets/css/extended/gamingList.css` + `recentGaming.css` (auto-bundled, theme-variable-based so they work in light/dark); i18n lives under the `# Gaming` block in `i18n/{en,de,sv}.yaml`. Covers are resolved with `resources.Get .cover` + `.Fill "300x450"` for uniform tiles, with a title placeholder when a `cover` is absent. Not in the nav menu (reached via the About preview + the `/gaming/` URL), matching the reading list. **Hiding a game**: add its exact `title` to the `titles:` list in `data/gamingIgnore.yaml` (case-insensitive, whitespace-trimmed) — the entry stays in `data/gaming.yaml` and keeps syncing, but is dropped from every view. The filter lives at the shared choke point `layouts/partials/gaming-merged.html` (used by both `gamingList` and `recentGaming`), so it applies to the grid, the stats header, and the About-page recent row alike.

**Syncing Steam — use `scripts/sync-steam.py`** (stdlib only; see `AGENTS.md` for the full workflow). It owns only the `platform: steam` entries: it fetches the owned-games library from the Steam Web API, optionally per-game achievements + portrait covers, and **rebuilds** those entries (new games added, de-listed games pruned) as the last block in the file, below a marker it emits. Everything that is **not** `platform: steam` is left byte-for-byte untouched (raw-text editing, no YAML dep), so hand-added games are safe. Human-owned fields (`rating`/`genres`/`tags`/`notes`/`extraMinutes`) on a Steam entry are preserved across syncs — re-emitted verbatim, keyed by `appid` (keep them single-line). Needs `STEAM_API_KEY` + `STEAM_ID` (env or flags; never commit them). Default excludes 0-playtime games (`--include-unplayed` to keep them). Do **not** run `./deploy.sh` after syncing — separate, explicitly-authorized step.

**Syncing Epic — use `scripts/sync-epic.py`** (stdlib only; see `AGENTS.md`). Epic has **no** Steam-style public API, so this merges **two disjoint sources**, both already on disk from the **Heroic** launcher (no separate login): the owned library + Heroic-launched playtime (`store_cache/legendary_library.json` + `store/timestamp.json` under the Heroic config), and — by reusing the Epic OAuth refresh token Heroic stored (`legendaryConfig/legendary/user.json`) — the *historical* official-launcher playtime from Epic's private `library-service` cloud endpoint. A play session is launched by exactly one client, so the two are disjoint and `playtimeMinutes = heroic + cloud` per game, matched on the Epic `appName` (`artifactId` in the cloud response). It owns only `platform: epic` entries, rebuilds them as a marked block last in the file (mirroring the Steam sync), preserves human fields keyed by `appName`, and defaults to played-only (`--include-unplayed` to keep the rest). **No achievements** — Epic closed the achievement-progress API in Jan 2025. `--no-cloud` uses only the Heroic-local data (no token needed); if the cloud token is stale, **open Heroic once** to re-auth, then rerun. Do **not** run `./deploy.sh` after syncing — separate, explicitly-authorized step.

**Syncing GOG — use `scripts/sync-gog.py`** (stdlib only; see `AGENTS.md`). Modelled on the Epic sync — GOG also has **no** Steam-style public API, so it reads what the **Heroic** launcher cached on disk and (optionally) reaches GOG's cloud with the token Heroic stored: the owned library + Heroic-launched playtime (`store_cache/gog_library.json` + `store/timestamp.json`), and — by reusing the GOG OAuth refresh token in `gog_store/auth.json` (Galaxy client id) — GOG's authoritative per-game playtime (`gameplay.gog.com/…/sessions` → `time_sum`) and achievements (`gameplay.gog.com/…/achievements`). **Two differences from Epic:** (1) playtime is **prefer-cloud, NOT summed** — Heroic pushes its sessions up to GOG so the cloud total already contains them, and the script takes `max(cloud, local)` to avoid double-counting; (2) **achievements ARE set** (GOG exposes them, the win over Epic — though sparse until games run through GOG's achievement service). `lastPlayed` comes from Heroic's `store/timestamp.json`, but Heroic frequently records playtime with an empty date (and GOG's playtime API carries no date); as a fallback the script reads the GOG cloud-save sync time from `gog_store/saveTimestamps.json` (`_save_date`), used only when Heroic has no date and only for games that use GOG cloud saves. It owns only `platform: gog` entries, keyed on `appName` (the numeric GOG product id), rebuilds them as a marked block last in the file (after the Steam/Epic blocks), preserves human fields, and defaults to played-only. The cloud is a per-game fan-out (~one request per owned game); `--no-cloud` uses only Heroic-local data (no token). If the token is stale, **open Heroic once** to re-auth. Do **not** run `./deploy.sh` after syncing — separate, explicitly-authorized step.

### Photo dex

A Pokédex-style species checklist at `/gallery/dex/`, layered on top of the gallery rather than beside it: which animals the gallery already contains, and which are still open. Ported from the `animal-dex` proof of concept (`../animal-dex`), but restructured to this repo's conventions — central data file + templates, not one page bundle per species.

**Data**: `data/dex.yaml` — one record per species, ~190 of them. Language-neutral facts (`slug`, `number`, `scientific`, `family`, `group`, `difficulty`, `iucn`, `gbif_taxon_key`, `inat_taxon_id`, `wikidata_id`, `height`, `body_weight`, `diet`, `lifespan`) sit at the top level; anything that reads as prose is nested per language under `names` / `description` / `habitat` / `tips.best_time` / `tips.approach` and **falls back to `en`** (via `layouts/partials/dex-text.html`) when a language is missing. `diet` is a slug translated through i18n, not free text. Optional `sightings: [{lat, lng, label, date}]` are hand-entered — only 13 of 633 gallery photos carry GPS EXIF.

**The join**: `data/gallery.yaml` entries gained an optional `species: <slug>` field. **A species counts as photographed when at least one gallery entry carries its slug** — there is no separate caught/uncaught flag to keep in sync, and archive photos count (they just sort last). 158 of the 168 `category: animals` photos are tagged, covering 44 species.

**`layouts/partials/dex-index.html`** is the single join point and the thing to reach for in any new dex template. Called via `partialCached`, it returns `{all, bySlug, caught, total, groups}`; each entry carries `slug`, `number`, `group`, `caught`, `species` (the raw record), `photos` (portfolio → current → archive) and `cover`. `collect-images.html` gained matching `Species` / `Section` / `Portfolio` fields and a `species` filter key.

**Pages** are generated by a **content adapter**, not by content files: `content/gallery/dex/_content.{en,de,sv}.gotmpl` each call `layouts/partials/dex-pages.html`, which does the `.AddPage` loop. There is one adapter per language because Hugo scopes an adapter to the language of its filename — a bare `_content.gotmpl` only produces pages for English. Species pages set `params.theme: dex-species` plus `filter_species`/`include_archive`, so the photo strip is the ordinary `gallery.html` partial and inherits PhotoSwipe, the like counters and the EXIF captions for free.

**Theme dispatch**: `dex-home` in `layouts/_default/list.html` → `dex-overview.html`; `dex-species` in **both** `page.html` and `single.html` → `dex-detail.html`. The gallery home has a fourth nav card (`dex_cover` param picks its image, else the first tagged animal photo).

**Map** (`dex-map.html` + `assets/js/dex-map.js`): the default view is **entirely local** — Natural Earth land/borders drawn as GeoJSON instead of raster tiles, plus the species' simplified iNaturalist range and any sighting pins. A species page therefore makes **zero third-party requests** on load, which is what makes it usable on the Tor onion build. A "detailed map" button is the explicit opt-in that swaps the drawn world for OpenStreetMap tiles + the GBIF density overlay; the range polygon stays on top in both modes. Leaflet is already vendored at `/packages/leaflet/` and is loaded per-page from `head.html`, not site-wide.

Three things in that file are load-bearing and easy to break:
- **Every vector layer is drawn at three longitude offsets** (`COPIES = [-360, 0, 360]`). A raster base repeats forever but a GeoJSON world is drawn once, so land, borders, ocean and range must all be duplicated together — duplicating only the range leaves its copies floating over empty sea at the edges of a zoomed-out map. Panning is capped at ±360° so there is always a further copy past the edge, and `worldCopyJump` is **off** (it would snap the view for no gain now that the overlays exist in every copy).
- **Stacking order is pinned by panes**, not by load order: `dex-land` 410 → `dex-range` 420 → `dex-ocean` 430 → `dex-lines` 440. These are independent fetches that finish in any order, and a shared renderer paints as layers arrive — which once put the range *underneath* the land, visible only over the sea.
- **The ocean layer is a mask.** iNaturalist's geomodel is a thresholded prediction raster, so a widespread terrestrial species' polygon genuinely covers open water (wild boar contains the north Pacific in the raw source data — this is not a simplification artifact). Repainting the ocean over the range clips it to the coastline. Species with `marine: true` in `data/dex.yaml` skip that layer, or whales, sharks, sea turtles and penguins would be masked down to nothing — 22 species carry the flag.

**Committed assets** (unlike gallery photos, these *are* in git): `assets/data/dex/world-{land,borders}.geojson` (Natural Earth, public domain, ~215 KB), `assets/data/dex/ranges/<slug>.geojson` (iNaturalist, CC BY 4.0, 173 species, ~5 MB — simplified and coordinate-rounded to fit a 45 KB per-species budget), and `assets/images/dex/reference/<slug>.jpg` (Wikimedia Commons 320px stand-ins, fetched only for species with no photo of the user's own, always rendered dimmed and credited).

**Scripts** (stdlib only, sharing `scripts/dex_common.py` for the YAML reader/writer): `dex-import.py` (one-shot animal-dex import), `dex-add.py` (add one species by hand, auto-numbered), `dex-tag-photos.py` (propose `species:` for gallery photos; carries a `MANUAL` table of visually identified files and refuses to guess), `dex-enrich.py` (fill *empty* fields only, from GBIF/Wikidata/Wikipedia), `dex-ranges.py`, `dex-covers.py`. Full workflow in `AGENTS.md`. Styles are `assets/css/extended/dex.css`; i18n lives under the `# Photo dex` block in `i18n/{en,de,sv}.yaml`.

### i18n

UI strings in `i18n/{en,de,sv}.yaml`. Per-language menus, descriptions, and home content live under `languages.<lang>.params` in `hugo.yaml`. Content files use `index.<lang>.md` for branch bundles and `_index.<lang>.md` for sections.

## Conventions worth knowing

- Use Hugo image processing (`images.Process`, `images.AutoOrient`) — never reference raw image URLs directly, and always `AutoOrient` first so EXIF rotation is applied.
- New gallery images: drop the file into the photo store (the `gallery-photos` mount target), then add a matching entry to `data/gallery.yaml` **including a UUID `id`** (the build will hard-fail without one — `scripts/add-gallery-ids.py` populates missing ids in bulk).
- Renaming an existing gallery image: rename the file in the photo store (`gallery-photos` target) and update only the matching `src:` in `data/gallery.yaml`. Do not touch `id` — deep links, the likes API key, and any `featured_image:` referencing it all use the id.
- New license values must be added to `data/licenseMap.yaml` or the build will `errorf`.
- Gallery scripting/migration helpers are written in Python (per project memory).
