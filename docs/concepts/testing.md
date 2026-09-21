# Concept: making the site testable

**Status:** proposal, 2026-09-18, revised the same day after review with the author (browser matrix, single command and report, Tor and CI scope); re-read against the tree on 2026-09-20 and amended for the three features that landed in between — the model pages, the download dialog and the photo pages (`a3493a3`, `9b43872`, `a40d8ec`). **Implemented on 2026-09-20** — phases 1 to 5 of §8; §11 below records what the build found and where the implementation departs from this design. Phase 6 (fixtures, hosted CI) is still designed rather than scheduled, as intended. Every number below was measured against the working tree on that day: `data/gallery.yaml` with 648 entries, the photo store (648 files, 6.6 GB), a warm image cache (2.1 GB), Hugo 0.166.0, and a fresh production build (4,641 HTML files, 8.0 GB, 15.2 s).
**Read against:** the tree after the metadata single-source work (`gallery-metadata-single-source.md`, `gallery-metadata-import.md`), which is what introduced the one permanent automated check this repo has — `gallery-embed-metadata.py --check`.

The site has three kinds of logic and none of them is under test: ~90 Go templates that resolve, filter and join the data files; ~2,400 lines of client-side JavaScript (lightbox with hand-wired history, filters, the dex map, the feed, the newsletter form, the download dialog); and four stdlib-only Python toolchains (gallery, dex, reading list, game syncs) that write the data files. The only automated checks are the 24 `errorf` and 8 `warnf` calls in the templates, plus `--check` in `deploy.sh`. Everything else has been verified by hand, often with a throwaway probe script written beside a concept document and deleted with its worktree — `test-feed.py` ran 285 feed assertions, `xmllint` over 114 feeds and an MD5 diff over 753 pages for the RSS work, and none of that runs today.

Two constraints shape what "testable" can mean here and both are in CLAUDE.md already: **the photos are not in git**, so no hosted CI can build the real gallery, and **the image cache costs more than ten minutes cold**, so nothing may ever start from a clean build. The proposal is four layers behind **one command, `npm test`, producing one report**: the build itself, Python unit tests, static checks over the built HTML, and browser tests in Firefox first, Chromium and WebKit beside it. All of it runs locally and becomes the gate in `deploy.sh`; hosted CI on a fixture gallery is designed in §4 but not scheduled.

## Settled decisions

