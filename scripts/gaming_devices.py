#!/usr/bin/env python3
"""Per-device snapshots of Heroic's local game data, for the Epic and GOG syncs.

Heroic records some things only on the machine that ran the game: every Epic
session (Heroic never uploads Epic playtime), and every `lastPlayed` date for
Epic and GOG (neither cloud endpoint carries one). While the syncs read that
straight out of the local Heroic config dir, whichever machine ran the sync
last was the only one whose Heroic data was in data/gaming.yaml.

So each machine keeps a snapshot of its own local data in
sources/gaming-devices/<device>.json, and the syncs merge all of them:

  * one file per device, written only by that device — a run never writes
    another device's file, so the syncs can run on any machine without
    overwriting the others;
  * the file holds the device's FULL current state (Heroic's totals are already
    cumulative) and is replaced on every run — never deltas, so exporting twice
    changes nothing and a device that has not run for a while only delays its
    numbers;
  * an allowlist of fields (title, minutes, lastPlayed as a date, cover, link) —
    no tokens, paths, host names or clock times: the repository is public.
    Token files are never even opened.

The device id is GAMING_DEVICE in the machine's .env (or --device). There is no
default and no host-name fallback. A machine whose Heroic has played games but
no id is an error rather than silently contributing nothing.

The export refuses to write a snapshot in which a game lost minutes or
disappeared: that is Heroic reinstalled, and writing it would take the device's
playtime off the site. `export --rotate` freezes the old file as
<device>-until-<date>.json (still merged) and starts a fresh one; `export
--force` overwrites anyway.

This script writes files and nothing else. Pulling, committing and pushing stay
manual. Design: docs/concepts/gaming-devices.md. Standard library only.

Usage:
    python3 scripts/gaming_devices.py status            # one line per device
    python3 scripts/gaming_devices.py check             # what sync-games.sh runs first; writes nothing
    python3 scripts/gaming_devices.py export --dry-run  # would this device's snapshot change?
    python3 scripts/gaming_devices.py export            # write it (the syncs also do this)
    python3 scripts/gaming_devices.py export --rotate   # after a Heroic reinstall
    python3 scripts/gaming_devices.py export --force    # accept a shrink without rotating
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DEVICES_DIR = REPO / "sources" / "gaming-devices"

# Heroic config roots to try, in order (Flatpak install first, then native) —
# the same list the syncs use.
HEROIC_CONFIG_CANDIDATES = [
    Path.home() / ".var/app/com.heroicgameslauncher.hgl/config/heroic",
    Path.home() / ".config/heroic",
]

# The stores whose Heroic-local data a snapshot carries, and the library cache
# Heroic keeps for each (under <heroic>/store_cache/).
STORES = ("epic", "gog")
LIBRARY_FILES = {"epic": "legendary_library.json", "gog": "gog_library.json"}

# GOG library rows that are not real games (redistributables / DLC roots).
GOG_SKIP_APP_NAMES = {"gog-redist"}

SCHEMA = 1
# The allowlist. Nothing else is ever written into a snapshot, and a snapshot
# carrying anything else is refused on read.
SNAPSHOT_FIELDS = ("device", "schema", "stores")
GAME_FIELDS = ("cover", "lastPlayed", "link", "minutes", "title")

DEVICE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# `<device>-until-<date>` is how --rotate names a frozen snapshot, so a live
# device id may not contain it.
ROTATED_INFIX = "-until-"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

NO_DEVICE_MESSAGE = (
    "this machine's Heroic has played games, but no device id is set. Add "
    "GAMING_DEVICE=<name> (e.g. pc, laptop) to the .env in the repo root, or pass "
    "--device. Without it, this machine's Heroic playtime would silently drop off "
    "the site. See docs/concepts/gaming-devices.md."
)


class DeviceError(Exception):
    """Something the user has to fix; the callers print it and exit non-zero."""


# --------------------------------------------------------------------------- #
# .env loading (stdlib only — copied from sync-steam.py)                        #
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
# Device id                                                                     #
# --------------------------------------------------------------------------- #
def resolve_device(explicit=None):
    """The device id from --device, else GAMING_DEVICE, else None. Validated."""
    device = (explicit or os.environ.get("GAMING_DEVICE") or "").strip() or None
    if device is not None:
        check_device(device)
    return device


def check_device(device):
    if not DEVICE_RE.match(device):
        raise DeviceError(f"device id {device!r} must be lowercase letters, digits "
                          "and single dashes (e.g. pc, laptop, steam-deck).")
    if ROTATED_INFIX in device:
        raise DeviceError(f"device id {device!r} contains {ROTATED_INFIX!r}, which is "
                          "reserved for snapshots frozen by --rotate.")


# --------------------------------------------------------------------------- #
# Reading Heroic (never the token files)                                        #
# --------------------------------------------------------------------------- #
def resolve_heroic_config(explicit=None):
    """Return the Heroic config dir that holds a store library cache, or None."""
    candidates = [Path(explicit)] if explicit else HEROIC_CONFIG_CANDIDATES
    for cand in candidates:
        if any((cand / "store_cache" / name).exists() for name in LIBRARY_FILES.values()):
            return cand
    return None


def read_library(heroic_dir, store):
    """{app_name: {"title", "cover", "link"}} for one store's owned games, from
    the library cache Heroic keeps (`cover` / `link` may be None). Empty when the
    store is not set up in Heroic. GOG skips DLC and redistributables."""
    path = Path(heroic_dir) / "store_cache" / LIBRARY_FILES[store]
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("library", []) if store == "epic" else data.get("games", [])
    library = {}
    for g in rows:
        app = g.get("app_name")
        if not app:
            continue
        if store == "gog" and (app in GOG_SKIP_APP_NAMES
                               or (g.get("install") or {}).get("is_dlc")):
            continue
        library[app] = {
            "title": g.get("title") or app,
            "cover": g.get("art_square") or g.get("art_cover") or None,
            # GOG library rows carry no reliable store URL.
            "link": (g.get("store_url") or None) if store == "epic" else None,
        }
    return library


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


def read_local(heroic_dir):
    """This machine's played games, per store: {store: {app: record}}, where a
    record holds only GAME_FIELDS.

    Playtime and lastPlayed come from store/timestamp.json, which Heroic keys by
    app id across all its runners; matching against each store's library keeps
    Epic and GOG apart and leaves Amazon and sideloaded apps out. For GOG,
    Heroic often records playtime but no date (typically when it pulled the
    total down from GOG's cloud), so the GOG cloud-save sync time stands in for
    it — it flushes on exit, within seconds of the real last-played time. That
    fallback is a fact about this device, so it is resolved here.

    A game is in the snapshot when it has minutes or a date."""
    heroic_dir = Path(heroic_dir)
    ts_path = heroic_dir / "store" / "timestamp.json"
    played = json.loads(ts_path.read_text(encoding="utf-8")) if ts_path.exists() else {}
    try:
        saves = json.loads((heroic_dir / "gog_store" / "saveTimestamps.json")
                           .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saves = {}

    stores = {}
    for store in STORES:
        games = {}
        for app, lib in read_library(heroic_dir, store).items():
            info = played.get(app) or {}
            minutes = int(info.get("totalPlayed") or 0)  # already minutes
            last = (info.get("lastPlayed") or "")[:10] or None
            if store == "gog" and not last:
                last = _save_date((saves.get(app) or {}).get("saves"))
            if minutes <= 0 and not last:
                continue
            rec = {"minutes": minutes, "title": lib["title"]}
            if last:
                rec["lastPlayed"] = last
            if lib["cover"]:
                rec["cover"] = lib["cover"]
            if lib["link"]:
                rec["link"] = lib["link"]
            games[app] = rec
        stores[store] = games
    return stores


# --------------------------------------------------------------------------- #
# Snapshot files                                                               #
# --------------------------------------------------------------------------- #
def make_snapshot(device, stores):
    return {"schema": SCHEMA, "device": device,
            "stores": {store: dict(stores.get(store) or {}) for store in STORES}}


def dumps(snapshot):
    """Deterministic text: sorted keys, 2-space indent, trailing newline, and no
    export timestamp — a run with nothing new leaves the file byte-identical."""
    return json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def validate(snapshot, name):
    """Refuse a snapshot that is not exactly the allowlisted shape. `name` is the
    file stem, which must equal the `device` inside."""
    where = f"{name}.json"
    if not isinstance(snapshot, dict):
        raise DeviceError(f"{where}: not a JSON object.")
    extra = set(snapshot) - set(SNAPSHOT_FIELDS)
    if extra:
        raise DeviceError(f"{where}: unexpected key(s) {sorted(extra)}.")
    if snapshot.get("schema") != SCHEMA:
        raise DeviceError(f"{where}: schema {snapshot.get('schema')!r}, expected {SCHEMA}.")
    if snapshot.get("device") != name:
        raise DeviceError(f"{where}: device {snapshot.get('device')!r} does not match "
                          "the file name.")
    stores = snapshot.get("stores")
    if not isinstance(stores, dict) or set(stores) - set(STORES):
        raise DeviceError(f"{where}: `stores` must be an object with only {list(STORES)}.")
    for store, games in stores.items():
        if not isinstance(games, dict):
            raise DeviceError(f"{where}: stores.{store} must be an object.")
        for app, rec in games.items():
            at = f"{where}: {store} {app}"
            if not isinstance(rec, dict):
                raise DeviceError(f"{at}: not an object.")
            extra = set(rec) - set(GAME_FIELDS)
            if extra:
                raise DeviceError(f"{at}: unexpected key(s) {sorted(extra)}.")
            minutes = rec.get("minutes")
            if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 0:
                raise DeviceError(f"{at}: `minutes` must be a whole number >= 0.")
            if not isinstance(rec.get("title"), str) or not rec["title"]:
                raise DeviceError(f"{at}: `title` missing.")
            if "lastPlayed" in rec and not (isinstance(rec["lastPlayed"], str)
                                            and DATE_RE.match(rec["lastPlayed"])):
                raise DeviceError(f"{at}: `lastPlayed` must be YYYY-MM-DD.")
    return snapshot


def load_snapshot(path):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise DeviceError(f"{path.name}: not valid JSON ({exc}).") from exc
    return validate(data, path.stem)


def load_snapshots(devices_dir):
    """{device: snapshot} for every *.json in the directory, in device order
    (sorted by name, not by file name: `pc` before `pc-until-…`)."""
    devices_dir = Path(devices_dir)
    if not devices_dir.is_dir():
        return {}
    paths = sorted(devices_dir.glob("*.json"), key=lambda p: p.stem)
    return {p.stem: load_snapshot(p) for p in paths}


def shrinkage(old, new):
    """Readable lines for every game whose minutes went down, or that had minutes
    and vanished. A record that only carried a date may vanish — it cost no
    playtime."""
    lost = []
    for store in STORES:
        before = old["stores"].get(store, {})
        after = new["stores"].get(store, {})
        for app, rec in sorted(before.items()):
            now = after.get(app)
            if now is None and rec["minutes"] > 0:
                lost.append(f"{store} {rec['title']} ({app}): {rec['minutes']} min -> gone")
            elif now is not None and now["minutes"] < rec["minutes"]:
                lost.append(f"{store} {rec['title']} ({app}): "
                            f"{rec['minutes']} -> {now['minutes']} min")
    return lost


def export(device, heroic_dir, devices_dir, *, write, force=False):
    """Build this device's snapshot from its Heroic and — when `write` — store it
    as <devices_dir>/<device>.json, only if the text changed. Returns
    (snapshot, changed). Raises DeviceError instead of shrinking the stored
    snapshot, unless `force`."""
    check_device(device)
    snapshot = make_snapshot(device, read_local(heroic_dir))
    path = Path(devices_dir) / f"{device}.json"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    if old_text is not None and not force:
        lost = shrinkage(load_snapshot(path), snapshot)
        if lost:
            raise DeviceError(
                f"Heroic on this machine reports less than {path.name} already holds:\n    "
                + "\n    ".join(lost)
                + "\n  Nothing was written. If Heroic was reinstalled, freeze the old "
                  "snapshot and start a fresh one:\n"
                  "    python3 scripts/gaming_devices.py export --rotate\n"
                  "  If the decrease is genuinely correct: export --force.")
    text = dumps(snapshot)
    changed = text != old_text
    if write and changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return snapshot, changed


def rotate(devices_dir, device, today):
    """Freeze <device>.json as <device>-until-<today>.json — still merged, never
    written again — so a fresh <device>.json can start from zero."""
    check_device(device)
    devices_dir = Path(devices_dir)
    path = devices_dir / f"{device}.json"
    if not path.exists():
        raise DeviceError(f"{path.name} does not exist; nothing to rotate.")
    frozen = f"{device}{ROTATED_INFIX}{today}"
    target = devices_dir / f"{frozen}.json"
    if target.exists():
        raise DeviceError(f"{target.name} already exists.")
    snapshot = load_snapshot(path)
    snapshot["device"] = frozen
    target.write_text(dumps(snapshot), encoding="utf-8")
    path.unlink()
    return target


# --------------------------------------------------------------------------- #
# What the syncs call                                                          #
# --------------------------------------------------------------------------- #
def collect(heroic_dir, devices_dir, device, *, write):
    """Export this machine's snapshot (in memory only unless `write`) and return
    (snapshots, changed): every device's snapshot, this one's fresh, in device
    order. Without a device id this machine contributes nothing — allowed only
    while its Heroic has nothing played."""
    snapshots = load_snapshots(devices_dir)
    if device is None:
        if any(read_local(heroic_dir).values()):
            raise DeviceError(NO_DEVICE_MESSAGE)
        return snapshots, False
    snapshot, changed = export(device, heroic_dir, devices_dir, write=write)
    snapshots[device] = snapshot
    return dict(sorted(snapshots.items())), changed


def per_game(snapshots, store):
    """{app: [(device, record), ...]} for one store, in device order."""
    games = {}
    for device, snapshot in snapshots.items():
        for app, rec in snapshot["stores"].get(store, {}).items():
            games.setdefault(app, []).append((device, rec))
    return games


def newest(dates):
    """The latest of some 'YYYY-MM-DD' strings (None ignored), or None."""
    return max((d for d in dates if d), default=None)


def copied_config_suspects(snapshots, store):
    """[(app, [devices])] for games that two devices report with the same nonzero
    minutes AND the same lastPlayed — a coincidence for a real game, a copied
    Heroic config otherwise. Only meaningful for Epic, where devices are summed;
    GOG takes the max, and devices legitimately share the cloud total there."""
    seen = {}
    for device, snapshot in snapshots.items():
        for app, rec in snapshot["stores"].get(store, {}).items():
            if rec["minutes"] > 0 and rec.get("lastPlayed"):
                seen.setdefault((app, rec["minutes"], rec["lastPlayed"]), []).append(device)
    return sorted((key[0], devices) for key, devices in seen.items() if len(devices) > 1)


def describe(snapshots, device, changed, *, dry_run):
    """One stderr line for the syncs: which snapshot moved, which were merged."""
    if device is None:
        head = "no device id and nothing played in this Heroic"
    elif not changed:
        head = f"{device}.json unchanged"
    elif dry_run:
        head = f"{device}.json would be updated (dry-run: not written)"
    else:
        head = f"{device}.json updated"
    names = ", ".join(snapshots) or "none"
    return f"Device snapshot: {head}; merging {len(snapshots)} device(s): {names}."


# --------------------------------------------------------------------------- #
# status                                                                       #
# --------------------------------------------------------------------------- #
def status_lines(snapshots):
    """One line per device: Epic games, GOG games, local minutes, newest date."""
    rows = [("device", "epic", "gog", "minutes", "last played")]
    for device, snapshot in snapshots.items():
        stores = snapshot["stores"]
        recs = [rec for store in STORES for rec in stores.get(store, {}).values()]
        rows.append((device,
                     str(len(stores.get("epic", {}))),
                     str(len(stores.get("gog", {}))),
                     str(sum(rec["minutes"] for rec in recs)),
                     newest(rec.get("lastPlayed") for rec in recs) or "-"))
    width = max(len(r[0]) for r in rows)
    return [f"{r[0]:<{width}}  {r[1]:>4}  {r[2]:>4}  {r[3]:>7}  {r[4]}" for r in rows]


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--devices-dir", type=Path, default=DEFAULT_DEVICES_DIR,
                        help="Where the snapshots live (default: sources/gaming-devices/).")
    common.add_argument("--env-file", type=Path, action="append", default=None,
                        help="Load GAMING_DEVICE from this file (repeatable). "
                             "Default: .env in the repo root and the cwd.")
    local = argparse.ArgumentParser(add_help=False)
    local.add_argument("--device", default=None,
                       help="This machine's device id (default: GAMING_DEVICE).")
    local.add_argument("--heroic-config", type=Path, default=None,
                       help="Heroic config dir (default: auto-detect Flatpak, then ~/.config/heroic).")

    parser = argparse.ArgumentParser(
        description="Per-device Heroic snapshots for the Epic and GOG syncs.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", parents=[common], help="One line per device snapshot.")
    sub.add_parser("check", parents=[common, local],
                   help="Validate every snapshot and this machine's export; write nothing.")
    p_export = sub.add_parser("export", parents=[common, local],
                              help="Write this machine's snapshot.")
    p_export.add_argument("--dry-run", action="store_true",
                          help="Report whether the snapshot would change; write nothing.")
    mode = p_export.add_mutually_exclusive_group()
    mode.add_argument("--rotate", action="store_true",
                      help="Freeze the current snapshot as <device>-until-<today>.json "
                           "and start a fresh one (after a Heroic reinstall).")
    mode.add_argument("--force", action="store_true",
                      help="Overwrite even if games lost minutes or vanished.")
    args = parser.parse_args(argv)

    for env_path in args.env_file or [REPO / ".env", Path(".env")]:
        load_dotenv(env_path)

    try:
        if args.command == "status":
            snapshots = load_snapshots(args.devices_dir)
            if not snapshots:
                print(f"No device snapshots in {args.devices_dir}.")
                return 0
            print("\n".join(status_lines(snapshots)))
            return 0

        device = resolve_device(args.device)
        heroic_dir = resolve_heroic_config(args.heroic_config)
        if heroic_dir is None:
            if args.command == "check":
                load_snapshots(args.devices_dir)  # still validate what is there
                print("gaming devices: no Heroic install on this machine; nothing to export.",
                      file=sys.stderr)
                return 0
            raise DeviceError("could not find a Heroic config with a store library cache. "
                              "Point at it with --heroic-config.")

        if args.command == "check":
            snapshots, changed = collect(heroic_dir, args.devices_dir, device, write=False)
            print("gaming devices: ok. "
                  + describe(snapshots, device, changed, dry_run=True), file=sys.stderr)
            return 0

        # export
        if device is None:
            raise DeviceError("no device id: set GAMING_DEVICE in .env or pass --device.")
        if args.rotate and not args.dry_run:
            frozen = rotate(args.devices_dir, device, datetime.date.today().isoformat())
            print(f"Froze the old snapshot as {frozen.name}.", file=sys.stderr)
        _, changed = export(device, heroic_dir, args.devices_dir,
                            write=not args.dry_run, force=args.force or args.rotate)
        if args.dry_run:
            print(f"{device}.json would be {'updated' if changed else 'unchanged'} "
                  "(dry-run: nothing written).", file=sys.stderr)
        else:
            print(f"{device}.json {'written' if changed else 'unchanged'}.", file=sys.stderr)
        return 0
    except DeviceError as exc:
        print(f"! {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
