"""Shared helpers for the game syncs and the game-page scripts.

Imported by scripts/sync-steam.py, sync-epic.py, sync-gog.py,
gaming-add-slugs.py and game-enrich.py. Standard library only.

Four things live here because more than one script needs them, and two copies
of any of them would drift:

  * the slug rule — a game's page URL, written once per copy and never
    recomputed (docs/concepts/gaming-game-pages.md §2);
  * slug assignment during a sync — keep the old slug, give a new game one, and
    report when a new copy joins a game already on another platform;
  * the achievement files — deterministic JSON under data/gameAchievements/ and
    the icon store under static/images/games/achievements/;
  * Europe/Berlin timestamps, so an unlock at 00:14 local time is dated that day
    on the page and not the day before.
"""

import json
import re
import sys
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
GAMING_DATA = REPO / "data" / "gaming.yaml"
PAGES_DATA = REPO / "data" / "gamePages.yaml"
ACH_DATA_DIR = REPO / "data" / "gameAchievements"
FACTS_DIR = REPO / "data" / "gameFacts"
# Static, not assets: the icons need no processing, and ~3,100 of them as Hugo
# resources overflowed its resource cache (see game-achievements.html). The ref
# is the URL path the file is served at.
ACH_ICON_DIR = REPO / "static" / "images" / "games" / "achievements"
ACH_ICON_REF = "images/games/achievements"

LANGS = ("en", "de", "sv")
BERLIN = ZoneInfo("Europe/Berlin")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# The platforms a sync owns. Anything else in data/gaming.yaml is hand-added.
SYNCED_PLATFORMS = ("steam", "gog", "epic")

USER_AGENT = "lna-dev.net gaming-sync (github.com/lna-dev; contact via site)"


# --------------------------------------------------------------------------- #
# Slugs                                                                        #
# --------------------------------------------------------------------------- #
def slugify(title):
    """The page slug for a game title: language-neutral, ASCII only.

    Trademark signs go, ß becomes ss, every other letter is folded to ASCII the
    way the gallery's English `.fileSlug` folds it (ä → a, é → e), and every run
    of anything else becomes one hyphen. `Life is Strange™` → `life-is-strange`,
    `>observer_` → `observer`, `Pokémon HeartGold` → `pokemon-heartgold`."""
    text = re.sub(r"[™®©]", "", str(title or ""))
    text = text.replace("ß", "ss").replace("ẞ", "SS")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def assign_slugs(games, key_of, old_slugs, taken):
    """Give every fetched game of one platform its slug.

    `games`     the fetched games, in the order the sync writes them;
    `key_of`    game -> the platform's stable key (appid / appName) as a string;
    `old_slugs` {key: slug} read back out of this platform's previous block;
    `taken`     every slug used by an entry this sync does NOT own.

    A game that had a slug keeps it — that is what makes a URL survive a Steam
    rename. A new game gets slugify(title); if another game of the SAME platform
    already has that slug (two different games, one title), the key is appended,
    because the build refuses two same-platform copies under one slug. A new slug
    that another platform already uses is a JOIN: the copy becomes part of that
    game's page. That is the intended outcome for the same game on two stores,
    and it is reported so the dry run shows it.

    Returns ({key: slug}, new: [(key, slug)], joined: [(key, slug)])."""
    out, new, joined = {}, [], []
    used = set()
    for g in games:
        key = key_of(g)
        slug = old_slugs.get(key)
        if slug:
            out[key] = slug
            used.add(slug)
    for g in games:
        key = key_of(g)
        if key in out:
            continue
        slug = slugify(g.get("title")) or slugify(key) or "game"
        if slug in used:
            slug = f"{slug}-{slugify(key)}"
        out[key] = slug
        used.add(slug)
        new.append((key, slug))
        if slug in taken:
            joined.append((key, slug))
    return out, new, joined


def report_slugs(new, joined, stream=sys.stderr):
    """Print what a sync did with slugs — the part of a dry run worth reading."""
    joined_keys = {k for k, _ in joined}
    for key, slug in new:
        note = "  (joins an existing game)" if key in joined_keys else ""
        print(f"  new slug: {key} -> {slug}{note}", file=stream)


# --------------------------------------------------------------------------- #
# Deterministic JSON                                                           #
# --------------------------------------------------------------------------- #
def dump_json(obj):
    """One canonical serialisation: sorted keys, one-space indent, real UTF-8,
    trailing newline. Same input, same bytes — so a sync that changed nothing
    leaves nothing in the diff."""
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def write_json(path, obj):
    """Write `obj` to `path` only when the bytes differ. Returns True if written."""
    path = Path(path)
    text = dump_json(obj)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


# --------------------------------------------------------------------------- #
# Time                                                                         #
# --------------------------------------------------------------------------- #
def berlin_iso(value):
    """A Unix timestamp (int/float/str) or an ISO 8601 string -> RFC 3339 in
    Europe/Berlin with its offset, e.g. "2019-02-11T21:14:03+01:00". None for
    anything that is not a real point in time (Steam writes 0 for "unknown").

    A fixed zone rather than the machine's local time, so two machines produce
    the same file; and the offset is kept, because Hugo formats a time in the
    zone it carries — a UTC value would date a 00:14 unlock the day before."""
    if value in (None, "", 0, "0"):
        return None
    try:
        if isinstance(value, (int, float)) or re.fullmatch(r"\d+(\.\d+)?", str(value)):
            ts = float(value)
            if ts <= 0:
                return None
            moment = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            text = str(value).strip().replace("Z", "+00:00")
            moment = datetime.fromisoformat(text)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return moment.astimezone(BERLIN).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- #
