# Concept: the other languages' posts on every home page

**Status:** **implemented 2026-11-18**, all three layers and §6a/§6d; §6b (search across languages) and §6c (the intro sentences) are left for later. Proposal of 2026-11-17, revised 2026-11-18 after review: the revision corrected §5 (the first plan would also have rewritten the `/<lang>/page/1/` redirects), fixed the reordering in §4 (groups would have jumped above their heading) and added the SEO conditions in §8. The decisions were taken as recommended (table at the end). Where the build departs from the text, §12 says so.
**Read against:** the working tree of 2026-11-17 (`24d9c58`), 22 post files. The Hugo techniques in §3–§5 were checked on a scratch site with Hugo 0.166.0 (the *Verified* paragraphs). The full site was not built: this container has no photo store and no Dart Sass.

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

| home | the three posts it shows | not listed on this home |
|---|---|---|
| `/en/` | 2026-03, 2025-09, 2025-05 | the **three newest posts on the site** (de: 2026-08, 2026-10, 2026-11), and all of Swedish |
| `/de/` | 2026-11, 2026-10, 2026-08 | 11 English-only posts, all of Swedish |
| `/sv/` | 2024-12, 2024-06, 2024-01 | everything in English and German, i.e. everything since 2024 |

The English home, which is `x-default` and where `/` sends everyone, has had no new post for eight months, although the site published three in that time. `/sv/` has only one page of posts, so it shows no "All posts »" link at all (`home.html` prints it only when there is more than one page).

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

- **Every home, page 1 only**: after the own-language list (and its "All posts »" link, where there is one), before the photo strip.
- **`/posts/`, page 1 only**: the "All posts »" link leads there, so that is where a reader who wants more goes next.
- Not in the home's RSS, JSON-LD or sitemap. **No new URL.**

### What

- For each other language (by `weight`): its **3 newest posts that have no translation in the page's language**. A translated post is already in the own-language list. `hiddenInHomeList` is respected. A language with nothing to show is left out, and if every language is left out there is no block.
- Each entry has the title in its own language, the date in the page's language and format, the reading time and a flag. Whether to add a cover thumbnail is open decision D1. A description is not offered: it would multiply the foreign text on the page (§8).
- Below each group is a count link written in the page's language, for example *"All 6 posts in German →"* to `/de/posts/`. The number counts **every** post on that list, translated ones included, so it matches what the reader finds there. Last comes a link to `/feed/`: *"Everything in all languages, in one timeline: Feed →"*.
- The heading and labels are in the **page's** language, from i18n. Only the titles are in the other language. That keeps the amount of foreign text small, as rule 1 requires.

### Markup

```html
<section class="lang-more" aria-labelledby="lang-more-title">
  <h2 id="lang-more-title" class="home-header">Also on this site in other languages</h2>
  <p class="lang-more-intro">I write different posts in different languages. These ones are not available in English.</p>
  <div class="lang-more-groups">
    <div class="lang-more-group" data-lang="de">
      <h3><span aria-hidden="true">🇩🇪</span> Only in German</h3>
      <a class="lang-more-all" href="/de/posts/" hreflang="de">All 6 posts in German →</a>
      <ul>
        <li>
          <a href="/de/posts/books/feuerlilie-liza-grimm-review/" hreflang="de" lang="de">Feuerlilie von Liza Grimm: Rezension &amp; Zusammenfassung</a>
          <time datetime="2026-11-04">November 4, 2026</time> · 15 min
        </li>
        …
      </ul>
    </div>
    <div class="lang-more-group" data-lang="sv">…</div>
  </div>
  <a class="lang-more-feed" href="/en/feed/">📰 Everything in all languages, in one timeline: Feed →</a>
</section>
```

- `lang` goes on the link only, not on the `<li>`, because the date belongs to the page's language. With `lang`, a screen reader reads a German title with a German voice, and the browser's translate feature can tell what is foreign. `hreflang` on `<a>` is valid HTML and states the language of the target.
- The groups sit in **their own flex container**, `.lang-more-groups`. §4 reorders them with CSS `order`, and `order` works among siblings: if the groups shared a container with the heading, the visitor's group would move above the heading.

