# Gaming syncs: Steam, Epic, GOG and devices

**Syncing Steam — use `scripts/sync-steam.py`** (stdlib only; full workflow below). It owns only the `platform: steam` entries: it fetches the owned-games library from the Steam Web API, optionally every achievement (the files in `docs/gaming/overview.md`) + portrait covers, and **rebuilds** those entries (new games added, de-listed games pruned) as the last block in the file, below a marker it emits. Everything that is **not** `platform: steam` is left byte-for-byte untouched (raw-text editing, no YAML dep), so hand-added games are safe. Human-owned fields (`extraMinutes`, and any stray `rating`/`genres`/`tags`/`notes` — which the build then asks to move) on a Steam entry are preserved across syncs — re-emitted verbatim, keyed by `appid` (keep them single-line); the `slug` is preserved too, as the entry's second line. Needs `STEAM_API_KEY` + `STEAM_ID` (env or flags; never commit them). Default excludes 0-playtime games (`--include-unplayed` to keep them). Do **not** run `./deploy.sh` after syncing — separate, explicitly-authorized step.

**Syncing Epic — use `scripts/sync-epic.py`** (stdlib only; workflow below). Epic has **no** Steam-style public API, so this merges **two disjoint sources**, both reached through the **Heroic** launcher (no separate login): the owned library (`store_cache/legendary_library.json` under the Heroic config) + the Heroic-launched playtime of **every device** (the snapshots in `sources/gaming-devices/`, see *Gaming devices* below), and — by reusing the Epic OAuth refresh token Heroic stored (`legendaryConfig/legendary/user.json`) — the *historical* official-launcher playtime from Epic's private `library-service` cloud endpoint. A play session is launched by exactly one client on exactly one machine, so the sources are disjoint and `playtimeMinutes = Σ devices + cloud` per game, matched on the Epic `appName` (`artifactId` in the cloud response). It owns only `platform: epic` entries, rebuilds them as a marked block last in the file (mirroring the Steam sync), preserves human fields keyed by `appName`, and defaults to played-only (`--include-unplayed` to keep the rest). **No achievements** — Epic closed the achievement-progress API in Jan 2025. `--no-cloud` uses only the Heroic-local data (no token needed); if the cloud token is stale, **open Heroic once** to re-auth, then rerun. Do **not** run `./deploy.sh` after syncing — separate, explicitly-authorized step.

**Syncing GOG — use `scripts/sync-gog.py`** (stdlib only; workflow below). Modelled on the Epic sync — GOG also has **no** Steam-style public API, so it reads what the **Heroic** launcher cached on disk and (optionally) reaches GOG's cloud with the token Heroic stored: the owned library (`store_cache/gog_library.json`) + the Heroic-local playtime and dates of every device (the snapshots in `sources/gaming-devices/`), and — by reusing the GOG OAuth refresh token in `gog_store/auth.json` (Galaxy client id) — GOG's authoritative per-game playtime (`gameplay.gog.com/…/sessions` → `time_sum`) and achievements (`gameplay.gog.com/…/achievements`). **Two differences from Epic:** (1) playtime is **prefer-cloud, NOT summed** — Heroic pushes its sessions up to GOG so the cloud total already contains them, and Heroic also pulls that total back down into a device's local file, so the script takes `max(cloud, max over devices)` to avoid double-counting (with `--no-cloud` and two devices, a lower bound); (2) **achievements ARE set** (GOG exposes them, the win over Epic — though sparse until games run through GOG's achievement service), fetched for every game played anywhere: on any device or per the cloud's own `time_sum`, and written in full to `data/gameAchievements/gog-<appName>.json` with their icons, like Steam's. `lastPlayed` is the newest date any device's Heroic recorded; Heroic frequently records playtime with an empty date (and GOG's playtime API carries no date), so as a per-device fallback the export reads the GOG cloud-save sync time from `gog_store/saveTimestamps.json` (`_save_date` in `gaming_devices.py`), used only when Heroic has no date and only for games that use GOG cloud saves. It owns only `platform: gog` entries, keyed on `appName` (the numeric GOG product id), rebuilds them as a marked block last in the file (after the Steam/Epic blocks), preserves human fields, and defaults to played-only. The cloud is a per-game fan-out (~one request per owned game); `--no-cloud` uses only Heroic-local data (no token). If the token is stale, **open Heroic once** to re-auth. Do **not** run `./deploy.sh` after syncing — separate, explicitly-authorized step.