# Achievements                                                                 #
# --------------------------------------------------------------------------- #
def localised(values):
    """{lang: text} with every language that only repeats English dropped.

    Steam answers a language it has no translation for with the English text,
    silently, so "the German name equals the English one" means "there is no
    German name". Storing it anyway would make every file three times as long
    and say nothing the English fallback in the template does not already say."""
    en = (values.get("en") or "").strip()
    out = {"en": en} if en else {}
    for lang in LANGS[1:]:
        text = (values.get(lang) or "").strip()
        if text and text != en:
            out[lang] = text
    return out


def icon_basename(url):
    """The file name an icon is stored under: the last path segment of its URL,
    with a .jpg extension if it has none. Steam's are content hashes for most
    games (a few older Valve ones are named after the achievement), so an
    unchanged icon keeps its name and is never downloaded twice."""
    name = str(url).split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name) or "icon"
    if "." not in name:
        name += ".jpg"
    return name


def achievement_file(platform, key):
    return ACH_DATA_DIR / f"{platform}-{key}.json"


def icon_ref(platform, key, url):
    return f"{ACH_ICON_REF}/{platform}/{key}/{icon_basename(url)}"


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def sync_icons(platform, key, urls, *, icon_root=ACH_ICON_DIR, fetch=_fetch):
    """Make static/images/games/achievements/<platform>/<key>/ hold exactly the
    icons in `urls`: download the missing ones, delete the ones no achievement
    references any more. Only that one game's folder is ever touched. Returns
    (downloaded, removed, failed)."""
    folder = Path(icon_root) / platform / str(key)
    wanted = {icon_basename(u): u for u in urls if u}
    missing = {name: url for name, url in wanted.items() if not (folder / name).exists()}

    downloaded, failed = 0, []
    if missing:
        folder.mkdir(parents=True, exist_ok=True)

        def one(item):
            name, url = item
            try:
                data = fetch(url)
            except Exception as exc:  # noqa: BLE001 - one icon never fails the sync
                return name, None, exc
            return name, data, None

        with ThreadPoolExecutor(max_workers=8) as pool:
            for name, data, exc in pool.map(one, sorted(missing.items())):
                if data:
                    (folder / name).write_bytes(data)
                    downloaded += 1
                else:
                    failed.append((name, exc))

    removed = 0
    if folder.is_dir():
        for f in folder.iterdir():
            if f.is_file() and f.name not in wanted:
                f.unlink()
                removed += 1
        if not any(folder.iterdir()):
            folder.rmdir()
    return downloaded, removed, failed


def prune_achievements(platform, keep_keys, *, data_dir=ACH_DATA_DIR, icon_root=ACH_ICON_DIR):
    """Remove the achievement file and the icon folder of every copy of
    `platform` whose key is not in `keep_keys`. Returns the removed keys."""
    removed = []
    prefix = f"{platform}-"
    data_dir = Path(data_dir)
    if data_dir.is_dir():
        for f in sorted(data_dir.glob(f"{prefix}*.json")):
            key = f.stem[len(prefix):]
            if key not in keep_keys:
                f.unlink()
                removed.append(key)
    icons = Path(icon_root) / platform
    if icons.is_dir():
        for d in sorted(icons.iterdir()):
            if d.is_dir() and d.name not in keep_keys:
                for f in d.iterdir():
                    f.unlink()
                d.rmdir()
    return removed


def write_achievement_docs(platform, docs, urls, keep_keys, *, dry_run=False, stream=sys.stderr):
    """The filesystem half of a sync's achievement step, shared by Steam and GOG.

    `docs`      {key: document} for every copy whose achievements were fetched;
    `urls`      {key: [icon url, ...]} for the same copies;
    `keep_keys` every key whose file must survive — the fetched ones plus any
                whose fetch failed transiently and so keep yesterday's file.

    Writes each document (only if its bytes changed), syncs its icons, and
    deletes the file and icons of every copy not in `keep_keys`."""
    if dry_run:
        print(f"  achievements: {len(docs)} {platform} file(s) would be written "
              "(dry-run: nothing written)", file=stream)
        return
    written = 0
    for key, doc in sorted(docs.items()):
        if write_json(achievement_file(platform, key), doc):
            written += 1
        got, gone, failed = sync_icons(platform, key, urls.get(key, []))
        if failed:
            # Some stores reference icons they no longer serve (verified for three
            # Steam games: every CDN host 404s, the grey variant too). The page
            # shows an empty tile; the next sync simply tries again.
            print(f"  icons: {len(failed)} of {platform}/{key} not available "
                  f"({failed[0][1]})", file=stream)
    removed = prune_achievements(platform, set(keep_keys))
    print(f"  achievements: {written} {platform} file(s) written, "
          f"{len(docs) - written} unchanged, {len(removed)} removed.", file=stream)
