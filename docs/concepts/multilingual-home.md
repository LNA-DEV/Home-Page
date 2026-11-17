# Concept: the other languages' posts on every home page

**Status:** proposal, 2026-11-17. Nothing is built. The open decisions are listed at the end.
**Read against:** the working tree of 2026-11-17 (`24d9c58`), 22 post files. The Hugo techniques in §3–§5 were checked on a scratch site with Hugo 0.166.0 (§3, *Verified*). The full site was not built: this container has no photo store and no Dart Sass.

Each language home lists only posts in its own language. The site writes **different posts in different languages**: 18 of 20 posts exist in one language only. So each home hides most of the site, and the home a visitor lands on can look abandoned while another language is active. The only hint today is one hand-written sentence in each home's intro.

The proposal has three layers. Only the first is required, and each later one builds on the one before:

1. **Static, for everyone** (§3): a clearly labelled block on every home (and on `/posts/`) listing the newest posts that exist **only** in the other languages. Every visitor and every crawler gets the same HTML.
2. **Browser language, without moving anything** (§4): one inline line in `<head>` writes the visitor's languages onto `<html>` before first paint. CSS then puts the groups the visitor can read first and shows a "this page is also in German" bar. The HTML does not change, nothing shifts after paint, and nothing is hidden from a crawler.
3. **The domain root only** (§5): `/` sends a visitor to the home in their language instead of always to `/en/`. No content URL ever redirects.

---

## 1. What the data says

| | en | de | sv |
|---|---:|---:|---:|
| posts | 13 | 6 | 3 |
| of those, in this language only | 11 | 4 | 3 |
| newest post | 2026-03-02 | **2026-11-04** | 2024-12-07 |

Only two posts are translated: *Fedodo* and *Fediverse* (en + de).

What each home lists today (`.Paginate $pages 3`, own language only):

| home | the three posts it shows | not reachable from this home |
|---|---|---|
| `/en/` | 2026-03, 2025-09, 2025-05 | the **three newest posts on the site** (de: 2026-08, 2026-10, 2026-11), and all of Swedish |
| `/de/` | 2026-11, 2026-10, 2026-08 | 11 English-only posts, all of Swedish |
| `/sv/` | 2024-12, 2024-06, 2024-01 | everything since 2024 |

The English home, which is `x-default` and where `/` sends everyone, has had no new post for eight months, although the site published three in that time.

The other ways into the content are per-language too:

