# Concept: gear — cameras and lenses, counted

**Status:** implemented 2026-10-06 — `data/gear.yaml`, `layouts/partials/gear-{map,index,overview,card,segments,pct}.html`, `assets/css/extended/gear.css`, `tests/static/gear.spec.ts`. Open questions settled in review the same day. Where the build differs from the text below it is marked *(implementation)*.
**Read against:** the working tree of 2026-10-06, `data/gallery.yaml` at 661 photos, and the photo store's EXIF (read with exiftool).

One page at `/gallery/gear/` that answers what the gallery already knows but never says: **which lens made which photos, how many of them made the portfolio, and what each lens is used for.** Cameras appear too, but the page is built around lenses — a body is the box, the lens is the decision.

Everything on it is computed at build time from the **published photos alone**: their EXIF and their entry in `data/gallery.yaml`. The site reads nothing from darktable — no shot counts, no ratings, no library (§5).

## Decisions

| | |
|---|---|
| URL | `/<lang>/gallery/gear/`, one page, all three languages. No per-lens pages — §5 |
| Title | Gear / Ausrüstung / Utrustning |
| Data source | The published photos only: their EXIF plus `data/gallery.yaml`. **No darktable data**, neither as shot counts nor as ratings — settled in review |
| Gear on the page | Only what took at least one published photo. Gear that exists only in darktable (today: a Canon EOS R6 Mark III with an RF 24–105) has no record and does not appear — settled in review |
| Gear identity | `data/gear.yaml`: one record per body and per lens, with a slug, a display name and the EXIF spellings that mean it — §2 |
| Unrecognised EXIF string | Hard build error naming the photo and the string, like a missing title: it is the reminder to write the record |
| No camera EXIF at all | Allowed. The 92 photos without it stay without it: counted in a visible "without camera data" bucket, never guessed, no per-photo override — settled in review |
| G91 lens | The G91 has only ever had the LUMIX G VARIO 14–140 II, so a G91 photo without a lens string is that lens (`lens_default`) — confirmed in review |
| Teleconverter | A modifier of its lens, not a lens of its own: counted with the 180–600, shown as "of which 7 with TC‑1.4×" |
| Archive photos | Counted, shown as their own segment of the bar — the page describes the body of work, as the dex does |
| Charts | Rendered by Hugo as HTML tables drawn with CSS. No chart library, no JavaScript needed — §4 |
| Photo pages | Gain the display names and a link from the camera/lens rows to the lens on the gear page |
| Entry point | A text link beside "Archive" on the gallery home, plus the links from every photo |

---

## 1. What the data says today

### Published photos, per lens

From the store files' EXIF joined with `data/gallery.yaml`:

| Lens (body) | Photos | Portfolio | of published | Archive | Dex species | Main categories |
|---|---:|---:|---:|---:|---:|---|
| LUMIX G VARIO 14–140 II (G91) | **336** | 12 | 3.6 % | 24 | 28 | animals 109, plants 97, landscape 86 |
| NIKKOR Z MC 105mm f/2.8 VR S (Z 8) | **83** | 8 | 9.6 % | 0 | 10 | animals 26, landscape 26, plants 13 |
| NIKKOR Z 20mm f/1.8 S (Z 8) | **58** | 0 | 0 % | 1 | 1 | landscape 40 |
| DJI Air 2S, fixed lens | **38** | 0 | 0 % | 15 | 1 | landscape 37 |
| NIKKOR Z 50mm f/1.8 S (Z 8) | **21** | 1 | 4.8 % | 0 | 1 | landscape 15 |
| NIKKOR Z 180–600mm f/5.6–6.3 VR (Z 8) | **21** | 4 | **19 %** | 0 | 8 | animals 19 |
|   … of which with TC‑1.4× | 7 | 1 | | | | |
| OnePlus 9 Pro, phone | **12** | 0 | 0 % | 7 | 5 | animals 9 |
| without camera data | **92** | 2 | | 29 | 8 | landscape 59 |
| **total** | **661** | **27** | | 76 | 46 | |

