#!/usr/bin/env python3
"""Sync Epic Games into data/gaming.yaml.

data/gaming.yaml is a flat list of games written by MULTIPLE sources (see the
header comment in that file). This script owns exactly one slice of it: the
entries with `platform: epic`. On every run it:

  * Reads the Epic library + local playtime that Heroic already cached on disk
    (no login — Heroic did the auth). Two files under the Heroic config dir:
      - store_cache/legendary_library.json  -> owned games (title, cover, link)
      - store/timestamp.json                -> playtime for games launched via
                                               Heroic (minutes), keyed by app_name
  * Optionally reaches Epic's cloud for the *historical* playtime recorded by the
    official Epic launcher (the part Heroic never sees). It reuses the OAuth
    refresh token Heroic stored (legendaryConfig/legendary/user.json), refreshes
    it, and reads library-service's per-account playtime endpoint.
  * MERGES the two: a play session is launched by exactly one client, so the two
    sources are disjoint and the true total is `heroic + cloud` (matched on the
    Epic app_name). It then rebuilds the `platform: epic` entries (played games
    added, others pruned) and writes them as the LAST block in the file, below a
    marker it emits.

Everything that is NOT `platform: epic` is left byte-for-byte untouched, so
hand-added games and the Steam block (platform: steam) are safe. Human-owned
fields on an Epic entry (rating, genres, tags, notes) are preserved across syncs:
they are read back out of the old entry and re-emitted verbatim, keyed by
`appName`. (Keep those human fields to a single line each.)

Achievements are intentionally omitted — Epic closed the achievement-progress API
in Jan 2025 and nothing usable is available (see the plan / AGENTS.md).

The YAML is edited as raw text — no YAML dependency, matching sync-steam.py /
add-book.py. Standard library only.

Auth: no separate login. The script reads the Epic refresh token Heroic already
stored and refreshes it via Epic's public "launcher" OAuth client (a well-known
constant, not a secret). If that token is stale (last Heroic session was a while
ago), open Heroic once to re-auth, then rerun — or pass --no-cloud to use only
the Heroic-local data. A manual token can be supplied via EPIC_REFRESH_TOKEN /
EPIC_ACCOUNT_ID (env or a gitignored .env file).

Usage:
    python3 scripts/sync-epic.py --no-cloud --dry-run   # Heroic-local only, preview
    python3 scripts/sync-epic.py --dry-run              # + Epic cloud history, preview
    python3 scripts/sync-epic.py                        # write the file
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DATA = REPO / "data" / "gaming.yaml"
DEFAULT_COVERS = REPO / "assets" / "images" / "games" / "covers"
COVER_REF_PREFIX = "images/games/covers"

USER_AGENT = "lna-dev.net gaming-sync (github.com/lna-dev; contact via site)"
# Launcher User-Agent for Epic's private endpoints (mirrors Legendary), to look
# like the real client and avoid tripping WAF heuristics.
EPIC_USER_AGENT = ("UELauncher/11.0.1-14907503+++Portal+Release-Live "
                   "Windows/10.0.19041.1.256.64bit")

# Epic's public "launcher" OAuth client — a well-known constant used by Legendary
# and Playnite, NOT a per-user secret. The Basic value is base64("<id>:<secret>")
# for 34a02cf8f4414e29b15921876da36f9a:daafbccc737745039dffe53d94fc76cf.
EPIC_OAUTH_TOKEN_URL = (
    "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token"
)
EPIC_BASIC_AUTH = "MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzZmOWE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc2Y2Y="
EPIC_PLAYTIME_URL = (
    "https://library-service.live.use1a.on.epicgames.com"
    "/library/api/public/playtime/account/{account_id}/all"
)

# Heroic config roots to try, in order (Flatpak install first, then native).
HEROIC_CONFIG_CANDIDATES = [
    Path.home() / ".var/app/com.heroicgameslauncher.hgl/config/heroic",
    Path.home() / ".config/heroic",
]

# Sentinel marking the start of the auto-managed Epic block. Any line exactly
# equal to this is stripped on every run and re-emitted once (mirrors sync-steam).
EPIC_MARKER = "# ==== EPIC: auto-managed by scripts/sync-epic.py (regenerated each sync) ===="

# Human-owned fields on an Epic entry that must survive a resync.
HUMAN_FIELDS = ("rating", "genres", "tags", "notes")


# --------------------------------------------------------------------------- #
# .env loading (stdlib only — copied from sync-steam.py)                        #
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
# HTTP + YAML text helpers (mirrors sync-steam.py)                             #
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
    """Return the Heroic config dir that holds the Epic library cache, or None."""
    candidates = [Path(explicit)] if explicit else HEROIC_CONFIG_CANDIDATES
    for cand in candidates:
        if (cand / "store_cache" / "legendary_library.json").exists():
            return cand
    return None


# --------------------------------------------------------------------------- #
# Collector 1: Heroic-local (no auth)                                          #
# --------------------------------------------------------------------------- #
def collect_heroic(heroic_dir):
    """Return {app_name: {title, cover_url, store_url, minutes, lastPlayed}} for
    the owned Epic library, overlaid with Heroic-launched playtime."""
    games = {}
    lib_path = heroic_dir / "store_cache" / "legendary_library.json"
    library = json.loads(lib_path.read_text(encoding="utf-8")).get("library", [])
    for g in library:
        app = g.get("app_name")
        if not app:
            continue
        games[app] = {
            "app_name": app,
            "title": g.get("title") or app,
            "cover_url": g.get("art_square") or g.get("art_cover"),
            "store_url": g.get("store_url") or "",
            "minutes": 0,
            "lastPlayed": None,
        }
    # Overlay Heroic-launched playtime. timestamp.json is keyed by app id across
    # ALL runners (Epic/GOG/Amazon); the `app in games` guard keeps only Epic.
    ts_path = heroic_dir / "store" / "timestamp.json"
    if ts_path.exists():
        for app, info in json.loads(ts_path.read_text(encoding="utf-8")).items():
            if app in games:
                games[app]["minutes"] += int(info.get("totalPlayed") or 0)  # already minutes
                last = (info.get("lastPlayed") or "")[:10]
                if last:
                    games[app]["lastPlayed"] = last
    return games


# --------------------------------------------------------------------------- #
# Collector 2: Epic cloud playtime (reuses Heroic's stored token)             #
# --------------------------------------------------------------------------- #
def read_epic_token(user_json_path):
    data = json.loads(Path(user_json_path).read_text(encoding="utf-8"))
    return data.get("refresh_token"), data.get("account_id")


def refresh_epic_token(refresh_token):
    """Exchange a refresh token for a fresh access token via Epic's OAuth."""
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "token_type": "eg1",
    }).encode()
    headers = {
        "Authorization": "basic " + EPIC_BASIC_AUTH,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": EPIC_USER_AGENT,
    }
    return http_request(EPIC_OAUTH_TOKEN_URL, method="POST",
                        headers=headers, data=body, accept_json=True)


