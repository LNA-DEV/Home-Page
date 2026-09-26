# AGENTS.md

Generic entrypoint for coding agents working in this repo. The authoritative,
detailed project guide is **`CLAUDE.md`** — read it first for build/deploy,
the gallery system, and overall architecture. This file documents workflows
that are worth spelling out step by step.

## Adding gallery photos, and what happens to them on deploy

Two scripts, at opposite ends of a photo's life. Both are standard-library only
(no `pip install`) and both edit `data/gallery.yaml` as text, so lines that are
not part of the change stay byte-identical. Neither ever writes to the photo
store — that folder is darktable's export target and a Nextcloud share.

### `scripts/sync-gallery.py` — the photo enters the data file

Run it after exporting new photos into the photo store (the gallery mount
`source` in `config/_default/module.yaml`; the script reads that file, so the two
never drift):

```bash
python3 scripts/sync-gallery.py --dry-run   # look first
python3 scripts/sync-gallery.py
```

- A `src:` in the YAML with no file on disk is an **error**, not a fix: it usually
  means a rename to make by hand. The script reports every one and writes nothing.
- A file on disk with no entry gets a stub appended, with a fresh UUID `id`,
  **empty `title` and `alt` slots in all three languages**, `tags: []`, and only
  `license` / `artist` pre-filled from darktable's preset in the JPEG
  (`scripts/gallery_xmp.py`, one exiftool process for all new files; without
  exiftool those two are simply left out).
- **Title, alt text, description and tags are typed in `data/gallery.yaml`, never
  in darktable** (`docs/concepts/gallery-metadata-yaml-only.md`). Whatever the file
  carries in those fields is ignored, and the export filename can be anything —
  the site publishes the photo under its English title's slug. Set darktable's
  export conflict handling to "create unique filename", never "overwrite": camera
  counters like `DSC_0001` repeat.
- **The build stops on the new photo until `title.en` is written** — that is the
  reminder. An empty alt is a backlog item, not an error.
- `license` is written as a **key** (`cc-by-sa-4.0`), mapped from darktable's
  display string through `data/licenseMap.yaml`.

Left for a human: the title (all three languages), the alt text, the tags,
`category` (the stub says `others`), `section`, `project`, `portfolio`, `species`.

### `scripts/gallery-embed-metadata.py` — the photo leaves for the web

The post-build pass that writes the metadata into the files the site serves and
takes the camera's private data back out of the published originals. `deploy.sh`
runs it after each of its two builds; run it by hand only to inspect the result:

```bash
hugo
python3 scripts/gallery-embed-metadata.py --dry-run    # resolve and report, write nothing
python3 scripts/gallery-embed-metadata.py              # ~3m40s for 4,161 files
python3 scripts/gallery-embed-metadata.py --check      # every served file carries its UUID
exiftool "public/images/gallery/<some photo>.JPG"      # see what a visitor downloads
```

- It reads `public/<lang>/gallery-metadata.json`, which Hugo renders — so **run
  `hugo` first**, and re-run it after any change to the gallery data or templates.
- Every file is **cleared first** (all metadata but the ICC profile), then gets the
  technical EXIF from the source and the editorial set from the manifest. Nothing
  darktable, the camera or a phone left in the source survives unless it is
  written again.
- It is idempotent: a second run leaves every file byte-identical.
- It aborts before writing anything if a published file maps to no photo, or if a
  source original is missing from the photo store.
- `--check` is what stands between a wrong file and the live site. It compares
  every editorial field of every served file with the manifest, refuses any
  metadata group outside its allowlist, and checks each published original's
  image data against its store file (~25 s per build). If it fails, do not deploy — read what it names
  (a stray group from a new camera belongs either in `ALLOWED_GROUPS` or cleared),
  fix, rerun the embedding step.
- After each rsync `deploy.sh` reloads the site's nginx container, so a changed
  image redirect map (`/_nginx/gallery-image-redirects.map`) takes effect.

Do **not** run `./deploy.sh` after either script. That is a separate, explicitly
authorised step.

### `scripts/gallery-import-xmp.py` — done, do not re-run

The one-time migration that made "the YAML is the truth" literally true. It is
kept for the record; **it has run and there is nothing left for it to do.** Before
it, 282 photos had their licence, 281 their alt text and 21 their title only inside
the exported JPEG, and the build read them back through fallbacks — so a darktable
re-export could change what the site said about a photo with no diff in git.

What it did, in one pass over `data/gallery.yaml` (`docs/concepts/gallery-metadata-import.md`):

