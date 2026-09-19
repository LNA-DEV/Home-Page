# Concept: the download dialog — pick a size, read the licence, get a named file

**Status:** **built, 2026-09-19**, and verified against a fresh build of all three languages. Where the implementation departs from what this file proposed, the file has been corrected rather than the code — each such spot says so. What is still open is in §13.
**Measured:** 2026-09-18, against the working tree (Hugo 0.166.0), `data/gallery.yaml` at 648 photos (632 `cc-by-sa-4.0`, 16 `all-rights-reserved`, 0 `cc-by-nd-4.0`), and a fresh `public/` from the same day (4,163 served gallery files). Every size, count and byte figure below comes from that build.

The lightbox has a download button. It hands over one file — the 4000 px render — under a name like `Alpaca behind tree_hu_564ab7caf97be6b0.JPG`, and says nothing about the licence at the moment it matters most. This replaces the single link with a small dialog: choose one of the renders the site already serves, see the licence and what it lets you do in plain words, and receive a file named after the photo's title in the language you are reading. Photos that are all rights reserved say so, allow the download for private use, and point at the way to ask for anything else.

Nothing here adds an image render. The four sizes on offer exist today for every one of the 648 photos, so the build cost is zero and the deploy time does not move.

## Settled decisions

| | |
|---|---|
| Where | Two entry points, one data set: the lightbox toolbar button (every grid, album, dex, model and photo page) opens the dialog; the photo page also prints the same content as a static block in its licence card, which works without JavaScript — §7 |
| Sizes | The renders that already exist for every photo: **600 · 1200 · 4000 px fit** and the **published original**. No new render, ever — §2 |
| Duplicate tiers | A tier whose dimensions equal the next larger one is not shown. 46 originals are under 4000 px, so their "Large" *is* the original in pixels and only the original is offered — §2 |
| Filename | `<title in the page's language>.jpg`, the same name for every tier. Sanitised **at build time** and emitted as `data-download-name`, so the no-JavaScript path gets it too — §3 |
| Licence in the dialog | The label linked to the deed, a **may / must / not** block in the reader's language, and for Creative Commons a ready-to-copy **credit line** — §4 |
| Where that text lives | `data/licenseMap.yaml`, per key, per language: new `short`, `deed` and `requires_permission` fields. A key without a `deed` is a build error — §4 |
| All rights reserved | A notice: download for private use only, anything else needs permission. "Contact me" (the site author's address) and "Licensing details" beside it. The size buttons are disabled until a checkbox is ticked — §5 |
| File sizes | Fetched with `HEAD` when the dialog opens, not computed at build time — §6 |
| Dialog element | A native `<dialog>` shown with `showModal()`, the pattern `newsletter-cta.html` already uses. Dark sheet like the info popup, because it only ever opens over the black lightbox — §6 |
| Markup contract | One partial, `gallery-download-attrs.html`, emits `data-license`, `data-downloads` and `data-download-name` on every `.gallery-item`. The JS reads nothing else, and computes nothing of its own — §8 |
| Analytics | One Plausible event, `Image Download`, with the size tier and the licence key — §9 |

## Decisions still open

| | Recommendation |
|---|---|
| Checkbox before an all-rights-reserved download | **Yes.** It has no legal weight of its own — §5 says why it is there anyway. Creative Commons downloads get **no** checkbox: the licence is granted by the act of use, and a click-through adds friction and nothing else. Flipping either is one line |
| A size suffix in the filename (`… (1200 px).jpg`) | **No.** The request was the title; a visitor who downloads two sizes gets `Title.jpg` and `Title (1).jpg` from the browser, and the pixel size is one right-click away. Easy to add later, hard to take back once files are out |
| The original on all-rights-reserved photos | **Offer it**, like everywhere else. The original is already published — the `ImageObject` microdata's `contentUrl` points at it — so hiding the button would protect nothing, and since the embedding pass it carries no serial numbers, no GPS and no thumbnail. The notice, not the tier list, is what says how it may be used |

---

## 1. Diagnosis — what a download is today

| | Today |
|---|---|
| The toolbar button | An `<a download target="_blank" rel="noopener">` whose `href` is `data-download` — the 4000 px fit render. One size, no choice |
| The filename | Hugo's hashed output name: `Alpaca behind tree_hu_564ab7caf97be6b0.JPG`, or `_DSC2784_hu_6b3d532ba01067cb.jpg` for the 427 camera-code files. The `download` attribute is set but empty, so the browser keeps the URL's name |
| The licence at that moment | Not shown. The info popup has it — under a heading that says **Copyright**, with the label but no link to the deed and no word on what it allows |
| The photo page | "View full size (4000 × 3000)" opens the render in the tab; no `download`, so the name is the hashed one again |
| Inside the file | Correct and complete since `gallery-embed-metadata.py`: creator, `© year artist`, `xmpRights:UsageTerms` per language, `WebStatement`, `dc:title` and `dc:description` per language, the UUID |

The last row is the point. The **file** already knows its title in three languages and its licence — the metadata concept fixed that. What the *visitor* sees at the moment of downloading is a button, and what they get is a hash. The dialog is the human-facing half of the same information: the filename it sets and the `dc:title` inside the file are the same string, and the deed it shows is the same licence `UsageTerms` names.

`target="_blank"` on a `download` link is a leftover: the attribute already means "save, do not navigate", and the target can make Safari open an empty tab beside the download. It goes.

## 2. The ladder — what exists for every photo

Every served gallery file, grouped by what produced it:

| Tier | Render | Files | Median | p90 | Max | Long side |
|---|---|---:|---:|---:|---:|---|
| Small | `fit 600x600` (grid thumbnail) | 648 | 39 KB | 67 KB | 0.1 MB | 600 |
| Medium | `fit 1200x1200` (photo page hero) | 648 | 96 KB | 201 KB | 0.4 MB | 1200 |
| Large | `fit 4000x4000` (lightbox, today's download) | 648 | 474 KB | 1.6 MB | 3.5 MB | 4000 — or the original's size, below |
| Original | the published source file | 648 | **9.2 MB** | **19.6 MB** | **35.7 MB** | median 5198, max 8280; 168 above 6000 |

Together the 4000 px renders are 0.9 GB; the originals 7.0 GB.

Not offered, and why: the 1600 px RSS render (571 files, not every photo), the `fit 1200x630` OpenGraph render (411 files — not every photo, and a box nobody would pick by hand), the dex's `fill 900x900` covers (cropped, 49 files), the 120 px feed thumbnails, and the shortcode ladders (posts only). A tier has to be an uncropped render of every photo, or the dialog would differ from photo to photo for no reason a visitor could see.

**The dedupe rule.** 46 originals have a long side under 4000 px, so `fit 4000x4000` re-encodes them at their own size: same pixels, worse file, sitting next to the untouched original. For those the Large tier is dropped and the ladder is three steps. The rule is general — *drop a tier whose dimensions equal the next larger tier's* — so it also covers the single photo whose original is under 1200 px, and any future 600 px original.

**As built: 50 photos, not 46.** The rule is "equal to", and five more originals sit at *exactly* 4000 on the long side, where `fit 4000x4000` returns the original's own dimensions. 46 under + 5 at = **50 three-step ladders** out of 648 (verified against exiftool over every published original, with the EXIF rotation applied). The predicate to hold in mind is **at or under 4000**, not under it. The same check confirmed the oriented dimensions the ladder reports for the original are correct on all 648 — see §8 for how they are derived without paying for a fourth render.

**The original, on purpose.** It is the one tier that can genuinely surprise: a median of 9 MB and a maximum of 36 MB, on a phone, over Tor. That is the reason the dialog shows the byte size before the click (§6) rather than the reason to hide the tier. Hiding it would be theatre — the URL is in the page's microdata on every grid, and the embedding pass already made the published copy safe to hand out.

## 3. The filename

```
download="<sanitised title in site.Language.Lang>.jpg"
```

The `download` attribute names the saved file for a same-origin URL, which every gallery render is — on the clearnet build and on the onion. The server sets no `Content-Disposition` on static files (`deploy.sh` rsyncs `public/`, nothing sits in front), so the attribute is authoritative. Should a header ever be added, it would win in Chromium; that is worth knowing, not worth designing around.

**The title is always there.** Since the URL work, a missing title in any language is a hard build error, and the data confirms it: all 648 entries carry `en`, `de` and `sv` titles, the longest is 73 characters in English and 92 in German, and none of the 1,944 contains a character a filesystem rejects. The German grid therefore saves `Deckung am Baum - Alpaka lugt hinter einem Stamm hervor.jpg`, the Swedish one `Skydd vid trädet - alpacka kikar fram bakom en stam.jpg`, the English one `Tree Cover - Alpaca Peeking Out From Behind a Trunk.jpg`. Umlauts and `å ä ö` are legal on NTFS, APFS and every Linux filesystem in use; nothing is transliterated.

**Sanitised anyway, and purely defensively.** `\ / : * ? " < > |` and control characters become `-`, whitespace collapses, trailing dots and spaces go (Windows), the stem is capped at 120 characters, and an empty result falls back to `photo-<uuid>` — which cannot happen with today's data, but `.jpg` alone must never be the answer. The extension comes from the render's own URL, lowercased: `.JPG` sources produce `.jpg` files. Measured across all 1,944 titles: **not one is altered by any of those rules**, and the longest stem is 92 characters (German; English 73, Swedish 74), so the cap never fires either. The sanitiser exists for the title nobody has written yet.

**Computed at build time, not in the script.** The finished name is emitted once per item as `data-download-name` (§8), and the dialog reads it. This is the one place where doing the work in JavaScript would quietly cancel the feature: the static card on the photo page (§7) needs exactly the same string, and a JS-only sanitiser leaves that path with Hugo's hashed name — precisely what this section exists to remove, missing on the one path that is meant to work without JavaScript. The alternative, the same five rules implemented twice in two languages, is the worse half of that trade. Hugo does all of it with `replaceRE`, `strings.TrimRight`, `substr` and `default`.

One attribute, not one per tier: the name is the same for every size, so the ladder in `data-downloads` stays a pure `WxH URL` list.

**The joining word is translated.** The credit line reads `"Title" by Lukas Nagel, CC BY-SA 4.0` in English and `… von …` / `… av …` in German and Swedish, from a `download_credit_by` key. An English "by" on the German page is exactly the kind of thing the per-language filename work exists to prevent, and it was in the first build until the German dialog was read back. The template builds the line with explicit quotes rather than `%q`, whose Go-string-literal escaping is not what a credit line wants.

**The attribute needs no JavaScript to do its job.** `download` is HTML. Given the same-origin URL and the absent `Content-Disposition` above, the browser writes `<title>.jpg` on a left-click, a middle-click, a long-press and "save link as" — with scripts off, and on the onion build. That is what makes §7's static card a second full entry point rather than a fallback that silently drops the headline feature.

**Where the title comes from.** `collect-images.html` resolves it for the page's language; `gallery-download-attrs.html` sanitises it and writes the attribute. It is the same string the photo page's heading shows and the same string `dc:title` carries inside the file. The `<span class="caption-title">` in `.pswp-caption-content` stays what it is — the info popup's and the lightbox's title — and the dialog does not read it.

## 4. The licence block

The dialog shows three things about a Creative Commons photo, in this order: the licence label linked to the deed in the reader's language (`url_by_lang` already exists for exactly this), a plain-language summary, and a credit line.

### The summary lives in the licence map

`data/licenseMap.yaml` is the licence's single source of truth — label, deed URL, the `terms` sentence embedded in the files. The summary belongs beside them, not in `i18n/` keyed by licence name, so that adding a licence is one YAML block and cannot be done half-way:

```yaml
cc-by-sa-4.0:
  url: https://creativecommons.org/licenses/by-sa/4.0/
  url_by_lang: { de: …/deed.de, sv: …/deed.sv }
  label: Creative Commons Attribution-ShareAlike 4.0
  short: CC BY-SA 4.0                     # NEW — for the credit line and the dialog heading
  terms: "Licensed under CC BY-SA 4.0 — …"
  deed:                                   # NEW — per language, English fallback
    en:
      may:
        - Share it — copy and redistribute it, in any medium
        - Adapt it — crop, edit, build on it
        - Use it commercially
      must:
        - Credit Lukas Nagel and link to the source
        - Link to the licence and mark any changes
        - Release adaptations under this same licence
      not: []
    de: { … }
    sv: { … }

cc-by-nd-4.0:
  …
  deed:
    en:
      may: [Share it, in any medium — commercially too]
      must: [Credit Lukas Nagel and link to the source, Link to the licence]
      not: [Distribute a modified version — cropping and colour edits included]

all-rights-reserved:
  url: /licensing/
  label: { en: All rights reserved, de: Alle Rechte vorbehalten, sv: Alla rättigheter förbehållna }
  short: { en: All rights reserved, de: Alle Rechte vorbehalten, sv: Alla rättigheter förbehållna }
  requires_permission: true               # NEW — drives the notice, the contact link and the checkbox
  deed:
    en:
      may: [Keep it for yourself — look at it, use it as a wallpaper]
      must: [Ask before doing anything else]
      not: [Publish, share or use it commercially without my permission]
```

`deed` is a per-language block rather than string-or-map per item, because nine translated bullets per licence are easier to write and review as three lists than as nine two-line maps. It resolves through the same English fallback as `label` and `terms`, in `license-index.html`, and **a key without a `deed` is a build error**: a licence the dialog cannot explain must not be attachable to a photo. `short` falls back to `label`.

`requires_permission` is a **flag, not a key comparison**. Neither the template nor the JS may branch on `eq $key "all-rights-reserved"`: the day a second restricted licence appears (a model who agrees to the site but not to CC, a competition's terms), it must behave identically by carrying the flag, not by being special-cased.

### How it reaches the dialog

Per licence, not per photo. Three licences × label, short, url, deed, flag is a few hundred bytes, and `head.html` already builds a `$params` dict for `main.js` — it gains `"licenses" (partialCached "license-index.html" . site.Language.Lang)`, resolved for the current language like every other string in that dict. Each `.gallery-item` then carries only `data-license="cc-by-sa-4.0"` (§8), and the JS looks the key up. Emitting the deed per item would repeat ~400 bytes 572 times on the general grid; the key is 25.

### The credit line

Creative Commons' own attribution guidance is *title, author, source, licence*. The dialog composes exactly that and puts a copy button next to it:

```
"Signpost Above the Fog - A Bavarian Trail Marker" by Lukas Nagel, CC BY-SA 4.0
https://lna-dev.net/en/gallery/photo/signpost-above-the-fog-a-bavarian-trail-marker/
```

Title from `.caption-title`, author from `.caption-artist`, licence from `short`, source from `data-page` resolved against `location.origin` (on the onion build that is the onion URL, which is the URL the visitor is on; the embedded `plus:LicensorURL` stays clearnet, as the metadata concept decided, and that is the right place for the canonical one). The copy button is `.photo-copy[data-copy]` — `photo-page.js` binds it by delegation on `document` precisely so copies of the markup injected into a popup work, and this is one more such copy. Nothing new to write for it.

A `requires_permission` licence gets no credit line: there is nothing to attribute because there is nothing to reuse.

## 5. All rights reserved

Sixteen photos today, and the model concept expects more. For them the dialog reads, in the visitor's language:

> **All rights reserved.** You are welcome to download this photo for yourself — to look at it, to use it as a wallpaper. Publishing it, sharing it or using it commercially needs my permission.
> [Contact me] · [Licensing details]

Then the checkbox — *I will use this photo privately only* — and the size buttons, disabled until it is ticked. The `may / must / not` lists render above the notice exactly as for CC, so the two licence kinds share one layout and differ in the notice and the gate.

**Why printing is not on the list, though it was.** Both this notice and the `may` bullet in §4 used to end "…, to print it for your own wall". It came out after the build, deliberately. Looking at a photo and setting it as a wallpaper are screen-bound and end with the file; a print is a physical object that outlives it, can be given away or hung somewhere public, and carries none of the creator, `xmpRights:UsageTerms` or `WebStatement` that the embedding pass writes into every served JPEG — so the one use being actively invited is the one where attribution is guaranteed to be lost. It is also the likeliest thing somebody would pay for, on the sixteen photos whose whole point is that they are not given away, and the tier list beside the sentence offers their **original**, up to 8280 px: the sentence and the ladder together do not read as "I will not chase private use", they read as "here is a file you can make a poster from".

There is a real argument the other way and it is worth knowing: where a statutory private-copy limitation exists — §53 UrhG in Germany, for instance — a print for one's own wall is lawful whatever this file says, so removing the clause takes nothing away there and only stops asserting it. In a jurisdiction with no such limitation the clause *was* a grant. Saying nothing is not a prohibition; "Ask before doing anything else" sits directly underneath. **This was a decision — do not put printing back unasked.** `data/licenseMap.yaml` carries the same note where the bullet lives.

**Why a checkbox with no legal weight.** It is not a contract; nobody believes a tick box in a lightbox binds anyone. Its value is the moment of reading: the download cannot happen before the eye has passed the sentence that says what the licence is, and the tick is the cheapest evidence that the sentence was on screen. That is the whole case for it, and the reason CC photos do not get one — their sentence grants, it does not restrict, and reading it is not a precondition of anything.

**Contact.** "Contact me" is `mailto:` from `site.Params.author.name`/`email` (`me@lna-dev.net`) — the address the licensing page's own Contact section uses. Not a new field: the author block is already the source of the artist fallback and the credit. "Licensing details" is `site.Params.licensingPage` resolved per language, the same target the info popup and `photo-meta.html` link to, with `#contact` appended so it lands on the section that says how to ask. Today that anchor exists only in English: Hugo derives heading ids from the heading text, so the German and Swedish pages have `#kontakt`. The three `## Contact` / `## Kontakt` headings get an explicit `{#contact}` so one anchor works in every language.

**Not the model rights note.** CLAUDE.md records that a rights sentence on model pages was removed by decision and must not come back unasked. This notice is a different thing: it is about the *licence key* a photo carries and appears only for photos whose key says `requires_permission`, in the one place a visitor is about to take the file. It says nothing about the people in a photo, and a CC-licensed model photo shows the CC block like any other.

## 6. The dialog

```
┌──────────────────────────────────────────────────┐
│ Download                                      ✕  │
│ Signpost Above the Fog - A Bavarian Trail Marker │
│                                                  │
│ LICENCE                                          │
│ Creative Commons Attribution-ShareAlike 4.0 ↗    │
│ ✓ You may   share · adapt · use commercially     │
│ ! You must  credit and link · mark changes ·     │
│             share alike                          │
│                                                  │
│ CREDIT LINE                                 copy │
│ "Signpost Above the Fog - …" by Lukas Nagel,       │
│ CC BY-SA 4.0 — https://lna-dev.net/en/…          │
│                                                  │
│ SIZE                                             │
│ [ Small     400 × 600      44 KB  ]  avatars     │
│ [ Medium    800 × 1200    120 KB  ]  posts       │
│ [ Large    2667 × 4000    780 KB  ]  prints, 4K  │
│ [ Original 5520 × 8280   11.2 MB  ]  as exported │
└──────────────────────────────────────────────────┘
```

Each size row is an `<a download="…" href="…">` — a real link, so a middle-click, a long-press and "save link as" all do the expected thing. The byte sizes fill in as they arrive; the dimensions are in the markup and render immediately.

**A native `<dialog>`, shown with `showModal()`.** `newsletter-cta.html` is the precedent and its comment explains the choice: only the modal form puts the element in the top layer and brings the focus trap, the `Escape` handling and `::backdrop` with it. The top layer also settles a stacking question for free — PhotoSwipe's root is at `z-index: 100000` and the info popup at `999999 !important`; a modal dialog paints above both without a number.

**Escape has two listeners.** PhotoSwipe binds `keydown` on `document` and closes the lightbox on `Escape` when `escKey` is on. With the dialog open, one key press would close both. PhotoSwipe checks `pswp.dispatch('keydown', …).defaultPrevented` before acting, so the guard is `pswp.on('keydown', (e) => { if (dialog.open) e.preventDefault(); })` — its own event object, its own contract, no monkey-patching. Closing the lightbox closes the dialog with it (the `close` handler in `lightbox.js` already does this for the info popup). Focus returns to the toolbar button on close, which `showModal()` does by itself.

**The toolbar button changes element.** Today it is registered with `tagName: "a"`; it becomes a `<button>` with `onClick` opening the dialog for `pswp.currSlide.data.element`. `data-download` on the items becomes redundant once the ladder attribute exists (§8) and is removed in the same step, so nothing can read the old single URL by accident.

**Sizes by `HEAD`.** Hugo does not know the byte size of a processed image without reading it (`.Content | len` over 1,296 renders per language is not a build cost worth paying), and the embedding pass changes every file's size after Hugo is done anyway. So the dialog asks: one `fetch(url, { method: "HEAD" })` per tier when it opens, `Content-Length` formatted with `Intl.NumberFormat` in the page's language, results memoised per URL for the session. Same origin, static files, four requests — on the onion build too. If a `HEAD` fails or is slow the row simply keeps showing dimensions only; the download does not wait for it.

**Dark, literal colours.** The lightbox is `bgOpacity: 1` — black — and the dialog exists only over it, so it follows the info popup's `#1a1a1a` sheet rather than the theme variables the newsletter modal uses. Under 700 px, PhotoSwipe's own breakpoint in `paddingFn`, it becomes a full-width bottom sheet.

## 7. The photo page — the same content, without JavaScript

The photo page already has a licence card in `photo-meta.html`: photographer, licence, "Licensing details". It grows the rest of the dialog as static markup: the `may / must / not` lists, the credit line, the notice where the flag says so, and the size ladder as plain `<a download>` links with dimensions. One thing is **not** in that markup — the checkbox in front of an all-rights-reserved download, because it does nothing without a script; `gallery-download.js` inserts it when it runs, which is also the only way round that degrades correctly (below).

**The copy button, by contrast, IS in the markup**, and an earlier revision of this file was wrong to say otherwise. The repo already solves that exact problem better than a JS insertion would: `.photo-copy[data-copy]` is bound by delegation in `photo-page.js` and is `display:none` until `<html>` gains `has-clipboard`, which that script adds only when `navigator.clipboard` exists. So the control is never dead — not with JavaScript off, not in an insecure context, not where the Clipboard API is blocked — and the credit line beside it is selectable text either way. The download card reuses that control verbatim, which is what §4 means by "nothing new to write for it". `id="download"` on the card. The "View full size (4000 × 3000)" link in `.photo-actions` becomes **Download** with `href="#download"` — a real in-page link that works with no script at all, the same reasoning `newsletter-cta.html` gives for being a link rather than a button.

That gives the page two renderings of one data set: the static card, and the dialog the hero's lightbox opens. `photo-meta.html` and the info popup are already exactly that pair — the partial's comment says so — and the rule is the same: the two UIs are separate on purpose, only the data is shared. Both read the ladder from `gallery-download-attrs.html` and the deed from `license-index.html`, so they cannot disagree.

**The gate is added by the script, never removed by it.** Hugo renders the static card *ungated* — every size link carries its `href` and its `download` — and the script, when it runs, inserts the checkbox, marks the links `aria-disabled="true"` and adds a click handler that swallows the click until the box is ticked. Verified on the built page: the served HTML of an all-rights-reserved photo contains no `aria-disabled`, no `<input>` and four working `download=` links. Written the obvious way round (ship the markup gated, let JS ungate on tick) the gate becomes permanent with scripts off, which is the exact opposite of the intended degradation, so the direction is load-bearing rather than a style choice. There is also nothing to un-set: these are `<a>` elements and `disabled` is not an attribute of `<a>`, which is why it is `aria-disabled` plus a handler and not a form control. Without JS the links work and the notice sits directly above them — the visitor with scripts off on the Tor build reads the same sentence in the same place, one tick fewer.

**What a no-JavaScript visitor gets, and what they do not.** The way in is already open: `gallery.html` links each grid item at the photo's own page rather than at the image, so a click with no PhotoSwipe lands on the page that carries this card.

| | With JavaScript off |
|---|---|
| The size ladder | All of it — every tier, with its dimensions |
| The filename | Correct. `download` is HTML and the name is computed by Hugo (§3) |
| Licence, the `may / must / not` lists, the credit line | Static text, identical to the dialog's |
| Copy button on the credit line | Rendered, then hidden by CSS — `has-clipboard` never lands on `<html>`, so it is not a dead control. The line itself is selectable `<code>`, which is the part that matters |
| The checkbox and its gate | Never rendered — see above. The notice it guards is static and sits right where it would |
| Byte sizes | Gone, and permanently so: §6's two reasons (the read cost, and `gallery-embed-metadata.py` rewriting every file *after* Hugo) mean the build cannot know them, only state them wrongly. The rows show dimensions only. Do not later "fix" this with `.Content \| len` |
| The dialog itself | Does not exist. PhotoSwipe is JavaScript from top to bottom, and nothing here tries to rebuild a modal without it |

## 8. The markup contract

One partial, `layouts/partials/gallery-download-attrs.html`, called from `gallery.html`, `gallery-portfolio.html` and `gallery-photo.html` — the three templates that today each restate `data-download`, `data-pswp-src` and the rest by hand — produces:

```html
data-license="cc-by-sa-4.0"
data-downloads="400x600 /images/gallery/_DSC2784_hu_f71e34ea8f842b00.jpg|800x1200 /images/gallery/_DSC2784_hu_e5f30ad298aa6102.jpg|2667x4000 /images/gallery/_DSC2784_hu_6b3d532ba01067cb.jpg|5520x8280 /images/gallery/_DSC2784.jpg"
data-download-name="Deckung am Baum - Alpaka lugt hinter einem Stamm hervor.jpg"
```

**As built it RETURNS these rather than printing them**, as `{license, downloads, name, tiers}`, and each caller writes the three attributes from that dict in one line. Go's `html/template` decides its escaping from the *caller's* parse context, and a partial call sitting in attribute-name position inside an open `<a …>` tag is a context this repo has no precedent for; returning a value makes the escaping unambiguous and costs one line per call site while every piece of logic — the renders, the dedupe, the sanitising — still lives in one file. The fourth key, `tiers` (`[{tier, w, h, url}]`), is what the static card in `photo-meta.html` iterates, so the card and the dialog are fed by the same computation rather than by two.

Ascending, `WxH URL`, pipe-separated, already deduplicated by the §2 rule; the JS assigns the tier labels by position from the top (the last is always Original, the first Small, whatever is in between fills Medium and Large). The name is the page's language's, finished and ready to assign (§3) — the same one the static card's links carry, because both come from this partial. The dialog reads these three attributes plus `.caption-artist` and `data-page`, which exist today; it no longer reads `.caption-title`, because it no longer builds a filename. The `RelPermalink`s are the same resources the templates already process — `fit 600x600`, `fit 1200x1200` (today rendered only on the photo page; referencing it from the grid is a cache hit, not a render) and `fit 4000x4000` — so **no image is processed that is not processed now**. Confirmed: the first build carrying the ladder finished in 14 s on a warm cache, where rendering even one new variant per photo runs into minutes.

**The original's dimensions cost nothing.** The published original is the one tier with no processed variant to read a size off, and `AutoOrient`ing it just to ask would be a fourth render for all 648. Instead `.Width`/`.Height` give the stored pair and the already-oriented 4000 variant's own landscape/portrait sense says whether that pair needs swapping — `AutoOrient` only ever rotates by a multiple of 90°, so the oriented pair is that same pair or its swap, and nothing else. Checked against exiftool over all 648 published originals: **zero mismatches**, rotated files included.

**Cost, measured.** The general grid is 1.5 MB raw / 134 KB gzipped today with 572 items. Adding the licence key and the ladder, with realistic hashed paths, comes to **+159 KB raw, +24 KB gzipped** (134 → 158 KB); the name is measured separately below. Hashed filenames do not compress, which is most of the 24. The cheaper alternative — reuse the `<img src>` for Small, `data-pswp-src` for Large, the microdata `contentUrl` for Original, and add only the 1200 URL and the missing dimensions — is about a third of that, at the price of a dialog that reads its inputs from an `<img>`, a PhotoSwipe attribute and a schema.org `<meta>` that each exist for other reasons and may each change for other reasons. One explicit attribute is the better contract for 16 KB gzipped; if the general page ever needs the bytes back, that is the fallback.

**The name attribute's own cost, measured the same way.** `data-download-name` on those 572 items: **+42 KB raw, +3.3 KB gzipped** on `/en/` (134.2 → 137.5), +44.1 / +3.1 on `/de/`, +41.1 / +2.7 on `/sv/`. It is close to free after compression because the identical string already sits on the same element as `title="{{ .Title }}"`, a few dozen bytes away and comfortably inside the deflate window — the mirror image of the hashed paths in `data-downloads`, which have nothing to match against and account for most of that attribute's 24 KB.

## 9. Analytics

`lightbox.js` already reports `Image View` to Plausible with the photo's id and title, deduplicated per slide. A download is the other event worth having: `Image Download` with `gallery_image_id`, `quality` (`small` / `medium` / `large` / `original`) and `license` (the key). Fired on the anchor's click, before the browser starts saving, so the size distribution and the CC-versus-restricted split become visible without any server-side counting. Nothing else is recorded — not the checkbox, not the copy button.

**A gated click reports nothing, and the check is the attribute, not `defaultPrevented`.** The first build got this wrong in both senders: the gate cancels the click, but its handler is registered *after* the row's own (addGate runs once the rows exist) and listeners fire in registration order, so `e.defaultPrevented` was still false when the event went out; on the static card the gate calls `preventDefault` and not `stopPropagation`, so the delegated listener on `document` saw the click regardless. Every blocked click on an all-rights-reserved photo was counted as a download — over-reporting by exactly the visitors who had to go looking for the checkbox, which is precisely the comparison this event exists to make. Both senders now test `aria-disabled` before firing. Measured after the fix: gated click → no event, ticked then clicked → one event; a CC photo, which has no gate and therefore no attribute at all, still reports all four tiers.

**What it cannot see.** Only a click on one of these links passes a listener. A right-click "save image as", a middle-click, and a direct hit on the file's URL do not — so the numbers are a lower bound, and the tiers whose files are easiest to grab another way are the ones most likely to be under-counted. Worth remembering before reading "the original is barely downloaded" off the dashboard.

**Both the goal and the properties have to be enabled in Plausible.** Custom events reach a self-hosted instance regardless, but they surface in the dashboard only once `Image Download` exists as a goal, and `quality` / `license` only once they are allowed as custom properties. That is admin work, not a repo change.

## 10. Cost

| Dimension | Now | After | Note |
|---|---:|---:|---|
| Image renders | 4 per photo used | 4 per photo used | Nothing new is processed; the 1200 render already exists for every photo |
| Build time | — | unchanged | The deed resolves once per language in `license-index.html`, which is `partialCached` |
| General grid HTML | 1.5 MB / 134 KB gz | 1.68 MB / 161 KB gz | The three attributes, §8 — the name costs 3 KB gz of the 27 |
| JS | `lightbox.js` 590 lines | + ~230 lines in a new module | Dialog, `HEAD` sizes, gate, event — no filename logic, that is Hugo's |
| Requests per dialog open | 0 | 4 `HEAD` | Same origin, memoised |
| i18n | — | ~18 keys × 3 languages | Plus the deeds in the licence map |
| Deploy | 7m30s | unchanged | The embedding pass is not touched |

## 11. Build order

Each step leaves the site working; nothing a visitor can see changes before step 4.

1. **Licence data** — `short`, `deed`, `requires_permission` in `data/licenseMap.yaml`, all three keys, all three languages. `license-index.html` resolves them per language and hard-fails on a key without a `deed`. Verify with a deliberate omission that the build stops and names the key.
2. **The ladder partial** — `gallery-download-attrs.html`, wired into the three templates, `data-download` removed. It emits the ladder *and* the sanitised `data-download-name`, so the filename exists before anything that consumes it does. Verify on a fresh build that every `data-downloads` URL resolves to a file under `public/`, that the 46 short originals get a three-step ladder, that `data-download-name` differs between `/en/`, `/de/` and `/sv/` for the same `data-id`, and that the toolbar download still works (it reads the last entry until step 4).
3. **The photo page card** — the static block in `photo-meta.html`, the `#download` link in `.photo-actions`, the `{#contact}` anchors on the licensing pages. Rendered ungated, with the credit line as selectable `<code>` and no copy button in the markup. Verify with JavaScript **off**, which is the whole point of this step and not a spot check: every link saves a file named after the title in that page's language, in all three languages; the all-rights-reserved links work; nothing on the card is inert.
4. **The dialog** — `assets/js/gallery-download.js`, imported by `main.js`; the toolbar element swapped to a button; the `Escape` guard; the `HEAD` sizes; the credit copy button, *added* to the static card as well as built into the dialog; the gate, likewise *added* (§7); the Plausible event. Verify: open from a grid, from a dex species page, from a model page and from the photo page hero; `Escape` closes the dialog and leaves the lightbox open; the second `Escape` closes the lightbox; a middle-click on a size row saves the file.
5. **Styles and strings** — `assets/css/extended/gallery-download.css` for the card, the dialog rules beside the info popup's in `main.scss`, the `# Download` block in `i18n/{en,de,sv}.yaml`. Verify Swedish parity explicitly — the testing concept found eight `sv` keys already missing.
6. **Verify against a fresh build**, not the long-running `hugo server` on :1313, which misses newly created layout files.

The testing concept's layers, when they exist, each get one case from this: the L2 static check that every `data-downloads` URL resolves and every `download=` differs between `/en/`, `/de/` and `/sv/` for the same photo; the L3 scenario for the two-`Escape` sequence and the filename the browser actually saves.

## 12. Files touched

### New

| Path | Purpose |
|---|---|
| `layouts/partials/gallery-download-attrs.html` | Builds and dedupes the ladder; derives the original's oriented dimensions; sanitises the filename. Returns `{license, downloads, name, tiers}` — the callers write the attributes (§8) |
| `assets/js/gallery-download.js` | The dialog: build, open, `HEAD` sizes, the gate (dialog *and* static card), the event. It reads the filename, it does not make one. The copy button is `photo-page.js`'s existing `.photo-copy` control in both places |
| `assets/css/extended/gallery-download.css` | The photo page card's ladder and deed lists, theme-variable based |

### Modified

| Path | Change |
|---|---|
| `data/licenseMap.yaml` | `short`, `deed`, `requires_permission` on every key |
| `layouts/partials/license-index.html` | Resolve the three new fields per language; error on a missing `deed` |
| `layouts/partials/collect-images.html` | Expose `.LicenseShort`, `.LicenseDeed`, `.LicenseRequiresPermission` |
| `layouts/partials/gallery.html`, `gallery-portfolio.html`, `gallery-photo.html` | Call the attrs partial and write the three attributes; drop `data-download`. `gallery-photo.html` also swaps "View full size" for the `#download` link |
| `layouts/partials/photo-meta.html` | The static download card — ungated, copy-button-free, and complete without JavaScript (§7) |
| `layouts/partials/head.html` | `licenses`, `authorEmail`, `contactUrl` and the new labels in the `main.js` params |
| `assets/js/lightbox.js` | Toolbar button → `<button>` that opens the dialog; the `Escape` guard; close the dialog on lightbox close |
| `assets/js/main.js` | Import the new module |
| `assets/css/main.scss` | Dialog rules beside `.pswp-info-popup`. Two gotchas: Sass resolves a bare `min(92vw, 420px)` itself and rejects the mixed units (write the two declarations), and PaperMod strips link underlines globally, which on a dark sheet with no colour to fall back on left the deed link looking like plain text |
| `content/licensing/index.{en,de,sv}.md` | `{#contact}` on the Contact heading |
| `i18n/{en,de,sv}.yaml` | A `# Download` block — 19 keys × 3 languages, parity checked. `photo_view_full` is retired with the link it named |

## 12a. What the build settled

Four things this file could not know before there was a build:

- **The dedupe count is 50, not 46** — the rule is "equal to", and five originals sit at exactly 4000 (§2).
- **The partial returns rather than prints** (§8), and the copy button was already solved in the repo (§7). Both are recorded where they belong; neither changes what a visitor sees.
- **The gate needs one class per surface.** `addGate` is shared by the dialog and the static card, and giving both the dialog's class made the card's gate render *only* because `main.scss` happens to be loaded on every `/gallery` path — luck, with the card's own rule sitting dead in `extended/gallery-download.css`. It now takes the class as an argument. The two stylesheets are separate for a real reason: the card sits in the light/dark page, the dialog only ever over the black lightbox.
- **The credit line's joining word is translated** (§3).

Verified on a fresh build of all three languages: every `.gallery-item` on every surface that renders one — portfolio, general grid, archive, project albums, dex species pages, model pages and the photo-page heroes, 4,650 of them — carries the ladder, and no `data-download` survives anywhere. All 648 photos give three distinct filenames across `en`/`de`/`sv`. In the browser: the toolbar button opens the dialog, the four `HEAD` sizes fill in, the first Escape closes the dialog and leaves the lightbox open, the second closes the lightbox, the gate disables and re-enables the rows, and the console is clean.

## 13. Found in passing

- **The `ImageObject`'s name was the filename — fixed.** `gallery.html` and `gallery-portfolio.html` set `<meta itemprop="name">` from `{{ .Name }}`, the source filename, so **1,671 of the built microdata entries told crawlers the image was called `DSC_0517.jpg`** — while `gallery-photo.html` gave the same entity its real name in `<h1 itemprop="name">`. Two contradictory names for one image, and the useless one sat on the grids that get crawled; 425 of the 648 photos have camera-code source filenames. Both now read `{{ .Title }}`, which `gallery-meta.html` guarantees is non-empty. Verified: 6,048 `itemprop="name"` values in the build, **zero** filenames, zero empty. Found because a hover preview showed a camera name and the question "is the download name wrong?" turned out to be about a different field entirely.
- **The published file's URL still carries the camera name**, and nothing in HTML changes that. `download=` names the *saved* file correctly — measured, not assumed: a real click on a size row produced `Was es verschluckt hat - Sperlingsjunges, gestorben an Plastik.jpg`, and a second click `… (1).jpg`, which is also the evidence for the "no size suffix in the filename" decision above. But the URL itself is `/images/gallery/DSC_0517.jpg`, and that is what a hover preview, "copy link address", a middle-click and a right-click "save image as" all show or save. Neither dev nor production sends a `Content-Disposition` (checked), so nothing overrides it either way. The only real fixes are to rename the sources in the photo store — the workflow CLAUDE.md already documents, `id` stays, so deep links, the likes API and `featured_image:` are unaffected, at the cost of re-rendering those photos' variants — or to publish renamed copies, which needs a language-neutral name and roughly doubles the originals in `public/`. **Open.**
- **The licensing page states the wrong default.** "Most images are licensed under CC BY-ND" — the data says 632 of 648 are **CC BY-SA** and no photo is ND. The page is the one thing the dialog links to for details; it should agree with the dialog.
- **Two contact addresses.** The licensing page and `site.Params.author.email` say `me@lna-dev.net`; `socialIcons` links `info@lna-dev.net`. The dialog uses the author param. Whichever is meant, one of the two should change.
- **The info popup's licence lives under "Copyright"** and, like "Settings", "Gear", "Date taken" and "Tags", the heading is hard-coded English on the German and Swedish sites. Not this concept's job, but once the dialog names the licence properly the popup's section could simply link to it.

## 14. Deliberately out of scope

- **New sizes.** A 1920 or 2560 px "wallpaper" tier would be the first render that exists only for downloading, at 648 renders and a cold-cache cost the repo has a memory about. If the `Image Download` numbers show the Large tier dominating on phones, that is the evidence to revisit with.
- **Server-side download counts.** Plausible gets the event; a counter in the companion API beside the likes is a companion feature, not a site one.
- **Bulk download of an album as a zip.** No client-side zip of 30 × 9 MB.
- **Watermarks, or withholding the original.** The metadata concept settled that publishing the originals stays and that the published copy gets the same metadata treatment as every render. This concept builds on that: the file is out there, and the honest lever is the licence written into it and now shown beside it.
