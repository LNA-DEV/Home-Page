#!/usr/bin/env python3
"""Sync Steam-owned games into data/gaming.yaml.

data/gaming.yaml is a flat list of games written by MULTIPLE sources (see the
header comment in that file). This script owns exactly one slice of it: the
entries with `platform: steam`. On every run it:

  * Fetches the owned-games library from the Steam Web API (IPlayerService).
  * Optionally fetches every achievement of every game (ISteamUserStats: the
    schema in en/de/sv, the player's unlocks, the global unlock percentages),
    writes them to data/gameAchievements/steam-<appid>.json and the icons to
    static/images/games/achievements/steam/<appid>/, and downloads each game's
    portrait cover into assets/images/games/covers/.
  * Rebuilds the `platform: steam` entries from the live library — games newly
    owned are ADDED, games no longer in the library are PRUNED — and writes
    them as the LAST block in the file, below a marker it emits.

Everything that is NOT `platform: steam` is left byte-for-byte untouched, so
hand-added games (platform: gog / switch / manual / ...) are safe. Human-owned
fields on a Steam entry (extraMinutes, and the rating / genres / tags / notes
that now belong in data/gamePages.yaml) are preserved across syncs: they are
read back out of the old entry and re-emitted verbatim, keyed by `appid`. (Keep
those human fields to a single line each — that is how the script re-emits
them.)

Every entry carries a `slug:` — the game's page URL. A game keeps the slug it
was given the first time it was synced; a new game gets one from its title
(scripts/gaming_common.py), and one whose slug another platform already uses
joins that game's page. See docs/concepts/gaming-game-pages.md §2.

The YAML is edited as raw text — there is no YAML dependency, matching
add-book.py / sync-gallery.py. Standard library only.

Credentials (never printed, never committed) — supplied via a CLI flag, the
environment, or a .env file (repo-root or cwd, gitignored):
    STEAM_API_KEY   from https://steamcommunity.com/dev/apikey   (or --api-key)
    STEAM_ID        your 64-bit SteamID                          (or --steam-id)
Precedence: --api-key / --steam-id  >  real environment variable  >  .env file.

Usage:
    # with a .env file in the repo root holding STEAM_API_KEY / STEAM_ID:
    python3 scripts/sync-steam.py --dry-run
    # or inline / from the environment:
    STEAM_API_KEY=... STEAM_ID=... python3 scripts/sync-steam.py
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gaming_common  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DATA = REPO / "data" / "gaming.yaml"
DEFAULT_COVERS = REPO / "assets" / "images" / "games" / "covers"
COVER_REF_PREFIX = "images/games/covers"

USER_AGENT = "lna-dev.net gaming-sync (github.com/lna-dev; contact via site)"

# Sentinel marking the start of the auto-managed Steam block. Any line exactly
# equal to this is stripped on every run and re-emitted once, so it never
# accumulates or drifts above the hand-added entries.
STEAM_MARKER = "# ==== STEAM: auto-managed by scripts/sync-steam.py (regenerated each sync) ===="

# Human-owned fields on a Steam entry that must survive a resync. Re-emitted
# verbatim (single line each) after the script-owned mechanical fields.
# rating / genres / tags / notes belong in data/gamePages.yaml now, and the build
# says so — but a sync never destroys what somebody typed, so they are kept here.
# `slug` is not in this list: it is identity, emitted second, not a trailing line.
HUMAN_FIELDS = ("rating", "genres", "tags", "notes", "extraMinutes")

# Steam's language names for the three site languages.
STEAM_LANGS = (("en", "english"), ("de", "german"), ("sv", "swedish"))


class TransientError(Exception):
    """A fetch that failed for a reason that may be gone next time (network,
    5xx, rate limit). The game keeps yesterday's achievement counts and file."""


# --------------------------------------------------------------------------- #
# .env loading (stdlib only — no python-dotenv dependency)                      #
# --------------------------------------------------------------------------- #
def load_dotenv(path, *, override=False):
    """Load KEY=VALUE pairs from a .env file into os.environ.

    Ignores blank lines and `#` comments, tolerates a leading `export `, and
    strips a matching pair of single/double quotes around the value (and an
    inline `#` comment on unquoted values). A missing file is a no-op. Existing
    environment variables win unless override=True. Returns the keys loaded."""
    loaded = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return loaded
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        else:
            hash_idx = value.find(" #")  # strip trailing inline comment
            if hash_idx != -1:
                value = value[:hash_idx].rstrip()
        if override or key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


