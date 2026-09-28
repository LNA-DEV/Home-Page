# Concept: a page per game

**Status:** implemented (2026-09-28), with the deviations listed under *As built* at the end. The API answers in §1 were probed on 2026-09-28 against the owner's own Steam library, against Wikidata and against the Steam store. The Hugo mechanics in §8 were checked on a scratch site with Hugo 0.166.0.
**Read against:** the working tree of 2026-09-28 (`96f84a7`). `data/gaming.yaml` has 171 entries; after merging and `data/gamingIgnore.yaml`, 151 games are shown.

Every tile on `/gaming/` becomes a link to `/<lang>/gaming/<slug>/`. That page shows the playtime, every achievement with its status and the share of players who unlocked it, a short description, the genres and facts, and (later) the owner's own screenshots.

This builds a lot on data the site already has. `sync-steam.py` asks Steam for every achievement of every game and keeps two integers. It downloads nothing else about the game.

The rule that runs through the whole concept is the one the gallery manifest follows: **scripts fetch, Hugo resolves.** Every candidate text is stored with its source. Which one a page shows is a template decision, so it can be changed without fetching again.

## Settled decisions

| | |
|---|---|
| Which games | **All** shown games, 151 today. Anything in `data/gamingIgnore.yaml` gets no page |
| URL | `/<lang>/gaming/<slug>/`. The slug is language-neutral, and the three pages are linked through a top-level `translationKey: game-<slug>` |
| Identity | A **`slug:` on every copy** in `data/gaming.yaml`. It is written once, the first time a sync sees the game, and never recomputed. A missing one stops the build (§2) |
| Merging | Copies merge on **slug**, no longer on title |
| Renaming | `slugAliases:` in `data/gamePages.yaml` → per-language redirects |
| Achievements | `data/gameAchievements/<platform>-<id>.json`, one file per copy, written by the syncs. Not in `gaming.yaml` (§3) |
| Achievement icons | Downloaded and **committed** under `static/images/games/achievements/`, one per achievement. A locked achievement is greyed by CSS. No third-party request on any page |
| Global percentage | Steam's, as Steam delivers it (one decimal). GOG's only if its response carries one (§4.1) |
| Hidden achievements | **Shown**, no spoiler masking for now. Steam delivers no description for them at all, locked or unlocked (§1) |
| Description | A priority chain: **own text → Wikipedia → Steam store**, language before source, English last (§5.1) |
| Genres and facts | From Wikidata: genre, game mode, developer, publisher, release date |
| Per-game editorial | `data/gamePages.yaml`, keyed by slug: own description, rating, notes, Wikidata pin, aliases. `rating` and `notes` move there from `gaming.yaml` (§3) |
| Indexing | `noindex, follow`, and **out of the sitemap**. Still in the site search. One switch to change later (§8) |
| Feeds | None. The section stub sets `outputs: [HTML]` |
| Screenshots | A machine-local mount like the gallery's, **one folder per game slug**. The section appears once a folder has files (§7) |

Four points above were set by me rather than discussed. Each is one line to change:
- Wikipedia before Steam in the chain.
- Language before source.
- `rating`/`notes` moving to `gamePages.yaml`.
- Genres from Wikidata only.

---

## 1. What the data says

### The library

| Platform | Entries | Playtime | Achievements |
|---|---:|---|---|
| Steam | 59 | synced | 55 games, 3,373 achievements |
| GOG | 5 | synced | 3 games, 131 achievements |
| Epic | 42 | synced | none: Epic closed the progress API in Jan 2025 |
| Switch / 3DS / DS | 64 | by hand | none: Nintendo has no achievements |
| no platform | 1 | — | — |

- `rating`, `genres`, `tags` and `notes` are set on **zero** entries.
- 15 games exist on more than one platform.

### Steam achievements

These come from the owner's API key, run against all 48 played Steam games with at least one unlock.