### Verified (scratch site, Hugo 0.166.0)

- `range site.Home.Translations` → `.Site.RegularPages` returns the other languages' pages from inside one language's build. This is the same pattern `layouts/feed/list.html` already uses.
- `range .Translations` + `eq .Lang $lang` correctly excludes a translated post. On the English home, *A de* (which has an English twin) is excluded and *B de only* is listed.
- The translation's `.Site.Params` holds **that** language's params. §4 needs this for its text (below).

## 4. Layer 2 — the browser language, decided before first paint

### The script

`head.html` already sets `js` on `<html>` with an inline script before first paint (for the newsletter). This goes next to it:

```js
(function () {
  var s = ["en", "de", "sv"], r = [], d = document.documentElement, c = null, x = false;
  (navigator.languages || [navigator.language || ""]).forEach(function (l) {
    l = String(l).slice(0, 2).toLowerCase();
    if (s.indexOf(l) > -1 && r.indexOf(l) < 0) r.push(l);
  });
  try {
    c = localStorage.getItem("lang-choice");             // set by the switcher, §6a
    x = !!localStorage.getItem("lang-hint-dismissed");
  } catch (e) {}
  if (s.indexOf(c) < 0) c = null;                        // a stored value that is not a site language counts as none
  d.dataset.reads = r.join(" ");
  d.dataset.top = c || r[0] || "";
  if (x) d.dataset.hintDismissed = "";
})();
```

Storage is read in its own `try`: a browser that blocks storage still gets its languages.

Everything else is CSS on those attributes. Nothing is moved in the DOM, and the attributes exist before the first frame, so there is nothing to flash and nothing to shift. §8 makes that a hard condition.

### On the home: what the visitor reads comes first

```css
.lang-more-groups { display: flex; flex-direction: column; gap: 16px; }
html[data-reads~="de"] .lang-more-group[data-lang="de"],
html[data-reads~="sv"] .lang-more-group[data-lang="sv"],
html[data-reads~="en"] .lang-more-group[data-lang="en"] { order: -1; border: 2px solid var(--primary); }
```

Groups in languages the visitor does not read stay visible in their normal place. The whole point is to show that there is more, and hiding them would also give a crawler a different rendered page.

### The hint bar: "this page is also in German"

