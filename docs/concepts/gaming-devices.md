# Concept: gaming devices — Heroic playtime from more than one machine

**Status:** implemented 2026-09-28 — `scripts/gaming_devices.py`, the Epic/GOG syncs, `sync-games.sh`, tests in `tests/py/`. Two refinements over the text below are marked *(implementation)*.
**Read against:** the working tree of 2026-09-28, `data/gaming.yaml` at 171 entries, `scripts/sync-{steam,epic,gog}.py` as of `c45f825`, and this PC's Heroic config (Flatpak).

The Epic and GOG syncs read **one** Heroic install: whichever machine runs `scripts/sync-games.sh`. Everything Heroic records only on disk — Epic playtime, every `lastPlayed` date, the GOG save-sync dates — therefore comes from that machine alone. Run the script on the gaming laptop instead, and the Epic block in `data/gaming.yaml` is rebuilt from the laptop's Heroic: the PC's Heroic minutes and dates are overwritten. Run it on the PC, and the laptop's are.

This adds **devices**. Every machine with Heroic keeps a small snapshot of its own local data in the repository, and the syncs merge all snapshots instead of reading the local Heroic directory directly. A run writes **only its own device's snapshot** and never another device's, so the script can run on any device without overwriting the others. Git stays manual, exactly as today.

"Device" is **not** a new `platform:`. The site keeps grouping by store (`steam` / `epic` / `gog` / `switch` …); a device is only where a number was collected, and it never reaches `data/gaming.yaml` or the page.

## Decisions

| | |
|---|---|
| Devices | Linux machines running **Heroic** (this PC, the gaming laptop). Flatpak or native, both paths already auto-detected |
| Unit | One **snapshot file per device**, holding that device's *full* current state — never deltas or sessions (§3) |
| Writer | Each file has exactly **one** writer: the device it is named after. A run never writes another device's snapshot |
| Location | `sources/gaming-devices/<device>.json`, committed. Outside `data/`, so Hugo never loads it. The name is free to change; nothing depends on it |
| Content | An allowlist: per store, per game `title`, `minutes`, `lastPlayed` (date only), `cover`, `link`. No tokens, paths, host names or clock times (§4) |
| Device id | `GAMING_DEVICE=<slug>` in the machine's gitignored `.env`, which every sync already loads. No default, no host-name fallback |
| Merge, Epic | `Σ devices + cloud` — every session is recorded by exactly one client on exactly one machine |
| Merge, GOG | `max(cloud, max over devices)` — Heroic pushes GOG sessions to the cloud *and* pulls cloud totals back down |
| `lastPlayed` | Newest across devices, for both stores |
| Where it runs | **Any device, the same command.** `data/gaming.yaml` is rebuilt from all snapshots in the working tree, so the result does not depend on the machine |
| Git | **Manual, unchanged.** Pull before running, review the diff, commit, push. The script runs no git command |
| Shrinking snapshot | The export **refuses** to write a snapshot in which a game lost minutes or vanished; `--rotate` freezes the old file after a Heroic reinstall (§6) |
| Retiring a device | Nothing to do. Its snapshot stays and keeps counting |
| Steam | Unchanged — the Web API is already account-wide |

---

## 1. What the data says today

This PC's Heroic `store/timestamp.json` has **5** entries:

| store | appName | minutes | dates |
|---|---|---:|---|
| epic | `Salt` | 14 | first + last |
| epic | `CrabEA` | 9 | first + last |
| gog | `1423049311` | 478 | last only |
| gog | `1816031813` | 2 | first + last |
| gog | `1297352383` | 28 | **none** |

And in `data/gaming.yaml`:

| platform | games | hours | with `lastPlayed` | source of the playtime |
|---|---:|---:|---:|---|
| steam | 59 | 1,937 | 59 | Web API, account-wide |
| epic | 42 | 107 | **2** | Epic cloud (official launcher) + Heroic-local |
| gog | 5 | 8 | 3 | GOG cloud (includes Heroic) |

Three things follow:

- **The Heroic-local Epic share is 23 minutes out of 107 hours today.** 40 of the 42 Epic games come from the official launcher's cloud history and have no date at all — the only two Epic dates on the site are the two Heroic games. With both machines on Heroic, every future Epic session is Heroic-local, so this share is where all new Epic playtime lands.
- **`1297352383` has 28 minutes and no date.** Heroic did not record that session itself; it wrote GOG's cloud total into the local file. So a device's local GOG number can already contain *another* device's play. That rules out summing GOG across devices (§5).
- `lastPlayed` for Epic and GOG is a purely local fact. Neither cloud endpoint carries a date.

