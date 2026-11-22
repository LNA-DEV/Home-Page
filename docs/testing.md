# Testing

`npm test` — one command, four layers, one HTML report (~1 min warm). It is the
gate in `deploy.sh`. Design: `docs/concepts/testing.md`; full workflow and the
traps: *Working with the tests* below. The short version:

- Seven Playwright projects: `build` (Hugo, **every `WARN` a failure**),
  `python` (stdlib `unittest` over `scripts/`), `static` (the built site: data ↔
  output, links, JSON-LD, feeds, sitemap, URL stability, image URLs, model
  visibility), and
  the browsers `firefox` / `chromium` / `mobile-chrome`. `webkit` and
  `mobile-safari` are opt-in (`WEBKIT=1`) — Playwright's WebKit does not run on
  Fedora as shipped.
- **The build under test is `.test-site/`, never `public/`.** `public/` is
  written only by `deploy.sh`.
- **A warning blocks a deploy.** Loosen it through Hugo's `ignoreLogs` in
  `hugo.yaml`, keyed by warning id, never by weakening a test.
- **A new published URL needs `npm run golden:update`**, and a retired one may
  only leave `tests/golden/published-urls.txt` in the commit that adds its
  redirect. This is the URL-stability rule of the gallery and of RSS (`docs/site.md`), and
  nothing could check it before.
- **No test reaches the network**: the companion API (map tiles included) and
  listmonk are mocked; everything else off localhost is aborted, which is itself
  the assertion every map rests on.
- **A literal colour, spacing length, font size, radius, shadow or off-set
  breakpoint fails the suite.** `tests/static/design-tokens.spec.ts` counts them
  per file against `tests/golden/css-literals.json` (at zero); see
  `docs/design-system.md` and `npm run tokens:ratchet`.

## Working with the tests

One command, one report. `docs/concepts/testing.md` is the design; §11 of it is
what the first run found and where the implementation departs from the plan.

```
npm test              # everything: build + python + static + browsers, ~1 min warm
npm run test:quick    # build + python + static, no browsers, no determinism
npm run test:e2e      # firefox only
npm run report        # reopen the last HTML report
npm run golden:update # after an INTENTIONAL URL change — see below
```

First time on a machine: `npm install` and `npx playwright install firefox chromium`.

### The seven projects

| Project | What it is | Needs the photos |
|---|---|---|
| `build` | `hugo -e production -b http://localhost:1414 -d .test-site` with **every `WARN` treated as a failure**, plus `hugo mod verify` | yes |
| `python` | `python3 -m unittest` over `tests/py/`, one report entry per module | no |
| `static` | the checks over the built site — data ↔ output, links, JSON-LD, feeds, sitemap, URL stability, models | reads the build |
| `firefox` | **the primary browser**; a failure here is the one to look at first | yes |
| `chromium` | the same scenarios | yes |
| `mobile-chrome` | the `@mobile` subset on a Pixel 7 | yes |
| `webkit` / `mobile-safari` | **opt-in**, see below | yes |

`static` and the browser projects depend on `build`, so a failed build is one red
test with Hugo's log attached and everything downstream is skipped.

### Things that will bite you

- **A warning fails the build test.** That is deliberate: it is what turns an
  unknown `species:`, an empty gallery mount or a PaperMod deprecation into a
  stopped deploy. The escape hatch for a warning that is genuinely somebody
  else's problem is Hugo's `ignoreLogs` in `hugo.yaml`, keyed by the warning id,
  so an ignore is visible and reviewable — never a loosened test.
- **`.test-site/` is the build under test, never `public/`.** `public/` is
  written only by `deploy.sh`. Both are gitignored; `.test-site/` is another full build of several GB.
- **A new i18n key lands in all three files or the suite fails** — in L0 as a
  Hugo warning and in L2 as a key-parity failure. That is the point.
- **A new page means `npm run golden:update`.** The golden list is append-only by
  construction: the script unions the current build with what is committed and
  never drops a line. A URL may only *leave* `tests/golden/published-urls.txt` in
  the same commit that adds its redirect — an alias on the page that replaced it,
  or an entry in that photo's `slugAliases:`.
- **Run `npm run golden:update` only on an otherwise green build.** It records
  whatever the build publishes, so a URL that exists only because of the bug that
  is failing the suite lands in the list, and getting it out again is a manual
  edit and the owner's call.