- **`GetSchemaForGame`** returns `name`, `displayName`, `description`, `icon`, `icongray`, `hidden` and `defaultvalue`. With `l=german` / `l=swedish` the names and descriptions come back translated where the game has translations:

  | Game | Translated (German) | Translated (Swedish) |
  |---|---|---|
  | Portal 2 | 51/51 | 50/51 |
  | Stardew Valley | 48/49 | 0 |
  | Ori and the Will of the Wisps | 37/37 | 37/37 |
  | Life is Strange | 51/60 | 0 |
  | The Binding of Isaac: Rebirth | 0/641 | 0/641 |

  Where no translation exists, Steam silently returns the English text.
- **`GetPlayerAchievements`** returns `apiname`, `achieved` and `unlocktime` (Unix seconds), plus the localised `name`/`description` when asked with `l=`.
- **Hidden achievements carry no description anywhere.** Across the 48 games there are 660 hidden achievements, 135 of them unlocked. The number with a description, in either endpoint, locked or unlocked: **0**. The name and icon are delivered. The text is only on Steam's community HTML pages, which this concept does not scrape.
- **`GetGlobalAchievementPercentagesForApp`** is public and needs no key. It returns `percent` as a string that is already rounded to one decimal (`"74.1"`).
- **Icons:** 42 icons from 7 games average 6.3 KB, ranging from 1.0 to 35.9 KB. 3,373 icons come to **~21 MB**, about what the dex reference images already commit. *The Binding of Isaac* alone has 641.

### Descriptions and facts

- **Wikidata, Steam games:** all 59 Steam app ids resolve through `P1733` (Steam application ID) to exactly one item each.
  - Wikipedia articles: 50 English, 40 German, 18 Swedish.
  - 56 of the 59 have at least one genre (`P136`).
- **Wikidata, the 93 other titles:** there is no id to match on.
  - `P2725` (GOG) and `P6278` (Epic) hold store *slugs*. The syncs store GOG's numeric product id and Epic's internal `appName`.
  - A title search restricted to `P31 = video game` found 85 items, 71 of them with the exact label. Some are plainly wrong: *#RaceDieRun* → *Stay Safe*, *Catz* → *Catz: Your Computer Petz*. Eight found nothing (*Dolphins*, *Animal Life: Dinosaurs*, …).
  - Of the 85: Wikipedia articles in 72 English, 50 German, 37 Swedish. **45 carry a Steam app id**, so they can get Steam store text even though they are not owned on Steam.
- **Steam store `appdetails`** (no key; 59 apps × 3 languages):
  - 58 answer. *TRANSFORMERS: Rise of the Dark Spark* is delisted.
  - `short_description` has a median of 233 characters. It exists in its own German on 48 games and in its own Swedish on 24. Otherwise Steam silently returns English: *Stardew Valley* in Swedish is the English text.
  - Steam's genres are coarse and partly not genres: Action 43, Indie 32, Adventure 31, Casual 16, *Free To Play* 11, *Early Access* 6.
- **What the chain in §5.1 yields** for the 59 Steam games:

  | Page | Own-language Wikipedia | Own-language Steam | English fallback | nothing |
  |---|---:|---:|---:|---:|
  | en | 50 | 9 | — | 0 |
  | de | 40 | 15 | 4 | 0 |
  | sv | 18 | 17 | 24 | 0 |

  For the other 93 titles the numbers depend on how many Wikidata items get pinned. About 11 will end up with no description at all.

## 2. Identity: the slug

```yaml
# data/gaming.yaml, one copy
- title: "Life is Strange™"
  platform: steam
  appid: 319630
  slug: life-is-strange
  playtimeMinutes: 612
```

- **On the copy, because it is the grouping key.** All copies with the same slug are one game and one page. The title stops mattering: *Rocket League®* and *Rocket League* are two cards today and become one.
- **Frozen at first sight.** When a sync meets an `appid` / `appName` it has no entry for, it writes `slug:` once. From then on `slug` is a preserved field, like `extraMinutes` today. When Steam renames a game (adding a `™`, dropping an edition suffix), the title changes and the URL does not. A hand-added entry gets its slug typed by hand.
- **The rule** lives in a new shared `scripts/gaming_common.py` used by all three syncs:
  - strip `™ ® ©`;
  - `ß` → `ss`;
  - fold to ASCII with NFKD, which is the English folding the gallery's `.fileSlug` uses, since the slug is language-neutral;
  - every run of non-alphanumerics → `-`.

  If the slug already exists, the new copy **joins** that game, and the sync prints this in `--dry-run`. The build never recomputes a slug. It only checks the format `^[a-z0-9]+(-[a-z0-9]+)*$`.