def collect_cloud(user_json_path, refresh_token=None, account_id=None):
    """Return {app_name: minutes} of historical (official-launcher) playtime from
    Epic's cloud, or {} on any failure (so the run degrades to Heroic-local)."""
    if not refresh_token:
        try:
            refresh_token, account_id = read_epic_token(user_json_path)
        except OSError:
            print(f"  cloud: no Epic token at {user_json_path}; skipping cloud playtime "
                  "(is Heroic logged into Epic?).", file=sys.stderr)
            return {}
        except (ValueError, KeyError) as exc:
            print(f"  cloud: could not parse Epic token ({exc}); skipping.", file=sys.stderr)
            return {}
    if not refresh_token:
        print("  cloud: token file has no refresh_token; skipping cloud playtime.",
              file=sys.stderr)
        return {}

    try:
        tok = refresh_epic_token(refresh_token)
    except urllib.error.HTTPError as exc:
        print(f"  cloud: token refresh failed ({exc.code} {exc.reason}). The stored Epic "
              "session is likely stale — open Heroic once to re-auth, then rerun "
              "(or use --no-cloud).", file=sys.stderr)
        return {}
    except Exception as exc:  # noqa: BLE001 - network/transient => degrade gracefully
        print(f"  cloud: token refresh error ({exc}); skipping cloud playtime.", file=sys.stderr)
        return {}

    access_token = tok.get("access_token")
    account_id = tok.get("account_id") or account_id
    if not access_token or not account_id:
        print("  cloud: refresh response missing access_token/account_id; skipping.",
              file=sys.stderr)
        return {}

    url = EPIC_PLAYTIME_URL.format(account_id=urllib.parse.quote(str(account_id)))
    headers = {"Authorization": "bearer " + access_token, "User-Agent": EPIC_USER_AGENT}
    try:
        items = http_request(url, headers=headers, accept_json=True)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        print(f"  cloud: playtime fetch failed ({exc}); skipping cloud playtime.", file=sys.stderr)
        return {}

    out = {}
    for it in items or []:
        app = it.get("artifactId")  # == Epic app_name
        if app:
            out[app] = out.get(app, 0) + round((it.get("totalTime") or 0) / 60)  # sec -> min
    return out


