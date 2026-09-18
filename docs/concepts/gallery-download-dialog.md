# Concept: the download dialog — pick a size, read the licence, get a named file

**Status:** concept, nothing implemented. No build has been run against it.
**Measured:** 2026-09-18, against the working tree (Hugo 0.166.0), `data/gallery.yaml` at 648 photos (632 `cc-by-sa-4.0`, 16 `all-rights-reserved`, 0 `cc-by-nd-4.0`), and a fresh `public/` from the same day (4,163 served gallery files). Every size, count and byte figure below comes from that build.

The lightbox has a download button. It hands over one file — the 4000 px render — under a name like `Alpaca behind tree_hu_564ab7caf97be6b0.JPG`, and says nothing about the licence at the moment it matters most. This replaces the single link with a small dialog: choose one of the renders the site already serves, see the licence and what it lets you do in plain words, and receive a file named after the photo's title in the language you are reading. Photos that are all rights reserved say so, allow the download for private use, and point at the way to ask for anything else.

Nothing here adds an image render. The four sizes on offer exist today for every one of the 648 photos, so the build cost is zero and the deploy time does not move.

## Settled decisions

| | |
|---|---|
| Where | Two entry points, one data set: the lightbox toolbar button (every grid, album, dex, model and photo page) opens the dialog; the photo page also prints the same content as a static block in its licence card, which works without JavaScript — §7 |
| Sizes | The renders that already exist for every photo: **600 · 1200 · 4000 px fit** and the **published original**. No new render, ever — §2 |
| Duplicate tiers | A tier whose dimensions equal the next larger one is not shown. 46 originals are under 4000 px, so their "Large" *is* the original in pixels and only the original is offered — §2 |
| Filename | `<title in the page's language>.jpg`, the same name for every tier — §3 |
| Licence in the dialog | The label linked to the deed, a **may / must / not** block in the reader's language, and for Creative Commons a ready-to-copy **credit line** — §4 |
| Where that text lives | `data/licenseMap.yaml`, per key, per language: new `short`, `deed` and `requires_permission` fields. A key without a `deed` is a build error — §4 |
| All rights reserved | A notice: download for private use only, anything else needs permission. "Contact me" (the site author's address) and "Licensing details" beside it. The size buttons are disabled until a checkbox is ticked — §5 |
| File sizes | Fetched with `HEAD` when the dialog opens, not computed at build time — §6 |
| Dialog element | A native `<dialog>` shown with `showModal()`, the pattern `newsletter-cta.html` already uses. Dark sheet like the info popup, because it only ever opens over the black lightbox — §6 |
| Markup contract | One partial, `gallery-download-attrs.html`, emits `data-license` and `data-downloads` on every `.gallery-item`. The JS reads nothing else — §8 |
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

**The original, on purpose.** It is the one tier that can genuinely surprise: a median of 9 MB and a maximum of 36 MB, on a phone, over Tor. That is the reason the dialog shows the byte size before the click (§6) rather than the reason to hide the tier. Hiding it would be theatre — the URL is in the page's microdata on every grid, and the embedding pass already made the published copy safe to hand out.

## 3. The filename

```
download="<sanitised title in site.Language.Lang>.jpg"
```

The `download` attribute names the saved file for a same-origin URL, which every gallery render is — on the clearnet build and on the onion. The server sets no `Content-Disposition` on static files (`deploy.sh` rsyncs `public/`, nothing sits in front), so the attribute is authoritative. Should a header ever be added, it would win in Chromium; that is worth knowing, not worth designing around.

**The title is always there.** Since the URL work, a missing title in any language is a hard build error, and the data confirms it: all 648 entries carry `en`, `de` and `sv` titles, the longest is 73 characters, and none contains a character a filesystem rejects. The German grid therefore saves `Deckung am Baum - Alpaka lugt hinter einem Stamm hervor.jpg`, the Swedish one `Skydd vid trädet - alpacka kikar fram bakom en stam.jpg`, the English one `Tree Cover - Alpaca Peeking Out From Behind a Trunk.jpg`. Umlauts and `å ä ö` are legal on NTFS, APFS and every Linux filesystem in use; nothing is transliterated.

**Sanitised anyway.** The JS replaces `\ / : * ? " < > |` and control characters with `-`, collapses whitespace, trims trailing dots and spaces (Windows), caps the stem at 120 characters and falls back to `photo-<uuid>` if the result is empty — which cannot happen with today's data, but `.jpg` alone must never be the answer. The extension comes from the render's own URL, lowercased: `.JPG` sources produce `.jpg` files.

**Where the title comes from at runtime.** The grid already emits `<span class="caption-title">` inside `.pswp-caption-content`, resolved for the page's language by `collect-images.html`. The dialog reads that span — no new attribute, and it is the same string the heading shows and the same string `dc:title` carries inside the file.

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
      may: [Keep it for yourself — look at it, use it as a wallpaper, print it for your own wall]
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

> **All rights reserved.** You are welcome to download this photo for yourself — to look at it, to use it as a wallpaper, to print it for your own wall. Publishing it, sharing it or using it commercially needs my permission.
> [Contact me] · [Licensing details]

Then the checkbox — *I will use this photo privately only* — and the size buttons, disabled until it is ticked. The `may / must / not` lists render above the notice exactly as for CC, so the two licence kinds share one layout and differ in the notice and the gate.

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

The photo page already has a licence card in `photo-meta.html`: photographer, licence, "Licensing details". It grows the rest of the dialog as static markup: the `may / must / not` lists, the credit line with its copy button, the notice and the checkbox where the flag says so, and the size ladder as plain `<a download>` links with dimensions. `id="download"` on the card. The "View full size (4000 × 3000)" link in `.photo-actions` becomes **Download** with `href="#download"` — a real in-page link that works with no script at all, the same reasoning `newsletter-cta.html` gives for being a link rather than a button.

That gives the page two renderings of one data set: the static card, and the dialog the hero's lightbox opens. `photo-meta.html` and the info popup are already exactly that pair — the partial's comment says so — and the rule is the same: the two UIs are separate on purpose, only the data is shared. Both read the ladder from `gallery-download-attrs.html` and the deed from `license-index.html`, so they cannot disagree.

The checkbox gate on the static card is JavaScript (a `disabled` attribute the script removes on tick). Without JS the links work and the notice sits directly above them, which is the acceptable degradation — a visitor with scripts off on the Tor build reads the sentence in the same place, one tick fewer.

## 8. The markup contract

One partial, `layouts/partials/gallery-download-attrs.html`, called from `gallery.html`, `gallery-portfolio.html` and `gallery-photo.html` — the three templates that today each restate `data-download`, `data-pswp-src` and the rest by hand — emits:

```html
data-license="cc-by-sa-4.0"
data-downloads="400x600 /images/gallery/_DSC2784_hu_f71e34ea8f842b00.jpg|800x1200 /images/gallery/_DSC2784_hu_e5f30ad298aa6102.jpg|2667x4000 /images/gallery/_DSC2784_hu_6b3d532ba01067cb.jpg|5520x8280 /images/gallery/_DSC2784.jpg"
```

Ascending, `WxH URL`, pipe-separated, already deduplicated by the §2 rule; the JS assigns the tier labels by position from the top (the last is always Original, the first Small, whatever is in between fills Medium and Large). The dialog reads these two attributes plus `.caption-title`, `.caption-artist` and `data-page`, all of which exist today. The `RelPermalink`s are the same resources the templates already process — `fit 600x600`, `fit 1200x1200` (today rendered only on the photo page; referencing it from the grid is a cache hit, not a render) and `fit 4000x4000` — so **no image is processed that is not processed now**.

**Cost, measured.** The general grid is 1.5 MB raw / 134 KB gzipped today with 572 items. Adding the two attributes with realistic hashed paths comes to **+159 KB raw, +24 KB gzipped** (134 → 158 KB). Hashed filenames do not compress, which is most of the 24. The cheaper alternative — reuse the `<img src>` for Small, `data-pswp-src` for Large, the microdata `contentUrl` for Original, and add only the 1200 URL and the missing dimensions — is about a third of that, at the price of a dialog that reads its inputs from an `<img>`, a PhotoSwipe attribute and a schema.org `<meta>` that each exist for other reasons and may each change for other reasons. One explicit attribute is the better contract for 16 KB gzipped; if the general page ever needs the bytes back, that is the fallback.

## 9. Analytics

`lightbox.js` already reports `Image View` to Plausible with the photo's id and title, deduplicated per slide. A download is the other event worth having: `Image Download` with `gallery_image_id`, `quality` (`small` / `medium` / `large` / `original`) and `license` (the key). Fired on the anchor's click, before the browser starts saving, so the size distribution and the CC-versus-restricted split become visible without any server-side counting. Nothing else is recorded — not the checkbox, not the copy button.

## 10. Cost

| Dimension | Now | After | Note |
|---|---:|---:|---|
| Image renders | 4 per photo used | 4 per photo used | Nothing new is processed; the 1200 render already exists for every photo |
| Build time | — | unchanged | The deed resolves once per language in `license-index.html`, which is `partialCached` |
| General grid HTML | 1.5 MB / 134 KB gz | 1.66 MB / 158 KB gz | The two attributes, §8 |
| JS | `lightbox.js` 590 lines | + ~250 lines in a new module | Dialog, sanitiser, `HEAD` sizes, gate, event |
| Requests per dialog open | 0 | 4 `HEAD` | Same origin, memoised |
| i18n | — | ~18 keys × 3 languages | Plus the deeds in the licence map |
| Deploy | 7m30s | unchanged | The embedding pass is not touched |

## 11. Build order

Each step leaves the site working; nothing a visitor can see changes before step 4.

1. **Licence data** — `short`, `deed`, `requires_permission` in `data/licenseMap.yaml`, all three keys, all three languages. `license-index.html` resolves them per language and hard-fails on a key without a `deed`. Verify with a deliberate omission that the build stops and names the key.
2. **The ladder partial** — `gallery-download-attrs.html`, wired into the three templates, `data-download` removed. Verify on a fresh build that every `data-downloads` URL resolves to a file under `public/`, that the 46 short originals get a three-step ladder, and that the toolbar download still works (it reads the last entry until step 4).
3. **The photo page card** — the static block in `photo-meta.html`, the `#download` link in `.photo-actions`, the `{#contact}` anchors on the licensing pages. Verify with JavaScript off: every link saves a file named after the title in that page's language, in all three languages.
4. **The dialog** — `assets/js/gallery-download.js`, imported by `main.js`; the toolbar element swapped to a button; the `Escape` guard; the `HEAD` sizes; the credit copy; the gate; the Plausible event. Verify: open from a grid, from a dex species page, from a model page and from the photo page hero; `Escape` closes the dialog and leaves the lightbox open; the second `Escape` closes the lightbox; a middle-click on a size row saves the file.
5. **Styles and strings** — `assets/css/extended/gallery-download.css` for the card, the dialog rules beside the info popup's in `main.scss`, the `# Download` block in `i18n/{en,de,sv}.yaml`. Verify Swedish parity explicitly — the testing concept found eight `sv` keys already missing.
6. **Verify against a fresh build**, not the long-running `hugo server` on :1313, which misses newly created layout files.

The testing concept's layers, when they exist, each get one case from this: the L2 static check that every `data-downloads` URL resolves and every `download=` differs between `/en/`, `/de/` and `/sv/` for the same photo; the L3 scenario for the two-`Escape` sequence and the filename the browser actually saves.

## 12. Files touched

### New

| Path | Purpose |
|---|---|
| `layouts/partials/gallery-download-attrs.html` | Builds and dedupes the ladder; emits `data-license` and `data-downloads` |
| `assets/js/gallery-download.js` | The dialog: build, open, sanitise the filename, `HEAD` sizes, the gate, the event |
| `assets/css/extended/gallery-download.css` | The photo page card's ladder and deed lists, theme-variable based |

### Modified

| Path | Change |
|---|---|
| `data/licenseMap.yaml` | `short`, `deed`, `requires_permission` on every key |
| `layouts/partials/license-index.html` | Resolve the three new fields per language; error on a missing `deed` |
| `layouts/partials/collect-images.html` | Expose `.LicenseShort`, `.LicenseDeed`, `.LicenseRequiresPermission` |
| `layouts/partials/gallery.html`, `gallery-portfolio.html`, `gallery-photo.html` | Call the attrs partial; drop `data-download` |
| `layouts/partials/photo-meta.html` | The static download card |
| `layouts/partials/head.html` | `licenses`, `authorEmail`, `contactUrl` and the new labels in the `main.js` params |
| `assets/js/lightbox.js` | Toolbar button → `<button>` that opens the dialog; the `Escape` guard; close the dialog on lightbox close |
| `assets/js/main.js` | Import the new module |
| `assets/css/main.scss` | Dialog rules beside `.pswp-info-popup` |
| `content/licensing/index.{en,de,sv}.md` | `{#contact}` on the Contact heading |
| `i18n/{en,de,sv}.yaml` | A `# Download` block |

## 13. Found in passing

- **The licensing page states the wrong default.** "Most images are licensed under CC BY-ND" — the data says 632 of 648 are **CC BY-SA** and no photo is ND. The page is the one thing the dialog links to for details; it should agree with the dialog.
- **Two contact addresses.** The licensing page and `site.Params.author.email` say `me@lna-dev.net`; `socialIcons` links `info@lna-dev.net`. The dialog uses the author param. Whichever is meant, one of the two should change.
- **The info popup's licence lives under "Copyright"** and, like "Settings", "Gear", "Date taken" and "Tags", the heading is hard-coded English on the German and Swedish sites. Not this concept's job, but once the dialog names the licence properly the popup's section could simply link to it.

## 14. Deliberately out of scope

- **New sizes.** A 1920 or 2560 px "wallpaper" tier would be the first render that exists only for downloading, at 648 renders and a cold-cache cost the repo has a memory about. If the `Image Download` numbers show the Large tier dominating on phones, that is the evidence to revisit with.
- **Server-side download counts.** Plausible gets the event; a counter in the companion API beside the likes is a companion feature, not a site one.
- **Bulk download of an album as a zip.** No client-side zip of 30 × 9 MB.
- **Watermarks, or withholding the original.** The metadata concept settled that publishing the originals stays and that the published copy gets the same metadata treatment as every render. This concept builds on that: the file is out there, and the honest lever is the licence written into it and now shown beside it.
