#!/usr/bin/env python3
"""Fetch the facts and description candidates for every game page.

Writes one machine-owned file per game, data/gameFacts/<slug>.json, and nothing
else. The page decides what to show from it (layouts/partials/game-description.html
and game-facts.html); this script resolves nothing — it stores every candidate
with its source, so the order of the description chain is a template decision
that needs no refetch. Design: docs/concepts/gaming-game-pages.md §4.2.

Per game, keyed by the slug its copies carry in data/gaming.yaml:

  Wikidata item   the pin in data/gamePages.yaml (`wikidata: Q…`, or `none`);
                  else the item whose Steam application ID (P1733) is the appid
                  of the game's Steam copy — one batched SPARQL query; else none.
                  A TITLE match is never written: `--propose` prints candidates
                  for a person to check and pin, because a title search finds
                  convincing wrong hits (#RaceDieRun → "Stay Safe").
  Wikipedia       the item's en / de / sv sitelinks → each language's OWN
                  article, abridged to two or three sentences (wiki_common.py,
                  the dex's rule). Nothing is machine-translated.
  Steam store     `short_description` in english / german / swedish for the
                  Steam copy's appid, else the gamePages.yaml `steam_appid` pin,
                  else the item's P1733. Steam answers a missing translation with
                  the English text, silently — such a language is dropped.
  Facts           genre (P136) and game mode (P404) with en/de/sv labels,
                  developer (P178), publisher (P123), earliest publication date
                  (P577).

The file is overwritten completely on every run for that game: it is
machine-owned. Anything a person writes lives in data/gamePages.yaml, which is
only read here. A game with nothing to store has no file.

Standard library only; it writes files and never runs git. The Steam store
allows ~200 requests per 5 minutes, so store requests are spaced 1.5 s apart;
a full run takes about eight minutes, `--missing` or `--only` seconds.

Usage:
    python3 scripts/game-enrich.py --dry-run
    python3 scripts/game-enrich.py
    python3 scripts/game-enrich.py --missing
    python3 scripts/game-enrich.py --only stardew-valley --only hollow-knight
    python3 scripts/game-enrich.py --propose        # Wikidata candidates to pin
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gaming_common  # noqa: E402
import wiki_common  # noqa: E402
from dex_common import load_yaml  # noqa: E402

USER_AGENT = "lna-dev.net game pages (https://lna-dev.net/; me@lna-dev.net)"
WIKI_DELAY = 0.2
STORE_DELAY = 1.5
STEAM_LANGS = (("en", "english"), ("de", "german"), ("sv", "swedish"))
VIDEO_GAME = "Q7889"


# --------------------------------------------------------------------------- #
# HTTP                                                                         #
# --------------------------------------------------------------------------- #
def http_get(url, params=None, retries=3):
    """GET JSON. None on 404 or after the retries run out."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (429, 500, 502, 503, 504):
                time.sleep(3 * (attempt + 1))
                continue
            print(f"    ! {url}: {exc}", file=sys.stderr)
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries - 1:
                print(f"    ! {url}: {exc}", file=sys.stderr)
            time.sleep(1.5 * (attempt + 1))
    return None


def wiki_get(url, params=None):
    data = http_get(url, params)
    time.sleep(WIKI_DELAY)
    return data


# --------------------------------------------------------------------------- #
# The games                                                                    #
# --------------------------------------------------------------------------- #
def load_games(gaming_path=gaming_common.GAMING_DATA, pages_path=gaming_common.PAGES_DATA,
               ignore_path=gaming_common.REPO / "data" / "gamingIgnore.yaml"):
    """{slug: {"titles", "platforms", "steam_appids", "page"}} for every game
    that gets a page — gamingIgnore.yaml removes a copy here as in the build."""
    ignore = {str(t).strip().lower()
              for t in ((load_yaml(ignore_path) or {}).get("titles") or [])}
    pages = {str(p.get("slug")): p for p in ((load_yaml(pages_path) or {}).get("games") or [])
             if p and p.get("slug")}
    games = {}
    for copy in load_yaml(gaming_path) or []:
        slug = copy.get("slug")
        title = str(copy.get("title") or "")
        if not slug or title.strip().lower() in ignore:
            continue
        g = games.setdefault(str(slug), {"titles": [], "platforms": [], "steam_appids": [],
                                         "page": pages.get(str(slug), {})})
        g["titles"].append(title)
        g["platforms"].append(copy.get("platform") or "manual")
        if copy.get("platform") == "steam" and copy.get("appid"):
            g["steam_appids"].append(str(copy["appid"]))
    return games


# --------------------------------------------------------------------------- #
# Wikidata                                                                     #
# --------------------------------------------------------------------------- #
def qids_for_steam_appids(appids):
    """{appid: QID} through P1733, in one query. Where several items carry the
    same appid (a game and its edition), the lowest QID — the older item, as a
    rule the game itself — wins."""
    if not appids:
        return {}
    values = " ".join(f'"{a}"' for a in sorted(set(appids)))
    query = f"SELECT ?app ?item WHERE {{ VALUES ?app {{ {values} }} ?item wdt:P1733 ?app . }}"
    data = wiki_get("https://query.wikidata.org/sparql", {"query": query, "format": "json"})
    out = {}
    for row in ((data or {}).get("results") or {}).get("bindings") or []:
        app = row["app"]["value"]
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        if app not in out or int(qid[1:]) < int(out[app][1:]):
            out[app] = qid
    return out