**Gaming devices — the syncs run on any machine without overwriting the others** (`scripts/gaming_devices.py`; design `docs/concepts/gaming-devices.md`). Heroic records Epic playtime (it never uploads it) and every Epic/GOG `lastPlayed` only on the machine that ran the game, so while the syncs read one Heroic directly, whichever machine synced last was the only one in `data/gaming.yaml`. Now each machine with Heroic keeps a **snapshot** of its own local data in `sources/gaming-devices/<device>.json` (committed; outside `data/`, so Hugo never loads it), and the Epic/GOG syncs merge all of them. Load-bearing rules: **one writer per file** — a run refreshes only its own device's snapshot and never writes another's; the snapshot is the device's **full state**, replaced each run (Heroic's totals are cumulative), never deltas, and deterministic (sorted keys, no export timestamp) so an idle run leaves it byte-identical; its fields are an **allowlist** (`title`, `minutes`, `lastPlayed` as a date, `cover`, `link`), the token files are never opened, and `validate()` refuses any other key on read. The device id is **`GAMING_DEVICE`** in the machine's gitignored `.env` (or `--device`) — no default, no host-name fallback, and a machine whose Heroic has played games but no id **stops the run** rather than silently contributing nothing. The export **refuses to shrink** a snapshot (a game losing minutes, or one with minutes vanishing — Heroic was reinstalled): `gaming_devices.py export --rotate` freezes the old file as `<device>-until-<date>.json` (still merged) and starts fresh; `--force` overwrites. A retired device needs nothing — its file stays and keeps counting; deleting it is how playtime would leave the site. Never copy a Heroic config onto a new machine (Epic would count it twice; the Epic sync warns on identical minutes + date across devices). `sync-games.sh` runs `gaming_devices.py check` first (writes nothing, so a missing id or a shrink stops the run before any sync writes) and `status` last. **No script runs git** — pull before, review/commit/push after, by hand.

## Syncing games from Steam

The gaming list lives in `data/gaming.yaml` (one entry per game) with cover
images committed under `assets/images/games/covers/`. The full data model is in
`docs/gaming/overview.md`. The file is written by **multiple
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
- Gives a game it sees for the first time a **`slug:`** (second line of the
  entry) and keeps every existing one forever — the slug is the game's page URL.
  The dry run prints each new slug, and says when it **joins** a game already on
  another platform (the same game on Switch and Steam becomes one page).
- Unless `--no-achievements`, writes **every achievement** of every game to
  `data/gameAchievements/steam-<appid>.json` — names and descriptions in
  en/de/sv where Steam has them, the unlock time (Europe/Berlin), the global
  unlock percentage — and downloads the icons into
  `static/images/games/achievements/steam/<appid>/`. Both are committed. A few
  icons Steam no longer serves at all are reported in one line per game; the
  page shows an empty tile for those. A game whose achievements could not be
  fetched keeps yesterday's counts and file.
- Downloads each game's portrait cover (`library_600x900`, falling back to
  `header.jpg`) into `assets/images/games/covers/<appid>.jpg`, skipping files
  that already exist (`--no-covers` to skip entirely).
- **Reconciles only the `platform: steam` entries** against the live library:
  newly-owned games are **added**, games no longer owned are **pruned**. It
  writes them as the last block in the file, under a marker it emits. By
  default 0-playtime games are excluded (`--include-unplayed` to keep them).

### What it deliberately leaves for a human