- Rendered by the server **for each translation the page has**, by `header.html`, directly below the header and centred at `--main-width`. Rendering it there puts it in one place for every kind of page: homes, posts, and also photo, dex, model and game pages, which all have translations. Which of those get a bar is open decision D3.
- Each bar is written in its target language. On a home it says *"🇩🇪 Diese Seite gibt es auch auf Deutsch."* with the link *"Zur deutschen Seite →"*. On any other page it also names the translation's title, for example *"Diese Seite gibt es auch auf Deutsch: Was ist das Fediverse?"* with *"Auf Deutsch lesen →"*. The strings come from the translation's `.Site.Params.langHint` (`text`, `link`, `close`), because a page's i18n reaches only its own language (verified, §3).
- The bars are hidden by default. CSS shows one when it is in the visitor's first language: `html[data-top="de"]:not([data-hint-dismissed]) .lang-hint[data-lang="de"] { display: flex }`. The page's own language never has a bar, so no further condition is needed.
- The bar has a ✕ (a real `<button>`, labelled in the bar's language) that stores `lang-hint-dismissed`. Using the switcher stores `lang-choice` (§6a), and from then on that choice counts instead of the browser language. Both go in `localStorage`, so a blocked storage just means the bar comes back next time.
- An untranslated post shows no bar. There is nothing equivalent to offer, and the §3 block on the home handles that case.
- Known limit: only the visitor's **first** site language can produce a bar. A visitor who reads Swedish first and German second sees no bar on a page that exists in German but not in Swedish. Choosing the best available language per page would need script after the page is parsed, which is exactly what the no-shift rule forbids.

### Why this is safe for SEO

- The HTML is identical for every client. Googlebot renders with `en-US`, so it sees the static order, and the hidden bars are only a few words of link text, about what the language switcher already says. That is the ordinary pattern of tabs and accordions, not hidden text in the spam sense.
- Without JavaScript (Tor Browser at *Safest*) nothing changes. With JavaScript, Tor Browser normally reports English (its "request English versions of web pages" setting is on by default), so the Tor build behaves like an English browser and gives away nothing about the visitor.
- Both safety points depend on how the bar is built. §8 lists them as hard conditions: no layout shift, and a bar in the page flow, never an overlay.

## 5. Layer 3 — `/` picks the home

**Today:** Hugo writes `/index.html` itself (`renderDefaultSiteRedirect` in `hugolib/site_render.go`) through `layouts/alias.html`, as a meta refresh to `/en/`.

**Not through `alias.html`.** The first version of this concept branched `alias.html` on `.Page.IsHome`. The scratch site shows why that does not work: Hugo writes the paginator's `/<lang>/page/1/` redirect through the same template, with the same context. `/` and `/en/page/1/` both arrive with `.Page` = the English home and `.Permalink` = `/en/`, and `/de/page/1/` with the German home. The branch would have turned all of them into a language picker, so `/de/page/1/` would no longer lead to `/de/`. The template cannot tell those cases apart.

**Instead: an output format of its own**, the same technique `security.txt` and the nginx maps already use:

```yaml
disableDefaultLanguageRedirect: true    # Hugo writes no /index.html of its own
outputFormats:
  rootpicker:
    mediaType: text/html
    baseName: index
    path: ".."                          # relative to the language directory: the domain root
    isHTML: true
    notAlternative: true
    permalinkable: false
languages:
  en:
    outputs:
      home: [HTML, RSS, JSON, securitytxt, gallerymeta, nginxmap, nginxvariantmap, rootpicker]
```

`layouts/_default/home.rootpicker.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ site.Params.ShortTitle }}</title>
  <link rel="canonical" href="{{ .Permalink }}">
  <meta name="robots" content="noindex">
  <script>
    (function () {
      var s = ["en", "de", "sv"], l = null;
      try { l = localStorage.getItem("lang-choice"); } catch (e) {}
      if (s.indexOf(l) < 0) {
        l = "en";
        (navigator.languages || [navigator.language || ""]).some(function (x) {
          x = String(x).slice(0, 2).toLowerCase();
          if (s.indexOf(x) > -1) { l = x; return true; }
        });
      }
      location.replace("/" + l + "/");
    })();
  </script>
  <noscript><meta http-equiv="refresh" content="0; url={{ .Permalink }}"></noscript>
</head>
<body>
  <ul>{{ range .AllTranslations }}<li><a href="{{ .Permalink }}" hreflang="{{ .Lang }}" lang="{{ .Lang }}">{{ .Language.Label }}</a></li>{{ end }}</ul>
</body>
</html>
```

- The script jumps to a root-relative `/de/`, so it works the same in the clearnet and the onion build. The fallbacks use `.Permalink`, which carries the right `baseURL` in each build.
- The jump carries the query and the hash along (`"/" + l + "/" + location.search + location.hash`, added with the newsletter deep link): `?ref=` and `utm_*` are what Plausible attributes the visit by, and `#newsletter` opens the newsletter dialog. The snippet above predates that.
- Without JavaScript and for crawlers the result is the same as today: `/en/`, `noindex`, canonical `/en/`. `x-default` stays `/en/`. A redirecting home page is the case `x-default` was introduced for, and that cluster does not change.
- The root uses the same stored choice as §4. Someone who picked English in the switcher keeps getting English from `/`, even in a German browser.
- `alias.html` stays untouched, and so do all the `/<lang>/page/1/` redirects.

**Verified (scratch site, Hugo 0.166.0):**

- With `disableDefaultLanguageRedirect: true` and the `rootpicker` format on the English home only, `/index.html` comes from the new template, with `.Permalink` = `/en/` and all three homes in `.AllTranslations`.
- `/en/page/1/` and `/de/page/1/` are still written through `alias.html` as before.
- The newer key `disableDefaultSiteRedirect` behaves the same. Neither key logs a deprecation notice at `--logLevel info`.

**Alternative:** an nginx `map $http_accept_language` that answers `/` with a 302, plus `Vary: Accept-Language`. That saves one hop and works without JavaScript. But it lives in `../Web-Services`, it needs a cookie instead of `localStorage` for the stored choice, and it adds a second repository to every change. Recommendation: build it in this repo first, and move to nginx only if the hop is ever noticeable.

**Swedish** is learner content (*"jag är nybörjare"*). A Swedish browser would land on `/sv/`. With §3 that home lists the newest English and German posts too, so it is a complete entrance and explains the setup in Swedish. Whether Swedish browsers should go to `/en/` instead is open decision D5.

## 6. Smaller changes in the same direction (optional)

- **a) The switcher goes to the translation.** On a page with a translation, link to that translation; otherwise, to the other language's home, as today. Clicking it stores `lang-choice`. This is a small change to `header.html`, and it makes the switcher agree with the hint bar.
- **b) Search across languages.** Add the other languages' posts to each language's `index.json` with a `lang` field, and show a flag in the results. This has no SEO effect, because the search runs in the browser. It needs a `fastsearch.js` override. Later, if wanted (D6).
- **c) The intro sentence.** Once §3 shows the other languages, the hand-written *"Keep in mind that I post different content in different languages"* in each home's `homeInfoParams` can go or become shorter (D7).
- **d) "All posts »" is hard-coded English** (`layouts/_default/home.html:129`), so `/de/` shows it too, and `/sv/` would as soon as it has a second page. It needs an i18n key. This is independent of the rest and a one-line fix.