def entities(ids, props="labels", languages="en|de|sv"):
    """wbgetentities for up to any number of ids, 50 per request."""
    out = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), 50):
        data = wiki_get("https://www.wikidata.org/w/api.php", {
            "action": "wbgetentities", "ids": "|".join(ids[i:i + 50]),
            "props": props, "languages": languages, "format": "json",
        })
        out.update((data or {}).get("entities") or {})
    return out


def claim_values(entity, prop):
    return [c.get("mainsnak", {}).get("datavalue", {}).get("value")
            for c in (entity.get("claims") or {}).get(prop, [])
            if c.get("mainsnak", {}).get("datavalue")]


def claim_ids(entity, prop):
    return [v["id"] for v in claim_values(entity, prop) if isinstance(v, dict) and v.get("id")]


def earliest_date(entity):
    """The earliest P577 as YYYY-MM-DD, YYYY-MM or YYYY — as precise as the
    statement is, and no more."""
    best = None
    for v in claim_values(entity, "P577"):
        if not isinstance(v, dict) or not v.get("time"):
            continue
        m = re.match(r"^\+?(\d{4})-(\d{2})-(\d{2})", v["time"])
        if not m:
            continue
        precision = int(v.get("precision") or 9)
        year, month, day = m.groups()
        text = year if precision <= 9 else f"{year}-{month}" if precision == 10 else f"{year}-{month}-{day}"
        key = (year, month if precision >= 10 else "99", day if precision >= 11 else "99")
        if best is None or key < best[0]:
            best = (key, text)
    return best[1] if best else ""


def labels_of(entity):
    """{en, de, sv} labels of an item, only the languages that exist."""
    return {lang: entity["labels"][lang]["value"]
            for lang in gaming_common.LANGS if lang in (entity.get("labels") or {})}


def name_of(entity):
    """One display name for a company: English, else the first label there is."""
    labels = entity.get("labels") or {}
    for lang in ("en", "de", "sv"):
        if lang in labels:
            return labels[lang]["value"]
    return next((v["value"] for v in labels.values()), "")


def propose(title):
    """Wikidata items that are video games and match `title`: [(qid, label,
    year, exact)]. Printed for a person to check, never written."""
    clean = re.sub(r"[™®©]", "", title).strip()
    found = wiki_get("https://www.wikidata.org/w/api.php", {
        "action": "wbsearchentities", "search": clean, "language": "en",
        "type": "item", "limit": 7, "format": "json"})
    ids = [x["id"] for x in (found or {}).get("search", [])]
    if not ids:
        return []
    ents = entities(ids, props="claims|labels", languages="en")
    out = []
    for qid in ids:
        e = ents.get(qid) or {}
        if VIDEO_GAME not in claim_ids(e, "P31"):
            continue
        label = name_of(e)
        out.append((qid, label, earliest_date(e)[:4], label.lower() == clean.lower()))
    return out


# --------------------------------------------------------------------------- #
# Steam store                                                                  #
# --------------------------------------------------------------------------- #
def plain_text(fragment):
    """The store's short description is HTML-ish: entities, the odd tag."""
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def store_descriptions(appid):
    """{en, de, sv} short descriptions of a Steam app, a language dropped where
    it only repeats English (Steam's silent fallback)."""
    texts = {}
    for lang, steam_lang in STEAM_LANGS:
        data = http_get("https://store.steampowered.com/api/appdetails",
                        {"appids": appid, "l": steam_lang})
        time.sleep(STORE_DELAY)
        entry = (data or {}).get(str(appid)) or {}
        if entry.get("success"):
            texts[lang] = plain_text((entry.get("data") or {}).get("short_description"))
    return gaming_common.localised(texts)


# --------------------------------------------------------------------------- #
# One game                                                                     #
# --------------------------------------------------------------------------- #
def build_facts(qid, match, entity, labels, summaries, steam_appid, steam_texts):
    """Pure: the facts document of one game from what was fetched.

    `entity`    the item (claims, sitelinks with urls) or {}
    `labels`    {QID: entity with labels} for genres, modes and companies
    `summaries` {lang: (text, url)} — the abridged article of each language
    Returns the document, or None when there is nothing at all to store."""
    doc = {}
    if qid:
        doc["wikidata"] = qid
        doc["match"] = match
        wp = {lang: {"text": text, "url": url} for lang, (text, url) in summaries.items() if text}
        if wp:
            doc["wikipedia"] = wp
        for key, prop in (("genres", "P136"), ("modes", "P404")):
            items = [labels_of(labels[i]) for i in claim_ids(entity, prop) if i in labels]
            items = [i for i in items if i.get("en")]
            if items:
                doc[key] = items
        for key, prop in (("developers", "P178"), ("publishers", "P123")):
            names = []
            for i in claim_ids(entity, prop):
                name = name_of(labels.get(i) or {})
                if name and name not in names:
                    names.append(name)
            if names:
                doc[key] = names
        released = earliest_date(entity)
        if released:
            doc["released"] = released
    if steam_appid and steam_texts:
        doc["steam_appid"] = int(steam_appid)
        doc["steam"] = steam_texts
    return doc or None