| | |
|---|---:|
| licence display strings rewritten to keys | 366 |
| `license` filled from the file | 282 |
| `alt` filled from the file | 281 |
| `title` filled from the file | 22 |
| `description` added from the file | 7 |

`artist` was deliberately **not** imported: all 287 file values are `Lukas Nagel`,
which is `site.Params.author.name` and already the fallback (`--artist` imports
them if uniformity is ever preferred). Tags were not imported by this script; the
second one-time import below did that.

It removed the fallbacks with it, so from here on:

- A photo with no `license:` in `data/gallery.yaml` is a **hard build error** naming
  the file. There is no `Exif.Copyright` to fall back to any more.
- `license:` must be a **key** of `data/licenseMap.yaml`. The old display strings
  were registered there as `aliases`; those lists are now empty.
- `alt` comes from the YAML alone. 60 photos still have none anywhere — that is an
  editorial backlog, not a defect, and the script lists them.
- `layouts/partials/image-alt.html` still exists, but only `sitemap.xml` uses it,
  for page-bundle images that are not gallery photos.

### `scripts/gallery-import-tags.py` and `scripts/gallery-cache-link.py` — done, do not re-run

The two one-time steps of `docs/concepts/gallery-metadata-yaml-only.md`, run on
2026-09-26 and kept for the record. A second run of either prints that there is
nothing to do.

- **`gallery-import-tags.py`** moved the tags the build used to read out of the
  files into `data/gallery.yaml`: 4,422 tags on 289 entries, in darktable's
  camelCase spelling (`bavarianAlps`). The set and order came from Hugo's own
  manifest, so the site showed exactly the same tags before and after — all three
  `gallery-metadata.json` stayed byte-identical, before the template stopped
  reading the files and after. Three German file tags (`Eidechse`,
  `Eidechsenkampf`, `Schnecke`) that duplicated English YAML tags were then
  deleted by hand. Tags are now typed in the YAML only.
- **`gallery-cache-link.py`** kept the image cache warm when the build started
  publishing under slug names: it hardlinked the 5,819 cached variants
  `<store stem>_hu_<hash>.<ext>` to `<file slug>_hu_<hash>.<ext>` (the hash does not
  depend on the name), so the switch reprocessed nothing. It only ever adds links.

### A reworded English title

The English title decides the photo's page URL **and** its image file names. After
rewording one: add the old English page slug to the entry's `slugAliases:` (keeps
the old page URL and, through the nginx redirect map, the old image URLs alive),
then `npm run golden:update`.

Running it again prints `Nothing to import` and changes nothing, which is the
intended way to confirm the state. It refuses to run at all if `data/gallery.yaml`
and the photo store are out of step, or if any licence value is unknown.

## Adding books to the reading list

The reading list lives in `data/reading.yaml` (one entry per book) with cover
images committed under `assets/images/books/covers/`. See the "Reading list"
section of `CLAUDE.md` for the full data model.

Use **`scripts/add-book.py`** — it does the mechanical fetching. It is
standard-library only (no `pip install`), and mirrors `sync-gallery.py`'s
convention of editing YAML as raw text so existing entries stay byte-for-byte
unchanged.

### What the script does

- Looks the book up on **Open Library** (`openlibrary.org`) — free, no API key,
  reliable. (Google Books was evaluated and rejected: it rate-limits with
  HTTP 429 without an API key.)
- Auto-fills `title`, `author`, `year` (first publish), `pages` (median edition).
- Downloads the cover to `assets/images/books/covers/<Title>.jpg` (skips tiny
  placeholder blobs Open Library returns when it has no real cover).
- Proposes a `link:` in the preferred order **Wikipedia → Open Library →
  Goodreads**. Goodreads has had no public API since 2020, so its fallback is
  only a *search* URL to paste-verify. **Always eyeball the proposed link.**
- Suggests `genres:` by mapping Open Library "subjects" onto the site's own
  genre vocabulary (`GENRE_VOCAB` in the script). This is heuristic and
  produces occasional false positives (e.g. a stray `fantasy`) — **review the
  genres before committing.**

### What it deliberately leaves for a human

These are personal or ambiguous and are emitted as `# TODO` / empty:

- `originalLanguage` — Open Library lists *every* edition's language, not the
  original; the script prints the language list as a hint but does not guess.
- `rating`, `dateRead`, `languagesRead`, `languagesListened` — only the user
  knows these.

### Workflow

1. **Preview** (prints a paste-ready block, downloads the cover):
   ```
   python3 scripts/add-book.py "Book Title" --author "Author Name"
   ```
   Use `--isbn <isbn>` for the most precise match, or `--year` / `--series` to
   override/supply fields Open Library gets wrong or lacks.