- `/posts/`, the RSS feed and the site search (`layouts/_default/index.json` ranges `site.RegularPages`, the current language only). Searching for *Eislotus* on `/en/search/` finds nothing.
- The language switcher in the header (`header.html`, PaperMod's own behaviour) always links to the **other home**, even on a post that has a translation. Only the "Translations:" line in the post meta links the translation.
- `/` is Hugo's default-site redirect: a `noindex` meta refresh to `/en/`, whatever the visitor's language.
- **`/feed/` is the exception.** It already merges all three languages with flags (`lang.Merge`), which shows that a mixed list works on this site as long as it is a separate page.

## 2. The SEO ground rules

These rules shape the design. They follow Google Search Central's guidance on multilingual sites (links at the end). The pages could not be fetched from this container, so the wording below is a summary, not a quote.

1. **One language per page for content and navigation.** Google decides a page's language from its **visible text**. The `lang` attribute does not count for that. So the English home has to stay clearly English: the other languages' posts go into a separate, labelled block of links below the English list, never into the main list.
2. **Never redirect a language URL by the visitor's language.** Googlebot mostly crawls from US addresses and without an `Accept-Language` header. A `/de/…` URL that redirects English-speaking clients would be crawled as English or not at all, and a shared link would land somewhere else. The only URL that may choose a language is `/`. It is not a content page: it is `noindex`, and its canonical is `/en/` (§5).
3. **Use `hreflang` only between equivalent pages.** The home pages form one cluster with `x-default` = `/en/`, and that stays as it is. A link from the English home to a German-only post is an ordinary internal link, not an alternate.
4. **Send everyone the same HTML.** Personalisation may only reorder or reveal what is already in the page. Different content for a crawler than for a visitor would be cloaking.
5. **No placeholder pages** such as "this post is only available in German" in the other languages. That would be thin content, an alternate pointing at a page that is not equivalent, and three times the URLs.
6. **Cross-language internal links help.** The three homes are the site's strongest pages. Today a new German post is linked from `/de/` only. With §3 it is linked from all three homes, so it is found and crawled sooner.

## 3. Layer 1 — "Also in other languages", static

### Where

- **Every home, page 1 only**: after the own-language list and its "All posts »" link, before the photo strip.
- **`/posts/`, page 1 only**: the "All posts »" link leads there, so that is where a reader who wants more goes next.
- Not in the home's RSS, JSON-LD or sitemap. **No new URL.**

### What

- For each other language (by `weight`): its **3 newest posts that have no translation in the page's language**. A translated post is already in the own-language list. `hiddenInHomeList` is respected. A language with nothing to show is left out, and if every language is left out there is no block.
- Each entry has the title in its own language, the date in the page's language and format, and a flag. Whether to add the description or a cover thumbnail is an open decision (D1).
- Below each group is a count link written in the page's language, for example *"All 6 posts in German →"* to `/de/posts/`. Last comes a link to `/feed/`: *"Everything in one timeline →"*.
- The heading and labels are in the **page's** language, from i18n. Only the titles are in the other language. That keeps the amount of foreign text small, as rule 1 requires.

### Markup

```html
<section class="lang-more" aria-labelledby="lang-more-title">
  <h2 id="lang-more-title" class="home-header">Also on this site in other languages</h2>
  <div class="lang-more-group" data-lang="de">
    <h3><span aria-hidden="true">🇩🇪</span> Only in German</h3>
    <ul>
      <li>
        <a href="/de/posts/books/feuerlilie-liza-grimm-review/" hreflang="de" lang="de">Feuerlilie von Liza Grimm: Rezension &amp; Zusammenfassung</a>
        <time datetime="2026-11-04">November 4, 2026</time>
      </li>
      …
    </ul>
    <a class="lang-more-all" href="/de/posts/" hreflang="de">All 6 posts in German →</a>
  </div>
  <div class="lang-more-group" data-lang="sv">…</div>
</section>
```

- `lang` goes on the link only, not on the `<li>`, because the date belongs to the page's language. With `lang`, a screen reader reads a German title with a German voice, and the browser's translate feature can tell what is foreign. `hreflang` on `<a>` is valid HTML and states the language of the target.
- The groups are flex items, so §4 can reorder them with CSS `order` without touching the DOM.

### Verified (scratch site, Hugo 0.166.0)

- `range site.Home.Translations` → `.Site.RegularPages` returns the other languages' pages from inside one language's build. This is the same pattern `layouts/feed/list.html` already uses.
- `range .Translations` + `eq .Lang $lang` correctly excludes a translated post. On the English home, *A de* (which has an English twin) is excluded and *B de only* is listed.
- The translation's `.Site.Params` holds **that** language's params. §4 needs this for its text (below).

## 4. Layer 2 — the browser language, decided before first paint

### The script

`head.html` already sets `js` on `<html>` with an inline script before first paint (for the newsletter). One more line goes next to it:

```js
// navigator.languages ∩ {en, de, sv}, in the visitor's order; plus a stored choice
try {
  var s = ["en","de","sv"], r = [];
  (navigator.languages || [navigator.language || ""]).forEach(function (l) {
    l = String(l).slice(0, 2).toLowerCase();
    if (s.indexOf(l) > -1 && r.indexOf(l) < 0) r.push(l);
  });
  var c = localStorage.getItem("lang-choice");          // set by the switcher, §6a
  var d = document.documentElement;
  d.dataset.reads = r.join(" ");
  d.dataset.top = c || r[0] || "";
  if (localStorage.getItem("lang-hint-dismissed")) d.dataset.hintDismissed = "";
} catch (e) {}
```

Everything else is CSS on those attributes. Nothing is moved in the DOM, so there is no layout shift. The attributes exist before the first frame, so there is nothing to flash.

### On the home: what the visitor reads comes first

```css
.lang-more { display: flex; flex-direction: column; }
html[data-reads~="de"] .lang-more-group[data-lang="de"] { order: -1; /* + accent */ }
html[data-reads~="sv"] .lang-more-group[data-lang="sv"] { order: -1; }
html[data-reads~="en"] .lang-more-group[data-lang="en"] { order: -1; }
```

Groups in languages the visitor does not read stay visible in their normal place. The whole point is to show that there is more, and hiding them would also give a crawler a different rendered page.

### The hint bar: "this page is also in German"

- Rendered by the server **for each translation the page has**: every home, and every translated post. Each bar is written in its target language, for example *"🇩🇪 Diese Seite gibt es auch auf Deutsch →"* linking to the translation. The text comes from the translation's `.Site.Params.langHint` (verified, §3), because a page's i18n reaches only its own language.
- The bars are hidden by default. CSS shows one when it is in the visitor's first language: `html[data-top="de"]:not([data-hint-dismissed]) .lang-hint[data-lang="de"] { display: flex }`. The page's own language never has a bar, so no further condition is needed.
- The bar has a ✕ that stores `lang-hint-dismissed`. Using the switcher stores `lang-choice` (§6a), and from then on that choice counts instead of the browser language. Both go in `localStorage`, read and written inside `try` blocks, so a blocked storage just means the bar comes back next time.
- An untranslated post shows no bar. There is nothing equivalent to offer, and the §3 block on the home handles that case.

### Why this is safe for SEO

- The HTML is identical for every client. Googlebot renders with `en-US`, so it sees the static order, and the hidden bars are only a few words of link text, about what the language switcher already says.
- Without JavaScript (Tor Browser at *Safest*) nothing changes. With JavaScript, Tor Browser reports `en-US` anyway (`privacy.spoof_english`), so the Tor build behaves like an English browser and gives away nothing about the visitor.

## 5. Layer 3 — `/` picks the home

**Today:** Hugo writes `/index.html` through `layouts/alias.html` (`renderDefaultSiteRedirect` in `hugolib/site_render.go`). On the scratch site the template's `.Page` is the English home with `.IsHome` = true. No other alias targets a home (there is no `content/_index.*`), so `{{ if and .Page .Page.IsHome }}` picks out exactly this one file.

**Proposal:** add a branch to `alias.html` for that case:

```html
<link rel="canonical" href="https://lna-dev.net/en/">
<meta name="robots" content="noindex">
<script>
  try {
    var c = localStorage.getItem("lang-choice"), r = (navigator.languages || []).map(…);
    location.replace("/" + (c || first of r in [en, de, sv] || "en") + "/");
  } catch (e) { location.replace("/en/"); }
</script>
<noscript><meta http-equiv="refresh" content="0; url=https://lna-dev.net/en/"></noscript>
<!-- body: the three homes as plain links, for the moment before the jump -->
```

- Without JavaScript and for crawlers the result is the same as today: `/en/`, `noindex`, canonical `/en/`. `x-default` stays `/en/`. A redirecting home page is the case `x-default` was introduced for, and that cluster does not change.
- The root uses the same stored choice as §4. Someone who picked English in the switcher keeps getting English from `/`, even in a German browser.
- **Alternative:** an nginx `map $http_accept_language` that answers `/` with a 302, plus `Vary: Accept-Language`. That saves one hop and works without JavaScript. But it lives in `../Web-Services`, it needs a cookie instead of `localStorage` for the stored choice, and it adds a second repository to every change. Recommendation: build it in this repo first, and move to nginx only if the hop is ever noticeable.
- **Swedish** is learner content (*"jag är nybörjare"*). A Swedish browser would land on `/sv/`. With §3 that home lists the newest English and German posts too, so it is a complete entrance and explains the setup in Swedish. Whether Swedish browsers should go to `/en/` instead is open decision D5.

## 6. Smaller changes in the same direction (optional)

- **a) The switcher goes to the translation.** On a page with a translation, link to that translation; otherwise, to the other language's home, as today. Clicking it stores `lang-choice`. This is a small change to `header.html`, and it makes the switcher agree with the hint bar.
- **b) Search across languages.** Add the other languages' posts to each language's `index.json` with a `lang` field, and show a flag in the results. This has no SEO effect, because the search runs in the browser. It needs a `fastsearch.js` override. Later, if wanted (D6).
- **c) The intro sentence.** Once §3 shows the other languages, the hand-written *"Keep in mind that I post different content in different languages"* in each home's `homeInfoParams` can go or become shorter (D7).