- **One-time migration.** `scripts/gaming-add-slugs.py` inserts `slug:` into all 171 entries as raw text, byte-for-byte elsewhere. Run against today's file it gives 155 slugs for 156 distinct titles. The only new merge is *Rocket League*.
- **The title of a merged page** is `title:` from `gamePages.yaml` if set. Otherwise it is the first copy in a fixed order: hand-added, then steam, then gog, then epic. File order would not do, because each sync moves its block to the bottom.
- **Hard build errors, each naming the entry:**
  - a copy without `slug`;
  - a malformed slug;
  - two copies on the **same platform** with the same slug. A game is not owned twice on one platform, so this is the accidental merge of two different games (*DOOM* 1993 and 2016);
  - a `gamePages.yaml` record whose slug no copy has;
  - a `slugAliases` entry that is a live slug.
- **Renaming** means editing `slug:` on the copies and the key in `gamePages.yaml`, and adding the old slug to `slugAliases`. The golden-URL test refuses the move otherwise. A bare alias from a content adapter resolves relative to the page's section, so `stardew` lands at `/<lang>/gaming/stardew/` (checked on the scratch site).

## 3. Data layout: four files, one owner each

| File | Written by | Holds |
|---|---|---|
| `data/gaming.yaml` | syncs + hand | one entry per **copy**: platform, ids, playtime, `extraMinutes`, last played, the two achievement counts, cover, store link, `slug` |
| `data/gamePages.yaml` | **human only** | one record per **game**: `title`, `description`, `rating`, `notes`, `wikidata`, `steam_appid`, `slugAliases`, all optional |
| `data/gameFacts/<slug>.json` | `game-enrich.py` | every fetched candidate: Wikidata item, Wikipedia extracts, Steam store text, genres, facts |
| `data/gameAchievements/<platform>-<id>.json` | `sync-steam.py`, `sync-gog.py` | the achievement list of one copy |

**Why not in `gaming.yaml`:**
- The file is 1,383 lines. With the achievements it would pass 25,000.
- Three scripts edit it as raw text and re-emit human fields as single lines only. A three-language description does not fit a single line.

**Why JSON for the machine files:** stdlib `json` writes them deterministically (`sort_keys`, fixed indent, trailing newline) with no hand-rolled YAML writer. Hugo reads JSON and YAML alike. `data/gaming.yaml` and a `data/gameAchievements/` directory coexist without a key clash (checked).

**`rating` and `notes` move.** They are set on no entry, so nothing needs migrating. On a copy they are ambiguous: `gaming-merged.html` takes "the first non-empty", which depends on file order. `genres` and `tags` are dropped from the header docs; Wikidata replaces them. The syncs' `HUMAN_FIELDS` becomes `("extraMinutes", "slug")`. A `rating`/`notes`/`genres`/`tags` line found on a copy is a build error that names `gamePages.yaml`.

```yaml
# data/gamePages.yaml
- slug: stardew-valley
  description:          # own text; beats every fetched source in its language
    de: "…"
  rating: 5
  notes: "…"            # a string (= en) or {en, de, sv}
  wikidata: Q21011185   # pin, or `none`; Steam games resolve without one
  steam_appid: 413150   # only when Wikidata has no P1733, for the store text
  slugAliases: []
```

```json
// data/gameAchievements/steam-413150.json
{
 "achievements": [
  {
   "description": {"de": "…", "en": "…"},
   "hidden": false,
   "icon": "images/games/achievements/steam/413150/5a1b….jpg",
   "key": "Achievement_Cowpoke",
   "name": {"de": "…", "en": "Cowpoke"},
   "percent": 71.4,
   "unlocked": "2019-02-11T21:14:03+01:00"
  }
 ],
 "id": "413150",
 "platform": "steam"
}
```

