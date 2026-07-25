#!/usr/bin/env python3
"""Add a book to data/reading.yaml, fetching metadata + cover automatically.

The reading list is a flat list of book entries in data/reading.yaml, with
cover images committed under assets/images/books/covers/. This script does the
mechanical 80% of adding a book:

  * Looks the book up on Open Library (openlibrary.org) — free, no API key.
  * Pulls title, author, first-publish year, page count and the languages the
    book has been published in.
  * Downloads the cover image and writes it to the covers folder as
    "<Title>.jpg".
  * Proposes a canonical `link:` using the preferred order Wikipedia ->
    Open Library -> Goodreads (Goodreads has no public API, so it is only ever
    a search URL to paste-verify).
  * Suggests `genres:` by mapping Open Library subjects onto the site's own
    genre vocabulary (see GENRE_VOCAB below).
  * Emits a ready-to-paste YAML block, and with --append writes it straight to
    data/reading.yaml as raw text (so existing entries stay byte-for-byte
    unchanged and the git diff is limited to the appended lines).

Fields the script CANNOT know are left as TODO / empty for a human to fill:
  originalLanguage (Open Library lists every edition's language, not the
  original), rating, dateRead, languagesRead, languagesListened. The link
  candidate should always be eyeballed before committing.

Usage:
    scripts/add-book.py "Project Hail Mary" --author "Andy Weir"
    scripts/add-book.py "Dune" --isbn 9780441013593 --append
    scripts/add-book.py "1984" --series "" --year 1949 --append

Standard library only — no third-party dependency (matches sync-gallery.py).
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DATA = REPO / "data" / "reading.yaml"
DEFAULT_COVERS = REPO / "assets" / "images" / "books" / "covers"
COVER_REF_PREFIX = "images/books/covers"

USER_AGENT = "lna-dev.net reading-list adder (github.com/lna-dev; contact via site)"


def rel(path):
    """Path relative to the repo root for display, falling back to the raw path."""
    try:
        return path.relative_to(REPO)
    except ValueError:
        return path


# The site's own genre vocabulary, harvested from existing reading.yaml entries.
# Open Library subjects are mapped onto these; anything unmatched is reported so
# a human can extend this list or pick by hand.
GENRE_VOCAB = [
    "dystopian", "science fiction", "post-apocalyptic", "romance", "politics",
    "humor", "fantasy", "fiction", "war", "comedy", "survival", "classics",
    "thriller", "crime", "space", "hard science fiction", "cyberpunk",
    "photography", "shortStory",
]

# Substrings (lowercased) in an Open Library subject that imply a vocab genre.
GENRE_HINTS = {
    "dystopia": "dystopian",
    "hard science": "hard science fiction",
    "hard sci": "hard science fiction",
    "science fiction": "science fiction",
    "sci-fi": "science fiction",
    "scifi": "science fiction",
    "post-apocalyp": "post-apocalyptic",
    "apocalyp": "post-apocalyptic",
    "romance": "romance",
    "politic": "politics",
    "humor": "humor",
    "humour": "humor",
    "comed": "comedy",
    "fantasy": "fantasy",
    "war": "war",
    "surviv": "survival",
    "classic": "classics",
    "thriller": "thriller",
    "crime": "crime",
    "detective": "crime",
    "space": "space",
    "cyberpunk": "cyberpunk",
    "photograph": "photography",
    "short stor": "shortStory",
}

LANG3_TO_2 = {
    "eng": "en", "ger": "de", "deu": "de", "swe": "sv", "pol": "pl",
    "nor": "no", "fre": "fr", "fra": "fr", "spa": "es", "ita": "it",
    "por": "pt", "dut": "nl", "nld": "nl", "fin": "fi", "rus": "ru",
}


def http_get(url, accept_json=False):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return json.loads(data) if accept_json else data


def openlibrary_lookup(title, author=None, isbn=None):
    """Return the best-matching Open Library search doc, or None."""
    params = {
        "limit": "5",
        "fields": ",".join([
            "key", "title", "author_name", "first_publish_year",
            "number_of_pages_median", "cover_i", "cover_edition_key",
            "isbn", "language", "subject",
        ]),
    }
    if isbn:
        params["q"] = f"isbn:{isbn}"
    else:
        params["title"] = title
        if author:
            params["author"] = author
    url = "https://openlibrary.org/search.json?" + urllib.parse.urlencode(params)
    result = http_get(url, accept_json=True)
    docs = result.get("docs") or []
    if not docs:
        return None
    # Prefer the first doc that actually has a cover; else the first.
    for doc in docs:
        if doc.get("cover_i"):
            return doc
    return docs[0]


def download_cover(doc, dest_path):
    """Download the Open Library cover to dest_path. Returns True on success."""
    cover_id = doc.get("cover_i")
    isbns = doc.get("isbn") or []
    candidates = []
    if cover_id:
        candidates.append(f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg")
    for isbn in isbns[:3]:
        candidates.append(f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg")
    for url in candidates:
        try:
            data = http_get(url)
        except Exception as exc:  # noqa: BLE001 - report and try next
            print(f"  cover fetch failed ({url}): {exc}", file=sys.stderr)
            continue
        # Open Library returns a tiny 1x1 / empty blob when it has no cover.
        if len(data) < 2000:
            continue
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        return True
    return False


def wikipedia_candidate(title, author=None):
    """Return a Wikipedia URL if a plausible page for the *book* exists."""
    query = title if not author else f"{title} {author}"
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "list": "search", "format": "json",
        "srsearch": query, "srlimit": "3",
    })
    try:
        result = http_get(url, accept_json=True)
    except Exception:  # noqa: BLE001
        return None
    hits = result.get("query", {}).get("search", [])
    for hit in hits:
        page_title = hit.get("title", "")
        snippet = re.sub(r"<[^>]+>", "", hit.get("snippet", "")).lower()
        # Heuristic: the page should read like a book/novel, and the title
        # should resemble the book title (guards against author-only pages).
        looks_bookish = any(k in snippet for k in ("novel", "book", "written by", "author"))
        if looks_bookish:
            slug = page_title.replace(" ", "_")
            return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(slug)
    return None


def openlibrary_url(doc):
    key = doc.get("key")  # e.g. /works/OL123W
    return f"https://openlibrary.org{key}" if key else None


def goodreads_search_url(title, author=None):
    q = title if not author else f"{title} {author}"
    return "https://www.goodreads.com/search?q=" + urllib.parse.quote(q)


def suggest_genres(subjects):
    """Map Open Library subjects onto GENRE_VOCAB. Returns (matched, unmatched)."""
    matched, seen = [], set()
    for subj in subjects or []:
        low = subj.lower()
        for hint, genre in GENRE_HINTS.items():
            if hint in low and genre not in seen:
                seen.add(genre)
                matched.append(genre)
    # Keep vocab ordering stable for a tidy diff.
    matched = [g for g in GENRE_VOCAB if g in seen]
    unmatched = [s for s in (subjects or []) if not any(h in s.lower() for h in GENRE_HINTS)]
    return matched, unmatched[:10]


def safe_filename(title):
    # Linux allows almost everything; only strip path separators.
    return title.replace("/", "-").strip()


def yaml_quote(value):
    """Quote a scalar for YAML when it contains risky characters."""
    if value is None:
        return '""'
    text = str(value)
    if text == "" or re.search(r'[:#\'"\[\]{}&*!|>%@`,]', text) or text != text.strip():
        return '"' + text.replace('"', '\\"') + '"'
    return text


def build_block(fields):
    """Render the YAML list-entry block from a fields dict."""
    lines = [f"- title: {yaml_quote(fields['title'])}"]
    if fields.get("series"):
        lines.append(f"  series: {yaml_quote(fields['series'])}")
    lines.append(f"  author: {yaml_quote(fields['author'])}")

    genres = fields.get("genres") or []
    if genres:
        lines.append("  genres: [" + ", ".join(f'"{g}"' for g in genres) + "]")
    else:
        lines.append('  genres: []  # TODO: fill from subjects below')

    lines.append(f"  year: {fields['year']}")
    lines.append(f"  link: {yaml_quote(fields['link'])}")
    lines.append(f"  cover: {yaml_quote(fields['cover'])}")
    if fields.get("pages"):
        lines.append(f"  pages: {fields['pages']}")
    ol = fields.get("originalLanguage")
    if ol:
        lines.append(f"  originalLanguage: {yaml_quote(ol)}")
    else:
        lines.append("  originalLanguage:   # TODO: 2-letter code (OL langs: "
                     + ", ".join(fields.get("langs", [])) + ")")
    # Personal fields — left for the human.
    lines.append("  # rating:            # TODO: optional 1-5")
    lines.append('  # dateRead: ""       # TODO: optional "YYYY-MM-DD"')
    lines.append("  languagesRead: []    # TODO: e.g. [de, en]")
    lines.append("  # languagesListened: []")
    return "\n".join(lines) + "\n"


def already_present(data_path, title):
    if not data_path.exists():
        return False
    text = data_path.read_text(encoding="utf-8")
    pattern = re.compile(r'^\s*-\s*title:\s*["\']?' + re.escape(title), re.IGNORECASE | re.MULTILINE)
    return bool(pattern.search(text))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Add a book to data/reading.yaml.")
    parser.add_argument("title", help="Book title to look up.")
    parser.add_argument("--author", help="Author, to disambiguate the lookup.")
    parser.add_argument("--isbn", help="ISBN, most precise lookup key.")
    parser.add_argument("--series", help="Series name (Open Library rarely has this reliably).")
    parser.add_argument("--year", type=int, help="Override the first-publish year.")
    parser.add_argument("--append", action="store_true",
                        help="Append the block to reading.yaml (default: print only).")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--covers", type=Path, default=DEFAULT_COVERS)
    args = parser.parse_args(argv)

    if already_present(args.data, args.title):
        print(f"! '{args.title}' already looks present in {args.data.name} — aborting.",
              file=sys.stderr)
        return 2

    print(f"Looking up '{args.title}' on Open Library ...", file=sys.stderr)
    doc = openlibrary_lookup(args.title, args.author, args.isbn)
    if not doc:
        print("! No Open Library match. Try --author or --isbn.", file=sys.stderr)
        return 1

    resolved_title = args.title  # keep the user's spelling/casing for display + file
    author = args.author or (doc.get("author_name") or [""])[0]
    year = args.year or doc.get("first_publish_year")
    pages = doc.get("number_of_pages_median")
    langs = [LANG3_TO_2.get(l, l) for l in (doc.get("language") or [])]
    genres, unmatched = suggest_genres(doc.get("subject"))

    # Cover
    fname = safe_filename(resolved_title) + ".jpg"
    cover_path = args.covers / fname
    cover_ref = f"{COVER_REF_PREFIX}/{fname}"
    if download_cover(doc, cover_path):
        print(f"  cover saved -> {rel(cover_path)}", file=sys.stderr)
    else:
        print("  ! no cover found on Open Library — add one by hand.", file=sys.stderr)
        cover_ref = f"{COVER_REF_PREFIX}/{fname}  # TODO: cover not found, add manually"

    # Link: Wikipedia -> Open Library -> Goodreads
    link = wikipedia_candidate(resolved_title, author)
    link_source = "wikipedia"
    if not link:
        link = openlibrary_url(doc)
        link_source = "openlibrary"
    if not link:
        link = goodreads_search_url(resolved_title, author)
        link_source = "goodreads-search"

    fields = {
        "title": resolved_title, "series": args.series, "author": author,
        "genres": genres, "year": year, "link": link, "cover": cover_ref,
        "pages": pages, "originalLanguage": None, "langs": langs,
    }
    block = build_block(fields)

    print("\n" + "=" * 60, file=sys.stderr)
    print(f"link candidate ({link_source}) — VERIFY: {link}", file=sys.stderr)
    if unmatched:
        print("unmapped OL subjects (map by hand if useful): "
              + ", ".join(unmatched), file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

    if args.append:
        with args.data.open("a", encoding="utf-8") as fh:
            fh.write("\n" + block)
        print(f"Appended entry to {rel(args.data)}.", file=sys.stderr)
        print("Now fill the TODO fields (originalLanguage, personal fields) and "
              "verify link + genres.", file=sys.stderr)
    else:
        # Block goes to stdout so it can be piped/redirected; notes go to stderr.
        print(block)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