- `rating`, `notes`, your own description — subjective, and about the **game**
  rather than one copy of it, so they live in `data/gamePages.yaml`, keyed by
  slug, which no script writes. (A `rating:` or `notes:` line on an entry in
  `gaming.yaml` is still preserved by the sync, but the build stops and says to
  move it.) `extraMinutes` stays on the entry and survives syncs.
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
   `assets/images/games/covers/` look right. The Steam block moves to the bottom
   of the file on every run, so the diff is larger than what changed; the
   `data/gameAchievements/` diff is the real one — mostly `percent` lines.

5. **Sanity-check the build**: `hugo` should succeed. A new game gets a new page
   in three languages, so `npm test` then asks for `npm run golden:update`.

Do **not** run `./deploy.sh` — deployment is a separate step the user authorizes
explicitly.

### Adding a non-Steam game by hand

Copy the commented template at the top of `data/gaming.yaml`, uncomment it, and
set `platform:` to something other than `steam` (e.g. `switch`, `gog`,
`manual`). The Steam sync will leave it alone.

Give it a **`slug:`** — lowercase letters, digits, single hyphens; the build
refuses an entry without one. To put it on the page of a game you already have
on another platform, use **that** game's slug: copies with one slug are one
game. Then `npm run golden:update` for the new page's three URLs.

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
  uploads it to Epic) — on whichever machine ran it. Each machine's share is in
  its own device snapshot (see *Gaming devices* below).

A session is launched by exactly one client on exactly one machine, so the
totals are disjoint and the true per-game total is `Σ devices + cloud`, matched
on the Epic `appName` (the codename like `Salt` / `CrabEA`; the cloud endpoint
calls it `artifactId`).

### What the script does

- **Heroic-local (always, no login):** reads the owned library
  (`store_cache/legendary_library.json` → title, `appName`, portrait cover URL,
  store link), refreshes this machine's device snapshot from its Heroic-launched
  playtime + `lastPlayed` (`store/timestamp.json`, minutes), and reads every
  device's snapshot from `sources/gaming-devices/`. The Heroic config dir is
  auto-detected (Flatpak `~/.var/app/com.heroicgameslauncher.hgl/config/heroic`,
  then native `~/.config/heroic`; override with `--heroic-config`).
- **Epic cloud (unless `--no-cloud`):** reuses the Epic OAuth refresh token Heroic
  already stored (`legendaryConfig/legendary/user.json`) — **no separate login**.
  It refreshes that token and GETs `library-service`'s per-account playtime
  endpoint for the historical official-launcher hours (seconds → minutes).
- **Merges** them (`playtimeMinutes = Σ devices + cloud`, `lastPlayed` = the
  newest any device recorded), downloads each game's
  portrait cover into `assets/images/games/covers/<Title>.<ext>` (skipping ones
  that exist; `--no-covers` to skip), and **rebuilds only the `platform: epic`
  entries** (played games added, others pruned) as the last block in the file,
  under a marker it emits. 0-playtime games are excluded by default
  (`--include-unplayed` to keep them).
- Like the Steam sync, gives a new game a `slug:` once and keeps it forever; an
  Epic copy of a game you already own elsewhere joins that game's page.

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
  portrait cover URL; skips DLC/redist); this machine's device snapshot refreshed
  from its Heroic-launched playtime + `lastPlayed` (`store/timestamp.json`,
  minutes, with the cloud-save date as fallback), and every device's snapshot
  read from `sources/gaming-devices/`. Heroic config dir auto-detected (Flatpak
  first, then `~/.config/heroic`; `--heroic-config` to override).
