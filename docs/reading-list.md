# Reading list

Books the user has read. **Data**: `data/reading.yaml` — a flat list, one entry per book. Fields: `title`, `series` (optional), `author`, `genres[]`, `year`, `link`, `cover`, `pages`, `originalLanguage` (2-letter code), `languagesRead[]` / `languagesListened[]`, and optional `rating` (1–5), `dateRead` (`"YYYY-MM-DD"`, drives the `recentReading` preview order), `notes`. **Covers**: committed JPEG/WebP files in `assets/images/books/covers/`, referenced as `images/books/covers/<Title>.<ext>` and resized to a 200×300 fit through `image-variant.html` (published at `/images/books/covers/fit-200x300/<Title>.<ext>`). Unlike gallery photos, these images *are* in git. Rendered by `layouts/shortcodes/readingList.html` (full list) and `layouts/shortcodes/recentReading.html` (profile-page preview).

**A post about a book** names it in its front matter with `book: "<exact title in data/reading.yaml>"`; `schema_json.html` then gives the BlogPosting an `about: Book` (author, series, language, pages, `link` as `sameAs`). **`review: true`** on top adds a separate schema.org `Review` with the entry's `rating` as `reviewRating` (x/5), the shape Google's review snippet reads, so the rating is kept in the reading list and nowhere else. Google wants a marked-up rating visible on the page, so the post should say it in the text. A `book:` that matches no title, or more than one, and a `review: true` without `book:` are build errors (production builds only, like all JSON-LD). No cover in the markup: publisher art, like the game covers.

**Adding a book — use `scripts/add-book.py`** (stdlib only; full workflow below). It looks the book up on Open Library (free, no key), downloads the cover into the covers folder, and appends a YAML entry (`--append`) or prints a paste-ready block. It auto-fills `title`/`author`/`year`/`pages`/`cover`, proposes a `link` (Wikipedia → Open Library → Goodreads-search, always verify), and suggests `genres` mapped onto the existing vocabulary. It **cannot** know `originalLanguage`, `rating`, `dateRead`, `languagesRead`/`languagesListened` — those are left as TODO/empty for a human. Always eyeball the link and genres before committing (subject mapping produces occasional false positives). Do **not** run `./deploy.sh` after adding — that is a separate, explicitly-authorized step.

## Adding books to the reading list

The reading list lives in `data/reading.yaml` (one entry per book) with cover
images committed under `assets/images/books/covers/`. The full data model is
above.

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