2. **Verify** the printed notes: is the link the right one? Do the suggested
   genres match the book (and the existing vocabulary)? Check the downloaded
   cover under `assets/images/books/covers/` actually looks like the book.

3. **Append** to `data/reading.yaml`:
   ```
   python3 scripts/add-book.py "Book Title" --author "Author Name" --append
   ```
   (Or paste the previewed block in by hand if you want it in a specific spot —
   the list is unordered, so appending at the end is fine.)

4. **Fill the TODO fields** in the new entry: set `originalLanguage`, and add
   the user-supplied `rating` / `dateRead` / `languagesRead` /
   `languagesListened`. Uncomment the lines you use; delete the ones you don't.

5. **Sanity-check the build**: `hugo` should succeed and the new book should
   appear on `/en/reading-list/` (and the recent-reading strip on the profile
   page if you set `dateRead`).

Do **not** run `./deploy.sh` — deployment is a separate step the user
authorizes explicitly.

### Doing it without the script

If the script can't be run, the same result is achievable by hand: find the
book on Open Library, download the `-L` cover
(`https://covers.openlibrary.org/b/id/<cover_i>-L.jpg`) into the covers folder,
and add a matching entry to `data/reading.yaml` following the existing entries'
shape. Keep the field order consistent with neighbouring entries.

## Syncing games from Steam

The gaming list lives in `data/gaming.yaml` (one entry per game) with cover
images committed under `assets/images/games/covers/`. See the "Gaming" section
of `CLAUDE.md` for the full data model. The file is written by **multiple
sources**: hand-added entries (any `platform:` other than `steam`) and
Steam-synced entries (`platform: steam`).

Use **`scripts/sync-steam.py`** for the Steam half. It is standard-library only
(no `pip install`), and edits `gaming.yaml` as raw text so hand-added entries
stay byte-for-byte unchanged (same convention as `add-book.py` /
`sync-gallery.py`).

### What the script does

- Fetches the owned-games library from the Steam Web API
  (`IPlayerService/GetOwnedGames`) — needs an API key + your 64-bit SteamID.
- Auto-fills `title`, `appid`, `playtimeMinutes`, `lastPlayed`, and (unless
  `--no-achievements`) `achievementsUnlocked` / `achievementsTotal` via
  `ISteamUserStats/GetPlayerAchievements` (silently skipped for games with no
  stats or a private profile).
- Downloads each game's portrait cover (`library_600x900`, falling back to
  `header.jpg`) into `assets/images/games/covers/<appid>.jpg`, skipping files
  that already exist (`--no-covers` to skip entirely).
- **Reconciles only the `platform: steam` entries** against the live library:
  newly-owned games are **added**, games no longer owned are **pruned**. It
  writes them as the last block in the file, under a marker it emits. By
  default 0-playtime games are excluded (`--include-unplayed` to keep them).

### What it deliberately leaves for a human

- `rating`, `genres`, `tags`, `notes` — subjective. Add them by hand to a Steam
  entry and they are **preserved across future syncs** (re-emitted verbatim,
  matched by `appid`). Keep each to a single line — that's how they're re-added.
- Any non-Steam game — the sync never touches entries whose `platform` isn't
  `steam`.

### Workflow

1. **Credentials** — get a key at <https://steamcommunity.com/dev/apikey>, then
   supply `STEAM_API_KEY` and `STEAM_ID` (your 64-bit SteamID) in any of three
   ways (precedence: flag > environment > `.env`):
   - a **`.env`** file in the repo root (gitignored) — the easiest; the script
     auto-loads it (or point at another file with `--env-file`):
     ```
     STEAM_API_KEY=...
     STEAM_ID=7656119...
     ```
   - the **environment**: `export STEAM_API_KEY=...` / `export STEAM_ID=...`
   - **flags**: `--api-key ...` / `--steam-id ...`

   Never commit the key or SteamID.

2. **Preview** the reconcile (writes nothing):
   ```
   python3 scripts/sync-steam.py --dry-run
   ```
   It prints `+N added, ~M updated, -K pruned` and the pruned appids. Sanity-check
   the counts before writing.

3. **Sync**:
   ```
   python3 scripts/sync-steam.py
   ```
   (Add `--no-achievements` / `--no-covers` for a faster run.)

4. **Eyeball the diff**: `git diff data/gaming.yaml` — confirm hand-added and
   non-Steam entries are untouched and the covers under
   `assets/images/games/covers/` look right.