## 7. Rejected

| Idea | Why not |
|---|---|
| One merged, mixed-language list as the home's main list | Weakens the page's language signal (rule 1), and an English visitor would meet German titles first. `/feed/` already offers the mixed view as a separate page |
| Server-side language negotiation on content URLs | Rule 2: crawlers would see only one language, and shared links would break |
| Placeholder pages for missing translations | Rule 5 |
| Machine-translated posts or summaries | The site writes different posts per language on purpose, and unreviewed automatic translation is a quality risk |
| Hiding the groups a visitor does not read | It goes against the goal, and crawlers would render a different page |
| `hreflang` from a home to another language's posts | Rule 3: they are not equivalents |
| A language pop-up or modal ("Choose your language") | An intrusive interstitial, which Google demotes on mobile (§8) |
| Inserting the bar with a deferred script | Layout shift (§8) |
| Branching `alias.html` for the root page | It would also rewrite the `/<lang>/page/1/` redirects (§5) |

## 8. SEO: the expected effect, and the conditions for it

Done as described, the change does not make SEO worse. It should make it slightly better. Google promises nothing, and for a site of this size the effect is small either way.

### What gets better

- **Discovery.** A new post in one language is linked from all three homes, the domain's strongest pages, with its title as the link text. Google finds and crawls it sooner than today, when only its own language's home links it.
- **Freshness.** `/en/` and `/sv/` change whenever any language publishes, instead of looking frozen since March 2026 and December 2024. A home that changes gets recrawled more often.

### What stays neutral, as long as the design holds

- **Language signal.** On `/en/` the block adds about 60 words of foreign titles, against several hundred English words (intro, three posts with summaries, navigation, headings). The page stays clearly English. That is why D1 offers only cover thumbnails, which have no language, and no foreign descriptions.
- **No new URLs and no duplicate content**: the block lists titles, and the posts exist once. `hreflang`, canonicals and the sitemap do not change.
- **Same HTML for everyone** (rule 4). Googlebot sees Layer 1.

### Hard conditions

A build that breaks one of these does not ship. Each one has a test in §9.

1. **No layout shift.** The language attributes are set by the inline script in `<head>`, before first paint. The bar and the highlighted group are in the HTML from the start and are only shown or styled by CSS. Nothing is inserted, moved or resized by a script after the page has been painted. Cumulative Layout Shift is one of the Core Web Vitals, and they count toward ranking.
2. **The bar is part of the page, never an overlay.** It is in the normal flow (no `position: fixed`, `sticky` or `absolute`), has no backdrop, covers no content, and is small on a phone. Google demotes pages whose content is covered by an intrusive interstitial on mobile. A banner that uses a reasonable amount of space is explicitly fine.
3. **Only titles in the foreign language** (above).
4. **Plain followed links.** No `rel="nofollow"` on the block's links, which would throw away the discovery gain.