Details of the achievements file:
- Achievements are listed in the game's own schema order. The display order is the template's job.
- `name` and `description` hold a language only when it differs from English.
- `unlocked` is absent while an achievement is locked. It is written in **Europe/Berlin** with the offset, which is fixed and so deterministic. Hugo's `time.Format ":date_medium"` keeps that offset: `00:14 +01:00` prints as 11.02.2019, not the 10th (checked). Between syncs only `percent` and new unlocks change.

```json
// data/gameFacts/stardew-valley.json
{
 "developers": ["ConcernedApe"],
 "genres": [{"de": "…", "en": "farm life sim", "sv": "…"}],
 "match": "steam-appid",
 "modes": [{"de": "Einzelspieler", "en": "single-player video game", "sv": "…"}],
 "publishers": ["ConcernedApe"],
 "released": "2016-02-26",
 "steam": {"de": "Dein Großvater hat dir …", "en": "You've inherited …"},
 "steam_appid": 413150,
 "wikidata": "Q21011185",
 "wikipedia": {
  "de": {"text": "…", "url": "https://de.wikipedia.org/wiki/Stardew_Valley"},
  "en": {"text": "…", "url": "https://en.wikipedia.org/wiki/Stardew_Valley"}
 }
}
```

## 4. Fetching

### 4.1 Achievements: inside the existing syncs

They already iterate the games, hold the credentials, and make one of the calls needed.

- **`sync-steam.py`**, for each game with achievements:
  - `GetSchemaForGame` three times (english / german / swedish);
  - `GetPlayerAchievements` once;
  - `GetGlobalAchievementPercentagesForApp` once.

  That is 5 requests per game, 275 in total. The counts in `gaming.yaml` and the JSON come from the same response, so the card and the page cannot disagree.

  Icons: the colour `icon` URL is saved as `static/images/games/achievements/steam/<appid>/<basename>`. The basename is a content hash, so an unchanged icon is never downloaded twice. Files the JSON no longer references are removed from that game's folder only. A game pruned from the library loses its JSON and its icon folder. The existing `--no-achievements` skips all of it.
- **`sync-gog.py`** already fetches the `items`. It writes the JSON from the same response.
  - Icon: `image_url_unlocked`, falling back to `image_url_locked`. The first is empty until anyone at all has earned the achievement.
  - Percentage: the documented response has no field for it. The script takes `rarity` if the live response carries one. Otherwise GOG rows show no percentage. This is checked on the first run, and only three games are affected.
  - Whether the endpoint honours a locale is also checked then; if not, English only.
- **Epic and Nintendo**: nothing to fetch.

### 4.2 Facts and descriptions: new `scripts/game-enrich.py`

This runs on demand, not with every sync, like `dex-enrich.py`. It uses the stdlib only and never runs git.

1. **Wikidata item**, in this order:
   - the pin in `gamePages.yaml`;
   - the Steam app id of a Steam copy through `P1733` (one batched SPARQL query);
   - otherwise nothing.

   `--propose` prints title-search candidates as paste-ready `wikidata:` lines for the owner to check. **A title match is never written automatically.** The probe found wrong hits with convincing labels, so the script keeps the `dex-tag-photos.py` rule and refuses to guess.
2. **Wikipedia**, per language, from the item's sitelinks: the REST summary, trimmed to two or three sentences. `wikipedia_summary()` / `split_sentences()` move from `dex-enrich.py` into a shared `scripts/wiki_common.py`, which both scripts import. There is one trimming rule for the dex and the games, not two copies of it.
3. **Steam store**, for the Steam copy's id, else `P1733`, else the `steam_appid` pin: `appdetails` × 3 languages → `short_description`, with HTML stripped and entities decoded. **A language whose text equals the English one is dropped**, because that is Steam's silent fallback and not a translation. The store allows ~200 requests per 5 minutes, so the script sleeps 1.5 s between requests. A full run of ~104 apps × 3 takes about 8 minutes; `--missing` does only games without a facts file.
4. **Facts** from the item, with en/de/sv labels: genre (`P136`), game mode (`P404`), developer (`P178`), publisher (`P123`), earliest publication date (`P577`).

