# AGENTS.md

Generic entrypoint for coding agents working in this repo. The authoritative,
detailed project guide is **`CLAUDE.md`** — read it first for build/deploy,
the gallery system, and overall architecture. This file documents workflows
that are worth spelling out step by step.

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