### What to watch after launch (Search Console)

- **URL inspection of the next new post:** when it was discovered and first crawled, compared with earlier posts.
- **Core Web Vitals report:** CLS stays *good* for the homes and for posts.
- **The English home in search results:** its title and snippet stay English. They come from `params.description`, which is English.
- **Pages report:** no new URLs, and no new redirects except `/`, which already was one.

## 9. Tests

- **static** (`tests/static/multilingual-home.spec.ts`):
  - every home page 1 and `/posts/` page 1 has the block, and no entry is in the page's own language;
  - no entry has a translation in the page's language;
  - every entry links to a built page whose `<html lang>` equals the link's `hreflang` and `lang`;
  - each count link's number equals the number of posts on the target list;
  - no link in the block carries `rel="nofollow"`;
  - the block is not in the RSS, the JSON-LD or the sitemap;
  - the hint bars exist exactly for the page's translations and are hidden without the `data-top` attribute;
  - `/index.html` keeps `noindex` and the canonical `/en/`;
  - `/en/page/1/`, `/de/page/1/` and `/sv/page/1/` still redirect to their own home.
- **e2e:** Playwright's `locale` option sets `navigator.languages` and `Accept-Language`.
  - `de-DE` on `/en/`: the German group comes first and the German bar is shown;
  - `en-US`: no bar;
  - ✕ keeps the bar away after a reload;
  - a switcher click wins over the browser language;
  - `/` with `sv-SE` lands on `/sv/`, and the no-JS project gets `/en/`;
  - **no layout shift:** CLS is 0 on a home and on a translated post, for `de-DE`, `sv-SE` and `en-US`;
  - **no overlay:** the bar's computed `position` is `static` or `relative`, and on `mobile-chrome` it is at most 120 px tall, with the page's `<h1>` still inside the first viewport.
- **Golden URLs:** unchanged. There is no new URL, unless D1 adds cover thumbnails, whose variants would need `npm run golden:update`.

## 10. Build order

0. **Before anything else:** check whether `../Web-Services/homepage/nginx.conf` (and the onion one) sends a `Content-Security-Policy`. If it allows inline scripts only by hash, the two new inline scripts (§4, §5) need their hashes there. The existing inline `js` script shows that inline scripts run today, but not how that is allowed.
1. §3, the block on the homes and `/posts/`: i18n, CSS and static tests. This is useful on its own. §6d fits in the same step.
2. §6a, the switcher, so that `lang-choice` exists.
3. §4, the head script, the CSS and the hint bar, with e2e tests including the CLS and overlay checks.
4. §5, the root page.
5. Optionally §6b and §6c.

## 11. Files

