# Concept: one URL space for the gallery

**Status:** concept, nothing implemented. No build has been run against it.
**Read against:** the working tree of 2026-09-14, after the per-photo pages landed (see `gallery-photo-pages.md`).

A photograph currently has two public addresses that behave differently, and the lightbox invents a third state that no address describes. This proposes collapsing them: the PhotoSwipe lightbox pushes the photo's real page URL instead of a fragment, so the address bar always names something the server can render on its own.

## Decisions still open

Unlike `gallery-photo-pages.md`, nothing here is settled. These are the calls that change the shape of the work — see §7.

| | |
|---|---|
| Reload semantics | Reloading inside the lightbox would land on the photo page, not reopen the viewer |
| Legacy `#<uuid>` | Keep accepting forever; never emit. Canonicalise on arrival, or leave alone? |
| Feed + shortcode | Switch their links to photo pages, or leave pointing at the grid? |
| Scope | Gallery grids only, or also the single-item hero on a photo page? |

---

## 1. How many addressing schemes there actually are

Two, not three. **`CLAUDE.md` is stale on this point**: it documents the activity feed as keying photo permalinks on an FNV32a hash of the gallery `RelPermalink`, with `gallery.html` writing a matching `data-id`. That scheme no longer exists anywhere in the tree — `grep -rn "fnv" layouts/ assets/` returns nothing. `layouts/feed/list.html:127` now builds `printf "%s#%s" $galleryGeneral.RelPermalink $meta.id`, i.e. the same `#<uuid>` the gallery itself uses. Whoever changed it did not update the note.

So the real inventory:

| Address | Emitted by | Renders without JS | Shareable |
|---|---|---|---|
| `/gallery/general/#<uuid>` | `gallery.html`, `feed/list.html`, `gallery-image-figure.html` | The *grid*, not the photo | Preview is the gallery page |
| `/gallery/archive/#<uuid>` | same, for archived photos | The *grid*, not the photo | same |
| `/gallery/photo/<slug>/` | `gallery.html` `href` (new) | Yes — the photo, its metadata, related photos | Yes, with a correct `og:image` |
| `/gallery/photo/<uuid>/` | alias only | Redirect stub | **No** — `noindex`, zero OG tags |

The cost of the fragment scheme is concentrated in the third and fourth columns. A `#<uuid>` URL names a *photo* but resolves to a *page listing 572 photos*; the open viewer is a state the server cannot reproduce. Anyone pasting that link into a chat gets the gallery's preview, not the photograph — and pasting the uuid alias gets nothing at all, because Hugo's alias stub carries no OpenGraph tags and a `<meta http-equiv="refresh">` is markup a crawler may decline to follow.

That asymmetry is new. Before the photo pages existed there was no better address to offer, so the fragment was the only option available. It no longer is.

## 2. The proposal

When the lightbox opens a slide, push the photo page's URL rather than a fragment:

```
/gallery/general/            →  /gallery/photo/alpaca-behind-tree/
  (grid, scroll preserved)        (pushState, same document, viewer open)
```

The URL is already in the DOM. `gallery.html:43` gives every `.gallery-item` an `href` pointing at the photo page, because that is what a visitor without JavaScript follows. The lightbox can read `element.getAttribute("href")` and needs no new data attribute — the progressive-enhancement link and the history entry become the same string, which is the whole point.

What that buys:

- **Reload or copy-paste lands on a real page.** Same title, same alt text, same EXIF, same licence — served by `gallery-photo.html` with no JavaScript involved.
- **Sharing from the viewer works.** All 648 slug pages now carry the photograph as `og:image` (840×630, 80 KB), verified after the `get-page-images.html` fix. Previously every photo page shared the site's penguin logo; the fragment URLs still share the gallery's.
- **One thing to reason about.** The address bar stops describing a page-plus-hidden-state and starts describing a photograph.

It also removes a class of bug rather than adding a feature: today the lightbox's URL and the page's URL are different vocabularies that can drift, and one of them is already `noindex`.

## 3. Mechanics

Four touch points in `assets/js/lightbox.js`, plus a rule about where it applies.

**`openFromHash(fromHistory)` becomes `openFromLocation(fromHistory)`.** It currently reads `location.hash.substring(1)` and matches it against `el.dataset.id`. It gains a path branch and keeps the hash branch:

```
match on location.pathname against each anchor's href   (new, canonical)
else match on location.hash against data-id             (legacy, input only)
```

**The `change` handler swaps its value, not its logic.** The existing rule — one history entry per lightbox *session*, not per slide, so swiping thirty photos still costs one back press — is preserved exactly: `pushState` on the first slide, `replaceState` on every subsequent one. Only the string changes from `"#" + id` to the item's `href`.

**The deep-link branch changes its test.** It currently asks whether `location.hash.substring(1)` already equals the slide's id, meaning "we arrived here *as* this photo, so rewrite to the bare gallery URL before pushing, or there is nothing inside this page to go back to". With paths, the same question is asked of `location.pathname`.

**`popstate` is unchanged in structure.** It still distinguishes "our entry was popped, close the viewer" from "forward navigation back onto a photo URL, reopen it", and still defers a close that arrives mid-opening-animation via `pendingClose`.