5. **Sanity-check the build**: `hugo` should succeed. (Nothing renders the data
   yet, but the file must still parse.)

Do **not** run `./deploy.sh` — deployment is a separate step the user authorizes
explicitly.

### Adding a non-Steam game by hand

Copy the commented template at the top of `data/gaming.yaml`, uncomment it, and
set `platform:` to something other than `steam` (e.g. `switch`, `gog`,
`manual`). The Steam sync will leave it alone.

## Syncing games from Epic

Epic Games has **no** Steam-style public API (no API key, no owned-games
endpoint). `scripts/sync-epic.py` instead reads what the **Heroic** launcher has
already cached on disk and merges it with Epic's private cloud playtime. It is
standard-library only and edits `gaming.yaml` as raw text, exactly like
`sync-steam.py` — it owns only the `platform: epic` entries.

### Why two sources

Playtime is split by which client launched the game, and the two never overlap:

- **Historical** play through the **official Epic launcher** lives only on Epic's
  **cloud**.
- Play through **Heroic** lives only in Heroic's **local** files (Heroic never
  uploads it to Epic).

A session is launched by exactly one client, so the totals are disjoint and the
true per-game total is `heroic + cloud`, matched on the Epic `appName` (the
codename like `Salt` / `CrabEA`; the cloud endpoint calls it `artifactId`).

### What the script does

- **Heroic-local (always, no login):** reads the owned library
  (`store_cache/legendary_library.json` → title, `appName`, portrait cover URL,
  store link) and Heroic-launched playtime + `lastPlayed` (`store/timestamp.json`,
  minutes). The Heroic config dir is auto-detected (Flatpak
  `~/.var/app/com.heroicgameslauncher.hgl/config/heroic`, then native
  `~/.config/heroic`; override with `--heroic-config`).
- **Epic cloud (unless `--no-cloud`):** reuses the Epic OAuth refresh token Heroic
  already stored (`legendaryConfig/legendary/user.json`) — **no separate login**.
  It refreshes that token and GETs `library-service`'s per-account playtime
  endpoint for the historical official-launcher hours (seconds → minutes).
- **Merges** the two (`playtimeMinutes = heroic + cloud`), downloads each game's
  portrait cover into `assets/images/games/covers/<Title>.<ext>` (skipping ones
  that exist; `--no-covers` to skip), and **rebuilds only the `platform: epic`
  entries** (played games added, others pruned) as the last block in the file,
  under a marker it emits. 0-playtime games are excluded by default
  (`--include-unplayed` to keep them).

### What it deliberately leaves out / for a human

- **Achievements** — Epic closed the achievement-progress API in Jan 2025; there
  is no reliable public source, so the Epic sync never sets them.
- `rating`, `genres`, `tags`, `notes` — subjective. Add them by hand to an Epic
  entry and they are **preserved across syncs** (re-emitted verbatim, matched by
  `appName`). Keep each to a single line.
- Any non-Epic game — the sync never touches entries whose `platform` isn't
  `epic` (including the Steam block).

### Workflow

1. **Freshen the token (for the cloud half):** the script reuses Heroic's stored
   Epic session, which goes stale when Heroic hasn't run in a while. **Open Heroic
   once** (it re-auths Epic) before syncing. If the token is still stale the script
   prints a warning and proceeds Heroic-local only. (A manual token can be supplied
   via `EPIC_REFRESH_TOKEN` / `EPIC_ACCOUNT_ID` in the env or a gitignored `.env`;
   never commit it.)

2. **Preview** (writes nothing):
   ```
   python3 scripts/sync-epic.py --dry-run             # Heroic + cloud
   python3 scripts/sync-epic.py --no-cloud --dry-run  # Heroic-local only
   ```
   It prints `+N added, ~M updated, -K pruned`. Sanity-check the counts.

3. **Sync**:
   ```
   python3 scripts/sync-epic.py
   ```

4. **Eyeball the diff**: `git diff data/gaming.yaml` — confirm hand-added entries
   and the Steam block are untouched and the new covers under
   `assets/images/games/covers/` look right.

5. **Sanity-check the build**: `hugo` should succeed.

Do **not** run `./deploy.sh` — deployment is a separate step the user authorizes
explicitly.

### Note on the private Epic API

The cloud half calls Epic's undocumented launcher endpoints with your own token —
the same thing Heroic / Legendary / Playnite do. It's your own data, one read per
run. Not a sanctioned public API; keep it to personal use. The OAuth client
id/secret baked into the script is the well-known public "launcher" constant, not
a secret.

## Syncing games from GOG