# --------------------------------------------------------------------------- #
# Covers                                                                        #
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
    """Download a portrait cover to <covers>/<title>.<ext>, named after the game
    (like the book/Steam covers). Skips the download when a cover already exists.
    Detects the real image format so Hugo can process it. Returns the repo ref
    (or None)."""
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
def merge_games(heroic, cloud):
    """Merge Heroic-local games with cloud playtime (both keyed by app_name).
    The two sources are disjoint, so playtime sums. Cloud-only records with no
    library entry (delisted) are dropped — we can't render them without a title."""
    merged = []
    for app, g in heroic.items():
        merged.append({
            "app_name": app,
            "title": g["title"],
            "playtimeMinutes": g["minutes"] + cloud.get(app, 0),
            "lastPlayed": g["lastPlayed"],  # cloud carries no lastPlayed
            "cover_url": g["cover_url"],
            "store_url": g["store_url"],
        })
    orphan = sorted(set(cloud) - set(heroic))
    if orphan:
        print(f"  note: {len(orphan)} cloud playtime record(s) have no library entry "
              "(delisted/removed) — skipped.", file=sys.stderr)
    return merged


def build_games(heroic_dir, user_json, covers_dir, *, include_unplayed, do_cloud,
                do_covers, refresh_token=None, account_id=None):
    heroic = collect_heroic(heroic_dir)
    print(f"Heroic library: {len(heroic)} owned Epic games.", file=sys.stderr)
    cloud = {}
    if do_cloud:
        cloud = collect_cloud(user_json, refresh_token=refresh_token, account_id=account_id)
        print(f"Epic cloud: {len(cloud)} games with recorded playtime.", file=sys.stderr)

    merged = merge_games(heroic, cloud)
    games = []
    for g in merged:
        if g["playtimeMinutes"] <= 0 and not include_unplayed:
            continue
        g["cover"] = download_cover(g["cover_url"], g["title"], covers_dir) if do_covers else None
        games.append(g)
    print(f"Kept {len(games)} played Epic games "
          f"({'incl.' if include_unplayed else 'excl.'} unplayed).", file=sys.stderr)
    return games


# --------------------------------------------------------------------------- #
# Raw-text YAML rebuild (no YAML dependency)                                    #
# --------------------------------------------------------------------------- #
def build_epic_entry(game, human_lines):
    """Render one `platform: epic` YAML entry from merged game metadata."""
    lines = [
        f"- title: {yaml_quote(game['title'])}",
        "  platform: epic",
        f"  appName: {yaml_quote(game['app_name'])}",
        f"  playtimeMinutes: {game['playtimeMinutes']}",
    ]
    if game.get("lastPlayed"):
        lines.append(f'  lastPlayed: "{game["lastPlayed"]}"')
    if game.get("cover"):
        lines.append(f"  cover: {yaml_quote(game['cover'])}")
    if game.get("store_url"):
        lines.append(f"  link: {yaml_quote(game['store_url'])}")
    lines.extend(human_lines)  # already 2-space indented, verbatim
    return "\n".join(lines)