## 2. What a second Heroic machine loses today

| | Steam | Epic via Heroic | GOG via Heroic |
|---|---|---|---|
| playtime | cloud ✓ | **✗ overwritten** — Heroic never uploads it | cloud ✓ |
| `lastPlayed` | cloud ✓ | ✗ overwritten | ✗ overwritten |
| achievements | cloud ✓ | — (API closed) | ✗ (below) |

"Overwritten" means: whichever device ran the sync last is the only one whose Heroic data is in the file.

The GOG achievements gap is an existing one: `sync-gog.py` fetches achievements only for games with **local** playtime (`played_local` in `build_games`), so a GOG game played only on another machine gets its cloud playtime but never its achievements — unless Heroic happened to pull the total down as in `1297352383`. The fix comes with this concept (§5).

## 3. The model: one full-state snapshot per device

A snapshot is `timestamp.json` reduced to what the site uses, for one device, replaced wholesale on every run of that device. The merge reads all of them.

**Full state, not deltas.** Heroic's `totalPlayed` is already cumulative, so exporting it is idempotent: running twice changes nothing, a device that has not run for a while only delays its numbers, and nothing has to remember what was sent. A delta or session log would need exactly that bookkeeping, and a lost or duplicated delta would corrupt a total permanently, with nothing to recompute it from.

**One file per device.** Every file has one writer, so two devices never change the same snapshot and git never has to merge one. The one shared file, `data/gaming.yaml`, is derived output: if it ever conflicts, it is regenerated rather than merged (§7).

Three alternatives, and why not:

- **Syncing Heroic's config directory, or `timestamp.json` itself, between machines** (Nextcloud/Syncthing). Both Heroics write the same file, the last writer wins, and one machine's sessions are gone. The directory also holds install paths, Wine prefixes and both OAuth tokens.
- **Pushing sessions to the HomePageCompanion API.** A new endpoint, authentication, server-side state and an uptime dependency — for a number that is only read at build time anyway.
- **A Nextcloud folder for the snapshots.** A second transport next to git — the devices need the repository anyway to run the syncs — and a machine-specific absolute path in a gitignored file, like the gallery mount in `config/_default/module.yaml`, with the same "forgot to set it up on this machine" failure mode. Snapshots in git are also versioned, which is what makes a lost one recoverable.

**A side effect worth having:** the committed snapshot also protects the *current* setup. Today, a lost or reinstalled Heroic config on this PC silently removes its Heroic minutes from the site at the next sync. With snapshots, the numbers are in git history and the export refuses to shrink them (§6).

## 4. Snapshot format

`sources/gaming-devices/laptop.json`:

```json
{
  "schema": 1,
  "device": "laptop",
  "stores": {
    "epic": {
      "Salt": {
        "cover": "https://cdn1.epicgames.com/…",
        "lastPlayed": "2026-02-26",
        "link": "https://www.epicgames.com/store/product/celeste",
        "minutes": 14,
        "title": "Celeste"
      }
    },
    "gog": {
      "1423049311": {
        "cover": "https://images.gog.com/…",
        "lastPlayed": "2026-08-01",
        "minutes": 478,
        "title": "Cyberpunk 2077"
      }
    }
  }
}
```

- **Only games with minutes or a date.** The owned library is account-wide and comes from the running machine's Heroic as today; a snapshot only carries what the device *played*.
- **`title` / `cover` / `link` ride along** for the games it lists, so a game bought and played only on the laptop still gets a card when the PC's library cache is stale. The running machine's library wins where it has the game.
- **`lastPlayed` is resolved at export**, with the GOG save-timestamp fallback `sync-gog.py` already applies (`gog_store/saveTimestamps.json`). That fallback is a per-device fact, so it belongs to the device.
- **Deterministic:** sorted keys, 2-space indent, trailing newline, and **no export timestamp**. A run with nothing new leaves the file byte-identical, so it shows up in `git diff` only when something was played — the same rule `security.txt` and the embed script follow. Freshness is `git log` on the file, or `status` (§8).
- **Allowlist, not denylist.** The exporter never opens `legendaryConfig/legendary/user.json` or `gog_store/auth.json`, and writes no path, host name, user name, install directory or clock time. `firstPlayed` is dropped too: the site does not use it, and the repository is public. Everything left is already on the page, except the split by device.
- `schema` lets the format change later without guessing.

## 5. Merge rules

`D` is the set of all snapshots in the working tree, the running device's fresh export included.

**Epic**