GOG has **no** Steam-style public API either. `scripts/sync-gog.py` is modelled on
`sync-epic.py`: it reads what the **Heroic** launcher cached on disk and optionally
reaches GOG's cloud with the token Heroic stored. Standard-library only, raw-text
edits, owns only the `platform: gog` entries.

### What the script does

- **Heroic-local (always, no login):** owned library
  (`store_cache/gog_library.json` → title, `appName` = numeric GOG product id,
  portrait cover URL; skips DLC/redist) and Heroic-launched playtime + `lastPlayed`
  (`store/timestamp.json`, minutes). Heroic config dir auto-detected (Flatpak first,
  then `~/.config/heroic`; `--heroic-config` to override).
- **GOG cloud (unless `--no-cloud`):** reuses the GOG OAuth refresh token Heroic
  stored (`gog_store/auth.json`, under the Galaxy client id) — **no separate login**.
  Refreshes it (GOG's token endpoint is a GET), then per owned game GETs the
  authoritative playtime (`gameplay.gog.com/games/{id}/users/{uid}/sessions` →
  `time_sum`) and, for played games (unless `--no-achievements`), achievements
  (`gameplay.gog.com/clients/{id}/users/{uid}/achievements`).
- **Merges** with the **prefer-cloud** rule (`playtimeMinutes = max(cloud, local)`),
  downloads covers into `assets/images/games/covers/<Title>.<ext>` (skips existing;
  `--no-covers`), and **rebuilds only the `platform: gog` entries** (played added,
  others pruned) as the last block, under a marker it emits. 0-playtime games
  excluded by default (`--include-unplayed`).

### How GOG differs from the Epic sync

- **Playtime is prefer-cloud, NOT summed.** Heroic *pushes* its GOG sessions up to
  GOG, so the cloud `time_sum` already contains them — summing would double-count.
- **Achievements ARE set** (GOG exposes them). Expect them sparse until games run
  through GOG's achievement service (Comet); Heroic's local achievement cache is
  often empty.
- The cloud is a **per-game fan-out** (~one request per owned game), not a single
  aggregate call — the slow part; `--no-cloud` is the fast, no-network path.

### What it deliberately leaves for a human

- `rating`, `genres`, `tags`, `notes` — subjective; add by hand to a GOG entry and
  they are **preserved across syncs** (matched by `appName`, one line each).
- Any non-GOG game — never touched (the Steam block, the Epic block, hand-added rows).
- `link` — GOG library rows carry no reliable store URL, so GOG entries have none.

### Workflow

1. **Freshen the token (cloud half):** open **Heroic once** so its GOG session is
   fresh, else the script warns and proceeds Heroic-local only. (Manual override:
   `GOG_REFRESH_TOKEN` / `GOG_USER_ID` in env or a gitignored `.env`; never commit.)

2. **Preview** (writes nothing):
   ```
   python3 scripts/sync-gog.py --dry-run             # Heroic + cloud
   python3 scripts/sync-gog.py --no-cloud --dry-run  # Heroic-local only
   ```

3. **Sync**:
   ```
   python3 scripts/sync-gog.py
   ```

4. **Eyeball the diff**: `git diff data/gaming.yaml` — confirm the Steam/Epic blocks
   and hand-added entries are untouched and new covers look right.

5. **Sanity-check the build**: `hugo` should succeed.

Do **not** run `./deploy.sh` — deployment is a separate step the user authorizes
explicitly.

### Note on the private GOG API

The cloud half uses GOG's undocumented Galaxy endpoints (`auth.gog.com`,
`gameplay.gog.com`) with your own token — the same thing Heroic / gogdl do. Your own
data, read-only. The OAuth client id/secret baked into the script is the well-known
public Galaxy constant, not a secret.

## Working on the photo dex

The dex at `/gallery/dex/` is a Pokédex-style checklist of animal species: which
ones the photo gallery already contains, and which are still open. See the
"Photo dex" section of `CLAUDE.md` for the data model. All seven scripts are
standard-library only and edit `data/dex.yaml` through the shared reader/writer
in `scripts/dex_common.py`, so field order and quoting stay stable and the git
diff only shows what actually changed.

### The scripts, in the order they are normally used

| Script | Owns | Rerunnable |
|---|---|---|
| `dex-import.py` | one-shot import of the `animal-dex` proof of concept | yes, only adds missing species |
| `dex-add.py` | adding one species by hand | yes |
| `dex-tag-photos.py` | the `species:` field in `data/gallery.yaml` | yes, never retags |
| `dex-enrich.py` | the empty fields of `data/dex.yaml` | yes, never overwrites |
| `dex-ranges.py` | `assets/data/dex/**` | yes, `--force` to refetch |
| `dex-covers.py` | `assets/images/dex/reference/**` + `reference.*` | yes, `--force` to refetch |
| `dex-renumber.py` | the `number` field — closes gaps after a removal | yes, idempotent |