The facts file is **overwritten completely** on every run for that game. It is machine-owned. Anything the owner writes lives in `gamePages.yaml`, which the script only reads.

Flags: `--only <slug>`, `--missing`, `--dry-run`, `--propose`.

## 5. Resolution in Hugo

### 5.1 The description chain

`layouts/partials/game-description.html` returns `{text, source, url}`. For a page in language L it takes the first non-empty of:

```
own(L) → wikipedia(L) → steam(L) → own(en) → wikipedia(en) → steam(en)
```

- **Language before source.** A German page with Steam's German text reads better than one with an English Wikipedia paragraph.
- **Wikipedia before Steam.**
  - Wikipedia is CC BY-SA and neutral, and its credit is already solved in the dex.
  - Steam's text is advertising copy, under the publisher's copyright, with no licence at all. On this site it is a short quote with a source link.
  - Both lists live in one `slice` in the partial, and every candidate is stored. Putting Steam first is a one-line change with no refetch.
- **Credit** travels with the text, as in the dex, including when the fallback is English:
  - Wikipedia gets `game_source_wikipedia`: the article link plus CC BY-SA, the same wording as `dex_source_wikipedia`.
  - Steam gets `game_source_steam`: "Description from the Steam store", linked.
  - Own text gets no credit line.
- **Nothing found** means no description section at all. A placeholder sentence about a game is worse than none.

### 5.2 `gaming-merged.html`

- It groups by `slug` instead of `title`. `gamingIgnore.yaml` still filters by title, per copy, before grouping, exactly as now.
- It additionally returns:
  - `slug`;
  - the resolved `title`;
  - `copies`: platform, minutes including `extraMinutes`, last played, store link, and the achievement file key `steam-<appid>` / `gog-<appName>`;
  - `rating`, from `gamePages.yaml`.

  It stays `partialCached` without a variant. Everything in it is language-neutral.
- The card's `href` becomes the game page and no longer the store. The card's `id` becomes the slug. `recentGaming.html` links to the page instead of `/gaming/#<urlize title>`.

## 6. The page

`content/gaming/index.{en,de,sv}.md` becomes **`_index.{en,de,sv}.md`**, because a leaf bundle cannot have child pages. The URL stays the same. The stub gets:
- `params.theme: gaming-home`;
- `outputs: [HTML]`;
- a branch in `layouts/_default/list.html` that renders `.Content` (the `gamingList` shortcode) and nothing else. Without it, PaperMod's list would append all 151 game pages as post entries.

`content/gaming/_content.{en,de,sv}.gotmpl` call `layouts/partials/game-pages.html`, which runs the `.AddPage` loop. There is one file per language because Hugo scopes an adapter to its filename's language. Pages set `params.theme: game`. Dispatch is in **both** `page.html` and `single.html` (the Hugo 0.146+ rule the dex and model pages follow), and goes to `layouts/partials/game-detail.html`.

Top to bottom:

1. **Breadcrumb:** Gaming → title.
2. **Head:**
   - the cover, `Fill 300x450` like the card, or the title placeholder;
   - title, platform badges (`platform-icon.html`) and rating stars;
   - a facts row: genres · game mode · developer · publisher · year, each omitted when empty;
   - one store link per copy.
3. **Playtime:** the total, a per-platform breakdown when there is more than one copy, and last played.
4. **Description** and its credit line (§5.1).
5. **Notes**, the owner's own, when present.
6. **Screenshots**, when present (§7).
7. **Achievements**, one block per copy that has them, headed with the platform only when there are two.
   - **Summary:** unlocked/total, a progress bar and the percentage.
   - **Controls:** filter (all · unlocked · locked) and sort (default · rarity · A–Z). These are client-side and styled like the grid's `.gaming-btn`.
   - **Row:**
     - the icon at 48 px, `grayscale(1)` plus reduced opacity when locked;
     - name and description in L, falling back to English;
     - for a hidden achievement without a description: "Hidden achievement, Steam publishes no description";
     - the unlock date (`:date_medium`) or "locked";
     - the global percentage with a thin bar.
   - **Default order:** unlocked first, newest first; then locked, most common first.
   - **Long lists:** *Isaac*'s 641 rows get `loading="lazy"` on the icons and `content-visibility: auto` on the rows.