```
playtimeMinutes = Σ_d minutes_d[app] + cloud[app]
lastPlayed      = max_d lastPlayed_d[app]
```

A session is launched by exactly one client on exactly one machine, and Heroic never uploads Epic playtime, so every term is disjoint — the same argument `sync-epic.py` already makes for `heroic + cloud`, extended across machines.

**GOG**

```
playtimeMinutes = max(cloud[app], max_d minutes_d[app])
lastPlayed      = max_d lastPlayed_d[app]
achievements    fetched for every app with playtimeMinutes > 0
```

The cloud stays authoritative. Across devices the local numbers take the **max**, not the sum: `1297352383` shows a device's local GOG total may already be the cloud total, which includes every other device. Consequence: with `--no-cloud`, GOG playtime is a **lower bound** once there are two devices. That is acceptable — `--no-cloud` is the offline path — and the sync says so when it applies.

The achievements gate moves from "played on this machine" to "played anywhere": the cloud loop already fetches `time_sum` first, so it can fetch achievements in the same pass whenever `time_sum > 0` or any snapshot has minutes for the game. At most one extra request for a game played only elsewhere.

**Both**

- A game counts as played — and is kept past the played-only filter — if any device or the cloud has minutes for it.
- `title` / `cover` / `link`: the running machine's library first, else the first snapshot (in device-name order, for stable output) that has the game.
- Human fields (`rating`, `genres`, `tags`, `notes`, `extraMinutes`) are untouched; they live on the `gaming.yaml` entry, not on a device.
- **The result does not depend on which device runs it.** Same snapshots, same cloud → same `data/gaming.yaml`, byte for byte.

**Acceptance criterion for the switch-over:** with only this PC's snapshot present, both syncs produce a `data/gaming.yaml` byte-identical to today's.

## 6. Device identity and lifecycle

**Id.** `GAMING_DEVICE=pc` in the machine's `.env` (gitignored, already auto-loaded by all three syncs for the API keys), overridable with `--device`. The slug is chosen by hand, `[a-z0-9-]+`. There is no default and **no host-name fallback**: host names change, leak into a public repository, and a silently derived id would register the same machine twice after a rename.

**A machine with Heroic data and no id is an error.** If the sync finds a local Heroic install with played games but `GAMING_DEVICE` is unset, it stops and says so. The alternative — quietly skipping the local export — would drop this machine's newest sessions from the site with no trace.

**New device**, once:

1. Clone the repository (needed anyway to run the script).
2. `.env` with `GAMING_DEVICE=<slug>` plus `STEAM_API_KEY` / `STEAM_ID` — `sync-games.sh` runs all three syncs and stops at the first one that fails.
3. Log Heroic in to Epic and GOG **fresh**. **Never copy an existing Heroic config onto the new machine:** its `timestamp.json` would arrive with the old machine's totals and Epic would count them twice. The merge warns when two devices report the same nonzero minutes *and* the same `lastPlayed` for one game — a coincidence for a real game, a copied config otherwise.

**Retired device** (sold, wiped, broken). Nothing. Its snapshot is never written again and keeps counting as it stands. Deleting the file is how playtime would leave the site, so it is not something to do.

**Heroic reinstalled on a device** — `timestamp.json` restarts at zero. The export compares against the device's existing snapshot and **refuses** to write if any game's minutes went down or a game disappeared, naming the games; the run stops before `data/gaming.yaml` is touched. *(implementation)* A game "disappeared" only counts when it had minutes: a record that carried nothing but a GOG save date may vanish, since it cost no playtime. And because `sync-games.sh` runs the Steam sync before Epic and GOG, it starts with `gaming_devices.py check`, which runs the same checks and writes nothing — otherwise the Steam block would already be written when the Epic sync stopped. `--rotate` then renames the old file to `<device>-until-<date>.json` (frozen, still merged) and starts a fresh `<device>.json`. For Epic the sum stays exact. For GOG the max over a frozen file and a fresh one is a floor, which the cloud supersedes anyway. `--force` overwrites without rotating, for the case where a decrease is genuinely correct.

## 7. Git: manual, as today

The script runs no git command. What it writes on a device:

| file | written by |
|---|---|
| `sources/gaming-devices/<this device>.json` | this device only |
| `sources/gaming-devices/<other device>.json` | **never** — read only |
| `data/gaming.yaml`, new covers | every device, regenerated from all snapshots |

That table is the whole guarantee: another device's data can only change on that device.

**Pull before running.** The merge sees the snapshots that are in the working tree. Running without pulling does not overwrite anything — the other device's snapshot is simply not the newest yet, and its latest sessions show up at the next run after a pull.