## 7. Rejected

| Idea | Why not |
|---|---|
| One merged, mixed-language list as the home's main list | Weakens the page's language signal (rule 1), and an English visitor would meet German titles first. `/feed/` already offers the mixed view as a separate page |
| Server-side language negotiation on content URLs | Rule 2: crawlers would see only one language, and shared links would break |
| Placeholder pages for missing translations | Rule 5 |
| Machine-translated posts or summaries | The site writes different posts per language on purpose, and unreviewed automatic translation is a quality risk |
| Hiding the groups a visitor does not read | It goes against the goal, and crawlers would render a different page |
| `hreflang` from a home to another language's posts | Rule 3: they are not equivalents |

## 8. Tests

- **static** (`tests/static/multilingual-home.spec.ts`):
  - every home page 1 and `/posts/` page 1 has the block, and no entry is in the page's own language;
  - no entry has a translation in the page's language;
  - every entry links to a built page whose `<html lang>` equals the link's `hreflang` and `lang`;
  - each count link's number equals the number of posts on the target list;
  - the block is not in the RSS, the JSON-LD or the sitemap;
  - the hint bars exist exactly for the page's translations and are hidden without the `data-top` attribute;
  - `/index.html` keeps `noindex` and the canonical `/en/`.
- **e2e:** Playwright's `locale` option sets `navigator.languages` and `Accept-Language`.
  - `de-DE` on `/en/`: the German group comes first and the German bar is shown;
  - `en-US`: no bar;
  - ✕ keeps the bar away after a reload;
  - a switcher click wins over the browser language;
  - `/` with `sv-SE` lands on `/sv/`;
  - the no-JS project gets `/en/` and the static order;
  - layout shift on the home is 0.