Icons go out through `resources.Get … .RelPermalink`. They are published as-is, with no image processing, once, as language-neutral global resources.

A DS game with no Wikidata item gets a page with a head and a playtime section. That is the accepted consequence of "all games".

## 7. Screenshots

- **Mount.** `config/_default/module.yaml` (gitignored, machine-specific) gets a second machine mount beside the gallery's:
  ```yaml
  - source: /absolute/path/to/your/screenshot/store
    target: assets/images/games/screenshots
    disableWatch: true
  ```
  `module.yaml.example` gets the same lines, commented. As with the gallery, the source must be a **real directory, not a symlink**, since Hugo 0.163.1. And `mounts` replaces rather than merges, so this goes into the one list that already restates `assets`.
- **Layout:** `<store>/<slug>/<file>.{jpg,png,webp}`. The order is by file name; both Steam and the Switch name screenshots by capture time.
- **Rendering:**
  - `AutoOrient`, then a `Fit 640x640` thumbnail and a `Fit 1920x1920` large variant, both JPEG. `Fit` never upscales.
  - The lightbox is the vendored PhotoSwipe, through a small new `assets/js/game-screenshots.js`. It does not use `lightbox.js`, which is built around likes, deep links and the download dialog.
  - Alt text: `game_screenshot_alt` ("Screenshot {n} of {total} from {title}").
- **No original is published and no metadata leaves.** The original is never referenced, so Hugo never writes it. The variants are re-encoded and Hugo emits no metadata segment. `gallery-embed-metadata.py` walks only `public/images/gallery/`, so it neither sees nor needs these.
- **Checks:**
  - A folder whose name is no page's slug is a `warnf`, which blocks the deploy like every warning.
  - An empty or missing mount is **no** warning, unlike the gallery's. No screenshots is the normal state today.
- **Captions** are out of scope. If wanted later, add `screenshots: {<file>: {en, de, sv}}` in `gamePages.yaml`.

## 8. Indexing, search, feeds, structured data

- **noindex.**
  - `game-pages.html` sets `params.robotsNoIndex` from one variable, `$indexable := false`.
  - It also sets the top-level `.AddPage` key `sitemap: {disable: true}`. Checked on 0.166.0: the key is accepted, and the page leaves `sitemap.xml` while staying in `site.RegularPages`.
  - Opening the pages later means changing that one variable, for example to "has own text or screenshots". If `tag-pages.md` lands first, its `robots-indexable.html` predicate is the place instead.
- **Site search:** the pages stay in `site.RegularPages` and therefore in `index.json`. Noindex is about search engines, not about the visitor who types "Hollow Knight".
- **Feeds:** the pages carry no date, like the dex pages, none of which appear in today's `index.xml`. The section emits no feed of its own (`outputs: [HTML]`).
- **Structured data:** the default `WebPage` branch in `schema_json.html` applies (undated, so no invented `datePublished`). A new branch adds `about: {@type: VideoGame, name, genre, gamePlatform, sameAs: [Wikidata, Wikipedia]}`, which is the dex's `Taxon` pattern. There is no `author` on the page, since the description is not the owner's text.

## 9. Tests

- **build:**
  - a missing or malformed slug, a same-platform slug clash, an unknown `gamePages.yaml` slug, a live-slug alias, or a moved field on a copy → failure;
  - a screenshot folder with no page → warning (and so a failure).
- **python:**
  - the slug rule;
  - the syncs write `slug` once for a new game, preserve it after that, and join an existing slug;
  - the achievements JSON is byte-identical for identical input, English-duplicate translations are dropped, and `unlocked` carries the Berlin offset;
  - a Steam store text equal to the English one is dropped.