- **GOG cloud (unless `--no-cloud`):** reuses the GOG OAuth refresh token Heroic
  stored (`gog_store/auth.json`, under the Galaxy client id) — **no separate login**.
  Refreshes it (GOG's token endpoint is a GET), then per owned game GETs the
  authoritative playtime (`gameplay.gog.com/games/{id}/users/{uid}/sessions` →
  `time_sum`) and, for played games (unless `--no-achievements`), achievements
  (`gameplay.gog.com/clients/{id}/users/{uid}/achievements`) — written in full to
  `data/gameAchievements/gog-<appName>.json`, icons to
  `static/images/games/achievements/gog/<appName>/`, exactly like the Steam sync.
  GOG's documented response has no global unlock percentage; if the live one
  carries `rarity` it is used, otherwise the page shows none. Achievements not
  fetched this run keep their old counts and file.
- Like the Steam sync, gives a new game a `slug:` once and keeps it forever.
- **Merges** with the **prefer-cloud** rule
  (`playtimeMinutes = max(cloud, max over devices)`, `lastPlayed` = the newest any
  device recorded),
  downloads covers into `assets/images/games/covers/<Title>.<ext>` (skips existing;
  `--no-covers`), and **rebuilds only the `platform: gog` entries** (played added,
  others pruned) as the last block, under a marker it emits. 0-playtime games
  excluded by default (`--include-unplayed`).

### How GOG differs from the Epic sync

- **Playtime is prefer-cloud, NOT summed.** Heroic *pushes* its GOG sessions up to
  GOG, so the cloud `time_sum` already contains them — summing would double-count.
  Heroic also pulls that total back down into a device's local file, so across
  devices the local numbers take the max too; with `--no-cloud` and two devices
  the result is a lower bound.
- **Achievements ARE set** (GOG exposes them), for every game played anywhere —
  on any device or per the cloud's own `time_sum`. Expect them sparse until games
  run through GOG's achievement service (Comet); Heroic's local achievement cache
  is often empty.
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

## Gaming devices (more than one Heroic machine)

Heroic records some things only on the machine that ran the game: every Epic
session, and every Epic/GOG `lastPlayed`. So each machine with Heroic keeps a
**snapshot** of its own local data in `sources/gaming-devices/<device>.json`,
and the Epic/GOG syncs merge all of them. A run writes **only its own device's
snapshot** — the syncs can run on any machine without overwriting the others.
Module and CLI: `scripts/gaming_devices.py`. Design:
`docs/concepts/gaming-devices.md`.

### Workflow — the same on every machine

```
git pull
scripts/sync-games.sh
git diff                 # sources/gaming-devices/<device>.json, data/gaming.yaml, covers
git commit … && git push
```

No script runs git; that stays manual. Forgetting the pull loses nothing — the
other machine's newest sessions just arrive at the next run after a pull. If
`data/gaming.yaml` conflicts (both machines committed without pulling in
between), take either side and run the sync again: the file is derived from the
snapshots, which never conflict.

### New machine, once

1. Clone the repository.
2. `.env` in the repo root with `GAMING_DEVICE=<slug>` (lowercase, e.g.
   `laptop`) plus `STEAM_API_KEY` / `STEAM_ID` — `sync-games.sh` runs all three
   syncs and stops at the first that fails.
3. Log Heroic in to Epic and GOG **fresh**. Never copy a Heroic config over from
   another machine: its `timestamp.json` would bring that machine's totals, and
   Epic (which sums devices) would count them twice. The Epic sync warns when
   two devices report the same minutes and `lastPlayed` for a game.

A machine whose Heroic has played games but no `GAMING_DEVICE` stops the run —
silently skipping it would drop its playtime from the site.

### The commands

```
python3 scripts/gaming_devices.py status            # one line per device
python3 scripts/gaming_devices.py check             # what sync-games.sh runs first; writes nothing
python3 scripts/gaming_devices.py export --rotate   # after a Heroic reinstall
python3 scripts/gaming_devices.py export --force    # accept a shrink without rotating
```

- **Heroic reinstalled** → the export refuses to write a snapshot in which a
  game lost minutes or vanished, and the sync stops before anything is written.
  `export --rotate` freezes the old file as `<device>-until-<date>.json` (still
  merged, never written again) and starts a fresh `<device>.json`.
- **Retired machine** → nothing to do. Its snapshot stays and keeps counting.
  Deleting a snapshot is how playtime would leave the site.
- The snapshot is an **allowlist** (`title`, `minutes`, `lastPlayed` as a date,
  `cover`, `link`) — no tokens, paths, host names or clock times, because the
  repository is public. A snapshot with any other key is refused on read.