- **Golden URLs:** unchanged. There is no new URL, unless D1 adds cover thumbnails, whose variants would need `npm run golden:update`.

## 9. Build order

1. §3, the block on the homes and `/posts/`: i18n, CSS and static tests. This is useful on its own.
2. §6a, the switcher, so that `lang-choice` exists.
3. §4, the head line, the CSS and the hint bar, with e2e tests.
4. §5, the root page.
5. Optionally §6b and §6c.

## 10. Files

- **New:**
  - `layouts/partials/lang-more.html`
  - `layouts/partials/lang-hint.html`
  - `assets/css/extended/lang-more.css`
  - `tests/static/multilingual-home.spec.ts`
  - `tests/e2e/multilingual-home.spec.ts`
- **Changed:**
  - `layouts/_default/home.html` and `layouts/_default/list.html` (the `/posts/` page);
  - `layouts/partials/head.html` (one inline line next to the `js` class);
  - `layouts/partials/header.html` (§6a);
  - `layouts/alias.html` (§5);
  - `hugo.yaml` (`langHint` under each `languages.<lang>.params`);
  - `i18n/{en,de,sv}.yaml`;
  - `CLAUDE.md` and `AGENTS.md`.

## Open decisions

| | Question | Recommendation |
|---|---|---|
| D1 | What each entry shows: title + date only, plus description, or plus cover thumbnail? | Title + date. A cover is language-neutral and attractive, but it adds variants and golden URLs |
| D2 | How many entries per language? | 3 |
| D3 | The hint bar: homes only, or translated posts too? | Both |
| D4 | `/`: client-side in this repo, nginx, or leave it? | Client-side (§5) |
| D5 | Send Swedish browsers from `/` to `/sv/`? | Yes, consistently. With §3, `/sv/` shows everything |
| D6 | Search across languages (§6b)? | Later |
| D7 | Keep the hand-written intro sentence? | Shorten it once §3 is in |

## Sources

- Google Search Central, [Managing multi-regional and multilingual sites](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites): no automatic redirect by perceived language, page language from visible content, links between language versions.
- Google Search Central, [Tell Google about localized versions of your page](https://developers.google.com/search/docs/specialty/international/localized-versions): `hreflang`, `x-default`.
- Google Search Central Blog, [Introducing x-default hreflang](https://developers.google.com/search/blog/2013/04/x-default-hreflang-for-international-pages), [Creating the right homepage for your international users](https://developers.google.com/search/blog/2014/05/creating-right-homepage-for-your) and [How x-default can help you](https://developers.google.com/search/blog/2023/05/x-default): redirecting or selector home pages use `x-default`.
- Google Search Central Blog, [Crawling and indexing of locale-adaptive pages](https://developers.google.com/search/blog/2015/01/crawling-and-indexing-of-locale): Googlebot crawls without `Accept-Language`, from US addresses by default.