- **static:**
  - every shown game has a page in all three languages, and its card links to it;
  - achievement rows equal `achievementsTotal`, and unlocked rows equal `achievementsUnlocked`;
  - `noindex` on every game page, none in any `sitemap.xml`, and a three-language hreflang cluster;
  - no game page references a resource off the site;
  - no file under `images/games/screenshots/` is published without `_hu_`.
- **e2e:** achievement filter and sort; the screenshot lightbox opens and closes.
- **golden:** +450 URLs (150 × 3), `npm run golden:update` — which needs the collector change under *As built*, since these pages are in no sitemap.

The screenshot path is tested only once a folder exists. The test build uses the machine's `module.yaml`, and a fixture mount would have to restate the whole replace-not-merge mount list in a second config file. Not worth it for a section that is empty by design today.

## 10. Cost

- **Repository:**
  - icons ~21 MB (3,373 × 6.3 KB) plus ~0.5 MB for GOG;
  - achievement JSON ~1.5 MB;
  - facts JSON ~0.5 MB.

  After that, it grows only with new games.
- **Sync:** +275 Steam requests, +1–2 minutes. The diff per sync is the `percent` lines that moved and new unlocks.
- **Enrich:** ~8 minutes for a full run, seconds with `--only`.
- **Build:** 453 more pages with no image processing for icons. Screenshots go through the same resource cache as everything else (never clear it).

## 11. Build order

Each step builds and passes `npm test` on its own.

1. **Slugs.**
   - `gaming_common.py`, then `gaming-add-slugs.py` (one-time), then the three syncs preserving and writing `slug`.
   - `gaming-merged.html` groups by slug and runs the checks.
   - The grid looks the same apart from the Rocket League merge.
2. **`gamePages.yaml`**: `rating`/`notes` move, `HUMAN_FIELDS` shrinks, and its checks.
3. **Pages.**
   - The stub goes from leaf to branch, plus the `gaming-home` branch in `list.html`.
   - Adapters ×3, `game-pages.html`, `game-detail.html` (head, playtime, notes).
   - Dispatch, the card link, the `recentGaming` link, noindex and sitemap, i18n, CSS.
   - Golden update.