- **Nothing reaches the network.** Every request to a host other than localhost
  is aborted; the companion API (map tiles included) and listmonk are mocked, and
  the analytics script is answered with an empty stub (blocking it makes Chromium
  log a console error that Firefox does not). If a scenario needs a third party, it
  asks for it by name with `test.use({ net: { allow: [...] } })`.
- **Writing a lightbox scenario? Use `openLightbox()` from
  `tests/support/fixtures.ts`.** PhotoSwipe wires the keyboard and the close path
  in `openingAnimationEnd`, which is well after `.pswp--open` appears — act too
  early and the click or key press is swallowed, which looks exactly like a bug
  in the site. That helper waits for the right moment.
- **WebKit does not run on Fedora as shipped.** Playwright's build links
  `libicu*.so.74` and `libjpeg.so.8`; Fedora has ICU 77 and `libjpeg.so.62`, and
  `playwright install-deps` only knows apt. Run it in the container:
  ```
  podman run --rm --network=host -v "$PWD":/w -w /w \
    mcr.microsoft.com/playwright:v1.63.0-noble npx playwright test --project webkit
  ```
  or `WEBKIT=1 npm test` once the libraries are present. It is out of the default
  run on purpose: a suite that is red every time teaches people to ignore red.
- **An engine-specific skip is written down with its reason**, never left silent
  — see the clipboard read-back in `tests/e2e/photo-page.spec.ts`.

### Adding a Python test

`tests/py/test_*.py`, stdlib `unittest`, no pytest — the scripts are stdlib-only
so that any machine with `python3` can add a photo, and their tests keep that
property. `from _load import load` imports a script whose filename has dashes
(`load("sync-steam")`); the dashless modules import by name. The bridge picks up
new `test_*.py` files automatically.

### Where the deploy gate sits

`deploy.sh` runs `npm test` first, then its own `hugo --panicOnWarning`, then the
`static` project **once more over `public/`** with the production base URL — the
one check that can catch a stale or development build in the artefact itself —
and only then embeds metadata, checks and rsyncs. `set -e` means a failure at any
step stops the script before anything reaches the server.

## Checking a change by hand

- **`npm test` runs only when the owner asks for it.** A routine data edit does
  not call for the full suite. When only the golden URL list needs updating (a
  photo title changed, say), run the `build` project, which builds
  `.test-site/`, then the update: `npx playwright test --project build` and
  `npm run golden:update`.
- **Mind the RAM.** Never start a full-site `hugo server` to look at a page: on
  2026-10-06 one was OOM-killed on the 15 GB machine and took VS Code with it.
  For a visual check, serve the `.test-site/` the `build` project already made
  (`python3 -m http.server <port>` inside it) and send
  `https://companion.lna-dev.net/*` to a local companion through Playwright's
  `page.route`. One headless browser at a time, closed right after; check
  `free -m` before anything heavy.
- **Never verify against the owner's dev server or an existing `public/`.** The
  owner usually has `hugo server` running on :1313. Its watcher does not always
  re-render pages after a layout file is *created*, so it can serve the old HTML
  for a change that works. And `hugo server` writes to `public/` by default, so
  `public/` may hold a development build (`localhost:1313` links, no Open Graph,
  no JSON-LD — `head.html` emits those in production only). Build it yourself, into
  `.test-site/` or a scratch directory. Never kill hugo processes broadly — the
  owner's server is a working tool; stop only your own.
- **The Claude-in-Chrome window is often in the background** on the owner's
  machine. Then `document.visibilityState` is `hidden`, screenshots time out after
  30 s, and IntersectionObserver and animations do not run (lazy maps are not
  built, PhotoSwipe does not close), while `javascript_tool` still works. Check
  `visibilityState` before the first screenshot; if it is `hidden`, ask once to
  bring the window forward instead of retrying in a loop, and meanwhile use
  headless Playwright against `.test-site/`. A real scroll (the `computer` scroll
  action) wakes IntersectionObserver where a JavaScript scroll does not.
  `notification.js` registers a service worker, so pages can come back stale
  after a rebuild: bust the cache with `?v=N` or `fetch(url, {cache: "reload"})`.