Two bodies carry the gallery: the G91 (336, mostly 2022–2024) and the Z 8 (183, 2025–2026). The 92 photos without camera data are exactly the 92 whose capture year is unknown to the embed script — the same photos, the same cause.

The column worth a chart is *of published*. The 180–600 has the fewest photos of any Z 8 lens and by far the highest share of them in the portfolio, 4 of 21; the 14–140, the lens with the most photos, has one of the lowest. Neither the count nor the share says that alone; the two side by side do (§3).

### Focal lengths

The zooms are used at their ends. 107 of the G91's 336 photos are at 140 mm (280 mm equivalent), 35 at 14 mm. 13 of the 180–600's 21 are at 600 mm, two more at 840 mm with the converter.

### What Hugo sees today

Hugo reads standard EXIF and XMP, not maker notes. The Panasonic G91 writes its lens **only** into the Panasonic maker note (`LensType: LUMIX G VARIO 14-140/F3.5-5.6 II`) and never into `LensModel` — so `.LensModel` is empty on all 336 G91 photos, and no G91 photo page shows a lens row today. (exiftool's composite `LensID` even calls the same lens "Lumix G Vario 14-140mm F3.5-5.6 Asph. Power OIS", the first version, because the numeric lens id is shared — the camera's own string is the right one.) The bodies show up as the raw `NIKON Z 8` and `DC-G91`. Fixing that is a by-product of §2.

## 2. Gear identity — `data/gear.yaml`

The EXIF strings cannot be the identity: one lens is invisible to Hugo, a converter appears as part of the lens name (`… VR Z TC-1.4x`), and the body names are the cameras' uppercase model codes. So the site gets a small hand-written register, the same move as `data/models.yaml`: the slug is the identity, the display name lives in one place.

```yaml
bodies:
  - slug: nikon-z8
    name: Nikon Z 8
    match: [NIKON Z 8]                 # EXIF Model, compared case-insensitively
    format: full-frame                  # crop 1.0
  - slug: lumix-g91
    name: Panasonic Lumix G91
    match: [DC-G91]
    format: mft                         # crop 2.0
    lens_default: lumix-g-vario-14-140-ii   # its only lens; the G91 writes it only into the maker note
  - slug: dji-air-2s
    name: DJI Air 2S
    match: [FC3411]
    kind: drone                         # a fixed lens: the body is its own lens
  - slug: oneplus-9-pro
    name: OnePlus 9 Pro
    match: [OnePlus 9 Pro]
    kind: phone

lenses:
  - slug: nikkor-z-mc-105
    name: NIKKOR Z MC 105mm f/2.8 VR S
    type: [prime, macro]
    match: [NIKKOR Z MC 105mm f/2.8 VR S]
  - slug: nikkor-z-180-600
    name: NIKKOR Z 180–600mm f/5.6–6.3 VR
    type: [zoom]
    match:
      - NIKKOR Z 180-600mm f/5.6-6.3 VR
      - { name: NIKKOR Z 180-600mm f/5.6-6.3 VR Z TC-1.4x, teleconverter: 1.4 }
  - slug: lumix-g-vario-14-140-ii
    name: LUMIX G VARIO 14–140mm F3.5–5.6 II
    type: [zoom]
    match: []                           # Hugo never sees a string for it; reached through lens_default
  # optional on any record: note {en, de, sv}, cover (gallery UUID)
```

Rules — the file's own by `gear-map.html`, the photos' by `gear-index.html` *(implementation; the header comment of `data/gear.yaml` is the field reference)*:

- **An EXIF body or lens string that matches no record stops the build**, naming the photo and the string. Gear is a small closed set the author owns, so a miss is always a new lens nobody wrote down — the same reasoning as an unknown `model:` slug, and the same effect as a missing title: the first published photo from a new lens is the reminder to add it. Gear that took no published photo never needs a record.
- **A photo with no camera EXIF at all is not an error.** It lands in the "without camera data" bucket. Nothing is inferred from the filename, the date or the category, and there is no per-photo override.
- `lens_default` applies only when the body is known and `LensModel` is empty — today the 336 G91 photos. `kind: drone | phone` bodies count as their own lens.
- Slugs are unique across bodies and lenses (they are anchors on one page), and an alias may belong to one record only.
- A record that no published photo resolves to renders nothing, like a model without photos.

