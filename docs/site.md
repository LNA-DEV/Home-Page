# Site features

## Software projects page (different from gallery projects)

`content/projects/index.{en,de}.md` lists the user's software projects in front-matter (`projects:` array). Rendered by `layouts/projects/single.html`, which fetches live GitHub stats per repo/org via `resources.GetRemote` against the GitHub API (allowed by the `security.http.urls` whitelist in `hugo.yaml`). Don't confuse these with gallery `projects/` (photo series).

## Activity feed

`content/feed/_index.*` + `layouts/feed/list.html` builds a unified activity timeline by merging:
1. All `RegularPages` in the `posts` section across all languages (`lang.Merge`),
2. Photos from the gallery headless bundle (filtered to non-archive, dated >2000),
3. Talks from `data/talks.yaml`.

Items are grouped by year/month and filterable client-side. Photo permalinks use `#<uuid>` so they jump to the right gallery item — `gallery.html` writes the matching `data-id` attribute. Keep the two consistent if you change either side.

## RSS

Custom `layouts/_default/rss.xml`. The gallery overhaul preserves RSS URL stability — when moving images around, generate redirects rather than breaking old item links.

## security.txt

- `security.txt` (RFC 9116) is **generated, not static** — `layouts/_default/home.securitytxt.txt` plus the `securitytxt` output format in `hugo.yaml`. It was a static file whose `Expires` sat four months in the past before anyone noticed; generating it refreshes the date on every build (build day + 1 year - 1 day, so it stays inside the RFC's "less than a year" recommendation, truncated to whole days so rebuilds are byte-identical). Two things are load-bearing: the format's `path` is `../.well-known` because `path` resolves relative to the **language** directory and the file must sit at the domain root, and it is listed under `languages.en.outputs.home` **only** — putting it in the top-level `outputs` makes all three languages write the same target path. `Canonical` uses `absURL`, so the Tor build in `deploy.sh` emits the onion URL instead of the clearnet one. Do not re-add `static/.well-known/security.txt`; a static file of the same name would collide with the generated one.

## i18n

UI strings in `i18n/{en,de,sv}.yaml`. Per-language menus, descriptions, and home content live under `languages.<lang>.params` in `hugo.yaml`. Content files use `index.<lang>.md` for branch bundles and `_index.<lang>.md` for sections.

### The other languages: a block, a bar and the root page

Design: `docs/concepts/multilingual-home.md`. The site writes **different posts in different languages** (most exist in one language only), so each home used to hide most of the site. Three layers fix that, and none of them ever redirects a content URL by the visitor's language or sends a crawler different HTML:

- **The block** (`layouts/partials/lang-more.html`, on page 1 of every home and of `/posts/`): per other language, its 3 newest posts that have **no translation in this page's language**, with a count link to that language's `/posts/` and a link to `/feed/`. Headings and labels come from this page's i18n (`lang_more_*`); only the titles are foreign, each with `lang` and `hreflang`. No foreign descriptions, ever: they would blur the page's language for Google (§8). Membership mirrors `home.html`'s list (`mainSections`, `hiddenInHomeList`). **Translating a post takes it out of that language's block**; nothing else is needed (`docs/posts.md`).
- **The browser language** (§4): an inline script in `head.html`, next to the `js` class, sets `data-reads` (the site languages the browser lists) and `data-top` (the language picked in the switcher, else the first of `data-reads`) on `<html>` **before first paint**. `assets/css/extended/lang-more.css` does the rest: the visitor's group comes first (`order: -1`, a 2px `--primary` border with the padding shrunk by 1px so nothing changes size), and **the hint bar** in `data-top` shows. The bars (`layouts/partials/lang-hint.html`, rendered by `header.html` right after `</header>`) exist for every translation of every page, hidden by default; each is written in its target language from that translation's **`.Site.Params.langHint`** (`home`, `homeLink`, `page`, `pageLink`, `close` under `languages.<lang>.params` in `hugo.yaml`) — i18n cannot be used, it reaches only the page's own language. `assets/js/lang-hint.js` (every page, deferred) stores `lang-choice` when a `data-lang-choice` link is clicked (switcher, bar) and `lang-hint-dismissed` on the ✕. Two rules are hard, each with an e2e test: **no layout shift** (nothing is inserted or moved by a script after paint) and **the bar is never an overlay** (normal flow, at most 120 px on a phone).
- **The switcher** (`header.html`) links the page's translation where there is one, else that language's home.
- **The root page** (§5): `/index.html` comes from `layouts/_default/home.rootpicker.html` through the `rootpicker` output format (English home only, `path: ".."`, like `securitytxt`), with **`disableDefaultLanguageRedirect: true`** switching Hugo's own root redirect off. It jumps to `lang-choice`, else the first site language the browser lists, else `/en/`; without JavaScript and for crawlers it is still a `noindex` meta refresh to `/en/`, canonical `/en/`, and `x-default` stays `/en/`. **Never do this in `layouts/alias.html`**: Hugo writes the `/<lang>/page/1/` redirects through that template with the same context as `/`, so a branch there would turn `/de/page/1/` into a language picker.
- **The language list is written out in five places**: the two inline scripts (`head.html`, `home.rootpicker.html`), the two `$flags` dicts (`lang-more.html`, `lang-hint.html`) and the attribute selectors in `lang-more.css`. A fourth language needs all five, plus `langHint` and the `lang_more_*` keys (every key in all three i18n files, the self-language ones included, for the parity test).
- If the nginx config (in `../Web-Services`, `docs/build-deploy.md`) ever sends a `Content-Security-Policy` that allows inline scripts only by hash, the two inline scripts need theirs; nginx must also not answer `/` itself.
- Tests: `tests/static/multilingual-home.spec.ts` (the block against `content/posts/`, every page's bars and switcher against its hreflang alternates, the root page and the `page/1` redirects) and `tests/e2e/multilingual-home.spec.ts` (per browser language; the no-shift test serves `/css/cantarell.css` empty, because Cantarell's swap shifts the header a little on every page, bar or no bar — blocking only the font file is not enough where Cantarell is installed system-wide (Fedora/GNOME): Chrome then swaps to the local font after the web font fails — and it runs in Chromium only, the one engine that reports layout shifts).