### Adding a species you just photographed

1. **Add the photo** to the gallery the normal way (drop it in the photo store,
   then `python3 scripts/sync-gallery.py` and fill in the stub entry).

2. **Make sure the species exists** in `data/dex.yaml`:
   ```
   python3 scripts/dex-add.py "Sand Lizard" --scientific "Lacerta agilis" \
       --family Lacertidae --difficulty moderate
   ```
   The dex number is assigned automatically. Skip this if the species is
   already listed — the script tells you and does nothing.

3. **Tag the photo.** Either add `species: <Scientific name>` under the entry's
   `category:` line by hand (`species: Lacerta agilis` — the scientific name, not
   the slug, and it must match `scientific:` in `data/dex.yaml`), or let the
   tagger propose it:
   ```
   python3 scripts/dex-tag-photos.py --dry-run
   python3 scripts/dex-tag-photos.py --write
   ```
   The tagger only ever fills in entries that have no `species:` yet, so it is
   safe to rerun. Its `MANUAL`/`ALIASES` tables are keyed by slug because that is
   what is readable to write by hand; it resolves the slug to the scientific name
   as it writes. Photos it cannot identify are listed and left alone — an
   untagged photo is a normal gallery photo, it just is not in the dex. A
   `species:` value that matches no dex species logs a build warning and drops
   those photos from the dex; the build still succeeds.

4. **Fill in the facts** (only touches empty fields):
   ```
   python3 scripts/dex-enrich.py --only sand-lizard
   ```
   **Check `body_weight`, `height` and `lifespan` by hand afterwards — do not
   trust them.** A full audit of all 186 species then in the dex (August 2026; 34 were
   removed afterwards) found 82 of the 83 `body_weight` values this script had
   produced were wrong, several by three
   to six orders of magnitude (whale shark `12`, humpback `1.5–45` with no unit,
   giant panda `104–117.5 g`, common buzzard `0.9–966.5 kg`, giraffe `54.5 kg`).
   The cause is `quantity_range()` in `scripts/dex-enrich.py`: it takes
   `min()`/`max()` across *every* Wikidata mass statement for the taxon while
   ignoring the qualifiers that distinguish them, so a newborn's mass becomes the
   low end and a record specimen the high end; it also silently discards any
   value whose unit QID is missing from the 5-entry `UNIT_MAP` (pounds, tonnes),
   leaving an incoherent partial set. `lifespan` has the same shape of problem —
   it tends to land on the record-longevity figure rather than the typical adult
   range. The audit also established the house conventions those fields follow:
   en-dash ranges, `mm`/`cm`/`m` and `g`/`kg`/`t`, a bare year range for
   `lifespan`, and a `height_measure` slug on every record that has a `height`.

   Also note two rules the script cannot know: a **domesticated form has no IUCN
   assessment**, so `iucn` must be absent on dog/cat/cattle/sheep/goat/chicken/
   domestic duck/alpaca rather than carrying the wild ancestor's category, and a
   **Europe-only regional assessment is not a global one** (the honeybee and
   carder bee had regional categories that had to be removed). Both rules are now
   held by the `PROTECTED` table at the top of `scripts/dex-enrich.py`: "fill only
   what is empty" cannot tell a never-populated field from a deliberately emptied
   one, so a rerun used to put those twelve `iucn` values straight back. **If you
   ever correct a field by clearing it, add it to `PROTECTED`** or the next run
   undoes you.

5. **Fetch its map and, if you have not photographed it, its stand-in photo:**
   ```
   python3 scripts/dex-ranges.py --only sand-lizard
   python3 scripts/dex-covers.py --only sand-lizard
   ```

6. **Check the build**: `hugo` should succeed and the species should appear at
   `/en/gallery/dex/sand-lizard/`.

Do **not** run `./deploy.sh` — deployment is a separate step the user authorizes
explicitly.

### Removing a species

Nothing automates this, and the order matters:

1. **Check it is not photographed first.** A species counts as photographed when a
   `data/gallery.yaml` entry carries its scientific name. Removing a dex entry that
   photos still point at leaves those photos referencing nothing — the build warns
   but does not fail, and they silently drop out of the dex:
   ```
   grep -c "^  species: <Scientific name>$" data/gallery.yaml
   ```
   If it is non-zero, retag or keep the species; do not remove it.