`collect-images.html` resolves each photo once, through a `partialCached` lookup map keyed by the lowercased EXIF string, and exposes `.BodySlug` / `.LensSlug` / `.Teleconverter` next to the existing fields. `.CameraModel` and `.LensModel` switch to the **display names** — so all 336 G91 photo pages gain a lens row and every photo page says `Nikon Z 8` instead of `NIKON Z 8` — and the photo page, the lightbox and the photo-meta rows link both to `/gallery/gear/#<slug>`. The collector is hot (it runs once per dex species page), which is why the lookup is a prebuilt map and not a loop over `gear.yaml`.

## 3. The page

A single page, top to bottom. Every number comes from the same aggregate, so no two sections can disagree. *(implementation)* The overview charts come first and the lens cards after them — seven cards would otherwise push every chart below the fold, and each chart row links down to its card.

```
Gallery › Gear

  Gear
  [ Photos 661 ]  [ Cameras 4 ]  [ Lenses 5 ]  [ In the portfolio 27 ]

  ── Into the portfolio ───────────────────────────────────────────────────
     ■ portfolio  ■ gallery  ■ archive
     Lens        Photos                              Portfolio share
     14-140mm    ▮████████████████████████▯  336     ███          3.6%
     MC 105mm    ▮██████  83                         ████████     9.6%
     180-600mm   ▮█  21                              ████████████████  19%
     …

  ── Focal lengths ────────────────────────────────────────────────────────
                18–24  25–35  36–50  51–85  86–135  136–200  201–300  …
     14-140mm          [37]   [14]   [31]   [56]    [42]     [154]
     MC 105mm                               [83]
     …                       shade = share of that lens's photos

  ── Timeline ─────────────────────────────────────────────────────────────
                2022        2023        2024        2025        2026
     14-140mm     ● ● ● ●   ● ● ● ●   ● ● ● ●   ●
     MC 105mm                                   ● ● ●       · ●
     …            one column per quarter, dot area ∝ photos

  ── Lenses ───────────────────────────────────────────────────────────────
  ┌──────────────────────────────────────┐
  │  NIKKOR Z MC 105mm f/2.8 VR S        │
  │  on the Nikon Z 8   [Prime] [Macro]  │
  │  Photos 83   Portfolio 8 9.6%   Dex species 10
  │  ▮██████████████████████████████     │
  │  Photos from   May 2025 – Jul 2026   │
  │  Typical       f/11 · ISO 160        │
  │  Subjects      Landscape 26 · …      │
  │  [photo] [photo] [photo]             │
  └──────────────────────────────────────┘
  … one card per lens or drone / phone, most photos first

  ── Cameras ──────────────────────────────────────────────────────────────
     Panasonic Lumix G91 (14-140mm)       ███████████████  336
     Nikon Z 8 (MC 105mm, 20mm, 50mm, 180-600mm)  ████████  183
     …

  92 photos carry no camera data and are counted under no lens.
```

- **Lens cards are the core.** Each card: name, body, type badges, the first and last month of a published photo taken with it; published count with a portfolio / gallery / archive bar; portfolio share; dex species count; median aperture and ISO; for a zoom the focal length used most often; the top three categories; a teleconverter line where one was used; and three photos — `cover:` first, then portfolio, then newest — as the existing 600 px tiles linking to their photo pages. Drone and phone bodies get a card each.
- **Into the portfolio** puts the published count (as a portfolio / gallery / archive stack) and the portfolio share per lens side by side, which is where §1's finding shows itself without a sentence explaining it.
- **Focal lengths** use the 35 mm equivalent so the G91 and the Z 8 share one axis: EXIF `FocalLengthIn35mmFormat` where the file has it, else focal length × the body's `crop`. *(implementation)* A lens × bin table with the count in every cell and four shades by the cell's share of that lens's photos, rather than bars stacked by lens: seven stacked series would need seven colours, a row per lens needs one ramp. Log-spaced bins, empty ones at either end trimmed. The phone writes no 35 mm value and has no crop factor, so it has no row.
- **Timeline**: one row per lens, one column per quarter from the first dated photo to the last, a dot sized by count (area). It shows the switch from the G91 to the Z 8 in 2025 at a glance.
- **Cameras** last and compact, each with its lenses linked.
- **The footnote** names the photos without camera data. They are part of every total on the site, so a page that counts per lens says where they went instead of letting the sums quietly not add up.