4. **Achievements**: JSON and icons in both syncs, then the section and its JS.
5. **Facts**: `wiki_common.py` (moved out of `dex-enrich.py`), `game-enrich.py`, `game-description.html`, the facts row, the `VideoGame` structured data.
6. **Screenshots**: mount example, section, JS, the folder warning.
7. `CLAUDE.md` (*Gaming* section) and `AGENTS.md` (enrich workflow; the syncs' new output); `npm test`.

## 12. Files touched

### New
- `data/gamePages.yaml`, `data/gameFacts/*.json`, `data/gameAchievements/*.json`
- `static/images/games/achievements/{steam,gog}/<id>/*`
- `content/gaming/_content.{en,de,sv}.gotmpl`
- `layouts/partials/game-pages.html`, `game-detail.html`, `game-description.html`
- `assets/css/extended/gamePage.css`, `assets/js/game-screenshots.js`
- `scripts/gaming_common.py`, `scripts/gaming-add-slugs.py`, `scripts/game-enrich.py`, `scripts/wiki_common.py`
- tests under `tests/py/`, `tests/static/`, `tests/e2e/`

### Modified
- `data/gaming.yaml`: `slug` on every entry, and the header docs
- `content/gaming/index.*.md` → `_index.*.md`
- `layouts/partials/gaming-merged.html`, `layouts/shortcodes/gamingList.html`, `recentGaming.html`
- `layouts/_default/list.html`, `page.html`, `single.html`
- `layouts/partials/templates/schema_json.html`
- `scripts/sync-steam.py`, `sync-gog.py`, `sync-epic.py` (slug), `dex-enrich.py` (imports `wiki_common`)
- `config/_default/module.yaml.example`
- `i18n/{en,de,sv}.yaml` (`# Gaming` block)
- `tests/golden/published-urls.txt`
- `CLAUDE.md`, `AGENTS.md`

## 13. Deliberately out of scope

- **Descriptions of hidden Steam achievements.** The API does not deliver them, and scraping community HTML is not worth its fragility.
- **Spoiler masking**: deferred by decision. Revisit once the pages are live.
- **Epic achievements**: no API. **Nintendo**: no achievements.
- Steam's per-OS playtime split and `playtime_2weeks`.
- Screenshot captions; the publisher's store screenshots, which are not the owner's.
- A genre filter on the grid.
- Opening the pages to search engines. That is the one-variable switch in §8, once there is own content worth indexing.

## As built

Where the implementation differs from the text above, and what the first real runs showed.

- **150 games, 450 URLs**, not 151 and 453. The Rocket League merge (§2) is one game fewer.
- **`HUMAN_FIELDS` is unchanged**, not reduced to `("extraMinutes", "slug")` as §3 said. A sync never destroys what somebody typed, so a stray `rating:` on a copy still survives a sync, and the build is what says to move it. `slug` is not a human field at all: it is identity, and every sync emits it as the entry's second line, where the migration also put it.
- **`noindex, follow` needed a new param.** `head.html` only knew `robotsNoIndex` → `noindex, nofollow`. Game pages also set `robotsFollow: true`.
- **The golden URL list would not have seen the pages.** `tests/golden/collect.mjs` collects sitemap `<loc>`s and feed `<link>`s, and a noindex page is in neither — so the frozen slug would have had no test behind it. The collector now also adds every real page under `/<lang>/gaming/<slug>/` (an alias stub, recognisable by its `refresh`, is not a page).
- **`/gaming/` fell out of the site search.** As a leaf page it was a RegularPage; as a section it is not. `layouts/_default/index.json` now adds it by hand, like `/travel`. The 150 game pages are in the index on their own.
- **The site's `sitemap.xml` ignored `sitemap.disable`.** It overrides Hugo's built-in template, which honours the flag; the override did not. It now ranges over `where .Data.Pages "Sitemap.Disable" "!=" true`. No other page sets the flag, so nothing else changed.
- **Editions.** A Steam app id often belongs to an *edition* item with no articles (*Horizon Zero Dawn Complete Edition*). `game-enrich.py` then follows its `P629` "edition of" to the game, recorded as `match: steam-appid+edition-of`.
- **Icons live in `static/`, not `assets/`.** Every file fetched with `resources.Get` goes through one LRU partition of Hugo's in-memory cache that is capped by *count*: about 4,000 entries (dynacache: 100,000 / 10 × weight 0.4). Memory plays no part, and `HUGO_MEMORYLIMIT=64` changed nothing. The site already sends ~1,200 files through it. With the ~3,100 icons on top, evicted resources were re-created on their next use and published a second time, and Hugo warned `Duplicate target paths`, which stops a deploy. The warning named all 150 dex range files and 28–65 icons, varying with render order.
  - Measured by rendering only the first *n* icons of each game: clean at 3,104 icons, broken at 3,145.
  - Clean again with all 3,145 icons but an empty gallery mount.
  - The icons need no processing, so they are plain static files; the template checks `fileExists` before it emits an `<img>`.
  - The ceiling is the site's, not the icons': the gallery alone has room for roughly 2,800 more photos before it reaches it.
  - **This is a workaround with a follow-up task**, `duplicate-target-paths.md`: a classifier that lets the harmless re-publish through while every real path conflict still fails, and then the icons move back to `assets/`.
- **Icons: 3,112 files, 23 MB.** 33 icons of three games (PixARK, Aimlabs, Core Keeper) are gone from every Steam CDN host, grey variant included. Those rows show an empty tile, the sync reports them in one line per game, and the next sync tries again.
- **`--no-achievements` and transient failures keep the old counts and file.** Before this, `--no-achievements` silently dropped the counts from `gaming.yaml`. With a file on the page, card and page would have disagreed.
- **Link previews keep the site logo.** A cover is publisher art under no licence at all. The same reasoning keeps the dex's Commons stand-ins out of `og:image`.
- **The Wikipedia credit reuses the dex's `dex_source_wikipedia`** rather than a new `game_source_wikipedia` key: the same words for the same licence.
- **GOG was not run.** Its sync refreshes the OAuth token Heroic stored. `rarity` and the locale question (§4.1) are therefore still open until the owner's next GOG sync.