2. **Delete the record** from `data/dex.yaml` (match on `slug`).

3. **Delete the assets it owned**, or they become orphans nothing renders:
   ```
   rm -f assets/data/dex/ranges/<slug>.geojson
   rm -f assets/images/dex/reference/<slug>.jpg
   ```

4. **Close the numbering gap** it left behind:
   ```
   python3 scripts/dex-renumber.py --dry-run
   python3 scripts/dex-renumber.py --write
   ```
   `number` is both the badge and the grid's only sort key, so holes read as
   missing entries. The renumber preserves the existing order and only closes the
   holes. It does shift numbers, which is safe: `number` appears in the two badges
   and that one sort, never in a URL, a deep link, or the likes API.

5. **Update the counts** in `CLAUDE.md` (species total, range/reference file counts,
   `marine: true` count) and rebuild.

### What the scripts deliberately leave for a human

- **Species identification.** `dex-tag-photos.py` matches alt text, tags and
  filenames against the dex names, and carries a `MANUAL` table of photos that
  were identified by eye. It will not guess: a gull that could be two species
  stays untagged.
- **`difficulty`** — how hard the animal is to photograph is a judgement call,
  so `dex-add.py` defaults it to `moderate`.
- **`tips.best_time` / `tips.approach`** — the field notes are yours to write;
  nothing generates them.
- **`sightings`** — where you actually saw it. Only 13 of the gallery photos
  carry GPS EXIF, so these coordinates are hand-entered.
- **Habitat prose, in every language.** `dex-enrich.py` fills `description` in
  all three languages — each one abridged from that language's *own* Wikipedia
  article via the Wikidata sitelink, so nothing is machine-translated — but
  `habitat` is hand-written and only ever carries `en` and `de`. Where a language
  has no article (4 species have no `svwiki` sitelink, and the sv summary for
  `european-polecat` is a 28-character stub the script's 50-character floor
  rejects), the page falls back to English and credits the English article.

### If a species' range looks wrong on the map

Work through it in this order — the first two are rendering, the third is the data.

1. **Green floating in open ocean at the left/right edge, mirroring a landmass.**
   That is the ±360° copies showing without a base map under them. Every vector
   layer must be duplicated together; see the map notes in `CLAUDE.md`.
2. **Green everywhere *except* on land.** The range is painting under the land
   instead of over it — check the pane z-indexes in `assets/js/dex-map.js`.
3. **Green spilling a few hundred km out from the coast, or across a whole sea.**
   That is the source data, not the pipeline: iNaturalist's geomodel is a coarse
   thresholded prediction and genuinely includes water for widespread species.
   The ocean mask hides it for terrestrial species. If a *marine* species looks
   wrong, check its `marine: true` flag — without it the mask erases its range.
4. **A wrong animal's range entirely.** Check `inat_taxon_id`. `dex-enrich.py`
   resolves it by name and falls back to iNaturalist's first search hit, which
   can silently attach the wrong taxon. Fix the id by hand, then
   `python3 scripts/dex-ranges.py --only <slug> --force`.
5. **Scattered fragments where the animal is actually widespread.** The geomodel
   itself is thin for that species — nothing downstream can recover it. Compare
   against its peers with `python3 scripts/dex-ranges.py --audit`, which lists
   the area every stored range covers. Red fox is the known case: 608 sq deg
   against 7,748 for grey wolf and 25,189 for wild boar, and it renders as
   coastal fringes. Small numbers are not automatically wrong — the Galapagos
   giant tortoise is legitimately 3 sq deg.

Note that the ocean mask makes simplification much less visible — coarsened
outlines mostly get clipped away at the coast — so raising `--max-kb` buys less
than it looks like it should.

### Sizes to keep an eye on