# --------------------------------------------------------------------------- #
# HTTP helpers (mirrors add-book.py)                                           #
# --------------------------------------------------------------------------- #
def http_get(url, accept_json=False):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return json.loads(data) if accept_json else data


def yaml_quote(value):
    """Quote a scalar for YAML when it contains risky characters."""
    if value is None:
        return '""'
    text = str(value)
    if text == "" or re.search(r'[:#\'"\[\]{}&*!|>%@`,]', text) or text != text.strip():
        return '"' + text.replace('"', '\\"') + '"'
    return text


def safe_filename(title):
    # Match add-book.py's convention: Linux allows almost everything in a
    # filename, so only strip path separators (and surrounding whitespace).
    return title.replace("/", "-").strip()


# --------------------------------------------------------------------------- #
# Steam Web API                                                               #
# --------------------------------------------------------------------------- #
def steam_owned_games(api_key, steam_id):
    params = {
        "key": api_key,
        "steamid": steam_id,
        "include_appinfo": "1",
        "include_played_free_games": "1",
        "format": "json",
    }
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?" + \
        urllib.parse.urlencode(params)
    result = http_get(url, accept_json=True)
    return (result.get("response") or {}).get("games") or []


def steam_api(path, params):
    url = f"https://api.steampowered.com/{path}?" + urllib.parse.urlencode(params)
    return http_get(url, accept_json=True)


def steam_player_achievements(api_key, steam_id, appid):
    """The player's achievement list for a game (apiname, achieved, unlocktime,
    name, description), or None when the game has no stats. 400 means "no stats",
    403 a private profile — both are answers, not failures. Anything else raises
    TransientError, so the caller keeps what it had."""
    try:
        result = steam_api("ISteamUserStats/GetPlayerAchievements/v1/",
                           {"appid": appid, "key": api_key, "steamid": steam_id, "l": "english"})
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 403, 404):
            return None
        raise TransientError(f"HTTP {exc.code}") from exc
    except Exception as exc:  # noqa: BLE001 - network: transient by definition
        raise TransientError(str(exc)) from exc
    stats = result.get("playerstats") or {}
    if not stats.get("success"):
        return None
    return stats.get("achievements") or None


def steam_schema(api_key, appid, lang):
    """The game's achievement schema in one Steam language (displayName,
    description, icon, hidden). [] on any failure — the English fallback in the
    player list and in the template covers a missing language."""
    try:
        result = steam_api("ISteamUserStats/GetSchemaForGame/v2/",
                           {"key": api_key, "appid": appid, "l": lang})
    except Exception:  # noqa: BLE001 - a missing translation is not an error
        return []
    return ((result.get("game") or {}).get("availableGameStats") or {}).get("achievements") or []