## 4. Build

- `layouts/partials/gear-index.html`, `partialCached`, reads `gallery-collected.html` (already cached, already carries every photo's EXIF) and `data/gear.yaml`, and returns one aggregate per lens and body plus the without-camera-data bucket. Every section of the page reads only that.
- Section stub `content/gallery/gear/_index.{en,de,sv}.md` with `params.theme: gear-home`, dispatched in `layouts/_default/list.html`, and `outputs: [HTML]` — without it the section would emit another copy of the whole gallery feed per language, the bug `gallery-models.md` fixed for its own section.
- **Charts as server-rendered HTML tables drawn with CSS, no chart library.** The alternative is a vendored library like Chart.js or ECharts. It loses here on every count that matters for this site: the data is fixed per build, so there is nothing for client-side rendering to do; a canvas chart is invisible without JavaScript and to screen readers, while a table is the accessible "table view" of its own chart and its text goes through the same `i18n` calls as the rest of the page; PaperMod's theme variables give dark mode for free, where a canvas library needs its colours re-plumbed per theme; and it is 100–300 KB of script on a page that should load like the dex map, with nothing third-party, on the onion build too. *(implementation)* Tables rather than the inline SVG first proposed: every chart here is rows × columns, and a table wraps, scrolls and localises without measuring text. PaperMod makes every `table` `display: block`; `.gear table` resets it. The colours are one blue ramp, validated as ordinal ramps against white and PaperMod's dark `--entry` and flipped in dark mode (the most important step is the lightest there).
- Structured data: a plain `WebPage`. No `Product` or `Review` markup — that would claim reviews and invite rich results for gear the page does not review.
- Indexable and in the sitemap: unlike the tag pages, this is the owner's own content.
- i18n under a `# Gear` block in `i18n/{en,de,sv}.yaml`; styles in `assets/css/extended/gear.css`, theme variables only.
- One new published URL per language → `npm run golden:update`.
- Tests: `tests/static/gear.spec.ts` — every card counts exactly the photo pages that link to it (the photo pages are the per-photo truth, and need no EXIF reader in the test), the cards plus the footnote account for every photo in `data/gallery.yaml`, and a body with a `lens_default` leaves no photo page without a lens row. *(implementation)* The unknown-EXIF-string check lives in `gear-index.html`, not in `gallery-meta.html`: only `collect-images.html` sees EXIF, and it is not cached at its call sites.

## 5. Deliberately out

- **No darktable data.** Shot counts would make a funnel (*shot → published → portfolio*), but the library covers only part of the history — many G91 photos were straight-from-camera JPEGs that never went through it — and it is workflow data on one machine, not something the site should depend on. No ratings either. Settled in review; revisit only with a data source that covers the whole history.
- **No gear without a published photo.** A body that exists only in darktable is not on the page and needs no record.
- **No per-lens pages.** Five lenses do not need five URLs; a card with an anchor is the right size, and the photo strips already exist on the photo and tag pages. Revisit if the gear list grows past a dozen.
- **No prices, shop or affiliate links**, no "recommended gear" — it is a record, not a review.
- **No shutter counts** from maker notes: a body's mileage, not a photographic statement, and only some cameras write it.
- **Nothing inferred for a photo without camera EXIF** — not from its date, its neighbours or its category, and no hand-written override.

## 6. Build order

1. `data/gear.yaml` with the current five lenses and four bodies; the lookup and its validation in `gear-map.html` / `collect-images.html`; display names and gear links on the photo pages and in the lightbox. Visible on its own: the G91 lens row appears on 336 pages.
2. `gear-index.html` and the page: header, the portfolio chart, focal lengths, timeline, lens cards, cameras, footnote. Gallery-home link, search index, golden list.
3. Tests; `CLAUDE.md` and `AGENTS.md` sections.