**If `data/gaming.yaml` conflicts** (both devices ran and committed without pulling in between): take either side and run the script again. The file is derived from the snapshots, which never conflict, so the rerun produces the correct version. Resolving it by hand would be wasted work.

## 8. The tool and the workflow

`scripts/gaming_devices.py` — a module the syncs import (underscore name, like `dex_common.py`) and a small CLI:

```
python3 scripts/gaming_devices.py status              # one line per device
python3 scripts/gaming_devices.py check               # id set, snapshots valid, nothing shrinking; writes nothing
python3 scripts/gaming_devices.py export --rotate     # after a Heroic reinstall (§6)
python3 scripts/gaming_devices.py export --force      # accept a shrink without rotating
```

`sync-games.sh` stays the entry point with the same interface; the export of the running device happens inside the Epic and GOG syncs, so there is no extra step. It runs `check` first *(implementation)* and `status` last. `status` prints, per device: Epic games, GOG games, minutes, newest `lastPlayed`:

```
device  epic   gog  minutes  last played
pc         2     3      531  2026-08-01
```

**On every device:**

```
git pull
scripts/sync-games.sh
git diff                 # sources/gaming-devices/<device>.json, data/gaming.yaml, covers
git commit … && git push
```

The same four steps as today, on whichever machine.

## 9. What this does not do

- **No git automation.** Pulling, committing and pushing stay manual.
- **No per-device display on the site.** The page keeps grouping by store.
- **Consoles are not devices.** Switch / 3DS / DS stay hand-entered platforms, and the syncs never touch them.
- **No Amazon (nile) or sideloaded games.** Heroic's `timestamp.json` has them too; the snapshot's per-store layout leaves room for an `amazon` key if an Amazon sync ever exists.
- **No Windows.** Both devices run Heroic on Linux. A Windows device would need `%APPDATA%\heroic` as a path candidate and Python; the snapshot format would not change.
- **No change to Steam.** `GetOwnedGames` is account-wide.

## 10. Tests

In `tests/py/test_gaming_devices.py` and `tests/py/test_game_syncs.py`, stdlib `unittest` — no Heroic install, no network:

- export from a fixture Heroic dir: only played games, allowlisted keys only (a test lists the keys and fails on any other), no token file opened, date-only `lastPlayed`, GOG save-date fallback applied;
- a second export over the same input is byte-identical;
- **a run writes only its own snapshot**: the other device's file is byte-identical afterwards;
- a decreased or vanished game refuses the write; `--rotate` freezes and restarts; `--force` overwrites;
- Epic: two devices + cloud sum; `lastPlayed` is the newest;
- GOG: two devices take the max, the cloud wins when higher; a game played only on another device gets its achievements requested;
- a laptop-only game gets its title and cover from the snapshot;
- the same snapshots give the same `gaming.yaml` whichever device is "local";
- identical `(minutes, lastPlayed)` on two devices warns;
- no `GAMING_DEVICE` with a local played game is an error;
- **with one device, both `rebuild()` outputs equal the ones produced from today's direct read** — the acceptance criterion of §5, as a test.

## 11. Build order

1. `scripts/gaming_devices.py`: export, guard, `--rotate`, `status`; its tests.
2. **On this PC** (a local setup step, done by hand): `GAMING_DEVICE=pc` in `.env`.
3. `sync-epic.py` exports the local device and reads all snapshots; verify `data/gaming.yaml` is byte-identical.
4. `sync-gog.py` the same, plus the max rule and the achievements gate; verify byte-identical except where the gate adds achievements.
5. `sync-games.sh` prints `status` at the end.
6. Docs: the *Gaming* section of `CLAUDE.md`, the sync workflows in `AGENTS.md`, the header comment of `data/gaming.yaml`.
7. Laptop: the three steps of §6 *New device*, then the normal workflow.

## 12. Files touched

### New

- `scripts/gaming_devices.py`
- `sources/gaming-devices/pc.json` (and `laptop.json`, written by the laptop's first run)
- `tests/py/test_gaming_devices.py`

### Modified

- `scripts/sync-epic.py` — export the local device; playtime and dates from all snapshots instead of `store/timestamp.json`; sum across devices
- `scripts/sync-gog.py` — same; max across devices; achievements gate
- `scripts/sync-games.sh` — `check` first, `status` at the end
- `tests/py/test_game_syncs.py` — the merge cases above
- `CLAUDE.md`, `AGENTS.md`, `data/gaming.yaml` (header comment only)