> **The one that will bite: `galleryUrl()` must be captured, not computed.**
> It is currently `() => window.location.pathname + window.location.search`, evaluated lazily inside the `change` handler — which is safe today because the pathname never changes; only the hash does. The moment the lightbox pushes a *path*, `location.pathname` becomes the photo URL, and any later call returns the photo URL instead of the grid. Closing would then "restore" the URL the viewer was already showing. The grid URL has to be read once at module init and held in a constant.

**Scope: grids only.** `gallery-photo.html:63` wraps the hero in `id="gallery"` with a single `.gallery-item` carrying `data-id` — that is deliberate, and it is what gives the photo page PhotoSwipe, the like counter and the info popup with no new JavaScript. But it means `lightbox.js` binds there too, and on that page the document URL *already is* the photo URL. Pushing it again would stack two identical entries and make back appear to do nothing but close the viewer. The lightbox should therefore skip history manipulation entirely when the container holds a single item whose `href` matches the current path.

**Scroll restoration is mostly a non-issue**, which is worth stating because it sounds like it should be one. A `pushState` never leaves the document, so popping back to the grid preserves scroll for free. It only becomes a real concern on a genuine navigation — someone opening a shared photo URL cold and then pressing back — and that is the browser's own restoration, which the current code does not touch (`history.scrollRestoration` is left at its default).

## 4. Why the risk is concentrated in one place

The history block is the most delicate code in the file, and not by accident. PhotoSwipe v5 removed v4's history module deliberately; everything in `lightbox.js` from `historyEntryPushed` down is hand-wired to replace it. Three flags interact:

| Flag | Guards against |
|---|---|
| `historyEntryPushed` | Pushing a second entry for the same viewer session |
| `suppressHistoryBack` | `close()` arriving *from* `popstate` calling `history.back()` again and leaving the page |
| `pendingClose` | Back pressed mid-open; PhotoSwipe ignores `close()` until `opener.isOpen` flips at `openingAnimationEnd` |

Each exists because of a specific failure that was observed and fixed. Changing what gets pushed does not change that logic, but it does mean re-walking every path through it: open, swipe, close; open, back; back mid-animation; deep link, close; deep link, back; forward after back. Those six cases are the test plan, and they should be checked in a real browser rather than reasoned about — the `pendingClose` case in particular only reproduces with the animation running.

Two second-order effects worth deciding on rather than discovering:

- **Analytics.** The Plausible `Image View` event fires on `change` and is deduped by image id. If Plausible is configured for history-based pageview tracking, real URL pushes may also register as pageviews — which could be a genuine improvement in per-photo reporting, or double-counting. Worth checking what the current config does before shipping.
- **Reload stops reopening the viewer.** Today, refreshing on `#<uuid>` reloads the grid (572 images) and re-opens the lightbox. With paths it loads the photo page instead: far lighter, server-rendered, but the visitor is now on a page rather than in a viewer. This is arguably the better outcome, but it is a behaviour change and not merely an implementation detail.

## 5. Migration and compatibility

**Legacy `#<uuid>` links must keep resolving, permanently.** They are already published in the RSS feed, in the activity feed, and in every post using the `galleryImage` shortcode. The rule: accept as input, never emit. `openFromLocation` keeps the `data-id` branch indefinitely; the cost is a few lines.

Whether to *canonicalise* on arrival — `replaceState` the fragment URL into the photo path — is an open question. It tidies the address bar, but it rewrites an entry the visitor did not create and muddies what back means for someone who arrived from the feed. Leaving the hash alone and simply opening the viewer is the conservative choice.

**The uuid alias is unaffected.** `/gallery/photo/<uuid>/` remains the durable permalink for renames, and remains `noindex` — it was never a sharing URL.

**The feed and the shortcode are the interesting ones.** `feed/list.html:127` and `gallery-image-figure.html:95` both build `<gallery page>#<uuid>`. Both could point at `/gallery/photo/<slug>/` instead, which would give feed items and inline post images a destination with a working link preview and real indexable content. That is a genuine improvement and a small diff — but it changes published URLs in the RSS feed, so it belongs in its own change with its own reasoning, not smuggled into this one. `gallery-photo-pages.md` already lists both as deliberately out of scope for the same reason.

## 6. What this does not solve

- **The two rendering paths.** This unifies *addressing*, not *rendering*. `lightbox.js` still rebuilds the metadata panel by scraping `.pswp-caption-content` and labelling it with hardcoded English strings, so German and Swedish visitors still see an untranslated popup. That is concept #1 — the shared fragment partial — and it is independent of this.
- **Archive and general remain separate walks.** The lightbox only ever traverses the grid it was opened from, which is why the per-photo prev/next links were split into two chains. A single URL space does not merge those galleries and should not.
- **No-JS behaviour.** Already correct: the anchor's `href` is the photo page and PhotoSwipe `preventDefault`s the click. Nothing here changes for a visitor without JavaScript.
- **The 427 camera-code slugs.** `/gallery/photo/p1002301/` is a real URL either way. Renaming the files remains the highest-value follow-up and is untouched by this.

## 7. Open questions

1. **Canonicalise legacy fragments on arrival, or leave them?** Tidier address bar versus not rewriting history the visitor did not make.
2. **Is "reload lands on the photo page" the behaviour you want?** It is the natural consequence, and probably an improvement, but it is the one user-visible change that is not strictly a fix.
3. **Should the feed and `galleryImage` switch to photo-page links now or later?** Later keeps this change small; now avoids publishing more `#<uuid>` URLs into RSS that will be legacy input forever.
4. **Does Plausible need reconfiguring** before real URLs start being pushed?
