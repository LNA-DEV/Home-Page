#!/usr/bin/env python3
"""Sync GOG games into data/gaming.yaml.

data/gaming.yaml is a flat list of games written by MULTIPLE sources (see the
header comment in that file). This script owns exactly one slice of it: the
entries with `platform: gog`. It is modelled directly on sync-epic.py — GOG, like
Epic, has no Steam-style public API, so it reads what the **Heroic** launcher has
already cached on disk and (optionally) reaches GOG's cloud with the OAuth token
Heroic stored. On every run it:

  * Reads the GOG library + local playtime Heroic already cached (no login):
      - store_cache/gog_library.json  -> owned games (title, cover), keyed by
                                         app_name (the numeric GOG product id)
      - store/timestamp.json          -> playtime for games launched via Heroic
                                         (minutes), keyed by app id (cross-runner)
      - gog_store/saveTimestamps.json -> GOG cloud-save sync time, used as a
                                         lastPlayed FALLBACK for games that have
                                         playtime but an empty timestamp.json date
  * Optionally reaches GOG's cloud (unless --no-cloud) by reusing the GOG refresh
    token Heroic stored (gog_store/auth.json, under the Galaxy client id):
      - gameplay.gog.com .../sessions      -> `time_sum`, the authoritative total
      - gameplay.gog.com .../achievements  -> unlocked/total (unless --no-achievements)
  * Rebuilds the `platform: gog` entries (played games added, others pruned) and
    writes them as the LAST block in the file, below a marker it emits.

Everything that is NOT `platform: gog` is left byte-for-byte untouched, so the
Steam block, the Epic block, and hand-added games are all safe. Human-owned fields
on a GOG entry (rating, genres, tags, notes) are preserved across syncs: read back
out of the old entry and re-emitted verbatim, keyed by `appName`. (Keep those
human fields to a single line each.)

THREE deliberate differences from sync-epic.py:

  1. Playtime is PREFER-CLOUD, NOT summed. Epic's two sources are disjoint so it
     adds them. GOG is the opposite: Heroic *pushes* its sessions up to GOG, so the
     cloud `time_sum` already includes Heroic-launched time. We take
     max(cloud, local) — summing would double-count.
  2. Achievements ARE set (GOG exposes them; Epic's API is closed). Expect this
     sparse until games run through GOG's achievement service (Comet).
  3. The cloud is a PER-GAME fan-out (one request per owned game for playtime,
     one per played game for achievements) — GOG has no aggregate endpoint like
     Epic's. --no-cloud stays the fast, no-network path.

The YAML is edited as raw text — no YAML dependency, matching sync-epic.py /
sync-steam.py / add-book.py. Standard library only.

Auth: no separate login. The script reads the GOG refresh token Heroic already
stored (gog_store/auth.json) and refreshes it via GOG's public "Galaxy" OAuth
client (a well-known constant, not a secret). If that token is stale, open Heroic
once to re-auth, then rerun — or pass --no-cloud to use only the Heroic-local data.
A manual token can be supplied via GOG_REFRESH_TOKEN / GOG_USER_ID (env or a
gitignored .env file).

Usage:
    python3 scripts/sync-gog.py --no-cloud --dry-run   # Heroic-local only, preview
    python3 scripts/sync-gog.py --dry-run              # + GOG cloud playtime/achv, preview
    python3 scripts/sync-gog.py                        # write the file
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

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DATA = REPO / "data" / "gaming.yaml"
DEFAULT_COVERS = REPO / "assets" / "images" / "games" / "covers"
COVER_REF_PREFIX = "images/games/covers"

USER_AGENT = "lna-dev.net gaming-sync (github.com/lna-dev; contact via site)"
# Galaxy-ish User-Agent for GOG's private endpoints, to look like the real client.
GOG_USER_AGENT = "GOGGalaxyClient/2.0.51.61 (GOG Galaxy)"

# GOG's public "Galaxy" OAuth client — a well-known constant used by gogdl,
# wyvern, Playnite, etc., NOT a per-user secret. Same values gogdl ships.
GOG_CLIENT_ID = "46899977096215655"
GOG_CLIENT_SECRET = "9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9"
# GOG's token endpoint is a GET with query params (unusual, but that's how gogdl
# and Galaxy do it — see heroic-gogdl gogdl/auth.py).
GOG_TOKEN_URL = "https://auth.gog.com/token"
# Per-game cloud endpoints (gameplay.gog.com). {app} is the numeric GOG product
# id (== library app_name); {uid} is the account user_id.
GOG_SESSIONS_URL = "https://gameplay.gog.com/games/{app}/users/{uid}/sessions"
GOG_ACHIEVEMENTS_URL = "https://gameplay.gog.com/clients/{app}/users/{uid}/achievements"

# Heroic config roots to try, in order (Flatpak install first, then native).
HEROIC_CONFIG_CANDIDATES = [
    Path.home() / ".var/app/com.heroicgameslauncher.hgl/config/heroic",
    Path.home() / ".config/heroic",
]

# Sentinel marking the start of the auto-managed GOG block. Any line exactly
# equal to this is stripped on every run and re-emitted once (mirrors sync-epic).
GOG_MARKER = "# ==== GOG: auto-managed by scripts/sync-gog.py (regenerated each sync) ===="

# Human-owned fields on a GOG entry that must survive a resync.
HUMAN_FIELDS = ("rating", "genres", "tags", "notes")

# GOG library rows that are not real games (redistributables / DLC roots).
SKIP_APP_NAMES = {"gog-redist"}


# --------------------------------------------------------------------------- #
# .env loading (stdlib only — copied from sync-epic.py)                         #
# --------------------------------------------------------------------------- #
def load_dotenv(path, *, override=False):
    """Load KEY=VALUE pairs from a .env file into os.environ."""
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
# HTTP + YAML text helpers (mirrors sync-epic.py)                              #
# --------------------------------------------------------------------------- #
def http_request(url, *, method="GET", headers=None, data=None, accept_json=False):
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
    return json.loads(body) if accept_json else body


def yaml_quote(value):
    """Quote a scalar for YAML when it contains risky characters."""
    if value is None:
        return '""'
    text = str(value)
    if text == "" or re.search(r'[:#\'"\[\]{}&*!|>%@`,]', text) or text != text.strip():
        return '"' + text.replace('"', '\\"') + '"'
    return text


def safe_filename(title):
    # Match add-book.py / sync-steam.py: only strip path separators + whitespace.
    return title.replace("/", "-").strip()


def split_entries(lines):
    """Split YAML lines into (preamble, chunks). A chunk starts at each top-level
    list item (`- ` at column 0) and runs to just before the next. Trailing blank
    lines are stripped so spacing normalises to one blank line (idempotent)."""
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


# --------------------------------------------------------------------------- #
# Source resolution                                                            #
# --------------------------------------------------------------------------- #
def resolve_heroic_config(explicit):
    """Return the Heroic config dir that holds the GOG library cache, or None."""
    candidates = [Path(explicit)] if explicit else HEROIC_CONFIG_CANDIDATES
    for cand in candidates:
        if (cand / "store_cache" / "gog_library.json").exists():
            return cand
    return None


# --------------------------------------------------------------------------- #
# Collector 1: Heroic-local (no auth)                                          #
# --------------------------------------------------------------------------- #
def _save_date(raw):
    """Convert a GOG cloud-save unix timestamp (seconds, possibly fractional, as a
    str or number) to a 'YYYY-MM-DD' UTC date string, or None if unparseable. UTC
    to match the sliced 'Z' timestamps in store/timestamp.json."""
    try:
        ts = float(raw)
    except (TypeError, ValueError):
        return None
    if ts <= 0:
        return None
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def collect_heroic(heroic_dir):
    """Return {app_name: {title, cover_url, minutes, lastPlayed}} for the owned GOG
    library (real games only), overlaid with Heroic-launched playtime."""
    games = {}
    lib_path = heroic_dir / "store_cache" / "gog_library.json"
    library = json.loads(lib_path.read_text(encoding="utf-8")).get("games", [])
    for g in library:
        app = g.get("app_name")
        if not app or app in SKIP_APP_NAMES:
            continue
        if (g.get("install") or {}).get("is_dlc"):
            continue
        games[app] = {
            "app_name": app,
            "title": g.get("title") or app,
            "cover_url": g.get("art_square") or g.get("art_cover"),
            "minutes": 0,
            "lastPlayed": None,
        }
    # Overlay Heroic-launched playtime. timestamp.json is keyed by app id across
    # ALL runners (Epic/GOG/Amazon); the `app in games` guard keeps only GOG.
    ts_path = heroic_dir / "store" / "timestamp.json"
    if ts_path.exists():
        for app, info in json.loads(ts_path.read_text(encoding="utf-8")).items():
            if app in games:
                games[app]["minutes"] = int(info.get("totalPlayed") or 0)  # already minutes
                last = (info.get("lastPlayed") or "")[:10]
                if last:
                    games[app]["lastPlayed"] = last
    # lastPlayed fallback. Heroic often records playtime for a game but leaves
    # `lastPlayed` empty (typically when the total was reconciled from GOG's cloud,
    # which carries no date — and GOG's playtime API exposes no dates either). Use
    # the GOG cloud-save sync time as a proxy: it flushes on exit, so it lands
    # within seconds of the real last-played time. Only fills games still missing a
    # date, and only reaches games that use GOG cloud saves.
    saves_path = heroic_dir / "gog_store" / "saveTimestamps.json"
    if saves_path.exists():
        try:
            saves = json.loads(saves_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saves = {}
        for app, info in saves.items():
            g = games.get(app)
            if not g or g["lastPlayed"]:
                continue
            date = _save_date((info or {}).get("saves"))
            if date:
                g["lastPlayed"] = date
    return games


# --------------------------------------------------------------------------- #
# Collector 2: GOG cloud (reuses Heroic's stored token)                        #
# --------------------------------------------------------------------------- #
def read_gog_token(auth_json_path):
    """Return (refresh_token, user_id) from Heroic's gog_store/auth.json, keyed by
    the Galaxy client id."""
    data = json.loads(Path(auth_json_path).read_text(encoding="utf-8"))
    creds = data.get(GOG_CLIENT_ID) or {}
    return creds.get("refresh_token"), creds.get("user_id")


def refresh_gog_token(refresh_token):
    """Exchange a refresh token for fresh credentials. GOG's token endpoint is a
    GET with query params (see gogdl/auth.py)."""
    query = urllib.parse.urlencode({
        "client_id": GOG_CLIENT_ID,
        "client_secret": GOG_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    })
    return http_request(f"{GOG_TOKEN_URL}?{query}",
                        headers={"User-Agent": GOG_USER_AGENT}, accept_json=True)


def _gameplay_get(url, access_token):
    """GET a gameplay.gog.com endpoint, returning parsed JSON or None on 404/empty
    (a game with no sessions/achievements) — anything else re-raises."""
    try:
        return http_request(url, headers={
            "Authorization": "Bearer " + access_token,
            "User-Agent": GOG_USER_AGENT,
        }, accept_json=True)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404):
            return None
        raise


def collect_cloud(auth_json_path, app_names, *, want_achievements,
                  refresh_token=None, user_id=None):
    """Return {app_name: {"minutes": int, "ach_unlocked": int|None,
    "ach_total": int|None}} from GOG's cloud, or {} on auth failure (so the run
    degrades to Heroic-local). Playtime is fetched for every app; achievements
    only for apps flagged in `want_achievements` (played games)."""
    if not refresh_token:
        try:
            refresh_token, user_id = read_gog_token(auth_json_path)
        except OSError:
            print(f"  cloud: no GOG token at {auth_json_path}; skipping cloud "
                  "(is Heroic logged into GOG?).", file=sys.stderr)
            return {}
        except (ValueError, KeyError) as exc:
            print(f"  cloud: could not parse GOG token ({exc}); skipping.", file=sys.stderr)
            return {}
    if not refresh_token:
        print("  cloud: token file has no refresh_token; skipping cloud data.",
              file=sys.stderr)
        return {}

    try:
        tok = refresh_gog_token(refresh_token)
    except urllib.error.HTTPError as exc:
        print(f"  cloud: token refresh failed ({exc.code} {exc.reason}). The stored GOG "
              "session is likely stale — open Heroic once to re-auth, then rerun "
              "(or use --no-cloud).", file=sys.stderr)
        return {}
    except Exception as exc:  # noqa: BLE001 - network/transient => degrade gracefully
        print(f"  cloud: token refresh error ({exc}); skipping cloud data.", file=sys.stderr)
        return {}

    access_token = tok.get("access_token")
    user_id = tok.get("user_id") or user_id
    if not access_token or not user_id:
        print("  cloud: refresh response missing access_token/user_id; skipping.",
              file=sys.stderr)
        return {}

    out = {}
    total = len(app_names)
    for i, app in enumerate(sorted(app_names), 1):
        rec = {"minutes": 0, "ach_unlocked": None, "ach_total": None}
        try:
            sess = _gameplay_get(GOG_SESSIONS_URL.format(app=app, uid=user_id), access_token)
            if sess:
                rec["minutes"] = int(sess.get("time_sum") or 0)
        except Exception as exc:  # noqa: BLE001 - per-game degrade
            print(f"  cloud: playtime fetch failed for {app} ({exc}); using local.",
                  file=sys.stderr)
        if want_achievements and app in want_achievements:
            try:
                ach = _gameplay_get(GOG_ACHIEVEMENTS_URL.format(app=app, uid=user_id),
                                    access_token)
                items = (ach or {}).get("items") or []
                if items:
                    rec["ach_total"] = len(items)
                    rec["ach_unlocked"] = sum(1 for a in items if a.get("date_unlocked"))
            except Exception as exc:  # noqa: BLE001 - per-game degrade
                print(f"  cloud: achievements fetch failed for {app} ({exc}); skipping.",
                      file=sys.stderr)
        out[app] = rec
        if i % 25 == 0 or i == total:
            print(f"  cloud: {i}/{total} games queried…", file=sys.stderr)
    return out


# --------------------------------------------------------------------------- #
# Covers (copied from sync-epic.py)                                             #
# --------------------------------------------------------------------------- #
def _image_ext(data):
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ".jpg"


def _existing_cover(covers_dir, title):
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = covers_dir / (safe_filename(title) + ext)
        if p.exists():
            return f"{COVER_REF_PREFIX}/{p.name}"
    return None


def download_cover(url, title, covers_dir):
    """Download a portrait cover to <covers>/<title>.<ext>, named after the game.
    Skips the download when a cover already exists. Returns the repo ref or None."""
    existing = _existing_cover(covers_dir, title)
    if existing:
        return existing
    if not url:
        return None
    try:
        data = http_request(url)
    except Exception:  # noqa: BLE001 - no cover is fine
        return None
    if len(data) < 2000:  # tiny/empty blob => no real image
        return None
    fname = safe_filename(title) + _image_ext(data)
    dest = covers_dir / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return f"{COVER_REF_PREFIX}/{fname}"


# --------------------------------------------------------------------------- #
# Merge + fetch orchestration                                                  #
# --------------------------------------------------------------------------- #
def build_games(heroic_dir, auth_json, covers_dir, *, include_unplayed, do_cloud,
                do_achievements, do_covers, refresh_token=None, user_id=None):
    heroic = collect_heroic(heroic_dir)
    print(f"Heroic library: {len(heroic)} owned GOG games (real, non-DLC).", file=sys.stderr)

    cloud = {}
    if do_cloud:
        # Achievements only for games we already know are played (local playtime),
        # to keep the per-game fan-out reasonable.
        played_local = {a for a, g in heroic.items() if g["minutes"] > 0}
        cloud = collect_cloud(
            auth_json, set(heroic),
            want_achievements=played_local if do_achievements else set(),
            refresh_token=refresh_token, user_id=user_id,
        )
        n_pt = sum(1 for r in cloud.values() if r["minutes"] > 0)
        n_ach = sum(1 for r in cloud.values() if r["ach_total"])
        print(f"GOG cloud: {n_pt} games with playtime, {n_ach} with achievements.",
              file=sys.stderr)

    games = []
    for app, g in heroic.items():
        c = cloud.get(app, {})
        # PREFER-CLOUD, not summed: cloud time_sum already contains Heroic sessions.
        minutes = max(int(c.get("minutes") or 0), g["minutes"])
        if minutes <= 0 and not include_unplayed:
            continue
        game = {
            "app_name": app,
            "title": g["title"],
            "playtimeMinutes": minutes,
            "lastPlayed": g["lastPlayed"],  # cloud carries no lastPlayed
            "ach_unlocked": c.get("ach_unlocked"),
            "ach_total": c.get("ach_total"),
        }
        game["cover"] = download_cover(g["cover_url"], g["title"], covers_dir) if do_covers else None
        games.append(game)

    print(f"Kept {len(games)} GOG games "
          f"({'incl.' if include_unplayed else 'excl.'} unplayed).", file=sys.stderr)
    return games


# --------------------------------------------------------------------------- #
# Raw-text YAML rebuild (no YAML dependency)                                    #
# --------------------------------------------------------------------------- #
def build_gog_entry(game, human_lines):
    """Render one `platform: gog` YAML entry from merged game metadata."""
    lines = [
        f"- title: {yaml_quote(game['title'])}",
        "  platform: gog",
        f"  appName: {yaml_quote(game['app_name'])}",
        f"  playtimeMinutes: {game['playtimeMinutes']}",
    ]
    if game.get("lastPlayed"):
        lines.append(f'  lastPlayed: "{game["lastPlayed"]}"')
    if game.get("ach_total"):
        lines.append(f"  achievementsUnlocked: {game.get('ach_unlocked') or 0}")
        lines.append(f"  achievementsTotal: {game['ach_total']}")
    if game.get("cover"):
        lines.append(f"  cover: {yaml_quote(game['cover'])}")
    lines.extend(human_lines)  # already 2-space indented, verbatim
    return "\n".join(lines)


def rebuild(raw, games):
    """Pure reconcile: given the current file text and merged GOG `games`, return
    (new_text, summary). No network, no filesystem. Non-gog entries (hand-added
    rows AND the Steam/Epic blocks) are preserved verbatim; gog entries are
    regenerated (add new / prune de-listed) and written last, keyed by appName."""
    trailing_newline = raw.endswith("\n") or raw == ""
    lines = raw.split("\n")
    if raw.endswith("\n"):
        lines = lines[:-1]
    # Drop any previously-emitted marker so it never accumulates.
    lines = [ln for ln in lines if ln != GOG_MARKER]

    preamble, chunks = split_entries(lines)

    non_gog, old_human, old_keys = [], {}, set()
    for chunk in chunks:
        is_gog = (chunk_field(chunk, "platform") or "").lower() == "gog"
        key = chunk_field(chunk, "appName") if is_gog else None
        if is_gog and key:
            old_keys.add(key)
            old_human[key] = chunk_human_lines(chunk)
        else:
            # Non-gog, or a hand-added gog row without an appName — preserve it.
            non_gog.append(chunk)

    # Stable order (by app_name) => clean, idempotent diffs.
    games = sorted(games, key=lambda g: g["app_name"].lower())
    new_keys = {g["app_name"] for g in games}

    gog_blocks = [
        build_gog_entry(g, old_human.get(g["app_name"], []))
        for g in games
    ]

    sections = []
    if preamble:
        sections.append("\n".join(preamble))
    for chunk in non_gog:
        sections.append("\n".join(chunk))
    if gog_blocks:
        sections.append(GOG_MARKER + "\n\n" + "\n\n".join(gog_blocks))

    out = "\n\n".join(sections)
    if trailing_newline and not out.endswith("\n"):
        out += "\n"

    summary = {
        "added": sorted(new_keys - old_keys),
        "pruned": sorted(old_keys - new_keys),
        "updated": sorted(new_keys & old_keys),
        "manual": len(non_gog),
    }
    return out, summary


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description="Sync GOG games into data/gaming.yaml.")
    parser.add_argument("--heroic-config", type=Path, default=None,
                        help="Heroic config dir (default: auto-detect Flatpak, then ~/.config/heroic).")
    parser.add_argument("--auth-json", type=Path, default=None,
                        help="Path to Heroic's gog_store/auth.json (GOG token). "
                             "Default: gog_store/auth.json under the Heroic config.")
    parser.add_argument("--no-cloud", action="store_true",
                        help="Skip GOG cloud; use only Heroic-local data (no token needed).")
    parser.add_argument("--no-achievements", action="store_true",
                        help="Fetch cloud playtime but skip per-game achievements.")
    parser.add_argument("--no-covers", action="store_true", help="Skip cover downloads.")
    parser.add_argument("--include-unplayed", action="store_true",
                        help="Include games with 0 total playtime (default: played only).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report add/update/prune counts without writing the file.")
    parser.add_argument("--env-file", type=Path, action="append", default=None,
                        help="Load GOG_REFRESH_TOKEN / GOG_USER_ID from this file "
                             "(repeatable). Default: .env in the repo root and the cwd.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--covers", type=Path, default=DEFAULT_COVERS)
    args = parser.parse_args(argv)

    # Load .env before resolving optional manual credentials (real env wins).
    env_files = args.env_file or [REPO / ".env", Path(".env")]
    for env_path in env_files:
        loaded = load_dotenv(env_path)
        if loaded:
            print(f"Loaded {', '.join(loaded)} from {env_path}", file=sys.stderr)

    heroic_dir = resolve_heroic_config(args.heroic_config)
    if heroic_dir is None:
        print("! Could not find a Heroic config with store_cache/gog_library.json. "
              "Is Heroic installed and logged into GOG? Point at it with --heroic-config.",
              file=sys.stderr)
        return 2
    print(f"Heroic config: {heroic_dir}", file=sys.stderr)

    auth_json = args.auth_json or (heroic_dir / "gog_store" / "auth.json")

    games = build_games(
        heroic_dir, auth_json, args.covers,
        include_unplayed=args.include_unplayed,
        do_cloud=not args.no_cloud,
        do_achievements=not args.no_achievements,
        do_covers=not args.no_covers,
        refresh_token=os.environ.get("GOG_REFRESH_TOKEN"),
        user_id=os.environ.get("GOG_USER_ID"),
    )

    raw = args.data.read_text(encoding="utf-8") if args.data.exists() else ""
    new_text, summary = rebuild(raw, games)

    print(f"\nReconcile: +{len(summary['added'])} added, "
          f"~{len(summary['updated'])} updated, "
          f"-{len(summary['pruned'])} pruned; "
          f"{summary['manual']} non-GOG/manual entries untouched.", file=sys.stderr)
    if summary["pruned"]:
        print("  pruned: " + ", ".join(summary["pruned"]), file=sys.stderr)

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