def rebuild(raw, games):
    """Pure reconcile: given the current file text and merged Epic `games`, return
    (new_text, summary). No network, no filesystem. Non-epic entries (hand-added
    rows AND the Steam block) are preserved verbatim; epic entries are regenerated
    (add new / prune de-listed) and written last, keyed by appName."""
    trailing_newline = raw.endswith("\n") or raw == ""
    lines = raw.split("\n")
    if raw.endswith("\n"):
        lines = lines[:-1]
    # Drop any previously-emitted marker so it never accumulates.
    lines = [ln for ln in lines if ln != EPIC_MARKER]

    preamble, chunks = split_entries(lines)

    non_epic, old_human, old_keys = [], {}, set()
    for chunk in chunks:
        is_epic = (chunk_field(chunk, "platform") or "").lower() == "epic"
        key = chunk_field(chunk, "appName") if is_epic else None
        if is_epic and key:
            old_keys.add(key)
            old_human[key] = chunk_human_lines(chunk)
        else:
            # Non-epic, or a hand-added epic row without an appName — preserve it.
            non_epic.append(chunk)

    # Stable order (by app_name) => clean, idempotent diffs.
    games = sorted(games, key=lambda g: g["app_name"].lower())
    new_keys = {g["app_name"] for g in games}

    epic_blocks = [
        build_epic_entry(g, old_human.get(g["app_name"], []))
        for g in games
    ]

    sections = []
    if preamble:
        sections.append("\n".join(preamble))
    for chunk in non_epic:
        sections.append("\n".join(chunk))
    if epic_blocks:
        sections.append(EPIC_MARKER + "\n\n" + "\n\n".join(epic_blocks))

    out = "\n\n".join(sections)
    if trailing_newline and not out.endswith("\n"):
        out += "\n"

    summary = {
        "added": sorted(new_keys - old_keys),
        "pruned": sorted(old_keys - new_keys),
        "updated": sorted(new_keys & old_keys),
        "manual": len(non_epic),
    }
    return out, summary


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description="Sync Epic games into data/gaming.yaml.")
    parser.add_argument("--heroic-config", type=Path, default=None,
                        help="Heroic config dir (default: auto-detect Flatpak, then ~/.config/heroic).")
    parser.add_argument("--user-json", type=Path, default=None,
                        help="Path to legendary user.json (Epic token). "
                             "Default: legendaryConfig/legendary/user.json under the Heroic config.")
    parser.add_argument("--no-cloud", action="store_true",
                        help="Skip Epic cloud playtime; use only Heroic-local data (no token needed).")
    parser.add_argument("--no-covers", action="store_true", help="Skip cover downloads.")
    parser.add_argument("--include-unplayed", action="store_true",
                        help="Include games with 0 total playtime (default: played only).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report add/update/prune counts without writing the file.")
    parser.add_argument("--env-file", type=Path, action="append", default=None,
                        help="Load EPIC_REFRESH_TOKEN / EPIC_ACCOUNT_ID from this file "
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
        print("! Could not find a Heroic config with store_cache/legendary_library.json. "
              "Is Heroic installed and logged into Epic? Point at it with --heroic-config.",
              file=sys.stderr)
        return 2
    print(f"Heroic config: {heroic_dir}", file=sys.stderr)

    user_json = args.user_json or (heroic_dir / "legendaryConfig" / "legendary" / "user.json")

    games = build_games(
        heroic_dir, user_json, args.covers,
        include_unplayed=args.include_unplayed,
        do_cloud=not args.no_cloud,
        do_covers=not args.no_covers,
        refresh_token=os.environ.get("EPIC_REFRESH_TOKEN"),
        account_id=os.environ.get("EPIC_ACCOUNT_ID"),
    )

    raw = args.data.read_text(encoding="utf-8") if args.data.exists() else ""
    new_text, summary = rebuild(raw, games)

    print(f"\nReconcile: +{len(summary['added'])} added, "
          f"~{len(summary['updated'])} updated, "
          f"-{len(summary['pruned'])} pruned; "
          f"{summary['manual']} non-Epic/manual entries untouched.", file=sys.stderr)
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