def steam_global_percentages(appid):
    """{apiname: percent of all players who unlocked it}. Public, no key."""
    try:
        result = steam_api("ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/",
                           {"gameid": appid})
    except Exception:  # noqa: BLE001 - a game without percentages still renders
        return {}
    out = {}
    for a in (result.get("achievementpercentages") or {}).get("achievements") or []:
        try:
            out[a["name"]] = float(a["percent"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def build_steam_achievements(appid, player, schemas, percents):
    """Pure: one Steam copy's achievements document and the icon URLs it needs.

    `player`   GetPlayerAchievements' list — authoritative for WHICH achievements
               exist and which are unlocked, so the page's row count always
               equals the card's achievementsTotal;
    `schemas`  {"en"|"de"|"sv": GetSchemaForGame list} — names, descriptions,
               icons, the hidden flag, and the display order;
    `percents` {apiname: global unlock percentage}.

    Steam delivers no description for a hidden achievement at all, locked or
    unlocked (checked 2026-09-28: 0 of 660), so those items simply have none."""
    by_lang = {lang: {a.get("name"): a for a in schemas.get(lang) or []}
               for lang, _ in STEAM_LANGS}
    pmap = {p.get("apiname"): p for p in player if p.get("apiname")}
    order = [a.get("name") for a in schemas.get("en") or [] if a.get("name") in pmap]
    seen = set(order)
    order += [k for k in pmap if k not in seen]

    items, urls = [], []
    for key in order:
        s_en = by_lang["en"].get(key) or {}
        p = pmap[key]
        names = {"en": s_en.get("displayName") or p.get("name") or key}
        descs = {"en": s_en.get("description") or p.get("description") or ""}
        for lang in ("de", "sv"):
            s = by_lang[lang].get(key) or {}
            names[lang] = s.get("displayName") or ""
            descs[lang] = s.get("description") or ""
        item = {
            "key": key,
            "name": gaming_common.localised(names),
            "hidden": bool(int(s_en.get("hidden") or 0)),
        }
        description = gaming_common.localised(descs)
        if description:
            item["description"] = description
        if s_en.get("icon"):
            item["icon"] = gaming_common.icon_ref("steam", appid, s_en["icon"])
            urls.append(s_en["icon"])
        if p.get("achieved"):
            item["achieved"] = True
            when = gaming_common.berlin_iso(p.get("unlocktime"))
            if when:
                item["unlocked"] = when
        if key in percents:
            item["percent"] = round(percents[key], 1)
        items.append(item)
    return {"platform": "steam", "id": str(appid), "achievements": items}, urls


def download_cover(appid, title, covers_dir):
    """Download a portrait cover to <covers>/<title>.jpg, named after the game
    like the book covers. The Steam CDN is still addressed by appid — only the
    saved filename and repo ref are title-based. Returns the repo ref (or None).
    Skips the download when the file already exists."""
    fname = safe_filename(title) + ".jpg"
    dest = covers_dir / fname
    ref = f"{COVER_REF_PREFIX}/{fname}"
    if dest.exists():
        return ref
    candidates = [
        f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg",
        f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
    ]
    for url in candidates:
        try:
            data = http_get(url)
        except Exception:  # noqa: BLE001 - try next candidate
            continue
        if len(data) < 2000:  # tiny/empty blob => no real image
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return ref
    return None


# --------------------------------------------------------------------------- #
# Raw-text YAML parsing / rebuild (no YAML dependency)                         #
# --------------------------------------------------------------------------- #
def split_entries(lines):
    """Split a list of YAML lines into (preamble, chunks).

    A chunk starts at each top-level list item (`- ` at column 0) and runs to
    just before the next one. Trailing blank lines are stripped from every
    chunk and from the preamble so inter-entry spacing normalises to one blank
    line on output (idempotent). `preamble` is everything before the first
    entry (the header comment block)."""
    starts = [i for i, ln in enumerate(lines) if re.match(r"^-\s", ln)]
    if not starts:
        return _rstrip_blank(lines), []
    preamble = _rstrip_blank(lines[:starts[0]])
    chunks = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        chunks.append(_rstrip_blank(lines[start:end]))
    return preamble, chunks


def _rstrip_blank(block):
    block = list(block)
    while block and block[-1].strip() == "":
        block.pop()
    return block


def chunk_field(chunk, key):
    """Return the (unquoted) scalar value of `key` in a chunk, or None."""
    pat = re.compile(r'^\s*' + re.escape(key) + r':\s*(.*?)\s*$')
    for ln in chunk:
        m = pat.match(ln)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def chunk_human_lines(chunk):
    """Return the raw lines for any human-owned fields present in the chunk."""
    keep = []
    for ln in chunk:
        stripped = ln.strip()
        if any(stripped.startswith(f"{k}:") for k in HUMAN_FIELDS):
            keep.append(ln)
    return keep


def build_steam_entry(game, human_lines, slug):
    """Render one `platform: steam` YAML entry from fetched game metadata."""
    lines = [
        f"- title: {yaml_quote(game['title'])}",
        f"  slug: {slug}",
        "  platform: steam",
        f"  appid: {game['appid']}",
        f"  playtimeMinutes: {game['playtimeMinutes']}",
    ]
    if game.get("lastPlayed"):
        lines.append(f'  lastPlayed: "{game["lastPlayed"]}"')
    if game.get("achievementsTotal") is not None:
        lines.append(f"  achievementsUnlocked: {game['achievementsUnlocked']}")
        lines.append(f"  achievementsTotal: {game['achievementsTotal']}")
    if game.get("cover"):
        lines.append(f"  cover: {yaml_quote(game['cover'])}")
    lines.append(f'  link: "https://store.steampowered.com/app/{game["appid"]}/"')
    lines.extend(human_lines)  # already 2-space indented, verbatim
    return "\n".join(lines)


def rebuild(raw, games):
    """Pure reconcile: given the current file text and freshly fetched Steam
    `games`, return (new_text, summary). No network, no filesystem — unit
    testable. Non-steam entries are preserved verbatim; steam entries are
    regenerated (add new / prune de-listed) and written last."""
    trailing_newline = raw.endswith("\n") or raw == ""
    lines = raw.split("\n")
    if raw.endswith("\n"):
        lines = lines[:-1]
    # Drop any previously-emitted marker so it never accumulates.
    lines = [ln for ln in lines if ln != STEAM_MARKER]

    preamble, chunks = split_entries(lines)

    non_steam, old_human, old_appids = [], {}, set()
    old_slugs, old_counts, taken = {}, {}, set()
    for chunk in chunks:
        if (chunk_field(chunk, "platform") or "").lower() == "steam":
            appid = chunk_field(chunk, "appid")
            if appid:
                old_appids.add(appid)
                old_human[appid] = chunk_human_lines(chunk)
                old_slugs[appid] = chunk_field(chunk, "slug")
                old_counts[appid] = (chunk_field(chunk, "achievementsUnlocked"),
                                     chunk_field(chunk, "achievementsTotal"))
        else:
            non_steam.append(chunk)
            if chunk_field(chunk, "slug"):
                taken.add(chunk_field(chunk, "slug"))

    # Stable order => clean, idempotent diffs.
    games = sorted(games, key=lambda g: int(g["appid"]))
    new_appids = {str(g["appid"]) for g in games}

    # A game whose achievements were not fetched this time (--no-achievements, or
    # a transient failure) keeps the counts it had rather than silently losing
    # them — its achievement file is kept too, and the two must agree.
    carried = []
    for g in games:
        unlocked, total = old_counts.get(str(g["appid"]), (None, None))
        if g.get("achievementsSkipped") and total:
            g = dict(g, achievementsUnlocked=int(unlocked or 0), achievementsTotal=int(total))
        carried.append(g)
    games = carried

    slugs, new_slugs, joined = gaming_common.assign_slugs(
        games, lambda g: str(g["appid"]), old_slugs, taken)

    steam_blocks = [
        build_steam_entry(g, old_human.get(str(g["appid"]), []), slugs[str(g["appid"])])
        for g in games
    ]

    sections = []
    if preamble:
        sections.append("\n".join(preamble))
    for chunk in non_steam:
        sections.append("\n".join(chunk))
    if steam_blocks:
        sections.append(STEAM_MARKER + "\n\n" + "\n\n".join(steam_blocks))

    out = "\n\n".join(sections)
    if trailing_newline and not out.endswith("\n"):
        out += "\n"

    summary = {
        "added": sorted(new_appids - old_appids, key=int),
        "pruned": sorted(old_appids - new_appids, key=int),
        "updated": sorted(new_appids & old_appids, key=int),
        "manual": len(non_steam),
        "new_slugs": new_slugs,
        "joined": joined,
    }
    return out, summary


# --------------------------------------------------------------------------- #
# Fetch orchestration                                                          #
# --------------------------------------------------------------------------- #
def fetch_achievements(api_key, steam_id, entry):
    """Fill `entry` with the achievement counts, the document and its icon URLs.
    Five requests for a game with achievements: the player list, the schema in
    three languages, the global percentages."""
    appid = entry["appid"]
    try:
        player = steam_player_achievements(api_key, steam_id, appid)
    except TransientError as exc:
        print(f"  achievements fetch failed (appid {appid}): {exc} — keeping the old data",
              file=sys.stderr)
        entry["achievementsSkipped"] = True
        return
    if not player:
        return
    schemas = {lang: steam_schema(api_key, appid, name) for lang, name in STEAM_LANGS}
    percents = steam_global_percentages(appid)
    doc, urls = build_steam_achievements(appid, player, schemas, percents)
    entry["achievementsUnlocked"] = sum(1 for p in player if p.get("achieved"))
    entry["achievementsTotal"] = len(player)
    entry["achievementDoc"] = doc
    entry["achievementIcons"] = urls


def fetch_games(api_key, steam_id, covers_dir, *, include_unplayed,
                do_achievements, do_covers):
    raw_games = steam_owned_games(api_key, steam_id)
    print(f"Steam library: {len(raw_games)} owned games.", file=sys.stderr)
    games = []
    for g in raw_games:
        playtime = g.get("playtime_forever", 0)
        if not include_unplayed and playtime <= 0:
            continue
        appid = g["appid"]
        entry = {
            "appid": appid,
            "title": g.get("name", f"App {appid}"),
            "playtimeMinutes": playtime,
        }
        last = g.get("rtime_last_played")
        if last:
            entry["lastPlayed"] = time.strftime("%Y-%m-%d", time.gmtime(last))
        if do_achievements:
            fetch_achievements(api_key, steam_id, entry)
            time.sleep(0.3)  # be polite to the API
        else:
            entry["achievementsSkipped"] = True
        if do_covers:
            entry["cover"] = download_cover(appid, entry["title"], covers_dir)
        games.append(entry)
    print(f"Kept {len(games)} played games "
          f"({'incl.' if include_unplayed else 'excl.'} unplayed).", file=sys.stderr)
    return games


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sync Steam games into data/gaming.yaml.")
    parser.add_argument("--api-key", default=None,
                        help="Steam Web API key (else env STEAM_API_KEY or a .env file).")
    parser.add_argument("--steam-id", default=None,
                        help="64-bit SteamID (else env STEAM_ID or a .env file).")
    parser.add_argument("--env-file", type=Path, action="append", default=None,
                        help="Load STEAM_API_KEY / STEAM_ID from this file (repeatable). "
                             "Default: .env in the repo root and the current directory.")
    parser.add_argument("--include-unplayed", action="store_true",
                        help="Include owned games with 0 playtime (default: played only).")
    parser.add_argument("--no-achievements", action="store_true",
                        help="Skip per-game achievement lookups (faster). Every game keeps "
                             "the counts and the achievement file it already had.")
    parser.add_argument("--no-covers", action="store_true",
                        help="Skip cover downloads.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report add/update/prune counts without writing the file.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--covers", type=Path, default=DEFAULT_COVERS)
    args = parser.parse_args(argv)

    # Load .env before resolving credentials. Real environment variables win
    # over .env values; an explicit --api-key / --steam-id flag wins over both.
    env_files = args.env_file or [REPO / ".env", Path(".env")]
    for env_path in env_files:
        loaded = load_dotenv(env_path)
        if loaded:
            print(f"Loaded {', '.join(loaded)} from {env_path}", file=sys.stderr)

    api_key = args.api_key or os.environ.get("STEAM_API_KEY")
    steam_id = args.steam_id or os.environ.get("STEAM_ID")

    if not api_key or not steam_id:
        print("! Need a Steam API key and SteamID. Set STEAM_API_KEY and STEAM_ID "
              "(in the environment, a .env file, or via --api-key / --steam-id). "
              "Get a key at https://steamcommunity.com/dev/apikey", file=sys.stderr)
        return 2

    try:
        games = fetch_games(
            api_key, steam_id, args.covers,
            include_unplayed=args.include_unplayed,
            do_achievements=not args.no_achievements,
            do_covers=not args.no_covers,
        )
    except urllib.error.HTTPError as exc:
        print(f"! Steam API error: {exc} — check the key, SteamID, and that the "
              "profile's game details are public.", file=sys.stderr)
        return 1

    raw = args.data.read_text(encoding="utf-8") if args.data.exists() else ""
    new_text, summary = rebuild(raw, games)

    print(f"\nReconcile: +{len(summary['added'])} added, "
          f"~{len(summary['updated'])} updated, "
          f"-{len(summary['pruned'])} pruned; "
          f"{summary['manual']} manual entries untouched.", file=sys.stderr)
    if summary["pruned"]:
        print("  pruned appids: " + ", ".join(summary["pruned"]), file=sys.stderr)
    gaming_common.report_slugs(summary["new_slugs"], summary["joined"])

    # Achievement files: written for every game fetched this time, kept for every
    # game that was skipped (so the file and its carried-over counts agree), and
    # removed for games that left the library or turned out to have none.
    docs = {str(g["appid"]): g["achievementDoc"] for g in games if g.get("achievementDoc")}
    urls = {str(g["appid"]): g["achievementIcons"] for g in games if g.get("achievementDoc")}
    keep = set(docs) | {str(g["appid"]) for g in games if g.get("achievementsSkipped")}
    gaming_common.write_achievement_docs("steam", docs, urls, keep, dry_run=args.dry_run)

    if args.dry_run:
        print("(dry-run: nothing written)", file=sys.stderr)
        return 0

    args.data.write_text(new_text, encoding="utf-8")
    print(f"Wrote {args.data.relative_to(REPO) if args.data.is_relative_to(REPO) else args.data}.",
          file=sys.stderr)
    print("Now eyeball the diff and covers, then run `hugo` to sanity-check the build. "
          "Do NOT run ./deploy.sh — that is a separate, explicitly-authorized step.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