def enrich(slug, game, qid, match):
    """Fetch everything for one game and return its facts document (or None)."""
    entity, labels, summaries = {}, {}, {}
    if qid:
        entity = (entities([qid], props="claims|sitelinks/urls").get(qid)) or {}
        # A Steam app id often belongs to an EDITION ("Horizon Zero Dawn Complete
        # Edition"), whose item has no articles. Its "edition of" (P629) is the
        # game the articles are about; that item is the one to read.
        if not any(f"{lang}wiki" in (entity.get("sitelinks") or {}) for lang in gaming_common.LANGS):
            parents = claim_ids(entity, "P629")
            if parents:
                parent = (entities(parents[:1], props="claims|sitelinks/urls").get(parents[0])) or {}
                if parent.get("sitelinks"):
                    qid, match, entity = parents[0], f"{match}+edition-of", parent
        wanted = [i for p in ("P136", "P404", "P178", "P123") for i in claim_ids(entity, p)]
        labels = entities(wanted) if wanted else {}
        for lang in gaming_common.LANGS:
            link = (entity.get("sitelinks") or {}).get(f"{lang}wiki")
            if link:
                text = wiki_common.wikipedia_summary(link["title"], lang, wiki_get)
                url = link.get("url") or wiki_common.article_url(link["title"], lang)
                summaries[lang] = (text, url)

    steam_appid = (game["steam_appids"][:1] or [None])[0] \
        or (str(game["page"].get("steam_appid")) if game["page"].get("steam_appid") else None)
    if not steam_appid:
        p1733 = [str(v) for v in claim_values(entity, "P1733")]
        steam_appid = p1733[0] if p1733 else None
    steam_texts = store_descriptions(steam_appid) if steam_appid else {}
    return build_facts(qid, match, entity, labels, summaries, steam_appid, steam_texts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch facts for the game pages.")
    parser.add_argument("--only", action="append", default=[], help="Only this slug (repeatable).")
    parser.add_argument("--missing", action="store_true", help="Only games without a facts file.")
    parser.add_argument("--propose", action="store_true",
                        help="Print Wikidata candidates for games without an item; write nothing.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and report; write nothing.")
    args = parser.parse_args(argv)

    games = load_games()
    slugs = sorted(games)
    if args.only:
        unknown = sorted(set(args.only) - set(games))
        if unknown:
            print(f"! unknown slug(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        slugs = [s for s in slugs if s in args.only]
    if args.missing:
        slugs = [s for s in slugs if not (gaming_common.FACTS_DIR / f"{s}.json").exists()]

    by_appid = qids_for_steam_appids([a for s in slugs for a in games[s]["steam_appids"]])

    def resolve(slug):
        pin = str(games[slug]["page"].get("wikidata") or "").strip()
        if pin.lower() == "none":
            return None, "none"
        if pin:
            return pin, "pinned"
        for appid in games[slug]["steam_appids"]:
            if appid in by_appid:
                return by_appid[appid], "steam-appid"
        return None, ""

    if args.propose:
        for slug in slugs:
            qid, match = resolve(slug)
            if qid or match == "none":
                continue
            g = games[slug]
            print(f"# {g['titles'][0]} ({', '.join(sorted(set(g['platforms'])))})")
            candidates = propose(g["titles"][0])
            if not candidates:
                print(f"- slug: {slug}\n  wikidata: none   # no video-game item found\n")
                continue
            for n, (cand, label, year, exact) in enumerate(candidates):
                mark = "exact" if exact else "check"
                prefix = "" if n == 0 else "# "
                print(f"{prefix}- slug: {slug}\n{prefix}  wikidata: {cand}   # {label} ({year or '?'}) [{mark}]")
            print()
        print("(propose: nothing written — paste what is right into data/gamePages.yaml)",
              file=sys.stderr)
        return 0

    written = unchanged = removed = 0
    for n, slug in enumerate(slugs, 1):
        qid, match = resolve(slug)
        doc = enrich(slug, games[slug], qid, match)
        path = gaming_common.FACTS_DIR / f"{slug}.json"
        what = []
        if doc:
            what = [k for k in ("wikipedia", "steam", "genres") if k in doc]
        print(f"[{n}/{len(slugs)}] {slug}: {qid or '—'} {' '.join(what)}", file=sys.stderr)
        if args.dry_run:
            continue
        if doc:
            if gaming_common.write_json(path, doc):
                written += 1
            else:
                unchanged += 1
        elif path.exists():
            path.unlink()
            removed += 1

    if args.dry_run:
        print("(dry-run: nothing written)", file=sys.stderr)
    else:
        print(f"{written} written, {unchanged} unchanged, {removed} removed.", file=sys.stderr)
        print("Games with no Wikidata item: python3 scripts/game-enrich.py --propose",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
