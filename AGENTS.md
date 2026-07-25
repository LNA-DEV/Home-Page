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