`dex-ranges.py` simplifies the iNaturalist polygons until each fits `--max-kb`
(45 KB), coarsening a wide-ranging species rather than dropping its map. The
whole set is ~4.2 MB. `dex-covers.py` fetches ~960px Commons thumbnails (`--width 900`; see that script's docstring for why, and why Commons ignores widths in between) and, by
default, only for species you have *not* photographed — the rest show your own
photo, so a stand-in for them would be bytes nothing renders.

## Adding a model

A "model" is a person who appears in a gallery photo and has a page at
`/gallery/models/<slug>/`. See the "Models" section of `CLAUDE.md` for the data
model and the reasoning. There is **no script** for this — it is a handful of
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
   notice was built and then deliberately removed — see CLAUDE.md; do not re-add
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

All four are hard errors naming the file and the value, not warnings — unlike a
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

Do **not** run `./deploy.sh` — deployment is a separate step the user authorizes
explicitly.

## Testing

One command, one report. `docs/concepts/testing.md` is the design; §11 of it is
what the first run found and where the implementation departs from the plan.

```
npm test              # everything: build + python + static + browsers, ~1 min warm
npm run test:quick    # build + python + static, no browsers, no determinism
npm run test:e2e      # firefox only
npm run report        # reopen the last HTML report
npm run golden:update # after an INTENTIONAL URL change — see below
```

First time on a machine: `npm install` and `npx playwright install firefox chromium`.

### The seven projects

| Project | What it is | Needs the photos |
|---|---|---|
| `build` | `hugo -e production -b http://localhost:1414 -d .test-site` with **every `WARN` treated as a failure**, plus `hugo mod verify` | yes |
| `python` | `python3 -m unittest` over `tests/py/`, one report entry per module | no |
| `static` | the checks over the built site — data ↔ output, links, JSON-LD, feeds, sitemap, URL stability, models | reads the build |
| `firefox` | **the primary browser**; a failure here is the one to look at first | yes |
| `chromium` | the same scenarios | yes |
| `mobile-chrome` | the `@mobile` subset on a Pixel 7 | yes |
| `webkit` / `mobile-safari` | **opt-in**, see below | yes |

`static` and the browser projects depend on `build`, so a failed build is one red
test with Hugo's log attached and everything downstream is skipped.

### Things that will bite you

- **A warning fails the build test.** That is deliberate: it is what turns an
  unknown `species:`, an empty gallery mount or a PaperMod deprecation into a
  stopped deploy. The escape hatch for a warning that is genuinely somebody
  else's problem is Hugo's `ignoreLogs` in `hugo.yaml`, keyed by the warning id,
  so an ignore is visible and reviewable — never a loosened test.
- **`.test-site/` is the build under test, never `public/`.** `public/` is
  written only by `deploy.sh`. Both are gitignored; `.test-site/` is another 8 GB.
- **A new i18n key lands in all three files or the suite fails** — in L0 as a
  Hugo warning and in L2 as a key-parity failure. That is the point.
- **A new page means `npm run golden:update`.** The golden list is append-only by
  construction: the script unions the current build with what is committed and
  never drops a line. A URL may only *leave* `tests/golden/published-urls.txt` in
  the same commit that adds its redirect — an alias on the page that replaced it,
  or an entry in that photo's `slugAliases:`.
- **Nothing reaches the network.** Every request to a host other than localhost
  is aborted; the companion API, listmonk and the map tiles are mocked, and the
  analytics script is answered with an empty stub (blocking it makes Chromium log
  a console error that Firefox does not). If a scenario needs a third party, it
  asks for it by name with `test.use({ net: { allow: [...] } })`.
- **Writing a lightbox scenario? Use `openLightbox()` from
  `tests/support/fixtures.ts`.** PhotoSwipe wires the keyboard and the close path
  in `openingAnimationEnd`, which is well after `.pswp--open` appears — act too
  early and the click or key press is swallowed, which looks exactly like a bug
  in the site. That helper waits for the right moment.
- **WebKit does not run on Fedora as shipped.** Playwright's build links
  `libicu*.so.74` and `libjpeg.so.8`; Fedora has ICU 77 and `libjpeg.so.62`, and
  `playwright install-deps` only knows apt. Run it in the container:
  ```
  podman run --rm --network=host -v "$PWD":/w -w /w \
    mcr.microsoft.com/playwright:v1.63.0-noble npx playwright test --project webkit
  ```
  or `WEBKIT=1 npm test` once the libraries are present. It is out of the default
  run on purpose: a suite that is red every time teaches people to ignore red.
- **An engine-specific skip is written down with its reason**, never left silent
  — see the clipboard read-back in `tests/e2e/photo-page.spec.ts`.

### Adding a Python test

`tests/py/test_*.py`, stdlib `unittest`, no pytest — the scripts are stdlib-only
so that any machine with `python3` can add a photo, and their tests keep that
property. `from _load import load` imports a script whose filename has dashes
(`load("sync-steam")`); the dashless modules import by name. The bridge picks up
new `test_*.py` files automatically.

### Where the deploy gate sits

`deploy.sh` runs `npm test` first, then its own `hugo --panicOnWarning`, then the
`static` project **once more over `public/`** with the production base URL — the
one check that can catch a stale or development build in the artefact itself —
and only then embeds metadata, checks and rsyncs. `set -e` means a failure at any
step stops the script before anything reaches the server.