| | |
|---|---|
| Layers | Four. L0 the build with warnings counted as failures; L1 Python unit tests for `scripts/`; L2 static checks over the built site (data ↔ output invariants, links, structured data, feeds, URL stability); L3 browser tests |
| One command, one report | `npm test` runs every layer through **one runner, `@playwright/test`** (1.63), and writes one HTML report. The build and the Python suite are Playwright *projects* too, so a failed build shows up as a red test with the Hugo log attached and skips everything downstream. §5 |
| Primary browser | **Firefox** — every L3 scenario runs there first. **Chromium and WebKit** (Safari's engine) run the same scenarios; two mobile projects, Chrome on a Pixel and Safari on an iPhone, run the scenarios tagged `@mobile`. Firefox cannot emulate mobile in Playwright, which is why the mobile projects are the other two engines. §2 |
| Python tests | stdlib **`unittest`**, no pytest. The scripts are stdlib-only on purpose (any machine with `python3` can add a photo); their tests keep that property. They appear in the report as one entry per test module |
| YAML in the Node tests | the `yaml` npm package as a devDependency. Not a Python venv with PyYAML — Node is already there for Playwright, and the tests check the *site*, which Hugo builds from that YAML |
| The build under test | `hugo -e production -b http://localhost:1414 -d .test-site` — **production environment** (`head.html:246` emits opengraph, twitter cards and JSON-LD only then), a **localhost base URL** so the menu's absolute links stay on the test server, and its **own destination**, so `public/` remains exclusively the deploy artefact. Served by `python3 -m http.server`; no second Hugo process. §5 |
| Network under test | every request to a host other than `localhost` is **aborted by default**; the companion API and listmonk are mocked with `page.route`. The block is itself the assertion the dex map needs (*zero third-party requests on load*) |
| The deploy gate | `deploy.sh` runs `npm test` first, then its own `hugo`, then the static project once more over that `public/` (2 s) — the one check that can catch a stale or development build in the artefact itself — then publishes. §6 |
| The Tor build | **has to build and be reachable, nothing more.** No clearnet-leak policy, no second test pass; `deploy.sh` builds and publishes it as today |
| Hosted CI | **not excluded, not near-term.** The fixture environment in §4 is the design for when it comes; nothing in phases 1–5 depends on it |
| Fixture photos | whichever six to eight — decided when §4 is built, not before |
| Accessibility, visual regression | out of scope (§10) |
| Invariants that make a page wrong | stay **`errorf` in the templates**, the pattern the repo already has. Tests cover what a build cannot see: cross-file consistency, rendered output, behaviour |
| URL stability | a **golden list** of every published URL, checked in. The test is not "the list is unchanged" but "every URL that was ever on it still resolves to a page or an alias" |
| Language | tests, fixtures and their comments in English, like the rest of the repo |

## Still open — nothing blocking

| | |
|---|---|
| ~~WebKit on this machine~~ | **Answered, 2026-09-20: the container.** Playwright's Linux WebKit links `libicu*.so.74` and `libjpeg.so.8`; Fedora 44 ships ICU 77 and `libjpeg.so.62`, so there is no `dnf` list that satisfies it without compat packages. Chromium and Firefox run natively and needed nothing. `webkit` and `mobile-safari` are therefore **opt-in** (`WEBKIT=1`), not in the default run — a suite that is red every time teaches people to ignore red — and `playwright.config.ts` carries the podman command |
| ~~The `@mobile` subset~~ | **Built as designed:** navbar, gallery back link, grid layout, lightbox under touch — four scenarios in `tests/e2e/mobile.spec.ts`, each tagged `@mobile`. It grows when a mobile bug appears |

---

## 1. What is checked today — and what a one-second probe found

**In the build.** 24 `errorf` and 8 `warnf`, all in the gallery, dex and shortcode templates. They cover: a `license:` that is missing or not a key, a missing artist, an entry without `id`, an empty or duplicate slug, a `galleryImage` id that names no photo, a dex page whose species is gone, a species without slug or scientific name, bad shortcode arguments, and a `newsletter.yaml` without list uuids. Two things are *warnings* where they should fail: a `species:` in the gallery that names no dex species (`dex-index.html:107`) and an empty gallery mount (`gallery-images.html:18`).

**In deploy.** `gallery-embed-metadata.py --check` reads every served file back and asserts its `DigitalImageGUID`. That is the model for L2: a function of the built site that refuses to ship.

**Nowhere.** Everything that lives in the browser, every cross-file consistency, and every property of the rendered HTML. A read-only probe over the build on the day of writing, ~80 lines of Python, 0.9 s:

| Finding | Where | Would be caught by |
|---|---|---|
| 7 Swedish i18n keys missing; the lightbox falls back to English on `/sv/` | `i18n/sv.yaml` — 219 ids against 226 in `en` and `de`: `arrowNextTitle`, `arrowPrevTitle`, `closeTitle`, `downloadTitle`, `errorMsg`, `words`, `zoomTitle`. It was 9 when this was measured; `photoCount` and `albumCount` were added by the models commit two days later, and `downloadTitle` arrived missing with the download dialog the day after that — which is the case for the parity test better than the count is | L0 `--printI18nWarnings`, and the key-parity test in L2 |
| 8 broken internal links (the count on the day of the probe) | `<a class="next" href="posts">` in `home.html:126` and `list.html:265` is *relative*, so on `/en/page/2/` it resolves to `/en/page/2/posts` — broken on every paginated home page in `en` and `de`; plus the two relative links in `content/posts/Projects/pixelfed-automation/index.en.md` (lines 19 and 22 — note the capital `Projects` in that path) | L2 link check |
| `public/` held a **development build**: `http://localhost:1313` on 4,640 of 4,641 pages, no opengraph, no JSON-LD | `hugo server` **writes to disk by default** in this Hugo version (`hugo server --help`), so the everyday server on :1313 overwrites `public/` on every rebuild. `deploy.sh` rebuilds before it publishes, so nothing shipped — but nothing would have stopped it either, and it is why the test build gets its own destination | the static project run over `public/` in `deploy.sh` — "no `localhost`, every page has its schema" |
| `--printUnusedTemplates` is **unusable as a gate** | it reports `schema_json.html`, `opengraph.html`, `twitter_cards.html` and `_default/page.html` as unused; the first three are invoked with `template`, not `partial`, and are on every page | nothing — noted so nobody wires it in |
| HTML is not byte-reproducible | `layouts/shortcodes/map.html:3` uses `math.Rand` for the element id, so two builds of the same tree differ | a determinism test, once the id comes from `.Ordinal` |

**In the history.** Of the last 30 `fix` commits, the ones a test would have caught: `fix rss` (twice), `fix gallery link in feed`, `Fix alias`, `Fix categories`, `Fix security txt` (an `Expires` four months in the past), `Fix swedish language locale`, `Fix tags missing` — all L2; `Fix navbar on mobile`, `fix back link on mobile`, `Fix click on image on homepage`, `fix console error`, `fix dex viewport`, `fix newsletter popup` — all L3. The lightbox back button has its own worktree.

## 2. The four layers

| | What runs | What it catches | Needs the photos | Cost |
|---|---|---|---|---|
| **L0 Build** | `hugo -e production -b http://localhost:1414 -d .test-site --cleanDestinationDir --printI18nWarnings --printPathWarnings --logLevel warn`, asserted to exit 0 with **no `WARN` line**; then `hugo mod verify` | everything the templates already `errorf`, promoted: missing translations, duplicate output paths, the unknown-species and empty-mount warnings, Hugo deprecations after an upgrade | yes | 15 s warm |
| **L1 Python** | `python3 -m unittest discover -s tests/py`, one report entry per module | the writers of the data files and the embedding step | no | < 1 s |
| **L2 Static** | the `static` project over `.test-site/` (or `public/`, in deploy) | data ↔ output consistency, links, JSON-LD, feeds, sitemap, URL stability, leaks | yes (reads the build) | ~2 s |
| **L3 Browser** | `firefox`, `chromium`, `webkit`, `mobile-chrome`, `mobile-safari` against `http://localhost:1414` | the JavaScript, the CSS at two viewports, the network policy | yes | ~2–4 min |

### L0 — the build as a test

Hugo already refuses to build on an `errorf`. Treating every `WARN` line as a failure extends that to the `warnf`s and to Hugo's own warnings, which turns a deploy into a gate for free: an unknown `species:`, an empty mount, a template deprecation introduced by a PaperMod bump. The test does **not** pass `--panicOnWarning` — that stops at the first warning, and the report should show all of them at once — while `deploy.sh`'s own `hugo` does pass it, because there the first warning is reason enough to stop. The trade-off is explicit: **a warning blocks a deploy.** That is the point. The escape hatch for a warning that is genuinely someone else's problem is Hugo's `ignoreLogs` list in `hugo.yaml`, keyed by the warning's id, so an ignore is visible and reviewable. `--printPathWarnings` catches the class of bug the `securitytxt` output format hit (three languages writing one target path). `--printUnusedTemplates` stays out for the reason in §1. The build test gets a 20-minute timeout: a cold image cache is slow, not wrong.

### L1 — the Python scripts

The scripts are text-level writers with pure cores. The tests need no photos and no exiftool:

- `gallery_common`: `yaml_scalar` — the quoting rule for every scalar the writers emit (`" #"`, leading `-`, trailing space, `yes`/`no`, the two escapes); `source_name` — `_hu_<hash>` stripping, the untouched original included; `photos_dir_from_hugo_mounts` — the example file, a malformed pairing, a missing file; `license_aliases`.
- `gallery_xmp`: the record → fields mapping (a bag `dc:creator` joined, empties dropped). Needs one small refactor — the parsing moves out of `read()` into a pure `parse_records(json_text)` so it can be fed exiftool's JSON without exiftool.
- `gallery-embed-metadata`: `clip` against the IIM limits; `lang_values` and the `en` fallback; `photo_args` — **never `Orientation`**, no year when the capture year is unknown, `ColorSpace=sRGB` on variants only, clearnet URLs in every build; `build_argfile` is deterministic (same jobs → same bytes, twice); `load_manifests` merges three languages on `id` and refuses a file with no record. The script's name has dashes, so the tests load it with `importlib` from a tiny `tests/py/_load.py`.
- `dex_common`: the hand-written YAML subset. Round-trip `load → dump → load` over the real `data/dex.yaml` is equal; edge cases (flow lists, quoted scalars, per-language maps) as snippets. This is the parser every dex script trusts and it has never been exercised outside its happy path.
- `sync-gallery`: `find_images_block`, `build_stub`; `sync-steam` / `sync-epic` / `sync-gog`: the merge that rebuilds a platform block while leaving every other line byte-identical, and the human-field preservation keyed on `appid` / `appName` — against fixture JSON for the API responses, offline.

### L2 — static checks over the built site

This is the layer with the highest payoff per line, because the build output is the contract with the outside world and it is already on disk. The project reads `SITE_DIR` (default `.test-site`) and `SITE_BASE` (default `http://localhost:1414`) so the same checks run over `public/` with the production base URL from `deploy.sh`. Grouped:

*Data ↔ output.* Every `id` in `gallery.yaml` is a UUID and unique; every entry has a photo page in all three languages and every photo page maps back to an entry; the set of `data-id`s on `/gallery/general/` + `/gallery/archive/` equals the set of ids in `gallery-metadata.json` equals the set in the YAML, and the three manifests agree on `count` and on ids; every `species:` is a `scientific:` in `dex.yaml`; every `project:` slug is an album under `content/gallery/projects/`; every `featured_image` / `*_cover` / `photo_id` UUID exists; every `license:` is a key; i18n key parity across the three files; every dex record with `height` has `height_measure`; every `sightings` entry has numeric `lat`/`lng`.

*Models.* The section that landed after this was written, and the one place where a silent failure costs somebody other than the author. Four checks, all of them reading `data/models.yaml` against the built site: every `model:` slug in `gallery.yaml` has a record and every record's `visibility` is exactly `public`, `unlisted` or `hidden`; a **`hidden`** record's slug and — when it has one — its name appear **nowhere** under `SITE_DIR`, not in a page, a caption, a `data-` attribute, `index.json`, a feed or a path; an **`unlisted`** record's page resolves but its URL is in no `sitemap.xml`, no section feed and no `index.json`; a **`public`** record's page carries a `ProfilePage` JSON-LD whose `sameAs` holds exactly the record's `links` and no more. The `hidden` test is vacuous today — the file holds one record, `lukas-nagel`, `public` — and that is the reason to write it now rather than when it first matters. Note a `hidden` record may carry `slug:` and `visibility:` and nothing else, so the search is over the slug plus the name only if present.

*HTML.* No `localhost:1313`, `ZgotmplZ`, `map[`, `<no value>` or `%!` anywhere, and — when `SITE_BASE` is the production URL — no `localhost` at all (one legitimate `localhost` sits in the nginx-proxy-manager post body and is allow-listed by path); every `<img>` has `alt`; every internal `href`/`src`/`srcset` resolves to a file or an alias, and every `#fragment` on a gallery deep link matches a `data-id` on the target page; translated pages carry `hreflang` alternates; every `<script type="application/ld+json">` parses and has the `@type` its theme promises — `ImageObject` on `gallery-photo`, `WebPage` + `about.Taxon` on `dex-species`, `ImageGallery` on the list themes, `BlogPosting` on posts and **never** on a dex page (§ SEO in CLAUDE.md); `robotsNoIndex` pages carry `noindex`.

*Feeds and sitemap.* Every `index.xml` is well-formed XML; every item `<link>` and every URL in `content:encoded` is absolute and resolves; the sitemap lists no URL that does not exist and no adapter page with `<priority>0</priority>`; `security.txt` has an `Expires` in the future and less than a year out.

*URL stability.* `tests/golden/published-urls.txt` — every `<loc>` in the sitemap and every RSS item link, path only, committed. The test asserts each still resolves to a page **or an alias**. New URLs are appended by `npm run golden:update`; a URL may only *leave* the list in a commit that also adds its redirect, which is exactly the rule CLAUDE.md states for the gallery and RSS and nobody can currently check.

*Determinism.* Build twice, diff the HTML: identical. Blocked today by the `map` shortcode id (§1); a phase-1 fix.

### L3 — browser tests

**The matrix.**

| Project | Engine | Viewport | Runs |
|---|---|---|---|
| `firefox` | Playwright's Firefox build | 1280 × 800 | every scenario — **the primary browser**; a failure here is the one to look at first |
| `chromium` | Chromium | 1280 × 800 | every scenario |
| `webkit` | WebKit — Safari's engine, Playwright's Linux build; close to Safari, not Safari | 1280 × 800 | every scenario |
| `mobile-chrome` | Chromium, `Pixel 7` device descriptor | 412 × 915, touch | scenarios tagged `@mobile` |
| `mobile-safari` | WebKit, `iPhone 14` device descriptor | 390 × 844, touch | scenarios tagged `@mobile` |

Two engine differences the tests have to respect. Playwright cannot grant clipboard permissions outside Chromium, so the copy-link test asserts the button's `is-copied` state and label in every browser and reads the clipboard back only in `chromium`. And Firefox has no mobile emulation in Playwright, hence the two mobile projects on the other engines — which is also the honest choice, since the phones in question run Chrome and Safari.

**The scenarios.** One per behaviour the site hand-wires, starting with the ones that have a fix commit:

| Scenario | Asserts |
|---|---|
| Lightbox from the grid | click opens PhotoSwipe on the clicked photo; Escape closes; the info panel shows the **Species** row linked to the dex page and the **Edited with** row |
| Deep link `#<uuid>` | loading `/en/gallery/general/#<uuid>` opens that slide; **back** closes the viewer and stays on the gallery; swiping 5 slides then back costs one press (`lightbox.js:205`) |
| Filter bubbles | clicking a category hides every `.gallery-item` of another category; "all" restores |
| Photo page | prev/next stay within general or archive; copy-link marks the button copied (clipboard content asserted in Chromium) |
| Dex overview | search narrows, a group pill narrows, "photographed only" leaves only `data-caught="1"` cards, the empty state appears when nothing matches |
| Dex map | **no request leaves localhost on load**; land, range and sightings render at the three longitude copies; "detailed map" requests `tile.openstreetmap.org` and `api.gbif.org` (mocked, asserted) and nothing else |
| Language switcher | from a translated page lands on the translation, from an untranslated page on the other language's home |
| Feed | filter buttons hide the other kinds; a photo item's link jumps to the gallery and opens the lightbox on the right photo (the FNV hash contract in CLAUDE.md) |
| Gaming | sort by playtime / recent / A–Z reorders the tiles; the platform row appears only with two or more platforms |
| Search | typing finds a known post title |
| Newsletter form | submit posts to the mocked `data-api`; success and error states render; nothing goes to the network |
| Likes | the mocked companion returns a count; the heart toggles and posts once |
| Download dialog | opening from a grid item lists the size tiers and each row's `download` attribute equals the `data-download-name` Hugo wrote — the script computes no filename, so the test is that it did not start; Escape and a backdrop click close the native `<dialog>`; the per-tier HEAD requests go to `localhost` and nowhere else. On an `all-rights-reserved` photo the gate appears, a row click is cancelled while `aria-disabled="true"`, and ticking the box releases it. With JavaScript disabled the static card on the photo page still renders every link **ungated** — the property the module's comment calls the point of it, and the only one a JS test cannot see |
| Model page | a `public` record's page shows the name, the bio and the photo strip, and the **Model** row in the lightbox info panel links to it; an `unlisted` record's page is reachable by URL and absent from the `/gallery/models/` grid; the photo of a model with no record renders no row at all rather than a row built from the slug |
| Console | no `error`-level console message and no failed request on one page per theme |
| `@mobile` | at phone width the navbar and the gallery back link are visible and clickable — the two September fixes; the grid and the lightbox work with touch |

## 3. Tooling — build against reuse

| Need | Chosen | Named alternatives, and why not |
|---|---|---|
| Browser automation | Playwright (`@playwright/test`) | **Cypress**: runs inside the browser, weaker on multi-origin and network interception, slower, WebKit only experimental, no first-class mobile emulation. **Puppeteer**: Chromium-centred driver, not a runner — no assertions, retries, fixtures or report, and no Firefox parity. **WebdriverIO / Selenium**: would drive the *real* installed Firefox and Safari, but Safari does not exist on Linux and the setup is far heavier; Playwright's Firefox and WebKit builds are the pragmatic stand-ins |
| Playwright binding | Node | **Python Playwright**: the runner, `webServer`, project dependencies, auto-retrying `expect`, trace viewer and the HTML report are Node-only; Python gets `pytest-playwright` and hand-rolled orchestration — and the "one command, one report" requirement is precisely what the Node runner provides. The code under test is JavaScript anyway |
| Runner for everything else | the same `@playwright/test`, as browser-less projects (`build`, `python`, `static`) | **vitest / jest** for the static checks: a second runner and report. **pytest** for the Python: a pip dependency the scripts avoid on purpose. **A shell script** chaining the layers: no single report, no attachments, no skip-on-dependency |
| Generic HTML/link checking | own code in L2 (~100 lines; the probe in §1 ran in 0.9 s) | **htmltest** (Go, built for Hugo sites): checks links, `alt`, `hreflang`, doctype — but not `data-id` ↔ UUID, not manifest ↔ YAML, not `@type` per theme, not the golden list. The valuable half needs custom code regardless; a binary for the cheap half is a second tool for a hundred lines, outside the one report. **lychee / html-proofer**: same, plus Rust or Ruby. If external-link checking is ever wanted, `lychee` by hand, occasionally — never in the gate (§10) |
| Python tests | `unittest` | **pytest**: nicer, but `pip install` on every machine that runs the suite; the scripts' stdlib-only rule exists so they run anywhere |
| YAML in Node | `yaml` (2.9) | **js-yaml**: fine too; `yaml` keeps comments and positions, useful for error messages that name a line. **Reusing `dex_common`'s parser from Node**: no |
| Schema validation of `gallery.yaml` | none in phase 1 | **JSON Schema via `ajv`**: would express the per-entry shape (string-or-`{en,de,sv}`, `project` string-or-list, `license` enum) declaratively. Worth it once the shape stops moving; the cross-file invariants are code either way |
| Serving under test | `python3 -m http.server 1414 -d .test-site` — stdlib, already on the machine, serves `index.html` for directories and decodes `Ping%C3%BCino` | **`hugo server -e production -p 1414`**: writes to `public/` by default in this version and would clobber the deploy artefact; `--renderToMemory` avoids that at the price of holding the published images in RAM. **`serve` / `http-server` from npm**: fine, one more dependency for what the stdlib does. **A static server over `public/` itself**: the menu and about half of all internal links (595 of 1,191 on `/en/gallery/general/`) are absolute `.Permalink`s, so a click in the test would leave for `https://lna-dev.net` — the localhost base URL of the test build is what keeps them home |
| Report | Playwright's `list` reporter on the terminal + the `html` reporter, opening in the browser on failure | **Allure / JUnit XML**: for a CI dashboard that does not exist yet; JUnit can be added with one line when it does |

## 4. The photo problem, and the fixture environment — designed, not scheduled

Locally there is no problem: the store is mounted, the cache is warm, `hugo` takes 15 s, and every layer runs on the real 648 photos. The suite never clears the cache and never writes to the store.

For a machine without the photos — hosted CI, or a clean checkout — Hugo's environments do the work. `hugo -e test` reads `config/test/` on top of `config/_default/`, and a `config/test/module.yaml` with its own `mounts` list **replaces** the machine's list (replace-not-merge, the property CLAUDE.md warns about, here used on purpose):

```yaml
# config/test/module.yaml
mounts:
  - source: assets
    target: assets
  - source: tests/fixtures/gallery       # six to eight real photos
    target: assets/images/gallery
  - source: tests/fixtures/data          # gallery.yaml for exactly those photos
    target: data
  - source: data                         # everything else falls through
    target: data
```

Two mounts on one target are a union in which the earlier mount wins on a path collision, so the fixture `gallery.yaml` shadows the real one and `dex.yaml`, `licenseMap.yaml`, `reading.yaml` and the rest are read unchanged. **This precedence rule is the first thing to verify when this phase starts** — if Hugo resolves it the other way round, the fixture data dir has to carry copies of every data file instead. Processing eight photos cold takes seconds, so a fixture build is fully reproducible and cache-free. The fixture photos are real exports from the store with their metadata as they are — the same rule the imagemeta test fixtures followed — so that the embedding step's tests see real darktable XMP, a real `2000:01:01` clock and a real portrait orientation. Which photos is decided then; only 13 of the 648 files carry GPS, and those are simply not picked.

The tests do not know which data set they run on. L2 reads `SITE_DIR` and the YAML Hugo was pointed at (`SITE_DATA=tests/fixtures/data` when set); L3 talks to whatever is on port 1414. The assertions are the same; only the counts differ.

## 5. One command, one report

`npm test` is `npx playwright test`. The configuration has seven projects and two dependency edges:

```
python ──────────────────────────────────────────┐
build ──┬── static                               ├── one HTML report
        ├── firefox   chromium   webkit          │
        └── mobile-chrome   mobile-safari  ──────┘
```

- **`webServer`**: `mkdir -p .test-site && python3 -m http.server 1414 -d .test-site`, readiness on `/` (a directory listing answers 200 before the build exists, so the server is up in a second and never in the way).
- **`build`**: two tests. *"hugo builds without warnings"* runs the L0 command from §2 into `.test-site/`, attaches the complete log to the report and asserts exit 0 and no `WARN` line. *"hugo mod verify"*. Timeout 20 min for the cold-cache case.
- **`python`**: one test per module under `tests/py/`, each spawning `python3 -m unittest -v` on that module and attaching its output. No dependency on `build`; runs alongside it.
- **`static`** depends on `build`; the browser projects depend on `build`. When the build fails, the report shows one red test and forty skipped ones, not forty red ones.
- **Browser projects**: `firefox` is listed first so its failures lead the report. A global fixture installs the network policy on every context (`page.route('**/*', …)`: abort unless `localhost`, plus the test's allow-list), grants `clipboard-read`/`clipboard-write` in Chromium only, and registers the mocks for `companion.lna-dev.net` and the listmonk form. Traces on first retry, screenshot and video on failure. `retries: 0` locally, so flakiness is seen rather than hidden — revisit when there is data.
- **Report**: `list` on the terminal while it runs; `playwright-report/index.html` at the end, opened automatically when something failed (`open: 'on-failure'`); `npm run report` reopens the last one. Every test carries its attachments — Hugo's log, unittest output, the trace of a failed browser step — so the report is the whole answer, not a pointer to a terminal.

Production environment throughout: `head.html:246` gates the SEO partials on it and `head.html:282` points the travel page at the real companion instead of `localhost:8080` — which is what makes mocking honest: the page asks for `https://companion.lna-dev.net/api/…` and the test answers. Plausible, the companion, listmonk, GitHub's API for the projects page (a build-time fetch anyway, `projects/single.html:67`) never see a test run.

## 6. Where it runs

```
npm test              # everything; ~3–5 min on this machine, real data
npm run test:quick    # build + python + static, no browsers; ~20 s
npm run test:e2e      # firefox only
npm run report        # reopen the last HTML report
npm run golden:update # regenerate tests/golden/published-urls.txt after an intentional URL change
```

`deploy.sh` becomes:

```
npm test                                                               # all four layers, on .test-site/
hugo --panicOnWarning --printI18nWarnings --printPathWarnings          # the artefact, as today
SITE_DIR=public SITE_BASE=https://lna-dev.net \
  npx playwright test --project static                                 # the artefact itself, ~2 s
python3 scripts/gallery-embed-metadata.py && … --check && rsync        # as today

hugo -b "$ONION" --panicOnWarning …                                    # builds, or the deploy stops
embed, check, rsync                                                    # reachable is the requirement
```

The second `static` run is the guard §1 asked for: it looks at the very files rsync is about to ship, with the production base URL, and would have refused the development build that sat in `public/` on the day of writing. With `SITE_DIR` set, the `static` project drops its dependency on `build` — otherwise Playwright would rebuild `.test-site/` first. A failing step stops the script before anything is written to the server; `set -euo pipefail` is already there. The Tor build gets no tests: it has to come out of `hugo` and be served, which the existing `--check` and rsync already establish.

## 7. Cost

| | |
|---|---|
| L0 | 15.2 s warm (measured); the flags add nothing measurable; `hugo mod verify` < 1 s |
| L1 | < 1 s |
| L2 | ~2 s over 4,641 pages (the probe: 0.9 s for links, leaks, JSON-LD, `alt`) |
| L3 | estimated 2–4 min: ~15 scenarios in each of three desktop browsers plus the `@mobile` subset in two, spread over Playwright's parallel workers; the static server adds nothing |
| `npm test` | ~3–5 min end to end |
| Added to a deploy | `npm test` + the 2 s static run on `public/` → today's ~7.5 min become ~11–13 min |
| One-time | `npm install`; `npx playwright install firefox chromium webkit` ≈ 500 MB into `~/.cache/ms-playwright`; on Fedora possibly a `dnf` list for WebKit or the podman image (§ Still open). `node_modules` is already gitignored |
| Disk | `.test-site/` is a second copy of the site, ~8 GB, rewritten by every run — the same cost `public/` already pays per build; gitignored |
| In git | `package.json` + lockfile, `playwright.config.ts`, ~1,500 lines of tests, the golden URL list (~5,000 lines) |
| Ongoing | every intentional URL retirement touches the golden list; every new i18n key lands in three files or the build test fails; every new engine-specific quirk gets a one-line `test.skip` with the reason — all three are the point |

## 8. Build order

1. **Prerequisites, so the first run is green rather than a backlog.** Add the 7 Swedish keys named in §1. Make the paginator link absolute (`home.html:126`, `list.html:265`). Fix the two relative links in `content/posts/Projects/pixelfed-automation/index.en.md`. Replace `math.Rand` in `map.html` with `.Ordinal`. Promote the unknown-species `warnf` to `errorf`, or leave it and let the build test do it. None of these change any URL.
2. **The skeleton: `build` + `static`, one report.** `package.json`, `playwright.config.ts` with the `webServer`, the `build` project and the `static` project, `tests/support/site.ts` (read the site dir, the YAML and the manifests once per run), the L2 groups of §2 in the order listed, the golden list generated and committed. After this step `npm test` exists and produces the report. Verify: run twice, identical result; run with `SITE_DIR=public` over a deploy build.
3. **`python`.** The `parse_records` refactor in `gallery_xmp.py`, `_load.py`, the tests of §2. Verify against the real `dex.yaml` round trip.
4. **Browsers, Firefox first.** `npx playwright install firefox`, the network fixture, the mocks, the scenarios in the order of the table — the six with a fix commit first — all green in Firefox. Then `chromium` and `webkit` (here the Fedora question resolves itself), then the two mobile projects with the `@mobile` tag. Engine-specific skips are written down with a reason, never silently.
5. **`deploy.sh`.** The block in §6. Run one real deploy with it and time it.
6. **Fixtures and hosted CI** — §4, when wanted. Verify the mount precedence, choose the photos, `config/test/module.yaml`, `tests/fixtures/`, the workflow file.

Each phase is independently useful and stops at a working state; phases 1 and 2 alone would have caught everything in §1.

## 9. Files touched

### New

- `package.json`, `package-lock.json` — `@playwright/test`, `yaml`
- `playwright.config.ts` — projects `python`, `build`, `static`, `firefox`, `chromium`, `webkit`, `mobile-chrome`, `mobile-safari`; `webServer`; reporters
- `tests/build/hugo.spec.ts` — the L0 tests
- `tests/python/unittest.spec.ts` — the L1 bridge, one entry per module
- `tests/static/*.spec.ts` — the L2 groups of §2, one file each, `models.spec.ts` among them
- `tests/e2e/*.spec.ts` — one file per L3 scenario row
- `tests/support/site.ts`, `tests/support/network.ts`, `tests/support/mocks.ts`
- `tests/golden/published-urls.txt`
- `tests/py/_load.py`, `tests/py/test_*.py`
- phase 6: `config/test/module.yaml`, `tests/fixtures/gallery/`, `tests/fixtures/data/gallery.yaml`, `.github/workflows/test.yml`

### Modified

- `deploy.sh` — `npm test` first, `--panicOnWarning` on its own builds, the `static` run over `public/`
- `i18n/sv.yaml` — the missing keys
- `layouts/_default/home.html`, `layouts/_default/list.html` — the paginator link
- `layouts/shortcodes/map.html` — deterministic id
- `content/posts/Projects/pixelfed-automation/index.en.md` — two links
- `scripts/gallery_xmp.py` — `parse_records` split out of `read`
- `.gitignore` — `.test-site/`, `playwright-report/`, `test-results/`
- `CLAUDE.md`, `AGENTS.md` — a *Testing* section: the one command, what each project is, how to run one layer, how to update the golden list, how to record an engine-specific skip

## 10. Deliberately out of scope

- **Visual regression** (`toHaveScreenshot`). The pages are photographs; font rendering, HiDPI and image decoding make pixel diffs flaky for little return, and three engines would mean three baselines per page. If ever, then for chrome-only regions (navbar, filter row, lightbox toolbar) with a generous threshold — a later decision.
- **Accessibility audits** (`@axe-core/playwright`). Decided out for now; it would plug into the existing `page` fixture in an afternoon if wanted.
- **External link checking.** Network-bound and flaky; never in a gate. `lychee` by hand when curious.
- **Testing the Tor build beyond building it.** Reachability is the requirement and `deploy.sh` already establishes it; no clearnet-leak policy, no onion test pass.
- **Real Safari, real Firefox releases.** Playwright ships its own Firefox and WebKit builds; they track the engines closely but are not the browsers users install. Good enough for a personal site; a device lab is not.
- **Performance budgets / Lighthouse.** A different kind of monitoring; not a test that fails a deploy.
- **PaperMod's own templates.** Only what this repo overrides or wires is asserted; a theme bump is covered by L0's warnings and L2's output checks.
- **The companion API.** Its own repository; here it is mocked, and the contract the mock encodes (paths, shapes) is the one place a change there shows up.
- **The 3m40s embedding run inside the suite.** `--check` stays where it is, in deploy; L1 tests `photo_args` and `build_argfile` as pure functions, plus a two-file smoke run into a temp dir when exiftool is present.
- **The Nextcloud sync and the photo store.** Read-only in every layer, as everywhere else.

---

## 11. What was built, 2026-09-20

Phases 1 to 5 of §8, in one sitting. `npm test` exists, runs **201 tests in seven
projects** and produces one HTML report. On this machine: **195 passed, 6 skipped,
0 failed, 1m 0s** end to end with a warm cache — comfortably inside the 3–5 min
§7 budgeted, because the browser scenarios parallelise better than estimated.

| Layer | What runs | Result |
|---|---|---|
| L0 `build` | the §2 command into `.test-site/`, every `WARN` a failure, plus `hugo mod verify` | 2 tests, 12–15 s |
| L1 `python` | `unittest` over six modules, one report entry each | 7 tests / **96 assertions**, < 1 s |
| L2 `static` | the six groups of §2 | 62 tests, **2.4 s over the real 8 GB artefact** |
| L3 browsers | 15 scenario files in `firefox`, `chromium` and `mobile-chrome` | 130 tests, ~50 s |

The six skips are honest ones, not hidden failures: the `hidden` and `unlisted`
model checks are vacuous while `data/models.yaml` holds one `public` record, the
determinism check is `@slow` and skips when pointed at a foreign `SITE_DIR`, the
clipboard read-back is Chromium-only, and two scenarios skip where the fixture
they need is absent.

### What the first green run cost — eight real defects

Every one of these was found by writing the check, not by reading the code:

1. **1,944 photo pages had no hreflang cluster.** `translationKey` sat inside
   `params` in `gallery-photo-pages.html`, where Hugo ignores it — it is a
   top-level key of `.AddPage`, like `aliases` and `build`. Hugo then paired
   translations by path, which works on the dex and model adapters (their slug is
   language-neutral) and cannot work here, where the three languages have three
   different slugs by design. Every photo page in every language declared only
   itself. Moved to the top level in all three adapters, and L2 gained *"a page
   that exists in three languages declares all three alternates"*, scoped to the
   adapter pages — the weaker "has at least one alternate" check passed happily
   on a page that named only itself.
2. **Every RSS feed advertised a PNG as its own site.** `<image><link>` in
   `rss.xml` held the image URL; RSS 2.0 says it is the URL of the site and
   should match the channel's `<link>`. 114 feeds × 3 languages. (The fix needs
   `$.Permalink`, not `.Permalink` — inside `with site.Params.images` the dot is
   the images slice.)
3. **Twenty-one relative links in post bodies.** They resolve on the page and
   break in a feed reader, which renders the body on its own origin. Found by the
   `content:encoded` check, not by the link checker, which correctly saw them
   resolve. **The first fix was to write the language prefix into the content by
   hand; the author asked for the `../` spelling to keep working instead**, which
   is the better answer — so the resolution moved into
   `layouts/_markup/render-link.html`, where it belongs, and the content went
   back to `../`. `../x` and `/en/x` now render byte-identically (verified by
   diffing 120 resolved hrefs across the ten affected pages before and after).
   L2 gained *"no relative link survives out of rendered Markdown"*, scoped to
   `.post-content`. Three links in that set were not relative-notation at all but
   genuinely broken — `posts/media/fediverse/` and `tags/open-source/` were
   missing their root and resolved into the post's own directory, and
   `/tags/Kubernetes` had no language prefix and the wrong case — and those
   stayed content fixes.
4. **Two genuinely dead links**: `/tags/Kubernetes` (no language prefix, wrong
   case) and a screenshot that has not existed for as long as git remembers.
5. The **7 Swedish i18n keys** and the **relative paginator link** of §1, as
   planned, plus `math.Rand` in `map.html` — after which the determinism check
   passes and two builds of the same tree are byte-identical.

### Where the implementation departs from this design

- **Determinism is tagged `@slow`** and `npm run test:quick` excludes it: it runs
  a second full build into `.test-site-verify/` (~13 s, 8 GB, removed afterwards),
  which is more than the "~20 s" §6 promised for the quick lane.
- **The analytics script is stubbed, not blocked.** `extend_head.html` loads
  Plausible unconditionally, so it is on every page of every build — including
  the Tor one. Chromium logs an aborted request as a console error and Firefox
  does not, so blocking it would make the "no console error" scenario pass in one
  engine and fail in the other. It is answered with an empty script instead; the
  real service still never sees a test run. The dex-map scenario names the
  exception out loud rather than filtering it silently, because the claim that
  page rests on is that **no map data** comes from a third party — which holds.
- **The network allow-list is an option fixture wrapped in an object**
  (`test.use({ net: { allow: [...] } })`). Playwright's option fixtures use a
  `[value, options]` tuple and a bare `RegExp[]` is ambiguous with it.
- **L3 needs one wait that is not obvious.** PhotoSwipe does its wiring — the
  keyboard listener, the heavy image, the close path — in `openingAnimationEnd`,
  not in `open`. Both `.pswp--open` and `.pswp--ui-visible` appear well before
  that, so a test that acts as soon as the viewer looks open has its click or key
  press swallowed, which reads exactly like a broken lightbox. `openLightbox()`
  in `tests/support/fixtures.ts` waits for the placeholder image to be swapped
  for the real one, which is the first thing that handler does. **This cost an
  hour and produced a convincing false bug report; it is written down here so it
  costs nobody else one.**

### One thing this found that is a decision, not a defect

**The language switcher always points at the language home**, on every page —
including pages that are fully translated, photo pages included. §2 assumed
"from a translated page it lands on the translation, from an untranslated page on
the other language's home"; only the second half is true. `tests/e2e/language.spec.ts`
asserts the shipped behaviour and says so in a header comment, and it separately
asserts that the translation *is* reachable through the hreflang alternate (which
it now is — finding 1). Teaching the switcher to follow `.Translations` is a
product decision, not a bug fix, and was left to the author.

### Files

Everything §9 lists, with these differences: `tests/python/unittest.spec.ts` is
the L1 bridge (one test per module), `tests/golden/collect.mjs` is shared by the
golden-list test and `npm run golden:update` so the two cannot disagree about
what counts as published, and `tests/support/fixtures.ts` holds the `probe`
fixture (network policy, console errors, failed requests) that every scenario
uses. `tests/golden/published-urls.txt` has **2,587 URLs**.