- **New:**
  - `layouts/partials/lang-more.html`
  - `layouts/partials/lang-hint.html`
  - `layouts/_default/home.rootpicker.html`
  - `assets/css/extended/lang-more.css`
  - `assets/js/lang-hint.js` (stores the switcher's choice and the ✕; on every page)
  - `tests/static/multilingual-home.spec.ts`
  - `tests/e2e/multilingual-home.spec.ts`
- **Changed:**
  - `layouts/_default/home.html` and `layouts/_default/list.html` (the `/posts/` page);
  - `layouts/partials/head.html` (the inline script next to the `js` class);
  - `layouts/partials/header.html` (the hint bar, and §6a);
  - `hugo.yaml` (`disableDefaultLanguageRedirect`, the `rootpicker` output format, `languages.en.outputs.home`, and `langHint` under each `languages.<lang>.params`);
  - `i18n/{en,de,sv}.yaml`;
  - `tests/e2e/language.spec.ts` (its last scenario asserted the old switcher);
  - `CLAUDE.md` and `AGENTS.md`.

## 12. As built

Built and tested on a full local build with placeholder photos (the photo store is not in this container) and Hugo 0.166.0: `tests/static/multilingual-home.spec.ts` (38 tests) and `tests/e2e/multilingual-home.spec.ts` + the turned-around `language.spec.ts` (22 runs across the `chromium` and `mobile-chrome` projects), all green. Firefox was not run here (not installed); nothing in the scripts is engine-specific, and the layout-shift test skips itself outside Chromium.

- **The bar's strings** are five, not three: `langHint.home`, `homeLink`, `page`, `pageLink`, `close`. A home's bar names no title and says *"Zur deutschen Seite →"*; any other page's names the translation (*"Diese Seite gibt es auch auf Deutsch: Was ist das Fediverse?"*, *"Auf Deutsch lesen →"*).
- **The whole sentence is the link.** On a wide screen its last part is drawn as the site's filled button; below 640 px (600 px before the design system's breakpoint set) the button goes, the sentence is underlined and clamped to three lines. On a Pixel 7 the bar was 64 px tall with the pre-token spacing.
- **✕ moves focus to `<main>`**, since the button disappears with its bar.
- **Layout shift**: every page already shifts its header by 0.001–0.01 while Cantarell swaps in, bar or no bar (measured on the home and a post, `en-US` and `de-DE`: the same shift, sourced at `nav` and the newsletter button). The e2e test therefore blocks the web fonts and then requires **zero** shifts with the bar showing; it got zero in every run. The font swap itself is not this feature's and is left alone.
- **i18n parity**: the `lang_more_only_<lang>` / `lang_more_all_<lang>` keys exist in all three files, the page's own language included, although a page never names its own language; the suite's key-parity test requires every key everywhere.
- **"All posts »"** was hard-coded English in `home.html` and `list.html`; both now use the `all_posts` key (§6d).
- Hugo adds its `generator` meta to the root page, as to every HTML output. Harmless.
- **Not verifiable from here**, and therefore step 0 of §10 stays a deploy check: whether nginx sends a `Content-Security-Policy` that needs hashes for the two inline scripts, and whether nginx answers `/` itself before the new page is ever served.

## Decisions

All taken as recommended on 2026-11-18, except where the last column says otherwise.

| | Question | Recommendation |
|---|---|---|
| D1 | What each entry shows: title, date and reading time only, or a cover thumbnail too? | Title, date and reading time. A cover has no language and looks good, but it adds image variants and golden URLs |
| D2 | How many entries per language? | 3 |
| D3 | Which pages get the hint bar: homes only, homes and posts, or every page with a translation (photos, dex, models, games too)? | Every page with a translation. It is one partial in the header, and a photo page in the visitor's language is just as useful as a post |
| D4 | `/`: client-side in this repo, nginx, or leave it? | Client-side (§5) |
| D5 | Send Swedish browsers from `/` to `/sv/`? | Yes, consistently. With §3, `/sv/` shows everything |
| D6 | Search across languages (§6b)? | Later — not built |
| D7 | Keep the hand-written intro sentence? | Shorten it once §3 is in — **left to the owner**: it is the owner's own text, in three languages |

## Sources

- Google Search Central, [Managing multi-regional and multilingual sites](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites): no automatic redirect by perceived language, page language from visible content, links between language versions.
- Google Search Central, [Tell Google about localized versions of your page](https://developers.google.com/search/docs/specialty/international/localized-versions): `hreflang`, `x-default`.
- Google Search Central Blog, [Introducing x-default hreflang](https://developers.google.com/search/blog/2013/04/x-default-hreflang-for-international-pages), [Creating the right homepage for your international users](https://developers.google.com/search/blog/2014/05/creating-right-homepage-for-your) and [How x-default can help you](https://developers.google.com/search/blog/2023/05/x-default): redirecting or selector home pages use `x-default`.
- Google Search Central Blog, [Crawling and indexing of locale-adaptive pages](https://developers.google.com/search/blog/2015/01/crawling-and-indexing-of-locale): Googlebot crawls without `Accept-Language`, from US addresses by default.
- Google Search Central, [Avoid intrusive interstitials and dialogs](https://developers.google.com/search/docs/appearance/avoid-intrusive-interstitials) and [Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals): the overlay and layout-shift conditions in §8.
